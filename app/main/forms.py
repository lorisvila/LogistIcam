from django import forms
from .models import Stock, Transaction, Client


class StockForm(forms.ModelForm):
    class Meta:
        model = Stock
        fields = ['produit', 'quantity', 'prix_vente']

class TransactionForm(forms.ModelForm):
    class Meta:
        model = Transaction
        fields = ['type', 'produit', 'quantity', 'client']