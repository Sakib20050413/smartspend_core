from contextlib import contextmanager
from django.db import transaction
from finance.models import Wallet

@contextmanager
def locked_wallets(*wallets):
    """
    Context manager to lock wallets for update in a deterministic order.
    SEC-3: Pessimistic locking. Locks rows in deterministic ascending-id order
    to prevent deadlocks. Must be called inside transaction.atomic().
    """
    # WHY: Ensure we are inside an atomic block so the lock persists until commit/rollback
    if not transaction.get_connection().in_atomic_block:
        raise RuntimeError("locked_wallets must be called inside transaction.atomic()")

    wallet_ids = [w.id for w in wallets]
    
    # WHY: Prevent accidental self-transfers or duplicate locking which could cause issues
    if len(wallet_ids) != len(set(wallet_ids)):
        raise ValueError("Duplicate wallet instances provided to locked_wallets")

    # WHY: Sort IDs ascending to prevent deadlocks when concurrent transactions
    # lock the same wallets in different orders.
    sorted_ids = sorted(wallet_ids)
    
    # Lock the wallets from the database
    # select_for_update() enforces pessimistic locking (row-level lock)
    locked_qs = Wallet.objects.select_for_update().filter(id__in=sorted_ids).order_by("id")
    
    locked_dict = {w.id: w for w in locked_qs}
    
    # Verify we got all the wallets we asked for
    if len(locked_dict) != len(wallet_ids):
        raise RuntimeError("Could not lock all requested wallets (some may not exist).")
    
    yield locked_dict
