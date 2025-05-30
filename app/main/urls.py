from django.contrib import admin
from django.contrib.auth.views import LoginView, LogoutView
from django.urls import path, include
from django.views.generic import RedirectView

from . import views

app_name = 'main'

urlpatterns = [
    path('', RedirectView.as_view(url='/accueil/')), # Rediriger si le client demande "/"

    path("admin/", admin.site.urls),
    path('login/', LoginView.as_view(), name='login'),
    path('logout/', LogoutView.as_view(), name='logout'),

    path('accueil/', views.page_accueil_view, name='home'),
    path('transactions/list', views.page_transactions_view, name='list_transactions'),
    path('stocks/list', views.page_stocks_view, name='list_stocks'),
    path('stocks/<int:pk>/edit/', views.page_edit_stock, name='edit_stock'),
    path('stocks/<int:pk>/delete/', views.StockDeleteView.as_view(), name='delete_stock'),
    path('stocks/add/', views.page_add_stock, name='add_stock')
]