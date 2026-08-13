# VedaApex Redis Conversation Memory System

## Overview

This document describes the Redis conversation memory layer added to VedaApex, enabling persistent and efficient AI chat context management.

### Key Features

- **Fast Memory Layer**: Redis caches recent conversations for sub-millisecond retrieval
- **Permanent Storage**: PostgreSQL database remains the source of truth
- **User Isolation**: Each user's data is scoped by `user_id`
- **Graceful Fallback**: Application works without Redis (just slower)
- **Context Windowing**: Automatic summarization for long conversations
- **Deduplication**: Support for idempotent message saves
- **Zero Breaking Changes**: Integrates seamlessly with existing chat API

## Architecture

### Data Flow

```
User Message
    ↓
[Chat Router] → Save to Database
    ↓            ↓
              Save to Redis Cache (async)
    ↓            ↓
Retrieve Context:
  1. Try Redis (fast)
  2. Fall back to Database (if cache miss)
  3. Restore Database results to Redis
    ↓
Build AI Context (recent + summary)
    ↓
Call AI Model
    ↓
Get AI Response
    ↓
Save to Database + Redis
    ↓
Return to User
```

### Redis Key Structure

```
chat:{user_id}:{conversation_id}:messages
  → Redis List of message JSON objects (chronological order)

chat:{user_id}:{conversation_id}:summary
  → Redis String with conversation summary

chat:{user_id}:{conversation_id}:metadata
  → Redis Hash with metadata

chat:{user_id}:conversations
  → Redis Set of conversation IDs for user
```

### TTL & Cleanup

- Each key has a TTL (default 30 days)
- After TTL expires, Redis automatically deletes the key
- Database records are NOT deleted (permanent storage)
- TTL is configurable via `REDIS_CHAT_TTL`

## Implementation Details

### Files Added

1. **`app/services/redis_client.py`**
   - Singleton Redis client with connection pooling
   - Lazy initialization on first use
   - Health check functionality
   - Graceful degradation if Redis unavailable

2. **`app/services/redis_chat_memory.py`**
   - RedisChatMemory class with static methods
   - Message storage and retrieval
   - Conversation summarization
   - User isolation enforcement
   - Database restoration logic

3. **`tests/test_redis_chat_memory.py`**
   - Comprehensive test suite
   - Tests for all scenarios (isolation, fallback, summarization, etc.)

### Files Modified

1. **`app/core/config.py`**
   - Added `REDIS_URL` configuration
   - Added `REDIS_CHAT_TTL` setting
   - Added `REDIS_CHAT_CONTEXT_LIMIT` setting
   - Added `REDIS_CHAT_SUMMARY_TOKEN_THRESHOLD` setting

2. **`app/main.py`**
   - Added `RedisClient.initialize()` in startup
   - Added `RedisClient.shutdown()` in shutdown
   - Health check logging

3. **`app/services/chat_memory_service.py`**
   - Enhanced `add_message()` to save to Redis asynchronously
   - Enhanced `list_messages()` to restore from Redis to database
   - Added `get_context_for_ai()` for optimized context retrieval
   - Added `clear_conversation_cache()` for cache clearing
   - Added `save_conversation_summary()` for long conversation handling

4. **`requirements.txt`**
   - Already included: `redis==5.0.1` and `aioredis==2.0.1`
   - No new dependencies needed

## Configuration

### Required Environment Variables

```bash
# Redis connection string
REDIS_URL=redis://localhost:6379/0

# Optional: Custom TTL (seconds)
REDIS_CHAT_TTL=2592000  # 30 days

# Optional: Context window limit
REDIS_CHAT_CONTEXT_LIMIT=50

# Optional: Token threshold for summarization
REDIS_CHAT_SUMMARY_TOKEN_THRESHOLD=5000
```

### Development Setup

**Local Redis (Docker)**:
```bash
docker run -d -p 6379:6379 redis:latest
export REDIS_URL=redis://localhost:6379/0
```

**Local Redis (with CLI tools)**:
```bash
# macOS
brew install redis
redis-server

# Linux
sudo apt-get install redis-server
redis-server

# Windows
# Use Docker or WSL2
```

**Connect with Redis CLI**:
```bash
redis-cli
> PING
PONG
> KEYS chat:*
> GET chat:1:conv_123:messages
```

### Production Deployment

1. **Redis Cloud (Recommended)**:
   ```bash
   REDIS_URL=redis://:your-api-key@redis-12345.c123.us-east-1-2.ec2.cloud.redislabs.com:12345
   ```

2. **AWS ElastiCache**:
   ```bash
   REDIS_URL=redis://your-cluster.abc123.ng.0001.usw2.cache.amazonaws.com:6379
   ```

3. **Self-Managed Redis**:
   - Deploy on EC2, VPC, or container
   - Enable authentication (Redis ACL or requirepass)
   - Configure TLS/SSL encryption
   - Set up replication and failover
   - Monitor with CloudWatch or Prometheus

## Usage

### Automatic (Transparent to Frontend)

The Redis integration is automatic. Existing chat API continues working:

```python
# Existing endpoint - now with Redis
@router.post("/chat/ask")
async def ask_chat(body: ChatMessageCreate, user: User = Depends(...)):
    result = await ChatMemoryService.ask(
        session=session,
        user=user,
        session_id=body.session_id,
        message=body.message,
        model="auto",
    )
    return result  # ← Messages automatically cached in Redis
```

### Explicit Context Retrieval (for AI calls)

When building context for the AI model:

```python
# Old way (database only)
messages = ChatMemoryService.list_messages(session, user, session_id, limit=50)
context = [{"role": m.role, "content": m.content} for m in messages]

# New way (Redis + database fallback)
context = await ChatMemoryService.get_context_for_ai(
    session, user, session_id, context_limit=50
)
# ↑ Uses Redis if available, falls back to DB if cache miss
```

### Conversation Management

```python
# Clear conversation cache (but keep database record)
await ChatMemoryService.clear_conversation_cache(user, session_id)

# Save a conversation summary (for long chats)
summary = "Earlier user asked about Python decorators and we discussed..."
await ChatMemoryService.save_conversation_summary(user, session_id, summary)
```

### Health Checks

```python
# Check Redis status
from app.services.redis_client import RedisClient

health = await RedisClient.health_check()
# Returns: {"status": "healthy", "available": True, "latency_ms": 1.5, ...}

# Check if Redis is available
if RedisClient.is_available():
    print("Using Redis cache")
else:
    print("Using database only")
```

## API Compatibility

### No Breaking Changes

The frontend API remains unchanged:

**Request**:
```json
POST /api/v1/chat/ask
{
  "session_id": "chat_abc123",
  "message": "What did I ask before?"
}
```

**Response** (unchanged):
```json
{
  "success": true,
  "session_id": "chat_abc123",
  "title": "Conversation Title",
  "answer": "You asked...",
  "history": [...],
  "metadata": {...}
}
```

### Optional: conversation_id in Frontend

If your frontend doesn't send `session_id`, the backend generates one automatically. No changes needed.

## Error Handling & Logging

### Graceful Degradation

If Redis is unavailable:
1. Application logs warning
2. Chat continues using database
3. No user-facing errors
4. Slower response time (database instead of cache)
5. Everything still works

### Logging Examples

```
✓ Redis connected and ready
Retrieved 25 cached messages: user=1 conversation=chat_123
Redis cache miss; fetching from database
Saved message to Redis: user=1 conversation=chat_123 role=user
Failed to save message to Redis (will continue without cache): ConnectionError
```

### No Secrets in Logs

- Redis passwords are masked in logs
- API keys are never logged
- Authentication tokens are never logged
- Only non-sensitive operational info is logged

## Performance Characteristics

### Latency

- **Redis hit** (cache): ~1-5ms
- **Database miss** (first request): ~10-50ms
- **Subsequent requests** (restored to Redis): ~1-5ms

### Memory Usage

- Each message ~200-500 bytes in Redis
- Typical conversation: 1-10KB
- 1000 active users × 50KB avg = 50MB Redis memory

### Token Count Management

For long conversations:
1. Count tokens in messages
2. If approaching `REDIS_CHAT_SUMMARY_TOKEN_THRESHOLD`:
   - Summarize messages older than N days
   - Store summary in Redis
   - Include summary in AI context
3. Keep recent messages as-is
4. Result: Rich context, manageable token count

## Testing

### Run Tests

```bash
# Run all Redis tests
pytest tests/test_redis_chat_memory.py -v

# Run specific test
pytest tests/test_redis_chat_memory.py::TestUserIsolation -v

# Run with coverage
pytest tests/test_redis_chat_memory.py --cov=app.services
```

### Manual Testing

**Test 1: Basic Saving & Retrieval**
```python
user_id, conv_id = 1, "test_conv"
await RedisChatMemory.save_message(user_id, conv_id, "user", "Hello")
messages = await RedisChatMemory.get_messages(user_id, conv_id)
assert len(messages) == 1
```

**Test 2: User Isolation**
```python
# User 1 saves message
await RedisChatMemory.save_message(1, "conv_A", "user", "Secret")

# User 2 tries to access
messages = await RedisChatMemory.get_messages(2, "conv_A")
assert len(messages) == 0  # User 2 sees nothing
```

**Test 3: Redis Fallback**
```python
# Disconnect Redis, then:
messages = await RedisChatMemory.get_messages(1, "conv_A")
assert messages == []  # Returns empty, no error
```

**Test 4: Long Conversation**
```python
# Save 100 messages
for i in range(100):
    await RedisChatMemory.save_message(1, "conv", "user" if i % 2 else "assistant", f"Message {i}")

# Get recent only
recent = await RedisChatMemory.get_recent_messages(1, "conv", limit=10)
assert len(recent) <= 10
```

## Troubleshooting

### Redis Won't Connect

```python
# Check configuration
print(settings.REDIS_URL)  # Should not be None

# Check Redis is running
redis-cli ping  # Should return PONG

# Check URL format
redis://[:password]@host:port/db

# Try connecting
redis-cli -u redis://localhost:6379/0
```

### Messages Not Persisting

1. Check database is working (messages should be in database)
2. Check Redis TTL hasn't expired
3. Check Redis memory (may be full)
4. Check Redis logs for errors

### Slow Performance

1. Check Redis latency: `redis-cli --latency`
2. Check network connectivity to Redis
3. Check Redis memory usage: `INFO memory`
4. Increase `REDIS_CHAT_CONTEXT_LIMIT` if needed
5. Reduce message frequency or use summarization

### Memory Growing

Redis by default keeps growing. Set memory limit and eviction policy:

```redis
# In Redis config or via CLI
CONFIG SET maxmemory 1gb
CONFIG SET maxmemory-policy allkeys-lru
```

### Connection Timeout

```
Error: Connection timeout
Solution: Check Redis host, port, and firewall rules
```

```
Error: WRONGPASS/AUTH failed
Solution: Check Redis password and REDIS_URL format
```

## Monitoring & Alerts

### Key Metrics

1. **Redis Connection Status**
   - Alert if disconnected for > 5 min
   - Log on startup success/failure

2. **Cache Hit Rate**
   - Track how often Redis cache is hit vs missed
   - Target: >80% hit rate for recurring users

3. **Memory Usage**
   - Alert if > 80% of max
   - Monitor growth trends

4. **Latency**
   - Typical: <5ms per operation
   - Alert if > 100ms

### Example Prometheus Metrics

```
redis_chat_memory_save_total{user_id="1", status="success"}
redis_chat_memory_retrieve_total{status="hit|miss"}
redis_chat_memory_latency_ms{operation="save|retrieve"}
redis_memory_used_bytes
redis_connection_status{status="connected|disconnected"}
```

## Migration & Upgrades

### From Database-Only to Redis

1. Add `REDIS_URL` to `.env`
2. Restart application
3. Redis automatically populates on first use
4. No data loss (database unchanged)

### Clearing All Cache

```python
from app.services.redis_client import RedisClient

redis = await RedisClient.get()
if redis:
    # Clear all chat cache
    pattern = "chat:*"
    keys = await redis.keys(pattern)
    if keys:
        await redis.delete(*keys)
    print(f"Cleared {len(keys)} Redis keys")
```

### Disabling Redis

1. Remove `REDIS_URL` from `.env`
2. Application continues using database
3. No breaking changes
4. Just slower (all reads from database)

## Security Considerations

### Never Expose Credentials

❌ BAD:
```python
REDIS_URL="redis://:mypassword@redis.com:6379"  # In code!
```

✅ GOOD:
```bash
# In .env file (not committed)
export REDIS_URL=redis://:mypassword@redis.com:6379

# Or environment variable
```

### TLS/SSL Encryption

For production:
```
REDIS_URL=rediss://:password@host:port  # Note: "rediss://" with SSL
```

### VPC/Network Security

- Redis should only be accessible from application servers
- Use security groups/network policies
- Never expose Redis to the internet
- Consider using SSH tunnel for access

### Access Control

- Use Redis ACL (Redis 6+) for user-based access
- Each service gets limited privileges
- Rotate credentials regularly
- Audit access logs

## FAQ

### Q: Will messages disappear from Redis?
**A**: Yes, after `REDIS_CHAT_TTL` (default 30 days). But database records are permanent.

### Q: Do I need Redis for production?
**A**: No, it's optional. Application works without it (just slower).

### Q: Can users access each other's messages?
**A**: No, Redis keys include `user_id` for isolation.

### Q: How much memory does Redis need?
**A**: Typical: 50-500MB for small deployments. Depends on active users and conversation size.

### Q: What if Redis goes down?
**A**: Application continues working, just falls back to database (slower).

### Q: Can I use Redis for other purposes?
**A**: Yes, Redis is a general-purpose cache store. Just be careful with key naming.

### Q: How do I monitor Redis?
**A**: Use `redis-cli`, RedisInsight, or cloud provider dashboards.

### Q: Can I replicate conversations?
**A**: Yes, via database backups. Redis is ephemeral.

## Further Reading

- [Redis Documentation](https://redis.io/docs/)
- [redis-py Client Documentation](https://redis-py.readthedocs.io/)
- [FastAPI + Redis Guide](https://fastapi.tiangolo.com/advanced/background-tasks/)
- [Redis in Production](https://redis.io/docs/management/sentinel/)

## Support

For issues or questions:
1. Check application logs: `grep -i redis app.log`
2. Check Redis status: `redis-cli info server`
3. Review this documentation
4. Check test cases in `tests/test_redis_chat_memory.py`

---

**Last Updated**: 2026-08-13  
**VedaApex Version**: 2.0.0  
**Redis Client**: redis==5.0.1  
**Status**: Production Ready
