import os
import base64
from cryptography.fernet import Fernet
from dotenv import load_dotenv

# Ensure .env is loaded (though app/__init__.py also does this)
load_dotenv()

class AESCipher:
    """
    Utility class for AES encryption/decryption using Fernet.
    Fernet uses AES-128 in CBC mode with PKCS7 padding and HMAC with SHA256 for authentication.
    """
    
    _instance = None
    _cipher = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(AESCipher, cls).__new__(cls)
            key = os.getenv("AES_SECRET_KEY")
            if not key:
                # Fallback for testing or if key is missing (not recommended for production)
                raise ValueError("AES_SECRET_KEY not found in environment variables.")
            
            try:
                cls._cipher = Fernet(key.encode())
            except Exception as e:
                raise ValueError(f"Invalid AES_SECRET_KEY: {str(e)}")
        return cls._instance

    @classmethod
    def encrypt(cls, data):
        """Encrypts data. Data must be a string."""
        if data is None:
            return None
        if not isinstance(data, str):
            data = str(data)
        
        cipher = cls()._cipher
        return cipher.encrypt(data.encode()).decode()

    @classmethod
    def decrypt(cls, encrypted_data):
        """Decrypts data. Returns a string."""
        if encrypted_data is None:
            return None
        
        # Ensure input is a string (or bytes) for decryption attempt
        # If it's a number (legacy), str(55) -> "55"
        try:
            data_str = str(encrypted_data)
            cipher = cls()._cipher
            return cipher.decrypt(data_str.encode()).decode()
        except Exception:
            # If decryption fails (e.g. data not encrypted), return the string version
            return str(encrypted_data)

# Singleton instance for easy access
cipher_suite = AESCipher()
