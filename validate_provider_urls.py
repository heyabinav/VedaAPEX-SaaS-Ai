import glob
import re
import pathlib
import httpx

pattern = re.compile(r"https?://[A-Za-z0-9/._\-?=&%]+")
files = sorted(glob.glob("app/services/providers/*.py"))
unique = {}
for path in files:
    text = pathlib.Path(path).read_text(encoding="utf-8")
    for m in pattern.finditer(text):
        u = m.group(0)
        if "{" in u or "}" in u:
            continue
        unique.setdefault(u, []).append(path)

client = httpx.Client(timeout=10.0, follow_redirects=True, verify=True)
print(f"Checking {len(unique)} unique URLs from {len(files)} provider files")
for url, paths in sorted(unique.items()):
    try:
        resp = client.head(url)
        status = resp.status_code
        reason = resp.reason_phrase
        ok = status in (200, 301, 302, 303, 307, 308, 401, 403, 405)
        if not ok and status == 404:
            try:
                resp2 = client.get(url)
                status = resp2.status_code
                reason = resp2.reason_phrase
                ok = status in (200, 301, 302, 303, 307, 308, 401, 403, 405)
            except Exception as e:
                reason = f"GETERR {type(e).__name__}: {e}"
        print(("OK " if ok else "BAD") + f" {status or 'ERR'} {url} | {reason} | files={len(paths)}")
    except Exception as e:
        print(f"BAD ERR {url} | {type(e).__name__}: {e} | files={len(paths)}")
