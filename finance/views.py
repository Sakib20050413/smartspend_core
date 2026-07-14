from django.shortcuts import render, redirect
from django.contrib.auth import login
from django.contrib.auth.decorators import login_required
from django.db.models import Sum
from .forms import RegisterForm, TransactionForm, GoalForm
from .models import Transaction, Goal

def register_user(request):
    if request.method == 'POST':
        form = RegisterForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user) # অ্যাকাউন্ট খোলার পর লগ-ইন
            return redirect('dashboard')
    else:
        form = RegisterForm()
    
    return render(request, 'finance/register.html', {'form': form})

@login_required
def dashboard(request):
    transactions = Transaction.objects.filter(user=request.user)
    goals = Goal.objects.filter(user=request.user)

    total_income = transactions.filter(transaction_type='Income').aggregate(Sum('amount'))['amount__sum'] or 0
    total_expense = transactions.filter(transaction_type='Expense').aggregate(Sum('amount'))['amount__sum'] or 0
    net_savings = total_income - total_expense

    goal_progress = []
    remaining_savings = net_savings
    
    for goal in goals:
        if remaining_savings >= goal.target_amount:
            progress = 100
            remaining_savings -= goal.target_amount
        elif remaining_savings > 0:
            progress = (remaining_savings / goal.target_amount) * 100
            remaining_savings = 0
        else:
            progress = 0
        
        goal_progress.append({
            'goal': goal,
            'progress': round(progress, 2)
        })

    context = {
        'total_income': total_income,
        'total_expense': total_expense,
        'net_savings': net_savings,
        'goal_progress': goal_progress,
    }
    return render(request, 'finance/dashboard.html', context)

@login_required
def add_transaction(request):
    if request.method == 'POST':
        form = TransactionForm(request.POST)
        if form.is_valid():
            transaction = form.save(commit=False)
            transaction.user = request.user
            transaction.save()
            return redirect('dashboard')
    else:
        form = TransactionForm()
        
    return render(request, 'finance/transaction_form.html', {'form': form})

@login_required
def add_goal(request):
    if request.method == 'POST':
        form = GoalForm(request.POST)
        if form.is_valid():
            goal = form.save(commit=False)
            goal.user = request.user
            goal.save()
            return redirect('dashboard')
    else:
        form = GoalForm()
        
    return render(request, 'finance/goal_form.html', {'form': form})

@login_required
def transaction_list(request):
    transactions = Transaction.objects.filter(user=request.user).order_by('-date')
    return render(request, 'finance/transaction_list.html', {'transactions': transactions})