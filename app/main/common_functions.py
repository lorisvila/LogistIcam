from datetime import datetime, timedelta
from django.utils import timezone


def get_dates(request):
    duree = request.GET.get('duree')
    date_str = request.GET.get('date')

    start_date = None
    end_date = None

    # Définir la date de référence
    if date_str:
        try:
            reference_date = datetime.strptime(date_str, '%Y-%m-%dT%H:%M')
        except ValueError:
            reference_date = timezone.localdate()
    else:
        reference_date = timezone.localdate()

    # Calculer start_date et end_date selon la durée
    match duree:
        case "year":
            start_date = reference_date - timedelta(days=182)
            end_date = reference_date + timedelta(days=183)
        case "month":
            start_date = reference_date - timedelta(days=15)
            end_date = reference_date + timedelta(days=15)
        case "week":
            start_date = reference_date - timedelta(days=7)
            end_date = reference_date + timedelta(days=3)
        case "day":
            start_date = reference_date - timedelta(hours=24)
            end_date = reference_date + timedelta(hours=12)
        case "hour":
            start_date = reference_date - timedelta(hours=1)
            end_date = reference_date + timedelta(hours=1)
        case _:
            start_date = None
            end_date = None
    return start_date, end_date


def filter_transactions(transactions, request):

    start_date, end_date = get_dates(request)

    if start_date:
        transactions = transactions.filter(time__gte=start_date)
    if end_date:
        transactions = transactions.filter(time__lte=end_date)

    return transactions