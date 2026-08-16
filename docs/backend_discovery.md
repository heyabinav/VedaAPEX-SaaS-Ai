# Backend Discovery Report

Date: 2026-08-16
Scope: Phase 0 discovery for VedaApex backend only.

## 1) FastAPI entrypoint and router structure

Primary app bootstrapping:
- app/main.py — FastAPI application, lifespan startup/shutdown, middleware registration, router includes, health endpoints.

Core router modules:
- app/routers/auth.py — authentication, registration, login, API key management.
- app/routers/chat.py — chat sessions and chat ask endpoint.
- app/routers/custom_skills.py — custom skills CRUD and execution API.
- app/routers/persistent_skills.py — persistent user skills.
- app/routers/skills_import.py — skill ingestion from GitHub/folder.
- app/routers/media_search.py — unified media search route.
- app/routers/mcp_custom.py — custom MCP connector lifecycle.
- app/routers/connectors.py — connector management.
- app/routers/connector_registry.py — connector registry.
- app/routers/search_history.py — search history.
- app/routers/ai_tools.py — AI model/tool orchestration entrypoints.
- app/routers/generation.py — generation and credit-gated AI generation.
- app/routers/payments.py — payments.
- app/routers/subscriptions.py — subscription plans.
- app/routers/wallet.py — wallet/credit endpoints.
- app/routers/api_keys.py — dev API key management.
- app/routers/admin.py — admin routes.
- app/routers/admin_dashboard.py — admin dashboard summary endpoints.
- app/routers/assets.py — AI asset storage/proxy.
- app/routers/website.py — website requirements questionnaire.

Additional route folders and modules:
- app/routes/media.py — media upload/action routes + credit deduction logic.
- app/routes/processor.py — processor service router.
- app/routes/google_mcp.py — Google MCP endpoints.
- app/routes/design_mcp.py — design MCP endpoints.
- app/routes/canva_oauth.py — Canva OAuth routes.
- app/routes/figma_oauth.py — Figma OAuth routes.
- app/email/routes/auth.py — email verification auth routes.
- app/mcp/connector_tools.py — MCP connector tooling router.

Router registration pattern:
- app/main.py includes routers with prefix patterns such as /api/v1, /auth, /chat, /skills, /search, /mcp, etc.

## 2) Existing services: auth/JWT, DB/ORM, Redis, streaming, MCP, provider router

Authentication and JWT:
- app/core/security.py — JWT creation helper and password hashing.
- app/routers/auth.py — current authenticated user dependency via AuthService.get_authenticated_user.
- app/services/auth_service.py — resolves users from x-api-key or Bearer token; validates Supabase tokens and local DB user.
- app/services/supabase_service.py — Supabase auth integration.
- app/services/api_key_service.py — API key validation service.

DB and ORM:
- app/db/session.py — SQLModel engine creation, DB URL normalization, startup table creation, schema repair.
- app/models/user.py — user model and relationships.
- app/models/token.py — wallets, transactions, subscription plans, promo codes, request log models.
- app/models/chat_session.py — chat session persistence.
- app/models/chat_message.py — chat message persistence.
- app/models/mcp_connector.py — MCP connector and OAuth tables.
- app/models/custom_skill.py — user custom skill models.
- app/models/search_history.py — search history models.
- app/models/search_history_result.py — saved result payload models.
- app/models/asset.py — AI asset metadata and provider usage log models.

Redis:
- app/services/redis_client.py — singleton Redis client with initialize/shutdown and health check.
- app/services/redis_chat_memory.py — Redis-backed chat memory manager.
- app/workers/celery_app.py — Celery app configured around Redis broker.
- app/workers/tasks.py — worker tasks.

Streaming / SSE / WebSocket:
- No explicit SSE or WebSocket streaming implementation was found in the backend scan; there is no EventSourceResponse or WebSocket route registration in the active backend code.
- The project appears to rely on standard HTTP request/response patterns instead of explicit SSE/WS streaming transport in the current codebase.
- Relevant files checked: app/main.py, app/routers/*, app/routes/*, app/services/*.

MCP client / MCP tooling:
- app/services/mcp/client.py — shared MCP client wrapper.
- app/services/mcp/transport.py — transport helper for MCP connection.
- app/services/mcp/security.py — SSRF protections and URL validation.
- app/services/mcp/oauth.py — OAuth flows for MCP connectors.
- app/services/mcp/discovery.py — MCP server discovery.
- app/services/mcp/tools.py — MCP tool processing.
- app/services/mcp/errors.py — MCP-specific exceptions.
- app/mcp/connector_tools.py — public router for connector MCP tools.
- app/routers/mcp_custom.py — end-to-end custom connector integration.

Provider router / AI provider abstraction:
- app/services/ai_service.py — high-level AI orchestration service; imports many provider-specific modules.
- app/services/providers/ — provider implementations for OpenRouter, Gemini, Groq, Tavily, Serper, etc.
- app/core/config.py — env-backed provider keys and runtime config.
- app/services/key_manager.py — API key rotation/availability manager.

Representative provider implementations:
- app/services/providers/gemini_provider.py
- app/services/providers/groq_provider.py
- app/services/providers/openrouter_provider.py
- app/services/providers/serper_provider.py
- app/services/providers/tavily_provider.py
- app/services/providers/python_search_provider.py

## 3) Existing search integrations

Unified media search and intent logic:
- app/routers/media_search.py — endpoint wrapper for media search.
- app/services/media_search/service.py — search orchestration.
- app/services/media_search/intent_router.py — detects image/video/space intent.
- app/services/media_search/models.py — request/result models.
- app/services/media_search/image_provider.py — Pexels image provider.
- app/services/media_search/video_provider.py — Pexels video provider.
- app/services/media_search/nasa_provider.py — NASA API provider.

Web search:
- app/services/search_router.py — smart provider routing for web search.
- app/services/search_decision_engine.py — classifies whether a query needs search and what type.
- app/services/providers/serper_provider.py — Serper web search provider.
- app/services/providers/tavily_provider.py — Tavily web search provider.
- app/services/providers/python_search_provider.py — fallback provider.

Other search-related modules:
- app/routers/search_history.py — saves and lists search history.
- app/models/search_history.py / app/models/search_history_result.py — persistence for search history.

## 4) Existing usage/credit/billing system

Credit and wallet system:
- app/models/token.py — TokenWallet, TokenTransaction, SubscriptionPlan, UserSubscription, DailyReward, PromoCode, RequestLog.
- app/services/token_service.py — atomic credit wallet operations.
- app/services/subscription_service.py — subscription lookup and plan logic.
- app/services/generation_policy_service.py — generation cost and daily credit limit logic.
- app/services/usage_tracking_service.py — usage tracking abstraction.
- app/services/ai_usage_logger.py — AI provider usage logging.
- app/models/asset.py — AIProviderUsageLog.
- app/cron/daily_reset.py — daily credit distribution and subscription expiry automation.

Billing and plan config:
- app/config/costs.py — generation and subscription cost constants.
- app/routers/payments.py — payments integration.
- app/routers/promo.py — promo code redemption and credit grants.
- app/routers/subscriptions.py — plan listing and subscription activation UI hooks.

## 5) Existing rate-limiting middleware

- middleware/rate_limit.py — in-memory rate limiter middleware for request paths.
- app/main.py — middleware registration includes RateLimitMiddleware with configured request caps and window.

Important note:
- This is an in-memory middleware, not a Redis-backed per-user rate limiter in the current codebase.

## 6) Existing error handling and logging conventions

Error handling:
- app/core/error_handlers.py — centralized FastAPI exception handlers for AppException, validation, JSON parsing, HTTPException, generic exceptions.
- app/core/exceptions.py — custom app exceptions (including AIProviderError, AuthenticationError, InsufficientCreditsError).

Logging:
- app/core/logging_config.py — structured logging setup, file handlers, and sensitive field masking.
- app/main.py — calls setup_logging(env=settings.APP_ENV) during app startup.

Request context and API logging:
- app/middleware/api_logger.py — request logging middleware.
- app/middleware/request_context.py — request context propagation for request_id.

## 7) Existing test setup

Pytest configuration:
- pytest.ini — root pytest config with testpaths = tests and warning filters.

Existing tests and fixtures:
- tests/ — repository tests covering AI service, rate limiting, Redis chat memory, MCP, OAuth, search integration, etc.
- Representative files:
  - tests/test_rate_limit_middleware.py
  - tests/test_redis_chat_memory.py
  - tests/test_mcp_custom.py
  - tests/test_search_integration.py
  - tests/test_persistent_user_skills.py
  - tests/test_oauth_login_endpoints.py
  - tests/test_error_handling.py

Mocked providers / test patterns:
- The repo uses direct provider classes and environment-based configuration; there is no evidence of a dedicated command-system test harness yet.
- Several tests check provider logic and route behavior with mocked or isolated dependencies rather than a full command registry abstraction.

## 8) Direct observations relevant to the command system spec

What appears to already exist and can be reused without duplication:
- Auth dependency pattern: app.routers.auth.get_current_user_auth.
- DB/session initialization: app.db.session.init_db + get_session.
- Redis: app.services.redis_client.RedisClient.
- Search router: app.services.search_router.SearchRouter.
- Media search wrappers: app.routers.media_search and app.services.media_search.*.
- MCP integration: app.services.mcp.* and app.routers.mcp_custom.
- Skills APIs: app.routers.custom_skills plus persistent user skills.
- User-scoped auth enforcement is already a repo pattern: user id is derived from current auth dependency, not from client input.

What does not appear to exist yet in the current backend scan:
- Command registry / parser module under app/core/commands/
- Skills/agents/tools registry model layout described in the prompt
- Dedicated command command parsing endpoints under app/api/v1/routes/
- SSE/WS streaming event transport with the specific command.started / agent.started / tool.started event names
- Agent tracking tables named commands, skills, agents, agent_runs, tool_runs under the current ORM structure
- A pre-existing /api/v1/commands endpoint or command registry in the app

## 9) Conclusion for Phase 0

The real backend already contains a broad set of reusable building blocks for auth, database, Redis, search, MCP, provider routing, wallet/credit logic, and tests. However, the command-layer architecture described in the prompt (command registry, parser, skill registry, agent registry, tool registry, agent/tool execution tracking, and SSE streaming events) is not yet present as a concrete implementation in this repository scan.

This means the safe next step is to build the command system on top of the existing repo patterns, not to invent a parallel architecture.
