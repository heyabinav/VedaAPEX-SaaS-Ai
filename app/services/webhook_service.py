import httpx
import logging
from typing import Optional, Dict, Any

logger = logging.getLogger("veda_cli")


class WebhookService:
    @staticmethod
    async def trigger_webhook(
        url: str, event_type: str, data: Dict[str, Any], secret: Optional[str] = None
    ):
        """Send a POST request to the specified webhook URL."""
        payload = {
            "event": event_type,
            "data": data,
            "timestamp": None,  # Will be filled by receiver or we can add it here
        }

        headers = {"Content-Type": "application/json"}
        if secret:
            headers["X-Veda-Signature"] = secret  # Simple signature placeholder

        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.post(url, json=payload, headers=headers)
                response.raise_for_status()
                logger.info(f"Webhook {event_type} sent successfully to {url}")
                return True
        except Exception as e:
            logger.error(f"Failed to send webhook {event_type} to {url}: {e}")
            return False

    @staticmethod
    async def broadcast_generation_completed(
        user_id: int, gen_type: str, output_url: str, webhook_url: Optional[str]
    ):
        """Specialized helper for generation events."""
        if not webhook_url:
            return

        await WebhookService.trigger_webhook(
            url=webhook_url,
            event_type="generation.completed",
            data={"user_id": user_id, "type": gen_type, "output_url": output_url},
        )
