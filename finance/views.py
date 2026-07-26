from django.shortcuts import render, redirect
from django.contrib.auth import login
from django.contrib.auth.decorators import login_required
from django.db.models import Sum
from .forms import RegisterForm, TransactionForm, GoalForm
from .models import Transaction, Goal

def register_user(request):
    f = RegisterForm(request.POST or None)
    if f.is_valid(): return login(request, f.save()) or redirect('dashboard')
    return render(request, 'form.html', {'f': f, 't': 'Create Account'})

@login_required
def dashboard(request):
    tx, gl = Transaction.objects.filter(user=request.user), Goal.objects.filter(user=request.user)
    inc = tx.filter(transaction_type='Income').aggregate(Sum('amount'))['amount__sum'] or 0
    exp = tx.filter(transaction_type='Expense').aggregate(Sum('amount'))['amount__sum'] or 0
    gp = [{'g': i, 'p': round(min((i.saved_amount/i.target_amount)*100, 100), 1) if i.target_amount else 0} for i in gl]
    return render(request, 'dashboard.html', {'tx': tx.order_by('-date')[:5], 'gp': gp, 'inc': inc, 'exp': exp, 'net': inc-exp})

@login_required
def add_transaction(request):
    f = TransactionForm(request.POST or None)
    if f.is_valid(): o = f.save(commit=False); o.user = request.user; o.save(); return redirect('dashboard')
    return render(request, 'form.html', {'f': f, 't': 'Add Transaction'})

@login_required
def add_goal(request):
    f = GoalForm(request.POST or None)
    if f.is_valid(): o = f.save(commit=False); o.user = request.user; o.save(); return redirect('dashboard')
    return render(request, 'form.html', {'f': f, 't': 'Add Goal'})

@login_required
def edit_goal(request, id):
    obj = Goal.objects.get(id=id, user=request.user)
    f = GoalForm(request.POST or None, instance=obj)
    if f.is_valid(): f.save(); return redirect('dashboard')
    return render(request, 'form.html', {'f': f, 't': 'Update Goal'})

@login_required
def transaction_list(request):
    return render(request, 'transaction_list.html', {'tx': Transaction.objects.filter(user=request.user).order_by('-date')})

