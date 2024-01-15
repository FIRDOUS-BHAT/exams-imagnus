# cache_config.py
from aiocache import Cache
from aiocache.serializers import JsonSerializer

# cache = Cache(Cache.REDIS, endpoint="localhost", port=6379, serializer=JsonSerializer())
cache = Cache(Cache.REDIS)

