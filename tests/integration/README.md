# Integration Tests

This directory contains comprehensive end-to-end integration tests for the FireMode Compliance Platform.

## Defects E2E Test

The `test_defects_e2e.py` file contains a comprehensive end-to-end integration test that validates the complete defects workflow from test session creation through evidence upload, defect creation, linking, status updates, and evidence flagging.

### Test Flow

The test validates the following complete workflow:

1. **Create test session (inspection)** - Creates a new test session for a building
2. **Upload evidence (photo)** - Uploads evidence with metadata to the session
3. **Create defect (link to session)** - Creates a defect associated with the test session
4. **Link evidence to defect** - Links the uploaded evidence to the defect
5. **Get defect with linked evidence** - Retrieves the defect and verifies evidence linkage
6. **Update defect status (acknowledge)** - Updates the defect status through the workflow
7. **Get building's defects (verify it appears)** - Retrieves all defects for the building
8. **Flag evidence for review** - Flags the evidence for administrative review

### Test Features

- **Real Database Testing**: Uses in-memory SQLite database for true integration testing
- **Complete Workflow Validation**: Tests the entire defects workflow end-to-end
- **Error Scenario Testing**: Validates proper error handling for invalid inputs
- **Performance Testing**: Ensures the workflow meets performance benchmarks
- **Proper Test Isolation**: Each test runs with clean database state
- **Comprehensive Assertions**: Validates data integrity at each step

### Running the Tests

#### Option 1: Using the Test Runner Script

```bash
# Run all E2E tests
python run_e2e_tests.py

# Run with verbose output
python run_e2e_tests.py --verbose

# Run only performance tests
python run_e2e_tests.py --performance-only

# Run only error scenario tests
python run_e2e_tests.py --error-only
```

#### Option 2: Using pytest directly

```bash
# Run all integration tests
pytest tests/integration/ -v

# Run specific test file
pytest tests/integration/test_defects_e2e.py -v

# Run specific test method
pytest tests/integration/test_defects_e2e.py::TestDefectsE2E::test_complete_defects_workflow -v
```

#### Option 3: Using poetry

```bash
# Run with poetry
poetry run pytest tests/integration/ -v
```

### Test Structure

The test file contains three main test classes:

1. **`test_complete_defects_workflow`** - Tests the happy path through the entire workflow
2. **`test_defects_workflow_error_scenarios`** - Tests error handling and validation
3. **`test_defects_workflow_performance`** - Tests performance benchmarks

### Test Database

The tests use an in-memory SQLite database that is created fresh for each test session. This provides:

- **True Integration Testing**: Tests against a real database with actual SQL queries
- **Fast Execution**: In-memory database provides quick test runs
- **Clean State**: Each test starts with a fresh database
- **No External Dependencies**: No need for external database setup

### Performance Benchmarks

The performance test validates that the defects workflow meets the following benchmarks:

- **Defect Creation**: < 5.0 seconds for 5 defects
- **Defect Listing**: < 1.0 second for paginated results
- **Defect Filtering**: < 1.0 second for filtered queries
- **Building Defects**: < 1.0 second for building-specific queries

### Mocked Components

The test mocks the following components to focus on the API workflow:

- **Go Service Proxy**: Mocks the Go service for evidence submission
- **S3 Operations**: Mocks S3 operations for file storage
- **Authentication**: Uses test user tokens for API calls

### Expected Output

When all tests pass, you should see output similar to:

```
🎉 Complete defects workflow test PASSED!
All 8 steps completed successfully:
1. ✓ Test session created
2. ✓ Evidence uploaded
3. ✓ Defect created
4. ✓ Evidence linked to defect
5. ✓ Defect retrieved with evidence
6. ✓ Defect status updated
7. ✓ Building defects retrieved
8. ✓ Evidence flagged for review

🎉 Error scenario tests PASSED!
All error scenarios properly handled:
1. ✓ Invalid test session rejected
2. ✓ Invalid severity rejected
3. ✓ Invalid status transition rejected
4. ✓ Unauthorized access rejected

🎉 Performance tests PASSED!
All performance benchmarks met:
1. ✓ Defect creation: 2.34s (< 5.0s)
2. ✓ Defect listing: 0.156s (< 1.0s)
3. ✓ Defect filtering: 0.089s (< 1.0s)
4. ✓ Building defects: 0.067s (< 1.0s)
```

### Troubleshooting

If tests fail, check:

1. **Database Connection**: Ensure SQLite is available
2. **Dependencies**: Run `poetry install` to ensure all dependencies are installed
3. **Environment Variables**: Check that test environment variables are set
4. **File Permissions**: Ensure the test runner script is executable

### Adding New Integration Tests

To add new integration tests:

1. Create a new test file in this directory
2. Follow the same pattern of using in-memory database
3. Use the same dependency override pattern for authentication
4. Include comprehensive assertions and error handling
5. Add performance benchmarks where appropriate

### Integration with CI/CD

These tests are designed to run in CI/CD pipelines:

- **No External Dependencies**: Uses in-memory database
- **Fast Execution**: Complete test suite runs in under 30 seconds
- **Clear Output**: Provides detailed success/failure information
- **Exit Codes**: Proper exit codes for CI/CD integration
