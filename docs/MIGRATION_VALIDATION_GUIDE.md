# Defects Table Migration Validation Guide

## Overview

This guide provides step-by-step instructions for validating the defects table migration for the FireAI platform.

## Migration Files

The following migrations have been created and fixed:

1. **[000_create_trigger_function.py](alembic/versions/000_create_trigger_function.py)**
   - Creates the `update_updated_at_column()` trigger function
   - Must be applied before other migrations that use this trigger
   - Revision: `000_create_trigger_function`
   - Revises: `phase2_final_indexes`

2. **[001_add_defects_table.py](alembic/versions/001_add_defects_table.py)**
   - Creates the defects table with complete schema
   - Includes all indexes, constraints, and triggers
   - Revision: `001_add_defects_table`
   - Revises: `000_create_trigger_function`

3. **[002_add_evidence_flag_columns.py](alembic/versions/002_add_evidence_flag_columns.py)**
   - Adds soft-delete flag columns to evidence table
   - Revision: `002_add_evidence_flag_columns`
   - Revises: `001_add_defects_table`

## Fixes Applied

### 1. Missing Trigger Function (CRITICAL)
**Issue:** Migration 001 referenced `update_updated_at_column()` function that didn't exist in migrations.

**Fix:** Created migration 000 to ensure the function exists before defects table is created.

### 2. ARRAY Column Defaults
**Issue:** Used Python-style string defaults `'{}'` for PostgreSQL ARRAY columns.

**Fix:** Changed to proper PostgreSQL syntax: `server_default=sa.text("'{}'::uuid[]")`

**Files:** [001_add_defects_table.py:54-59](alembic/versions/001_add_defects_table.py#L54-L59)

### 3. Missing server_default for status
**Issue:** Status column had `default='open'` but no `server_default`.

**Fix:** Added `server_default='open'` to ensure database-level default.

**Files:** [001_add_defects_table.py:42-44](alembic/versions/001_add_defects_table.py#L42-L44)

## Pre-Migration Checklist

Before running migrations, verify:

- [ ] PostgreSQL database is running and accessible
- [ ] Database user has CREATE privileges
- [ ] `uuid-ossp` extension is installed (for `uuid_generate_v4()`)
- [ ] Alembic is configured correctly (`alembic.ini`)
- [ ] Previous migrations (up to `phase2_final_indexes`) are applied

## Validation Steps

### Option 1: Automated Validation Script (Recommended)

Use the provided validation script:

```bash
# Set your database connection
export DATABASE_URL="postgresql://user:password@localhost:5432/fireai_db"

# Run validation
python3 validate_defects_migration.py
```

The script will:
- ✅ Check migration files exist
- ✅ Validate revision chain
- ✅ Check trigger function exists
- ✅ Validate table structure
- ✅ Check all columns present
- ✅ Verify indexes
- ✅ Validate CHECK constraints
- ✅ Verify foreign keys

### Option 2: Manual Validation

#### Step 1: Check Migration Chain

```bash
# View migration history
alembic history

# Should show:
# 002_add_evidence_flag_columns -> 001_add_defects_table -> 000_create_trigger_function -> phase2_final_indexes
```

#### Step 2: Apply Migrations

```bash
# Upgrade to latest
alembic upgrade head

# Check current revision
alembic current
```

#### Step 3: Validate Database Schema

Connect to your database and run:

```sql
-- Check table exists
SELECT EXISTS (
    SELECT FROM information_schema.tables
    WHERE table_name = 'defects'
);

-- List all columns
SELECT column_name, data_type, is_nullable, column_default
FROM information_schema.columns
WHERE table_name = 'defects'
ORDER BY ordinal_position;

-- Check indexes
SELECT indexname, indexdef
FROM pg_indexes
WHERE tablename = 'defects'
ORDER BY indexname;

-- Check constraints
SELECT conname, contype, pg_get_constraintdef(oid)
FROM pg_constraint
WHERE conrelid = 'defects'::regclass;

-- Check foreign keys
SELECT
    tc.constraint_name,
    tc.table_name AS source_table,
    kcu.column_name AS source_column,
    ccu.table_name AS target_table,
    ccu.column_name AS target_column,
    rc.delete_rule
FROM information_schema.table_constraints tc
JOIN information_schema.key_column_usage kcu
    ON tc.constraint_name = kcu.constraint_name
JOIN information_schema.constraint_column_usage ccu
    ON tc.constraint_name = ccu.constraint_name
JOIN information_schema.referential_constraints rc
    ON tc.constraint_name = rc.constraint_name
WHERE tc.table_name = 'defects'
  AND tc.constraint_type = 'FOREIGN KEY';

-- Check trigger exists
SELECT tgname, tgtype, tgenabled
FROM pg_trigger
WHERE tgrelid = 'defects'::regclass;
```

#### Step 4: Test Rollback

```bash
# Rollback one migration
alembic downgrade -1

# Verify defects table is removed
# (Connect to DB and check: \dt defects)

# Re-apply migration
alembic upgrade head

# Verify defects table is back
```

## Expected Schema Structure

### Columns (20 total)

| Column | Type | Nullable | Default | Description |
|--------|------|----------|---------|-------------|
| id | UUID | NO | uuid_generate_v4() | Primary key |
| test_session_id | UUID | NO | - | FK to test_sessions |
| building_id | UUID | NO | - | FK to buildings |
| asset_id | UUID | YES | - | Optional equipment ID |
| severity | VARCHAR(20) | NO | - | critical/high/medium/low |
| category | VARCHAR(50) | YES | - | Defect category |
| description | TEXT | NO | - | Defect description |
| as1851_rule_code | VARCHAR(20) | YES | - | AS1851 rule reference |
| status | VARCHAR(20) | NO | 'open' | Defect workflow status |
| discovered_at | TIMESTAMP | NO | now() | When discovered |
| acknowledged_at | TIMESTAMP | YES | - | When acknowledged |
| repaired_at | TIMESTAMP | YES | - | When repaired |
| verified_at | TIMESTAMP | YES | - | When verified |
| closed_at | TIMESTAMP | YES | - | When closed |
| evidence_ids | UUID[] | YES | '{}'::uuid[] | Evidence photo IDs |
| repair_evidence_ids | UUID[] | YES | '{}'::uuid[] | Repair photo IDs |
| created_at | TIMESTAMP | NO | now() | Record created |
| updated_at | TIMESTAMP | NO | now() | Record updated |
| created_by | UUID | YES | - | FK to users |
| acknowledged_by | UUID | YES | - | FK to users |

### Indexes (10 total)

| Index Name | Columns | Type |
|------------|---------|------|
| defects_pkey | id | PRIMARY KEY |
| idx_defects_test_session | test_session_id | BTREE |
| idx_defects_building | building_id | BTREE |
| idx_defects_status | status | BTREE |
| idx_defects_severity | severity | BTREE |
| idx_defects_created_by | created_by | BTREE |
| idx_defects_discovered_at | discovered_at | BTREE |
| idx_defects_building_status | building_id, status | BTREE (composite) |
| idx_defects_session_status | test_session_id, status | BTREE (composite) |

### Constraints

1. **CHECK Constraints:**
   - `chk_defects_severity`: Validates severity in ('critical', 'high', 'medium', 'low')
   - `chk_defects_status`: Validates status in ('open', 'acknowledged', 'repair_scheduled', 'repaired', 'verified', 'closed')

2. **Foreign Keys:**
   - `test_session_id` → `test_sessions(id)` ON DELETE CASCADE
   - `building_id` → `buildings(id)` ON DELETE CASCADE
   - `created_by` → `users(id)` ON DELETE SET NULL
   - `acknowledged_by` → `users(id)` ON DELETE SET NULL

### Triggers

- `update_defects_updated_at`: Automatically updates `updated_at` on row modification

## Integration Testing

### Test 1: Create Defect

```python
from app.models.defects import Defect
from app.database import SessionLocal
import uuid

db = SessionLocal()

# Create a defect
defect = Defect(
    test_session_id=uuid.UUID('...'),  # Use existing test session
    building_id=uuid.UUID('...'),       # Use existing building
    severity='high',
    status='open',
    description='Fire extinguisher pressure low',
    as1851_rule_code='FE-01',
    created_by=uuid.UUID('...')         # Use existing user
)

db.add(defect)
db.commit()
db.refresh(defect)

print(f"Created defect: {defect.id}")
print(f"Created at: {defect.created_at}")
print(f"Updated at: {defect.updated_at}")
```

### Test 2: Validate Constraints

```python
# Test invalid severity (should fail)
try:
    defect = Defect(
        test_session_id=uuid.UUID('...'),
        building_id=uuid.UUID('...'),
        severity='invalid',  # ❌ Not in CHECK constraint
        status='open',
        description='Test'
    )
    db.add(defect)
    db.commit()
    print("❌ FAIL: Should have rejected invalid severity")
except Exception as e:
    print(f"✅ PASS: Correctly rejected invalid severity: {e}")

# Test invalid status (should fail)
try:
    defect = Defect(
        test_session_id=uuid.UUID('...'),
        building_id=uuid.UUID('...'),
        severity='high',
        status='invalid_status',  # ❌ Not in CHECK constraint
        description='Test'
    )
    db.add(defect)
    db.commit()
    print("❌ FAIL: Should have rejected invalid status")
except Exception as e:
    print(f"✅ PASS: Correctly rejected invalid status: {e}")
```

### Test 3: Validate CASCADE Delete

```python
# Get a building with defects
building = db.query(Building).filter(Building.id == some_building_id).first()
defect_count = len(building.defects)

print(f"Building has {defect_count} defects")

# Delete building
db.delete(building)
db.commit()

# Verify defects were cascade deleted
remaining = db.query(Defect).filter(Defect.building_id == some_building_id).count()
if remaining == 0:
    print("✅ PASS: Defects were cascade deleted")
else:
    print(f"❌ FAIL: {remaining} defects still exist")
```

### Test 4: Validate updated_at Trigger

```python
import time

# Create defect
defect = Defect(...)
db.add(defect)
db.commit()
db.refresh(defect)

created_at = defect.created_at
updated_at = defect.updated_at

print(f"Initial timestamps:")
print(f"  created_at: {created_at}")
print(f"  updated_at: {updated_at}")

# Wait and update
time.sleep(1)
defect.status = 'acknowledged'
db.commit()
db.refresh(defect)

print(f"\nAfter update:")
print(f"  created_at: {defect.created_at}")  # Should be same
print(f"  updated_at: {defect.updated_at}")  # Should be newer

if defect.created_at == created_at:
    print("✅ PASS: created_at unchanged")
else:
    print("❌ FAIL: created_at was modified")

if defect.updated_at > updated_at:
    print("✅ PASS: updated_at was updated by trigger")
else:
    print("❌ FAIL: updated_at was not updated")
```

## Common Issues

### Issue 1: "function update_updated_at_column() does not exist"

**Cause:** Migration 000 was not applied before 001.

**Solution:**
```bash
# Check current version
alembic current

# If not on 000_create_trigger_function, run:
alembic upgrade 000_create_trigger_function
alembic upgrade head
```

### Issue 2: "malformed array literal"

**Cause:** Incorrect ARRAY default syntax.

**Solution:** Ensure migration uses `sa.text("'{}'::uuid[]")` not `'{}'` string.

### Issue 3: "relation 'defects' already exists"

**Cause:** Table was created manually or by previous migration attempt.

**Solution:**
```bash
# Rollback
alembic downgrade -1

# Or manually drop (⚠️ destroys data):
# DROP TABLE IF EXISTS defects CASCADE;

# Re-apply
alembic upgrade head
```

## Performance Validation

After migration, verify query performance:

```sql
-- Should use idx_defects_building_status
EXPLAIN ANALYZE
SELECT * FROM defects
WHERE building_id = 'some-uuid'
  AND status = 'open';

-- Should use idx_defects_session_status
EXPLAIN ANALYZE
SELECT * FROM defects
WHERE test_session_id = 'some-uuid'
  AND status IN ('open', 'acknowledged');

-- Should use idx_defects_discovered_at
EXPLAIN ANALYZE
SELECT * FROM defects
WHERE discovered_at > NOW() - INTERVAL '30 days'
ORDER BY discovered_at DESC;
```

All queries should show "Index Scan" in EXPLAIN output.

## Rollback Plan

If issues are discovered:

```bash
# Rollback all defects migrations
alembic downgrade phase2_final_indexes

# This will:
# 1. Remove evidence flag columns (002)
# 2. Drop defects table (001)
# 3. Drop trigger function (000)
```

## Sign-Off Checklist

Before considering migration validated:

- [ ] All migration files exist and are ordered correctly
- [ ] Migration chain is valid (000 → 001 → 002)
- [ ] Trigger function exists and is tested
- [ ] Defects table has all 20 columns
- [ ] All 10 indexes are present
- [ ] Both CHECK constraints work (severity, status)
- [ ] All 4 foreign keys exist with correct ON DELETE behavior
- [ ] updated_at trigger fires on row updates
- [ ] CASCADE delete works (building → defects)
- [ ] CRUD operations work via SQLAlchemy models
- [ ] Rollback and re-apply tested successfully

## Related Files

- [Defects Model](src/app/models/defects.py)
- [Defects Router](src/app/routers/defects.py)
- [Defects Schema](src/app/schemas/defect.py)
- [Migration 000](alembic/versions/000_create_trigger_function.py)
- [Migration 001](alembic/versions/001_add_defects_table.py)
- [Migration 002](alembic/versions/002_add_evidence_flag_columns.py)
- [Validation Script](validate_defects_migration.py)

## Support

If you encounter issues:

1. Check the [Common Issues](#common-issues) section
2. Run the automated validation script
3. Review Alembic logs: `alembic upgrade head --sql`
4. Check PostgreSQL logs for detailed errors
