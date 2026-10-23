from decimal import Decimal
from django.db import transaction
from django.utils import timezone
from finance.models import Wallet, Transaction, LedgerEntry
from finance.services.exceptions import TransferError
from finance.services.locking import locked_wallets
from finance.services.idempotency import idempotent_transaction_slot
from finance.services.fees import FeePolicy

def execute_p2p_transfer(
    *, 
    sender_wallet: Wallet, 
    receiver_wallet: Wallet, 
    amount: Decimal, 
    idempotency_key: str, 
    payload_hash: str,
    external_ref: str = "", 
    channel: str = Transaction.Channel.APP, 
    initiated_by_ip: str = None
) -> Transaction:
    """
    Executes a P2P transfer strictly adhering to SEC-1 to SEC-5.
    
    1. Validates basic business rules (currencies, active status).
    2. Uses idempotency slot to prevent duplicates.
    3. Uses pessimistic locking (sorted ascending by id).
    4. Calculates fee via FeePolicy.
    5. Checks sufficient funds.
    6. Creates double-entry LedgerEntry rows.
    7. Asserts sum == 0 before commit.
    8. Updates cached Wallet balances.
    """
    # WHY: Business rules validation upfront
    if amount <= Decimal("0.00"):
        raise TransferError("Transfer amount must be positive.")
    if sender_wallet.id == receiver_wallet.id:
        raise TransferError("Cannot transfer to the same wallet.")
    if sender_wallet.currency != receiver_wallet.currency:
        raise TransferError("Currency mismatch between sender and receiver.")

    # Find the platform REVENUE wallet for this currency
    revenue_wallet = Wallet.objects.filter(
        kind=Wallet.Kind.REVENUE, 
        currency=sender_wallet.currency
    ).first()
    
    if not revenue_wallet:
        raise TransferError(f"Platform revenue wallet not configured for {sender_wallet.currency}.")

    # SEC-5: All money movement wrapped in transaction.atomic()
    with transaction.atomic():
        # SEC-2: Reserve the idempotency slot. If this is a duplicate safe replay, 
        # it yields the existing transaction which we return immediately.
        with idempotent_transaction_slot(
            idempotency_key=idempotency_key, 
            payload_hash=payload_hash,
            transaction_type=Transaction.TransactionType.P2P_TRANSFER,
            status=Transaction.Status.PROCESSING,
            channel=channel,
            external_reference=external_ref,
            initiated_by_ip=initiated_by_ip
        ) as (tx, was_duplicate):
            
            if was_duplicate:
                return tx
                
            tx.processing_at = timezone.now()
            tx.save(update_fields=['processing_at'])

            # SEC-3: Lock wallets deterministically
            with locked_wallets(sender_wallet, receiver_wallet, revenue_wallet) as locked:
                locked_sender = locked[sender_wallet.id]
                locked_receiver = locked[receiver_wallet.id]
                locked_revenue = locked[revenue_wallet.id]

                if not locked_sender.is_active or not locked_receiver.is_active:
                    tx.status = Transaction.Status.FAILED
                    tx.failed_at = timezone.now()
                    tx.save(update_fields=['status', 'failed_at'])
                    raise TransferError("One or both wallets are inactive.")

                # Fee calculation
                fee_amount = FeePolicy.calculate_fee(Transaction.TransactionType.P2P_TRANSFER, amount)
                total_deduction = amount + fee_amount

                if locked_sender.balance < total_deduction:
                    tx.status = Transaction.Status.FAILED
                    tx.failed_at = timezone.now()
                    tx.save(update_fields=['status', 'failed_at'])
                    raise TransferError("Insufficient funds (including fee).")

                # Double-entry ledger preparation
                entries = []
                
                # Debit Sender
                sender_balance_after = locked_sender.balance - total_deduction
                entries.append(LedgerEntry(
                    transaction=tx,
                    wallet=locked_sender,
                    amount=-total_deduction,
                    currency=locked_sender.currency,
                    balance_after=sender_balance_after,
                    purpose=LedgerEntry.Purpose.PRINCIPAL
                ))
                
                # Credit Receiver
                receiver_balance_after = locked_receiver.balance + amount
                entries.append(LedgerEntry(
                    transaction=tx,
                    wallet=locked_receiver,
                    amount=amount,
                    currency=locked_receiver.currency,
                    balance_after=receiver_balance_after,
                    purpose=LedgerEntry.Purpose.PRINCIPAL
                ))
                
                # Credit Revenue
                if fee_amount > Decimal("0.00"):
                    revenue_balance_after = locked_revenue.balance + fee_amount
                    entries.append(LedgerEntry(
                        transaction=tx,
                        wallet=locked_revenue,
                        amount=fee_amount,
                        currency=locked_revenue.currency,
                        balance_after=revenue_balance_after,
                        purpose=LedgerEntry.Purpose.FEE
                    ))

                # WHY: Explicit sum-zero invariant assertion before commit.
                # Double-entry bookkeeping must balance exactly to zero.
                entries_sum = sum(e.amount for e in entries)
                if entries_sum != Decimal("0.00"):
                    raise TransferError(f"CRITICAL: Ledger entries do not sum to zero. Sum: {entries_sum}")

                # Bulk create entries
                LedgerEntry.objects.bulk_create(entries)

                # SEC-1 & SEC-5: Update cached balances on the locked instances
                locked_sender.balance = sender_balance_after
                locked_sender.save(update_fields=['balance', 'updated_at'])
                
                locked_receiver.balance = receiver_balance_after
                locked_receiver.save(update_fields=['balance', 'updated_at'])
                
                if fee_amount > Decimal("0.00"):
                    locked_revenue.balance = revenue_balance_after
                    locked_revenue.save(update_fields=['balance', 'updated_at'])

                # Mark transaction as completed
                tx.status = Transaction.Status.COMPLETED
                tx.completed_at = timezone.now()
                tx.save(update_fields=['status', 'completed_at'])

            return tx
