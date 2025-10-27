# Defects Migration - Quick Start Guide

## TL;DR - Run This

```bash
# 1. Set your database URL
export DATABASE_URL="postgresql://user:password@localhost:5432/fireai_db"

# 2. Apply migrations
alembic upgrade head

# 3. Validate (optional but recommended)
python3 validate_defects_migration.py
```

## What Was Fixed

### Critical Issues
- ✅ **Missing trigger function** - Created migration 000 to add `update_updated_at_column()`
- ✅ **Wrong ARRAY defaults** - Changed from `'{}'` to `'{}'::uuid[]`
- ✅ **Missing server_default** - Added `server_default='open'` for status column

### Files Modified
- [000_create_trigger_function.py](alembic/versions/000_create_trigger_function.py) - **NEW**
- [001_add_defects_table.py](alembic/versions/001_add_defects_table.py) - **FIXED**
- [002_add_evidence_flag_columns.py](alembic/versions/002_add_evidence_flag_columns.py) - Unchanged

## Migration Order

```
phase2_final_indexes (existing)
    ↓
000_create_trigger_function (NEW)
    ↓
001_add_defects_table (FIXED)
    ↓
002_add_evidence_flag_columns (existing)
```

## Quick Validation

### Check Migration Status
```bash
alembic current
# Should show: 002_add_evidence_flag_columns
```

### Verify Table Exists
```sql
\dt defects
```

### Check Column Count
```sql
SELECT COUNT(*) FROM information_schema.columns WHERE table_name = 'defects';
-- Should return: 20
```

### Verify Indexes
```sql
SELECT COUNT(*) FROM pg_indexes WHERE tablename = 'defects';
-- Should return: 9 (plus 1 primary key = 10 total)
```

## Test in Python

```python
from app.models.defects import Defect
from app.database import SessionLocal
import uuid

db = SessionLocal()

# Quick test
defect = Defect(
    test_session_id=uuid.UUID('YOUR-TEST-SESSION-ID'),
    building_id=uuid.UUID('YOUR-BUILDING-ID'),
    severity='high',
    status='open',
    description='Test defect'
)
db.add(defect)
db.commit()
print(f"✅ Created defect {defect.id}")
```

## Rollback If Needed

```bash
# Rollback all defects migrations
alembic downgrade phase2_final_indexes

# Re-apply
alembic upgrade head
```

## Full Documentation

See [MIGRATION_VALIDATION_GUIDE.md](MIGRATION_VALIDATION_GUIDE.md) for:
- Complete validation steps
- Integration testing examples
- Troubleshooting guide
- Performance validation queries

## Quick Reference

**Defects Table:** 20 columns, 10 indexes, 2 CHECK constraints, 4 foreign keys

**Supported Severities:** `critical`, `high`, `medium`, `low`

**Supported Statuses:** `open`, `acknowledged`, `repair_scheduled`, `repaired`, `verified`, `closed`

**Validation Script:** `python3 validate_defects_migration.py`
