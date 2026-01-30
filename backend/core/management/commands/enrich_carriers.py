from django.core.management.base import BaseCommand
from core.models import Carrier


class Command(BaseCommand):
    help = 'Updates airline codes with User-Preferred Names and Official Websites'

    def handle(self, *args, **kwargs):
        # 1. The Raw Data (Code -> {Name, URL})
        # We use YOUR preferred names, but we add the official URLs.
        data = {
            # --- Regional Carriers ---
            'S6': {'name': 'Sunrise Airways', 'url': 'https://www.sunriseairways.net'},
            'BW': {'name': 'Caribbean Airlines', 'url': 'https://www.caribbean-airlines.com'},
            'JY': {'name': 'interCaribbean Airways', 'url': 'https://www.intercaribbean.com'},
            # Updated to Liat 2020 site
            '5L': {'name': 'Liat', 'url': 'https://www.flyliat20.com'},
            '3S': {'name': 'Air Antilles', 'url': 'https://www.airantilles.com'},
            'TX': {'name': 'Air Caraïbes', 'url': 'https://www.aircaraibes.com'},
            'WM': {'name': 'Winair', 'url': 'https://www.winair.sx'},
            'LF': {'name': 'Contour Airlines', 'url': 'https://www.contourairlines.com'},

            # --- US/Canada Carriers ---
            'AA': {'name': 'American Airlines', 'url': 'https://www.aa.com'},
            'B6': {'name': 'JetBlue', 'url': 'https://www.jetblue.com'},
            'DL': {'name': 'Delta Air Lines', 'url': 'https://www.delta.com'},
            'UA': {'name': 'United Airlines', 'url': 'https://www.united.com'},
            'AC': {'name': 'Air Canada', 'url': 'https://www.aircanada.com'},
            'WS': {'name': 'WestJet', 'url': 'https://www.westjet.com'},
            'TS': {'name': 'Air Transat', 'url': 'https://www.airtransat.com'},
            'F9': {'name': 'Frontier Airlines', 'url': 'https://www.flyfrontier.com'},
            'NK': {'name': 'Spirit Airlines', 'url': 'https://www.spirit.com'},

            # --- European Carriers ---
            'BA': {'name': 'British Airways', 'url': 'https://www.britishairways.com'},
            'VS': {'name': 'Virgin Atlantic', 'url': 'https://www.virginatlantic.com'},
            'AF': {'name': 'Air France', 'url': 'https://www.airfrance.com'},
            'KL': {'name': 'KLM Royal Dutch Airlines', 'url': 'https://www.klm.com'},
            'DE': {'name': 'Condor', 'url': 'https://www.condor.com'},
            'LH': {'name': 'Lufthansa', 'url': 'https://www.lufthansa.com'},
            'E9': {'name': 'Eurowings', 'url': 'https://www.eurowings.com'},
            'SS': {'name': 'Corsair', 'url': 'https://www.flycorsair.com'},
            'Q4': {'name': 'Euroairlines', 'url': 'https://www.euroairlines.es'},
        }

        self.stdout.write("✈️  Enriching Carrier Data & Websites...")

        count = 0
        for code, info in data.items():
            # Update name AND website
            # We use 'update' so we don't accidentally create duplicates if the code exists
            rows = Carrier.objects.filter(code=code).update(
                name=info['name'],
                website=info['url']
            )

            # If the carrier doesn't exist yet (e.g. we haven't scraped a flight for it),
            # we CREATE it so it's ready for future flights.
            if rows == 0:
                Carrier.objects.create(
                    code=code,
                    name=info['name'],
                    website=info['url'],
                    carrier_type='AIR'
                )
                self.stdout.write(self.style.SUCCESS(
                    f"   ✨ Created {code}: {info['name']}"))
            else:
                self.stdout.write(self.style.SUCCESS(
                    f"   ✅ Updated {code}: {info['name']}"))
                count += 1

        self.stdout.write(f"\nDone! Enriched {len(data)} carriers.")
