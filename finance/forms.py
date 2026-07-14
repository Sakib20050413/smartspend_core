from django import forms
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.models import User
from .models import Transaction, Goal

class RegisterForm(UserCreationForm):
    class Meta:
        model = User
        fields = ['username', 'email']

class TransactionForm(forms.ModelForm):
    class Meta:
        model = Transaction
        fields = ['title', 'amount', 'transaction_type', 'date', 'category']
        widgets = {
            'date': forms.DateInput(attrs={'type': 'date', 'class': 'w-full px-3 py-2 border rounded-lg'}),
        }

class GoalForm(forms.ModelForm):
    class Meta:
        model = Goal
        fields = ['name', 'target_amount', 'deadline']
        widgets = {
            'deadline': forms.DateInput(attrs={'type': 'date', 'class': 'w-full px-3 py-2 border rounded-lg'}),
        }