from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
from starlette.requests import Request
import os

HOURLY_RATE_LIMIT = os.getenv("HOURLY_RATE_LIMIT", "50/hour")
DAILY_RATE_LIMIT = os.getenv("DAILY_RATE_LIMIT", "200/day")
GLOBAL_DAILY_LIMIT = os.getenv("GLOBAL_DAILY_LIMIT", "500/day")

limiter = Limiter(
    key_func=get_remote_address,
    default_limits=[HOURLY_RATE_LIMIT, DAILY_RATE_LIMIT]
)

def global_key_func(request: Request):
    return "global"

global_limit = limiter.shared_limit(GLOBAL_DAILY_LIMIT, scope="global", key_func=global_key_func) 