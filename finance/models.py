import uuid
from decimal import Decimal
from django.db import models
from django.conf import settings

# SEC-1: No floats for money. All currency fields are DecimalField.
# SEC-2: Idempotency keys everywhere (enforced via unique=True).
# SEC-5: General standards: Explicit state machines (Status enum).

class Wallet(models.fields.related.Model if False else models.Model):
    class Kind(models.TextChoices):
        USER = 'USER', 'User Wallet'
        REVENUE = 'REVENUE', 'Platform Revenue'
        SUSPENSE = 'SUSPENSE', 'Suspense Account'
        SETTLEMENT = 'SETTLEMENT', 'Settlement Account'

    class Currency(models.TextChoices):
        BDT = 'BDT', 'Bangladeshi Taka'
        USD = 'USD', 'US Dollar'

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    owner = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, null=True, blank=True, help_text="Null for platform/system wallets")
    kind = models.CharField(max_length=20, choices=Kind.choices, default=Kind.USER)
    currency = models.CharField(max_length=3, choices=Currency.choices, default=Currency.BDT)
    
    # SEC-1 & SEC-5: Decimal precision, cached balance mutated only in locked transactions
    balance = models.DecimalField(max_digits=18, decimal_places=4, default=Decimal("0.0000"))
    is_active = models.BooleanField(default=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=['owner', 'kind', 'currency'], name='unique_wallet_per_owner_kind_currency')
        ]

    def __str__(self):
        return f"{self.kind} Wallet {self.id} ({self.currency}) - Balance: {self.balance}"


class Transaction(models.Model):
    class TransactionType(models.TextChoices):
        P2P_TRANSFER = 'P2P_TRANSFER', 'P2P Transfer'
        MERCHANT_PAYMENT = 'MERCHANT_PAYMENT', 'Merchant Payment'
        MFS_DEPOSIT = 'MFS_DEPOSIT', 'MFS Deposit'
        MFS_WITHDRAWAL = 'MFS_WITHDRAWAL', 'MFS Withdrawal'
        FEE = 'FEE', 'Fee'
        REVERSAL = 'REVERSAL', 'Reversal'

    class Status(models.TextChoices):
        PENDING = 'PENDING', 'Pending'
        PROCESSING = 'PROCESSING', 'Processing'
        COMPLETED = 'COMPLETED', 'Completed'
        FAILED = 'FAILED', 'Failed'
        REVERSED = 'REVERSED', 'Reversed'
        
    class Channel(models.TextChoices):
        APP = 'APP', 'App'
        USSD = 'USSD', 'USSD'
        SMS = 'SMS', 'SMS'
        API = 'API', 'API'

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    # SEC-2: Idempotency enforced at DB level
    idempotency_key = models.UUIDField(unique=True, help_text="Client-provided idempotency key for safe retries")
    # GAP FIXED: payload_hash added to distinguish same key, different payload
    payload_hash = models.CharField(max_length=64, help_text="SHA-256 hash of the request payload to detect conflicts")
    
    transaction_type = models.CharField(max_length=20, choices=TransactionType.choices)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.PENDING)
    external_reference = models.CharField(max_length=100, blank=True, default="")
    reverses = models.ForeignKey('self', on_delete=models.PROTECT, null=True, blank=True, related_name='reversals')
    channel = models.CharField(max_length=10, choices=Channel.choices, default=Channel.APP)
    initiated_by_ip = models.GenericIPAddressField(null=True, blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    processing_at = models.DateTimeField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    failed_at = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return f"{self.transaction_type} {self.id} ({self.status})"


class LedgerEntry(models.Model):
    class Purpose(models.TextChoices):
        PRINCIPAL = 'PRINCIPAL', 'Principal Amount'
        FEE = 'FEE', 'Fee'
        REVERSAL = 'REVERSAL', 'Reversal'

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    transaction = models.ForeignKey(Transaction, on_delete=models.PROTECT, related_name='ledger_entries')
    wallet = models.ForeignKey(Wallet, on_delete=models.PROTECT, related_name='ledger_entries')
    
    # SEC-1: Strict decimal type for all money amounts
    amount = models.DecimalField(max_digits=18, decimal_places=4, help_text="Signed value: negative for debit, positive for credit")
    currency = models.CharField(max_length=3, choices=Wallet.Currency.choices)
    balance_after = models.DecimalField(max_digits=18, decimal_places=4, help_text="Snapshot of the wallet balance after this entry")
    purpose = models.CharField(max_length=20, choices=Purpose.choices, default=Purpose.PRINCIPAL)
    
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Entry {self.id} for {self.wallet_id}: {self.amount} {self.currency}"
