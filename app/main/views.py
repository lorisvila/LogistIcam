import json
from django.contrib.auth import logout
from django.db.models import Q, Case, When
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse_lazy
from django.views.generic import DeleteView
from .common_functions import filter_transactions
from .forms import StockForm, TransactionForm, ClientForm
from .models import Stock, Client
from datetime import timedelta
from django.http import Http404
from datetime import datetime
from decimal import Decimal
from django.shortcuts import render
from django.contrib.auth.decorators import permission_required
from django.db.models import Sum, Count, F, ExpressionWrapper, DecimalField
from django.utils import timezone

from .models import Transaction

@permission_required('main.view_transaction', login_url='/login/')
def page_accueil_view(request):
    # 1) Début du mois courant
    now = timezone.now()
    month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)

    # 2) Filtrer les transactions du mois
    trans_month = Transaction.objects.filter(time__gte=month_start)
    ventes = trans_month.filter(type='Vente')
    achats = trans_month.filter(type='Achat')

    # 3) Nombre de ventes
    nb_ventes = ventes.count()

    # 4) Chiffre d'affaires du mois (= somme quantité * prix_vente)
    ca_aggregate = ventes.annotate(
        revenue=ExpressionWrapper(
            F('quantity') * F('produit__prix_vente'),
            output_field=DecimalField(max_digits=14, decimal_places=2)
        )
    ).aggregate(total_ca=Sum('revenue'))
    chiffre_affaires = ca_aggregate['total_ca'] or Decimal('0.00')

    # 5) Coût d'achat du mois (= somme quantité * prix_achat)
    cost_aggregate = ventes.annotate(
        cost=ExpressionWrapper(
            F('quantity') * F('produit__prix_achat'),
            output_field=DecimalField(max_digits=14, decimal_places=2)
        )
    ).aggregate(total_cost=Sum('cost'))
    total_cost = cost_aggregate['total_cost'] or Decimal('0.00')

    # 6) Bénéfice du mois
    benefice = chiffre_affaires - total_cost

    # 7) Articles les plus vendus (top 5)
    articles_most_sold = (
        ventes
        .values('produit__produit')
        .annotate(total_qty=Sum('quantity'))
        .order_by('-total_qty')[:5]
    )

    # 8) Articles les plus achetés (top 5)
    articles_most_bought = (
        achats
        .values('produit__produit')
        .annotate(total_qty=Sum('quantity'))
        .order_by('-total_qty')[:5]
    )

    # 9) Client du mois (celui qui a généré le plus de CA)
    client_spend = (
        ventes
        .filter(client__isnull=False)
        .annotate(spent=ExpressionWrapper(
            F('quantity') * F('produit__prix_vente'),
            output_field=DecimalField(max_digits=14, decimal_places=2)
        ))
        .values('client', 'client__name', 'client__surname')
        .annotate(total_spent=Sum('spent'))
        .order_by('-total_spent')
    )
    if client_spend:
        top = client_spend[0]
        client_of_month = {
            'id': top['client'],
            'name': f"{top['client__name']} {top['client__surname']}",
            'total_spent': top['total_spent']
        }
    else:
        client_of_month = None

    # 10) Passage du contexte à la vue
    context = {
        'nb_ventes': nb_ventes,
        'chiffre_affaires': chiffre_affaires,
        'benefice': benefice,
        'articles_most_sold': articles_most_sold,
        'articles_most_bought': articles_most_bought,
        'client_of_month': client_of_month,
    }
    return render(request, 'page_accueil.html', context)

@permission_required('main.view_transaction', login_url='/login/')
def page_transactions_view(request):
    transactions = Transaction.objects.all().order_by('-time')

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

    context = {'clients': clients}
    return render(request, 'clients/page_clients.html', context)

@permission_required('main.add_stock', login_url='/login/')
def page_add_client(request):
    if request.method == 'POST':
        form = ClientForm(request.POST)
        if form.is_valid():
            form.save()
            return redirect('main:list_clients')
    else:
        form = ClientForm()

    return render(request, 'clients/page_add_client.html', {'form': form})