from __future__ import annotations

from collections import defaultdict
from datetime import date, datetime, time, timedelta
from typing import Any

from django.core.cache import cache
from rest_framework import mixins, viewsets
from rest_framework.decorators import action
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.serializers import BaseSerializer
from rest_framework.throttling import ScopedRateThrottle

from .constants import (
    CACHE_TTL_AVAILABLE_DATES,
    CACHE_TTL_REFERENCE,
    CACHE_TTL_SEARCH,
    MAX_CONNECT_SECONDS,
    MIN_CONNECT_FERRY_SECONDS,
    MIN_CONNECT_FLIGHT_SECONDS,
    SEARCH_WINDOW_DAYS,
)
from .models import Carrier, FlightInstance, Location, ReportedIssue, Route, Sailing
from .serializers import (
    CarrierSerializer,
    ItineraryLegSerializer,
    LocationSerializer,
    ReportedIssueSerializer,
    RouteSerializer,
    SailingSerializer,
)


def _get_leg_departure_time(leg: FlightInstance | Sailing) -> time | None:
    return leg.departure_time if isinstance(leg, Sailing) else leg.route.departure_time


def _get_leg_arrival_time(leg: FlightInstance | Sailing) -> time | None:
    return leg.arrival_time if isinstance(leg, Sailing) else leg.route.arrival_time


def get_sliding_window(today: date | None = None) -> tuple[date, date]:
    """
    Compute the active 3- or 4-day sliding window (window_start, window_end)
    aligned with the Wednesday / Sunday automated scraper schedule:
    - Wed, Thu, Fri, Sat (weekday 2..5): window ends on upcoming Sunday (weekday 6)
    - Sun (weekday 6): window ends on upcoming Wednesday (+3 days)
    - Mon, Tue (weekday 0..1): window ends on upcoming Wednesday (weekday 2)
    """
    if today is None:
        today = date.today()
    window_start = today + timedelta(days=1)
    weekday = today.weekday()  # Mon=0, Tue=1, Wed=2, Thu=3, Fri=4, Sat=5, Sun=6
    if weekday in (2, 3, 4, 5):
        days_until_end = 6 - weekday
    elif weekday == 6:
        days_until_end = 3
    else:
        days_until_end = 2 - weekday
    window_end = today + timedelta(days=days_until_end)
    return window_start, window_end


def filter_and_sort_itineraries(
    itineraries: list[dict[str, Any]], transport_filter: str = "all"
) -> list[dict[str, Any]]:
    """
    Filter and sort dynamically assembled itineraries by transport mode.

    Filters:
    - 'ferry': Returns itineraries where at least one leg is a ferry.
    - 'flight': Returns itineraries where NO legs are ferries (all flights).
    - 'all': Returns all itineraries.
    """
    if transport_filter == "ferry":
        filtered = [
            it
            for it in itineraries
            if any(leg.get("is_ferry", False) for leg in it["legs"])
        ]
    elif transport_filter == "flight":
        filtered = [
            it
            for it in itineraries
            if not any(leg.get("is_ferry", False) for leg in it["legs"])
        ]
    else:
        filtered = list(itineraries)

    return sorted(
        filtered,
        key=lambda x: 1
        if any(leg.get("is_ferry", False) for leg in x["legs"])
        else 0,
        reverse=True,
    )


class LocationViewSet(viewsets.ReadOnlyModelViewSet):
    """
    ViewSet for listing selectable Locations (Airports and Primary Hubs).

    Internal sub-terminals (ferry ports with a parent airport) are excluded by default
    so the frontend receives a clean list of selectable hubs. To optimize database
    performance and prevent N+1 query problems, we use `select_related` for 'parent'
    and `prefetch_related` for 'sub_locations'.
    """

    queryset = (
        Location.objects.exclude(
            location_type=Location.LocationType.PRT,
            parent__isnull=False,
        )
        .select_related("parent")
        .prefetch_related("sub_locations")
        .all()
    )
    serializer_class = LocationSerializer

    def list(self, request: Request, *args: Any, **kwargs: Any) -> Response:
        cached = cache.get("prop_locations_list")
        if cached is not None:
            return Response(cached)
        response = super().list(request, *args, **kwargs)
        cache.set("prop_locations_list", list(response.data), CACHE_TTL_REFERENCE)
        return response


class CarrierViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Carrier.objects.all()
    serializer_class = CarrierSerializer

    def list(self, request: Request, *args: Any, **kwargs: Any) -> Response:
        cached = cache.get("prop_carriers_list")
        if cached is not None:
            return Response(cached)
        response = super().list(request, *args, **kwargs)
        cache.set("prop_carriers_list", list(response.data), CACHE_TTL_REFERENCE)
        return response


class SailingViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Sailing.objects.all()
    serializer_class = SailingSerializer


class ReportedIssueViewSet(
    mixins.CreateModelMixin, viewsets.GenericViewSet
):
    """
    Write-only endpoint for user-submitted route/schedule reports.
    Restricted to POST to prevent public exposure of user notes.
    """

    http_method_names = ["post", "options"]
    queryset = ReportedIssue.objects.all()
    serializer_class = ReportedIssueSerializer
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = "contact"

    def perform_create(self, serializer: BaseSerializer[Any]) -> None:
        issue = serializer.save()
        issue.send_notifications()


class RouteViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Route.objects.all()
    serializer_class = RouteSerializer

    def _compute_available_dates(
        self, origin_aliases: list[str], dest_aliases: list[str]
    ) -> list[str]:
        """
        Compute sorted YYYY-MM-DD strings with either a direct flight/sailing
        or a valid 2-leg connection between origin_aliases and dest_aliases.
        """
        # 1. DIRECT ROUTES
        flight_dates = set(
            FlightInstance.objects.filter(
                route__origin__code__in=origin_aliases,
                route__destination__code__in=dest_aliases,
                route__is_active=True,
            )
            .values_list("date", flat=True)
            .distinct()
        )

        ferry_dates = set(
            Sailing.objects.filter(
                route__origin__code__in=origin_aliases,
                route__destination__code__in=dest_aliases,
                route__is_active=True,
            )
            .values_list("date", flat=True)
            .distinct()
        )

        known_dates = flight_dates | ferry_dates
        connected_dates: set[date] = set()

        # 2. CONNECTING ROUTES (LEG 1)
        leg1_flights = list(
            FlightInstance.objects.filter(
                route__origin__code__in=origin_aliases,
                route__is_active=True,
            )
            .exclude(route__destination__code__in=dest_aliases)
            .select_related("route", "route__destination")
        )

        leg1_ferries = list(
            Sailing.objects.filter(
                route__origin__code__in=origin_aliases,
                route__is_active=True,
            )
            .exclude(route__destination__code__in=dest_aliases)
            .select_related("route", "route__destination")
        )

        all_leg1: list[FlightInstance | Sailing] = [*leg1_flights, *leg1_ferries]

        if all_leg1:
            hub_codes = {item.route.destination.code for item in all_leg1}
            hub_locations = (
                Location.objects.filter(code__in=hub_codes)
                .select_related("parent")
                .prefetch_related("sub_locations", "parent__sub_locations")
            )
            expanded_hubs: set[str] = set()
            hub_alias_map: dict[str, set[str]] = {}
            for loc in hub_locations:
                aliases = set(loc.resolve_aliases())
                hub_alias_map[loc.code] = aliases
                expanded_hubs.update(aliases)

            leg2_flights = list(
                FlightInstance.objects.filter(
                    route__origin__code__in=expanded_hubs,
                    route__destination__code__in=dest_aliases,
                    route__is_active=True,
                ).select_related("route", "route__origin")
            )

            leg2_ferries = list(
                Sailing.objects.filter(
                    route__origin__code__in=expanded_hubs,
                    route__destination__code__in=dest_aliases,
                    route__is_active=True,
                ).select_related("route", "route__origin")
            )

            leg2_by_date: dict[date, list[FlightInstance | Sailing]] = defaultdict(list)
            leg2_all: list[FlightInstance | Sailing] = [*leg2_flights, *leg2_ferries]
            for l2_item in leg2_all:
                leg2_by_date[l2_item.date].append(l2_item)

            for l1 in all_leg1:
                if l1.date in known_dates or l1.date in connected_dates:
                    continue

                l1_is_ferry = isinstance(l1, Sailing)
                l1_arr_time = _get_leg_arrival_time(l1)
                if not l1_arr_time:
                    continue

                l1_arr_dt = datetime.combine(l1.date, l1_arr_time)
                dest_code = l1.route.destination.code
                l1_dest_aliases = hub_alias_map.get(dest_code, {dest_code})

                candidate_l2 = (
                    leg2_by_date[l1.date] + leg2_by_date[l1.date + timedelta(days=1)]
                )
                for l2 in candidate_l2:
                    if l2.route.origin.code not in l1_dest_aliases:
                        continue
                    l2_is_ferry = isinstance(l2, Sailing)
                    l2_dep_time = _get_leg_departure_time(l2)
                    if not l2_dep_time:
                        continue

                    l2_dep_dt = datetime.combine(l2.date, l2_dep_time)
                    gap = (l2_dep_dt - l1_arr_dt).total_seconds()
                    min_connect = (
                        MIN_CONNECT_FERRY_SECONDS
                        if (l1_is_ferry or l2_is_ferry)
                        else MIN_CONNECT_FLIGHT_SECONDS
                    )
                    if min_connect <= gap <= MAX_CONNECT_SECONDS:
                        connected_dates.add(l1.date)
                        break

        all_dates = sorted(known_dates | connected_dates)
        return [d.strftime("%Y-%m-%d") for d in all_dates]

    @action(detail=False, methods=["get"], url_path="available-dates")
    def available_dates(self, request: Request) -> Response:
        origin_query = (request.GET.get("origin") or "").strip().upper()
        dest_query = (request.GET.get("destination") or "").strip().upper()

        if not origin_query or not dest_query:
            return Response({"error": "Missing parameters"}, status=400)
        if len(origin_query) > 10 or len(dest_query) > 10:
            return Response({"error": "Invalid parameters"}, status=400)

        window_start, window_end = get_sliding_window()
        cache_key = f"prop_dates_{origin_query}_{dest_query}"
        cached_dates = cache.get(cache_key)
        if cached_dates is not None:
            return Response(
                {
                    "available_dates": cached_dates,
                    "window_start": window_start.strftime("%Y-%m-%d"),
                    "window_end": window_end.strftime("%Y-%m-%d"),
                }
            )

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

        avail_dates = self._compute_available_dates(origin_aliases, dest_aliases)
        cache.set(cache_key, avail_dates, CACHE_TTL_AVAILABLE_DATES)
        return Response(
            {
                "available_dates": avail_dates,
                "window_start": window_start.strftime("%Y-%m-%d"),
                "window_end": window_end.strftime("%Y-%m-%d"),
            }
        )

    @action(detail=False, methods=["get"])
    def search(self, request: Request) -> Response:
        """
        Main search endpoint for dynamically assembling multi-leg itineraries.

        Algorithm Overview:
        Given an origin, destination, and optional target date, this method constructs
        potential travel itineraries. If `date` is omitted (e.g. 1-click Showcase Route),
        the server automatically resolves available dates and selects the earliest date
        in the active sliding window.

        1. Direct routes (single leg, flight or ferry)
        2. Connected routes (two legs: Flight -> Flight, Flight -> Ferry, Ferry -> Flight, Ferry -> Ferry)

        Sliding Window Mechanism:
        Uses a 4-day sliding window to catch overnight connections where a late flight
        on Day 1 connects to an early ferry on Day 2. If no valid itineraries are found
        on the requested date, it scans subsequent days and returns the first date with availability.
        """
        origin_query = (request.GET.get("origin") or "").strip().upper()
        dest_query = (request.GET.get("destination") or "").strip().upper()
        target_date_str = (request.GET.get("date") or "").strip()
        transport_filter = (request.GET.get("filter") or "all").strip().lower()

        if not origin_query or not dest_query:
            return Response({"error": "Missing parameters"}, status=400)
        if len(origin_query) > 10 or len(dest_query) > 10:
            return Response({"error": "Invalid parameters"}, status=400)

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
            return Response({"error": "Invalid parameters"}, status=400)

        origin_aliases = origin_loc.resolve_aliases()
        dest_aliases = dest_loc.resolve_aliases()
        window_start, window_end = get_sliding_window()

        avail_dates: list[str] | None = None
        if not target_date_str:
            dates_cache_key = f"prop_dates_{origin_query}_{dest_query}"
            avail_dates = cache.get(dates_cache_key)
            if avail_dates is None:
                avail_dates = self._compute_available_dates(origin_aliases, dest_aliases)
                cache.set(dates_cache_key, avail_dates, CACHE_TTL_AVAILABLE_DATES)

            window_start_str = window_start.strftime("%Y-%m-%d")
            future_dates = [d for d in avail_dates if d >= window_start_str]
            target_date_str = future_dates[0] if future_dates else window_start_str

        try:
            target_date = datetime.strptime(target_date_str, "%Y-%m-%d").date()
        except ValueError:
            return Response({"error": "Invalid parameters"}, status=400)

        cache_key = f"prop_search_{origin_query}_{dest_query}_{target_date_str}_{transport_filter}"
        cached = cache.get(cache_key)
        if cached is not None:
            response_payload = dict(cached)
            response_payload["window_start"] = window_start.strftime("%Y-%m-%d")
            response_payload["window_end"] = window_end.strftime("%Y-%m-%d")
            if avail_dates is not None:
                response_payload["available_dates"] = avail_dates
            return Response(response_payload)

        # Fetch 4 days of data to allow for overnight bleed into the 4th day
        end_date = target_date + timedelta(days=SEARCH_WINDOW_DAYS)

        # --- 1. FETCH DIRECT ROUTES ---
        direct_flights = list(
            FlightInstance.objects.filter(
                route__origin__code__in=origin_aliases,
                route__destination__code__in=dest_aliases,
                date__range=[target_date, end_date],
                route__is_active=True,
            ).select_related(
                "route", "route__carrier", "route__origin", "route__destination"
            )
        )

        direct_ferries = list(
            Sailing.objects.filter(
                route__origin__code__in=origin_aliases,
                route__destination__code__in=dest_aliases,
                date__range=[target_date, end_date],
                route__is_active=True,
            ).select_related(
                "route", "route__carrier", "route__origin", "route__destination"
            )
        )

        # --- 2. FETCH CONNECTING ROUTES (LEG 1) ---
        leg1_flights = list(
            FlightInstance.objects.filter(
                route__origin__code__in=origin_aliases,
                date__range=[target_date, end_date],
                route__is_active=True,
            )
            .exclude(route__destination__code__in=dest_aliases)
            .select_related(
                "route", "route__carrier", "route__origin", "route__destination"
            )
        )

        leg1_ferries = list(
            Sailing.objects.filter(
                route__origin__code__in=origin_aliases,
                date__range=[target_date, end_date],
                route__is_active=True,
            )
            .exclude(route__destination__code__in=dest_aliases)
            .select_related(
                "route", "route__carrier", "route__origin", "route__destination"
            )
        )

        # Determine all unique locations these leg 1 flights and ferries land at
        hub_codes = {f.route.destination.code for f in leg1_flights} | {
            s.route.destination.code for s in leg1_ferries
        }

        # Expand these hubs to include their aliases (e.g. an airport and a nearby ferry port)
        hub_locations = (
            Location.objects.filter(code__in=hub_codes)
            .select_related("parent")
            .prefetch_related("sub_locations", "parent__sub_locations")
        )
        expanded_hubs: set[str] = set()
        hub_alias_map: dict[str, set[str]] = {}
        for loc in hub_locations:
            aliases = set(loc.resolve_aliases())
            hub_alias_map[loc.code] = aliases
            expanded_hubs.update(aliases)

        # --- 3. FETCH CONNECTING ROUTES (LEG 2) ---
        leg2_flights = list(
            FlightInstance.objects.filter(
                route__origin__code__in=expanded_hubs,
                route__destination__code__in=dest_aliases,
                date__range=[target_date, end_date],
                route__is_active=True,
            ).select_related(
                "route", "route__carrier", "route__origin", "route__destination"
            )
        )

        leg2_ferries = list(
            Sailing.objects.filter(
                route__origin__code__in=expanded_hubs,
                route__destination__code__in=dest_aliases,
                date__range=[target_date, end_date],
                route__is_active=True,
            ).select_related(
                "route", "route__carrier", "route__origin", "route__destination"
            )
        )

        # --- 4. ASSEMBLE ITINERARIES ---
        results: list[dict[str, Any]] = []
        found_date = target_date
        date_was_changed = False

        for i in range(SEARCH_WINDOW_DAYS):
            check_date = target_date + timedelta(days=i)
            next_date = check_date + timedelta(days=1)
            day_itineraries: list[dict[str, Any]] = []

            for f in (x for x in direct_flights if x.date == check_date):
                leg_data = dict(ItineraryLegSerializer(f).data)
                day_itineraries.append(
                    {
                        "id": f"f_{f.id}",
                        "is_sold_out": bool(leg_data.get("is_sold_out", False)),
                        "legs": [leg_data],
                    }
                )
            for s in (x for x in direct_ferries if x.date == check_date):
                leg_data = dict(ItineraryLegSerializer(s).data)
                day_itineraries.append(
                    {
                        "id": f"s_{s.id}",
                        "is_sold_out": False,
                        "legs": [leg_data],
                    }
                )

            day_l1_all: list[FlightInstance | Sailing] = [
                *(f for f in leg1_flights if f.date == check_date),
                *(s for s in leg1_ferries if s.date == check_date),
            ]
            l2_candidates_all: list[FlightInstance | Sailing] = [
                *(f for f in leg2_flights if f.date in (check_date, next_date)),
                *(s for s in leg2_ferries if s.date in (check_date, next_date)),
            ]

            # Unified connection stitcher across all 4 transport permutations (FF, FS, SF, SS)
            for l1 in day_l1_all:
                l1_is_ferry = isinstance(l1, Sailing)
                l1_arr_time = _get_leg_arrival_time(l1)
                if not l1_arr_time:
                    continue

                l1_arr_dt = datetime.combine(l1.date, l1_arr_time)
                hub_code = l1.route.destination.code
                hub_city = l1.route.destination.city
                l1_dest_aliases = hub_alias_map.get(hub_code, {hub_code})
                l1_base_data: dict[str, Any] | None = None

                for l2 in l2_candidates_all:
                    if l2.route.origin.code not in l1_dest_aliases:
                        continue
                    l2_is_ferry = isinstance(l2, Sailing)
                    l2_dep_time = _get_leg_departure_time(l2)
                    if not l2_dep_time:
                        continue

                    l2_dep_dt = datetime.combine(l2.date, l2_dep_time)
                    gap = (l2_dep_dt - l1_arr_dt).total_seconds()
                    min_connect = (
                        MIN_CONNECT_FERRY_SECONDS
                        if (l1_is_ferry or l2_is_ferry)
                        else MIN_CONNECT_FLIGHT_SECONDS
                    )

                    if min_connect <= gap <= MAX_CONNECT_SECONDS:
                        if l1_base_data is None:
                            l1_base_data = dict(ItineraryLegSerializer(l1).data)
                        l2_data = dict(ItineraryLegSerializer(l2).data)

                        hours, mins = int(gap // 3600), int((gap % 3600) // 60)
                        connect_mode = "Ferry" if l2_is_ferry else "Flight"
                        connect_icon = "⛴️" if l2_is_ferry else "✈️"

                        if l1.date != l2.date:
                            layover_text = (
                                f"🌙 Overnight Layover: {hours}h {mins}m in {hub_city} "
                                f"• Connect via {connect_mode}"
                            )
                        else:
                            layover_text = (
                                f"{connect_icon} {hours}h {mins}m Layover in {hub_city} "
                                f"• Connect via {connect_mode}"
                            )

                        l1_data = {**l1_base_data, "layover_text": layover_text}
                        prefix = f"c_{'s' if l1_is_ferry else 'f'}{'s' if l2_is_ferry else 'f'}"
                        is_sold_out = bool(
                            l1_data.get("is_sold_out", False)
                            or l2_data.get("is_sold_out", False)
                        )
                        day_itineraries.append(
                            {
                                "id": f"{prefix}_{l1.id}_{l2.id}",
                                "is_sold_out": is_sold_out,
                                "legs": [l1_data, l2_data],
                            }
                        )

            if day_itineraries:
                results = day_itineraries
                if i > 0:
                    date_was_changed = True
                    found_date = check_date
                break

        results = filter_and_sort_itineraries(results, transport_filter)

        response_data: dict[str, Any] = {
            "date_was_changed": date_was_changed,
            "found_date": found_date.strftime("%Y-%m-%d"),
            "results": results,
        }
        cache.set(cache_key, response_data, CACHE_TTL_SEARCH)

        full_response = {
            **response_data,
            "window_start": window_start.strftime("%Y-%m-%d"),
            "window_end": window_end.strftime("%Y-%m-%d"),
        }
        if avail_dates is not None:
            full_response["available_dates"] = avail_dates
        return Response(full_response)

