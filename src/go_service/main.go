package main

import (
        "context"
        "crypto/sha256"
        "encoding/hex"
        "encoding/json"
        "fmt"
        "io"
        "log"
        "net/http"
        "os"
        "strings"
        "time"

        "github.com/gorilla/mux"
        "github.com/jackc/pgx/v5"
        "github.com/google/uuid"
        "github.com/Masterminds/semver/v3"
        "github.com/golang-jwt/jwt/v5"
)

// CRDTPayload represents the structure for CRDT-based test results
type CRDTPayload struct {
        SessionID      string                   `json:"session_id"`
        Changes        []map[string]interface{} `json:"changes"`
        VectorClock    map[string]int          `json:"vector_clock"`
        IdempotencyKey string                  `json:"idempotency_key"`
}

// EvidenceResponse represents the response for evidence submission
type EvidenceResponse struct {
        EvidenceID string `json:"evidence_id"`
        Hash       string `json:"hash"`
        Status     string `json:"status"`
}

// CRDTResponse represents the response for CRDT results
type CRDTResponse struct {
        SessionID   string         `json:"session_id"`
        Status      string         `json:"status"`
        VectorClock map[string]int `json:"vector_clock"`
}

// FaultDataInput represents the structure for fault classification input
type FaultDataInput struct {
        ItemCode          string `json:"item_code"`
        ObservedCondition string `json:"observed_condition"`
}

// ClassificationResult represents the structure for classification response
type ClassificationResult struct {
        Classification   string `json:"classification"`
        RuleApplied      string `json:"rule_applied"`
        VersionApplied   string `json:"version_applied"`
        AuditLogID       string `json:"audit_log_id"`
}

// AS1851Rule represents an AS1851 compliance rule
type AS1851Rule struct {
        ID          string                 `json:"id"`
        RuleCode    string                 `json:"rule_code"`
        Version     string                 `json:"version"`
        RuleName    string                 `json:"rule_name"`
        Description string                 `json:"description"`
        RuleSchema  map[string]interface{} `json:"rule_schema"`
        IsActive    bool                   `json:"is_active"`
        CreatedAt   time.Time              `json:"created_at"`
}

// IdempotencyCheck represents an idempotency key check
type IdempotencyCheck struct {
        KeyHash      string    `json:"key_hash"`
        UserID       string    `json:"user_id"`
        Endpoint     string    `json:"endpoint"`
        RequestHash  string    `json:"request_hash"`
        ResponseData string    `json:"response_data,omitempty"`
        StatusCode   int       `json:"status_code,omitempty"`
        ExpiresAt    time.Time `json:"expires_at"`
}

// Database connection
var db *pgx.Conn

// Initialize database connection
func initDB() error {
        databaseURL := os.Getenv("DATABASE_URL")
        if databaseURL == "" {
                return fmt.Errorf("DATABASE_URL environment variable not set")
        }

        var err error
        db, err = pgx.Connect(context.Background(), databaseURL)
        if err != nil {
                return fmt.Errorf("failed to connect to database: %v", err)
        }
        return nil
}

// JWT validation middleware for internal service communication
func validateInternalJWT(next http.HandlerFunc) http.HandlerFunc {
        return func(w http.ResponseWriter, r *http.Request) {
                tokenStr := r.Header.Get("X-Internal-Authorization")
                if tokenStr == "" {
                        http.Error(w, "Unauthorized", http.StatusUnauthorized)
                        return
                }
                
                token, err := jwt.Parse(tokenStr, func(token *jwt.Token) (interface{}, error) {
                        // Validate signing method
                        if _, ok := token.Method.(*jwt.SigningMethodHMAC); !ok {
                                return nil, fmt.Errorf("unexpected signing method: %v", token.Header["alg"])
                        }
                        return []byte(os.Getenv("INTERNAL_JWT_SECRET_KEY")), nil
                })
                
                if err != nil || !token.Valid {
                        http.Error(w, "Invalid token", http.StatusUnauthorized)
                        return
                }
                
                next(w, r)
        }
}

        // Test the connection
        if err := db.Ping(context.Background()); err != nil {
                return fmt.Errorf("failed to ping database: %v", err)
        }

        log.Println("Database connection established")
        return nil
}

// calculateSHA256 calculates SHA-256 hash of the input data
func calculateSHA256(data []byte) string {
        hash := sha256.Sum256(data)
        return hex.EncodeToString(hash[:])
}

// checkIdempotency checks if a request is idempotent
func checkIdempotency(ctx context.Context, keyHash, userID, endpoint, requestHash string) (*IdempotencyCheck, error) {
        var check IdempotencyCheck
        
        query := `
                SELECT key_hash, user_id, endpoint, request_hash, response_data, status_code, expires_at
                FROM idempotency_keys 
                WHERE key_hash = $1 AND expires_at > CURRENT_TIMESTAMP
        `
        
        row := db.QueryRow(ctx, query, keyHash)
        err := row.Scan(&check.KeyHash, &check.UserID, &check.Endpoint, 
                &check.RequestHash, &check.ResponseData, &check.StatusCode, &check.ExpiresAt)
        
        if err == pgx.ErrNoRows {
                return nil, nil // No existing request found
        }
        if err != nil {
                return nil, fmt.Errorf("failed to check idempotency: %v", err)
        }
        
        return &check, nil
}

// storeIdempotencyKey stores an idempotency key
func storeIdempotencyKey(ctx context.Context, keyHash, userID, endpoint, requestHash string, responseData interface{}, statusCode int) error {
        responseJSON, _ := json.Marshal(responseData)
        expiresAt := time.Now().Add(24 * time.Hour) // 24 hour expiration
        
        query := `
                INSERT INTO idempotency_keys (key_hash, user_id, endpoint, request_hash, response_data, status_code, expires_at)
                VALUES ($1, $2, $3, $4, $5, $6, $7)
                ON CONFLICT (key_hash) DO NOTHING
        `
        
        _, err := db.Exec(ctx, query, keyHash, userID, endpoint, requestHash, responseJSON, statusCode, expiresAt)
        return err
}

// evidenceHandler handles POST /v1/evidence endpoint
func evidenceHandler(w http.ResponseWriter, r *http.Request) {
        if r.Method != http.MethodPost {
                http.Error(w, "Method not allowed", http.StatusMethodNotAllowed)
                return
        }

        // Read and hash the request body for idempotency
        body, err := io.ReadAll(r.Body)
        if err != nil {
                http.Error(w, "Failed to read request body", http.StatusBadRequest)
                return
        }

        requestHash := calculateSHA256(body)
        
        // Get idempotency key from header
        idempotencyKey := r.Header.Get("Idempotency-Key")
        if idempotencyKey == "" {
                http.Error(w, "Idempotency-Key header required", http.StatusBadRequest)
                return
        }
        
        keyHash := calculateSHA256([]byte(idempotencyKey))
        userID := r.Header.Get("X-User-ID") // Assume this is set by the reverse proxy
        
        // Check idempotency
        ctx := context.Background()
        existingCheck, err := checkIdempotency(ctx, keyHash, userID, "/v1/evidence", requestHash)
        if err != nil {
                log.Printf("Idempotency check failed: %v", err)
                http.Error(w, "Internal server error", http.StatusInternalServerError)
                return
        }
        
        if existingCheck != nil {
                // Return cached response
                w.Header().Set("Content-Type", "application/json")
                w.WriteHeader(existingCheck.StatusCode)
                w.Write([]byte(existingCheck.ResponseData))
                return
        }

        // Parse request
        var evidenceReq EvidenceRequest
        if err := json.Unmarshal(body, &evidenceReq); err != nil {
                http.Error(w, "Invalid JSON", http.StatusBadRequest)
                return
        }

        // Validate required fields
        if evidenceReq.SessionID == "" || evidenceReq.EvidenceType == "" {
                http.Error(w, "session_id and evidence_type are required", http.StatusBadRequest)
                return
        }

        // Calculate checksum if data is provided
        var checksum string
        if evidenceReq.Data != "" {
                checksum = calculateSHA256([]byte(evidenceReq.Data))
        }

        // Store evidence in database
        metadataJSON, _ := json.Marshal(evidenceReq.Metadata)
        
        query := `
                INSERT INTO evidence (session_id, evidence_type, file_path, metadata, checksum, created_at)
                VALUES ($1, $2, $3, $4, $5, CURRENT_TIMESTAMP)
                RETURNING id
        `
        
        var evidenceID string
        err = db.QueryRow(ctx, query, evidenceReq.SessionID, evidenceReq.EvidenceType, 
                evidenceReq.FilePath, metadataJSON, checksum).Scan(&evidenceID)
        
        if err != nil {
                log.Printf("Failed to store evidence: %v", err)
                http.Error(w, "Failed to store evidence", http.StatusInternalServerError)
                return
        }

        // Prepare response
        response := map[string]interface{}{
                "evidence_id": evidenceID,
                "checksum":    checksum,
                "status":      "stored",
                "timestamp":   time.Now().UTC(),
        }

        // Store idempotency key
        if err := storeIdempotencyKey(ctx, keyHash, userID, "/v1/evidence", requestHash, response, http.StatusCreated); err != nil {
                log.Printf("Failed to store idempotency key: %v", err)
        }

        // Return response
        w.Header().Set("Content-Type", "application/json")
        w.WriteHeader(http.StatusCreated)
        json.NewEncoder(w).Encode(response)
}

// testResultsHandler handles POST /v1/tests/sessions/{session_id}/results endpoint
func testResultsHandler(w http.ResponseWriter, r *http.Request) {
        if r.Method != http.MethodPost {
                http.Error(w, "Method not allowed", http.StatusMethodNotAllowed)
                return
        }

        // Extract session_id from URL
        vars := mux.Vars(r)
        sessionID := vars["session_id"]
        if sessionID == "" {
                http.Error(w, "session_id is required", http.StatusBadRequest)
                return
        }

        // Read and hash the request body for idempotency
        body, err := io.ReadAll(r.Body)
        if err != nil {
                http.Error(w, "Failed to read request body", http.StatusBadRequest)
                return
        }

        requestHash := calculateSHA256(body)
        
        // Get idempotency key from header
        idempotencyKey := r.Header.Get("Idempotency-Key")
        if idempotencyKey == "" {
                http.Error(w, "Idempotency-Key header required", http.StatusBadRequest)
                return
        }
        
        keyHash := calculateSHA256([]byte(idempotencyKey))
        userID := r.Header.Get("X-User-ID")
        endpoint := fmt.Sprintf("/v1/tests/sessions/%s/results", sessionID)
        
        // Check idempotency
        ctx := context.Background()
        existingCheck, err := checkIdempotency(ctx, keyHash, userID, endpoint, requestHash)
        if err != nil {
                log.Printf("Idempotency check failed: %v", err)
                http.Error(w, "Internal server error", http.StatusInternalServerError)
                return
        }
        
        if existingCheck != nil {
                // Return cached response
                w.Header().Set("Content-Type", "application/json")
                w.WriteHeader(existingCheck.StatusCode)
                w.Write([]byte(existingCheck.ResponseData))
                return
        }

        // Parse request
        var resultsReq TestResultRequest
        if err := json.Unmarshal(body, &resultsReq); err != nil {
                http.Error(w, "Invalid JSON", http.StatusBadRequest)
                return
        }

        resultsReq.SessionID = sessionID

        // Update test session with results
        resultsJSON, _ := json.Marshal(resultsReq.Results)
        
        query := `
                UPDATE test_sessions 
                SET session_data = COALESCE(session_data, '{}') || $2,
                    updated_at = CURRENT_TIMESTAMP
                WHERE id = $1
                RETURNING id
        `
        
        var updatedSessionID string
        err = db.QueryRow(ctx, query, sessionID, resultsJSON).Scan(&updatedSessionID)
        
        if err == pgx.ErrNoRows {
                http.Error(w, "Session not found", http.StatusNotFound)
                return
        }
        if err != nil {
                log.Printf("Failed to update session: %v", err)
                http.Error(w, "Failed to update session", http.StatusInternalServerError)
                return
        }

        // Prepare response
        response := map[string]interface{}{
                "session_id": updatedSessionID,
                "status":     "updated",
                "timestamp":  time.Now().UTC(),
        }

        // Store idempotency key
        if err := storeIdempotencyKey(ctx, keyHash, userID, endpoint, requestHash, response, http.StatusOK); err != nil {
                log.Printf("Failed to store idempotency key: %v", err)
        }

        // Return response
        w.Header().Set("Content-Type", "application/json")
        w.WriteHeader(http.StatusOK)
        json.NewEncoder(w).Encode(response)
}

// classificationHandler handles POST /v1/classify endpoint
func classificationHandler(w http.ResponseWriter, r *http.Request) {
        if r.Method != http.MethodPost {
                http.Error(w, "Method not allowed", http.StatusMethodNotAllowed)
                return
        }

        // Read and parse request body
        body, err := io.ReadAll(r.Body)
        if err != nil {
                http.Error(w, "Failed to read request body", http.StatusBadRequest)
                return
        }

        var input FaultDataInput
        if err := json.Unmarshal(body, &input); err != nil {
                http.Error(w, "Invalid JSON", http.StatusBadRequest)
                return
        }

        // Validate required fields
        if input.ItemCode == "" || input.ObservedCondition == "" {
                http.Error(w, "item_code and observed_condition are required", http.StatusBadRequest)
                return
        }

        userID := r.Header.Get("X-User-ID")
        if userID == "" {
                userID = "go_service_unauthenticated"
        }

        clientIP := r.Header.Get("X-Forwarded-For")
        if clientIP == "" {
                clientIP = r.RemoteAddr
        }
        
        // Remove port from IP address for inet column compatibility
        if idx := strings.LastIndex(clientIP, ":"); idx != -1 && !strings.Contains(clientIP, "::") {
                clientIP = clientIP[:idx]
        }
        userAgent := r.Header.Get("User-Agent")

        ctx := context.Background()

        // Find the latest active rule
        rule, err := findLatestActiveAS1851Rule(ctx, input.ItemCode)
        if err != nil {
                // Create audit log for failed classification
                createClassificationAuditLog(ctx, userID, input, nil, "", clientIP, userAgent, false, err.Error())
                
                if err.Error() == "no active rule found" {
                        http.Error(w, fmt.Sprintf("No active rule found for item code '%s'", input.ItemCode), http.StatusNotFound)
                } else {
                        http.Error(w, "Internal server error", http.StatusInternalServerError)
                }
                return
        }

        // Apply rule logic to get classification
        classification, err := applyAS1851Rule(rule, input.ObservedCondition)
        if err != nil {
                // Create audit log for failed classification
                createClassificationAuditLog(ctx, userID, input, rule, "", clientIP, userAgent, false, err.Error())
                http.Error(w, err.Error(), http.StatusUnprocessableEntity)
                return
        }

        // Create audit log for successful classification
        auditLogID, err := createClassificationAuditLog(ctx, userID, input, rule, classification, clientIP, userAgent, true, "")
        if err != nil {
                log.Printf("Failed to create audit log: %v", err)
                http.Error(w, "Failed to create audit log", http.StatusInternalServerError)
                return
        }

        // Return successful response
        response := ClassificationResult{
                Classification:   classification,
                RuleApplied:      rule.RuleCode,
                VersionApplied:   rule.Version,
                AuditLogID:       auditLogID,
        }

        w.Header().Set("Content-Type", "application/json")
        w.WriteHeader(http.StatusOK)
        json.NewEncoder(w).Encode(response)
}

// findLatestActiveAS1851Rule finds the latest active rule by semantic version
func findLatestActiveAS1851Rule(ctx context.Context, itemCode string) (*AS1851Rule, error) {
        query := `
                SELECT id, rule_code, version, rule_name, description, rule_schema, is_active, created_at
                FROM as1851_rules 
                WHERE rule_code = $1 AND is_active = true
                ORDER BY version DESC
        `
        
        rows, err := db.Query(ctx, query, itemCode)
        if err != nil {
                return nil, fmt.Errorf("database query failed: %v", err)
        }
        defer rows.Close()

        var rules []AS1851Rule
        for rows.Next() {
                var rule AS1851Rule
                var ruleSchemaJSON []byte
                
                err := rows.Scan(&rule.ID, &rule.RuleCode, &rule.Version, &rule.RuleName, 
                        &rule.Description, &ruleSchemaJSON, &rule.IsActive, &rule.CreatedAt)
                if err != nil {
                        return nil, fmt.Errorf("failed to scan rule: %v", err)
                }

                // Parse rule_schema JSON
                if err := json.Unmarshal(ruleSchemaJSON, &rule.RuleSchema); err != nil {
                        log.Printf("Failed to parse rule_schema for rule %s: %v", rule.ID, err)
                        continue
                }

                rules = append(rules, rule)
        }

        if len(rules) == 0 {
                return nil, fmt.Errorf("no active rule found")
        }

        // Find the highest semantic version
        var latestRule *AS1851Rule
        var latestVersion *semver.Version

        for i := range rules {
                version, err := semver.NewVersion(rules[i].Version)
                if err != nil {
                        log.Printf("Invalid semantic version %s for rule %s, skipping", rules[i].Version, rules[i].ID)
                        continue
                }

                if latestVersion == nil || version.GreaterThan(latestVersion) {
                        latestVersion = version
                        latestRule = &rules[i]
                }
        }

        if latestRule == nil {
                return nil, fmt.Errorf("no valid semantic versions found")
        }

        return latestRule, nil
}

// applyAS1851Rule applies the rule logic to classify the observed condition
func applyAS1851Rule(rule *AS1851Rule, observedCondition string) (string, error) {
        // Look for the observed condition in the rule schema
        if classification, exists := rule.RuleSchema[observedCondition]; exists {
                if classStr, ok := classification.(string); ok {
                        return classStr, nil
                }
        }
        
        return "", fmt.Errorf("condition '%s' not found in rule '%s'", observedCondition, rule.RuleCode)
}

// createClassificationAuditLog creates an audit log entry for classification attempts
func createClassificationAuditLog(ctx context.Context, userID string, input FaultDataInput, rule *AS1851Rule, classification, clientIP, userAgent string, success bool, errorDetail string) (string, error) {
        // Create old_values with input data
        oldValues := map[string]interface{}{
                "item_code":          input.ItemCode,
                "observed_condition": input.ObservedCondition,
        }

        // Create new_values with classification result
        newValues := map[string]interface{}{}
        if success && rule != nil {
                newValues["classification"] = classification
                newValues["rule_version"] = rule.Version
        }

        // Add error details if failed
        if !success {
                newValues["error"] = errorDetail
        }

        oldValuesJSON, err := json.Marshal(oldValues)
        if err != nil {
                log.Printf("Failed to marshal oldValues: %v", err)
                return "", fmt.Errorf("failed to marshal old values: %v", err)
        }
        
        newValuesJSON, err := json.Marshal(newValues)
        if err != nil {
                log.Printf("Failed to marshal newValues: %v", err)
                return "", fmt.Errorf("failed to marshal new values: %v", err)
        }

        var ruleIDUsed interface{}
        if rule != nil {
                ruleIDUsed = rule.ID
        } else {
                ruleIDUsed = nil
        }

        auditLogID := uuid.New().String()

        query := `
                INSERT INTO audit_log (id, user_id, action, resource_type, resource_id, old_values, new_values, ip_address, user_agent, created_at)
                VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, CURRENT_TIMESTAMP)
        `

        _, err = db.Exec(ctx, query, auditLogID, userID, "CLASSIFY_FAULT", "as1851_rule", ruleIDUsed, string(oldValuesJSON), string(newValuesJSON), clientIP, userAgent)
        if err != nil {
                log.Printf("Audit log creation failed - auditLogID: %s, userID: %s, error: %v", auditLogID, userID, err)
                return "", fmt.Errorf("failed to create audit log: %v", err)
        }

        return auditLogID, nil
}

// healthHandler handles health checks
func healthHandler(w http.ResponseWriter, r *http.Request) {
        w.Header().Set("Content-Type", "application/json")
        w.WriteHeader(http.StatusOK)
        json.NewEncoder(w).Encode(map[string]string{"status": "ok", "service": "go-performance-service"})
}

func main() {
        // Initialize database connection
        if err := initDB(); err != nil {
                log.Fatalf("Failed to initialize database: %v", err)
        }
        defer db.Close(context.Background())

        // Create router
        router := mux.NewRouter()

        // Add routes with JWT middleware for internal endpoints
        router.HandleFunc("/v1/evidence", validateInternalJWT(evidenceHandler)).Methods("POST")
        router.HandleFunc("/v1/tests/sessions/{session_id}/results", validateInternalJWT(testResultsHandler)).Methods("POST")
        router.HandleFunc("/v1/classify", classificationHandler).Methods("POST")
        router.HandleFunc("/health", healthHandler).Methods("GET")

        // Start server
        port := ":9090"
        log.Printf("Go performance service starting on port %s", port)
        
        server := &http.Server{
                Addr:         port,
                Handler:      router,
                ReadTimeout:  15 * time.Second,
                WriteTimeout: 15 * time.Second,
                IdleTimeout:  60 * time.Second,
        }

        if err := server.ListenAndServe(); err != nil {
                log.Fatalf("Server failed to start: %v", err)
        }
}