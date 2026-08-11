import os
import sys
import types
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

pkg = types.ModuleType('mcp')
sys.modules['mcp'] = pkg
sys.modules['mcp.client'] = types.ModuleType('mcp.client')
sys.modules['mcp.client.streamable_http'] = types.ModuleType('mcp.client.streamable_http')
sys.modules['mcp.client.sse'] = types.ModuleType('mcp.client.sse')
sys.modules['mcp.client.streamable_http'].streamablehttp_client = lambda *a, **k: None
sys.modules['mcp.client.sse'].sse_client = lambda *a, **k: None
sys.modules['mcp'].ClientSession = type('ClientSession', (), {})
from app.main import app


def expand(routes):
    for r in routes:
        if type(r).__name__ == '_IncludedRouter':
            yield from expand(r.effective_candidates())
        elif hasattr(r, 'methods') and hasattr(r, 'path'):
            yield r
        elif hasattr(r, 'routes'):
            yield from expand(r.routes)


seen = set()
lines = []
for r in sorted(expand(app.routes), key=lambda x: x.path):
    if r.path in seen:
        continue
    seen.add(r.path)
    lines.append(f"{sorted(list(r.methods))} {r.path}")
print('\n'.join(lines))
