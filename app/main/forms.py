from django import forms
from .models import Stock, Transaction, Client


class StockForm(forms.ModelForm):
    class Meta:
        model = Stock
        fields = ['produit', 'quantity', 'prix_vente', 'prix_achat']

class TransactionForm(forms.ModelForm):
    class Meta:
        model = Transaction
        fields = ['type', 'produit', 'quantity', 'client']

class ClientForm(forms.ModelForm):
    class Meta:
        model = Client
        fields = ['name', 'surname', 'type']