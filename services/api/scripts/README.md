# Demo Data Seeding Scripts

This directory contains scripts for seeding the FireAI Compliance Platform with demo data.

## Files

- `seed_demo_data.py` - Main seeding script that creates realistic test data for three buildings with different compliance profiles
- `test_seed_structure.py` - Test script to verify the seeding script structure without requiring a real database

## Demo Data Overview

The seeding script creates three buildings with different compliance profiles:

### Building A - "Sydney Office Tower" (Perfect Compliance - Target Score 95%)
- 20 test sessions (spread over last 12 months, all passed)
- 50 evidence items (all with valid WORM hash + device attestation)
- 0 open defects
- All AS1851 tests up to date (no overdue)

### Building B - "Melbourne Retail Complex" (Good Compliance - Target Score 62%)
- 15 test sessions (3 overdue tests)
- 30 evidence items (2 missing device attestation)
- 3 medium defects (status: acknowledged, not repaired)
- Average MTTR: 10 days

### Building C - "Brisbane Warehouse" (Poor Compliance - Target Score 45%)
- 10 test sessions (5 overdue tests)
- 20 evidence items (5 missing attestation)
- 5 critical defects (status: open, not acknowledged)
- Average MTTR: 20 days

## Prerequisites

1. **Database Setup**: Ensure you have a PostgreSQL database running and accessible
2. **Environment Variables**: Set the `DATABASE_URL` environment variable
3. **Dependencies**: Install required Python packages

## Running the Seeding Script

### Method 1: Using Poetry (Recommended)

```bash
# From the project root
export DATABASE_URL="postgresql://username:password@localhost:5432/fireai_db"
cd services/api
poetry run python scripts/seed_demo_data.py
```

### Method 2: Using Python directly

```bash
# From the project root
export DATABASE_URL="postgresql://username:password@localhost:5432/fireai_db"
cd services/api
python scripts/seed_demo_data.py
```

### Method 3: Make executable

```bash
# From the project root
export DATABASE_URL="postgresql://username:password@localhost:5432/fireai_db"
cd services/api/scripts
chmod +x seed_demo_data.py
./seed_demo_data.py
```

## Environment Variables

Required environment variables:

- `DATABASE_URL`: PostgreSQL connection string
  - Format: `postgresql://username:password@host:port/database_name`
  - Example: `postgresql://fireai_user:secure_password@localhost:5432/fireai_db`

## Features

### Idempotent Design
The script is designed to be idempotent - it can be run multiple times without creating duplicates:
- Checks if demo buildings exist by name before creating
- Uses query-first-create pattern to avoid duplicates
- Safe to run repeatedly for testing and demos

### Realistic Data
- **Timestamps**: Test sessions spread over realistic time periods
- **Evidence**: Realistic filenames and metadata
- **Defects**: Realistic descriptions aligned with AS1851 standards
- **WORM Hashes**: Proper SHA-256 checksums for evidence integrity
- **Device Attestation**: Realistic device metadata for evidence

### Error Handling
- Comprehensive try/catch with database rollback on errors
- Clear error messages for debugging
- Graceful handling of missing dependencies

## Output

The script provides detailed output including:

```
🌱 Starting FireAI Demo Data Seeding...
✅ Created demo user: demo_user
✅ Created Building A: Sydney Office Tower
✅ Created 20 test sessions for Building A
✅ Created 50 evidence items for Building A
✅ Building A has 0 defects (perfect compliance)
✅ Created Building B: Melbourne Retail Complex
✅ Created 15 test sessions for Building B (3 overdue)
✅ Created 30 evidence items for Building B (2 missing attestation)
✅ Created 3 medium defects for Building B (acknowledged, not repaired)
✅ Created Building C: Brisbane Warehouse
✅ Created 10 test sessions for Building C (5 overdue)
✅ Created 20 evidence items for Building C (5 missing attestation)
✅ Created 5 critical defects for Building C (open, not acknowledged)

============================================================
🎉 DEMO DATA SEEDING COMPLETED SUCCESSFULLY!
============================================================
✅ Seeded 3 buildings:
   • Sydney Office Tower (ID: xxx) - Perfect Compliance (95%)
   • Melbourne Retail Complex (ID: xxx) - Good Compliance (62%)
   • Brisbane Warehouse (ID: xxx) - Poor Compliance (45%)
✅ Seeded 65 test sessions
✅ Seeded 100 evidence items
✅ Seeded 8 defects

🏢 Building IDs for reference:
   Building A (Perfect): xxx
   Building B (Good): xxx
   Building C (Poor): xxx
============================================================
```

## Troubleshooting

### Common Issues

1. **Import Errors**: Ensure all required dependencies are installed
2. **Database Connection**: Verify DATABASE_URL is correct and database is accessible
3. **Permission Errors**: Ensure the database user has CREATE/INSERT permissions
4. **Duplicate Key Errors**: The script should handle these gracefully due to idempotent design

### Testing Script Structure

Before running with a real database, you can test the script structure:

```bash
cd services/api/scripts
python test_seed_structure.py
```

This will verify imports and function structure without requiring a database connection.

## Development Notes

- The script uses synchronous SQLAlchemy for simplicity
- Models are imported from the main application
- All timestamps are in UTC
- UUIDs are generated for all primary keys
- Evidence includes realistic metadata for device attestation
- Defects follow AS1851 classification standards
