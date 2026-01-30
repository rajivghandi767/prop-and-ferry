import os
import time
import re
from datetime import datetime, timedelta
from django.core.management.base import BaseCommand
from django.utils import timezone
from amadeus import Client, ResponseError
from core.models import Location, Route, Carrier
from core.constants import TARGETS, REGIONAL_HUBS, GATEWAYS


class Command(BaseCommand):
    help = (
        'Fetches flight routes using a 2-Phase Strategy to conserve API Quota:\n'
        '1. Topology Mapping (Cheap/Free): Filters out impossible routes.\n'
        '2. Schedule Sweep (Expensive): Checks specific dates for valid routes only.'
    )

    def parse_duration(self, iso_str: str) -> int:
        """
        Parses ISO 8601 duration format (e.g., 'PT1H30M') into total minutes (90).
        """
        if not iso_str:
            return 0
        hours_match = re.search(r'(\d+)H', iso_str)
        mins_match = re.search(r'(\d+)M', iso_str)
        hours = int(hours_match.group(1)) if hours_match else 0
        minutes = int(mins_match.group(1)) if mins_match else 0
        return (hours * 60) + minutes

    def get_valid_destinations(self, amadeus, origin):
        """
        PHASE 0 HELPER: TOPOLOGY CHECK
        ------------------------------
        Before asking "Is there a flight on Tuesday?", we ask "Do you fly there AT ALL?"
        This uses the 'Airport Routes' API which has a separate, cheaper quota.

        Returns: A Set of IATA codes reachable nonstop from the origin.
        """
        try:
            response = amadeus.airport.direct_destinations.get(
                departureAirportCode=origin)
            if response.data:
                return {item['iataCode'] for item in response.data}
            return set()
        except ResponseError:
            return set()
        except Exception:
            return set()

    def fetch_and_save(self, amadeus, origin, dest, date_str):
        """
        PHASE 1 HELPER: SCHEDULE SWEEP
        ------------------------------
        Checks availability for a specific Verified Route on a specific Date.
        Includes 'Smart Skip' caching to prevent double-billing.
        """

        # --- SMART SKIP LOGIC ---
        # If we successfully updated this specific route (Origin->Dest)
        # within the last 24 hours, do not call the API again.
        last_24h = timezone.now() - timedelta(hours=24)
        if Route.objects.filter(origin__code=origin, destination__code=dest, updated_at__gte=last_24h).exists():
            self.stdout.write(
                f"z Skipping {origin}->{dest} (Data is fresh < 24h)", ending='\r')
            return

        self.stdout.write(
            f". Checking {origin}->{dest} on {date_str}", ending='\r')

        try:
            # --- API CALL ---
            # strict nonStop='true' is CRITICAL.
            # We are building a graph of direct edges. Connecting flights are calculated
            # by our own graph engine, not by the airline.
            response = amadeus.shopping.flight_offers_search.get(
                originLocationCode=origin,
                destinationLocationCode=dest,
                departureDate=date_str,
                adults=1,
                max=1,
                nonStop='true'
            )

            if not response.data:
                return

            # --- DATA PROCESSING ---
            for offer in response.data:
                for itinerary in offer['itineraries']:
                    # Redundant check for nonstop safety (Segments > 1 means it has a layover)
                    if len(itinerary['segments']) > 1:
                        continue

                    segment = itinerary['segments'][0]
                    carrier_code = segment['carrierCode']
                    dep = segment['departure']['iataCode']
                    arr = segment['arrival']['iataCode']

                    # Parsing Metadata
                    minutes = self.parse_duration(segment['duration'])
                    dep_time = segment['departure']['at'].split('T')[1]
                    arr_time = segment['arrival']['at'].split('T')[1]

                    # 1. Get/Create Carrier
                    carrier, _ = Carrier.objects.get_or_create(
                        code=carrier_code,
                        defaults={'name': f"Airline {carrier_code}",
                                  'carrier_type': 'AIR'}
                    )

                    # 2. Get/Create Locations (Airports)
                    loc_dep, _ = Location.objects.get_or_create(
                        code=dep, defaults={'name': dep, 'location_type': 'APT'})
                    loc_arr, _ = Location.objects.get_or_create(
                        code=arr, defaults={'name': arr, 'location_type': 'APT'})

                    # 3. Update Route
                    route, created = Route.objects.update_or_create(
                        origin=loc_dep, destination=loc_arr, carrier=carrier,
                        defaults={
                            'is_active': True,
                            'duration_minutes': minutes,
                            'departure_time': dep_time,
                            'arrival_time': arr_time
                        }
                    )

                    # 4. Schedule Builder
                    # If it's a new route, reset the 'days_of_operation' string.
                    if created:
                        route.days_of_operation = ""

                    found_day = str(datetime.strptime(
                        date_str, '%Y-%m-%d').isoweekday())

                    # Append the day (e.g., add "3" to "15" -> "135")
                    if found_day not in route.days_of_operation:
                        route.days_of_operation = "".join(
                            sorted(route.days_of_operation + found_day))
                        route.save()

                        if created:
                            self.stdout.write(self.style.SUCCESS(
                                f"\n   ✨ NEW ROUTE DISCOVERED: {carrier_code} {dep}->{arr}"))
                        else:
                            self.stdout.write(self.style.NOTICE(
                                f"\n   🔄 UPDATED SCHEDULE: {carrier_code} {dep}->{arr} (Added Day {found_day})"))

            time.sleep(0.1)  # Respect API Rate Limits
        except Exception:
            pass

    def handle(self, *args, **kwargs):
        self.stdout.write("✈️  Initializing Smart Route Scraper...")

        amadeus = Client(
            client_id=os.getenv('AMADEUS_API_KEY'),
            client_secret=os.getenv('AMADEUS_API_SECRET')
        )

        # --- PHASE 0: TOPOLOGY MAPPING ---
        # Goal: Reduce the search space.
        # Instead of checking 3,000 combinations (Gateways * Hubs * Dates),
        # we first check which airports actually connect.

        self.stdout.write(self.style.WARNING(
            "\n--- PHASE 0: TOPOLOGY MAPPING (Filtering Invalid Routes) ---"))
        valid_routes = set()

        # A. Gateway <-> Hub Checks
        for gateway in GATEWAYS:
            self.stdout.write(
                f"   Mapping connections from {gateway}...", ending='\r')
            destinations = self.get_valid_destinations(amadeus, gateway)
            for hub in REGIONAL_HUBS:
                if hub in destinations:
                    valid_routes.add((gateway, hub))
                    # Assume return route exists for now
                    valid_routes.add((hub, gateway))

        # B. Hub <-> Target Checks
        for hub in REGIONAL_HUBS:
            self.stdout.write(
                f"   Mapping connections from {hub}...", ending='\r')
            destinations = self.get_valid_destinations(amadeus, hub)
            for target in TARGETS:
                if target in destinations:
                    valid_routes.add((hub, target))
                    valid_routes.add((target, hub))

        self.stdout.write(self.style.SUCCESS(
            f"\n   ✅ Topology Mapped. Search space reduced to {len(valid_routes)} valid routes."))

        # --- PHASE 1: 7-DAY SCHEDULE SWEEP ---
        # Goal: Determine WHICH DAYS these verified routes actually fly.
        # We check 7 consecutive days starting 3 weeks out (to avoid close-in booking anomalies).

        today = datetime.now()
        start_date = today + timedelta(days=21)
        dates = [(start_date + timedelta(days=i)).strftime('%Y-%m-%d')
                 for i in range(7)]

        self.stdout.write(
            f"\n📅 Starting 7-Day Schedule Sweep ({dates[0]} to {dates[-1]})")

        for date in dates:
            self.stdout.write(self.style.WARNING(
                f"\n--- PROCESSING DATE: {date} ---"))
            for origin, dest in valid_routes:
                self.fetch_and_save(amadeus, origin, dest, date)

        self.stdout.write(self.style.SUCCESS(
            "\n✨ Route Fetching Complete! Database is updated."))
