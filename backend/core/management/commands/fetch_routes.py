import os
import logging
import re
import time
from typing import Set
from datetime import datetime, timedelta

from django.core.management.base import BaseCommand
from django.utils import timezone
from amadeus import Client, ResponseError

from core.models import Location, Route, Carrier, FlightInstance
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
            return set()

    def fetch_and_save(self, amadeus: Client, origin: str, dest: str, date_str: str):
        # DATE-SPECIFIC CACHE: Avoids checking the same day repeatedly
        if FlightInstance.objects.filter(route__origin__code=origin, route__destination__code=dest, date=date_str).exists():
            self.stdout.write(
                f"[API Calls: {self.api_calls}] 💤 Skipping {origin}->{dest} on {date_str} (Cached)", ending='\r')
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
                time.sleep(2)
            return

        if response.data:
            for offer in response.data:
                price = offer.get('price', {}).get('total')
                currency = offer.get('price', {}).get('currency')
                seats = offer.get('numberOfBookableSeats')

                for itinerary in offer.get('itineraries', []):
                    segments = itinerary.get('segments', [])
                    if len(segments) == 1:
                        cabin = offer.get('travelerPricings', [{}])[0].get(
                            'fareDetailsBySegment', [{}])[0].get('cabin', '')
                        self._process_segment(
                            segments[0], date_str, price, currency, seats, cabin)
        time.sleep(0.1)

    def _process_segment(self, segment: dict, date_str: str, price: str, currency: str, seats: int, cabin: str):
        carrier_code = segment['carrierCode']
        dep_code = segment['departure']['iataCode']
        arr_code = segment['arrival']['iataCode']

        carrier, _ = Carrier.objects.get_or_create(code=carrier_code, defaults={
                                                   'name': f"Airline {carrier_code}", 'carrier_type': 'AIR'})
        loc_dep, _ = Location.objects.get_or_create(
            code=dep_code, defaults={'name': dep_code})
        loc_arr, _ = Location.objects.get_or_create(
            code=arr_code, defaults={'name': arr_code})

        dep_time = segment['departure']['at'].split('T')[1]
        arr_time = segment['arrival']['at'].split('T')[1]

        route, created = Route.objects.update_or_create(
            origin=loc_dep, destination=loc_arr, carrier=carrier, departure_time=dep_time,
            defaults={
                'is_active': True, 'duration_minutes': self.parse_duration(segment.get('duration')),
                'arrival_time': arr_time, 'flight_number': f"{carrier_code} {segment.get('number', '')}".strip(),
                'aircraft_type': segment.get('aircraft', {}).get('code', '')
            }
        )

        found_day = str(datetime.strptime(date_str, '%Y-%m-%d').isoweekday())
        current_days = route.days_of_operation or ""
        if found_day not in current_days:
            route.days_of_operation = "".join(sorted(current_days + found_day))
            route.save()

        date_obj = datetime.strptime(date_str, '%Y-%m-%d').date()
        FlightInstance.objects.update_or_create(
            route=route, date=date_obj,
            defaults={'price_amount': price, 'currency': currency,
                      'available_seats': seats, 'cabin_class': cabin}
        )

    def handle(self, *args, **kwargs):
        self.stdout.write("✈️  Initializing Smart Route Scraper...")

        # DB BLOAT PROTECTION: Clean up past flights
        today = datetime.now().date()
        deleted_flights, _ = FlightInstance.objects.filter(
            date__lt=today).delete()
        if deleted_flights:
            self.stdout.write(
                f"🧹 Pruned {deleted_flights} past flight instances.")

        amadeus = Client(client_id=os.getenv('AMADEUS_API_KEY'),
                         client_secret=os.getenv('AMADEUS_API_SECRET'))

        self.stdout.write(self.style.WARNING(
            "\n--- PHASE 0: TOPOLOGY MAPPING ---"))
        valid_routes = set()
        for origin in set(GATEWAYS + REGIONAL_HUBS):
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

        self.stdout.write(self.style.WARNING(
            "\n--- PHASE 1: SCHEDULE SWEEP ---"))
        # THE COLD START FIX:
        has_immediate_flights = FlightInstance.objects.filter(
            date__range=[today, today + timedelta(days=7)]).exists()

        if not has_immediate_flights:
            self.stdout.write(
                "🧊 Cold Start Detected! Running initial 28-day deep sweep...")
            dates = [(datetime.now() + timedelta(days=i)).strftime('%Y-%m-%d')
                     for i in range(1, 29)]
        else:
            self.stdout.write(
                "🔥 DB is warm. Appending new dates to the rolling window...")
            dates = [(datetime.now() + timedelta(days=21+i)
                      ).strftime('%Y-%m-%d') for i in range(7)]

        for date in dates:
            for origin, dest in valid_routes:
                self.fetch_and_save(amadeus, origin, dest, date)

        self.stdout.write(self.style.SUCCESS(
            f"\n✨ DONE! Total usage: {self.api_calls} calls."))
