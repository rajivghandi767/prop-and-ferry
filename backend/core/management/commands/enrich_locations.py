import logging
from django.core.management.base import BaseCommand
from core.models import Location

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = 'Updates airport metadata with real City, Name, and Parent relationships'

    def handle(self, *args, **kwargs):
        # Master Dictionary of Caribbean/Hub Data
        data = {
            # --- Major US Hubs ---
            'MIA': {'city': 'Miami', 'name': 'Miami International', 'country': 'USA'},
            'JFK': {'city': 'New York', 'name': 'John F. Kennedy', 'country': 'USA'},
            'EWR': {'city': 'Newark', 'name': 'Newark Liberty Intl', 'country': 'USA'},
            'ATL': {'city': 'Atlanta', 'name': 'Hartsfield-Jackson Atlanta Intl', 'country': 'USA'},
            'CLT': {'city': 'Charlotte', 'name': 'Charlotte Douglas Intl', 'country': 'USA'},
            'IAH': {'city': 'Houston', 'name': 'George Bush Intercontinental', 'country': 'USA'},
            'FLL': {'city': 'Fort Lauderdale', 'name': 'Fort Lauderdale-Hollywood Intl', 'country': 'USA'},
            'BOS': {'city': 'Boston', 'name': 'Logan International', 'country': 'USA'},

            # --- Major Canada Hubs ---
            'YYZ': {'city': 'Toronto', 'name': 'Toronto Pearson Intl', 'country': 'Canada'},
            'YUL': {'city': 'Montreal', 'name': 'Montréal-Pierre Elliott Trudeau Intl', 'country': 'Canada'},

            # --- Major Europe Hubs ---
            'FRA': {'city': 'Frankfurt', 'name': 'Frankfurt am Main', 'country': 'Germany'},
            'LGW': {'city': 'London', 'name': 'London Gatwick', 'country': 'United Kingdom'},
            'LHR': {'city': 'London', 'name': 'London Heathrow', 'country': 'United Kingdom'},
            'CDG': {'city': 'Paris', 'name': 'Charles de Gaulle', 'country': 'France'},
            'ORY': {'city': 'Paris', 'name': 'Paris Orly', 'country': 'France'},
            'AMS': {'city': 'Amsterdam', 'name': 'Amsterdam Schiphol', 'country': 'Netherlands'},

            # --- Caribbean Airports ---
            'DOM': {'city': 'Dominica', 'name': 'Douglas-Charles', 'country': 'Dominica'},
            'DCF': {'city': 'Dominica', 'name': 'Canefield', 'country': 'Dominica'},
            'SJU': {'city': 'San Juan', 'name': 'Luis Muñoz Marín', 'country': 'Puerto Rico'},
            'BGI': {'city': 'Bridgetown', 'name': 'Grantley Adams', 'country': 'Barbados'},
            'ANU': {'city': 'St. John\'s', 'name': 'V.C. Bird', 'country': 'Antigua'},
            'PTP': {'city': 'Pointe-à-Pitre', 'name': 'Pointe-à-Pitre Intl', 'country': 'Guadeloupe'},
            'FDF': {'city': 'Fort-de-France', 'name': 'Martinique Aimé Césaire', 'country': 'Martinique'},
            'SLU': {'city': 'Castries', 'name': 'George F. L. Charles', 'country': 'St. Lucia'},
            'UVF': {'city': 'Vieux Fort', 'name': 'Hewanorra', 'country': 'St. Lucia'},
            'SXM': {'city': 'St. Maarten', 'name': 'Princess Juliana', 'country': 'Sint Maarten'},
            'SFG': {'city': 'St. Martin', 'name': 'Grand Case-Espérance', 'country': 'Saint Martin'},
            'EIS': {'city': 'Tortola', 'name': 'Terrance B. Lettsome', 'country': 'BVI'},
            'POS': {'city': 'Port of Spain', 'name': 'Piarco', 'country': 'Trinidad'},
            'PUJ': {'city': 'Punta Cana', 'name': 'Punta Cana Intl', 'country': 'Dominican Republic'},
            'SDQ': {'city': 'Santo Domingo', 'name': 'Las Américas', 'country': 'Dominican Republic'},
            'SKB': {'city': 'St. Kitts', 'name': 'Robert L. Bradshaw', 'country': 'St. Kitts and Nevis'},
            'STT': {'city': 'St. Thomas', 'name': 'Cyril E. King', 'country': 'U.S. Virgin Islands'},
            'SVD': {'city': 'Kingstown', 'name': 'Argyle Intl', 'country': 'St. Vincent and the Grenadines'},

            # --- Caribbean Ferry Terminals ---
            'DMROS': {'city': 'Roseau', 'name': 'Roseau Ferry Terminal', 'country': 'Dominica'},
            'GPPTP': {'city': 'Pointe à Pitre', 'name': 'Bergevin Ferry Terminal', 'country': 'Guadeloupe'},
            'MQFDF': {'city': 'Fort de France', 'name': 'Fort de France Terminal', 'country': 'Martinique'},
            'LCCAS': {'city': 'Castries', 'name': 'Castries Ferry Terminal', 'country': 'St. Lucia'},
        }

        # Parent/Child Relationships (Smart Linking)
        # Links Ferry Terminals/Small Airports to the Main Island Code
        relationships = {
            'UVF': 'SLU',   # Hewanorra -> Castries (St. Lucia)
            'LCCAS': 'SLU',  # Castries Ferry -> Castries (St. Lucia)

            'DCF': 'DOM',   # Canefield -> Douglas-Charles (Dominica)
            'DMROS': 'DOM',  # Roseau Ferry -> Douglas-Charles (Dominica)

            'GPPTP': 'PTP',  # Bergevin Ferry -> PTP Airport (Guadeloupe)
            'MQFDF': 'FDF',  # FDF Ferry -> FDF Airport (Martinique)

            'SFG': 'SXM',
            'ORY': 'CDG',
            'LGW': 'LHR',
            'EWR': 'JFK',
        }

        self.stdout.write("🌍 Enriching Location Data...")

        # 1. Update Metadata
        for code, details in data.items():
            updated_count = Location.objects.filter(code=code).update(
                city=details['city'],
                name=details['name'],
                country=details['country']
            )
            if updated_count > 0:
                logger.info(f"Updated Metadata: {code} -> {details['city']}")
            else:
                logger.debug(f"Skipped {code} (Not found in DB)")

        # 2. Establish Relationships
        for child_code, parent_code in relationships.items():
            try:
                parent = Location.objects.filter(code=parent_code).first()
                child = Location.objects.filter(code=child_code).first()

                if parent and child:
                    child.parent = parent
                    child.save()
                    logger.info(
                        f"Linked {child_code} -> Parent: {parent_code}")
            except Exception as e:
                logger.error(
                    f"Failed to link {child_code} to {parent_code}: {e}")

        self.stdout.write(self.style.SUCCESS("✅ Locations Enriched"))
