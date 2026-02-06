# FireAI Project Guidelines

## Cowork vs Claude Code

**Cowork mode is sandboxed** - no network access to external services:
- ❌ Cannot connect to Supabase/PostgreSQL
- ❌ Cannot push to GitHub
- ❌ Cannot access external APIs

**Use Claude Code for:**
- Git operations (push, PR creation)
- Database seeding/migrations
- API testing against external services
- Any task requiring network access

**Use Cowork for:**
- File creation and editing
- Code generation
- Local validation scripts
- Documentation

**Workflow:** Prepare files in Cowork → Execute network operations in Claude Code

---

## Database Connection (Supabase)

**Always use the Transaction Pooler connection**, not Direct Connection.

- **Transaction Pooler** (port 6543): Works with IPv4, no special network requirements
- **Direct Connection**: Requires IPv6 or paid IPv4 add-on - will fail with DNS resolution errors

### Connection String Format
```
postgresql://postgres.[PROJECT-REF]:[PASSWORD]@aws-[N]-[REGION].pooler.supabase.com:6543/postgres
```

### This Project's Config
- Region: `ap-south-1`
- Pooler host: `aws-1-ap-south-1.pooler.supabase.com`
- Port: `6543` (transaction mode)

### Common Errors
| Error | Cause | Fix |
|-------|-------|-----|
| `could not translate host name` | Using direct connection without IPv6 | Use pooler connection |
| `Tenant or user not found` | Wrong region in pooler URL | Check project region in Supabase dashboard |
| `password authentication failed` | Missing special chars in password | URL-encode special chars (`@` = `%40`, `*` = `%2A`) |

### Password URL Encoding
Special characters in passwords must be URL-encoded in connection strings:
- `@` → `%40`
- `*` → `%2A`
- `#` → `%23`
- `!` → `%21`

---

## Context Files

**Read these before starting work to avoid expensive re-analysis:**

| Context | Location | When to Read |
|---------|----------|--------------|
| Backend Context | `.claude/context/BACKEND-CONTEXT.md` | Before any backend work |
| Full Repo Context | `.claude/context/REPO-CONTEXT.md` | For comprehensive codebase overview |
| Validation Plan | `plans/validation-backend-90-percent-complete.md` | Before running/writing tests |

**Future prompts start with:**
```
Read .claude/context/BACKEND-CONTEXT.md for repo context.
[Then your actual task]
```
