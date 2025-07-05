from datetime import timedelta
from decimal import Decimal

from django.contrib.auth import logout
from django.contrib.auth.decorators import permission_required
from django.db.models import Sum, F, ExpressionWrapper, DecimalField
from django.shortcuts import redirect
from django.shortcuts import render
from django.utils import timezone

from ..models import Transaction, Stock


@permission_required('main.view_transaction', login_url='/login/')
def page_accueil_view(request):
    # 1) Début du mois courant
    now = timezone.now()
    month_start = now - timedelta(days=30)

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

    # 12). Valeur du stock
    stock_value_agg = Stock.objects.aggregate(
        valeur_stock=Sum(
            ExpressionWrapper(
                F('quantity') * F('prix_vente'),
                output_field=DecimalField(max_digits=14, decimal_places=2)
            )
        )
    )
    valeur_stock = stock_value_agg['valeur_stock'] or Decimal('0.00')

    # 13) Passage du contexte à la vue
    context = {
        'nb_ventes': nb_ventes,
        'chiffre_affaires': chiffre_affaires,
        'benefice': benefice,
        'articles_most_sold': articles_most_sold,
        'articles_most_bought': articles_most_bought,
        'client_of_month': client_of_month,
        'valeur_stock': valeur_stock,
    }
    return render(request, 'page_accueil.html', context)


def logout_view(request):
    logout(request)
    return redirect('main:home')
