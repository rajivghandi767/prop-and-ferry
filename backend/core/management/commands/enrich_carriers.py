import logging
from django.core.management.base import BaseCommand
from core.models import Carrier

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = 'Updates airline codes with User-Preferred Names and Official Websites'

    def handle(self, *args, **kwargs):
        self.stdout.write("✈️  Enriching Carrier Data...")

        carrier_data = [
            ('S6', 'Sunrise Airways', 'AIR', 'https://www.sunriseairways.net'),
            ('BW', 'Caribbean Airlines', 'AIR',
             'https://www.caribbean-airlines.com'),
            ('JY', 'interCaribbean Airways', 'AIR',
             'https://www.intercaribbean.com'),
            ('5L', 'Liat 2020', 'AIR', 'https://www.flyliat20.com'),
            ('3S', 'Air Antilles', 'AIR', 'https://www.airantilles.com'),
            ('TX', 'Air Caraïbes', 'AIR', 'https://www.aircaraibes.com'),
            ('WM', 'Winair', 'AIR', 'https://www.winair.sx'),
            ('LF', 'Contour Airlines', 'AIR', 'https://www.contourairlines.com'),
            ('AA', 'American Airlines', 'AIR', 'https://www.aa.com'),
            ('B6', 'JetBlue', 'AIR', 'https://www.jetblue.com'),
            ('DL', 'Delta Air Lines', 'AIR', 'https://www.delta.com'),
            ('UA', 'United Airlines', 'AIR', 'https://www.united.com'),
            ('AC', 'Air Canada', 'AIR', 'https://www.aircanada.com'),
            ('WS', 'WestJet', 'AIR', 'https://www.westjet.com'),
            ('BA', 'British Airways', 'AIR', 'https://www.britishairways.com'),
            ('VS', 'Virgin Atlantic', 'AIR', 'https://www.virginatlantic.com'),
            ('AF', 'Air France', 'AIR', 'https://www.airfrance.com'),
            ('KL', 'KLM Royal Dutch Airlines', 'AIR', 'https://www.klm.com'),
            ('DE', 'Condor', 'AIR', 'https://www.condor.com'),
            ('LH', 'Lufthansa', 'AIR', 'https://www.lufthansa.com'),
            ('E9', 'Eurowings', 'AIR', 'https://www.eurowings.com'),
            ('SS', 'Corsair', 'AIR', 'https://www.flycorsair.com'),
            ('Q4', 'Euroairlines', 'AIR', 'https://www.euroairlines.es'),
            # Ferry Operator
            ('LXI', "L'Express des Iles", 'SEA',
             'https://www.frs-express.com'),
        ]

        updated_count = 0
        created_count = 0

        for code, name, c_type, url in carrier_data:
            obj, created = Carrier.objects.update_or_create(
                code=code,
                defaults={
                    'name': name,
                    'website': url,
                    'carrier_type': c_type
                }
            )

            if created:
                created_count += 1
                logger.info(f"Created Carrier: {code}")
            else:
                updated_count += 1

        logger.info(f"Updated {updated_count} existing carriers.")
        self.stdout.write(self.style.SUCCESS("✨ Carriers Enriched!"))
