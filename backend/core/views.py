from rest_framework import viewsets
from rest_framework.decorators import api_view
from rest_framework.response import Response
from datetime import datetime, timedelta

from .models import Location, Route, Carrier, Sailing
from .serializers import LocationSerializer, RouteSerializer, CarrierSerializer


class LocationViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Location.objects.all()
    serializer_class = LocationSerializer


class RouteViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Route.objects.all()
    serializer_class = RouteSerializer


class CarrierViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Carrier.objects.all()
    serializer_class = CarrierSerializer

# --- HYBRID SEARCH LOGIC ---


LOCATION_ALIASES = {
    'DOM': ['DOM', 'DMROS'], 'DMROS': ['DOM', 'DMROS'],
    'PTP': ['PTP', 'GPPTP'], 'GPPTP': ['PTP', 'GPPTP'],
    'FDF': ['FDF', 'MQFDF'], 'MQFDF': ['FDF', 'MQFDF'],
    'SLU': ['SLU', 'UVF', 'LCCAS'], 'LCCAS': ['SLU', 'UVF', 'LCCAS'],
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

    origins = resolve_location(origin_code)
    destinations = resolve_location(dest_code)

    try:
        start_date = datetime.strptime(date_str, '%Y-%m-%d').date()
    except ValueError:
        return Response({'error': 'Invalid date'}, status=400)

    found_results = []
    found_date = start_date
    date_was_changed = False

    # 7-Day Lookahead
    for i in range(7):
        current_date = start_date + timedelta(days=i)
        day_of_week = str(current_date.isoweekday())

        # 1. FIND FLIGHTS (Recurring Schedule)
        flights = Route.objects.filter(
            origin__code__in=origins,
            destination__code__in=destinations,
            carrier__carrier_type='AIR',  # Flights Only
            is_active=True,
            days_of_operation__contains=day_of_week
        ).select_related('origin', 'destination', 'carrier')

        # 2. FIND FERRIES (Exact Date Sailings)
        sailings = Sailing.objects.filter(
            route__origin__code__in=origins,
            route__destination__code__in=destinations,
            date=current_date
        ).select_related('route', 'route__origin', 'route__destination', 'route__carrier')

        if flights.exists() or sailings.exists():
            found_date = current_date
            if i > 0:
                date_was_changed = True

            # Process Flights
            for f in flights:
                found_results.append(format_route_response(
                    f, f.departure_time, f.arrival_time))

            # Process Ferries
            for s in sailings:
                found_results.append(format_route_response(
                    s.route, s.departure_time, s.arrival_time))

            break  # Stop looking once we find something

    return Response({
        'results': found_results,
        'search_date': date_str,
        'found_date': found_date.strftime('%Y-%m-%d'),
        'date_was_changed': date_was_changed
    })


def format_route_response(route_obj, dep_time, arr_time):
    return {
        'id': route_obj.id,
        'carrier': route_obj.carrier.name,
        'carrier_code': route_obj.carrier.code,
        'type': route_obj.carrier.carrier_type,
        'origin': route_obj.origin.code,
        'destination': route_obj.destination.code,
        'origin_name': route_obj.origin.name,
        'destination_name': route_obj.destination.name,
        'origin_city': route_obj.origin.city,
        'destination_city': route_obj.destination.city,
        'departure_time': dep_time.strftime('%H:%M') if dep_time else None,
        'arrival_time': arr_time.strftime('%H:%M') if arr_time else None,
        'duration': route_obj.duration_minutes,
        'is_ferry': route_obj.carrier.carrier_type == 'SEA'
    }
