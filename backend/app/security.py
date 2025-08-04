import os
import hashlib
import hmac
import base64
import json
import re
from datetime import datetime, timedelta
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from cryptography.hazmat.primitives.asymmetric import rsa, padding
from cryptography.hazmat.primitives import serialization
import secrets
from typing import Dict, Any, Optional
from dotenv import load_dotenv

load_dotenv()

class PaymentSecurity:
    def __init__(self):
        # Load encryption keys from environment
        self.encryption_key = os.getenv("ENCRYPTION_KEY")
        if not self.encryption_key:
            # Generate a new key if not exists
            self.encryption_key = Fernet.generate_key().decode()
            print(f"⚠️  Generated new encryption key. Add to .env: ENCRYPTION_KEY={self.encryption_key}")
        
        self.fernet = Fernet(self.encryption_key.encode())
        
        # Generate RSA key pair for asymmetric encryption
        self.private_key = self._load_or_generate_private_key()
        self.public_key = self.private_key.public_key()
        
        # Security salt
        self.security_salt = os.getenv("SECURITY_SALT", secrets.token_hex(32))
    
    def _load_or_generate_private_key(self):
        """Load existing private key or generate new one"""
        private_key_path = "private_key.pem"
        
        if os.path.exists(private_key_path):
            with open(private_key_path, "rb") as key_file:
                return serialization.load_pem_private_key(
                    key_file.read(),
                    password=None
                )
        else:
            # Generate new RSA key pair
            private_key = rsa.generate_private_key(
                public_exponent=65537,
                key_size=2048
            )
            
            # Save private key
            with open(private_key_path, "wb") as key_file:
                key_file.write(private_key.private_bytes(
                    encoding=serialization.Encoding.PEM,
                    format=serialization.PrivateFormat.PKCS8,
                    encryption_algorithm=serialization.NoEncryption()
                ))
            
            # Save public key
            public_key_path = "public_key.pem"
            with open(public_key_path, "wb") as key_file:
                key_file.write(private_key.public_key().public_bytes(
                    encoding=serialization.Encoding.PEM,
                    format=serialization.PublicFormat.SubjectPublicKeyInfo
                ))
            
            return private_key
    
    def validate_card_number(self, card_number: str) -> Dict[str, Any]:
        """Validate card number using Luhn algorithm and return card type"""
        # Remove spaces and dashes
        card_number = re.sub(r'[\s-]', '', card_number)
        
        if not card_number.isdigit():
            return {"valid": False, "error": "Card number must contain only digits"}
        
        # Luhn algorithm validation
        def luhn_checksum(card_num):
            def digits_of(n):
                return [int(d) for d in str(n)]
            
            digits = digits_of(card_num)
            odd_digits = digits[-1::-2]
            even_digits = digits[-2::-2]
            checksum = sum(odd_digits)
            for d in even_digits:
                checksum += sum(digits_of(d * 2))
            return checksum % 10
        
        if luhn_checksum(card_number) != 0:
            return {"valid": False, "error": "Invalid card number"}
        
        # Determine card type
        card_type = self._get_card_type(card_number)
        
        return {
            "valid": True,
            "card_type": card_type,
            "masked_number": f"**** **** **** {card_number[-4:]}"
        }
    
    def _get_card_type(self, card_number: str) -> str:
        """Determine card type based on number patterns"""
        if card_number.startswith('4'):
            return "visa"
        elif card_number.startswith(('51', '52', '53', '54', '55')):
            return "mastercard"
        elif card_number.startswith(('34', '37')):
            return "amex"
        elif card_number.startswith(('6011', '644', '645', '646', '647', '648', '649', '65')):
            return "discover"
        else:
            return "unknown"
    
    def validate_expiry_date(self, month: str, year: str) -> Dict[str, Any]:
        """Validate card expiry date"""
        try:
            exp_month = int(month)
            exp_year = int(year)
            
            if not (1 <= exp_month <= 12):
                return {"valid": False, "error": "Invalid month"}
            
            current_date = datetime.now()
            if exp_year < current_date.year:
                return {"valid": False, "error": "Card has expired"}
            
            if exp_year == current_date.year and exp_month < current_date.month:
                return {"valid": False, "error": "Card has expired"}
            
            return {"valid": True}
        except ValueError:
            return {"valid": False, "error": "Invalid date format"}
    
    def validate_cvv(self, cvv: str, card_type: str) -> Dict[str, Any]:
        """Validate CVV based on card type"""
        if not cvv.isdigit():
            return {"valid": False, "error": "CVV must contain only digits"}
        
        cvv_length = len(cvv)
        expected_length = 4 if card_type == "amex" else 3
        
        if cvv_length != expected_length:
            return {"valid": False, "error": f"CVV must be {expected_length} digits for {card_type}"}
        
        return {"valid": True}
    
    def encrypt_sensitive_data(self, data: Dict[str, Any]) -> str:
        """Encrypt sensitive payment data"""
        # Create a unique encryption key for this data
        data_key = secrets.token_hex(32)
        
        # Encrypt the data
        encrypted_data = self.fernet.encrypt(json.dumps(data).encode())
        
        # Create a secure package with metadata
        secure_package = {
            "encrypted_data": base64.b64encode(encrypted_data).decode(),
            "timestamp": datetime.utcnow().isoformat(),
            "data_key": data_key,
            "version": "1.0"
        }
        
        return json.dumps(secure_package)
    
    def decrypt_sensitive_data(self, encrypted_package: str) -> Dict[str, Any]:
        """Decrypt sensitive payment data"""
        try:
            package = json.loads(encrypted_package)
            encrypted_data = base64.b64decode(package["encrypted_data"])
            decrypted_data = self.fernet.decrypt(encrypted_data)
            return json.loads(decrypted_data.decode())
        except Exception as e:
            raise ValueError(f"Failed to decrypt data: {str(e)}")
    
    def create_payment_token(self, card_data: Dict[str, Any]) -> str:
        """Create a secure payment token"""
        # Create token data
        token_data = {
            "card_type": card_data["card_type"],
            "masked_number": card_data["masked_number"],
            "expiry_month": card_data["expiry_month"],
            "expiry_year": card_data["expiry_year"],
            "cardholder_name": card_data["cardholder_name"],
            "token_id": secrets.token_hex(32),
            "created_at": datetime.utcnow().isoformat()
        }
        
        # Encrypt the token data
        return self.encrypt_sensitive_data(token_data)
    
    def generate_security_hash(self, transaction_data: Dict[str, Any]) -> str:
        """Generate a security hash for transaction integrity"""
        # Create a string of critical transaction data
        hash_data = f"{transaction_data['amount']}{transaction_data['currency']}{transaction_data['email']}{datetime.utcnow().isoformat()}{self.security_salt}"
        
        # Generate SHA-256 hash
        return hashlib.sha256(hash_data.encode()).hexdigest()
    
    def calculate_risk_score(self, transaction_data: Dict[str, Any], ip_address: str = None) -> float:
        """Calculate risk score for transaction"""
        risk_score = 0.0
        
        # Amount-based risk
        amount = float(transaction_data.get('amount', 0))
        if amount > 1000:
            risk_score += 0.3
        elif amount > 500:
            risk_score += 0.2
        
        # Email domain risk
        email = transaction_data.get('email', '')
        if email:
            domain = email.split('@')[-1] if '@' in email else ''
            suspicious_domains = ['temp-mail.org', '10minutemail.com', 'guerrillamail.com']
            if domain in suspicious_domains:
                risk_score += 0.4
        
        # IP-based risk (basic implementation)
        if ip_address:
            # Check for localhost or private IPs
            if ip_address in ['127.0.0.1', 'localhost']:
                risk_score += 0.1
        
        return min(risk_score, 1.0)  # Cap at 1.0
    
    def sanitize_input(self, data: str) -> str:
        """Sanitize user input to prevent injection attacks"""
        # Remove potentially dangerous characters
        dangerous_chars = ['<', '>', '"', "'", '&', ';', '(', ')', '{', '}']
        for char in dangerous_chars:
            data = data.replace(char, '')
        return data.strip()

# Global security instance
payment_security = PaymentSecurity() 