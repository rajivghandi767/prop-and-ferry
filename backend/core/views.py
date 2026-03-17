import requests
from django.conf import settings
from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.response import Response
from datetime import timedelta, datetime

from .models import Location, Route, Sailing, FlightInstance, Carrier, ReportedIssue
from .serializers import (
    LocationSerializer, RouteSerializer, SailingSerializer,
    CarrierSerializer, ReportedIssueSerializer, ItineraryLegSerializer
)


class LocationViewSet(viewsets.ReadOnlyModelViewSet):
    # Prefetch relationships to prevent N+1 queries when evaluating 'has_children'
    queryset = Location.objects.select_related(
        'parent').prefetch_related('sub_locations').all()
    serializer_class = LocationSerializer


class CarrierViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Carrier.objects.all()
    serializer_class = CarrierSerializer


class SailingViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Sailing.objects.all()
    serializer_class = SailingSerializer


class ReportedIssueViewSet(viewsets.ModelViewSet):
    queryset = ReportedIssue.objects.all()
    serializer_class = ReportedIssueSerializer

    def perform_create(self, serializer):
        issue = serializer.save()
        webhook_url = getattr(settings, 'DISCORD_WEBHOOK_URL', None)

        if webhook_url:
            try:
                payload = {
                    "content": f"🚨 **New Prop & Ferry Issue Reported** 🚨\n**Type:** {issue.get_issue_type_display()}\n**Note:** {issue.user_note}"
                }
                requests.post(webhook_url, json=payload, timeout=5)
            except Exception:
                # Fail silently so the user still gets a success message in the UI
                pass


class RouteViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Route.objects.all()
    serializer_class = RouteSerializer

    @action(detail=False, methods=['get'], url_path='available-dates')
    def available_dates(self, request):
        origin_query = request.GET.get('origin')
        dest_query = request.GET.get('destination')

        if not origin_query or not dest_query:
            return Response({'error': 'Missing parameters'}, status=400)

        try:
            origin_loc = Location.objects.select_related('parent').prefetch_related(
                'sub_locations', 'parent__sub_locations').get(code=origin_query)
            dest_loc = Location.objects.select_related('parent').prefetch_related(
                'sub_locations', 'parent__sub_locations').get(code=dest_query)
        except Location.DoesNotExist:
            return Response({'error': 'Location not found'}, status=404)

        origin_aliases = origin_loc.resolve_aliases()
        dest_aliases = dest_loc.resolve_aliases()

        # Exclude sold-out flights from generating active dates on the frontend calendar
        flight_dates = FlightInstance.objects.filter(
            route__origin__code__in=origin_aliases,
            route__destination__code__in=dest_aliases,
            route__is_active=True,
            available_seats__gt=0
        ).values_list('date', flat=True).distinct()

        ferry_dates = Sailing.objects.filter(
            route__origin__code__in=origin_aliases,
            route__destination__code__in=dest_aliases,
            route__is_active=True
        ).values_list('date', flat=True).distinct()

        all_dates = sorted(list(set(flight_dates) | set(ferry_dates)))
        return Response({'available_dates': [d.strftime('%Y-%m-%d') for d in all_dates]})

    @action(detail=False, methods=['get'])
    def search(self, request):
        origin_query = request.GET.get('origin')
        dest_query = request.GET.get('destination')
        target_date_str = request.GET.get('date')

        if not origin_query or not dest_query or not target_date_str:
            return Response({'error': 'Missing parameters'}, status=400)

        try:
            origin_loc = Location.objects.select_related('parent').prefetch_related(
                'sub_locations', 'parent__sub_locations').get(code=origin_query)
            dest_loc = Location.objects.select_related('parent').prefetch_related(
                'sub_locations', 'parent__sub_locations').get(code=dest_query)
            target_date = datetime.strptime(target_date_str, '%Y-%m-%d').date()
        except (Location.DoesNotExist, ValueError):
            return Response({'error': 'Invalid parameters'}, status=400)

        origin_aliases = origin_loc.resolve_aliases()
        dest_aliases = dest_loc.resolve_aliases()

        # We fetch 4 days of data to allow for overnight bleed into the 4th day
        end_date = target_date + timedelta(days=4)

        # --- 1. FETCH DIRECT ROUTES ---
        direct_flights = FlightInstance.objects.filter(
            route__origin__code__in=origin_aliases,
            route__destination__code__in=dest_aliases,
            date__range=[target_date, end_date],
            route__is_active=True,
            available_seats__gt=0
        ).select_related('route', 'route__carrier', 'route__origin', 'route__destination')

        direct_ferries = Sailing.objects.filter(
            route__origin__code__in=origin_aliases,
            route__destination__code__in=dest_aliases,
            date__range=[target_date, end_date],
            route__is_active=True
        ).select_related('route', 'route__carrier', 'route__origin', 'route__destination')

        # --- 2. THE STITCHER (GRAPH TRAVERSAL) ---

        # Level 1: Get all outgoing flights that are NOT direct and NOT sold out
        leg1_flights = FlightInstance.objects.filter(
            route__origin__code__in=origin_aliases,
            date__range=[target_date, end_date],
            route__is_active=True,
            available_seats__gt=0
        ).exclude(route__destination__code__in=dest_aliases).select_related(
            'route', 'route__carrier', 'route__origin', 'route__destination'
        )

        # Find our graph hubs using O(1) set lookups
        hub_codes = {f.route.destination.code for f in leg1_flights}

        # Expand hubs to include their sub-terminals (e.g., DOM also includes DMROS)
        hub_locations = Location.objects.filter(code__in=hub_codes).prefetch_related(
            'sub_locations', 'parent__sub_locations')
        expanded_hubs = set()
        for loc in hub_locations:
            expanded_hubs.update(loc.resolve_aliases())

        # Level 2: Get all flights/ferries leaving those expanded hubs towards the final destination
        leg2_flights = FlightInstance.objects.filter(
            route__origin__code__in=expanded_hubs,
            route__destination__code__in=dest_aliases,
            date__range=[target_date, end_date],
            route__is_active=True,
            available_seats__gt=0
        ).select_related('route', 'route__carrier', 'route__origin', 'route__destination')

        leg2_ferries = Sailing.objects.filter(
            route__origin__code__in=expanded_hubs,
            route__destination__code__in=dest_aliases,
            date__range=[target_date, end_date],
            route__is_active=True
        ).select_related('route', 'route__carrier', 'route__origin', 'route__destination')

        # --- 3. OVERNIGHT-AWARE MEMORY STITCHING ---
        MIN_CONNECT_FLIGHT = 3600  # 1 Hour
        MIN_CONNECT_FERRY = 7200   # 2 Hours
        # 18 Hours (Easily captures a 7 PM arrival connecting to a 1 PM departure next day)
        MAX_CONNECT = 64800

        results = []
        found_date = target_date
        date_was_changed = False

        for i in range(4):
            check_date = target_date + timedelta(days=i)
            next_date = check_date + timedelta(days=1)
            day_itineraries = []

            # A. Add Directs First
            for f in [x for x in direct_flights if x.date == check_date]:
                day_itineraries.append(
                    {"id": f"f_{f.id}", "legs": [ItineraryLegSerializer(f).data]})
            for s in [x for x in direct_ferries if x.date == check_date]:
                day_itineraries.append(
                    {"id": f"s_{s.id}", "legs": [ItineraryLegSerializer(s).data]})

            # B. Evaluate Connections (Overnight Aware)
            day_l1 = [f for f in leg1_flights if f.date == check_date]

            # Leg 2 can happen TODAY or TOMORROW
            l2_candidates_f = [
                f for f in leg2_flights if f.date in (check_date, next_date)]
            l2_candidates_s = [
                s for s in leg2_ferries if s.date in (check_date, next_date)]

            for l1 in day_l1:
                if not l1.route.arrival_time:
                    continue
                # Create a true datetime object for Leg 1 Arrival
                l1_arr_dt = datetime.combine(l1.date, l1.route.arrival_time)
                l1_dest_aliases = l1.route.destination.resolve_aliases()

                # Stitch Flight -> Flight
                for l2 in l2_candidates_f:
                    if l2.route.origin.code not in l1_dest_aliases:
                        continue
                    if not l2.route.departure_time:
                        continue

                    # Create a true datetime object for Leg 2 Departure
                    l2_dep_dt = datetime.combine(
                        l2.date, l2.route.departure_time)
                    gap = (l2_dep_dt - l1_arr_dt).total_seconds()

                    if MIN_CONNECT_FLIGHT <= gap <= MAX_CONNECT:
                        l1_data = ItineraryLegSerializer(l1).data
                        l2_data = ItineraryLegSerializer(l2).data

                        hours, mins = int(gap // 3600), int((gap % 3600) // 60)

                        # Dynamically flag if the layover spills into the next day
                        if l1.date != l2.date:
                            l1_data['layover_text'] = f"🌙 Overnight Layover: {hours}h {mins}m in {l1.route.destination.city}"
                        else:
                            l1_data['layover_text'] = f"{hours}h {mins}m Layover in {l1.route.destination.city}"

                        day_itineraries.append(
                            {"id": f"c_ff_{l1.id}_{l2.id}", "legs": [l1_data, l2_data]})

                # Stitch Flight -> Ferry
                for l2 in l2_candidates_s:
                    if l2.route.origin.code not in l1_dest_aliases:
                        continue
                    if not l2.departure_time:
                        continue

                    # Create a true datetime object for Leg 2 Departure
                    l2_dep_dt = datetime.combine(l2.date, l2.departure_time)
                    gap = (l2_dep_dt - l1_arr_dt).total_seconds()

                    if MIN_CONNECT_FERRY <= gap <= MAX_CONNECT:
                        l1_data = ItineraryLegSerializer(l1).data
                        l2_data = ItineraryLegSerializer(l2).data

                        hours, mins = int(gap // 3600), int((gap % 3600) // 60)

                        # Dynamically flag if the layover spills into the next day
                        if l1.date != l2.date:
                            l1_data['layover_text'] = f"🌙 Overnight Transfer: {hours}h {mins}m to {l2.route.origin.name}"
                        else:
                            l1_data['layover_text'] = f"⛴️ {hours}h {mins}m Transfer to {l2.route.origin.name}"

                        day_itineraries.append(
                            {"id": f"c_fs_{l1.id}_{l2.id}", "legs": [l1_data, l2_data]})

            # If we found any valid trips on this day, lock it in and stop searching future days
            if day_itineraries:
                results = day_itineraries
                if i > 0:
                    date_was_changed = True
                    found_date = check_date
                break

        response_data = {
            "date_was_changed": date_was_changed,
            "found_date": found_date.strftime('%Y-%m-%d'),
            "results": results
        }

        return Response(response_data)
