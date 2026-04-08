import os
import logging
import re
import time
import requests
from datetime import datetime, timedelta

from django.core.management.base import BaseCommand
from core.models import Location, Route, Carrier, FlightInstance

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = 'Fetches strictly DOM-centric flight routes via Duffel API for a rolling 3-Day POC window.'
    api_calls = 0

    def get_duffel_headers(self):
        return {
            "Authorization": f"Bearer {os.getenv('DUFFEL_ACCESS_TOKEN')}",
            "Duffel-Version": "v2",
            "Accept": "application/json",
            "Content-Type": "application/json"
        }

    def parse_duration(self, iso_str: str) -> int:
        if not iso_str:
            return 0
        hours = int(match.group(1)) if (
            match := re.search(r'(\d+)H', iso_str)) else 0
        minutes = int(match.group(1)) if (
            match := re.search(r'(\d+)M', iso_str)) else 0
        return (hours * 60) + minutes

    def fetch_and_save(self, origin: str, dest: str, date_str: str) -> bool:
        target_date = datetime.strptime(date_str, '%Y-%m-%d').date()
        self.stdout.write(
            f"[API Calls: {self.api_calls + 1}] 🔎 Duffel: {origin}->{dest} on {date_str}", ending='\r')

        self.api_calls += 1
        payload = {
            "data": {
                "slices": [{"origin": origin, "destination": dest, "departure_date": date_str}],
                "passengers": [{"type": "adult"}],
                "max_connections": 0
            }
        }

        try:
            res = requests.post("https://api.duffel.com/air/offer_requests",
                                json=payload, headers=self.get_duffel_headers())
            if res.status_code == 429:
                time.sleep(2)
                return self.fetch_and_save(origin, dest, date_str)

            response_data = res.json().get('data', {})
        except Exception as e:
            logger.error(f"Request failed: {e}")
            return False

        offers = response_data.get('offers', [])

        # Overwrite logic: Drops existing records for this day to account for airline cancellations
        FlightInstance.objects.filter(
            route__origin__code=origin, route__destination__code=dest, date=target_date
        ).delete()

        if not offers:
            return False

        for offer in offers:
            price = offer.get('total_amount')
            currency = offer.get('total_currency')
            seats = 9  # Standardized availability assumption for the Stitcher

            for slice_obj in offer.get('slices', []):
                segments = slice_obj.get('segments', [])
                if len(segments) == 1:
                    cabin = segments[0].get('passengers', [{}])[
                        0].get('cabin_class', 'economy')
                    self._process_segment(
                        segments[0], date_str, price, currency, seats, cabin)

        time.sleep(0.2)
        return True

    def _process_segment(self, segment: dict, date_str: str, price: str, currency: str, seats: int, cabin: str):
        # 1. Safely handle null JSON objects by falling back to {}
        op_carrier = segment.get('operating_carrier') or {}
        mkt_carrier = segment.get('marketing_carrier') or {}
        aircraft_data = segment.get('aircraft') or {}

        # 2. Safely extract codes
        carrier_code = op_carrier.get(
            'iata_code') or mkt_carrier.get('iata_code', 'UNK')
        dep_code = segment['origin']['iata_code']
        arr_code = segment['destination']['iata_code']

        carrier, _ = Carrier.objects.get_or_create(
            code=carrier_code, defaults={'name': op_carrier.get(
                'name', f"Airline {carrier_code}"), 'carrier_type': 'AIR'}
        )
        loc_dep, _ = Location.objects.get_or_create(
            code=dep_code, defaults={'name': dep_code})
        loc_arr, _ = Location.objects.get_or_create(
            code=arr_code, defaults={'name': arr_code})

        dep_time = segment['departing_at'].split('T')[1][:5]
        arr_time = segment['arriving_at'].split('T')[1][:5]
        flight_num = segment.get('operating_carrier_flight_number') or segment.get(
            'marketing_carrier_flight_number', '')

        route, _ = Route.objects.update_or_create(
            origin=loc_dep, destination=loc_arr, carrier=carrier, departure_time=dep_time,
            defaults={
                'is_active': True,
                'duration_minutes': self.parse_duration(segment.get('duration')),
                'arrival_time': arr_time,
                'flight_number': f"{carrier_code} {flight_num}".strip(),
                'aircraft_type': aircraft_data.get('iata_code', '')
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
        self.stdout.write(
            "✈️  Initializing Global Micro-Network Duffel Scraper...")

        if not os.getenv('DUFFEL_ACCESS_TOKEN'):
            self.stdout.write(self.style.ERROR(
                "❌ Missing DUFFEL_ACCESS_TOKEN in environment."))
            return

        today = datetime.now().date()
        deleted_flights, _ = FlightInstance.objects.filter(
            date__lt=today).delete()
        if deleted_flights:
            self.stdout.write(
                f"🧹 Pruned {deleted_flights} past flight instances.")

        self.stdout.write(self.style.WARNING(
            "\n--- PHASE 1: GLOBAL MICRO-NETWORK DISCOVERY ---"))

        valid_routes = set()

        ferry_hubs = ['PTP', 'FDF', 'UVF']
        flight_hubs = ['ANU', 'BGI']

        GATEWAY_ROUTES = {
            'NYC': ['BGI', 'ANU', 'UVF'],
            'PAR': ['PTP', 'FDF'],
            'LON': ['ANU', 'BGI']
        }

        days_ahead = 5 - today.weekday()
        if days_ahead <= 0:
            days_ahead += 7
        next_saturday = (today + timedelta(days=days_ahead)
                         ).strftime('%Y-%m-%d')

        if self.fetch_and_save('NYC', 'DOM', next_saturday):
            valid_routes.add(('NYC', 'DOM'))
            valid_routes.add(('DOM', 'NYC'))

        active_flight_hubs = []
        for hub in flight_hubs:
            if self.fetch_and_save(hub, 'DOM', next_saturday):
                valid_routes.add((hub, 'DOM'))
                valid_routes.add(('DOM', hub))
                active_flight_hubs.append(hub)

        for gateway, valid_hubs in GATEWAY_ROUTES.items():
            for hub in valid_hubs:
                if hub in ferry_hubs or hub in active_flight_hubs:
                    if self.fetch_and_save(gateway, hub, next_saturday):
                        valid_routes.add((gateway, hub))
                        valid_routes.add((hub, gateway))

        self.stdout.write(self.style.SUCCESS(
            f"\n✅ Global Network Mapped! Found {len(valid_routes) // 2} active two-way routes."))

        self.stdout.write(self.style.WARNING(
            "\n--- PHASE 2: TARGETED 3-DAY ROLLING SWEEP ---"))
        rolling_dates = [(today + timedelta(days=i)).strftime('%Y-%m-%d')
                         for i in range(3)]

        for date in rolling_dates:
            for origin, dest in valid_routes:
                if date != next_saturday:
                    self.fetch_and_save(origin, dest, date)

        self.stdout.write(self.style.SUCCESS(
            f"\n✨ DONE! Total usage: {self.api_calls} Duffel calls."))
