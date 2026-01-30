from rest_framework import viewsets
from rest_framework.decorators import api_view
from rest_framework.response import Response
from datetime import datetime

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


# --- SMART SEARCH LOGIC (New) ---

# Maps generic codes to ALL valid sub-locations (Airports + Ferry Ports)
LOCATION_ALIASES = {
    # DOMINICA
    'DOM': ['DOM', 'DMROS'],       # Airport + Roseau Ferry
    'DMROS': ['DOM', 'DMROS'],

    # GUADELOUPE
    'PTP': ['PTP', 'GPPTP'],       # Airport + Pointe-à-Pitre Ferry
    'GPPTP': ['PTP', 'GPPTP'],

    # MARTINIQUE
    'FDF': ['FDF', 'MQFDF'],       # Airport + Fort-de-France Ferry
    'MQFDF': ['FDF', 'MQFDF'],

    # ST LUCIA
    'SLU': ['SLU', 'UVF', 'LCCAS'],
    'LCCAS': ['SLU', 'UVF', 'LCCAS'],
}


def resolve_location(code):
    """
    Input: 'DOM' -> Output: ['DOM', 'DMROS']
    """
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

    # 1. SMART EXPANSION
    origins = resolve_location(origin_code)
    destinations = resolve_location(dest_code)

    # 2. PARSE DATE
    try:
        search_date = datetime.strptime(date_str, '%Y-%m-%d')
        # ISO Weekday: 1=Mon, 7=Sun
        day_of_week = str(search_date.isoweekday())
    except ValueError:
        return Response({'error': 'Invalid date format (YYYY-MM-DD)'}, status=400)

    # 3. QUERY DATABASE
    # Find routes that match ANY of the origin/dest aliases AND run on this day of week
    routes = Route.objects.filter(
        origin__code__in=origins,
        destination__code__in=destinations,
        is_active=True,
        days_of_operation__contains=day_of_week
    )

    # 4. FORMAT RESULTS
    results = []
    for r in routes:
        results.append({
            'id': r.id,
            'carrier': r.carrier.name,
            'carrier_code': r.carrier.code,
            'type': r.carrier.carrier_type,  # 'AIR' or 'SEA'
            'origin': r.origin.code,
            'destination': r.destination.code,
            'departure_time': r.departure_time.strftime('%H:%M'),
            'arrival_time': r.arrival_time.strftime('%H:%M'),
            'duration': r.duration_minutes
        })

    return Response(results)
