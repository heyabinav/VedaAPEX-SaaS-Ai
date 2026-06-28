# 🔐 OAuth Setup & Testing Guide (Google + GitHub)

## ✅ Implementation Status

All required components are implemented and connected:

- ✅ **Provider-specific credentials** - Google and GitHub separate
- ✅ **Token exchange** - Server-side with correct credentials
- ✅ **User normalization** - Google and GitHub data handled correctly
- ✅ **User creation/update** - Auto-create on first login
- ✅ **Session management** - Secure JWT cookies
- ✅ **Error handling** - Complete error flows
- ✅ **Logging** - Comprehensive debug logging

---

## 📋 Pre-Setup Checklist

### **1. Supabase Configuration**

```
✓ Supabase project created
✓ Project URL: https://xxx.supabase.co
✓ Anon key: eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...
✓ Service role key: eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...
```

#### **Enable OAuth Providers in Supabase Console:**

Go to: **Supabase Dashboard → Authentication → Providers**

**For Google:**
- [ ] Click "Google" 
- [ ] Toggle "Enabled"
- [ ] Add your Google OAuth credentials
- [ ] Set Redirect URL: `https://api.yourdomain.com/auth/callback`

**For GitHub:**
- [ ] Click "GitHub"
- [ ] Toggle "Enabled"
- [ ] Add your GitHub OAuth credentials
- [ ] Set Redirect URL: `https://api.yourdomain.com/auth/callback`

---

### **2. Google OAuth Setup**

#### **Get Google Credentials:**

1. Go to [Google Cloud Console](https://console.cloud.google.com)
2. Create a new project or select existing
3. Go to **APIs & Services → Credentials**
4. Click **"Create Credentials" → "OAuth 2.0 Client ID"**
5. Choose **"Web application"**
6. Add Authorized redirect URIs:
   - `https://your-project.supabase.co/auth/v1/callback` (Supabase)
   - `https://api.yourdomain.com/auth/callback` (Your app callback)
7. Copy:
   - **Client ID** → `GOOGLE_OAUTH_CLIENT_ID`
   - **Client Secret** → `GOOGLE_OAUTH_CLIENT_SECRET`

#### **In Supabase Console:**
- Go to **Authentication → Providers → Google**
- Paste Client ID and Secret
- Save

#### **In Render (Backend Service):**
```
GOOGLE_OAUTH_CLIENT_ID = <paste-client-id>
GOOGLE_OAUTH_CLIENT_SECRET = <paste-secret> [Mark as SECRET]
```

---

### **3. GitHub OAuth Setup**

#### **Get GitHub Credentials:**

1. Go to [GitHub Settings → Developer applications](https://github.com/settings/developers)
2. Click **"New OAuth App"**
3. Fill form:
   - **Application name**: YourApp OAuth
   - **Homepage URL**: `https://app.yourdomain.com`
   - **Authorization callback URL**: `https://your-project.supabase.co/auth/v1/callback`
4. Click **"Register application"**
5. Go to **Settings → OAuth apps → Your App**
6. Copy:
   - **Client ID** → `GITHUB_OAUTH_CLIENT_ID`
   - **Client Secret** → `GITHUB_OAUTH_CLIENT_SECRET` (Generate new if needed)

#### **In Supabase Console:**
- Go to **Authentication → Providers → GitHub**
- Paste Client ID and Secret
- Save

#### **In Render (Backend Service):**
```
GITHUB_OAUTH_CLIENT_ID = <paste-client-id>
GITHUB_OAUTH_CLIENT_SECRET = <paste-secret> [Mark as SECRET]
```

---

## 🌐 Render Environment Variables (Complete List)

Add all these to your Render backend service:

### **Supabase:**
```
SUPABASE_URL = https://your-project-ref.supabase.co
SUPABASE_ANON_KEY = eyJhbGciOi...
SUPABASE_SERVICE_ROLE_KEY = eyJhbGciOi... (SECRET)
SUPABASE_TIMEOUT_SECONDS = 15
```

### **Google OAuth:**
```
GOOGLE_OAUTH_CLIENT_ID = 123456789-abc.apps.googleusercontent.com
GOOGLE_OAUTH_CLIENT_SECRET = GOCSPX-xxxxx (SECRET)
```

### **GitHub OAuth:**
```
GITHUB_OAUTH_CLIENT_ID = Iv1.abcdef123456
GITHUB_OAUTH_CLIENT_SECRET = ghp_xxxxxxxxxx (SECRET)
```

### **App Configuration:**
```
APP_BASE_URL = https://api.yourdomain.com
FRONTEND_BASE_URL = https://app.yourdomain.com
APP_ENV = production
```

### **Session Configuration:**
```
SESSION_COOKIE_NAME = vedaapex_session
SESSION_COOKIE_MAX_AGE = 604800
SESSION_COOKIE_SECURE = true
SESSION_COOKIE_SAMESITE = lax
```

---

## 🚀 Frontend OAuth Initiation URLs

Your frontend should redirect to these URLs when user clicks "Login with Google" or "Login with GitHub":

### **Google Login Button:**
```javascript
const googleAuthUrl = `https://your-project-ref.supabase.co/auth/v1/authorize?provider=google&redirect_to=https://api.yourdomain.com/auth/callback&scopes=openid%20email%20profile&state=google:/welcome`;

// User clicks button → redirect to googleAuthUrl
window.location.href = googleAuthUrl;
```

### **GitHub Login Button:**
```javascript
const githubAuthUrl = `https://your-project-ref.supabase.co/auth/v1/authorize?provider=github&redirect_to=https://api.yourdomain.com/auth/callback&scopes=openid%20email%20profile&state=github:/dashboard`;

// User clicks button → redirect to githubAuthUrl
window.location.href = githubAuthUrl;
```

---

## 🔄 OAuth Flow Diagram

```
User clicks "Login with Google"
         ↓
Frontend redirects to Supabase authorize URL (with state=google:/welcome)
         ↓
User approves permissions at Google
         ↓
Google redirects to: https://api.yourdomain.com/auth/callback?code=...&state=google:/welcome
         ↓
Backend receives callback:
  - Parses state → detects provider=google
  - Extracts redirect_path=/welcome
  - Uses GOOGLE_OAUTH_CLIENT_ID + GOOGLE_OAUTH_CLIENT_SECRET
         ↓
Backend exchanges code for token
         ↓
Backend fetches user info from Supabase
         ↓
Backend normalizes user data (handles Google format)
         ↓
Backend creates/updates user in database:
  - Matches by email (preferred)
  - Or matches by provider + provider_id
  - Stores provider="google"
         ↓
Backend creates JWT token
         ↓
Backend sets secure session cookie (HttpOnly, Secure, SameSite)
         ↓
Backend redirects to: https://app.yourdomain.com/welcome
         ↓
Frontend receives session cookie → User is logged in!
```

---

## 🧪 Testing Endpoints

### **1. Check Callback Endpoint Exists:**
```bash
curl -i "https://api.yourdomain.com/auth/callback"
# Expected: 400 Bad Request - Missing authorization code
```

### **2. Get Current User (after login):**
```bash
curl -i -b "vedaapex_session=<JWT_TOKEN_HERE>" \
  "https://api.yourdomain.com/api/v1/auth/oauth_me"

# Response:
{
  "success": true,
  "data": {
    "id": 123,
    "email": "user@example.com",
    "full_name": "User Name",
    "provider": "google",
    "provider_id": "118...",
    "role": "USER",
    "plan": "free"
  }
}
```

### **3. Check Session Exists:**
```bash
curl -i -b "vedaapex_session=<JWT_TOKEN>" \
  "https://api.yourdomain.com/api/v1/auth/oauth_me" \
  -H "Accept: application/json"
```

### **4. Logout:**
```bash
curl -i -X POST \
  "https://api.yourdomain.com/api/v1/auth/logout"
# Session cookie will be cleared
```

---

## 🔍 Debugging & Logs

When testing, check these logs:

### **Provider Detection:**
```
"Provider detected from state parameter: google"
```

### **Credentials Used:**
```
"Using Google OAuth credentials"  ← means correct credentials loaded
```

### **Token Exchange:**
```
"Exchanging code for token at https://xxx.supabase.co/auth/v1/token"
"Token payload keys: ['access_token', 'token_type', 'expires_in', 'user']"
```

### **User Normalization:**
```
"Normalized user: provider=google email=user@example.com provider_id=118..."
```

### **User Creation:**
```
"Created new local user id=123 email=user@example.com provider=google"
```

### **Session Creation:**
```
"OAuth login success for user_id=123 provider=google redirect=https://app.yourdomain.com/welcome"
```

---

## ❌ Common Issues & Fixes

### **Issue: 400 Missing authorization code**
- **Cause**: Frontend not passing `code` parameter
- **Fix**: Ensure Supabase authorize URL includes `&redirect_to=https://api.yourdomain.com/auth/callback`

### **Issue: Token exchange failed**
- **Cause**: Wrong client ID/secret OR redirect_uri mismatch
- **Fix**: 
  - Double-check credentials in Render
  - Verify Supabase config matches APP_BASE_URL
  - Check redirect URI is exactly `https://api.yourdomain.com/auth/callback`

### **Issue: No user info available**
- **Cause**: Access token invalid OR Supabase /auth/v1/user failed
- **Fix**: Check SUPABASE_ANON_KEY is correct

### **Issue: OAuth credentials not configured**
- **Cause**: Environment variable not set in Render
- **Fix**: 
  - Go to Render → Backend Service → Environment
  - Add GOOGLE_OAUTH_CLIENT_ID, GOOGLE_OAUTH_CLIENT_SECRET, etc.
  - Redeploy

### **Issue: Session cookie not set**
- **Cause**: SESSION_COOKIE_SECURE=true but HTTP (not HTTPS)
- **Fix**: Ensure production has HTTPS enabled

---

## ✨ Code Flow Summary

**File: `app/routers/oauth.py`**
- Receives callback at `/auth/callback`
- Parses state to detect provider
- Calls token exchange with provider-specific credentials

**File: `app/services/supabase_oauth.py`**
- `exchange_code_for_token()` - Uses GOOGLE_OAUTH_CLIENT_* or GITHUB_OAUTH_CLIENT_*
- `fetch_user_from_access_token()` - Gets user from Supabase
- `normalize_supabase_user()` - Normalizes Google/GitHub data

**File: `app/services/oauth_providers/google_oauth.py`**
- `GoogleOAuth.normalize()` - Handles Google user format

**File: `app/services/oauth_providers/github_oauth.py`**
- `GithubOAuth.normalize()` - Handles GitHub user format

---

## 🎯 Success Criteria

You'll know it's working when:

1. ✅ Frontend can redirect to Google/GitHub authorize URLs
2. ✅ User clicks approve on Google/GitHub
3. ✅ User gets redirected back to your frontend with session cookie
4. ✅ `/api/v1/auth/oauth_me` returns user data
5. ✅ Provider is stored as "google" or "github"
6. ✅ User can logout and session clears
7. ✅ Second login with same provider finds existing user
8. ✅ Logs show provider-specific credentials were used

---

## 📞 Need Help?

Check:
- ✅ All environment variables set in Render
- ✅ Redirect URIs match exactly in Supabase + Google/GitHub
- ✅ Credentials are correct (copy-paste carefully)
- ✅ HTTPS is enabled in production
- ✅ Check Render logs for error messages
