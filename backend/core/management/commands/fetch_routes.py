import os
import logging
import re
import time
from typing import Set
from datetime import datetime, timedelta

from django.core.management.base import BaseCommand
from django.utils import timezone
from amadeus import Client, ResponseError

from core.models import Location, Route, Carrier
from core.constants import TARGETS, REGIONAL_HUBS, GATEWAYS

# Configure structured logging for production observability
logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = 'Fetches flight routes using a 2-Phase Strategy: Topology Mapping -> Schedule Sweep.'

    # Global Counter to track API usage across methods
    api_calls = 0

    def parse_duration(self, iso_str: str) -> int:
        """Parses ISO 8601 duration (e.g., 'PT1H30M') into minutes."""
        if not iso_str:
            return 0
        hours = 0
        minutes = 0

        if match := re.search(r'(\d+)H', iso_str):
            hours = int(match.group(1))
        if match := re.search(r'(\d+)M', iso_str):
            minutes = int(match.group(1))

        return (hours * 60) + minutes

    def get_valid_destinations(self, amadeus: Client, origin: str) -> Set[str]:
        """
        PHASE 0: Queries Amadeus for all direct destinations from a generic origin.
        Used to build the search graph.
        """
        try:
            # --- API CALL (Airport Routes Endpoint) ---
            self.api_calls += 1
            # ------------------------------------------

            response = amadeus.airport.direct_destinations.get(
                departureAirportCode=origin)
            return {item['iataCode'] for item in response.data} if response.data else set()
        except ResponseError as e:
            logger.warning(f"Amadeus API Error for {origin}: {e}")
            return set()

    def fetch_and_save(self, amadeus: Client, origin: str, dest: str, date_str: str):
        """
        PHASE 1: Checks specific availability.
        """
        # --- SMART SKIP (Cache Check) ---
        # If we checked this exact route < 24 hours ago, skip the API call.
        yesterday = timezone.now() - timedelta(hours=24)
        if Route.objects.filter(origin__code=origin, destination__code=dest, updated_at__gte=yesterday).exists():
            self.stdout.write(
                f"[API Calls: {self.api_calls}] 💤 Skipping {origin}->{dest} (Fresh)", ending='\r')
            return

        self.stdout.write(
            f"[API Calls: {self.api_calls + 1}] 🔎 Checking {origin}->{dest} on {date_str}", ending='\r')

        try:
            # --- API CALL (Flight Offers Search Endpoint) ---
            self.api_calls += 1
            # ------------------------------------------------

            response = amadeus.shopping.flight_offers_search.get(
                originLocationCode=origin,
                destinationLocationCode=dest,
                departureDate=date_str,
                adults=1,
                max=10,  # Fetch up to 10 options to ensure we get a mix of times
                nonStop='true'
            )
        except ResponseError as e:
            if e.code == 429:
                logger.error(
                    f"[API Calls: {self.api_calls}] ⏳ Rate Limit Hit! Sleeping for 2 seconds...")
                time.sleep(2)
                return
            logger.warning(f"Failed to fetch {origin}->{dest}: {e}")
            return

        if not response.data:
            return

        for offer in response.data:
            for itinerary in offer.get('itineraries', []):
                segments = itinerary.get('segments', [])
                if len(segments) != 1:
                    # Skip connecting flights (we build our own graph)
                    continue

                segment = segments[0]
                self._process_segment(segment, date_str)

        # Respect API limits (Amadeus Free/Test is often 100ms)
        time.sleep(0.1)

    def _process_segment(self, segment: dict, date_str: str):
        """Helper to handle database writes."""
        carrier_code = segment['carrierCode']
        dep_code = segment['departure']['iataCode']
        arr_code = segment['arrival']['iataCode']

        # 1. Get/Create Carrier
        carrier, _ = Carrier.objects.get_or_create(
            code=carrier_code,
            defaults={'name': f"Airline {carrier_code}", 'carrier_type': 'AIR'}
        )

        # 2. Get/Create Locations
        loc_dep, _ = Location.objects.get_or_create(
            code=dep_code, defaults={'name': dep_code})
        loc_arr, _ = Location.objects.get_or_create(
            code=arr_code, defaults={'name': arr_code})

        # 3. Update Route
        minutes = self.parse_duration(segment.get('duration'))
        dep_time = segment['departure']['at'].split('T')[1]
        arr_time = segment['arrival']['at'].split('T')[1]

        # IDEMPOTENCY CHECK:
        # We uniquely identify a flight by Origin + Dest + Carrier + Departure Time.
        # This allows multiple flights per day (e.g. 10:00 AM and 5:00 PM) to coexist.
        route, created = Route.objects.update_or_create(
            origin=loc_dep, destination=loc_arr, carrier=carrier,
            departure_time=dep_time,
            defaults={
                'is_active': True,
                'duration_minutes': minutes,
                'arrival_time': arr_time
                # updated_at is auto-handled by the model
            }
        )

        # 4. Schedule Logic (Accumulate Days)
        found_day = str(datetime.strptime(date_str, '%Y-%m-%d').isoweekday())
        current_days = route.days_of_operation or ""

        if found_day not in current_days:
            route.days_of_operation = "".join(sorted(current_days + found_day))
            route.save()
            if created:
                logger.info(
                    f"✨ DISCOVERED: {carrier_code} {dep_code}->{arr_code} @ {dep_time} (Day {found_day})")

    def handle(self, *args, **kwargs):
        self.stdout.write("✈️  Initializing Smart Route Scraper...")

        amadeus = Client(
            client_id=os.getenv('AMADEUS_API_KEY'),
            client_secret=os.getenv('AMADEUS_API_SECRET')
        )

        # ==========================================================
        # PHASE 0: TOPOLOGY MAPPING (Optimized)
        # ==========================================================
        self.stdout.write(self.style.WARNING(
            "\n--- PHASE 0: TOPOLOGY MAPPING ---"))

        start_calls_p0 = self.api_calls
        valid_routes = set()

        # 1. Build a unique list of all airports we need to check
        all_origins = set(GATEWAYS + REGIONAL_HUBS)

        for origin in all_origins:
            self.stdout.write(
                f"[API Calls: {self.api_calls}] 📡 Mapping {origin}...", ending='\r')

            # ONE API Call per Unique Airport
            destinations = self.get_valid_destinations(amadeus, origin)

            # 2. Apply "Role-Based" Logic
            is_gateway = origin in GATEWAYS
            is_hub = origin in REGIONAL_HUBS

            # ROLE A: If it's a Gateway, check if it flies to Hubs or Targets
            if is_gateway:
                for hub in REGIONAL_HUBS:
                    if hub in destinations and hub != origin:
                        valid_routes.add((origin, hub))
                        valid_routes.add((hub, origin))

                for target in TARGETS:
                    if target in destinations:
                        valid_routes.add((origin, target))
                        valid_routes.add((target, origin))

            # ROLE B: If it's a Hub, check if it flies to Targets (or other Hubs)
            if is_hub:
                for target in TARGETS:
                    if target in destinations:
                        valid_routes.add((origin, target))
                        valid_routes.add((target, origin))

                # Optional: Hub -> Hub (Inter-island connectivity)
                for other_hub in REGIONAL_HUBS:
                    if other_hub in destinations and other_hub != origin:
                        valid_routes.add((origin, other_hub))

        # --- REPORT PHASE 0 USAGE ---
        p0_usage = self.api_calls - start_calls_p0
        self.stdout.write(self.style.SUCCESS(
            f"\n✅ Topology mapped. {p0_usage} API calls used from the Airport Search endpoint"
        ))

        # ==========================================================
        # PHASE 1: SCHEDULE SWEEP
        # ==========================================================
        today = datetime.now()
        start_date = today + timedelta(days=21)  # Look 3 weeks out
        dates = [(start_date + timedelta(days=i)).strftime('%Y-%m-%d')
                 for i in range(7)]

        self.stdout.write(
            f"\n📅 Starting 7-Day Schedule Sweep ({dates[0]} to {dates[-1]})")

        start_calls_p1 = self.api_calls

        for date in dates:
            self.stdout.write(self.style.WARNING(
                f"\n--- PROCESSING DATE: {date} ---"))
            for origin, dest in valid_routes:
                self.fetch_and_save(amadeus, origin, dest, date)

        # --- REPORT PHASE 1 USAGE ---
        p1_usage = self.api_calls - start_calls_p1
        self.stdout.write(self.style.SUCCESS(
            f"\n✅ Schedule sweep complete. {p1_usage} API calls used from the Flight Offers Search endpoint"
        ))

        self.stdout.write(self.style.SUCCESS(
            f"\n✨ DONE! Total usage: {self.api_calls} calls."
        ))
