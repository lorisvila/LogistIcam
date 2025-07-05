from django.contrib import admin
from django.contrib.auth.views import LoginView, LogoutView
from django.urls import path
from django.views.generic import RedirectView

from main.views import stock_views, client_views, common_views, transaction_views

app_name = 'main'

urlpatterns = [
    path('', RedirectView.as_view(url='/accueil/')), # Rediriger si le client demande "/"

    path("admin/", admin.site.urls, name='admin'),
    path('login/', LoginView.as_view(), name='login'),
    path('logout/', LogoutView.as_view(), name='logout'),

    path('accueil/', common_views.page_accueil_view, name='home'),

    path('transactions/list', transaction_views.page_transactions_view, name='list_transactions'),
    path('transactions/add/', transaction_views.page_add_transaction, name='add_transaction'),
    path('transactions/pdf/', transaction_views.generate_transactions_pdf_report, name='all_transactions'),

    path('stocks/list', stock_views.page_stocks_view, name='list_stocks'),
    path('stocks/<int:pk>/edit/', stock_views.page_edit_stock, name='edit_stock'),
    path('stocks/<int:pk>/delete/', stock_views.StockDeleteView.as_view(), name='delete_stock'),
    path('stocks/<int:pk>/details/', stock_views.stock_transactions_view, name='details_stock'),
    path('stocks/<int:pk>/pdf/', stock_views.generate_stock_item_pdf, name='generate_stock_item_pdf'),
    path('stocks/add/', stock_views.page_add_stock, name='add_stock'),

    path('clients/list', client_views.client_list, name='list_clients'),
    path('clients/add/', client_views.page_add_client, name='add_client'),
    path('clients/<int:pk>/edit/', client_views.page_edit_client, name='edit_client'),
    path('clients/<int:pk>/delete/', client_views.ClientDeleteView.as_view(), name='delete_client'),
    path('clients/<int:client_id>/pdf/', client_views.generate_client_pdf_report, name='client_pdf_report'),
]