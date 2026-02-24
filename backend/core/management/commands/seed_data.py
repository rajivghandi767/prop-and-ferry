import logging
import random
from datetime import datetime, time, timedelta
from django.core.management.base import BaseCommand
from core.models import Location, Carrier, Route, Sailing

# Configure logging to output to console
logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = 'Populates the database with realistic dummy data for testing without API calls.'

    def handle(self, *args, **kwargs):
        self.stdout.write("🌱 Seeding Database...")

        # ==========================================
        # 1. CARRIERS (Airlines & Ferry Operators)
        # ==========================================
        carriers_data = [
            # Airlines
            {'code': 'AA', 'name': 'American Airlines',
                'type': 'AIR', 'web': 'https://www.aa.com'},
            {'code': 'B6', 'name': 'JetBlue', 'type': 'AIR',
                'web': 'https://www.jetblue.com'},
            {'code': 'BA', 'name': 'British Airways', 'type': 'AIR',
                'web': 'https://www.britishairways.com'},
            {'code': 'JY', 'name': 'interCaribbean', 'type': 'AIR',
                'web': 'https://www.intercaribbean.com'},
            {'code': 'WM', 'name': 'Winair', 'type': 'AIR',
                'web': 'https://www.winair.sx'},
            {'code': 'TX', 'name': 'Air Caraibes', 'type': 'AIR',
                'web': 'https://www.aircaraibes.com'},
            # Ferries
            {'code': 'LXP', 'name': 'FRS Express', 'type': 'SEA',
                'web': 'https://www.lexpressdesiles.com'},
        ]

        carriers = {}
        for c in carriers_data:
            obj, _ = Carrier.objects.get_or_create(
                code=c['code'],
                defaults={'name': c['name'],
                          'carrier_type': c['type'], 'website': c['web']}
            )
            carriers[c['code']] = obj
        self.stdout.write(f"✅ Loaded {len(carriers)} Carriers")

        # ==========================================
        # 2. LOCATIONS (Gateways, Hubs, Islands)
        # ==========================================
        locations_data = [
            # Gateways
            {'code': 'JFK', 'name': 'John F. Kennedy Intl',
                'city': 'New York', 'type': 'APT'},
            {'code': 'MIA', 'name': 'Miami Intl', 'city': 'Miami', 'type': 'APT'},
            {'code': 'LHR', 'name': 'London Heathrow',
                'city': 'London', 'type': 'APT'},
            # Regional Hubs
            {'code': 'SJU', 'name': 'Luis Muñoz Marín',
                'city': 'San Juan', 'type': 'APT'},
            {'code': 'ANU', 'name': 'V.C. Bird Intl',
                'city': 'Antigua', 'type': 'APT'},
            {'code': 'BGI', 'name': 'Grantley Adams',
                'city': 'Barbados', 'type': 'APT'},
            {'code': 'SXM', 'name': 'Princess Juliana',
                'city': 'St. Maarten', 'type': 'APT'},
            {'code': 'PTP', 'name': 'Pointe-à-Pitre Intl',
                'city': 'Guadeloupe', 'type': 'APT'},
            {'code': 'FDF', 'name': 'Martinique Aimé Césaire',
                'city': 'Martinique', 'type': 'APT'},
            {'code': 'SLU', 'name': 'George F. L. Charles',
                'city': 'St. Lucia', 'type': 'APT'},
            # Target
            {'code': 'DOM', 'name': 'Douglas-Charles',
                'city': 'Dominica', 'type': 'APT'},
            {'code': 'DMROS', 'name': 'Roseau Ferry Terminal',
                'city': 'Roseau', 'type': 'PRT'},
            {'code': 'GPPTP', 'name': 'Pointe-à-Pitre Ferry Terminal',
                'city': 'Guadeloupe', 'type': 'PRT'},
            {'code': 'LCCAS', 'name': 'Castries Ferry Terminal',
                'city': 'St. Lucia', 'type': 'PRT'},
        ]

        locs = {}
        for l in locations_data:
            obj, _ = Location.objects.get_or_create(
                code=l['code'],
                defaults={'name': l['name'], 'city': l['city'],
                          'location_type': l['type']}
            )
            locs[l['code']] = obj
        self.stdout.write(f"✅ Loaded {len(locs)} Locations")

        # ==========================================
        # 3. ROUTES (The Network Graph)
        # ==========================================
        # Helper to create routes easily
        def create_route(origin, dest, carrier, dep_str, dur_min, flight_num, aircraft):
            dep_time = datetime.strptime(dep_str, '%H:%M').time()
            # Calculate arrival time roughly
            dummy_date = datetime(2022, 1, 1, dep_time.hour, dep_time.minute)
            arr_time = (dummy_date + timedelta(minutes=dur_min)).time()

            Route.objects.update_or_create(
                origin=locs[origin],
                destination=locs[dest],
                carrier=carriers[carrier],
                departure_time=dep_time,
                defaults={
                    'arrival_time': arr_time,
                    'duration_minutes': dur_min,
                    'days_of_operation': '1234567',  # Daily
                    'is_active': True,
                    'flight_number': flight_num,
                    'aircraft_type': aircraft
                }
            )

        self.stdout.write("🔗 Building Flight Network...")

        # --- A. GATEWAY -> REGIONAL HUB (Long Haul) ---
        create_route('JFK', 'ANU', 'AA', '08:00', 240,
                     'AA 123', '738')  # Arrives ~12:00
        create_route('JFK', 'BGI', 'B6', '09:30', 280,
                     'B6 456', 'A321')  # Arrives ~14:10
        create_route('MIA', 'DOM', 'AA', '10:00', 195,
                     'AA 3579', 'E175')  # Direct to DOM
        create_route('MIA', 'SXM', 'AA', '11:00', 180, 'AA 888', '738')
        create_route('LHR', 'ANU', 'BA', '10:00', 510,
                     'BA 255', '777')  # Arrives ~18:30 (Late!)

        # --- B. REGIONAL HUB -> DOM (Island Hoppers) ---
        # Good Connections
        create_route('ANU', 'DOM', 'WM', '14:00', 45, 'WM 333', 'DHC6')
        create_route('BGI', 'DOM', 'JY', '16:00', 50, 'JY 777', 'AT7')

        # Overnight Connection (Arrives ANU late from LHR, flies next morning)
        create_route('ANU', 'DOM', 'WM', '07:00', 45, 'WM 331', 'DHC6')

        # --- C. FERRY ROUTES ---
        # Note: Ferries need a Route object as a parent, but rely on Sailing objects for specific dates
        ferry_route, _ = Route.objects.get_or_create(
            origin=locs['GPPTP'], destination=locs['DMROS'], carrier=carriers['LXP'],
            defaults={'duration_minutes': 135, 'days_of_operation': '1234567'}
        )

        # Create Sailings for the next 7 days
        today = datetime.now().date()
        for i in range(7):
            date = today + timedelta(days=i)
            Sailing.objects.get_or_create(
                route=ferry_route,
                date=date,
                departure_time=time(8, 0),  # 8:00 AM
                defaults={
                    'arrival_time': time(10, 15),
                    'duration_minutes': 135,
                    'price_text': '€59'
                }
            )

        self.stdout.write(self.style.SUCCESS(
            "✨ Seed Data Complete! Ready for dev."))
