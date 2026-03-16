import logging
from django.core.management.base import BaseCommand
from core.models import Location

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = 'Updates airport metadata and bootstraps ferry terminals and topologies.'

    def handle(self, *args, **kwargs):
        self.stdout.write("🌍 Enriching Location Data...")

        # FORMAT: (Code, City, Name, Country)
        location_data = [
            # --- Major US Hubs ---
            ('MIA', 'Miami', 'Miami International', 'USA'),
            ('JFK', 'New York', 'John F. Kennedy', 'USA'),
            ('EWR', 'Newark', 'Newark Liberty Intl', 'USA'),
            ('ATL', 'Atlanta', 'Hartsfield-Jackson Atlanta Intl', 'USA'),
            ('CLT', 'Charlotte', 'Charlotte Douglas Intl', 'USA'),
            ('IAH', 'Houston', 'George Bush Intercontinental', 'USA'),
            ('FLL', 'Fort Lauderdale', 'Fort Lauderdale-Hollywood Intl', 'USA'),
            ('BOS', 'Boston', 'Logan International', 'USA'),

            # --- Major Canada Hubs ---
            ('YYZ', 'Toronto', 'Toronto Pearson Intl', 'Canada'),
            ('YUL', 'Montreal', 'Montréal-Pierre Elliott Trudeau Intl', 'Canada'),

            # --- Major Europe Hubs ---
            ('LHR', 'London', 'Heathrow', 'UK'),
            ('LGW', 'London', 'Gatwick', 'UK'),
            ('CDG', 'Paris', 'Charles de Gaulle', 'France'),
            ('ORY', 'Paris', 'Orly', 'France'),
            ('FRA', 'Frankfurt', 'Frankfurt am Main', 'Germany'),
            ('AMS', 'Amsterdam', 'Schiphol', 'Netherlands'),

            # --- Caribbean Hubs & Destinations ---
            ('SJU', 'San Juan', 'Luis Muñoz Marín Intl', 'Puerto Rico'),
            ('ANU', 'St. John\'s', 'V.C. Bird Intl', 'Antigua'),
            ('PTP', 'Pointe-à-Pitre', 'Pointe-à-Pitre Intl', 'Guadeloupe'),
            ('BGI', 'Bridgetown', 'Grantley Adams Intl', 'Barbados'),
            ('POS', 'Port of Spain', 'Piarco Intl', 'Trinidad & Tobago'),
            ('SXM', 'Philipsburg', 'Princess Juliana Intl', 'St. Maarten'),
            ('UVF', 'Vieux Fort', 'Hewanorra Intl', 'St. Lucia'),
            ('SLU', 'Castries', 'George F. L. Charles', 'St. Lucia'),
            ('DOM', 'Marigot', 'Douglas-Charles', 'Dominica'),
            ('FDF', 'Fort-de-France', 'Martinique Aimé Césaire Intl', 'Martinique'),
            ('SKB', 'Basseterre', 'Robert L. Bradshaw Intl', 'St. Kitts'),
            ('GND', 'St. George\'s', 'Maurice Bishop Intl', 'Grenada'),
            ('SVD', 'Kingstown', 'Argyle Intl', 'St. Vincent'),

            # --- Ferry Terminals ---
            ('DMROS', 'Roseau', 'Roseau Ferry Terminal', 'Dominica'),
            ('LCCAS', 'Castries', 'Castries Ferry Terminal', 'St. Lucia'),
            ('GPPTP', 'Pointe-à-Pitre', 'Bergevin Ferry Terminal', 'Guadeloupe'),
            ('MQFDF', 'Fort-de-France', 'Fort-de-France Ferry Terminal', 'Martinique'),

            # --- Metropolitan / Parent Codes ---
            ('NYC', 'New York', 'All Airports', 'USA'),
            ('LON', 'London', 'All Airports', 'UK'),
            ('PAR', 'Paris', 'All Airports', 'France'),
        ]

        # 1. Update or Create Metadata (Bootstrapping capability)
        for code, city, name, country in location_data:
            loc_type = 'PRT' if code in [
                'DMROS', 'LCCAS', 'GPPTP', 'MQFDF'] else 'APT'

            obj, created = Location.objects.update_or_create(
                code=code,
                defaults={
                    'city': city,
                    'name': name,
                    'country': country,
                    'location_type': loc_type
                }
            )
            if created:
                logger.info(f"🏗️ Built Core Location: {code} ({city})")

        # 2. Establish Relationships
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
            parent = Location.objects.filter(code=parent_code).first()
            if parent:
                for child_code in children:
                    child = Location.objects.filter(code=child_code).first()
                    if child:
                        child.parent = parent
                        child.save()
                        logger.info(
                            f"Linked {child_code} -> Parent: {parent_code}")
                    else:
                        logger.warning(
                            f"Could not find child {child_code} in DB.")
            else:
                logger.warning(f"Could not find parent {parent_code} in DB.")

        self.stdout.write(self.style.SUCCESS(
            "✨ Locations Enriched & Topologies Linked!"))
