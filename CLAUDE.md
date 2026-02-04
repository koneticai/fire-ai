# FireAI Project Guidelines

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
