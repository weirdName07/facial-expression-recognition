import json
import redis.asyncio as redis
from typing import Any, Callable

class RedisPubSub:
    def __init__(self, host='localhost', port=6379, db=0):
        self.redis_client = redis.Redis(host=host, port=port, db=db, decode_responses=True)
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
