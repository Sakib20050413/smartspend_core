from django import forms
from django.contrib.auth.forms import UserCreationForm
from .models import Transaction, Goal

class RegisterForm(UserCreationForm):
    class Meta(UserCreationForm.Meta): fields = ['username', 'email']

class TransactionForm(forms.ModelForm):
    class Meta: model, exclude, widgets = Transaction, ['user'], {'date': forms.DateInput(attrs={'type': 'date'})}

class GoalForm(forms.ModelForm):
    class Meta: model, exclude, widgets = Goal, ['user'], {'deadline': forms.DateInput(attrs={'type': 'date'})}