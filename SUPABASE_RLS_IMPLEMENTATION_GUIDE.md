# VedaApex Supabase RLS Implementation Guide

## Overview

This guide walks you through enabling Row Level Security (RLS) on 6 critical tables in your VedaApex Supabase project (`bjulbxkvpsbgwwwcenrt`). The policies are designed to:

1. **Protect user data** - Each user can only access their own chat sessions, chat messages, and search history
2. **Secure internal tables** - Restrict admin tables (error_log, system_metrics) to service_role only
3. **Maintain backward compatibility** - Existing authenticated users can still read/write their own data
4. **Leverage Supabase Auth** - Uses auth.uid() to determine data ownership

---

## Current Situation

### Tables to Secure

| Table | Type | Current RLS | User ID Column | Purpose |
|-------|------|-----------|----------------|---------|
| **chat_session** | User-owned | DISABLED | `user_id` (int) | Chat conversations |
| **chat_message** | User-owned | DISABLED | `user_id` + `session_id` | Individual messages |
| **search_history** | User-owned | DISABLED | `user_id` (int) | Search queries |
| **search_history_result** | User-owned | DISABLED | `history_id` (FK) | Search results |
| **error_log** | Internal | DISABLED | `user_id` (optional) | Error tracking |
| **system_metrics** | Internal | DISABLED | None | Performance metrics |

### Key Architecture Detail

- Your `user` table has an INTEGER primary key (`id`), not the Supabase auth UUID
- Supabase auth UUIDs are stored in `user.provider_id` column
- The RLS policies map `auth.uid()` → `user.provider_id` → `user.id` for access control

---

## How to Apply the Policies

### Option 1: Using Supabase CLI (Recommended)

If you have the Supabase CLI installed:

```bash
# 1. Login to your Supabase account
supabase login

# 2. Link your local project to your remote Supabase project
supabase link --project-ref bjulbxkvpsbgwwwcenrt

# 3. Create a migration with the RLS policies
supabase migration new enable_rls_policies

# 4. Copy the contents of supabase_rls_policies.sql into the migration file
# (Location: supabase/migrations/[TIMESTAMP]_enable_rls_policies.sql)

# 5. Push the migration to your remote project
supabase db push
```

### Option 2: Using Supabase Dashboard (Web Console)

1. **Go to Supabase Dashboard**
   - Open https://app.supabase.com
   - Select project: VedaApex (bjulbxkvpsbgwwwcenrt)

2. **Navigate to SQL Editor**
   - Click "SQL Editor" in the left sidebar
   - Click "+ New Query"

3. **Paste and Execute**
   - Copy the entire contents of `supabase_rls_policies.sql`
   - Paste into the SQL editor
   - Click "Run" (or Ctrl+Enter)

4. **Verify Execution**
   - Check that all queries completed without errors
   - You should see output like:
     ```
     ALTER TABLE
     CREATE POLICY
     (repeated for each policy)
     ```

### Option 3: Using Supabase Python Client

```python
import supabase
from os import environ

client = supabase.create_client(
    supabase_url=environ["SUPABASE_URL"],
    supabase_key=environ["SUPABASE_SERVICE_ROLE_KEY"]
)

# Read the SQL file
with open("supabase_rls_policies.sql", "r") as f:
    sql = f.read()

# Execute using Postgres connection
# Note: Requires direct access to PostgreSQL connection
# This is typically done via dashboard or CLI
```

---

## Schema Details for Reference

### chat_session Table
```sql
CREATE TABLE chat_session (
    id TEXT PRIMARY KEY,
    user_id INTEGER REFERENCES "user"(id),
    title TEXT,
    created_at TIMESTAMP,
    updated_at TIMESTAMP,
    last_message_at TIMESTAMP NULL
);
```
**RLS Policies Applied:**
- SELECT: `user_id IN (SELECT id FROM user WHERE provider_id = auth.uid())`
- INSERT: Same check with WITH CHECK
- UPDATE: Prevent changing user_id
- DELETE: Only by owner

---

### chat_message Table
```sql
CREATE TABLE chat_message (
    id TEXT PRIMARY KEY,
    session_id TEXT REFERENCES chat_session(id),
    user_id INTEGER REFERENCES "user"(id),
    role TEXT,
    content TEXT,
    created_at TIMESTAMP,
    metadata_json TEXT,
    tokens_used INTEGER NULL
);
```
**RLS Policies Applied:**
- SELECT: Messages from sessions owned by current user
- INSERT: Only into own sessions, with own user_id
- UPDATE: Only own messages in own sessions
- DELETE: Only own messages in own sessions

---

### search_history Table
```sql
CREATE TABLE search_history (
    id INTEGER PRIMARY KEY AUTO_INCREMENT,
    user_id INTEGER REFERENCES "user"(id),
    title TEXT,
    query TEXT,
    source TEXT NULL,
    notes TEXT NULL,
    created_at TIMESTAMP
);
```
**RLS Policies Applied:**
- SELECT: Own search history only
- INSERT: With own user_id only
- UPDATE: Own records only
- DELETE: Own records only

---

### search_history_result Table
```sql
CREATE TABLE search_history_result (
    id INTEGER PRIMARY KEY AUTO_INCREMENT,
    history_id INTEGER REFERENCES search_history(id),
    result_count INTEGER,
    results_json TEXT,
    created_at TIMESTAMP
);
```
**RLS Policies Applied:**
- SELECT: Results for own search history only
- INSERT: Results for own search history only
- UPDATE: Results for own search history only
- DELETE: Results for own search history only

---

### error_log Table (Admin Only)
```sql
CREATE TABLE error_log (
    id INTEGER PRIMARY KEY AUTO_INCREMENT,
    request_id TEXT NULL,
    user_id INTEGER NULL REFERENCES "user"(id),
    error_code TEXT,
    error_type TEXT,
    message TEXT,
    detail TEXT NULL,
    endpoint TEXT NULL,
    method TEXT NULL,
    ip_address TEXT NULL,
    user_agent TEXT NULL,
    stack_trace TEXT NULL,
    status_code INTEGER,
    created_at TIMESTAMP
);
```
**RLS Policies Applied:**
- ALL operations return FALSE for authenticated/anon users
- Service role bypasses RLS and can still read/write
- This is for logging only; users should never access directly

---

### system_metrics Table (Admin Only)
```sql
CREATE TABLE system_metrics (
    id INTEGER PRIMARY KEY AUTO_INCREMENT,
    metric_name TEXT,
    metric_value FLOAT,
    metric_unit TEXT NULL,
    tags TEXT NULL,
    recorded_at TIMESTAMP
);
```
**RLS Policies Applied:**
- ALL operations return FALSE for authenticated/anon users
- Service role bypasses RLS and can still read/write
- For internal monitoring only

---

## Verification Steps

### Step 1: Check RLS is Enabled

Open Supabase SQL Editor and run:

```sql
SELECT
    schemaname,
    tablename,
    rowsecurity AS "RLS Enabled"
FROM pg_tables
WHERE tablename IN ('chat_session', 'chat_message', 'search_history', 'search_history_result', 'error_log', 'system_metrics')
AND schemaname = 'public'
ORDER BY tablename;
```

**Expected Output:**
```
schemaname │ tablename               │ RLS Enabled
────────────┼─────────────────────────┼─────────────
public      │ chat_message            │ t
public      │ chat_session            │ t
public      │ error_log               │ t
public      │ search_history          │ t
public      │ search_history_result   │ t
public      │ system_metrics          │ t
```

All should show `t` (true).

### Step 2: Check Policies Are Created

Run this query to see all policies:

```sql
SELECT
    schemaname,
    tablename,
    policyname,
    permissive,
    roles,
    qual AS "USING clause",
    with_check AS "WITH CHECK clause"
FROM pg_policies
WHERE tablename IN ('chat_session', 'chat_message', 'search_history', 'search_history_result', 'error_log', 'system_metrics')
AND schemaname = 'public'
ORDER BY tablename, policyname;
```

**Expected Policies:**

**chat_session** (4 policies):
- `chat_session_select_own`
- `chat_session_insert_own`
- `chat_session_update_own`
- `chat_session_delete_own`

**chat_message** (4 policies):
- `chat_message_select_own`
- `chat_message_insert_own`
- `chat_message_update_own`
- `chat_message_delete_own`

**search_history** (4 policies):
- `search_history_select_own`
- `search_history_insert_own`
- `search_history_update_own`
- `search_history_delete_own`

**search_history_result** (4 policies):
- `search_history_result_select_own`
- `search_history_result_insert_own`
- `search_history_result_update_own`
- `search_history_result_delete_own`

**error_log** (4 policies):
- `error_log_deny_all`
- `error_log_deny_all_insert`
- `error_log_deny_all_update`
- `error_log_deny_all_delete`

**system_metrics** (4 policies):
- `system_metrics_deny_all`
- `system_metrics_deny_all_insert`
- `system_metrics_deny_all_update`
- `system_metrics_deny_all_delete`

---

## Testing the Policies

### Test Setup

1. **Create 2 test users in Supabase Auth:**
   - User A: `user.a@vedaapex.test` (gets auth.uid() = `<UUID-A>`)
   - User B: `user.b@vedaapex.test` (gets auth.uid() = `<UUID-B>`)

2. **Create local user records (run as service role):**
   ```sql
   INSERT INTO "user" (email, full_name, hashed_password, role, referral_code, provider_id)
   VALUES 
       ('user.a@vedaapex.test', 'User A', '...', 'USER', 'ref_a', '<UUID-A>'),
       ('user.b@vedaapex.test', 'User B', '...', 'USER', 'ref_b', '<UUID-B>');
   ```

### Test 1: User A Creates and Owns a Chat

**As User A (authenticated with UUID-A):**

```python
# Create a chat session
chat_response = supabase.table('chat_session').insert({
    'id': 'chat_1',
    'user_id': 1,  # User A's local id
    'title': 'My Chat'
}).execute()

# User A can read their own chat
chat = supabase.table('chat_session').select('*').eq('id', 'chat_1').execute()
print(chat.data)  # Should return 1 row
```

### Test 2: User B Cannot Access User A's Chat

**As User B (authenticated with UUID-B):**

```python
# Try to read User A's chat (should return 0 rows due to RLS)
chat = supabase.table('chat_session').select('*').eq('id', 'chat_1').execute()
print(chat.data)  # Should return 0 rows (RLS blocks it)

# Try to delete User A's chat (should fail)
try:
    supabase.table('chat_session').delete().eq('id', 'chat_1').execute()
except Exception as e:
    print(e)  # Should show permission denied or 0 rows affected
```

### Test 3: Error Log is Inaccessible to Authenticated Users

**As Any Authenticated User:**

```python
# Try to read error_log (should return 0 rows)
logs = supabase.table('error_log').select('*').execute()
print(logs.data)  # Should return empty array
```

### Test 4: Service Role Can Still Access All Tables

**Using service_role key:**

```python
import supabase
from os import environ

# Use service role key (bypasses RLS)
service_client = supabase.create_client(
    supabase_url=environ["SUPABASE_URL"],
    supabase_key=environ["SUPABASE_SERVICE_ROLE_KEY"]  # Service role key
)

# Service role can read error_log and system_metrics
logs = service_client.table('error_log').select('*').execute()
print(logs.data)  # Should return rows (RLS bypassed)
```

---

## Troubleshooting

### Issue: "PERMISSION DENIED" Errors

**Symptom:** Users get permission denied errors when trying to access their own data

**Cause:** 
- RLS policies may be denying access incorrectly
- User's `provider_id` doesn't match their Supabase auth.uid()
- User doesn't exist in the `user` table

**Fix:**
1. Verify user's auth.uid() matches their `provider_id` in the `user` table:
   ```sql
   SELECT id, email, provider_id FROM "user" WHERE email = 'user.email@example.com';
   ```

2. Verify the provider_id is a valid UUID (should be 36 chars or 32 hex chars)

3. Check that the user is authenticated properly:
   ```python
   user = supabase.auth.get_user(access_token)
   print(user.id)  # Should be a UUID
   ```

### Issue: Queries Suddenly Return 0 Rows

**Symptom:** After enabling RLS, queries return empty results

**Cause:** 
- RLS policies are correctly filtering data
- User's auth.uid() doesn't match their user.provider_id
- The JOIN through the `user` table is failing

**Fix:**
1. Verify the user exists and has the correct provider_id:
   ```python
   # Get current user's auth.uid()
   current_user = supabase.auth.get_user(access_token)
   print(current_user.id)
   
   # Check if this matches a user in the user table
   result = supabase.table('user').select('*').eq('provider_id', current_user.id).execute()
   print(result.data)  # Should return 1 row
   ```

### Issue: Service Role Cannot Access Admin Tables

**Symptom:** Service role queries to error_log or system_metrics fail

**Cause:** 
- This shouldn't happen; service role bypasses RLS
- May be a firewall or permission issue

**Fix:**
1. Verify you're using the correct service role key
2. Check Supabase project logs for errors
3. Try using the dashboard SQL editor with service role context

---

## Performance Considerations

The RLS policies use subqueries that join through the `user` table. For optimal performance:

1. **Ensure indexes exist:**
   ```sql
   -- Verify these indexes exist
   SELECT * FROM pg_indexes WHERE tablename = 'user' AND indexname LIKE '%provider_id%';
   SELECT * FROM pg_indexes WHERE tablename = 'chat_session' AND indexname LIKE '%user_id%';
   SELECT * FROM pg_indexes WHERE tablename = 'chat_message' AND indexname LIKE '%session_id%';
   SELECT * FROM pg_indexes WHERE tablename = 'search_history' AND indexname LIKE '%user_id%';
   SELECT * FROM pg_indexes WHERE tablename = 'search_history_result' AND indexname LIKE '%history_id%';
   ```

2. **If indexes are missing, create them:**
   ```sql
   CREATE INDEX IF NOT EXISTS user_provider_id_idx ON "user"(provider_id);
   CREATE INDEX IF NOT EXISTS chat_session_user_id_idx ON chat_session(user_id);
   CREATE INDEX IF NOT EXISTS chat_message_session_id_idx ON chat_message(session_id);
   CREATE INDEX IF NOT EXISTS chat_message_user_id_idx ON chat_message(user_id);
   CREATE INDEX IF NOT EXISTS search_history_user_id_idx ON search_history(user_id);
   CREATE INDEX IF NOT EXISTS search_history_result_history_id_idx ON search_history_result(history_id);
   ```

3. **Monitor query performance:**
   ```sql
   -- Check query execution plans
   EXPLAIN ANALYZE
   SELECT * FROM chat_session WHERE user_id IN (
       SELECT id FROM "user" WHERE provider_id = 'some-uuid-here'
   );
   ```

---

## Security Best Practices

1. **Test before deploying to production**
   - Enable RLS on a staging environment first
   - Verify all user workflows still work
   - Load test to ensure performance is acceptable

2. **Monitor audit logs**
   - Supabase logs all RLS policy evaluations
   - Check logs regularly for unexpected access patterns

3. **Regularly review policies**
   - Quarterly review of RLS policies
   - Update policies if data model changes
   - Remove unused policies to reduce complexity

4. **Backup policies**
   - Keep a copy of `supabase_rls_policies.sql` in version control
   - Document any custom modifications

5. **Use service role judiciously**
   - Service role bypasses RLS; use sparingly
   - Never expose service role key to frontend
   - Rotate keys periodically

---

## Rollback Plan

If you need to disable RLS (not recommended in production):

```sql
-- Disable RLS on all tables (WARNING: This exposes all data!)
ALTER TABLE chat_session DISABLE ROW LEVEL SECURITY;
ALTER TABLE chat_message DISABLE ROW LEVEL SECURITY;
ALTER TABLE search_history DISABLE ROW LEVEL SECURITY;
ALTER TABLE search_history_result DISABLE ROW LEVEL SECURITY;
ALTER TABLE error_log DISABLE ROW LEVEL SECURITY;
ALTER TABLE system_metrics DISABLE ROW LEVEL SECURITY;

-- Drop all policies (WARNING: This exposes all data!)
DROP POLICY IF EXISTS chat_session_select_own ON chat_session;
DROP POLICY IF EXISTS chat_session_insert_own ON chat_session;
DROP POLICY IF EXISTS chat_session_update_own ON chat_session;
DROP POLICY IF EXISTS chat_session_delete_own ON chat_session;
-- ... (repeat for all policies)
```

**Do NOT run this in production unless you have a critical incident.**

---

## Next Steps

1. **Apply the policies** using one of the three methods above
2. **Verify RLS is enabled** using the verification queries
3. **Test the policies** using the test cases provided
4. **Update your documentation** to reflect RLS is now enabled
5. **Inform your development team** that RLS is active
6. **Monitor application logs** for any permission-related errors after deployment

---

## Support & Questions

If you encounter issues:

1. Check the Supabase documentation: https://supabase.com/docs/guides/auth/row-level-security
2. Review the troubleshooting section above
3. Check your Supabase project logs for detailed error messages
4. Test policies in the SQL editor before deploying to production

---

**Last Updated:** 2026-08-13  
**Supabase Project:** VedaApex (bjulbxkvpsbgwwwcenrt)  
**Status:** Ready for Implementation
