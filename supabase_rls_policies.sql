-- ============================================================================
-- VedaApex Supabase RLS (Row Level Security) Policies
-- Project: VedaApex (bjulbxkvpsbgwwwcenrt)
-- 
-- This script enables RLS on 6 tables and creates appropriate policies.
-- 
-- Table Ownership Structure:
-- - user.id (INTEGER) is the local primary key
-- - user.provider_id (TEXT/UUID) stores the Supabase auth.uid()
-- - chat_session, chat_message, search_history, search_history_result use
--   INTEGER user_id as FK to user.id
-- - Policies must map auth.uid() -> user.provider_id -> user.id for checks
-- ============================================================================

-- ============================================================================
-- 1. CHAT_SESSION TABLE
-- ============================================================================
-- Enable RLS on chat_session
ALTER TABLE chat_session ENABLE ROW LEVEL SECURITY;

-- SELECT policy: User can only see their own chat sessions
CREATE POLICY chat_session_select_own
    ON chat_session
    FOR SELECT
    USING (
        user_id IN (
            SELECT id FROM "user"
            WHERE provider_id = auth.uid()
        )
    );

-- INSERT policy: User can only insert chat sessions with their own user_id
CREATE POLICY chat_session_insert_own
    ON chat_session
    FOR INSERT
    WITH CHECK (
        user_id IN (
            SELECT id FROM "user"
            WHERE provider_id = auth.uid()
        )
    );

-- UPDATE policy: User can only update their own chat sessions
CREATE POLICY chat_session_update_own
    ON chat_session
    FOR UPDATE
    USING (
        user_id IN (
            SELECT id FROM "user"
            WHERE provider_id = auth.uid()
        )
    )
    WITH CHECK (
        user_id IN (
            SELECT id FROM "user"
            WHERE provider_id = auth.uid()
        )
    );

-- DELETE policy: User can only delete their own chat sessions
CREATE POLICY chat_session_delete_own
    ON chat_session
    FOR DELETE
    USING (
        user_id IN (
            SELECT id FROM "user"
            WHERE provider_id = auth.uid()
        )
    );

-- ============================================================================
-- 2. CHAT_MESSAGE TABLE
-- ============================================================================
-- Enable RLS on chat_message
ALTER TABLE chat_message ENABLE ROW LEVEL SECURITY;

-- SELECT policy: User can only see messages in their own sessions
CREATE POLICY chat_message_select_own
    ON chat_message
    FOR SELECT
    USING (
        session_id IN (
            SELECT id FROM chat_session
            WHERE user_id IN (
                SELECT id FROM "user"
                WHERE provider_id = auth.uid()
            )
        )
    );

-- INSERT policy: User can only insert messages into their own sessions
CREATE POLICY chat_message_insert_own
    ON chat_message
    FOR INSERT
    WITH CHECK (
        session_id IN (
            SELECT id FROM chat_session
            WHERE user_id IN (
                SELECT id FROM "user"
                WHERE provider_id = auth.uid()
            )
        )
        AND
        user_id IN (
            SELECT id FROM "user"
            WHERE provider_id = auth.uid()
        )
    );

-- UPDATE policy: User can only update their own messages
CREATE POLICY chat_message_update_own
    ON chat_message
    FOR UPDATE
    USING (
        session_id IN (
            SELECT id FROM chat_session
            WHERE user_id IN (
                SELECT id FROM "user"
                WHERE provider_id = auth.uid()
            )
        )
        AND
        user_id IN (
            SELECT id FROM "user"
            WHERE provider_id = auth.uid()
        )
    )
    WITH CHECK (
        session_id IN (
            SELECT id FROM chat_session
            WHERE user_id IN (
                SELECT id FROM "user"
                WHERE provider_id = auth.uid()
            )
        )
        AND
        user_id IN (
            SELECT id FROM "user"
            WHERE provider_id = auth.uid()
        )
    );

-- DELETE policy: User can only delete their own messages
CREATE POLICY chat_message_delete_own
    ON chat_message
    FOR DELETE
    USING (
        session_id IN (
            SELECT id FROM chat_session
            WHERE user_id IN (
                SELECT id FROM "user"
                WHERE provider_id = auth.uid()
            )
        )
        AND
        user_id IN (
            SELECT id FROM "user"
            WHERE provider_id = auth.uid()
        )
    );

-- ============================================================================
-- 3. SEARCH_HISTORY TABLE
-- ============================================================================
-- Enable RLS on search_history
ALTER TABLE search_history ENABLE ROW LEVEL SECURITY;

-- SELECT policy: User can only see their own search history
CREATE POLICY search_history_select_own
    ON search_history
    FOR SELECT
    USING (
        user_id IN (
            SELECT id FROM "user"
            WHERE provider_id = auth.uid()
        )
    );

-- INSERT policy: User can only insert search history with their own user_id
CREATE POLICY search_history_insert_own
    ON search_history
    FOR INSERT
    WITH CHECK (
        user_id IN (
            SELECT id FROM "user"
            WHERE provider_id = auth.uid()
        )
    );

-- UPDATE policy: User can only update their own search history
CREATE POLICY search_history_update_own
    ON search_history
    FOR UPDATE
    USING (
        user_id IN (
            SELECT id FROM "user"
            WHERE provider_id = auth.uid()
        )
    )
    WITH CHECK (
        user_id IN (
            SELECT id FROM "user"
            WHERE provider_id = auth.uid()
        )
    );

-- DELETE policy: User can only delete their own search history
CREATE POLICY search_history_delete_own
    ON search_history
    FOR DELETE
    USING (
        user_id IN (
            SELECT id FROM "user"
            WHERE provider_id = auth.uid()
        )
    );

-- ============================================================================
-- 4. SEARCH_HISTORY_RESULT TABLE
-- ============================================================================
-- Enable RLS on search_history_result
ALTER TABLE search_history_result ENABLE ROW LEVEL SECURITY;

-- SELECT policy: User can only see results for their own search history
CREATE POLICY search_history_result_select_own
    ON search_history_result
    FOR SELECT
    USING (
        history_id IN (
            SELECT id FROM search_history
            WHERE user_id IN (
                SELECT id FROM "user"
                WHERE provider_id = auth.uid()
            )
        )
    );

-- INSERT policy: User can only insert results for their own search history
CREATE POLICY search_history_result_insert_own
    ON search_history_result
    FOR INSERT
    WITH CHECK (
        history_id IN (
            SELECT id FROM search_history
            WHERE user_id IN (
                SELECT id FROM "user"
                WHERE provider_id = auth.uid()
            )
        )
    );

-- UPDATE policy: User can only update results for their own search history
CREATE POLICY search_history_result_update_own
    ON search_history_result
    FOR UPDATE
    USING (
        history_id IN (
            SELECT id FROM search_history
            WHERE user_id IN (
                SELECT id FROM "user"
                WHERE provider_id = auth.uid()
            )
        )
    )
    WITH CHECK (
        history_id IN (
            SELECT id FROM search_history
            WHERE user_id IN (
                SELECT id FROM "user"
                WHERE provider_id = auth.uid()
            )
        )
    );

-- DELETE policy: User can only delete results for their own search history
CREATE POLICY search_history_result_delete_own
    ON search_history_result
    FOR DELETE
    USING (
        history_id IN (
            SELECT id FROM search_history
            WHERE user_id IN (
                SELECT id FROM "user"
                WHERE provider_id = auth.uid()
            )
        )
    );

-- ============================================================================
-- 5. ERROR_LOG TABLE (Admin/Internal Only)
-- ============================================================================
-- Enable RLS on error_log
ALTER TABLE error_log ENABLE ROW LEVEL SECURITY;

-- NOTE: error_log is for system/admin use only.
-- No policies needed for regular authenticated users (they'll see no rows).
-- Service role can still access all rows (service role bypasses RLS).

-- SELECT policy: Deny all for authenticated/anon users (only service_role can read)
CREATE POLICY error_log_deny_all
    ON error_log
    FOR SELECT
    USING (false);

-- INSERT policy: Deny all for authenticated/anon users
CREATE POLICY error_log_deny_all_insert
    ON error_log
    FOR INSERT
    WITH CHECK (false);

-- UPDATE policy: Deny all for authenticated/anon users
CREATE POLICY error_log_deny_all_update
    ON error_log
    FOR UPDATE
    USING (false)
    WITH CHECK (false);

-- DELETE policy: Deny all for authenticated/anon users
CREATE POLICY error_log_deny_all_delete
    ON error_log
    FOR DELETE
    USING (false);

-- ============================================================================
-- 6. SYSTEM_METRICS TABLE (Admin/Internal Only)
-- ============================================================================
-- Enable RLS on system_metrics
ALTER TABLE system_metrics ENABLE ROW LEVEL SECURITY;

-- NOTE: system_metrics is for system/admin use only.
-- No policies needed for regular authenticated users (they'll see no rows).
-- Service role can still access all rows (service role bypasses RLS).

-- SELECT policy: Deny all for authenticated/anon users (only service_role can read)
CREATE POLICY system_metrics_deny_all
    ON system_metrics
    FOR SELECT
    USING (false);

-- INSERT policy: Deny all for authenticated/anon users
CREATE POLICY system_metrics_deny_all_insert
    ON system_metrics
    FOR INSERT
    WITH CHECK (false);

-- UPDATE policy: Deny all for authenticated/anon users
CREATE POLICY system_metrics_deny_all_update
    ON system_metrics
    FOR UPDATE
    USING (false)
    WITH CHECK (false);

-- DELETE policy: Deny all for authenticated/anon users
CREATE POLICY system_metrics_deny_all_delete
    ON system_metrics
    FOR DELETE
    USING (false);

-- ============================================================================
-- VERIFICATION QUERIES
-- ============================================================================
-- After applying these policies, run these verification queries to confirm
-- RLS is properly enabled:

-- Check RLS status on all tables:
/*
SELECT
    schemaname,
    tablename,
    rowsecurity AS "RLS Enabled"
FROM pg_tables
WHERE tablename IN ('chat_session', 'chat_message', 'search_history', 'search_history_result', 'error_log', 'system_metrics')
AND schemaname = 'public'
ORDER BY tablename;
*/

-- Check all policies on these tables:
/*
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
*/

-- ============================================================================
-- TESTING GUIDELINES
-- ============================================================================
-- 1. Log in as a test user and verify they can:
--    - SELECT their own chat_session records
--    - INSERT new chat_session records with their user_id
--    - SELECT/INSERT/UPDATE/DELETE messages within their sessions
--    - SELECT/INSERT/UPDATE/DELETE their search_history entries
--    - Cannot access error_log or system_metrics
--
-- 2. Log in as a different user and verify they CANNOT:
--    - See the first user's chat_sessions
--    - See the first user's chat_messages
--    - See the first user's search_history
--
-- 3. Verify service_role can still access all tables (bypasses RLS)
-- ============================================================================
