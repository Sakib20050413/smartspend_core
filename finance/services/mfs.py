from decimal import Decimal
from abc import ABC, abstractmethod
from django.db import transaction
from django.utils import timezone
from finance.models import Wallet, Transaction, LedgerEntry
from finance.services.exceptions import TransferError
from finance.services.locking import locked_wallets
from finance.services.idempotency import idempotent_transaction_slot

class MFSAdapter(ABC):
    @abstractmethod
    def initiate_deposit(self, mfs_number: str, amount: Decimal, reference: str) -> dict:
        pass

    @abstractmethod
    def initiate_withdrawal(self, mfs_number: str, amount: Decimal, reference: str) -> dict:
        pass

class BkashAdapter(MFSAdapter):
    def initiate_deposit(self, mfs_number: str, amount: Decimal, reference: str) -> dict:
        # Mocked bKash API call
        return {"status": "SUCCESS", "mfs_txn_id": "BKASH123"}
        
    def initiate_withdrawal(self, mfs_number: str, amount: Decimal, reference: str) -> dict:
        # Mocked bKash API call
        return {"status": "SUCCESS", "mfs_txn_id": "BKASH456"}

class NagadAdapter(MFSAdapter):
    def initiate_deposit(self, mfs_number: str, amount: Decimal, reference: str) -> dict:
        return {"status": "SUCCESS", "mfs_txn_id": "NAGAD123"}
        
    def initiate_withdrawal(self, mfs_number: str, amount: Decimal, reference: str) -> dict:
        return {"status": "SUCCESS", "mfs_txn_id": "NAGAD456"}

class RocketAdapter(MFSAdapter):
    def initiate_deposit(self, mfs_number: str, amount: Decimal, reference: str) -> dict:
        return {"status": "SUCCESS", "mfs_txn_id": "ROCKET123"}
        
    def initiate_withdrawal(self, mfs_number: str, amount: Decimal, reference: str) -> dict:
        return {"status": "SUCCESS", "mfs_txn_id": "ROCKET456"}


def execute_mfs_deposit(
    *, 
    user_wallet: Wallet, 
    provider: str,
    mfs_number: str,
    amount: Decimal, 
    idempotency_key: str, 
    payload_hash: str
) -> Transaction:
    """
    Executes a deposit from an MFS provider into a user's wallet.
    Funds move from the Settlement account (representing external cash) to the User wallet.
    """
    if amount <= Decimal("0.00"):
        raise TransferError("Deposit amount must be positive.")
        
    settlement_wallet = Wallet.objects.filter(
        kind=Wallet.Kind.SETTLEMENT, 
        currency=user_wallet.currency
    ).first()
    
    if not settlement_wallet:
        raise TransferError(f"Settlement wallet not found for {user_wallet.currency}.")
        
    # Get adapter
    adapter_map = {'bkash': BkashAdapter(), 'nagad': NagadAdapter(), 'rocket': RocketAdapter()}
    adapter = adapter_map.get(provider.lower())
    if not adapter:
        raise TransferError(f"Unsupported MFS provider: {provider}")

    with transaction.atomic():
        with idempotent_transaction_slot(
            idempotency_key=idempotency_key, 
            payload_hash=payload_hash,
            transaction_type=Transaction.TransactionType.MFS_DEPOSIT,
            status=Transaction.Status.PROCESSING,
            channel=Transaction.Channel.API
        ) as (tx, was_duplicate):
            
            if was_duplicate:
                return tx
                
            tx.processing_at = timezone.now()
            tx.save(update_fields=['processing_at'])
            
            # Call external provider (mocked)
            api_resp = adapter.initiate_deposit(mfs_number, amount, str(tx.id))
            tx.external_reference = api_resp.get('mfs_txn_id', '')
            
            with locked_wallets(user_wallet, settlement_wallet) as locked:
                locked_user = locked[user_wallet.id]
                locked_settlement = locked[settlement_wallet.id]
                
                # Debit settlement, credit user
                entries = []
                
                settlement_balance_after = locked_settlement.balance - amount
                entries.append(LedgerEntry(
                    transaction=tx,
                    wallet=locked_settlement,
                    amount=-amount,
                    currency=locked_settlement.currency,
                    balance_after=settlement_balance_after
                ))
                
                user_balance_after = locked_user.balance + amount
                entries.append(LedgerEntry(
                    transaction=tx,
                    wallet=locked_user,
                    amount=amount,
                    currency=locked_user.currency,
                    balance_after=user_balance_after
                ))
                
                entries_sum = sum(e.amount for e in entries)
                if entries_sum != Decimal("0.00"):
                    raise TransferError("Ledger entries do not sum to zero.")
                    
                LedgerEntry.objects.bulk_create(entries)
                
                locked_settlement.balance = settlement_balance_after
                locked_settlement.save(update_fields=['balance', 'updated_at'])
                
                locked_user.balance = user_balance_after
                locked_user.save(update_fields=['balance', 'updated_at'])
                
            tx.status = Transaction.Status.COMPLETED
            tx.completed_at = timezone.now()
            tx.save(update_fields=['status', 'completed_at', 'external_reference'])
            
            return tx
