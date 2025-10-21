import logging
import secrets
from datetime import timedelta

from redis.asyncio import Redis

from app.services.email_service import email_service

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


async def send_otp_email(email: str, otp: str, user_name: str | None = None) -> bool:
    """
    Send OTP verification email to user.

    Args:
        email: User's email address
        otp: 6-digit OTP code
        user_name: User's name for personalization (optional)

    Returns:
        True if email sent successfully, False otherwise
    """
    try:
        result = await email_service.send_otp_email(email, otp, user_name)
        if result:
            logger.info("OTP email sent successfully", extra={"email": email})
        else:
            logger.error("Failed to send OTP email", extra={"email": email})
        return result
    except Exception as e:
        logger.error(f"Error sending OTP email: {e}", extra={"email": email, "error": str(e)})
        return False


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
