from rest_framework import viewsets
from rest_framework.decorators import api_view
from rest_framework.response import Response
from datetime import datetime, timedelta

from .models import Location, Route, Carrier
from .serializers import LocationSerializer, RouteSerializer, CarrierSerializer

# --- STANDARD VIEWSETS ---


class LocationViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Location.objects.all()
    serializer_class = LocationSerializer


class RouteViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Route.objects.all()
    serializer_class = RouteSerializer


class CarrierViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Carrier.objects.all()
    serializer_class = CarrierSerializer


# --- SMART SEARCH LOGIC ---

# Temporary Hardcoded Aliases (Until migration is applied)
LOCATION_ALIASES = {
    'DOM': ['DOM', 'DMROS'],
    'DMROS': ['DOM', 'DMROS'],
    'PTP': ['PTP', 'GPPTP'],
    'GPPTP': ['PTP', 'GPPTP'],
    'FDF': ['FDF', 'MQFDF'],
    'MQFDF': ['FDF', 'MQFDF'],
    'SLU': ['SLU', 'UVF', 'LCCAS'],
    'LCCAS': ['SLU', 'UVF', 'LCCAS'],
}


def resolve_location(code):
    if not code:
        return []
    code = code.upper().strip()
    return LOCATION_ALIASES.get(code, [code])


@api_view(['GET'])
def search_routes(request):
    origin_code = request.GET.get('origin')
    dest_code = request.GET.get('destination')
    date_str = request.GET.get('date')

    if not (origin_code and dest_code and date_str):
        return Response({'error': 'Missing parameters'}, status=400)

    # 1. RESOLVE LOCATIONS
    origins = resolve_location(origin_code)
    destinations = resolve_location(dest_code)

    # 2. PARSE START DATE
    try:
        start_date = datetime.strptime(date_str, '%Y-%m-%d').date()
    except ValueError:
        return Response({'error': 'Invalid date format (YYYY-MM-DD)'}, status=400)

    # 3. LOOKAHEAD LOOP (Max 7 days)
    found_routes = []
    found_date = start_date
    date_was_changed = False

    for i in range(7):
        current_date = start_date + timedelta(days=i)
        day_of_week = str(current_date.isoweekday())  # 1=Mon, 7=Sun

        routes = Route.objects.filter(
            origin__code__in=origins,
            destination__code__in=destinations,
            is_active=True,
            days_of_operation__contains=day_of_week
        ).select_related('origin', 'destination', 'carrier')  # Optimization

        if routes.exists():
            found_routes = routes
            found_date = current_date
            if i > 0:
                date_was_changed = True
            break

    # 4. FORMAT RESULTS (With Full Names)
    results = []
    for r in found_routes:
        results.append({
            'id': r.id,
            'carrier': r.carrier.name,
            'carrier_code': r.carrier.code,
            'type': r.carrier.carrier_type,
            'origin': r.origin.code,
            'destination': r.destination.code,

            # EXTENDED FIELDS for UI
            'origin_name': r.origin.name,
            'destination_name': r.destination.name,
            'origin_city': r.origin.city,
            'destination_city': r.destination.city,

            'departure_time': r.departure_time.strftime('%H:%M') if r.departure_time else None,
            'arrival_time': r.arrival_time.strftime('%H:%M') if r.arrival_time else None,
            'duration': r.duration_minutes,
            'is_ferry': r.carrier.carrier_type == 'SEA'
        })

    # 5. RETURN RICH RESPONSE
    return Response({
        'results': results,
        'search_date': date_str,
        'found_date': found_date.strftime('%Y-%m-%d'),
        'date_was_changed': date_was_changed
    })
