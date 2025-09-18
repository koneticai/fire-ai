"""
Security utilities for PII encryption and other security functions
"""

import os
import base64
from typing import Optional

from cryptography.fernet import Fernet

class PIIEncryption:
    """Handles encryption and decryption of PII data using Fernet symmetric encryption"""
    
    def __init__(self):
        # Get encryption key from environment
        key_str = os.getenv("PII_ENCRYPTION_KEY")
        if not key_str:
            # Generate a key for development (should be set in production)
            key_str = Fernet.generate_key().decode()
            print(f"WARNING: No PII_ENCRYPTION_KEY found. Using generated key: {key_str}")
        
        # Convert string key to bytes if needed
        if isinstance(key_str, str):
            key_bytes = key_str.encode()
        else:
            key_bytes = key_str
            
        self.cipher = Fernet(key_bytes)
    
    def encrypt(self, data: str) -> bytes:
        """Encrypt a string and return bytes"""
        if not data:
            return b''
        
        return self.cipher.encrypt(data.encode('utf-8'))
    
    def decrypt(self, encrypted_data: bytes) -> str:
        """Decrypt bytes and return string"""
        if not encrypted_data:
            return ''
        
        decrypted_bytes = self.cipher.decrypt(encrypted_data)
        return decrypted_bytes.decode('utf-8')
    
    def encrypt_to_base64(self, data: str) -> str:
        """Encrypt data and return as base64 string for JSON storage"""
        encrypted_bytes = self.encrypt(data)
        return base64.b64encode(encrypted_bytes).decode('ascii')
    
    def decrypt_from_base64(self, base64_data: str) -> str:
        """Decrypt from base64 string"""
        encrypted_bytes = base64.b64decode(base64_data.encode('ascii'))
        return self.decrypt(encrypted_bytes)

# Global instance
pii_encryption = PIIEncryption()

def encrypt_pii(data: str) -> bytes:
    """Convenience function to encrypt PII data"""
    return pii_encryption.encrypt(data)

def decrypt_pii(encrypted_data: bytes) -> str:
    """Convenience function to decrypt PII data"""
    return pii_encryption.decrypt(encrypted_data)

def encrypt_pii_base64(data: str) -> str:
    """Convenience function to encrypt PII data as base64"""
    return pii_encryption.encrypt_to_base64(data)

def decrypt_pii_base64(base64_data: str) -> str:
    """Convenience function to decrypt PII data from base64"""
    return pii_encryption.decrypt_from_base64(base64_data)