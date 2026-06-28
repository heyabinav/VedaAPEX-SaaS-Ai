import logging
import asyncio
import httpx
from app.core.config import settings

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("sync_supabase")


async def get_supabase_user_id(email: str):
    """Fetch the Supabase user ID by email using Admin API."""
    url = f"{settings.SUPABASE_URL}/auth/v1/admin/users"
    headers = {
        "apikey": settings.SUPABASE_SERVICE_ROLE_KEY or settings.SUPABASE_KEY,
        "Authorization": f"Bearer {settings.SUPABASE_SERVICE_ROLE_KEY or settings.SUPABASE_KEY}",
    }

    async with httpx.AsyncClient() as client:
        response = await client.get(url, headers=headers)
        if response.status_code != 200:
            logger.error(f"Failed to fetch users: {response.text}")
            return None

        data = response.json()
        users = data.get("users", []) if isinstance(data, dict) else data
        for user in users:
            if user.get("email") == email:
                return user.get("id")
    return None


async def update_supabase_metadata(email: str, metadata: dict):
    """Update user metadata in Supabase using the Admin API."""
    user_id = await get_supabase_user_id(email)
    if not user_id:
        logger.error(f"User {email} not found in Supabase.")
        return

    url = f"{settings.SUPABASE_URL}/auth/v1/admin/users/{user_id}"
    headers = {
        "apikey": settings.SUPABASE_SERVICE_ROLE_KEY or settings.SUPABASE_KEY,
        "Authorization": f"Bearer {settings.SUPABASE_SERVICE_ROLE_KEY or settings.SUPABASE_KEY}",
        "Content-Type": "application/json",
    }

    payload = {"user_metadata": metadata}

    async with httpx.AsyncClient() as client:
        response = await client.put(url, headers=headers, json=payload)
        if response.status_code == 200:
            logger.info(f"Successfully updated Supabase metadata for {email}: {metadata}")
        else:
            logger.error(f"Failed to update Supabase metadata: {response.text}")


if __name__ == "__main__":
    email = "himanshukumar892960@gmail.com"
    # Metadata to show Ultra plan and Admin status in Supabase Dashboard
    metadata = {
        "full_name": "Himanshu Kumar",
        "plan": "ultra",
        "role": "ADMIN",
        "is_pro": True,
    }
    asyncio.run(update_supabase_metadata(email, metadata))
