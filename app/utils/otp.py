import logging
import secrets
from datetime import timedelta

from redis.asyncio import Redis

OTP_TTL_SECONDS = 600
OTP_RATE_LIMIT = 3
OTP_RATE_LIMIT_WINDOW = timedelta(hours=1)

logger = logging.getLogger(__name__)


def generate_otp(length: int = 6) -> str:
    return "".join(str(secrets.randbelow(10)) for _ in range(length))


def _rate_limit_key(identifier: str) -> str:
    return f"otp:rate:{identifier}"


def _otp_key(identifier: str) -> str:
    return f"otp:{identifier}"


async def send_otp_email(email: str, otp: str) -> bool:
    # Placeholder for integration with actual email provider (e.g., SES, Mailgun)
    logger.info("Sending OTP email", extra={"email": email, "otp": otp})
    return True


async def send_otp_sms(phone: str, otp: str) -> bool:
    # Placeholder for integration with Twilio
    logger.info("Sending OTP SMS", extra={"phone": phone, "otp": otp})
    return True


async def store_otp(identifier: str, otp: str, redis_client: Redis) -> None:
    otp_key = _otp_key(identifier)
    rate_key = _rate_limit_key(identifier)

    current_count = await redis_client.get(rate_key)
    if current_count is None:
        await redis_client.set(rate_key, 1, ex=int(OTP_RATE_LIMIT_WINDOW.total_seconds()))
    else:
        if int(current_count) >= OTP_RATE_LIMIT:
            raise ValueError("OTP request limit reached. Please try again later.")
        await redis_client.incr(rate_key)

    await redis_client.set(otp_key, otp, ex=OTP_TTL_SECONDS)


async def verify_otp(identifier: str, otp: str, redis_client: Redis) -> bool:
    otp_key = _otp_key(identifier)
    stored_otp = await redis_client.get(otp_key)
    if stored_otp and secrets.compare_digest(stored_otp, otp):
        await redis_client.delete(otp_key)
        return True
    return False
