from django.contrib.auth import logout
from django.contrib.auth.decorators import user_passes_test
from django.db.models import ExpressionWrapper, F, DecimalField
from django.shortcuts import render, get_object_or_404, redirect
from django.urls import reverse_lazy
from django.views.generic import DeleteView

from .forms import StockForm
from .models import Transaction, Stock

def group_required(*group_names):
    """Verify user is in at least one of the required groups"""
    def in_groups(user):
        if user.is_authenticated:
            if bool(user.groups.filter(name__in=group_names)) | user.is_superuser:
                return True
        return False
    return user_passes_test(in_groups)

def page_accueil_view(request):
    return render(request, 'page_accueil.html')

@group_required('editor', 'viewer')
def page_transactions_view(request):
    transactions = Transaction.objects.all()
    return render(request, 'transactions/page_transactions.html', {
        'transactions': transactions
    })

@group_required('editor', 'viewer')
def page_stocks_view(request):
    stocks = Stock.objects.annotate(
            total_price=ExpressionWrapper(
                F("prix_unitaire") * F("quantity"),
                output_field=DecimalField(max_digits=10, decimal_places=2, default=0)
            )).all()
    return render(request, 'stocks/page_stocks.html', {
        'stocks': stocks
    })

@group_required('editor')
def page_edit_stock(request, pk):
    stock = get_object_or_404(Stock, pk=pk)

    if request.method == 'POST':
        form = StockForm(request.POST, instance=stock)
        if form.is_valid():
            form.save()
            return redirect('main:list_stocks')
    else:
        form = StockForm(instance=stock)

    return render(request, 'stocks/page_edit_stock.html', {'form': form})

def page_add_stock(request):
    if request.method == 'POST':
        form = StockForm(request.POST)
        if form.is_valid():
            form.save()
            return redirect('main:list_stocks')
    else:
        form = StockForm()

    return render(request, 'stocks/page_add_stock.html', {'form': form})

class StockDeleteView(DeleteView):
    model = Stock
    success_url = reverse_lazy('main:list_stocks')
    template_name = 'stocks/page_delete_stock.html'

def logout_view(request):
    logout(request)
    return redirect('main:home')