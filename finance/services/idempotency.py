from contextlib import contextmanager
from django.db import transaction, IntegrityError
from django.core.cache import cache
from finance.models import Transaction
from finance.services.exceptions import IdempotencyError

@contextmanager
def idempotent_transaction_slot(idempotency_key, payload_hash, **transaction_kwargs):
    """
    Context manager to reserve an idempotency slot.
    SEC-2: Idempotency keys everywhere, enforced at DB level via unique=True.
    
    Includes a Redis fast-path check (via Django's cache API) to reject
    obvious duplicates extremely fast without hitting the database.
    """
    if not transaction.get_connection().in_atomic_block:
        raise RuntimeError("idempotent_transaction_slot must be called inside transaction.atomic()")

    cache_key = f"idempotency_{idempotency_key}"
    
    # WHY: Redis fast-path check. We save a DB query and potential IntegrityError
    # rollback if we already know this key was used recently.
    cached_payload_hash = cache.get(cache_key)
    if cached_payload_hash:
        if cached_payload_hash != payload_hash:
            raise IdempotencyError("Idempotency conflict: Key used for a different request (caught by Redis cache).")
        # Fast path duplicate safe return
        existing_tx = Transaction.objects.get(idempotency_key=idempotency_key)
        yield existing_tx, True
        return

    try:
        # Savepoint is needed because an IntegrityError will abort the current transaction block
        with transaction.atomic():
            tx = Transaction.objects.create(
                idempotency_key=idempotency_key,
                payload_hash=payload_hash,
                **transaction_kwargs
            )
            
            # Cache the successful payload hash for fast-path lookups
            # Time-to-live is set to 24 hours (86400 seconds)
            cache.set(cache_key, payload_hash, timeout=86400)
            
            yield tx, False # (transaction, was_duplicate)
    except IntegrityError:
        # WHY: The key already exists in DB but expired from cache (or cache was flushed).
        
        existing_tx = Transaction.objects.get(idempotency_key=idempotency_key)
        
        # GAP FIXED: Check if the payload hash matches. 
        if existing_tx.payload_hash != payload_hash:
            raise IdempotencyError("Idempotency conflict: The provided idempotency key was already used for a different request.")
        
        # Repopulate the cache since it was missing
        cache.set(cache_key, existing_tx.payload_hash, timeout=86400)
        
        yield existing_tx, True
