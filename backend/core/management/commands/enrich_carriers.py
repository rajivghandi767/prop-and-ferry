import logging
from django.core.management.base import BaseCommand
from core.models import Carrier

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = 'Updates airline codes with User-Preferred Names and Official Websites'

    def handle(self, *args, **kwargs):
        data = {
            # --- Regional / Caribbean Carriers ---
            'S6': {'name': 'Sunrise Airways', 'url': 'https://www.sunriseairways.net'},
            'BW': {'name': 'Caribbean Airlines', 'url': 'https://www.caribbean-airlines.com'},
            'JY': {'name': 'interCaribbean Airways', 'url': 'https://www.intercaribbean.com'},
            '5L': {'name': 'Liat 2020', 'url': 'https://www.flyliat20.com'},
            '3S': {'name': 'Air Antilles', 'url': 'https://www.airantilles.com'},
            'TX': {'name': 'Air Caraïbes', 'url': 'https://www.aircaraibes.com'},
            'WM': {'name': 'Winair', 'url': 'https://www.winair.sx'},
            'LF': {'name': 'Contour Airlines', 'url': 'https://www.contourairlines.com'},

            # --- US Carriers ---
            'AA': {'name': 'American Airlines', 'url': 'https://www.aa.com'},
            'B6': {'name': 'JetBlue', 'url': 'https://www.jetblue.com'},
            'DL': {'name': 'Delta Air Lines', 'url': 'https://www.delta.com'},
            'UA': {'name': 'United Airlines', 'url': 'https://www.united.com'},
            'F9': {'name': 'Frontier Airlines', 'url': 'https://www.flyfrontier.com'},
            'NK': {'name': 'Spirit Airlines', 'url': 'https://www.spirit.com'},

            # --- Canada Carriers ---
            'AC': {'name': 'Air Canada', 'url': 'https://www.aircanada.com'},
            'WS': {'name': 'WestJet', 'url': 'https://www.westjet.com'},
            'TS': {'name': 'Air Transat', 'url': 'https://www.airtransat.com'},

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

        self.stdout.write("✈️  Enriching Carrier Data...")

        updated_count = 0
        created_count = 0

        for code, info in data.items():
            obj, created = Carrier.objects.update_or_create(
                code=code,
                defaults={
                    'name': info['name'],
                    'website': info['url'],
                    'carrier_type': 'AIR'
                }
            )

            if created:
                created_count += 1
                logger.info(f"Created Carrier: {code}")
            else:
                updated_count += 1

        logger.info(
            f"Carrier Enrichment: {created_count} Created, {updated_count} Updated")
        self.stdout.write(self.style.SUCCESS(
            f"✅ Enriched {len(data)} carriers."))
