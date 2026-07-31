import re
import requests
import json
from pathlib import Path

BASE = Path(__file__).resolve().parent.parent
ENV_FILE = BASE / 'user_keys.env'
REPORT_DIR = BASE / 'reports'
REPORT_DIR.mkdir(exist_ok=True)
OUT = REPORT_DIR / 'tiered_key_report.md'

# Load env-like file
env = {}
with open(ENV_FILE, 'r', encoding='utf-8') as f:
    for line in f:
        line = line.strip()
        if not line or line.startswith('#'):
            continue
        if '=' in line:
            k, v = line.split('=', 1)
            v = v.strip().strip('"').strip("'")
            env[k.strip()] = v

# Group keys by provider base
providers = {}
for k, v in env.items():
    # match patterns like PNAME_API_KEY_TIERn or PNAME_API_KEY or PNAME_KEY
    m = re.match(r'^([A-Z0-9]+?)(?:_API_KEY(?:_TIER(\d+))?|_API_KEY|_KEY(?:_TIER(\d+))?)(_.*)?$', k)
    if m:
        base = m.group(1)
        tier = m.group(2) or m.group(3) or 'PERM'
        providers.setdefault(base, []).append((k, tier, v))
    else:
        # fallback: group by first token before first underscore
        base = k.split('_')[0]
        providers.setdefault(base, []).append((k, 'PERM', v))

# helpers
MASK = lambda s: (s[:6] + '...' + s[-6:]) if s and len(s) > 12 else ('(not set)' if not s else s)
TIMEOUT = 8
session = requests.Session()
session.headers.update({'User-Agent': 'veda-tiered-verifier/1.0'})

results = {}

for base, items in sorted(providers.items()):
    results[base] = []
    for name, tier, val in sorted(items, key=lambda x: x[1]):
        status = 'FORMAT-ONLY'
        reason = ''
        valid = None
        if not val:
            status = 'NOT SET'
            reason = 'Empty value'
            results[base].append((name, tier, MASK(val), status, reason))
            continue
        # provider-specific checks
        try:
            if base in ('REPLICATE', 'REPLICATE_API') or name.startswith('REPLICATE'):
                r = session.get('https://api.replicate.com/v1/models', headers={'Authorization': f"Token {val}"}, timeout=TIMEOUT)
                valid = r.status_code == 200
                status = 'OK' if valid else 'FAIL'
                reason = f'Status {r.status_code}'
            elif base in ('GEMINI',):
                r = session.get('https://generativelanguage.googleapis.com/v1beta/models', params={'key': val}, timeout=TIMEOUT)
                valid = r.status_code == 200
                status = 'OK' if valid else 'FAIL'
                reason = f'Status {r.status_code}'
            elif base in ('GROQ',):
                r = session.get('https://api.groq.com/openai/v1/models', headers={'Authorization': f'Bearer {val}'}, timeout=TIMEOUT)
                valid = r.status_code == 200
                status = 'OK' if valid else 'FAIL'
                reason = f'Status {r.status_code}'
            elif base in ('HUGGINGFACE', 'HUGGINGFACE_API', 'HF'):
                r = session.get('https://api-inference.huggingface.co/models', headers={'Authorization': f'Bearer {val}'}, timeout=TIMEOUT)
                valid = r.status_code == 200
                status = 'OK' if valid else 'FAIL'
                reason = f'Status {r.status_code}'
            elif base in ('OPENAI', 'OPENAI_API'):
                r = session.get('https://api.openai.com/v1/models', headers={'Authorization': f'Bearer {val}'}, timeout=TIMEOUT)
                valid = r.status_code == 200
                status = 'OK' if valid else 'FAIL'
                reason = f'Status {r.status_code}'
            elif base in ('NASA',):
                r = session.get('https://api.nasa.gov/planetary/apod', params={'api_key': val}, timeout=TIMEOUT)
                valid = r.status_code == 200
                status = 'OK' if valid else 'FAIL'
                reason = f'Status {r.status_code}'
            elif base in ('SUPABASE',):
                # check URL and token formats
                url = env.get('SUPABASE_URL')
                ok = bool(url)
                status = 'OK' if ok else 'FAIL'
                reason = 'SUPABASE_URL present' if ok else 'SUPABASE_URL missing'
            else:
                # format heuristic
                pref_checks = ['sk-', 'hf_', 'r8_', 'gsk_', 'SG_', 'tgp_v1_', 'vk-', 'sk-free', 'sb_publishable_']
                pref = next((p for p in pref_checks if val.startswith(p)), None)
                if pref:
                    status = 'FORMAT-OK'
                    reason = f'Prefix matches {pref}'
                else:
                    status = 'UNKNOWN'
                    reason = 'No provider check available; format-only'
        except Exception as e:
            status = 'ERROR'
            reason = str(e)
        results[base].append((name, tier, MASK(val), status, reason))

# write markdown
with open(OUT, 'w', encoding='utf-8') as f:
    f.write('# Tiered API Key Verification Report\n\n')
    for base, rows in results.items():
        f.write(f'## {base}\n\n')
        f.write('| Key Name | Tier | Key (masked) | Status | Reason |\n')
        f.write('|---|---:|---|---|---|\n')
        for name, tier, masked, status, reason in rows:
            f.write(f'| {name} | {tier} | {masked} | {status} | {reason} |\n')
        f.write('\n')

print('Wrote', OUT)
