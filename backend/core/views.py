from rest_framework import viewsets
from rest_framework.response import Response
from .models import Location, Route, Carrier
from .serializers import RouteSerializer, LocationSerializer, CarrierSerializer
from datetime import datetime, timedelta, date


class LocationViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Location.objects.all()
    serializer_class = LocationSerializer
    lookup_field = 'code'


class CarrierViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Carrier.objects.all()
    serializer_class = CarrierSerializer


class RouteViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = RouteSerializer
    queryset = Route.objects.all()

    def list(self, request, *args, **kwargs):
        origin_code = request.query_params.get('origin')
        dest_code = request.query_params.get('destination')
        date_str = request.query_params.get('date')

        if not origin_code or not dest_code or not date_str:
            return Response([])

        try:
            original_date = datetime.strptime(date_str, '%Y-%m-%d').date()
        except ValueError:
            return Response([])

        # --- LOGIC: FIND NEXT AVAILABLE DATE ---
        # We loop up to 7 days to find the first date with valid flights
        results = []
        found_date = None

        for i in range(8):  # Check today + next 7 days
            check_date = original_date + timedelta(days=i)
            day_digit = str(check_date.isoweekday())  # 1=Mon, 7=Sun

            # Helper to filter by day of operation
            def runs_today(qs):
                return qs.filter(days_of_operation__contains=day_digit)

            # 1. Direct Flights
            direct = Route.objects.filter(
                origin__code=origin_code,
                destination__code=dest_code,
                is_active=True
            )
            direct = runs_today(direct)

            daily_results = []
            for r in direct:
                daily_results.append({
                    'type': 'direct',
                    'legs': [RouteSerializer(r).data],
                    'total_duration': r.duration_minutes,
                    'connection_duration': None
                })

            # 2. Connections (The "Stitch")
            # Leg 1: Origin -> Hub
            leg1_candidates = Route.objects.filter(
                origin__code=origin_code, is_active=True).exclude(destination__code=dest_code)
            leg1_candidates = runs_today(leg1_candidates)

            # Leg 2: Hub -> Dest
            leg2_candidates = Route.objects.filter(
                destination__code=dest_code, is_active=True)
            leg2_candidates = runs_today(leg2_candidates)

            # Create Map for Leg 2
            hub_map = {}
            for l2 in leg2_candidates:
                if l2.origin.code not in hub_map:
                    hub_map[l2.origin.code] = []
                hub_map[l2.origin.code].append(l2)

            for l1 in leg1_candidates:
                hub = l1.destination.code
                if hub in hub_map:
                    for l2 in hub_map[hub]:
                        # --- CRITICAL: SAME DAY CHECK ---
                        # We only want connections where Leg 2 departs AFTER Leg 1 arrives.
                        if l1.arrival_time and l2.departure_time:
                            if l2.departure_time > l1.arrival_time:
                                # Calculate Connection Time (in minutes)
                                # Dummy dates needed to subtract time objects
                                t1 = datetime.combine(
                                    date.min, l1.arrival_time)
                                t2 = datetime.combine(
                                    date.min, l2.departure_time)
                                conn_mins = int((t2 - t1).total_seconds() / 60)

                                # Optional: Enforce min connection (e.g. 45 mins)
                                if conn_mins >= 45:
                                    total_dur = (
                                        l1.duration_minutes or 0) + (l2.duration_minutes or 0) + conn_mins
                                    daily_results.append({
                                        'type': 'connection',
                                        'legs': [RouteSerializer(l1).data, RouteSerializer(l2).data],
                                        'total_duration': total_dur,
                                        'connection_duration': conn_mins
                                    })

            if daily_results:
                results = daily_results
                found_date = check_date
                break  # Stop searching, we found flights!

        return Response({
            'results': results,
            'search_date': str(original_date),
            'found_date': str(found_date) if found_date else None,
            'date_was_changed': found_date != original_date if found_date else False
        })
