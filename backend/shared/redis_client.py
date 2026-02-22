import json
import os
import redis.asyncio as redis
from typing import Any, Callable

class RedisPubSub:
    def __init__(self):
        host = os.environ.get("REDIS_HOST", "localhost")
        port = int(os.environ.get("REDIS_PORT", 6379))
        self.redis_client = redis.Redis(host=host, port=port, db=0, decode_responses=True)
        self.pubsub = self.redis_client.pubsub()

    async def publish(self, channel: str, message: dict):
        """Publish a JSON payload to a specific Redis channel."""
        await self.redis_client.publish(channel, json.dumps(message))

    async def subscribe(self, channel: str, callback: Callable[[dict], Any]):
        """Subscribe to a Redis channel and call a callback continuously."""
        await self.pubsub.subscribe(channel)
        async for message in self.pubsub.listen():
            if message['type'] == 'message':
                data = json.loads(message['data'])
                await callback(data)

    async def close(self):
        """Clean up connections."""
        await self.pubsub.close()
        await self.redis_client.aclose()
