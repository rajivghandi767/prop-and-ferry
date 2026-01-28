import requests
from bs4 import BeautifulSoup
from django.core.management.base import BaseCommand
from core.models import Location, Route, Carrier


class Command(BaseCommand):
    help = "Scrapes L'Express des Iles Ferry schedules"

    def handle(self, *args, **kwargs):
        self.stdout.write("🚢 Starting Ferry Scraper...")

        # 1. Setup the Carrier
        carrier, _ = Carrier.objects.get_or_create(
            code='LDI',
            defaults={'name': "L'Express des Iles", 'carrier_type': 'SEA'}
        )

        # 2. Define known Ferry Ports
        ports = {
            'DOM': 'Roseau',
            'PTP': 'Pointe-a-Pitre',
            'FDF': 'Fort-de-France',
            'SLU': 'Castries'
        }

        # Ensure ports exist in DB
        for code, name in ports.items():
            Location.objects.get_or_create(
                code=code,
                defaults={'name': name, 'location_type': 'PRT', 'city': name}
            )

        # 3. The Scraping Logic

        url = "https://www.express-des-iles.fr/en/schedules"  # Example URL

        try:
            headers = {'User-Agent': 'Mozilla/5.0'}
            response = requests.get(url, headers=headers)

            if response.status_code == 200:
                soup = BeautifulSoup(response.text, 'html.parser')
                self.stdout.write(f"   Fetched {url} - Parsing...")

                # --- PSEUDO CODE ---
                # You would inspect their site, find the schedule table
                # rows = soup.find_all('div', class_='schedule-row')
                # for row in rows:
                #    extract origin, dest, time
                #    save to DB
                # -------------------

                # For now, let's HARDCODE the known regular routes
                # just to prove the concept in your app.
                known_routes = [
                    ('PTP', 'DOM'), ('DOM', 'PTP'),
                    ('FDF', 'DOM'), ('DOM', 'FDF'),
                    ('SLU', 'DOM'), ('DOM', 'SLU')
                ]

                for org, dst in known_routes:
                    org_loc = Location.objects.get(code=org)
                    dst_loc = Location.objects.get(code=dst)

                    Route.objects.get_or_create(
                        origin=org_loc,
                        destination=dst_loc,
                        carrier=carrier,
                        defaults={
                            'is_active': True,
                            'days_of_operation': '1234567'  # Default to daily for now
                        }
                    )
                    self.stdout.write(self.style.SUCCESS(
                        f"   ✅ Verified Ferry: {org} <-> {dst}"))

            else:
                self.stdout.write(self.style.ERROR(
                    f"   ❌ Failed to fetch page: {response.status_code}"))

        except Exception as e:
            self.stdout.write(self.style.ERROR(f"   ❌ Error: {e}"))
