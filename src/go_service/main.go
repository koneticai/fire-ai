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
        "runtime"
        "runtime/debug"
        "time"

        "github.com/golang-jwt/jwt/v5"
        "github.com/gorilla/mux"
        "github.com/jackc/pgx/v5"
        "github.com/jackc/pgx/v5/pgxpool"
        "github.com/google/uuid"
        _ "net/http/pprof" // Import pprof for profiling endpoints
)

// CRDT payload structure for distributed session data
type CRDTPayload struct {
        SessionID      string                   `json:"session_id"`
        Changes        []map[string]interface{} `json:"changes"`
        VectorClock    map[string]int           `json:"vector_clock"`
        IdempotencyKey string                   `json:"idempotency_key"`
}

// CRDT response structure
type CRDTResponse struct {
        SessionID    string         `json:"session_id"`
        Status       string         `json:"status"`
        VectorClock  map[string]int `json:"vector_clock"`
        ProcessedAt  time.Time      `json:"processed_at"`
}

// Evidence submission structures
type EvidenceResponse struct {
        EvidenceID string `json:"evidence_id"`
        Hash       string `json:"hash"`
        Status     string `json:"status"`
}

// Idempotency check structure
type IdempotencyCheck struct {
        KeyHash      string    `json:"key_hash"`
        UserID       string    `json:"user_id"`
        Endpoint     string    `json:"endpoint"`
        RequestHash  string    `json:"request_hash"`
        ResponseData string    `json:"response_data"`
        StatusCode   int       `json:"status_code"`
        ExpiresAt    time.Time `json:"expires_at"`
}

// Database connection pool
var dbPool *pgxpool.Pool

// Initialize database connection pool
func initDB() error {
        databaseURL := os.Getenv("DATABASE_URL")
        if databaseURL == "" {
                return fmt.Errorf("DATABASE_URL environment variable not set")
        }

        config, err := pgxpool.ParseConfig(databaseURL)
        if err != nil {
                return fmt.Errorf("failed to parse database URL: %v", err)
        }

        // Configure connection pool settings for production
        config.MaxConns = 30
        config.MinConns = 5
        config.MaxConnLifetime = 1 * time.Hour
        config.MaxConnIdleTime = 30 * time.Minute

        dbPool, err = pgxpool.NewWithConfig(context.Background(), config)
        if err != nil {
                return fmt.Errorf("failed to create connection pool: %v", err)
        }

        // Test the connection
        if err := dbPool.Ping(context.Background()); err != nil {
                return fmt.Errorf("failed to ping database: %v", err)
        }

        log.Println("Database connection pool established")
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

                secret := os.Getenv("INTERNAL_JWT_SECRET_KEY")
                if secret == "" {
                        http.Error(w, "Internal configuration error", http.StatusInternalServerError)
                        return
                }

                token, err := jwt.Parse(tokenStr, func(token *jwt.Token) (interface{}, error) {
                        // Validate signing method
                        if _, ok := token.Method.(*jwt.SigningMethodHMAC); !ok {
                                return nil, fmt.Errorf("unexpected signing method: %v", token.Header["alg"])
                        }
                        return []byte(secret), nil
                })

                if err != nil || !token.Valid {
                        log.Printf("JWT validation failed: %v", err)
                        http.Error(w, "Invalid token", http.StatusUnauthorized)
                        return
                }

                // Validate claims
                if claims, ok := token.Claims.(jwt.MapClaims); ok {
                        // Check audience
                        if aud, ok := claims["aud"].(string); !ok || aud != "go-service" {
                                http.Error(w, "Invalid audience", http.StatusUnauthorized)
                                return
                        }
                        // Check issuer
                        if iss, ok := claims["iss"].(string); !ok || iss != "fastapi" {
                                http.Error(w, "Invalid issuer", http.StatusUnauthorized)
                                return
                        }
                } else {
                        http.Error(w, "Invalid token claims", http.StatusUnauthorized)
                        return
                }

                next(w, r)
        }
}

// Calculate SHA-256 hash
func calculateSHA256(data []byte) string {
        hash := sha256.Sum256(data)
        return hex.EncodeToString(hash[:])
}

// Check idempotency
func checkIdempotency(ctx context.Context, keyHash, userID, endpoint, requestHash string) (*IdempotencyCheck, error) {
        var check IdempotencyCheck

        query := `
                SELECT key_hash, user_id, endpoint, request_hash, response_data, status_code, expires_at
                FROM idempotency_keys 
                WHERE key_hash = $1 AND expires_at > CURRENT_TIMESTAMP
        `

        row := dbPool.QueryRow(ctx, query, keyHash)
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

// Store idempotency key
func storeIdempotencyKey(ctx context.Context, keyHash, userID, endpoint, requestHash string, responseData interface{}, statusCode int) error {
        responseJSON, _ := json.Marshal(responseData)
        expiresAt := time.Now().Add(24 * time.Hour) // 24 hour expiration

        query := `
                INSERT INTO idempotency_keys (key_hash, user_id, endpoint, request_hash, response_data, status_code, expires_at)
                VALUES ($1, $2, $3, $4, $5, $6, $7)
                ON CONFLICT (key_hash) DO NOTHING
        `

        _, err := dbPool.Exec(ctx, query, keyHash, userID, endpoint, requestHash, responseJSON, statusCode, expiresAt)
        return err
}

// Evidence handling with hash verification
func handleEvidence(w http.ResponseWriter, r *http.Request) {
        if r.Method != http.MethodPost {
                http.Error(w, "Method not allowed", http.StatusMethodNotAllowed)
                return
        }

        // Parse multipart form
        err := r.ParseMultipartForm(10 << 20) // 10MB max
        if err != nil {
                http.Error(w, "Failed to parse form", http.StatusBadRequest)
                return
        }

        // Get file and hash
        file, fileHeader, err := r.FormFile("file")
        if err != nil {
                http.Error(w, "File required", http.StatusBadRequest)
                return
        }
        defer file.Close()

        providedHash := r.FormValue("sha256_hash")
        if providedHash == "" {
                http.Error(w, "SHA256 hash required", http.StatusBadRequest)
                return
        }

        sessionID := r.FormValue("session_id")
        if sessionID == "" {
                http.Error(w, "Session ID required", http.StatusBadRequest)
                return
        }

        evidenceType := r.FormValue("evidence_type")
        if evidenceType == "" {
                http.Error(w, "Evidence type required", http.StatusBadRequest)
                return
        }

        // Calculate actual hash
        hasher := sha256.New()
        if _, err := io.Copy(hasher, file); err != nil {
                http.Error(w, "Failed to read file", http.StatusInternalServerError)
                return
        }

        actualHash := hex.EncodeToString(hasher.Sum(nil))
        if actualHash != providedHash {
                log.Printf("Hash mismatch - provided: %s, actual: %s", providedHash, actualHash)
                http.Error(w, "Hash mismatch - file integrity check failed", http.StatusBadRequest)
                return
        }

        // Get idempotency key and user ID
        idempotencyKey := r.Header.Get("Idempotency-Key")
        if idempotencyKey == "" {
                http.Error(w, "Idempotency-Key header required", http.StatusBadRequest)
                return
        }

        userID := r.Header.Get("X-User-ID")
        if userID == "" {
                http.Error(w, "X-User-ID header required", http.StatusBadRequest)
                return
        }

        keyHash := calculateSHA256([]byte(idempotencyKey))
        requestHash := calculateSHA256([]byte(fmt.Sprintf("%s:%s:%s:%s", sessionID, evidenceType, providedHash, fileHeader.Filename)))

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

        // Store evidence metadata in database
        evidenceID := uuid.New().String()

        // Store basic metadata
        metadata := map[string]interface{}{
                "original_filename": fileHeader.Filename,
                "file_size":         fileHeader.Size,
                "uploaded_by":       userID,
                "content_type":      fileHeader.Header.Get("Content-Type"),
        }
        metadataJSON, _ := json.Marshal(metadata)

        query := `
                INSERT INTO evidence (id, session_id, evidence_type, file_path, metadata, checksum, created_at)
                VALUES ($1, $2, $3, $4, $5, $6, CURRENT_TIMESTAMP)
        `

        _, err = dbPool.Exec(ctx, query, evidenceID, sessionID, evidenceType,
                fmt.Sprintf("/evidence/%s", evidenceID), string(metadataJSON), actualHash)

        if err != nil {
                log.Printf("Database error storing evidence: %v", err)
                http.Error(w, "Database error", http.StatusInternalServerError)
                return
        }

        // Prepare response
        response := EvidenceResponse{
                EvidenceID: evidenceID,
                Hash:       actualHash,
                Status:     "verified",
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

// CRDT results processing with vector clocks
func handleCRDTResults(w http.ResponseWriter, r *http.Request) {
        if r.Method != http.MethodPost {
                http.Error(w, "Method not allowed", http.StatusMethodNotAllowed)
                return
        }

        vars := mux.Vars(r)
        sessionID := vars["session_id"]
        if sessionID == "" {
                http.Error(w, "session_id is required", http.StatusBadRequest)
                return
        }

        var payload CRDTPayload
        if err := json.NewDecoder(r.Body).Decode(&payload); err != nil {
                http.Error(w, "Invalid JSON payload", http.StatusBadRequest)
                return
        }

        // Validate required fields
        if payload.IdempotencyKey == "" {
                http.Error(w, "Idempotency key required", http.StatusBadRequest)
                return
        }

        if len(payload.Changes) == 0 {
                http.Error(w, "Changes required", http.StatusBadRequest)
                return
        }

        // Get user ID for idempotency
        userID := r.Header.Get("X-User-ID")
        if userID == "" {
                http.Error(w, "X-User-ID header required", http.StatusBadRequest)
                return
        }

        // Check idempotency
        keyHash := calculateSHA256([]byte(payload.IdempotencyKey))
        changesJSON, _ := json.Marshal(payload.Changes)
        requestHash := calculateSHA256(changesJSON)
        endpoint := fmt.Sprintf("/v1/tests/sessions/%s/results", sessionID)

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

        // Process CRDT changes with vector clock merging
        // 1. Retrieve current session data and vector clock
        var currentData map[string]interface{}
        var currentVectorClock map[string]int

        query := `
                SELECT session_data, vector_clock 
                FROM test_sessions 
                WHERE id = $1
        `

        var sessionDataJSON, vectorClockJSON string
        err = dbPool.QueryRow(ctx, query, sessionID).Scan(&sessionDataJSON, &vectorClockJSON)
        if err != nil && err != pgx.ErrNoRows {
                log.Printf("Failed to retrieve session data: %v", err)
                http.Error(w, "Database error", http.StatusInternalServerError)
                return
        }

        // Initialize or parse existing data
        if sessionDataJSON != "" {
                json.Unmarshal([]byte(sessionDataJSON), &currentData)
        } else {
                currentData = make(map[string]interface{})
        }

        if vectorClockJSON != "" {
                json.Unmarshal([]byte(vectorClockJSON), &currentVectorClock)
        } else {
                currentVectorClock = make(map[string]int)
        }

        // 2. Merge vector clocks (take maximum for each node)
        mergedVectorClock := make(map[string]int)
        for k, v := range currentVectorClock {
                mergedVectorClock[k] = v
        }
        for k, v := range payload.VectorClock {
                if existing, exists := mergedVectorClock[k]; !exists || v > existing {
                        mergedVectorClock[k] = v
                }
        }

        // 3. Apply changes to session data
        mergedData := currentData
        for _, change := range payload.Changes {
                // Simple merge strategy - in production, this would be more sophisticated
                for k, v := range change {
                        mergedData[k] = v
                }
        }

        // 4. Update session in database
        mergedDataJSON, _ := json.Marshal(mergedData)
        mergedVectorClockJSON, _ := json.Marshal(mergedVectorClock)

        updateQuery := `
                UPDATE test_sessions 
                SET session_data = $2, vector_clock = $3, updated_at = CURRENT_TIMESTAMP
                WHERE id = $1
        `

        _, err = dbPool.Exec(ctx, updateQuery, sessionID, string(mergedDataJSON), string(mergedVectorClockJSON))
        if err != nil {
                log.Printf("Failed to update session: %v", err)
                http.Error(w, "Database error", http.StatusInternalServerError)
                return
        }

        // Prepare response
        response := CRDTResponse{
                SessionID:   sessionID,
                Status:      "processed",
                VectorClock: mergedVectorClock,
                ProcessedAt: time.Now().UTC(),
        }

        // Store idempotency key
        if err := storeIdempotencyKey(ctx, keyHash, userID, endpoint, requestHash, response, http.StatusOK); err != nil {
                log.Printf("Failed to store idempotency key: %v", err)
        }

        w.Header().Set("Content-Type", "application/json")
        json.NewEncoder(w).Encode(response)
}

// Health check handler
func healthHandler(w http.ResponseWriter, r *http.Request) {
        w.Header().Set("Content-Type", "application/json")
        w.WriteHeader(http.StatusOK)
        json.NewEncoder(w).Encode(map[string]string{
                "status":  "ok",
                "service": "go-performance-service",
                "time":    time.Now().UTC().Format(time.RFC3339),
        })
}

// Memory stats handler for performance monitoring
func memoryStatsHandler(w http.ResponseWriter, r *http.Request) {
        var m runtime.MemStats
        runtime.ReadMemStats(&m)
        
        stats := map[string]interface{}{
                "alloc_mb":         bToMb(m.Alloc),
                "total_alloc_mb":   bToMb(m.TotalAlloc),
                "sys_mb":           bToMb(m.Sys),
                "num_gc":           m.NumGC,
                "gc_cpu_fraction":  m.GCCPUFraction,
                "heap_alloc_mb":    bToMb(m.HeapAlloc),
                "heap_sys_mb":      bToMb(m.HeapSys),
                "heap_idle_mb":     bToMb(m.HeapIdle),
                "heap_inuse_mb":    bToMb(m.HeapInuse),
                "num_goroutines":   runtime.NumGoroutine(),
                "timestamp":        time.Now().UTC().Format(time.RFC3339),
        }
        
        w.Header().Set("Content-Type", "application/json")
        json.NewEncoder(w).Encode(stats)
}

// Convert bytes to megabytes
func bToMb(b uint64) float64 {
        return float64(b) / 1024 / 1024
}

func main() {
        // Initialize database connection
        if err := initDB(); err != nil {
                log.Fatalf("Failed to initialize database: %v", err)
        }
        defer dbPool.Close()

        // Create router
        router := mux.NewRouter()

        // Health endpoint (no authentication required)
        router.HandleFunc("/health", healthHandler).Methods("GET")
        
        // Memory stats endpoint for performance monitoring
        router.HandleFunc("/memory", memoryStatsHandler).Methods("GET")

        // Protected endpoints with JWT middleware
        router.HandleFunc("/v1/evidence", validateInternalJWT(handleEvidence)).Methods("POST")
        router.HandleFunc("/v1/tests/sessions/{session_id}/results", validateInternalJWT(handleCRDTResults)).Methods("POST")

        // Start profiling server on port 6060
        go func() {
                log.Println("pprof profiling server starting on :6060")
                if err := http.ListenAndServe(":6060", nil); err != nil {
                        log.Printf("pprof server error: %v", err)
                }
        }()

        // Start main server
        port := ":9091"
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