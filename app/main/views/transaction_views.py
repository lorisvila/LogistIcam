import io
from datetime import datetime, timedelta

import matplotlib.pyplot as plt
from django.contrib.auth.decorators import permission_required
from django.db.models import Sum, F, ExpressionWrapper, DecimalField
from django.http import HttpResponse
from django.shortcuts import redirect
from django.shortcuts import render
from django.utils import timezone
from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.units import inch
from reportlab.platypus import SimpleDocTemplate, Paragraph, Table, TableStyle, Image

from ..common_functions import filter_transactions
from ..forms import TransactionForm
from ..models import Transaction, Stock


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


@permission_required('main.view_transaction', login_url='/login/')
def generate_transactions_pdf_report(request):
    # 1. Create BytesIO buffer for PDF generation
    buffer = io.BytesIO()

    # 2. Calculate date ranges
    now = timezone.now()
    month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    week_start = now - timedelta(days=now.weekday())
    week_end = week_start + timedelta(days=6)

    # 3. Calculate KPIs
    # Value at date (stock value)
    stock_value = Stock.objects.aggregate(
        valeur_stock=Sum(
            ExpressionWrapper(
                F('quantity') * F('prix_vente'),
                output_field=DecimalField(max_digits=14, decimal_places=2)
            )
        )
    )['valeur_stock'] or 0.0

    # Transaction counts
    month_count = Transaction.objects.filter(time__gte=month_start).count()
    week_count = Transaction.objects.filter(time__range=[week_start, week_end]).count()

    # Recent transactions for extract
    recent_transactions = Transaction.objects.filter(
        time__gte=month_start
    ).order_by('-time')[:10]

    # Daily transaction counts
    dates = [(month_start + timedelta(days=i)).date() for i in range(32)
             if (month_start + timedelta(days=i)).month == month_start.month]
    daily_counts = []
    for day in dates:
        day_start = datetime.combine(day, datetime.min.time())
        day_end = datetime.combine(day, datetime.max.time())
        sales = Transaction.objects.filter(
            type='Vente', time__range=[day_start, day_end]
        ).count()
        purchases = Transaction.objects.filter(
            type='Achat', time__range=[day_start, day_end]
        ).count()
        total = sales + purchases
        daily_counts.append(total)

    # Stock levels for top products
    top_products = Stock.objects.annotate(
        value=ExpressionWrapper(
            F('quantity') * F('prix_vente'),
            output_field=DecimalField(max_digits=14, decimal_places=2)
        )
    ).order_by('-quantity')[:5]

    # 4. Generate charts
    plt.figure(figsize=(8, 4))
    plt.bar(range(len(daily_counts)), daily_counts, color='skyblue')
    plt.title('Daily Transactions Count')
    plt.xlabel('Day of Month')
    plt.ylabel('Transactions')
    plt.xticks(range(len(dates)), [d.day for d in dates])
    transaction_chart = io.BytesIO()
    plt.savefig(transaction_chart, format='png')
    plt.close()

    # Stock distribution chart
    plt.figure(figsize=(6, 6))
    labels = [p.produit for p in top_products]
    quantities = [p.quantity for p in top_products]
    plt.pie(quantities, labels=labels, autopct='%1.1f%%')
    plt.title('Stock Distribution (Top 5 Products)')
    stock_chart = io.BytesIO()
    plt.savefig(stock_chart, format='png')
    plt.close()

    # 5. Generate PDF
    doc = SimpleDocTemplate(buffer, pagesize=letter)
    styles = getSampleStyleSheet()
    elements = []

    # Title
    elements.append(Paragraph("Monthly Business Report", styles['Title']))

    # KPI Summary
    elements.append(Paragraph(f"Report Date: {now.strftime('%Y-%m-%d %H:%M')}", styles['Heading2']))
    kpi_data = [
        ["Metric", "Value"],
        ["Stock Value", f"{stock_value:.2f}€"],
        ["Monthly Transactions", month_count],
        ["Weekly Transactions", week_count],
        ["Value per Transaction", f"{(stock_value / month_count):.2f}€" if month_count else "N/A"]
    ]
    kpi_table = Table(kpi_data)
    kpi_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('FONTSIZE', (0, 0), (-1, 0), 14),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
        ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
        ('GRID', (0, 0), (-1, -1), 1, colors.black),
    ]))
    elements.append(kpi_table)

    # Recent Transactions
    elements.append(Paragraph("Recent Transactions", styles['Heading2']))
    trans_data = [["Date", "Type", "Product", "Quantity", "Amount"]]
    for trans in recent_transactions:
        trans_data.append([
            trans.time.strftime("%Y-%m-%d"),
            trans.type,
            trans.produit.produit,
            trans.quantity,
            f"{trans.price:.2f}€"
        ])
    trans_table = Table(trans_data)
    trans_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.lightblue),
        ('GRID', (0, 0), (-1, -1), 1, colors.black),
    ]))
    elements.append(trans_table)

    # Charts
    elements.append(Paragraph("Transactions Trend", styles['Heading2']))
    transaction_chart.seek(0)
    elements.append(Image(transaction_chart, 6 * inch, 3 * inch))

    elements.append(Paragraph("Stock Distribution", styles['Heading2']))
    stock_chart.seek(0)
    elements.append(Image(stock_chart, 4 * inch, 4 * inch))

    # Generate PDF
    doc.build(elements)

    # Create HTTP response
    buffer.seek(0)
    response = HttpResponse(buffer, content_type='application/pdf')
    response['Content-Disposition'] = 'attachment; filename="business_report.pdf"'
    return response
