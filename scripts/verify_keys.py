import requests
import json
import os
from urllib.parse import urljoin

# Keys are read from the environment and masked when printed.
ENV = {
    "SUPABASE_URL": os.getenv("SUPABASE_URL", ""),
    "SUPABASE_ANON_KEY": os.getenv("SUPABASE_ANON_KEY", ""),
    "SUPABASE_SERVICE_ROLE_KEY": os.getenv("SUPABASE_SERVICE_ROLE_KEY", ""),
    "GEMINI_API_KEY": os.getenv("GEMINI_API_KEY", ""),
    "NASA_API_KEY": os.getenv("NASA_API_KEY", "DEMO_KEY"),
    "OPENAI_API_KEY": os.getenv("OPENAI_API_KEY", ""),
    "REPLICATE_API_KEY": os.getenv("REPLICATE_API_KEY", ""),
    "HUGGINGFACE_API_KEY": os.getenv("HUGGINGFACE_API_KEY", ""),
    "GROQ_API_KEY": os.getenv("GROQ_API_KEY", ""),
}

MASK = lambda s: (s[:6] + '...' + s[-6:]) if s else '(not set)'

results = {}

# 1) Supabase basic checks: reachable and keys JWT-like
try:
    url = ENV["SUPABASE_URL"].rstrip('/') + '/'
    r = requests.get(url, timeout=8)
    reachable = r.status_code < 500
except Exception as e:
    reachable = False

anon = ENV.get("SUPABASE_ANON_KEY","")
service = ENV.get("SUPABASE_SERVICE_ROLE_KEY","")

results['supabase'] = {
    'url': ENV['SUPABASE_URL'],
    'reachable': reachable,
    'anon_key_format_ok': len(anon.split('.')) == 3,
    'service_key_format_ok': len(service.split('.')) == 3,
}

# 2) Gemini (Google Generative Language) - try list models
try:
    gem_key = ENV.get('GEMINI_API_KEY')
    r = requests.get('https://generativelanguage.googleapis.com/v1beta/models', params={'key': gem_key}, timeout=10)
    gem_valid = r.status_code == 200
    gem_status = r.status_code
except Exception as e:
    gem_valid = False
    gem_status = str(e)
results['gemini'] = {'masked_key': MASK(ENV.get('GEMINI_API_KEY','')),'valid':gem_valid,'status':gem_status}

# 3) NASA - test APOD
try:
    r = requests.get('https://api.nasa.gov/planetary/apod', params={'api_key': ENV.get('NASA_API_KEY')}, timeout=8)
    nasa_valid = r.status_code == 200
    nasa_status = r.status_code
except Exception as e:
    nasa_valid = False
    nasa_status = str(e)
results['nasa'] = {'masked_key': MASK(ENV.get('NASA_API_KEY','')),'valid':nasa_valid,'status':nasa_status}

# 4) OpenAI - if present
if ENV.get('OPENAI_API_KEY'):
    try:
        r = requests.get('https://api.openai.com/v1/models', headers={'Authorization': f"Bearer {ENV['OPENAI_API_KEY']}"}, timeout=8)
        openai_valid = r.status_code == 200
        openai_status = r.status_code
    except Exception as e:
        openai_valid = False
        openai_status = str(e)
else:
    openai_valid = None
    openai_status = 'not set'
results['openai'] = {'masked_key': MASK(ENV.get('OPENAI_API_KEY','')),'valid':openai_valid,'status':openai_status}

# 5) Replicate - list models
try:
    r = requests.get('https://api.replicate.com/v1/models', headers={'Authorization': f"Token {ENV.get('REPLICATE_API_KEY','')}", 'User-Agent':'verify-script'}, timeout=10)
    rep_valid = r.status_code == 200
    rep_status = r.status_code
except Exception as e:
    rep_valid = False
    rep_status = str(e)
results['replicate'] = {'masked_key': MASK(ENV.get('REPLICATE_API_KEY','')),'valid':rep_valid,'status':rep_status}

# 6) HuggingFace - list models (requires Bearer)
try:
    hf_key = ENV.get('HUGGINGFACE_API_KEY')
    r = requests.get('https://api-inference.huggingface.co/models', headers={'Authorization': f"Bearer {hf_key}"}, timeout=10)
    hf_valid = r.status_code == 200
    hf_status = r.status_code
except Exception as e:
    hf_valid = False
    hf_status = str(e)
results['huggingface'] = {'masked_key': MASK(ENV.get('HUGGINGFACE_API_KEY','')),'valid':hf_valid,'status':hf_status}

# 7) GROQ - simple call to openai compatibility endpoint
try:
    groq_key = ENV.get('GROQ_API_KEY')
    r = requests.get('https://api.groq.com/openai/v1/models', headers={'Authorization': f"Bearer {groq_key}"}, timeout=10)
    groq_valid = r.status_code == 200
    groq_status = r.status_code
except Exception as e:
    groq_valid = False
    groq_status = str(e)
results['groq'] = {'masked_key': MASK(ENV.get('GROQ_API_KEY','')),'valid':groq_valid,'status':groq_status}

# 8) Gemini sample generation (small prompt)
gen_output = None
try:
    gem_key = ENV.get('GEMINI_API_KEY')
    if gem_key:
        model = 'gemini-2.0-flash'
        endpoint = f'https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent'
        contents = [{"role":"user","parts":[{"text":"Say 'Hello' in Hindi and give a 1-sentence greeting."}]}]
        payload = {
            "system_instruction": {"parts": [{"text": "You are a helpful assistant."}]},
            "contents": contents,
        }
        r = requests.post(endpoint, params={'key': gem_key}, json=payload, timeout=15)
        if r.status_code == 200:
            data = r.json()
            # extract text
            gen_text = ''
            for candidate in data.get('candidates', []):
                parts = candidate.get('content', {}).get('parts', [])
                for p in parts:
                    gen_text += p.get('text','')
            gen_output = gen_text or str(data)
        else:
            gen_output = f'Error {r.status_code}: {r.text[:200]}'
    else:
        gen_output = 'gemini key not set'
except Exception as e:
    gen_output = f'exception: {e}'

results['gemini_sample'] = {'masked_key': MASK(ENV.get('GEMINI_API_KEY','')), 'output': gen_output}

print(json.dumps(results, indent=2))
