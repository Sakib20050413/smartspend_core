class SmartSpendError(Exception):
    """Base exception for all domain logic failures in SmartSpend."""
    pass

class TransferError(SmartSpendError):
    """Raised for business-rule failures during a transfer (e.g., insufficient funds)."""
    pass

class FeePolicyError(SmartSpendError):
    """Raised when a fee policy cannot be applied or is invalid."""
    pass

class IdempotencyError(SmartSpendError):
    """Raised for idempotency conflicts (e.g., same key but different payload)."""
    pass
