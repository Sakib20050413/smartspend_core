from django.shortcuts import render, redirect
from django.views import View
from .forms import RegisterForm
from django.contrib.auth import login
from django.contrib.auth.mixins import LoginRequiredMixin 
class RegisterView(View):
    def get(self, request):
        form = RegisterForm()
        return render(request, 'finance/register.html', {'form': form})

    def post(self, request):
        form = RegisterForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
            return redirect('dashboard')
        return render(request, 'finance/register.html', {'form': form})

class DashboardView(LoginRequiredMixin, View):
    def get(self, request):
        return render(request, 'finance/dashboard.html')