from datetime import datetime, timedelta
from django.utils import timezone


def get_dates(request):
    duree    = request.GET.get('duree')
    date_str = request.GET.get('date')

    # 1) Déterminer la date de référence (aware)
    if date_str:
        try:
            naive = datetime.strptime(date_str, '%Y-%m-%dT%H:%M')
            ref_date = timezone.make_aware(naive, timezone.get_current_timezone())
        except ValueError:
            ref_date = timezone.localtime()
    else:
        ref_date = timezone.localtime()

    start_date = end_date = None

    match duree:
        case 'year':
            # Du 1er janvier 00:00 de l’année de ref…
            start_date = ref_date.replace(month=1, day=1, hour=0, minute=0, second=0, microsecond=0)
            # …jusqu’au 1er janvier 00:00 de l’année suivante
            end_date   = start_date.replace(year=start_date.year + 1)

        case 'month':
            # Du 1er jour du mois à 00:00…
            start_date = ref_date.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
            # …au 1er jour du mois suivant à 00:00
            if start_date.month == 12:
                end_date = start_date.replace(year=start_date.year + 1, month=1)
            else:
                end_date = start_date.replace(month=start_date.month + 1)

        case 'week':
            # Semaine civile (Lundi 00:00 → Lundi suivant 00:00)
            weekday    = ref_date.weekday()         # Lundi=0
            start_date = (ref_date - timedelta(days=weekday)) \
                           .replace(hour=0, minute=0, second=0, microsecond=0)
            end_date   = start_date + timedelta(days=7)

        case 'day':
            # Jour calendaire (00:00 du jour → 00:00 du lendemain)
            start_date = ref_date.replace(hour=0, minute=0, second=0, microsecond=0)
            end_date   = start_date + timedelta(days=1)

        case 'hour':
            # Heure pleine (HH:00 → HH+1:00)
            start_date = ref_date.replace(minute=0, second=0, microsecond=0)
            end_date   = start_date + timedelta(hours=1)

        case _:
            # Aucun filtre
            start_date = end_date = None

    return start_date, end_date


def filter_transactions(transactions, request):

    start_date, end_date = get_dates(request)

    if start_date:
        transactions = transactions.filter(time__gte=start_date)
    if end_date:
        transactions = transactions.filter(time__lte=end_date)

    return transactions