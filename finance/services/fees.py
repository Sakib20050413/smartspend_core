from decimal import Decimal, ROUND_HALF_UP
from finance.models import Transaction
from finance.services.exceptions import FeePolicyError

class FeePolicy:
    """
    Base abstraction for calculating transaction fees.
    This replaces the hardcoded rates in transfers.py.
    """
    
    # WHY: A global rounding rule for all money movements ensures 
    # we never leak tiny decimal fractions into the ledger.
    @staticmethod
    def round_amount(amount: Decimal) -> Decimal:
        return amount.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)

    @classmethod
    def calculate_fee(cls, transaction_type: str, amount: Decimal) -> Decimal:
        """
        Calculate the fee for a given transaction type and amount.
        Returns the exact fee to be deducted.
        """
        if amount <= Decimal("0.00"):
            raise FeePolicyError("Cannot calculate fee for non-positive amount.")
            
        fee = Decimal("0.00")
        
        # Example tiers based on transaction type
        if transaction_type == Transaction.TransactionType.P2P_TRANSFER:
            # 1.5% flat fee for P2P transfers
            fee = amount * Decimal("0.015")
        elif transaction_type == Transaction.TransactionType.MFS_DEPOSIT:
            # No fee for deposits
            fee = Decimal("0.00")
        elif transaction_type == Transaction.TransactionType.MERCHANT_PAYMENT:
            # Example: 2% fee
            fee = amount * Decimal("0.02")
        else:
            # Default fallback fee or zero fee
            pass
            
        return cls.round_amount(fee)
