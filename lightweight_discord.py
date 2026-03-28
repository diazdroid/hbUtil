import aiohttp
import asyncio
import json

class DiscordAPIError(Exception):
    """Custom exception for Discord API failures."""
    def __init__(self, status, message):
        self.status = status
        self.message = message
        super().__init__(f"{status} - {message}")

class DiscordClient:
    def __init__(self, token):
        self.token = token
        self.headers = {
            "Authorization": token,
            "Content-Type": "application/json",
        }
        self.base_url = "https://discord.com/api/v10"
        self.session = None

    async def __aenter__(self):
        self.session = aiohttp.ClientSession(headers=self.headers)
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.session:
            await self.session.close()

    async def send_message(self, channel_id, content):
        url = f"{self.base_url}/channels/{channel_id}/messages"
        payload = {"content": content}

        # Adding a small retry logic for potential rate limits
        for attempt in range(3):
            async with self.session.post(url, json=payload) as response:
                if response.status == 200:
                    return await response.json()
                elif response.status == 429:
                    # Rate limited
                    data = await response.json()
                    retry_after = data.get("retry_after", 1.0)
                    print(f"[!] Rate limited. Waiting for {retry_after} seconds...")
                    await asyncio.sleep(retry_after)
                else:
                    text = await response.text()
                    raise DiscordAPIError(response.status, f"Failed to send message: {text}")
        raise DiscordAPIError(429, "Failed to send message after 3 attempts due to rate limits.")

    async def get_messages(self, channel_id, limit=10):
        url = f"{self.base_url}/channels/{channel_id}/messages"
        params = {"limit": limit}
        async with self.session.get(url, params=params) as response:
            if response.status == 200:
                return await response.json()
            else:
                text = await response.text()
                raise DiscordAPIError(response.status, f"Failed to get messages: {text}")
