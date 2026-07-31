"""Google OAuth scopes - least-privilege configuration."""

GOOGLE_AUTH_SCOPES = [
    "openid",
    "email",
    "profile",
    "https://www.googleapis.com/auth/gmail.readonly",
    "https://www.googleapis.com/auth/gmail.send",
    "https://www.googleapis.com/auth/gmail.modify",
    "https://www.googleapis.com/auth/drive",
    "https://www.googleapis.com/auth/documents",
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/presentations",
    "https://www.googleapis.com/auth/calendar",
    "https://www.googleapis.com/auth/contacts.readonly",
]

GOOGLE_AUTH_URL = "https://accounts.google.com/o/oauth2/v2/auth"
GOOGLE_TOKEN_URL = "https://oauth2.googleapis.com/token"
GOOGLE_REVOKE_URL = "https://oauth2.googleapis.com/revoke"

GOOGLE_API_BASE = "https://www.googleapis.com"
GMAIL_API = f"{GOOGLE_API_BASE}/gmail/v1"
DRIVE_API = f"{GOOGLE_API_BASE}/drive/v3"
DOCS_API = f"{GOOGLE_API_BASE}/docs/v1"
SHEETS_API = f"{GOOGLE_API_BASE}/sheets/v4"
SLIDES_API = f"{GOOGLE_API_BASE}/slides/v1"
CALENDAR_API = f"{GOOGLE_API_BASE}/calendar/v3"
PEOPLE_API = f"{GOOGLE_API_BASE}/people/v1"
