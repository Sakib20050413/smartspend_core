from django.urls import path
from . import views

urlpatterns = [
    path('', views.dashboard_view, name='dashboard'),
    path('login/', views.login_view, name='login'),
    path('register/', views.register_view, name='register'),
    path('logout/', views.logout_view, name='logout'),
    path('deposit/', views.deposit_view, name='deposit'),
    path('transfer/', views.transfer_view, name='transfer'),
    path('exchange/', views.exchange_view, name='exchange'),
    path('cards/', views.cards_view, name='cards'),
    path('transactions/', views.transactions_view, name='transactions'),
    path('security/', views.security_view, name='security'),
]
