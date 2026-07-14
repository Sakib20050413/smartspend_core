from django.urls import path
from . import views

urlpatterns = [
    path('register/', views.register_user, name='register'),
    path('', views.dashboard, name='dashboard'),
    path('transaction/add/', views.add_transaction, name='add_transaction'),
    path('goal/add/', views.add_goal, name='add_goal'),
    path('transactions/', views.transaction_list, name='transaction_list'),
]