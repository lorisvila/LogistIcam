import json
from datetime import datetime
from django.contrib.auth import logout
from django.contrib.auth.decorators import permission_required
from django.db.models import Count, Sum, Q, F, DecimalField, ExpressionWrapper, Case, When
from django.shortcuts import render, get_object_or_404, redirect
from django.urls import reverse_lazy
from django.views.generic import DeleteView

from . import models
from .common_functions import filter_transactions
from .forms import StockForm, TransactionForm
from .models import Transaction, Stock, Client
from datetime import timedelta
from django.http import Http404

@permission_required('main.view_transaction', login_url='/login/')
def page_accueil_view(request):
    return render(request, 'page_accueil.html')

@permission_required('main.view_transaction', login_url='/login/')
def page_transactions_view(request):
    transactions = Transaction.objects.all()

    transactions = filter_transactions(transactions, request)

    # Filtrage par date
    start_date = request.GET.get('start_date')
    end_date = request.GET.get('end_date')

    if start_date and end_date:
        start_date = datetime.strptime(start_date, '%Y-%m-%d')
        end_date = datetime.strptime(end_date, '%Y-%m-%d') + timedelta(days=1)
        transactions = transactions.filter(time__range=[start_date, end_date])

    return render(request, 'transactions/page_transactions.html', {
        'transactions': transactions,
        'show_date': True,
    })

@permission_required('main.add_transaction', login_url='/login/')
def page_add_transaction(request):
    if request.method == 'POST':
        form = TransactionForm(request.POST)
        if form.is_valid():
            from django.db import transaction
            from django.db import IntegrityError
            try:
                with transaction.atomic():
                    # Save transaction without committing to DB
                    transaction = form.save(commit=False)

                    # Fetch associated stock object
                    stock = transaction.produit

                    # Apply stock changes based on transaction type
                    if transaction.type == "Vente":
                        if stock.quantity < transaction.quantity:
                            raise ValueError("Stock insuffisant !")
                        transaction.price = stock.prix_vente * transaction.quantity
                        stock.quantity -= transaction.quantity
                    else:  # Achat
                        transaction.price = stock.prix_achat * transaction.quantity
                        stock.quantity += transaction.quantity

                    # Save updated stock and set new_stock_qt
                    stock.save()
                    transaction.new_stock_qt = stock.quantity
                    transaction.save()

                    return redirect('main:list_transactions')

            except ValueError as e:
                form.add_error('quantity', str(e))

            except IntegrityError:
                form.add_error(None, "Erreur système. Veuillez réessayer.")

    else:
        form = TransactionForm()

    return render(request, 'transactions/page_add_transaction.html', {'form': form})

@permission_required('main.view_stock', login_url='/login/')
def page_stocks_view(request):
    stocks = Stock.objects.annotate(
            retail_value=ExpressionWrapper(
                F("prix_vente") * F("quantity"),
                output_field=DecimalField(max_digits=10, decimal_places=2, default=0)
            )
            ).all()
    return render(request, 'stocks/page_stocks.html', {
        'stocks': stocks
    })

@permission_required('main.edit_stock', login_url='/login/')
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

@permission_required('main.add_stock', login_url='/login/')
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

@permission_required('main.view_transaction', login_url='/login/')
def stock_transactions_view(request, pk):
    # Get base product
    try:
        produit = Stock.objects.get(pk=pk)
    except Stock.DoesNotExist:
        raise Http404("Product not found")

    # Base queryset
    transactions_obj = Transaction.objects.filter(produit=pk).order_by('time')

    transactions_obj = filter_transactions(transactions_obj, request)

    # Prepare data for JSON
    transactions = list(transactions_obj.values())

    # Transform data
    transactions = [
        {**t, 'price': float(t['price'])} if 'price' in t else t
        for t in transactions
    ]
    transactions = [
        {**i, 'quantity': i['quantity'] * -1} if i['type'] == 'Vente' else i
        for i in transactions
    ]

    return render(request, 'stocks/page_view_item_stock.html', {
        'produit': produit,
        'transactions': json.dumps(transactions, cls=DateTimeEncoder),
        'transactions_obj': transactions_obj,
        'time_filters': {
            'available_spans': ['hour', 'day', 'week'],
        },
        'show_date': True,
    })


class DateTimeEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, datetime):
            return obj.timestamp()  # Convert datetime to Unix timestamp
        return super().default(obj)


@permission_required('main.view_client', login_url='/login/')
def client_list(request):
    clients = Client.objects.annotate(
        transaction_count=Count('transaction'),
        total_achat=Sum(
            Case(
                When(transaction__type="Achat", then='transaction__price'),
                default=0,
                output_field=DecimalField(max_digits=10, decimal_places=2)
            )
        ),
        achat_transactions=Count('transaction', filter=Q(transaction__type="Achat")),
        total_vente=Sum(
            Case(
                When(transaction__type="Vente", then='transaction__price'),
                default=0,
                output_field=DecimalField(max_digits=10, decimal_places=2)
            )
        ),
        vente_transactions=Count('transaction', filter=Q(transaction__type="Vente"))
    ).order_by('name', 'surname')

    # For debugging - check the first client's values
    debug_client = clients.first()
    if debug_client:
        print(f"""
        Client: {debug_client.name} {debug_client.surname}
        Total transactions: {debug_client.transaction_count}
        Achat count: {debug_client.achat_transactions}
        Vente count: {debug_client.vente_transactions}
        Total Achat: {debug_client.total_achat}
        Total Vente: {debug_client.total_vente}
        """)

    context = {'clients': clients}
    return render(request, 'clients/page_clients.html', context)