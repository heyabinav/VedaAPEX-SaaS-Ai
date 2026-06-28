#!/usr/bin/env python3
"""
OAuth Implementation Verification Script
Checks if all components are properly connected and configured.
"""

import os
import sys
import asyncio
from pathlib import Path

# Add app to path
sys.path.insert(0, str(Path(__file__).parent))


def check_imports():
    """Verify all OAuth modules import correctly."""
    print("📦 Checking imports...")
    try:
        from app.services.supabase_oauth import (
            exchange_code_for_token,
            detect_provider_from_payload,
            normalize_supabase_user,
            fetch_user_from_access_token,
            SupabaseOAuthError,
        )

        print("  ✅ app.services.supabase_oauth")

        from app.services.oauth_providers.google_oauth import GoogleOAuth

        print("  ✅ app.services.oauth_providers.google_oauth")

        from app.services.oauth_providers.github_oauth import GithubOAuth

        print("  ✅ app.services.oauth_providers.github_oauth")

        from app.routers.oauth import router as oauth_router

        print("  ✅ app.routers.oauth")

        from app.models.user import User

        print("  ✅ app.models.user (has provider fields)")

        from app.core.config import settings

        print("  ✅ app.core.config.settings")

        return True
    except ImportError as e:
        print(f"  ❌ Import failed: {e}")
        return False


def check_model_fields():
    """Verify User model has OAuth fields."""
    print("\n📋 Checking User model...")
    try:
        from app.models.user import User
        from sqlmodel import Session

        user_fields = User.__fields__ if hasattr(User, "__fields__") else User.model_fields

        if "provider" in user_fields:
            print("  ✅ User.provider field exists")
        else:
            print("  ❌ User.provider field missing")
            return False

        if "provider_id" in user_fields:
            print("  ✅ User.provider_id field exists")
        else:
            print("  ❌ User.provider_id field missing")
            return False

        return True
    except Exception as e:
        print(f"  ❌ Model check failed: {e}")
        return False


def check_config_settings():
    """Verify OAuth settings exist in config."""
    print("\n⚙️  Checking configuration...")
    from app.core.config import settings

    checks = [
        ("SUPABASE_URL", settings.SUPABASE_URL),
        ("SUPABASE_KEY", settings.SUPABASE_KEY),
        ("GOOGLE_OAUTH_CLIENT_ID", settings.GOOGLE_OAUTH_CLIENT_ID),
        ("GOOGLE_OAUTH_CLIENT_SECRET", settings.GOOGLE_OAUTH_CLIENT_SECRET),
        ("GITHUB_OAUTH_CLIENT_ID", settings.GITHUB_OAUTH_CLIENT_ID),
        ("GITHUB_OAUTH_CLIENT_SECRET", settings.GITHUB_OAUTH_CLIENT_SECRET),
        ("APP_BASE_URL", settings.APP_BASE_URL),
        ("FRONTEND_BASE_URL", settings.FRONTEND_BASE_URL),
        ("SESSION_COOKIE_NAME", settings.SESSION_COOKIE_NAME),
        ("SESSION_COOKIE_MAX_AGE", settings.SESSION_COOKIE_MAX_AGE),
    ]

    configured = []
    missing = []

    for name, value in checks:
        if value:
            print(f"  ✅ {name}")
            configured.append(name)
        else:
            print(f"  ⚠️  {name} (not configured)")
            missing.append(name)

    print(f"\n  Configured: {len(configured)}/{len(checks)}")
    if missing:
        print(f"  Missing: {', '.join(missing)}")

    return len(configured) >= 6  # At least Supabase + OAuth basics


def check_provider_detection():
    """Verify provider detection logic."""
    print("\n🔍 Checking provider detection...")
    from app.services.supabase_oauth import detect_provider_from_payload

    # Test Google payload
    google_payload = {
        "user": {
            "identities": [
                {
                    "provider": "google",
                    "id": "118...",
                }
            ]
        }
    }
    provider = detect_provider_from_payload(google_payload)
    if provider == "google":
        print("  ✅ Google provider detection")
    else:
        print(f"  ❌ Google provider detection (got {provider})")
        return False

    # Test GitHub payload
    github_payload = {
        "user": {
            "identities": [
                {
                    "provider": "github",
                    "id": "12345",
                }
            ]
        }
    }
    provider = detect_provider_from_payload(github_payload)
    if provider == "github":
        print("  ✅ GitHub provider detection")
    else:
        print(f"  ❌ GitHub provider detection (got {provider})")
        return False

    return True


def check_normalization():
    """Verify provider normalization."""
    print("\n🔄 Checking provider normalization...")
    from app.services.oauth_providers.google_oauth import GoogleOAuth
    from app.services.oauth_providers.github_oauth import GithubOAuth

    # Test Google normalization
    google_user = {
        "id": "118...",
        "email": "user@gmail.com",
        "name": "John Doe",
        "picture": "https://...",
        "identities": [
            {
                "provider": "google",
                "id": "118...",
                "user_id": "118...",
            }
        ],
    }
    normalized = GoogleOAuth.normalize(google_user)
    if normalized.get("provider") == "google" and normalized.get("email") == "user@gmail.com":
        print("  ✅ Google normalization")
    else:
        print(f"  ❌ Google normalization (got {normalized})")
        return False

    # Test GitHub normalization
    github_user = {
        "id": "12345",
        "email": "user@github.com",
        "login": "johndoe",
        "avatar_url": "https://...",
        "identities": [
            {
                "provider": "github",
                "id": "12345",
                "user_id": "12345",
            }
        ],
    }
    normalized = GithubOAuth.normalize(github_user)
    if normalized.get("provider") == "github" and normalized.get("email") == "user@github.com":
        print("  ✅ GitHub normalization")
    else:
        print(f"  ❌ GitHub normalization (got {normalized})")
        return False

    return True


def check_security_functions():
    """Verify security functions exist."""
    print("\n🔐 Checking security functions...")
    try:
        from app.core.security import (
            create_access_token,
            get_password_hash,
            verify_password,
        )

        # Test token creation
        token = create_access_token(subject="123")
        if token and len(token) > 20:
            print("  ✅ create_access_token()")
        else:
            print("  ❌ create_access_token() failed")
            return False

        # Test password hashing
        hashed = get_password_hash("test_password")
        if hashed and len(hashed) > 20:
            print("  ✅ get_password_hash()")
        else:
            print("  ❌ get_password_hash() failed")
            return False

        # Test password verification
        is_valid = verify_password("test_password", hashed)
        if is_valid:
            print("  ✅ verify_password()")
        else:
            print("  ❌ verify_password() failed")
            return False

        return True
    except Exception as e:
        print(f"  ❌ Security check failed: {e}")
        return False


def check_router_routes():
    """Verify OAuth routes are registered."""
    print("\n📍 Checking router routes...")
    try:
        from app.routers.oauth import router as oauth_router

        routes = {route.path: route.methods for route in oauth_router.routes}

        if "/auth/callback" in routes:
            print("  ✅ GET /auth/callback")
        else:
            print("  ❌ GET /auth/callback not found")
            return False

        if "/api/v1/auth/oauth_me" in routes:
            print("  ✅ GET /api/v1/auth/oauth_me")
        else:
            print("  ❌ GET /api/v1/auth/oauth_me not found")
            return False

        if "/api/v1/auth/logout" in routes:
            print("  ✅ POST /api/v1/auth/logout")
        else:
            print("  ❌ POST /api/v1/auth/logout not found")
            return False

        return True
    except Exception as e:
        print(f"  ❌ Router check failed: {e}")
        return False


def main():
    """Run all checks."""
    print("=" * 60)
    print("🔐 OAuth Implementation Verification")
    print("=" * 60)

    results = []

    results.append(("Imports", check_imports()))
    results.append(("Model Fields", check_model_fields()))
    results.append(("Configuration", check_config_settings()))
    results.append(("Provider Detection", check_provider_detection()))
    results.append(("Normalization", check_normalization()))
    results.append(("Security Functions", check_security_functions()))
    results.append(("Router Routes", check_router_routes()))

    print("\n" + "=" * 60)
    print("📊 Summary")
    print("=" * 60)

    passed = sum(1 for _, result in results if result)
    total = len(results)

    for check_name, result in results:
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{check_name:.<40} {status}")

    print(f"\nTotal: {passed}/{total} checks passed")

    if passed == total:
        print("\n🎉 All checks passed! OAuth implementation is ready.")
        print("\nNext steps:")
        print("1. Add Google OAuth credentials to Supabase")
        print("2. Add GitHub OAuth credentials to Supabase")
        print("3. Set environment variables in Render:")
        print("   - GOOGLE_OAUTH_CLIENT_ID")
        print("   - GOOGLE_OAUTH_CLIENT_SECRET")
        print("   - GITHUB_OAUTH_CLIENT_ID")
        print("   - GITHUB_OAUTH_CLIENT_SECRET")
        print("4. Deploy and test")
        return 0
    else:
        print("\n⚠️  Some checks failed. Please fix issues above.")
        return 1


if __name__ == "__main__":
    sys.exit(main())
