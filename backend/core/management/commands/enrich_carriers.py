from django.core.management.base import BaseCommand
from core.models import Carrier


class Command(BaseCommand):
    help = 'Updates airline codes with real Airline Names'

    def handle(self, *args, **kwargs):
        # The Caribbean & Major Carrier Dictionary
        data = {
            # Regional Carriers
            'S6': 'Sunrise Airways',
            'BW': 'Caribbean Airlines',
            'JY': 'interCaribbean Airways',
            '5L': 'Liat',
            '3S': 'Air Antilles',
            'TX': 'Air Caraïbes',
            'WM': 'Winair',
            'LF': 'Contour Airlines',

            # US/Canada Carriers
            'AA': 'American Airlines',
            'B6': 'JetBlue',
            'DL': 'Delta Air Lines',
            'UA': 'United Airlines',
            'AC': 'Air Canada',
            'WS': 'WestJet',
            'TS': 'Air Transat',
            'F9': 'Frontier Airlines',
            'NK': 'Spirit Airlines',


            # European Carriers
            'BA': 'British Airways',
            'VS': 'Virgin Atlantic',
            'AF': 'Air France',
            'KL': 'KLM Royal Dutch Airlines',
            'DE': 'Condor',
            'LH': 'Lufthansa',
            'E9': 'Eurowings',
            'SS': 'Corsair',
            'Q4': 'Euroairlines',
        }

        self.stdout.write("✈️  Enriching Carrier Data...")

        for code, name in data.items():
            # Update existing carriers found by the scraper
            updated_count = Carrier.objects.filter(code=code).update(name=name)

            if updated_count > 0:
                self.stdout.write(self.style.SUCCESS(
                    f"   ✅ Updated {code} -> {name}"))
            else:
                # Optional: We could create them, but usually we only care
                # if we actually have routes for them.
                self.stdout.write(f"   ⚠️  Skipped {code} (Not in DB yet)")
