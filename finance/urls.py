from django.urls import path
from .views import RegisterView, DashboardView

urlpatterns = [
    path('register/', RegisterView.as_view(), name='register'),
    path('', DashboardView.as_view(), name='dashboard'), 
]