# architecture.md

- Topology: FastAPI (API), SQLAlchemy (ORM), Alembic (migrations), PostgreSQL (DB), background jobs (if any)
- Data Contracts: See **./data_model.md** (Single Source of Truth)
- Security: JWT (short-lived + revocation), Fernet for sensitive fields, Argon2 for passwords
- Observability: logs/metrics/traces; error sampling
- Decisions & tradeoffs: keep bullets short with dates/owners
