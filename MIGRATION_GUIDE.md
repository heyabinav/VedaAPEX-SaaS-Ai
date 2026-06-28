<!-- Database Schema Migration Guide -->
# Database Migration Guide

## Automatic Migration (Recommended for Development)

The repository uses SQLModel with automatic table creation via `create_all()`. When the app starts, it automatically:

1. Imports all model modules from `app/models/`
2. Registers them in SQLModel.metadata
3. Runs `SQLModel.metadata.create_all(engine)` to ensure all tables exist

**On app startup**, new tables are automatically created. No manual migration needed for development!

```bash
# Just start the app — tables will auto-create
uvicorn app.main:app --reload
```

---

## Schema Changes Summary

### 1. User Table (app/models/user.py)

**New Fields Added:**
```sql
ALTER TABLE "user" ADD COLUMN provider VARCHAR;
ALTER TABLE "user" ADD COLUMN provider_id VARCHAR;
CREATE INDEX ix_user_provider ON "user" (provider);
CREATE INDEX ix_user_provider_id ON "user" (provider_id);
```

- `provider`: OAuth provider name (e.g., "google", "github")
- `provider_id`: Provider's unique user ID
- Used for OAuth login flow and linking provider accounts to local users

### 2. New APIKey Table (app/models/api_key.py)

```sql
CREATE TABLE api_key (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  user_id INTEGER NOT NULL REFERENCES "user"(id),
  name TEXT,
  prefix TEXT NOT NULL UNIQUE,
  key_hash TEXT NOT NULL,
  scopes TEXT,
  revoked BOOLEAN DEFAULT 0,
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  last_used_at TIMESTAMP
);

CREATE INDEX ix_api_key_prefix ON api_key(prefix);
CREATE INDEX ix_api_key_user_id ON api_key(user_id);
CREATE INDEX ix_api_key_revoked ON api_key(revoked);
```

**Purpose:**
- Store hashed API keys (raw secret never stored)
- Track key creation, last usage, revocation status
- Support multiple keys per user with different scopes

### 3. New APIUsage Table (app/models/api_key.py)

```sql
CREATE TABLE api_usage (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  user_id INTEGER NOT NULL REFERENCES "user"(id),
  api_key_prefix TEXT NOT NULL,
  endpoint TEXT NOT NULL,
  method TEXT NOT NULL,
  status_code INTEGER NOT NULL,
  response_time_ms INTEGER,
  tokens_used INTEGER DEFAULT 0,
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX ix_api_usage_user_id ON api_usage(user_id);
CREATE INDEX ix_api_usage_prefix ON api_usage(api_key_prefix);
CREATE INDEX ix_api_usage_endpoint ON api_usage(endpoint);
CREATE INDEX ix_api_usage_created_at ON api_usage(created_at);
```

**Purpose:**
- Track API calls per key for rate limiting
- Monitor performance and billing
- Analytics and usage reporting

---

## Migration for Production (Using Alembic)

If you want to set up Alembic for version-controlled migrations:

### Setup Alembic

```bash
pip install alembic
alembic init alembic
```

### Create Migration

```bash
alembic revision --autogenerate -m "Add OAuth provider fields and APIKey tables"
```

### Review and Run

```bash
# Check the generated migration file in alembic/versions/
cat alembic/versions/*.py

# Run the migration
alembic upgrade head
```

### Manual Migration SQL

If you prefer manual migration without Alembic:

#### For SQLite

```bash
sqlite3 vedaapex.db << 'EOF'
-- Add OAuth fields to user table
ALTER TABLE "user" ADD COLUMN provider VARCHAR;
ALTER TABLE "user" ADD COLUMN provider_id VARCHAR;
CREATE INDEX ix_user_provider ON "user" (provider);
CREATE INDEX ix_user_provider_id ON "user" (provider_id);

-- Create APIKey table
CREATE TABLE api_key (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  user_id INTEGER NOT NULL REFERENCES "user"(id),
  name TEXT,
  prefix TEXT NOT NULL UNIQUE,
  key_hash TEXT NOT NULL,
  scopes TEXT,
  revoked BOOLEAN DEFAULT 0,
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  last_used_at TIMESTAMP
);
CREATE INDEX ix_api_key_prefix ON api_key(prefix);
CREATE INDEX ix_api_key_user_id ON api_key(user_id);
CREATE INDEX ix_api_key_revoked ON api_key(revoked);

-- Create APIUsage table
CREATE TABLE api_usage (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  user_id INTEGER NOT NULL REFERENCES "user"(id),
  api_key_prefix TEXT NOT NULL,
  endpoint TEXT NOT NULL,
  method TEXT NOT NULL,
  status_code INTEGER NOT NULL,
  response_time_ms INTEGER,
  tokens_used INTEGER DEFAULT 0,
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX ix_api_usage_user_id ON api_usage(user_id);
CREATE INDEX ix_api_usage_prefix ON api_usage(api_key_prefix);
CREATE INDEX ix_api_usage_endpoint ON api_usage(endpoint);
CREATE INDEX ix_api_usage_created_at ON api_usage(created_at);
EOF
```

#### For PostgreSQL

```bash
psql $DATABASE_URL << 'EOF'
-- Add OAuth fields to user table
ALTER TABLE "user" ADD COLUMN IF NOT EXISTS provider VARCHAR;
ALTER TABLE "user" ADD COLUMN IF NOT EXISTS provider_id VARCHAR;
CREATE INDEX IF NOT EXISTS ix_user_provider ON "user" (provider);
CREATE INDEX IF NOT EXISTS ix_user_provider_id ON "user" (provider_id);

-- Create APIKey table
CREATE TABLE IF NOT EXISTS api_key (
  id SERIAL PRIMARY KEY,
  user_id INTEGER NOT NULL REFERENCES "user"(id) ON DELETE CASCADE,
  name TEXT,
  prefix TEXT NOT NULL UNIQUE,
  key_hash TEXT NOT NULL,
  scopes TEXT,
  revoked BOOLEAN DEFAULT false,
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  last_used_at TIMESTAMP
);
CREATE INDEX IF NOT EXISTS ix_api_key_prefix ON api_key(prefix);
CREATE INDEX IF NOT EXISTS ix_api_key_user_id ON api_key(user_id);
CREATE INDEX IF NOT EXISTS ix_api_key_revoked ON api_key(revoked);

-- Create APIUsage table
CREATE TABLE IF NOT EXISTS api_usage (
  id SERIAL PRIMARY KEY,
  user_id INTEGER NOT NULL REFERENCES "user"(id) ON DELETE CASCADE,
  api_key_prefix TEXT NOT NULL,
  endpoint TEXT NOT NULL,
  method TEXT NOT NULL,
  status_code INTEGER NOT NULL,
  response_time_ms INTEGER,
  tokens_used INTEGER DEFAULT 0,
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX IF NOT EXISTS ix_api_usage_user_id ON api_usage(user_id);
CREATE INDEX IF NOT EXISTS ix_api_usage_prefix ON api_usage(api_key_prefix);
CREATE INDEX IF NOT EXISTS ix_api_usage_endpoint ON api_usage(endpoint);
CREATE INDEX IF NOT EXISTS ix_api_usage_created_at ON api_usage(created_at);
EOF
```

---

## Verification

After migration, verify tables exist:

### SQLite

```bash
sqlite3 vedaapex.db ".schema api_key"
sqlite3 vedaapex.db ".schema api_usage"
sqlite3 vedaapex.db "PRAGMA table_info(user);"
```

### PostgreSQL

```bash
psql $DATABASE_URL -c "\dt api_key"
psql $DATABASE_URL -c "\dt api_usage"
psql $DATABASE_URL -c "\d user"
```

---

## Deployment Checklist

- [ ] Run migrations on staging database first
- [ ] Backup production database before migrating
- [ ] Test OAuth login flow after `provider`/`provider_id` fields added
- [ ] Test API key generation/validation
- [ ] Verify indexes are created (performance)
- [ ] Monitor database for any constraint violations
- [ ] Run on production database with `alembic upgrade head` or manual SQL

---

## References

- **Models:** [app/models/api_key.py](../models/api_key.py)
- **Session:** [app/db/session.py](../db/session.py)
- **User Model:** [app/models/user.py](../models/user.py)
