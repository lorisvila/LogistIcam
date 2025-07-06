import io
from datetime import timedelta

import matplotlib.pyplot as plt
from django.contrib.auth.decorators import permission_required
from django.db.models import Q, Case, When
from django.db.models import Sum, Count, F, ExpressionWrapper, DecimalField
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
from reportlab.platypus import SimpleDocTemplate, Paragraph, Table, TableStyle, Image, Spacer

from ..forms import ClientForm
from ..models import Client, Transaction, ExtractMonth, ExtractYear


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


@permission_required('main.add_client', login_url='/login/')
def page_add_client(request):
    if request.method == 'POST':
        form = ClientForm(request.POST)
        if form.is_valid():
            form.save()
            return redirect('main:list_clients')
    else:
        form = ClientForm()

    return render(request, 'clients/page_add_client.html', {'form': form})


@permission_required('main.edit_client', login_url='/login/')
def page_edit_client(request, pk):
    client = get_object_or_404(Client, pk=pk)

    if request.method == 'POST':
        form = ClientForm(request.POST, instance=client)
        if form.is_valid():
            form.save()
            return redirect('main:list_clients')
    else:
        form = ClientForm(instance=client)

    return render(request, 'clients/page_edit_client.html', {'form': form})


class ClientDeleteView(DeleteView):
    model = Client
    success_url = reverse_lazy('main:list_clients')
    template_name = 'clients/page_delete_client.html'


@permission_required('main.view_client', login_url='/login/')
def generate_client_pdf_report(request, client_id):
    try:
        client = Client.objects.get(pk=client_id)
    except Client.DoesNotExist:
        return HttpResponse('Client non trouvé', status=404)

    # Création du buffer pour le PDF
    buffer = io.BytesIO()

    # Définition des intervalles de temps
    now = timezone.now()
    today = now.replace(hour=0, minute=0, second=0, microsecond=0)
    yesterday = today - timedelta(days=1)
    week_start = now - timedelta(days=now.weekday())
    month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)

    # Récupération de toutes les transactions du client
    client_transactions = Transaction.objects.filter(client=client).order_by('-time')

    # Produit le plus acheté
    most_purchased_product = None
    if client.type == "Client":
        product_counts = client_transactions.filter(type="Vente").values('produit__produit').annotate(
            total=Sum('quantity')
        ).order_by('-total').first()
    else:  # Fournisseur
        product_counts = client_transactions.filter(type="Achat").values('produit__produit').annotate(
            total=Sum('quantity')
        ).order_by('-total').first()

    most_purchased_product = product_counts['produit__produit'] if product_counts else "Aucun"
    most_purchased_quantity = product_counts['total'] if product_counts else 0

    # Calcul des statistiques par période
    hour_transactions = client_transactions.filter(time__gte=now - timedelta(hours=1))
    today_transactions = client_transactions.filter(time__gte=today)
    yesterday_transactions = client_transactions.filter(time__range=[yesterday, today])
    week_transactions = client_transactions.filter(time__gte=week_start)
    month_transactions = client_transactions.filter(time__gte=month_start)

    # Statistiques de vente/achat
    stats = {
        'hour': {
            'sells': hour_transactions.filter(type='Vente').aggregate(
                count=Count('id'),
                amount=Sum('price')
            ),
            'buys': hour_transactions.filter(type='Achat').aggregate(
                count=Count('id'),
                amount=Sum('price')
            )
        },
        'today': {
            'sells': today_transactions.filter(type='Vente').aggregate(
                count=Count('id'),
                amount=Sum('price')
            ),
            'buys': today_transactions.filter(type='Achat').aggregate(
                count=Count('id'),
                amount=Sum('price')
            )
        },
        'yesterday': {
            'sells': yesterday_transactions.filter(type='Vente').aggregate(
                count=Count('id'),
                amount=Sum('price')
            ),
            'buys': yesterday_transactions.filter(type='Achat').aggregate(
                count=Count('id'),
                amount=Sum('price')
            )
        },
        'week': {
            'sells': week_transactions.filter(type='Vente').aggregate(
                count=Count('id'),
                amount=Sum('price')
            ),
            'buys': week_transactions.filter(type='Achat').aggregate(
                count=Count('id'),
                amount=Sum('price')
            )
        },
        'month': {
            'sells': month_transactions.filter(type='Vente').aggregate(
                count=Count('id'),
                amount=Sum('price')
            ),
            'buys': month_transactions.filter(type='Achat').aggregate(
                count=Count('id'),
                amount=Sum('price')
            )
        },
        'all_time': {
            'sells': client_transactions.filter(type='Vente').aggregate(
                count=Count('id'),
                amount=Sum('price')
            ),
            'buys': client_transactions.filter(type='Achat').aggregate(
                count=Count('id'),
                amount=Sum('price')
            )
        }
    }

    # Statistiques générales du client
    total_transactions = client_transactions.count()
    total_amount = client_transactions.aggregate(total=Sum('price'))['total'] or 0

    # Si c'est un client (qui achète)
    if client.type == "Client":
        benefit_transactions = client_transactions.filter(type='Vente').annotate(
            margin=ExpressionWrapper(
                F('price') - (F('produit__prix_achat') * F('quantity')),
                output_field=DecimalField()
            )
        )
        total_benefit = benefit_transactions.aggregate(total=Sum('margin'))['total'] or 0
    # Si c'est un fournisseur
    else:
        total_benefit = "N/A"

    # Création d'un graphique d'activité mensuelle
    last_year = now - timedelta(days=365)
    monthly_activity = client_transactions.filter(time__gte=last_year).annotate(
        month=ExtractMonth('time'),
        year=ExtractYear('time')
    ).values('month', 'year').annotate(
        count=Count('id'),
        total=Sum('price')
    ).order_by('year', 'month')

    months = []
    counts = []
    for item in monthly_activity:
        months.append(f"{item['year']}-{item['month']}")
        counts.append(item['count'])

    # Graphique d'activité mensuelle
    if months and counts:
        plt.figure(figsize=(10, 4))
        plt.bar(range(len(counts)), counts, color='skyblue')
        plt.title('Activité mensuelle')
        plt.xlabel('Mois')
        plt.ylabel('Nombre de transactions')
        plt.xticks(range(len(months)), months, rotation=45)
        plt.tight_layout()
        activity_chart = io.BytesIO()
        plt.savefig(activity_chart, format='png')
        plt.close()
    else:
        activity_chart = None

    # Génération du PDF
    doc = SimpleDocTemplate(buffer, pagesize=letter)
    styles = getSampleStyleSheet()
    elements = []

    # Titre
    elements.append(Paragraph(f"Rapport client: {client.name} {client.surname}", styles['Title']))
    elements.append(Paragraph(f"Type: {client.type}", styles['Heading3']))
    elements.append(Paragraph(f"Date du rapport: {now.strftime('%Y-%m-%d %H:%M')}", styles['Heading3']))
    elements.append(Spacer(1, 20))

    # Statistiques du client
    elements.append(Paragraph("Statistiques générales", styles['Heading2']))

    client_stats_data = [
        ["Métrique", "Valeur"],
        ["Nombre total de transactions", total_transactions],
        ["Produit le plus {0}".format("acheté" if client.type == "Client" else "vendu"), most_purchased_product],
        ["Quantité", most_purchased_quantity],
        ["Montant total des transactions", f"{total_amount:.2f}€"],
    ]

    if client.type == "Client":
        client_stats_data.append(["Bénéfice total", f"{total_benefit:.2f}€"])

    client_stats_table = Table(client_stats_data)
    client_stats_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('FONTSIZE', (0, 0), (-1, 0), 12),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
        ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
        ('GRID', (0, 0), (-1, -1), 1, colors.black),
    ]))
    elements.append(client_stats_table)
    elements.append(Spacer(1, 20))

    # Tableau des statistiques par période
    elements.append(Paragraph("Transactions par période", styles['Heading2']))

    period_data = [
        ["Période", "Ventes (Nb)", "Ventes (€)", "Achats (Nb)", "Achats (€)"]
    ]

    for period, data in [
        ("Dernière heure", stats['hour']),
        ("Aujourd'hui", stats['today']),
        ("Hier", stats['yesterday']),
        ("Cette semaine", stats['week']),
        ("Ce mois", stats['month']),
        ("Total", stats['all_time'])
    ]:
        period_data.append([
            period,
            data['sells']['count'],
            f"{data['sells']['amount'] or 0:.2f}€",
            data['buys']['count'],
            f"{data['buys']['amount'] or 0:.2f}€"
        ])

    period_table = Table(period_data)
    period_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.lightblue),
        ('GRID', (0, 0), (-1, -1), 1, colors.black),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
    ]))
    elements.append(period_table)
    elements.append(Spacer(1, 20))

    # Tableau de toutes les transactions
    elements.append(Paragraph("Liste des transactions", styles['Heading2']))

    if client_transactions:
        trans_data = [["Date", "Type", "Produit", "Quantité", "Montant"]]
        for trans in client_transactions[:50]:  # Limité à 50 transactions pour éviter un PDF trop volumineux
            trans_data.append([
                trans.time.strftime("%Y-%m-%d %H:%M"),
                trans.type,
                trans.produit.produit,
                trans.quantity,
                f"{trans.price:.2f}€"
            ])

        trans_table = Table(trans_data)
        trans_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.lightblue),
            ('GRID', (0, 0), (-1, -1), 1, colors.black),
            ('FONTSIZE', (0, 0), (-1, -1), 8),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ]))
        elements.append(trans_table)
    else:
        elements.append(Paragraph("Aucune transaction trouvée", styles['Normal']))

    elements.append(Spacer(1, 20))

    # Graphique d'activité mensuelle
    if activity_chart:
        elements.append(Paragraph("Activité mensuelle", styles['Heading2']))
        activity_chart.seek(0)
        elements.append(Image(activity_chart, 7 * inch, 3 * inch))

    # Construction du PDF
    doc.build(elements)

    # Création de la réponse HTTP
    buffer.seek(0)
    response = HttpResponse(buffer, content_type='application/pdf')
    response['Content-Disposition'] = f'attachment; filename="rapport_client_{client_id}.pdf"'

    return response
