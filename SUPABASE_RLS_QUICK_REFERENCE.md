# VedaApex Supabase RLS Quick Reference

## Files Created

1. **supabase_rls_policies.sql** - Complete SQL script with all RLS policies
2. **SUPABASE_RLS_IMPLEMENTATION_GUIDE.md** - Comprehensive implementation guide with testing procedures

## Quick Start (2 Options)

### Option A: Supabase Dashboard (Fastest)

1. Go to https://app.supabase.com → Select VedaApex project
2. Click "SQL Editor" → Click "+ New Query"
3. Copy entire contents of `supabase_rls_policies.sql`
4. Paste into SQL Editor → Click "Run"
5. Verify with queries below

### Option B: Supabase CLI

```bash
# Login and link project
supabase login
supabase link --project-ref bjulbxkvpsbgwwwcenrt

# Create migration
supabase migration new enable_rls_policies

# Copy contents of supabase_rls_policies.sql to the migration file
# Then push:
supabase db push
```

---

## What Gets Secured

| Table | Ownership | RLS Type |
|-------|-----------|----------|
| chat_session | User-owned | User can see/edit only their sessions |
| chat_message | User-owned | User can see/edit only messages in their sessions |
| search_history | User-owned | User can see/edit only their search history |
| search_history_result | User-owned | User can see/edit only results from their searches |
| error_log | Admin only | Deny all authenticated users (service role can read) |
| system_metrics | Admin only | Deny all authenticated users (service role can read) |

---

## Verification Queries

### Check RLS is Enabled (1 sec)

```sql
SELECT tablename, rowsecurity
FROM pg_tables
WHERE tablename IN ('chat_session', 'chat_message', 'search_history', 
                     'search_history_result', 'error_log', 'system_metrics')
AND schemaname = 'public'
ORDER BY tablename;
```

**Expected:** All show `rowsecurity = true`

### List All Policies (1 sec)

```sql
SELECT tablename, policyname, permissive
FROM pg_policies
WHERE tablename IN ('chat_session', 'chat_message', 'search_history', 
                     'search_history_result', 'error_log', 'system_metrics')
AND schemaname = 'public'
ORDER BY tablename;
```

**Expected:** 4 policies per table (SELECT, INSERT, UPDATE, DELETE)

---

## Testing (Optional but Recommended)

### Test 1: User Can Access Own Data

```python
from supabase import create_client

client = create_client(SUPABASE_URL, access_token)  # User's auth token

# User should be able to read their own chat sessions
result = client.table('chat_session').select('*').execute()
print(len(result.data))  # Should be > 0 if user has sessions
```

### Test 2: User Cannot Access Other User's Data

```python
# User A creates a chat
# User B tries to access it (should fail)
result = client.table('chat_session').select('*').eq('id', 'user_a_chat').execute()
print(len(result.data))  # Should be 0 due to RLS
```

### Test 3: Regular Users Cannot Access Admin Tables

```python
# Any authenticated user tries to access error_log
result = client.table('error_log').select('*').execute()
print(len(result.data))  # Should be 0 (RLS denies all)
```

### Test 4: Service Role Can Still Access Everything

```python
from supabase import create_client

# Use service role key (not user's token)
admin_client = create_client(SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY)

# Service role can read error_log
result = admin_client.table('error_log').select('*').execute()
print(len(result.data))  # Should return rows (RLS bypassed)
```

---

## Common Issues & Fixes

### Issue: Users Get 0 Rows After Enabling RLS

**Check:** Does `user.provider_id` match the user's `auth.uid()`?

```sql
-- As service role, find a user and check provider_id
SELECT id, email, provider_id FROM "user" LIMIT 1;

-- In your app, get current user's auth.uid():
-- In JS/Python: auth.currentUser.id or supabase.auth.getUser().user.id
-- This UUID should match provider_id in the SQL above
```

**If mismatch:** Update the user's provider_id to match their auth UUID

```sql
UPDATE "user" SET provider_id = 'their-auth-uuid-here' WHERE email = 'user@example.com';
```

### Issue: Policies Not Applied

**Check:** Did the SQL execute without errors? Look for error messages in the dashboard

**Verify:**
```sql
-- Count policies on each table
SELECT tablename, COUNT(*) as policy_count
FROM pg_policies
WHERE tablename IN ('chat_session', 'chat_message', 'search_history', 
                     'search_history_result', 'error_log', 'system_metrics')
AND schemaname = 'public'
GROUP BY tablename
ORDER BY tablename;

-- Should show 4 policies per table
```

### Issue: Performance Degradation

**The policies use JOINs through the user table. Verify indexes exist:**

```sql
CREATE INDEX IF NOT EXISTS user_provider_id_idx ON "user"(provider_id);
CREATE INDEX IF NOT EXISTS chat_session_user_id_idx ON chat_session(user_id);
CREATE INDEX IF NOT EXISTS chat_message_session_id_idx ON chat_message(session_id);
CREATE INDEX IF NOT EXISTS chat_message_user_id_idx ON chat_message(user_id);
CREATE INDEX IF NOT EXISTS search_history_user_id_idx ON search_history(user_id);
CREATE INDEX IF NOT EXISTS search_history_result_history_id_idx ON search_history_result(history_id);
```

---

## Policy Logic Summary

### For User-Owned Tables (chat_session, chat_message, etc.)

```
SELECT: Can user see this row?
  → Is row's user_id in (SELECT id FROM user WHERE provider_id = auth.uid())?
  → If yes, allow. If no, deny.

INSERT: Can user create this row?
  → Is user_id field pointing to current user?
  → If yes, allow. If no, deny.

UPDATE: Can user modify this row?
  → Is row's user_id their own?
  → If yes, allow. If no, deny.

DELETE: Can user remove this row?
  → Is row's user_id their own?
  → If yes, allow. If no, deny.
```

### For Admin Tables (error_log, system_metrics)

```
ALL operations: DENY for authenticated users, ANON users
  → Regular users always get 0 rows
  → Service role bypasses RLS (can read/write normally)
```

---

## Architecture Note

The app uses:
- **Supabase Auth** for authentication (stores UUID in auth.users)
- **Custom user table** with integer PK (app-specific users)
- **Mapping:** `user.provider_id` = Supabase auth UUID

The policies bridge this by:
1. Getting current user's auth.uid() (UUID)
2. Finding matching `user.provider_id`
3. Using the `user.id` (integer) to filter table rows

---

## Next Steps

1. **Apply policies** using Dashboard or CLI (5 min)
2. **Run verification queries** (1 min)
3. **Test with real users** (5-10 min)
4. **Update app docs** to note RLS is active
5. **Inform team** about the security changes

---

## Rollback (Emergency Only)

If you need to disable RLS (not recommended in production):

```sql
-- Disable RLS on all tables
ALTER TABLE chat_session DISABLE ROW LEVEL SECURITY;
ALTER TABLE chat_message DISABLE ROW LEVEL SECURITY;
ALTER TABLE search_history DISABLE ROW LEVEL SECURITY;
ALTER TABLE search_history_result DISABLE ROW LEVEL SECURITY;
ALTER TABLE error_log DISABLE ROW LEVEL SECURITY;
ALTER TABLE system_metrics DISABLE ROW LEVEL SECURITY;

-- Drop policies
DROP POLICY IF EXISTS chat_session_select_own ON chat_session;
DROP POLICY IF EXISTS chat_session_insert_own ON chat_session;
DROP POLICY IF EXISTS chat_session_update_own ON chat_session;
DROP POLICY IF EXISTS chat_session_delete_own ON chat_session;
DROP POLICY IF EXISTS chat_message_select_own ON chat_message;
DROP POLICY IF EXISTS chat_message_insert_own ON chat_message;
DROP POLICY IF EXISTS chat_message_update_own ON chat_message;
DROP POLICY IF EXISTS chat_message_delete_own ON chat_message;
DROP POLICY IF EXISTS search_history_select_own ON search_history;
DROP POLICY IF EXISTS search_history_insert_own ON search_history;
DROP POLICY IF EXISTS search_history_update_own ON search_history;
DROP POLICY IF EXISTS search_history_delete_own ON search_history;
DROP POLICY IF EXISTS search_history_result_select_own ON search_history_result;
DROP POLICY IF EXISTS search_history_result_insert_own ON search_history_result;
DROP POLICY IF EXISTS search_history_result_update_own ON search_history_result;
DROP POLICY IF EXISTS search_history_result_delete_own ON search_history_result;
DROP POLICY IF EXISTS error_log_deny_all ON error_log;
DROP POLICY IF EXISTS error_log_deny_all_insert ON error_log;
DROP POLICY IF EXISTS error_log_deny_all_update ON error_log;
DROP POLICY IF EXISTS error_log_deny_all_delete ON error_log;
DROP POLICY IF EXISTS system_metrics_deny_all ON system_metrics;
DROP POLICY IF EXISTS system_metrics_deny_all_insert ON system_metrics;
DROP POLICY IF EXISTS system_metrics_deny_all_update ON system_metrics;
DROP POLICY IF EXISTS system_metrics_deny_all_delete ON system_metrics;
```

---

**Created:** 2026-08-13  
**Project:** VedaApex (bjulbxkvpsbgwwwcenrt)  
**Status:** Ready for implementation
