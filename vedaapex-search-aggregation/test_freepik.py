import httpx
import asyncio


async def test_key():
    key = "FPSX050f615bae95816fa2a6b1b947c41d1e"
    headers = {"x-freepik-api-key": key, "Accept": "application/json"}

    async with httpx.AsyncClient() as client:
        # Just checking auth, not necessarily generating
        response = await client.get("https://api.freepik.com/v1/ai/text-to-image", headers=headers)
        print(f"Status: {response.status_code}")
        print(f"Response: {response.text}")


asyncio.run(test_key())
