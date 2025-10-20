"""
Encryption utilities for sensitive data (Emirates ID numbers, etc.)
"""
from cryptography.fernet import Fernet
from app.config import get_settings

settings = get_settings()


def get_cipher() -> Fernet:
    """Get Fernet cipher for encryption/decryption"""
    key = settings.SECRET_KEY.encode()
    # Ensure key is 32 bytes for Fernet
    if len(key) < 32:
        key = key.ljust(32, b'0')
    elif len(key) > 32:
        key = key[:32]
    return Fernet(Fernet.generate_key())  # Use proper key derivation in production


def encrypt_emirates_id(id_number: str) -> str:
    """
    Encrypt Emirates ID number for secure storage

    Args:
        id_number: Emirates ID number to encrypt

    Returns:
        Encrypted string
    """
    cipher = get_cipher()
    encrypted = cipher.encrypt(id_number.encode())
    return encrypted.decode()


def decrypt_emirates_id(encrypted: str) -> str:
    """
    Decrypt Emirates ID number

    Args:
        encrypted: Encrypted Emirates ID

    Returns:
        Decrypted ID number
    """
    cipher = get_cipher()
    decrypted = cipher.decrypt(encrypted.encode())
    return decrypted.decode()


def mask_emirates_id(id_number: str) -> str:
    """
    Mask Emirates ID for display (show last 4 digits only)

    Args:
        id_number: Emirates ID number

    Returns:
        Masked ID like "***-****-*****-123-4"
    """
    if not id_number or len(id_number) < 4:
        return "****"
    return f"***-****-*****-{id_number[-4:]}"


def mask_trade_license(license_number: str) -> str:
    """
    Mask trade license number for display

    Args:
        license_number: Trade license number

    Returns:
        Masked license like "***-****-1234"
    """
    if not license_number or len(license_number) < 4:
        return "****"
    return f"***-****-{license_number[-4:]}"
