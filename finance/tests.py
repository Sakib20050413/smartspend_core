from decimal import Decimal
from django.test import TestCase
from django.contrib.auth import get_user_model
from finance.models import Wallet, Transaction, LedgerEntry
from finance.services.transfers import execute_p2p_transfer
import uuid

User = get_user_model()

class TransferServiceTests(TestCase):
    def setUp(self):
        self.sender_user = User.objects.create(username="sender")
        self.receiver_user = User.objects.create(username="receiver")
        
        self.sender_wallet = Wallet.objects.create(
            owner=self.sender_user, 
            kind=Wallet.Kind.USER, 
            currency=Wallet.Currency.BDT,
            balance=Decimal("1000.00")
        )
        self.receiver_wallet = Wallet.objects.create(
            owner=self.receiver_user, 
            kind=Wallet.Kind.USER, 
            currency=Wallet.Currency.BDT,
            balance=Decimal("0.00")
        )
        self.revenue_wallet = Wallet.objects.create(
            owner=None, 
            kind=Wallet.Kind.REVENUE, 
            currency=Wallet.Currency.BDT,
            balance=Decimal("0.00")
        )

    def test_execute_p2p_transfer_success(self):
        amount = Decimal("100.00")
        # Fee is 1.5% of 100 = 1.50
        
        tx = execute_p2p_transfer(
            sender_wallet=self.sender_wallet,
            receiver_wallet=self.receiver_wallet,
            amount=amount,
            idempotency_key=str(uuid.uuid4()),
            payload_hash="dummyhash",
            channel=Transaction.Channel.APP
        )
        
        self.assertEqual(tx.status, Transaction.Status.COMPLETED)
        
        # Reload wallets
        self.sender_wallet.refresh_from_db()
        self.receiver_wallet.refresh_from_db()
        self.revenue_wallet.refresh_from_db()
        
        # 100 + 1.5 fee = 101.50 deducted
        self.assertEqual(self.sender_wallet.balance, Decimal("898.5000"))
        self.assertEqual(self.receiver_wallet.balance, Decimal("100.0000"))
        self.assertEqual(self.revenue_wallet.balance, Decimal("1.5000"))
        
        # Verify ledger entries sum to zero
        entries = LedgerEntry.objects.filter(transaction=tx)
        self.assertEqual(entries.count(), 3)
        entries_sum = sum(e.amount for e in entries)
        self.assertEqual(entries_sum, Decimal("0.0000"))
