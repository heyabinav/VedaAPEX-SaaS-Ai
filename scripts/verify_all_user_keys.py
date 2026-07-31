import re
import requests
import json
import os
from pathlib import Path
from urllib.parse import urlparse

BASE = Path(__file__).resolve().parent.parent
ENV_FILE = BASE / 'user_keys.env'
REPORT_DIR = BASE / 'reports'
REPORT_DIR.mkdir(exist_ok=True)

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

# Helpers
MASK = lambda s: (s[:6] + '...' + s[-6:]) if s and len(s) > 12 else ('(not set)' if not s else s)
results = {}
invalid = []

# Provider-specific tests
session = requests.Session()
session.headers.update({'User-Agent': 'veda-key-verifier/1.0'})
TIMEOUT = 8

# Supabase
if 'SUPABASE_URL' in env:
    url = env['SUPABASE_URL'].rstrip('/') + '/'
    try:
        r = session.get(url, timeout=TIMEOUT)
        ok = r.status_code < 500
        reason = f'Status {r.status_code}'
    except Exception as e:
        ok = False
        reason = str(e)
    kname = 'SUPABASE'
    results[kname] = {'masked': MASK(env.get('SUPABASE_URL','')),'valid': ok,'detail': reason}
    if not ok:
        invalid.append({'name':kname,'masked':MASK(env.get('SUPABASE_URL','')),'reason':reason})

# Gemini
if 'GEMINI_API_KEY' in env and env['GEMINI_API_KEY']:
    try:
        r = session.get('https://generativelanguage.googleapis.com/v1beta/models', params={'key': env['GEMINI_API_KEY']}, timeout=TIMEOUT)
        ok = r.status_code == 200
        reason = f'Status {r.status_code}'
    except Exception as e:
        ok = False
        reason = str(e)
    results['GEMINI'] = {'masked': MASK(env.get('GEMINI_API_KEY')),'valid': ok,'detail': reason}
    if not ok:
        invalid.append({'name':'GEMINI','masked':MASK(env.get('GEMINI_API_KEY')),'reason':reason})

# NASA
if 'NASA_API_KEY' in env:
    try:
        r = session.get('https://api.nasa.gov/planetary/apod', params={'api_key': env['NASA_API_KEY']}, timeout=TIMEOUT)
        ok = r.status_code == 200
        reason = f'Status {r.status_code}'
    except Exception as e:
        ok = False
        reason = str(e)
    results['NASA'] = {'masked': MASK(env.get('NASA_API_KEY')),'valid': ok,'detail': reason}
    if not ok:
        invalid.append({'name':'NASA','masked':MASK(env.get('NASA_API_KEY')),'reason':reason})

# Replicate
for k in list(env.keys()):
    if k.startswith('REPLICATE') and env[k]:
        try:
            r = session.get('https://api.replicate.com/v1/models', headers={'Authorization': f"Token {env[k]}"}, timeout=TIMEOUT)
            ok = r.status_code == 200
            reason = f'Status {r.status_code}'
        except Exception as e:
            ok = False
            reason = str(e)
        results[k] = {'masked': MASK(env[k]),'valid': ok,'detail': reason}
        if not ok:
            invalid.append({'name':k,'masked':MASK(env[k]),'reason':reason})

# HuggingFace
for k in list(env.keys()):
    if 'HUGGINGFACE' in k or k.startswith('HF_') or k.startswith('HUGGINGFACE'):
        if not env[k]:
            results[k] = {'masked': MASK(env[k]),'valid': None,'detail':'not set'}
            continue
        try:
            r = session.get('https://api-inference.huggingface.co/models', headers={'Authorization': f"Bearer {env[k]}"}, timeout=TIMEOUT)
            ok = r.status_code == 200
            reason = f'Status {r.status_code}'
        except Exception as e:
            ok = False
            reason = str(e)
        results[k] = {'masked': MASK(env[k]),'valid': ok,'detail':reason}
        if not ok:
            invalid.append({'name':k,'masked':MASK(env[k]),'reason':reason})

# GROQ
for k in list(env.keys()):
    if 'GROQ' in k or k.startswith('GROQ'):
        if not env[k]:
            results[k] = {'masked': MASK(env[k]),'valid': None,'detail':'not set'}
            continue
        try:
            r = session.get('https://api.groq.com/openai/v1/models', headers={'Authorization': f"Bearer {env[k]}"}, timeout=TIMEOUT)
            ok = r.status_code == 200
            reason = f'Status {r.status_code}'
        except Exception as e:
            ok = False
            reason = str(e)
        results[k] = {'masked': MASK(env[k]),'valid': ok,'detail':reason}
        if not ok:
            invalid.append({'name':k,'masked':MASK(env[k]),'reason':reason})

# OpenAI
for k in list(env.keys()):
    if 'OPENAI' in k:
        if not env[k]:
            results[k] = {'masked': MASK(env[k]),'valid': None,'detail':'not set'}
            continue
        try:
            r = session.get('https://api.openai.com/v1/models', headers={'Authorization': f"Bearer {env[k]}"}, timeout=TIMEOUT)
            ok = r.status_code == 200
            reason = f'Status {r.status_code}'
        except Exception as e:
            ok = False
            reason = str(e)
        results[k] = {'masked': MASK(env[k]),'valid': ok,'detail':reason}
        if not ok:
            invalid.append({'name':k,'masked':MASK(env[k]),'reason':reason})

# Generic heuristic checks for other keys (format-based)
prefix_checks = [
    ('sk-', 'OpenAI-like (sk-)'),
    ('hf_', 'HuggingFace-like (hf_)'),
    ('r8_', 'Replicate-like (r8_)'),
    ('gsk_', 'GROQ-like (gsk_)'),
    ('SG_', 'Segmind-like (SG_)'),
    ('tgp_v1_', 'TogetherAI-like (tgp_v1_)'),
    ('vk-', 'ImagenArt-like (vk-)'),
    ('sk-free', 'FreeAPI-like (sk-free)'),
]

for k,v in env.items():
    if k in results:
        continue
    # Skip DB URLs and secrets
    if 'DATABASE_URL' in k or 'SECRET' in k or k.endswith('_URL'):
        continue
    if not v:
        results[k] = {'masked':MASK(v),'valid':None,'detail':'not set'}
        continue
    # check known prefixes
    pref = next((desc for p,desc in prefix_checks if v.startswith(p)), None)
    if pref:
        results[k] = {'masked':MASK(v),'valid':'format_ok','detail':pref}
        continue
    # fallback: mark as format-only
    results[k] = {'masked':MASK(v),'valid':'unknown','detail':'format-only check applied'}

# Write reports
with open(REPORT_DIR / 'key_verification_report.json', 'w', encoding='utf-8') as f:
    json.dump({'summary':{'total':len(results),'invalid_count':len(invalid)},'results':results,'invalid':invalid}, f, indent=2)

# Create human-readable invalid list
with open(REPORT_DIR / 'invalid_keys.md', 'w', encoding='utf-8') as f:
    f.write('# Invalid API Keys Report\n\n')
    if not invalid:
        f.write('All tested keys appear valid or were format-checked.\n')
    else:
        for item in invalid:
            f.write(f"- **{item['name']}**: {item['masked']} — {item['reason']}\n")

print('Report written to', REPORT_DIR)
