from cryptography.fernet import Fernet
import base64
from app.config import settings


class Encryptor:
    """Handle encryption/decryption of sensitive data"""
    
    def __init__(self):
        # Ensure key is properly formatted for Fernet
        key = settings.ENCRYPTION_KEY.encode() if isinstance(settings.ENCRYPTION_KEY, str) else settings.ENCRYPTION_KEY
        # Pad or truncate to 32 bytes, then base64 encode for Fernet
        key = base64.urlsafe_b64encode(key[:32].ljust(32, b'0'))
        self.cipher = Fernet(key)
    
    def encrypt(self, plaintext: str) -> str:
        """Encrypt plaintext and return base64 encoded ciphertext"""
        if not plaintext:
            return ""
        encrypted = self.cipher.encrypt(plaintext.encode())
        return encrypted.decode()
    
    def decrypt(self, ciphertext: str) -> str:
        """Decrypt base64 encoded ciphertext and return plaintext"""
        if not ciphertext:
            return ""
        try:
            decrypted = self.cipher.decrypt(ciphertext.encode())
            return decrypted.decode()
        except Exception:
            return "[Decryption Error]"


# Global encryptor instance
encryptor = Encryptor()
