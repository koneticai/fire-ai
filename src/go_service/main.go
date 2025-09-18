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
	"time"

	"github.com/gorilla/mux"
	"github.com/jackc/pgx/v5"
)

// EvidenceRequest represents the structure for evidence submission
type EvidenceRequest struct {
	SessionID    string                 `json:"session_id"`
	EvidenceType string                 `json:"evidence_type"`
	FilePath     string                 `json:"file_path,omitempty"`
	Metadata     map[string]interface{} `json:"metadata,omitempty"`
	Data         string                 `json:"data,omitempty"`
}

// TestResultRequest represents the structure for test results submission
type TestResultRequest struct {
	SessionID string                 `json:"session_id"`
	Results   map[string]interface{} `json:"results"`
	Timestamp time.Time              `json:"timestamp"`
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

	// Add routes
	router.HandleFunc("/v1/evidence", evidenceHandler).Methods("POST")
	router.HandleFunc("/v1/tests/sessions/{session_id}/results", testResultsHandler).Methods("POST")
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