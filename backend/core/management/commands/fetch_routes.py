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

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = 'Fetches flight routes using a 2-Phase Strategy: Topology Mapping -> Schedule Sweep.'
    api_calls = 0

    def parse_duration(self, iso_str: str) -> int:
        if not iso_str:
            return 0
        hours = int(match.group(1)) if (
            match := re.search(r'(\d+)H', iso_str)) else 0
        minutes = int(match.group(1)) if (
            match := re.search(r'(\d+)M', iso_str)) else 0
        return (hours * 60) + minutes

    def get_valid_destinations(self, amadeus: Client, origin: str) -> Set[str]:
        try:
            self.api_calls += 1
            response = amadeus.airport.direct_destinations.get(
                departureAirportCode=origin)
            return {item['iataCode'] for item in response.data} if response.data else set()
        except ResponseError as e:
            logger.warning(f"Amadeus API Error for {origin}: {e}")
            return set()

    def fetch_and_save(self, amadeus: Client, origin: str, dest: str, date_str: str):
        yesterday = timezone.now() - timedelta(hours=24)
        if Route.objects.filter(origin__code=origin, destination__code=dest, updated_at__gte=yesterday).exists():
            self.stdout.write(
                f"[API Calls: {self.api_calls}] 💤 Skipping {origin}->{dest} (Fresh)", ending='\r')
            return

        self.stdout.write(
            f"[API Calls: {self.api_calls + 1}] 🔎 Checking {origin}->{dest} on {date_str}", ending='\r')

        try:
            self.api_calls += 1
            response = amadeus.shopping.flight_offers_search.get(
                originLocationCode=origin, destinationLocationCode=dest,
                departureDate=date_str, adults=1, max=10, nonStop='true'
            )
        except ResponseError as e:
            if e.code == 429:
                logger.error(
                    f"[API Calls: {self.api_calls}] ⏳ Rate Limit Hit! Sleeping for 2 seconds...")
                time.sleep(2)
            else:
                logger.warning(f"Failed to fetch {origin}->{dest}: {e}")
            return

        if response.data:
            for offer in response.data:
                for itinerary in offer.get('itineraries', []):
                    segments = itinerary.get('segments', [])
                    if len(segments) == 1:
                        self._process_segment(segments[0], date_str)
        time.sleep(0.1)

    def _process_segment(self, segment: dict, date_str: str):
        carrier_code = segment['carrierCode']
        dep_code = segment['departure']['iataCode']
        arr_code = segment['arrival']['iataCode']

        flight_num = f"{carrier_code} {segment.get('number', '')}".strip()
        aircraft_code = segment.get('aircraft', {}).get('code', '')

        carrier, _ = Carrier.objects.get_or_create(
            code=carrier_code, defaults={
                'name': f"Airline {carrier_code}", 'carrier_type': 'AIR'}
        )
        loc_dep, _ = Location.objects.get_or_create(
            code=dep_code, defaults={'name': dep_code})
        loc_arr, _ = Location.objects.get_or_create(
            code=arr_code, defaults={'name': arr_code})

        dep_time = segment['departure']['at'].split('T')[1]
        arr_time = segment['arrival']['at'].split('T')[1]

        route, created = Route.objects.update_or_create(
            origin=loc_dep, destination=loc_arr, carrier=carrier, departure_time=dep_time,
            defaults={
                'is_active': True,
                'duration_minutes': self.parse_duration(segment.get('duration')),
                'arrival_time': arr_time,
                'flight_number': flight_num,
                'aircraft_type': aircraft_code
            }
        )

        found_day = str(datetime.strptime(date_str, '%Y-%m-%d').isoweekday())
        current_days = route.days_of_operation or ""

        if found_day not in current_days:
            route.days_of_operation = "".join(sorted(current_days + found_day))
            route.save()
            if created:
                logger.info(
                    f"✨ DISCOVERED: {flight_num} {dep_code}->{arr_code} @ {dep_time} (Day {found_day})")

    def handle(self, *args, **kwargs):
        self.stdout.write("✈️  Initializing Smart Route Scraper...")
        amadeus = Client(client_id=os.getenv('AMADEUS_API_KEY'),
                         client_secret=os.getenv('AMADEUS_API_SECRET'))

        self.stdout.write(self.style.WARNING(
            "\n--- PHASE 0: TOPOLOGY MAPPING ---"))
        valid_routes = set()
        all_origins = set(GATEWAYS + REGIONAL_HUBS)

        for origin in all_origins:
            destinations = self.get_valid_destinations(amadeus, origin)

            if origin in GATEWAYS:
                for hub in REGIONAL_HUBS:
                    if hub in destinations and hub != origin:
                        valid_routes.update([(origin, hub), (hub, origin)])
                for target in TARGETS:
                    if target in destinations:
                        valid_routes.update(
                            [(origin, target), (target, origin)])

            if origin in REGIONAL_HUBS:
                for target in TARGETS:
                    if target in destinations:
                        valid_routes.update(
                            [(origin, target), (target, origin)])
                for other_hub in REGIONAL_HUBS:
                    if other_hub in destinations and other_hub != origin:
                        valid_routes.add((origin, other_hub))

        self.stdout.write(self.style.SUCCESS(
            f"\n✅ Topology mapped. {self.api_calls} API calls used."))

        self.stdout.write(self.style.WARNING(
            "\n--- PHASE 1: SCHEDULE SWEEP ---"))
        dates = [(datetime.now() + timedelta(days=21+i)).strftime('%Y-%m-%d')
                 for i in range(7)]

        for date in dates:
            for origin, dest in valid_routes:
                self.fetch_and_save(amadeus, origin, dest, date)

        self.stdout.write(self.style.SUCCESS(
            f"\n✨ DONE! Total usage: {self.api_calls} calls."))
