from django.core.management.base import BaseCommand
from core.models import Location


class Command(BaseCommand):
    help = 'Updates airport metadata with real City and Name values'

    def handle(self, *args, **kwargs):
        # A dictionary of common Caribbean/Hub codes
        # We act as the "Source of Truth" here
        data = {
            # Major US/Canada Hubs
            'MIA': {'city': 'Miami', 'name': 'Miami International', 'country': 'USA'},
            'JFK': {'city': 'New York', 'name': 'John F. Kennedy', 'country': 'USA'},
            'EWR': {'city': 'Newark', 'name': 'Newark Liberty Intl', 'country': 'USA'},
            'ATL': {'city': 'Atlanta', 'name': 'Hartsfield-Jackson Atlanta Intl', 'country': 'USA'},
            'YYZ': {'city': 'Toronto', 'name': 'Toronto Pearson Intl', 'country': 'Canada'},
            'CLT': {'city': 'Charlotte', 'name': 'Charlotte Douglas Intl', 'country': 'USA'},
            'IAH': {'city': 'Houston', 'name': 'George Bush Intercontinental', 'country': 'USA'},
            'YUL': {'city': 'Montreal', 'name': 'Montréal-Pierre Elliott Trudeau Intl', 'country': 'Canada'},
            'FLL': {'city': 'Fort Lauderdale', 'name': 'Fort Lauderdale-Hollywood Intl', 'country': 'USA'},

            # Major Europe Hubs
            'FRA': {'city': 'Frankfurt', 'name': 'Frankfurt am Main', 'country': 'Germany'},
            'LGW': {'city': 'London', 'name': 'London Gatwick', 'country': 'United Kingdom'},
            'LHR': {'city': 'London', 'name': 'London Heathrow', 'country': 'United Kingdom'},
            'CDG': {'city': 'Paris', 'name': 'Charles de Gaulle', 'country': 'France'},
            'ORY': {'city': 'Paris', 'name': 'Paris Orly', 'country': 'France'},
            'AMS': {'city': 'Amsterdam', 'name': 'Amsterdam Schiphol', 'country': 'Netherlands'},


            # Caribbean
            'DOM': {'city': 'Dominica', 'name': 'Douglas-Charles', 'country': 'Dominica'},
            'SJU': {'city': 'San Juan', 'name': 'Luis Muñoz Marín', 'country': 'Puerto Rico'},
            'BGI': {'city': 'Bridgetown', 'name': 'Grantley Adams', 'country': 'Barbados'},
            'ANU': {'city': 'St. John\'s', 'name': 'V.C. Bird', 'country': 'Antigua'},
            'PTP': {'city': 'Pointe-à-Pitre', 'name': 'Pointe-à-Pitre Intl', 'country': 'Guadeloupe'},
            'FDF': {'city': 'Fort-de-France', 'name': 'Martinique Aimé Césaire', 'country': 'Martinique'},
            'SLU': {'city': 'Castries', 'name': 'George F. L. Charles', 'country': 'St. Lucia'},
            'UVF': {'city': 'Vieux Fort', 'name': 'Hewanorra', 'country': 'St. Lucia'},
            'SXM': {'city': 'St. Maarten', 'name': 'Princess Juliana', 'country': 'Sint Maarten'},
            'EIS': {'city': 'Tortola', 'name': 'Terrance B. Lettsome', 'country': 'BVI'},
            'POS': {'city': 'Port of Spain', 'name': 'Piarco', 'country': 'Trinidad'},
            'PUJ': {'city': 'Punta Cana', 'name': 'Punta Cana Intl', 'country': 'Dominican Republic'},
            'SKB': {'city': 'St. Kitts', 'name': 'Robert L. Bradshaw', 'country': 'St. Kitts and Nevis'},
            'STT': {'city': 'St. Thomas', 'name': 'Cyril E. King', 'country': 'U.S. Virgin Islands'},
            'SVD': {'city': 'Kingstown', 'name': 'Argyle Intl', 'country': 'St. Vincent and the Grenadines'},

        }

        self.stdout.write("🌍 Enriching Location Data...")

        for code, details in data.items():
            # We use update() to fix existing records without creating duplicates
            updated_count = Location.objects.filter(code=code).update(
                city=details['city'],
                name=details['name'],
                country=details['country']
            )

            if updated_count > 0:
                self.stdout.write(self.style.SUCCESS(
                    f"   ✅ Updated {code} -> {details['city']}"))
            else:
                # Optional: Create it if it doesn't exist?
                # For now, we only polish what we have.
                self.stdout.write(f"   ⚠️  Skipped {code} (Not in DB yet)")
