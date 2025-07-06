from datetime import datetime, timedelta

from django.utils import timezone


def get_dates(request):
    """
    Extracts start and end datetime based on the given duration and reference datetime provided
    through a request. The function interprets the `duree` parameter to determine the time range
    and calculates the start and end dates accordingly. If a specific datetime is provided in the
    request, it uses it as the reference; otherwise, it defaults to the current local time.

    :param request: A Django HttpRequest object containing `duree` and optional `date` parameters.
    :type request: HttpRequest
    :return: A tuple where the first element is the start datetime and the second is the end datetime.
    :rtype: tuple[datetime.datetime | None, datetime.datetime | None]
    :raises ValueError: Raised when an invalid date format is provided in the `date` parameter.
    """
    duree = request.GET.get('duree')
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
            end_date = start_date.replace(year=start_date.year + 1)

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
            weekday = ref_date.weekday()  # Lundi=0
            start_date = (ref_date - timedelta(days=weekday)) \
                .replace(hour=0, minute=0, second=0, microsecond=0)
            end_date = start_date + timedelta(days=7)

        case 'day':
            # Jour calendaire (00:00 du jour → 00:00 du lendemain)
            start_date = ref_date.replace(hour=0, minute=0, second=0, microsecond=0)
            end_date = start_date + timedelta(days=1)

        case 'hour':
            # Heure pleine (HH:00 → HH+1:00)
            start_date = ref_date.replace(minute=0, second=0, microsecond=0)
            end_date = start_date + timedelta(hours=1)

        case _:
            # Aucun filtre
            start_date = end_date = None

    return start_date, end_date


def filter_transactions(transactions, request):
    """
    Filters a given list of transactions based on a date range specified in the request.

    This function retrieves the date range from the request object through
    a helper function and applies the corresponding filters to the list
    of transactions. If a `start_date` is present, only transactions
    with a timestamp greater than or equal to the `start_date` are included.
    Similarly, if an `end_date` is present, only transactions with a
    timestamp less than or equal to the `end_date` are included.

    :param transactions: A queryset or list-like object containing transactions,
        where each transaction is expected to have a `time` attribute.
    :param request: The request object containing the date range filters,
        typically passed as input to handle user input or programmatic context.
    :return: The filtered list of transactions that fall within the specified
        date range.
    """
    start_date, end_date = get_dates(request)

    if start_date:
        transactions = transactions.filter(time__gte=start_date)
    if end_date:
        transactions = transactions.filter(time__lte=end_date)

    return transactions
