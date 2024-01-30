from fastapi_cache import FastAPICache
from fastapi_cache.backends.redis import RedisBackend



def init_cache():
    # Configure your Redis server URL here
    FastAPICache.init(RedisBackend('redis://localhost'))

# Optional: Add a custom key builder function here if needed
