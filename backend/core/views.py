from rest_framework import viewsets, filters
from rest_framework.decorators import action
from rest_framework.response import Response
from datetime import timedelta, datetime
from django.core.cache import cache
from django_filters.rest_framework import DjangoFilterBackend

from .models import Location, Route, Sailing, FlightInstance, Carrier, ReportedIssue
from .serializers import (
    LocationSerializer,
    RouteSerializer,
    SailingSerializer,
    CarrierSerializer,
    ReportedIssueSerializer,
    ItineraryLegSerializer,
)

class ItineraryFilterBackend(DjangoFilterBackend):
    def filter_queryset(self, request, queryset, view):
        filter_val = request.GET.get("filter", "all")
        if filter_val == "ferry":
            return [it for it in queryset if any(leg.get("is_ferry", False) for leg in it["legs"])]
        if filter_val == "flight":
            return [it for it in queryset if not any(leg.get("is_ferry", False) for leg in it["legs"])]
        return queryset

class ItineraryOrderingFilter(filters.OrderingFilter):
    def filter_queryset(self, request, queryset, view):
        return sorted(queryset, key=lambda x: 1 if any(leg.get("is_ferry", False) for leg in x["legs"]) else 0, reverse=True)


class LocationViewSet(viewsets.ReadOnlyModelViewSet):
    # Prefetch relationships to prevent N+1 queries when evaluating 'has_children'
    queryset = (
        Location.objects.select_related("parent")
        .prefetch_related("sub_locations")
        .all()
    )
    serializer_class = LocationSerializer

    def list(self, request, *args, **kwargs):

        cached = cache.get("prop_locations_list")
        if cached:
            return Response(cached)
        response = super().list(request, *args, **kwargs)
        cache.set("prop_locations_list", list(response.data), 60 * 60)
        return response


class CarrierViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Carrier.objects.all()
    serializer_class = CarrierSerializer

    def list(self, request, *args, **kwargs):

        cached = cache.get("prop_carriers_list")
        if cached:
            return Response(cached)
        response = super().list(request, *args, **kwargs)
        cache.set("prop_carriers_list", list(response.data), 60 * 60)
        return response


class SailingViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Sailing.objects.all()
    serializer_class = SailingSerializer


class ReportedIssueViewSet(viewsets.ModelViewSet):
    http_method_names = ["get", "post", "head", "options"]
    queryset = ReportedIssue.objects.all()
    serializer_class = ReportedIssueSerializer

    def perform_create(self, serializer):
        issue = serializer.save()
        issue.send_notifications()


class RouteViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Route.objects.all()
    serializer_class = RouteSerializer

    @action(detail=False, methods=["get"], url_path="available-dates")
    def available_dates(self, request):

        origin_query = request.GET.get("origin")
        dest_query = request.GET.get("destination")

        if not origin_query or not dest_query:
            return Response({"error": "Missing parameters"}, status=400)

        cache_key = f"prop_dates_{origin_query}_{dest_query}"
        cached = cache.get(cache_key)
        if cached:
            return Response(cached)

        try:
            origin_loc = (
                Location.objects.select_related("parent")
                .prefetch_related("sub_locations", "parent__sub_locations")
                .get(code=origin_query)
            )
            dest_loc = (
                Location.objects.select_related("parent")
                .prefetch_related("sub_locations", "parent__sub_locations")
                .get(code=dest_query)
            )
        except Location.DoesNotExist:
            return Response({"error": "Location not found"}, status=404)

        origin_aliases = origin_loc.resolve_aliases()
        dest_aliases = dest_loc.resolve_aliases()


        flight_dates = (
            FlightInstance.objects.filter(
                route__origin__code__in=origin_aliases,
                route__destination__code__in=dest_aliases,
                route__is_active=True,
                available_seats__gt=0,
            )
            .values_list("date", flat=True)
            .distinct()
        )

        ferry_dates = (
            Sailing.objects.filter(
                route__origin__code__in=origin_aliases,
                route__destination__code__in=dest_aliases,
                route__is_active=True,
            )
            .values_list("date", flat=True)
            .distinct()
        )

        all_dates = sorted(list(set(flight_dates) | set(ferry_dates)))
        resp_data = {"available_dates": [d.strftime("%Y-%m-%d") for d in all_dates]}
        cache.set(cache_key, resp_data, 60 * 15)
        return Response(resp_data)

    @action(detail=False, methods=["get"])
    def search(self, request):
        """
        Main search endpoint for itineraries.
        
        Given an origin, destination, and target date, this method constructs
        potential travel itineraries. Because travel within the Caribbean often 
        requires multi-leg journeys, the algorithm checks for both:
        1. Direct routes (single leg, flight or ferry)
        2. Connected routes (two legs: Flight -> Flight, or Flight -> Ferry)

        It uses a 4-day sliding window to ensure overnight connections are caught.
        Responses are cached to minimize heavy database computation.
        """
        origin_query = request.GET.get("origin")
        dest_query = request.GET.get("destination")
        target_date_str = request.GET.get("date")
        transport_filter = request.GET.get("filter", "all")

        if not origin_query or not dest_query or not target_date_str:
            return Response({"error": "Missing parameters"}, status=400)

        cache_key = f"prop_search_{origin_query}_{dest_query}_{target_date_str}_{transport_filter}"
        cached = cache.get(cache_key)
        if cached:
            return Response(cached)

        try:
            origin_loc = (
                Location.objects.select_related("parent")
                .prefetch_related("sub_locations", "parent__sub_locations")
                .get(code=origin_query)
            )
            dest_loc = (
                Location.objects.select_related("parent")
                .prefetch_related("sub_locations", "parent__sub_locations")
                .get(code=dest_query)
            )
            target_date = datetime.strptime(target_date_str, "%Y-%m-%d").date()
        except (Location.DoesNotExist, ValueError):
            return Response({"error": "Invalid parameters"}, status=400)

        origin_aliases = origin_loc.resolve_aliases()
        dest_aliases = dest_loc.resolve_aliases()

        # We fetch 4 days of data to allow for overnight bleed into the 4th day
        # e.g., a late flight on day 1 may connect to an early ferry on day 2.
        end_date = target_date + timedelta(days=4)

        # --- 1. FETCH DIRECT ROUTES ---
        # Find direct flights or ferries between the origin and destination directly.
        direct_flights = FlightInstance.objects.filter(
            route__origin__code__in=origin_aliases,
            route__destination__code__in=dest_aliases,
            date__range=[target_date, end_date],
            route__is_active=True,
            available_seats__gt=0,
        ).select_related(
            "route", "route__carrier", "route__origin", "route__destination"
        )

        direct_ferries = Sailing.objects.filter(
            route__origin__code__in=origin_aliases,
            route__destination__code__in=dest_aliases,
            date__range=[target_date, end_date],
            route__is_active=True,
        ).select_related(
            "route", "route__carrier", "route__origin", "route__destination"
        )

        # --- 2. FETCH CONNECTING ROUTES (LEG 1) ---
        # Get all flights departing from the origin that do NOT go straight to the destination.
        # These are potential "Leg 1" flights landing at a hub.
        leg1_flights = (
            FlightInstance.objects.filter(
                route__origin__code__in=origin_aliases,
                date__range=[target_date, end_date],
                route__is_active=True,
                available_seats__gt=0,
            )
            .exclude(route__destination__code__in=dest_aliases)
            .select_related(
                "route", "route__carrier", "route__origin", "route__destination"
            )
        )

        # Determine all unique locations these leg 1 flights land at
        hub_codes = {f.route.destination.code for f in leg1_flights}

        # Expand these hubs to include their aliases (e.g. an airport and a nearby ferry port)
        hub_locations = Location.objects.filter(code__in=hub_codes).prefetch_related(
            "sub_locations", "parent__sub_locations"
        )
        expanded_hubs = set()
        for loc in hub_locations:
            expanded_hubs.update(loc.resolve_aliases())

        # --- 3. FETCH CONNECTING ROUTES (LEG 2) ---
        # Get all flights and ferries that depart from these expanded hubs and go to the final destination.
        leg2_flights = FlightInstance.objects.filter(
            route__origin__code__in=expanded_hubs,
            route__destination__code__in=dest_aliases,
            date__range=[target_date, end_date],
            route__is_active=True,
            available_seats__gt=0,
        ).select_related(
            "route", "route__carrier", "route__origin", "route__destination"
        )

        leg2_ferries = Sailing.objects.filter(
            route__origin__code__in=expanded_hubs,
            route__destination__code__in=dest_aliases,
            date__range=[target_date, end_date],
            route__is_active=True,
        ).select_related(
            "route", "route__carrier", "route__origin", "route__destination"
        )

        # --- 4. ASSEMBLE ITINERARIES ---
        # We define acceptable connection times based on the mode of transport
        MIN_CONNECT_FLIGHT = 3600  # 1 Hour: Minimum time to connect plane-to-plane
        MIN_CONNECT_FERRY = 7200  # 2 Hours: Minimum time to connect plane-to-ferry (accounts for port transit)
        MAX_CONNECT = 64800 # 18 Hours: Max layover time before we consider it two separate trips

        results = []
        found_date = target_date
        date_was_changed = False

        # Loop through the 4-day window looking for a day with valid itineraries
        for i in range(4):
            check_date = target_date + timedelta(days=i)
            next_date = check_date + timedelta(days=1)
            day_itineraries = []

            for f in [x for x in direct_flights if x.date == check_date]:
                day_itineraries.append(
                    {"id": f"f_{f.id}", "legs": [ItineraryLegSerializer(f).data]}
                )
            for s in [x for x in direct_ferries if x.date == check_date]:
                day_itineraries.append(
                    {"id": f"s_{s.id}", "legs": [ItineraryLegSerializer(s).data]}
                )

            day_l1 = [f for f in leg1_flights if f.date == check_date]

            l2_candidates_f = [
                f for f in leg2_flights if f.date in (check_date, next_date)
            ]
            l2_candidates_s = [
                s for s in leg2_ferries if s.date in (check_date, next_date)
            ]

            # Check combinations of Leg 1 and Leg 2 for valid connections
            for l1 in day_l1:
                if not l1.route.arrival_time:
                    continue
                l1_arr_dt = datetime.combine(l1.date, l1.route.arrival_time)
                l1_dest_aliases = l1.route.destination.resolve_aliases()

                for l2 in l2_candidates_f:
                    if l2.route.origin.code not in l1_dest_aliases:
                        continue
                    if not l2.route.departure_time:
                        continue

                    l2_dep_dt = datetime.combine(l2.date, l2.route.departure_time)
                    gap = (l2_dep_dt - l1_arr_dt).total_seconds()

                    if MIN_CONNECT_FLIGHT <= gap <= MAX_CONNECT:
                        l1_data = ItineraryLegSerializer(l1).data
                        l2_data = ItineraryLegSerializer(l2).data

                        hours, mins = int(gap // 3600), int((gap % 3600) // 60)

                        # Dynamically flag if the layover spills into the next day
                        if l1.date != l2.date:
                            l1_data["layover_text"] = (
                                f"🌙 Overnight Layover: {hours}h {mins}m in {l1.route.destination.city} • Connect via Flight"
                            )
                        else:
                            l1_data["layover_text"] = (
                                f"✈️ {hours}h {mins}m Layover in {l1.route.destination.city} • Connect via Flight"
                            )

                        day_itineraries.append(
                            {"id": f"c_ff_{l1.id}_{l2.id}", "legs": [l1_data, l2_data]}
                        )

                for l2 in l2_candidates_s:
                    if l2.route.origin.code not in l1_dest_aliases:
                        continue
                    if not l2.departure_time:
                        continue

                    l2_dep_dt = datetime.combine(l2.date, l2.departure_time)
                    gap = (l2_dep_dt - l1_arr_dt).total_seconds()

                    if MIN_CONNECT_FERRY <= gap <= MAX_CONNECT:
                        l1_data = ItineraryLegSerializer(l1).data
                        l2_data = ItineraryLegSerializer(l2).data

                        hours, mins = int(gap // 3600), int((gap % 3600) // 60)

                        # Dynamically flag if the layover spills into the next day
                        if l1.date != l2.date:
                            l1_data["layover_text"] = (
                                f"🌙 Overnight Layover: {hours}h {mins}m in {l1.route.destination.city} • Connect via Ferry"
                            )
                        else:
                            l1_data["layover_text"] = (
                                f"⛴️ {hours}h {mins}m Layover in {l1.route.destination.city} • Connect via Ferry"
                            )

                        day_itineraries.append(
                            {"id": f"c_fs_{l1.id}_{l2.id}", "legs": [l1_data, l2_data]}
                        )

            if day_itineraries:
                results = day_itineraries
                if i > 0:
                    date_was_changed = True
                    found_date = check_date
                break

        results = ItineraryFilterBackend().filter_queryset(request, results, self)
        results = ItineraryOrderingFilter().filter_queryset(request, results, self)

        response_data = {
            "date_was_changed": date_was_changed,
            "found_date": found_date.strftime("%Y-%m-%d"),
            "results": results,
        }

        cache.set(cache_key, response_data, 60 * 5)
        return Response(response_data)
