from django.db.models import ExpressionWrapper, F, DecimalField
from django.shortcuts import render, get_object_or_404, redirect
from django.urls import reverse_lazy
from django.views.generic import DeleteView

from .forms import StockForm
from .models import Transaction, Stock


def page_accueil_view(request):
    return render(request, 'page_accueil.html')

def page_transactions_view(request):
    transactions = Transaction.objects.all()
    return render(request, 'transactions/page_transactions.html', {
        'transactions': transactions
    })

def page_stocks_view(request):
    stocks = Stock.objects.annotate(
            total_price=ExpressionWrapper(
                F("prix_unitaire") * F("quantity"),
                output_field=DecimalField(max_digits=10, decimal_places=2, default=0)
            )).all()
    return render(request, 'stocks/page_stocks.html', {
        'stocks': stocks
    })


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