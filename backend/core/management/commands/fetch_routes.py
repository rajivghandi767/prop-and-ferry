import os
import time
import re
from django.core.management.base import BaseCommand
from django.utils import timezone
from amadeus import Client, ResponseError
from datetime import datetime, timedelta
from core.models import Location, Route, Carrier


class Command(BaseCommand):
    help = 'Fetches routes: 1. Maps Network (Topology) -> 2. Checks Schedules (Smart 7-Day Sweep)'

    def parse_duration(self, iso_str):
        if not iso_str:
            return None
        hours_match = re.search(r'(\d+)H', iso_str)
        mins_match = re.search(r'(\d+)M', iso_str)
        hours = int(hours_match.group(1)) if hours_match else 0
        minutes = int(mins_match.group(1)) if mins_match else 0
        return (hours * 60) + minutes

    def get_valid_destinations(self, amadeus, origin):
        """
        PHASE 0 HELPER: Asks 'Where can I fly NONSTOP from X?'
        Uses the 'Airport Routes' API (Separate 3k quota).
        """
        try:
            # This endpoint returns destinations served by direct flights.
            # We filter these again in Phase 1 just to be 100% sure.
            response = amadeus.airport.direct_destinations.get(
                departureAirportCode=origin
            )
            if response.data:
                return {item['iataCode'] for item in response.data}
            return set()
        except ResponseError:
            return set()
        except Exception:
            return set()

    def fetch_and_save(self, amadeus, origin, dest, date_str):
        """
        PHASE 1 HELPER: Asks 'What time is the flight on Date X?'
        STRICTLY ENFORCES NONSTOP FLIGHTS.
        """

        # --- 0. SMART SKIP (Save Money 💸) ---
        last_24h = timezone.now() - timedelta(hours=24)
        if Route.objects.filter(origin__code=origin, destination__code=dest, updated_at__gte=last_24h).exists():
            self.stdout.write(
                f"z Skipping {origin}->{dest} (Fresh 24h)", ending='\r')
            return

        self.stdout.write(
            f". Checking {origin}->{dest} on {date_str}", ending='\r')

        try:
            # --- 1. CALL API (STRICT NONSTOP) ---
            response = amadeus.shopping.flight_offers_search.get(
                originLocationCode=origin,
                destinationLocationCode=dest,
                departureDate=date_str,
                adults=1,
                max=1,
                nonStop='true'  # <--- HARDCODED LOCK: NO STOPS ALLOWED
            )

            if not response.data:
                return

            # --- 2. PROCESS & SAVE ---
            for offer in response.data:
                for itinerary in offer['itineraries']:
                    for segment in itinerary['segments']:
                        # Double check: If segment count > 1, it's not nonstop.
                        if len(itinerary['segments']) > 1:
                            continue

                        carrier_code = segment['carrierCode']
                        dep = segment['departure']['iataCode']
                        arr = segment['arrival']['iataCode']
                        minutes = self.parse_duration(segment['duration'])
                        dep_time = segment['departure']['at'].split('T')[1]
                        arr_time = segment['arrival']['at'].split('T')[1]

                        carrier, _ = Carrier.objects.get_or_create(
                            code=carrier_code, defaults={
                                'name': f"Airline {carrier_code}", 'carrier_type': 'AIR'}
                        )
                        loc_dep, _ = Location.objects.get_or_create(
                            code=dep, defaults={'name': dep, 'location_type': 'APT'})
                        loc_arr, _ = Location.objects.get_or_create(
                            code=arr, defaults={'name': arr, 'location_type': 'APT'})

                        route, created = Route.objects.update_or_create(
                            origin=loc_dep, destination=loc_arr, carrier=carrier,
                            defaults={
                                'is_active': True,
                                'duration_minutes': minutes,
                                'departure_time': dep_time,
                                'arrival_time': arr_time
                            }
                        )

                        if created:
                            route.days_of_operation = ""
                        found_day = str(datetime.strptime(
                            date_str, '%Y-%m-%d').isoweekday())

                        if found_day not in route.days_of_operation:
                            route.days_of_operation = "".join(
                                sorted(route.days_of_operation + found_day))
                            route.save()

                        if created:
                            self.stdout.write(self.style.SUCCESS(
                                f"\n   ✨ NEW: {carrier_code} {dep}->{arr}"))
                        else:
                            self.stdout.write(self.style.NOTICE(
                                f"\n   🔄 UPDATED: {carrier_code} {dep}->{arr} (Day {found_day})"))

            time.sleep(0.1)
        except Exception:
            pass

    def handle(self, *args, **kwargs):
        self.stdout.write("✈️  Initializing Nonstop Scraper...")

        amadeus = Client(
            client_id=os.getenv('AMADEUS_API_KEY'),
            client_secret=os.getenv('AMADEUS_API_SECRET')
        )

        # --- 1. CONFIGURATION ---
        TARGETS = ['DOM']
        REGIONAL_HUBS = ['SJU', 'BGI', 'ANU', 'PTP', 'FDF',
                         'SLU', 'SXM', 'POS', 'SKB', 'SVD', 'EIS', 'STT']
        GATEWAYS = ['MIA', 'JFK', 'EWR', 'ATL', 'CLT', 'IAH', 'FLL',
                    'YYZ', 'YUL', 'LHR', 'LGW', 'CDG', 'ORY', 'AMS', 'FRA']

        # --- 2. PHASE 0: TOPOLOGY MAPPING (The Filter) ---
        self.stdout.write(self.style.WARNING(
            "\n--- PHASE 0: MAPPING NETWORK (Filtering Impossible Routes) ---"))
        self.stdout.write(
            "   (This uses the 'Direct Destinations' API to skip non-existent routes)")

        valid_routes = set()

        # A. Gateways <-> Hubs
        for gateway in GATEWAYS:
            self.stdout.write(f"   Mapping from {gateway}...", ending='\r')
            destinations = self.get_valid_destinations(amadeus, gateway)
            for hub in REGIONAL_HUBS:
                if hub in destinations:
                    valid_routes.add((gateway, hub))
                    # Assume return flight exists
                    valid_routes.add((hub, gateway))

        # B. Hubs <-> Targets
        for hub in REGIONAL_HUBS:
            self.stdout.write(f"   Mapping from {hub}...", ending='\r')
            destinations = self.get_valid_destinations(amadeus, hub)
            for target in TARGETS:
                if target in destinations:
                    valid_routes.add((hub, target))
                    valid_routes.add((target, hub))

        self.stdout.write(self.style.SUCCESS(
            f"\n   ✅ Optimization Complete. Reduced search space to {len(valid_routes)} valid routes."))

        # --- 3. PHASE 1: THE 7-DAY SWEEP (The Execution) ---
        today = datetime.now()
        start_date = today + timedelta(days=21)
        dates = [(start_date + timedelta(days=i)).strftime('%Y-%m-%d')
                 for i in range(7)]

        self.stdout.write(
            f"\n📅 Starting 7-Day Sweep on VALID routes ({dates[0]} to {dates[-1]})")
        self.stdout.write("   ⚠️  Strictly enforcing NONSTOP flights.")

        for date in dates:
            self.stdout.write(self.style.WARNING(f"\n--- DATE: {date} ---"))
            for origin, dest in valid_routes:
                self.fetch_and_save(amadeus, origin, dest, date)

        self.stdout.write(self.style.SUCCESS("\n✨ Route Fetching Complete!"))
