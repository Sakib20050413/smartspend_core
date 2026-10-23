from django.contrib import admin
from .models import Wallet, Transaction, LedgerEntry

@admin.register(Wallet)
class WalletAdmin(admin.ModelAdmin):
    list_display = ('id', 'owner', 'kind', 'currency', 'balance', 'is_active', 'created_at')
    list_filter = ('kind', 'currency', 'is_active')
    search_fields = ('id', 'owner__username')
    readonly_fields = ('id', 'balance', 'created_at', 'updated_at')
    
    # WHY: Prevent manual adjustment of balances in the admin panel to ensure
    # all balance mutations go through the LedgerEntry double-entry system.
    def get_readonly_fields(self, request, obj=None):
        if obj: # Editing an existing object
            return self.readonly_fields + ('owner', 'kind', 'currency')
        return self.readonly_fields

@admin.register(Transaction)
class TransactionAdmin(admin.ModelAdmin):
    list_display = ('id', 'transaction_type', 'status', 'channel', 'created_at')
    list_filter = ('transaction_type', 'status', 'channel')
    search_fields = ('id', 'idempotency_key', 'external_reference')
    
    # WHY: Transactions should never be manually modified once created. 
    # Corrections happen via a new reversing Transaction.
    def has_change_permission(self, request, obj=None):
        return False
        
    def has_delete_permission(self, request, obj=None):
        return False

@admin.register(LedgerEntry)
class LedgerEntryAdmin(admin.ModelAdmin):
    list_display = ('id', 'transaction', 'wallet', 'amount', 'currency', 'purpose', 'created_at')
    list_filter = ('currency', 'purpose')
    search_fields = ('id', 'transaction__id', 'wallet__id')
    
    # WHY: Ledger entries are strictly insert-only and immutable.
    def has_add_permission(self, request):
        return False
        
    def has_change_permission(self, request, obj=None):
        return False
        
    def has_delete_permission(self, request, obj=None):
        return False
