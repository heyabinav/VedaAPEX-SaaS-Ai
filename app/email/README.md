# Email Verification Service

Complete Python-based email verification system using Brevo SMTP for user authentication.

## Features

✅ User registration with email verification
✅ Secure password hashing (bcrypt)
✅ Cryptographically secure tokens
✅ Token expiration handling (24 hours)
✅ Brevo SMTP email delivery
✅ Email verification blocking login
✅ Resend verification email
✅ Login with verification check
✅ Failed login attempt tracking
✅ Account lockout after failed attempts
✅ Input validation
✅ Comprehensive logging
✅ SQLite by default (PostgreSQL ready)

## Project Structure

```
app/email/
├── __init__.py
├── config.py                    # Configuration
├── database.py                  # Database setup
├── models.py                    # Database models
├── README.md
├── services/
│   ├── __init__.py
│   ├── email_service.py        # Brevo SMTP email
│   └── token_service.py        # Token generation
├── routes/
│   ├── __init__.py
│   └── auth.py                 # API endpoints
└── utils/
    ├── __init__.py
    └── validators.py            # Input validation
```

## Installation

### 1. Install Dependencies

```bash
pip install -r requirements.txt
```

Or install individually:

```bash
pip install fastapi
pip install sqlalchemy
pip install sqlalchemy-utils
pip install bcrypt
pip install python-multipart
```

### 2. Environment Variables

Create `.env` file in project root:

```env
# Brevo SMTP (Get from https://www.brevo.com)
BREVO_SMTP_HOST=smtp-relay.brevo.com
BREVO_SMTP_PORT=587
BREVO_SMTP_USERNAME=your-brevo-email@example.com
BREVO_SMTP_PASSWORD=your-brevo-api-key
EMAIL_FROM=noreply@yourdomain.com

# Application
SECRET_KEY=your-secret-key-change-in-production
DATABASE_URL=sqlite:///./email_verification.db
APP_BASE_URL=http://localhost:8000
APP_ENV=development
```

### 3. Initialize Database

```python
from app.email.database import init_db

init_db()
```

## API Endpoints

### 1. Register User

**POST** `/api/v1/email/register`

Request:
```json
{
    "email": "user@example.com",
    "username": "johndoe",
    "password": "SecurePass123",
    "full_name": "John Doe"
}
```

Response (201):
```json
{
    "success": true,
    "message": "User registered successfully. Please check your email to verify your account.",
    "user": {
        "id": 1,
        "email": "user@example.com",
        "username": "johndoe",
        "full_name": "John Doe",
        "is_email_verified": false,
        "created_at": "2024-01-15T10:30:00"
    }
}
```

### 2. Login User

**POST** `/api/v1/email/login`

Request:
```json
{
    "email": "user@example.com",
    "password": "SecurePass123"
}
```

Response (200):
```json
{
    "success": true,
    "message": "Login successful",
    "user": {
        "id": 1,
        "email": "user@example.com",
        "username": "johndoe",
        "is_email_verified": true,
        "last_login_at": "2024-01-15T10:35:00"
    }
}
```

Response (403 - Unverified):
```json
{
    "success": false,
    "message": "Email not verified. Please check your email for verification link."
}
```

### 3. Verify Email

**GET** `/api/v1/email/verify?token=abc123...`

Response (200):
```json
{
    "success": true,
    "message": "Email verified successfully. You can now login.",
    "user": {
        "id": 1,
        "email": "user@example.com",
        "is_email_verified": true,
        "email_verified_at": "2024-01-15T10:32:00"
    }
}
```

### 4. Resend Verification Email

**POST** `/api/v1/email/resend-verification`

Request:
```json
{
    "email": "user@example.com"
}
```

Response (200):
```json
{
    "success": true,
    "message": "Verification email sent successfully. Check your email."
}
```

### 5. Health Check

**GET** `/api/v1/email/health`

Response (200):
```json
{
    "status": "healthy",
    "service": "email-verification",
    "timestamp": "2024-01-15T10:30:00"
}
```

## Usage Example

### 1. Start FastAPI Server

```bash
uvicorn app.main:app --reload
```

### 2. Register User via cURL

```bash
curl -X POST "http://localhost:8000/api/v1/email/register" \
  -H "Content-Type: application/json" \
  -d '{
    "email": "test@example.com",
    "username": "testuser",
    "password": "TestPass123",
    "full_name": "Test User"
  }'
```

### 3. Check Email for Verification Link

Link format: `http://localhost:8000/api/v1/email/verify?token=<TOKEN>`

### 4. Verify Email via Link

```bash
curl -X GET "http://localhost:8000/api/v1/email/verify?token=abc123def456"
```

### 5. Login After Verification

```bash
curl -X POST "http://localhost:8000/api/v1/email/login" \
  -H "Content-Type: application/json" \
  -d '{
    "email": "test@example.com",
    "password": "TestPass123"
  }'
```

## Configuration

### EmailConfig (config.py)

```python
# Email Settings
VERIFICATION_TOKEN_EXPIRY = timedelta(hours=24)  # Token expires in 24 hours
VERIFICATION_TOKEN_LENGTH = 32                   # Token length in bytes
PASSWORD_MIN_LENGTH = 8                          # Minimum password length
MAX_LOGIN_ATTEMPTS = 5                           # Max failed attempts before lockout
LOGIN_ATTEMPT_TIMEOUT = timedelta(minutes=15)   # Lockout duration
RESEND_EMAIL_COOLDOWN = timedelta(minutes=5)    # Cooldown between resends
```

## Security Features

### 1. Password Security
- Bcrypt hashing (salted)
- Minimum 8 characters
- Must contain uppercase, lowercase, digits
- Maximum 128 characters

### 2. Token Security
- Cryptographically secure tokens (secrets module)
- 24-hour expiration
- Single-use (cleared after verification)
- Cannot be reused

### 3. Login Security
- Failed attempt tracking
- Account lockout (5 attempts)
- Email verification required for login
- Timestamp tracking

### 4. Email Security
- SMTP TLS encryption
- Secure credential storage (environment variables)
- Verification token in URL (not in email body)
- Proper MIME types and encoding

### 5. Input Validation
- Email format validation
- Username format (alphanumeric, 3-20 chars)
- Password strength requirements
- Length constraints
- SQL injection prevention (SQLAlchemy ORM)

## Database

### SQLite (Default)
```
DATABASE_URL=sqlite:///./email_verification.db
```

### PostgreSQL (Production)
```
DATABASE_URL=postgresql://user:password@localhost/dbname
```

No code changes required - just update DATABASE_URL!

## Logging

Logs are written to console and include:
- User registration events
- Email send events
- Verification events
- Login attempts
- Errors and warnings

Example:
```
✅ User registered: user@example.com
✅ Email sent successfully to user@example.com
✅ Email verified: user@example.com
✅ Successful login: user@example.com
```

## Error Handling

| Status | Error | Solution |
|--------|-------|----------|
| 400 | Invalid email format | Use valid email format |
| 400 | Password too weak | Use stronger password |
| 409 | Email already registered | Use different email |
| 401 | Invalid credentials | Check email/password |
| 403 | Email not verified | Verify email first |
| 403 | Account locked | Too many failed attempts |
| 404 | User not found | Check email address |
| 500 | Server error | Check logs |

## Brevo SMTP Setup

1. Create account at [Brevo](https://www.brevo.com)
2. Go to **Settings → SMTP**
3. Enable SMTP
4. Copy credentials:
   - Email: Your Brevo account email
   - Password: SMTP API key
5. Configure in `.env`:
   ```env
   BREVO_SMTP_USERNAME=your-brevo-email@example.com
   BREVO_SMTP_PASSWORD=your-smtp-api-key
   EMAIL_FROM=noreply@yourdomain.com
   ```

## Production Checklist

- [ ] Use PostgreSQL instead of SQLite
- [ ] Set `APP_ENV=production`
- [ ] Use strong `SECRET_KEY`
- [ ] Enable HTTPS (`APP_BASE_URL=https://...`)
- [ ] Set proper `EMAIL_FROM` domain
- [ ] Configure CORS properly
- [ ] Enable logging to file
- [ ] Set up monitoring/alerting
- [ ] Regular database backups
- [ ] Token rotation strategy
- [ ] Rate limiting on endpoints
- [ ] Security headers on responses

## Testing

### Registration Test
```bash
curl -X POST "http://localhost:8000/api/v1/email/register" \
  -H "Content-Type: application/json" \
  -d '{"email":"test@test.com","username":"testuser","password":"TestPass123"}'
```

### Login Before Verification
```bash
curl -X POST "http://localhost:8000/api/v1/email/login" \
  -H "Content-Type: application/json" \
  -d '{"email":"test@test.com","password":"TestPass123"}'
# Should return 403
```

### Check Health
```bash
curl http://localhost:8000/api/v1/email/health
```

## Troubleshooting

### SMTP Connection Failed
- Check `BREVO_SMTP_HOST` and `BREVO_SMTP_PORT`
- Verify credentials in Brevo dashboard
- Ensure firewall allows port 587
- Check internet connectivity

### Token Generation Failed
- Verify `SECRET_KEY` is set
- Check file permissions on `/logs` directory

### Database Error
- Verify `DATABASE_URL` format
- Check database file permissions
- Ensure SQLite file is writable

### Email Not Received
- Check spam/junk folder
- Verify `EMAIL_FROM` domain
- Check Brevo dashboard for delivery logs
- Test with Brevo's email tester

## License

MIT License - See LICENSE file
