import hmac
import hashlib
from django.conf import settings
from finance.services.exceptions import SmartSpendError

class SMSAuthError(SmartSpendError):
    pass

class SMSGateway:
    """
    Handles inbound encrypted/signed SMS messages for offline transactions.
    SEC-4: HMAC-SHA256 signature verification on every inbound webhook.
    """
    
    @staticmethod
    def verify_signature(payload: str, provided_signature: str) -> bool:
        """
        Verifies the HMAC-SHA256 signature of the incoming SMS payload.
        The secret key should be securely stored in Django settings.
        """
        secret_key = getattr(settings, 'SMS_GATEWAY_SECRET', 'default-unsafe-secret').encode('utf-8')
        
        # Calculate expected signature
        expected_mac = hmac.new(
            secret_key, 
            payload.encode('utf-8'), 
            hashlib.sha256
        ).hexdigest()
        
        # Constant-time comparison to prevent timing attacks
        return hmac.compare_digest(expected_mac, provided_signature)

    @classmethod
    def process_incoming_sms(cls, payload: str, signature: str) -> dict:
        """
        Validates and parses the incoming SMS payload.
        Expects payload format: "SENDER_MSISDN|COMMAND|AMOUNT|TARGET_MSISDN"
        """
        if not cls.verify_signature(payload, signature):
            raise SMSAuthError("Invalid SMS signature. Request rejected.")
            
        parts = payload.split('|')
        if len(parts) < 2:
            raise ValueError("Malformed SMS payload.")
            
        msisdn = parts[0]
        command = parts[1]
        
        return {
            "sender": msisdn,
            "command": command,
            "args": parts[2:]
        }
