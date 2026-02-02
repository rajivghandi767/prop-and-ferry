from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.response import Response
from datetime import datetime, timedelta

from .models import Location, Route, Carrier, Sailing
from .serializers import LocationSerializer, RouteSerializer, CarrierSerializer, SailingSerializer

# --- HELPERS ---
LOCATION_ALIASES = {
    # Caribbean Aliases (Airport + Ferry Codes)
    'DOM': ['DOM', 'DMROS', 'DCF'],
    'PTP': ['PTP', 'GPPTP'],
    'FDF': ['FDF', 'MQFDF'],
    'SLU': ['SLU', 'UVF', 'LCCAS'],

    # City Aliases (Major Hubs)
    'NYC': ['JFK', 'EWR', 'LGA'],
    'LON': ['LHR', 'LGW', 'LCY'],
    'MIA': ['MIA', 'FLL'],
    'WAS': ['IAD', 'DCA', 'BWI'],
}


def resolve_location(code):
    if not code:
        return []
    code = code.upper().strip()
    return LOCATION_ALIASES.get(code, [code])


def get_seconds(t):
    """Safely convert time object to seconds, returning None if time is missing."""
    if t is None:
        return None
    return (t.hour * 3600) + (t.minute * 60) + t.second


# --- VIEWSETS ---

class LocationViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Location.objects.all()
    serializer_class = LocationSerializer


class CarrierViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Carrier.objects.all()
    serializer_class = CarrierSerializer


class SailingViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Sailing.objects.all()
    serializer_class = SailingSerializer


class RouteViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Route.objects.all()
    serializer_class = RouteSerializer

    @action(detail=False, methods=['get'])
    def search(self, request):
        """
        GET /api/routes/search/?origin=JFK&destination=DOM&date=2026-02-01
        """
        origin_input = request.query_params.get('origin')
        dest_input = request.query_params.get('destination')
        date_str = request.query_params.get('date')

        if not (origin_input and dest_input and date_str):
            return Response({'error': 'Missing parameters'}, status=400)

        origins = resolve_location(origin_input)
        dests = resolve_location(dest_input)

        try:
            start_date = datetime.strptime(date_str, '%Y-%m-%d').date()
        except ValueError:
            return Response({'error': 'Invalid date format'}, status=400)

        final_itineraries = []
        found_on_requested_date = False

        # Check 3 days window
        for i in range(3):
            search_date = start_date + timedelta(days=i)
            day_of_week = str(search_date.isoweekday())

            # --- 1. FIND DIRECT ROUTES ---

            # A -> B (Flight)
            direct_flights = Route.objects.filter(
                origin__code__in=origins,
                destination__code__in=dests,
                is_active=True,
                days_of_operation__contains=day_of_week
            )

            # A -> B (Ferry)
            direct_ferries = Sailing.objects.filter(
                route__origin__code__in=origins,
                route__destination__code__in=dests,
                date=search_date
            )

            for f in direct_flights:
                final_itineraries.append({
                    'id': f.id,
                    'legs': [RouteSerializer(f).data],
                    'total_duration': f.duration_minutes,
                    'search_date': search_date
                })
                if i == 0:
                    found_on_requested_date = True

            for s in direct_ferries:
                final_itineraries.append({
                    'id': s.id + 900000,
                    'legs': [SailingSerializer(s).data],
                    'total_duration': s.duration_minutes,
                    'search_date': search_date
                })
                if i == 0:
                    found_on_requested_date = True

            # --- 2. FIND CONNECTING ROUTES (The Stitcher) ---
            # Origin -> Hub -> Destination

            # Leg 1: Origin -> Hub (Flight)
            possible_leg1s = Route.objects.filter(
                origin__code__in=origins,
                is_active=True,
                days_of_operation__contains=day_of_week
            ).exclude(destination__code__in=dests)

            for leg1 in possible_leg1s:
                # SAFETY CHECK 1: Ensure Leg 1 has valid times
                l1_arr = get_seconds(leg1.arrival_time)
                if l1_arr is None:
                    continue

                hub = leg1.destination
                hub_codes = resolve_location(hub.code)

                # Leg 2: Hub -> Destination (Flight)
                leg2_flights = Route.objects.filter(
                    origin__code__in=hub_codes,
                    destination__code__in=dests,
                    is_active=True,
                    days_of_operation__contains=day_of_week
                )

                # Leg 2: Hub -> Destination (Ferry)
                leg2_ferries = Sailing.objects.filter(
                    route__origin__code__in=hub_codes,
                    route__destination__code__in=dests,
                    date=search_date
                )

                # --- TIME MATH ---
                MIN_CONNECT_FLIGHT = 3600  # 1 Hour
                MIN_CONNECT_FERRY = 7200   # 2 Hours (Taxi/Buffer)
                MAX_CONNECT = 21600        # 6 Hours

                # Stitch Flight -> Flight
                for leg2 in leg2_flights:
                    l2_dep = get_seconds(leg2.departure_time)
                    if l2_dep is None:
                        continue

                    gap = l2_dep - l1_arr

                    if MIN_CONNECT_FLIGHT < gap < MAX_CONNECT:
                        leg1_data = RouteSerializer(leg1).data
                        leg2_data = RouteSerializer(leg2).data

                        hours = gap // 3600
                        mins = (gap % 3600) // 60
                        leg1_data['layover_text'] = f"{hours}h {mins}m Layover in {hub.city}"

                        final_itineraries.append({
                            'id': int(f"{leg1.id}{leg2.id}"),
                            'legs': [leg1_data, leg2_data],
                            'total_duration': leg1.duration_minutes + leg2.duration_minutes + (gap // 60),
                            'search_date': search_date
                        })
                        if i == 0:
                            found_on_requested_date = True

                # Stitch Flight -> Ferry
                for leg2 in leg2_ferries:
                    l2_dep = get_seconds(leg2.departure_time)
                    if l2_dep is None:
                        continue

                    gap = l2_dep - l1_arr

                    if MIN_CONNECT_FERRY < gap < MAX_CONNECT:
                        leg1_data = RouteSerializer(leg1).data
                        sailing_data = SailingSerializer(leg2).data

                        hours = gap // 3600
                        mins = (gap % 3600) // 60
                        leg1_data['layover_text'] = f"🚕 {hours}h {mins}m Transfer to {leg2.route.origin.name}"

                        final_itineraries.append({
                            'id': int(f"{leg1.id}{leg2.id}"),
                            'legs': [leg1_data, sailing_data],
                            'total_duration': leg1.duration_minutes + leg2.duration_minutes + (gap // 60),
                            'search_date': search_date
                        })
                        if i == 0:
                            found_on_requested_date = True

            if found_on_requested_date and i == 0:
                break

        return Response({
            'results': final_itineraries,
            'search_date': date_str,
            'found_date': final_itineraries[0]['search_date'] if final_itineraries else date_str,
            'date_was_changed': not found_on_requested_date and bool(final_itineraries)
        })
