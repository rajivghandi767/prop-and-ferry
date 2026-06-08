import logging
from datetime import datetime, time, timedelta
from django.core.management.base import BaseCommand
from core.models import Location, Carrier, Route, FlightInstance

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = 'Populates the database with the flight network and base ferry topology.'

    def handle(self, *args, **kwargs):
        self.stdout.write("🌱 Seeding Global Network Data...")

        # 1. CARRIERS
        carriers_data = [
            ('AA', 'American Airlines', 'AIR', 'https://www.aa.com'),
            ('BA', 'British Airways', 'AIR', 'https://www.britishairways.com'),
            ('B6', 'JetBlue', 'AIR', 'https://www.jetblue.com'),
            ('DL', 'Delta Air Lines', 'AIR', 'https://www.delta.com'),
            ('AF', 'Air France', 'AIR', 'https://www.airfrance.com'),
            ('TX', 'Air Caraibes', 'AIR', 'https://www.aircaraibes.com'),
            ('WM', 'Winair', 'AIR', 'https://www.winair.sx'),
            ('JY', 'interCaribbean', 'AIR', 'https://www.intercaribbean.com'),
            ('BW', 'Caribbean Airlines', 'AIR',
             'https://www.caribbean-airlines.com'),
            ('LXI', "L'Express des Iles", 'SEA',
             'https://www.frs-express.com'),
        ]

        carriers = {}
        for code, name, c_type, web in carriers_data:
            obj, _ = Carrier.objects.get_or_create(
                code=code, defaults={'name': name,
                                     'carrier_type': c_type, 'website': web}
            )
            carriers[code] = obj

        # 2. LOCATIONS
        locations_data = [
            ('NYC', 'All Airports', 'New York', 'APT'),
            ('PAR', 'All Airports', 'Paris', 'APT'),
            ('LON', 'All Airports', 'London', 'APT'),
            ('ORY', 'Paris Orly', 'Paris', 'APT'),
            ('CDG', 'Charles de Gaulle', 'Paris', 'APT'),
            ('JFK', 'John F. Kennedy', 'New York', 'APT'),
            ('EWR', 'Newark Liberty', 'Newark', 'APT'),
            ('LHR', 'London Heathrow', 'London', 'APT'),
            ('LGW', 'London Gatwick', 'London', 'APT'),
            ('MIA', 'Miami Intl', 'Miami', 'APT'),
            ('DFW', 'Dallas/Fort Worth Intl', 'Dallas', 'APT'),
            ('IAH', 'George Bush Intercontinental', 'Houston', 'APT'),
            ('ATL', 'Hartsfield-Jackson', 'Atlanta', 'APT'),
            ('PTP', 'Pointe-à-Pitre Intl', 'Guadeloupe', 'APT'),
            ('ANU', 'V.C. Bird Intl', 'Antigua', 'APT'),
            ('SJU', 'Luis Muñoz Marín', 'San Juan', 'APT'),
            ('BGI', 'Grantley Adams', 'Barbados', 'APT'),
            ('SLU', 'George F. L. Charles', 'Castries', 'APT'),
            ('UVF', 'Hewanorra', 'Vieux Fort', 'APT'),
            ('POS', 'Piarco Intl', 'Port of Spain', 'APT'),
            ('FDF', 'Martinique Aimé Césaire', 'Fort-de-France', 'APT'),
            ('SKB', 'Robert L. Bradshaw', 'Basseterre', 'APT'),
            ('SXM', 'Princess Juliana', 'St. Maarten', 'APT'),
            ('DOM', 'Douglas-Charles', 'Dominica', 'APT'),

            # Ferry Terminals (Must be seeded so scrape_ferries.py can find them in dev)
            ('DMROS', 'Roseau Ferry Terminal', 'Roseau', 'PRT'),
            ('GPPTP', 'Bergevin Ferry Terminal', 'Guadeloupe', 'PRT'),
            ('LCCAS', 'Castries Ferry Terminal', 'St. Lucia', 'PRT'),
            ('MQFDF', 'Fort-de-France Ferry Terminal', 'Fort-de-France', 'PRT'),
        ]

        locs = {}
        for code, name, city, l_type in locations_data:
            obj, _ = Location.objects.get_or_create(
                code=code, defaults={'name': name,
                                     'city': city, 'location_type': l_type}
            )
            locs[code] = obj

        # 3. RELATIONSHIPS
        self.stdout.write("🔗 Linking Parents & Children...")
        relationships = {
            'PAR': ['ORY', 'CDG'],
            'NYC': ['JFK', 'EWR'],
            'LON': ['LHR', 'LGW'],
            'DOM': ['DMROS'],
            'SLU': ['LCCAS', 'UVF'],
            'PTP': ['GPPTP'],
            'FDF': ['MQFDF']
        }

        for parent_code, children in relationships.items():
            if parent_code in locs:
                for child_code in children:
                    if child_code in locs:
                        locs[child_code].parent = locs[parent_code]
                        locs[child_code].save()

        # 4. MOCK FLIGHT ROUTES & INSTANCES
        def create_route(origin, dest, carrier, dep_str, arr_str, dur_min, flight_num, aircraft):
            dep_time = datetime.strptime(dep_str, '%H:%M').time()
            arr_time = datetime.strptime(arr_str, '%H:%M').time()

            route, _ = Route.objects.update_or_create(
                origin=locs[origin], destination=locs[dest], carrier=carriers[carrier], departure_time=dep_time,
                defaults={'arrival_time': arr_time, 'duration_minutes': dur_min, 'days_of_operation': '1234567',
                          'is_active': True, 'flight_number': flight_num, 'aircraft_type': aircraft}
            )

            # Generate searchable dates for the next 7 days
            today = datetime.now().date()
            for i in range(7):
                FlightInstance.objects.update_or_create(
                    route=route, date=today + timedelta(days=i),
                    defaults={'price_amount': 199.99,
                              'currency': 'USD', 'available_seats': 9}
                )

        self.stdout.write("✈️ Building Flight Network Graph...")
        create_route('CDG', 'SXM', 'AF', '10:30',
                     '14:20', 530, 'AF 498', 'A330')
        create_route('ORY', 'FDF', 'TX', '10:45',
                     '14:00', 530, 'TX 510', 'A350')
        create_route('ORY', 'PTP', 'TX', '11:00',
                     '13:35', 530, 'TX 540', 'A350')
        create_route('LHR', 'BGI', 'BA', '10:00',
                     '14:55', 510, 'BA 255', '777')
        create_route('LGW', 'ANU', 'BA', '09:30',
                     '14:15', 510, 'BA 2157', '777')
        create_route('JFK', 'ANU', 'B6', '08:30',
                     '13:00', 270, 'B6 1234', 'A321')
        create_route('ATL', 'SXM', 'DL', '09:45',
                     '14:10', 230, 'DL 1883', '757')
        create_route('IAH', 'MIA', 'AA', '06:00',
                     '09:30', 150, 'AA 1120', '738')
        create_route('DFW', 'SJU', 'AA', '08:00',
                     '13:30', 270, 'AA 1324', '738')
        create_route('MIA', 'UVF', 'AA', '10:15',
                     '13:45', 210, 'AA 888', '738')
        create_route('SXM', 'DOM', 'WM', '16:30',
                     '17:30', 60, 'WM 311', 'DHC6')
        create_route('SXM', 'SKB', 'WM', '15:30',
                     '16:00', 30, 'WM 112', 'DHC6')
        create_route('SKB', 'DOM', 'JY', '17:00',
                     '18:00', 60, 'JY 415', 'E120')
        create_route('ANU', 'DOM', 'WM', '15:30',
                     '16:15', 45, 'WM 333', 'DHC6')
        create_route('SJU', 'DOM', 'JY', '15:30',
                     '17:00', 90, 'JY 411', 'E120')
        create_route('BGI', 'DOM', 'JY', '17:00', '18:00', 60, 'JY 712', 'AT7')
        create_route('POS', 'DOM', 'BW', '14:00', '15:30', 90, 'BW 434', 'AT7')

        self.stdout.write(self.style.SUCCESS(
            "✨ Flight Network Seed Complete. Scrape ferries using scrape_ferries.py..."))
