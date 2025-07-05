import io
import json
from datetime import datetime, timedelta

import matplotlib.pyplot as plt
from django.contrib.auth.decorators import permission_required
from django.db.models import Sum, F, ExpressionWrapper, DecimalField
from django.http import Http404
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, redirect
from django.shortcuts import render
from django.urls import reverse_lazy
from django.utils import timezone
from django.views.generic import DeleteView
from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.units import inch
from reportlab.platypus import SimpleDocTemplate, Paragraph, Table, TableStyle, Spacer, Image

from ..common_functions import filter_transactions
from ..forms import StockForm
from ..models import Transaction, Stock


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


@permission_required('main.view_transaction', login_url='/login/')
def generate_stock_item_pdf(request, pk):
    # Vérifier si l'article existe
    try:
        stock_item = Stock.objects.get(pk=pk)
    except Stock.DoesNotExist:
        return HttpResponse("Article non trouvé", status=404)

    # 1. Créer un buffer BytesIO pour générer le PDF
    buffer = io.BytesIO()

    # 2. Calculer les plages de dates
    now = timezone.now()
    hour_start = now - timedelta(hours=1)
    day_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    week_start = now - timedelta(days=now.weekday())
    month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    year_start = now.replace(month=1, day=1, hour=0, minute=0, second=0, microsecond=0)

    # 3. Récupérer les statistiques de vente pour différentes périodes
    sales_last_hour = Transaction.objects.filter(
        produit=stock_item,
        type='Vente',
        time__gte=hour_start
    ).aggregate(
        total_quantity=Sum('quantity'),
        total_value=Sum(ExpressionWrapper(
            F('quantity') * F('produit__prix_vente'),
            output_field=DecimalField(max_digits=14, decimal_places=2)
        ))
    )

    sales_last_day = Transaction.objects.filter(
        produit=stock_item,
        type='Vente',
        time__gte=day_start
    ).aggregate(
        total_quantity=Sum('quantity'),
        total_value=Sum(ExpressionWrapper(
            F('quantity') * F('produit__prix_vente'),
            output_field=DecimalField(max_digits=14, decimal_places=2)
        ))
    )

    sales_last_week = Transaction.objects.filter(
        produit=stock_item,
        type='Vente',
        time__gte=week_start
    ).aggregate(
        total_quantity=Sum('quantity'),
        total_value=Sum(ExpressionWrapper(
            F('quantity') * F('produit__prix_vente'),
            output_field=DecimalField(max_digits=14, decimal_places=2)
        ))
    )

    sales_last_month = Transaction.objects.filter(
        produit=stock_item,
        type='Vente',
        time__gte=month_start
    ).aggregate(
        total_quantity=Sum('quantity'),
        total_value=Sum(ExpressionWrapper(
            F('quantity') * F('produit__prix_vente'),
            output_field=DecimalField(max_digits=14, decimal_places=2)
        ))
    )

    sales_last_year = Transaction.objects.filter(
        produit=stock_item,
        type='Vente',
        time__gte=year_start
    ).aggregate(
        total_quantity=Sum('quantity'),
        total_value=Sum(ExpressionWrapper(
            F('quantity') * F('produit__prix_vente'),
            output_field=DecimalField(max_digits=14, decimal_places=2)
        ))
    )

    # 4. Récupérer les transactions des 30 derniers jours
    thirty_days_ago = now - timedelta(days=30)
    recent_transactions = Transaction.objects.filter(
        produit=stock_item,
        time__gte=thirty_days_ago
    ).order_by('-time')

    # 5. Calculer la valeur actuelle du stock et le prix de vente potentiel
    current_stock_value = stock_item.quantity * stock_item.prix_achat
    potential_retail_value = stock_item.quantity * stock_item.prix_vente
    margin = potential_retail_value - current_stock_value if potential_retail_value and current_stock_value else 0
    margin_percentage = (margin / current_stock_value * 100) if current_stock_value else 0

    # 6. Générer un graphique des transactions pour les 30 derniers jours
    dates = [(thirty_days_ago + timedelta(days=i)).date() for i in range(31)]
    sales_data = []
    purchase_data = []

    for day in dates:
        day_start = datetime.combine(day, datetime.min.time())
        day_end = datetime.combine(day, datetime.max.time())

        sales = Transaction.objects.filter(
            produit=stock_item,
            type='Vente',
            time__range=[day_start, day_end]
        ).aggregate(total=Sum('quantity'))['total'] or 0

        purchases = Transaction.objects.filter(
            produit=stock_item,
            type='Achat',
            time__range=[day_start, day_end]
        ).aggregate(total=Sum('quantity'))['total'] or 0

        sales_data.append(sales)
        purchase_data.append(purchases)

    plt.figure(figsize=(10, 5))
    plt.bar(range(len(dates)), sales_data, color='blue', label='Ventes')
    plt.bar(range(len(dates)), purchase_data, color='green', label='Achats', bottom=sales_data)
    plt.title(f'Transactions pour {stock_item.produit} (30 derniers jours)')
    plt.xlabel('Date')
    plt.ylabel('Quantité')
    plt.legend()
    plt.xticks(range(0, len(dates), 5), [dates[i].strftime('%d/%m') for i in range(0, len(dates), 5)])

    transactions_chart = io.BytesIO()
    plt.savefig(transactions_chart, format='png')
    plt.close()

    # 7. Générer le PDF
    doc = SimpleDocTemplate(buffer, pagesize=letter)
    styles = getSampleStyleSheet()
    elements = []

    # Titre
    elements.append(Paragraph(f"Rapport détaillé de l'article : {stock_item.produit}", styles['Title']))
    elements.append(Paragraph(f"Généré le : {now.strftime('%d/%m/%Y à %H:%M')}", styles['Normal']))
    elements.append(Spacer(1, 12))

    # Informations sur l'article
    elements.append(Paragraph("Détails de l'article", styles['Heading2']))
    item_data = [
        ["Champ", "Valeur"],
        ["ID", stock_item.pk],
        ["Produit", stock_item.produit],
        ["Quantité en stock", stock_item.quantity],
        ["Prix d'achat", f"{stock_item.prix_achat:.2f}€"],
        ["Prix de vente", f"{stock_item.prix_vente:.2f}€"],
    ]
    item_table = Table(item_data)
    item_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
        ('FONTSIZE', (0, 0), (-1, 0), 12),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
        ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
        ('GRID', (0, 0), (-1, -1), 1, colors.black),
    ]))
    elements.append(item_table)
    elements.append(Spacer(1, 12))

    # Valeur actuelle et potentielle
    elements.append(Paragraph("Valorisation du stock", styles['Heading2']))
    value_data = [
        ["Métrique", "Valeur"],
        ["Valeur d'achat en stock", f"{current_stock_value:.2f}€"],
        ["Valeur potentielle de vente", f"{potential_retail_value:.2f}€"],
        ["Marge potentielle", f"{margin:.2f}€"],
        ["Pourcentage de marge", f"{margin_percentage:.2f}%"],
    ]
    value_table = Table(value_data)
    value_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
        ('FONTSIZE', (0, 0), (-1, 0), 12),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
        ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
        ('GRID', (0, 0), (-1, -1), 1, colors.black),
    ]))
    elements.append(value_table)
    elements.append(Spacer(1, 12))

    # Statistiques de vente
    elements.append(Paragraph("Statistiques de vente", styles['Heading2']))
    sales_data = [
        ["Période", "Quantité vendue", "Valeur des ventes"],
        ["Dernière heure", sales_last_hour['total_quantity'] or 0, f"{sales_last_hour['total_value'] or 0:.2f}€"],
        ["Aujourd'hui", sales_last_day['total_quantity'] or 0, f"{sales_last_day['total_value'] or 0:.2f}€"],
        ["Cette semaine", sales_last_week['total_quantity'] or 0, f"{sales_last_week['total_value'] or 0:.2f}€"],
        ["Ce mois-ci", sales_last_month['total_quantity'] or 0, f"{sales_last_month['total_value'] or 0:.2f}€"],
        ["Cette année", sales_last_year['total_quantity'] or 0, f"{sales_last_year['total_value'] or 0:.2f}€"],
    ]
    sales_table = Table(sales_data)
    sales_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
        ('FONTSIZE', (0, 0), (-1, 0), 12),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
        ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
        ('GRID', (0, 0), (-1, -1), 1, colors.black),
    ]))
    elements.append(sales_table)
    elements.append(Spacer(1, 12))

    # Graphique des transactions
    elements.append(Paragraph("Évolution des transactions (30 derniers jours)", styles['Heading2']))
    transactions_chart.seek(0)
    elements.append(Image(transactions_chart, 7 * inch, 3.5 * inch))
    elements.append(Spacer(1, 12))

    # Transactions récentes
    elements.append(Paragraph("Historique des 30 derniers jours", styles['Heading2']))
    if recent_transactions:
        trans_data = [["Date", "Type", "Quantité", "Prix Total", "Client/Fournisseur"]]
        for trans in recent_transactions:
            client_name = f"{trans.client.name} {trans.client.surname}" if trans.client else "N/A"
            if trans.type == 'Vente':
                total_price = trans.quantity * stock_item.prix_vente
            else:
                total_price = trans.price * trans.quantity if trans.price else 0

            trans_data.append([
                trans.time.strftime("%d/%m/%Y %H:%M"),
                trans.type,
                trans.quantity,
                f"{total_price:.2f}€",
                client_name
            ])
        trans_table = Table(trans_data)
        trans_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('FONTSIZE', (0, 0), (-1, 0), 12),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
            ('GRID', (0, 0), (-1, -1), 1, colors.black),
        ]))
        elements.append(trans_table)
    else:
        elements.append(Paragraph("Aucune transaction au cours des 30 derniers jours.", styles['Normal']))

    # Générer le PDF
    doc.build(elements)

    # Créer la réponse HTTP
    buffer.seek(0)
    response = HttpResponse(buffer, content_type='application/pdf')
    response[
        'Content-Disposition'] = f'attachment; filename="rapport_{stock_item.produit}_{now.strftime("%Y%m%d")}.pdf"'

    return response
