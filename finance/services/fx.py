from decimal import Decimal, ROUND_HALF_UP
from finance.services.exceptions import SmartSpendError

class FXError(SmartSpendError):
    pass

class FXBridge:
    """
    Handles currency conversion and FX spread calculation.
    """
    
    # Mocked static exchange rates
    RATES = {
        ("USD", "BDT"): Decimal("110.50"), # 1 USD = 110.50 BDT
        ("BDT", "USD"): Decimal("0.0090")  # 1 BDT = 0.0090 USD
    }
    
    # Platform takes a 0.5% spread on FX conversions
    FX_SPREAD_MARGIN = Decimal("0.005")

    @classmethod
    def get_rate(cls, from_currency: str, to_currency: str) -> Decimal:
        if from_currency == to_currency:
            return Decimal("1.0000")
            
        rate = cls.RATES.get((from_currency, to_currency))
        if not rate:
            raise FXError(f"No exchange rate found for {from_currency} to {to_currency}")
        return rate

    @classmethod
    def calculate_conversion(cls, amount: Decimal, from_currency: str, to_currency: str) -> dict:
        """
        Calculates the converted amount and the platform's spread (revenue).
        """
        if amount <= Decimal("0.00"):
            raise FXError("Amount must be positive.")
            
        base_rate = cls.get_rate(from_currency, to_currency)
        
        # Calculate raw converted amount
        raw_converted = amount * base_rate
        
        # Calculate spread (platform revenue in the TARGET currency)
        spread_amount = raw_converted * cls.FX_SPREAD_MARGIN
        
        # The user receives the raw amount minus the spread
        user_receives = raw_converted - spread_amount
        
        # Round according to standard policy
        user_receives = user_receives.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
        spread_amount = spread_amount.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
        
        return {
            "rate_applied": base_rate,
            "user_receives": user_receives,
            "platform_spread": spread_amount,
            "target_currency": to_currency
        }
