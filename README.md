# VedaApex MCP Server

This backend now runs as a FastAPI application with an MCP layer added on top. Your original REST routes continue to work, and Claude can call the same backend through MCP tools.

## What changed

- Existing FastAPI routes remain available at the original REST endpoints.
- MCP endpoints are exposed at `/mcp` for HTTP transport and `/sse` for SSE transport.
- Search, health, and chat endpoints are exposed as MCP tools.

## Installation

```bash
cd c:/Users/heyhi/Downloads/backend
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
```

## Configuration

Copy the sample environment file and adjust the values:

```bash
copy .env.example .env
```

Important variables:

```bash
APP_NAME=VedaApex Search Aggregation
APP_VERSION=1.0.0
APP_ENV=development
PORT=7860
HOST=0.0.0.0

PEXELS_API_KEY=your_pexels_key_here
NASA_API_KEY=DEMO_KEY
WIKIMEDIA_API_KEY=

MCP_HTTP_PATH=/mcp
MCP_SSE_PATH=/sse
```

## Run the server

```bash
.\.venv\Scripts\python.exe main.py
```

The API will be available at:

- REST docs: http://localhost:7860/api/v1/docs
- MCP HTTP: http://localhost:7860/mcp
- MCP SSE: http://localhost:7860/sse

## Test MCP locally

```bash
curl http://localhost:7860/api/v1/health
curl http://localhost:7860/mcp
```

You can also run the test suite:

```bash
.\.venv\Scripts\python.exe -m pytest -q test_mcp.py
```

## MCP tools available

- `health_check` — returns service health and enabled providers
- `unified_search` — runs the main intelligent search workflow
- `browser_search` — runs the browser-style search helper
- `chat` — sends a chat request to the configured LLM provider

## Claude Desktop configuration

Use this configuration in your Claude Desktop config file:

```json
{
  "mcpServers": {
    "vedaapex": {
      "type": "streamable-http",
      "url": "http://localhost:7860/mcp"
    }
  }
}
```

If you prefer SSE instead of HTTP transport, use:

```json
{
  "mcpServers": {
    "vedaapex": {
      "type": "sse",
      "url": "http://localhost:7860/sse"
    }
  }
}
```

## Notes

- Your existing REST API behavior is preserved.
- Authentication headers are forwarded for tool calls when present.
- If an endpoint needs an API key, pass it through the request headers or environment variables used by the app.


### Docker
```bash
docker build -t vedaapex-search . && docker run -p 7860:7860 vedaapex-search
```

### Render
See [DEPLOYMENT.md](DEPLOYMENT.md) for cloud deployment guides.

---

## ❓ FAQ

**Q: Can I add my own provider?**  
A: Yes! Create a provider class and add to `providers/`. The router will automatically include it.

**Q: How are conflicts handled (space + scientific)?**  
A: Primary provider is chosen based on which category matches first.

**Q: What if all providers fail?**  
A: Returns empty results with error details in logs.

**Q: Can I disable a provider?**  
A: Yes, set `ENABLE_PEXELS=false` in .env

---

**Built for intelligent search! 🧠✨**

Check out the configuration reference at https://huggingface.co/docs/hub/spaces-config-reference
