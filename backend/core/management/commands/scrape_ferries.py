import time
import requests
from bs4 import BeautifulSoup
from datetime import datetime, timedelta
from django.core.management.base import BaseCommand
from core.models import Location, Route, Carrier, Sailing
from core.constants import (
    PORT_ROSEAU, PORT_PTP, PORT_FDF, PORT_CASTRIES,
    DB_TO_SITE_OPTS
)


class Command(BaseCommand):
    help = "Saves EXACT DATE Sailings to DB"

    def handle(self, *args, **kwargs):
        self.stdout.write("🚢 Initializing Date-Specific Scraper...")

        base_routes = [
            (PORT_PTP, PORT_ROSEAU), (PORT_FDF,
                                      PORT_ROSEAU), (PORT_CASTRIES, PORT_ROSEAU),
        ]
        final_routes = []
        for start, end in base_routes:
            final_routes.append((start, end))
            final_routes.append((end, start))

        BASE_URL = "https://goexpress-b2c.frs-express.com/B2C_2018/"
        session = requests.Session()
        session.headers.update({
            'User-Agent': 'Chrome/91.0',
            'Referer': 'https://www.express-des-iles.fr/',
            'Accept-Language': 'fr-FR,fr;q=0.9'
        })

        carrier, _ = Carrier.objects.get_or_create(
            code="LXI", defaults={'name': "L'Express des Iles", 'carrier_type': 'SEA', 'website': 'https://www.frs-express.com'}
        )

        # Scrape 3 weeks out
        check_intervals = [0, 7, 14]
        start_date_base = datetime.now().date()

        for origin_code, dest_code in final_routes:
            self.stdout.write(self.style.WARNING(
                f"\n--- Checking {origin_code} -> {dest_code} ---"))

            for days_offset in check_intervals:
                check_date = start_date_base + timedelta(days=days_offset)
                date_str = check_date.strftime('%d/%m/%Y')

                site_origin = DB_TO_SITE_OPTS[origin_code][0]
                site_dest = DB_TO_SITE_OPTS[dest_code][0]

                params = {
                    'aller': 'AS', 'depart': site_origin, 'arrivee': site_dest,
                    'date_aller': date_str, 'adultes': '1', 'enfants': '0'
                }

                try:
                    resp = session.get(BASE_URL, params=params, timeout=20)
                    resp.encoding = 'utf-8'
                    if resp.status_code != 200:
                        continue

                    soup = BeautifulSoup(resp.content, 'html.parser')

                    # Find buttons with "à partir de"
                    all_buttons = soup.find_all("button")
                    calendar_buttons = [
                        b for b in all_buttons if "à partir de" in b.get_text()]

                    if not calendar_buttons:
                        continue

                    # Ensure Base Route Exists
                    loc_origin = Location.objects.get(code=origin_code)
                    loc_dest = Location.objects.get(code=dest_code)
                    route, _ = Route.objects.get_or_create(
                        origin=loc_origin, destination=loc_dest, carrier=carrier,
                        defaults={'is_active': True}
                    )

                    for btn in calendar_buttons:
                        p_tags = btn.find_all("p")
                        if len(p_tags) < 3:
                            continue

                        date_text = p_tags[0].get_text(
                            strip=True)  # "Lun. 02 Fév."
                        price_text = p_tags[2].get_text(strip=True)

                        if "-" in price_text and not any(c.isdigit() for c in price_text):
                            continue  # No sailing

                        parsed_date = self.parse_french_date(date_text)
                        if not parsed_date:
                            continue

                        # SAVE SAILING (Specific Date)
                        # We use default times (08:00) for calendar scrape.
                        # Deep scrape (clicking button) would update this.
                        sailing, created = Sailing.objects.update_or_create(
                            route=route,
                            date=parsed_date,
                            defaults={
                                'departure_time': "08:00",
                                'arrival_time': "10:00",
                                'duration_minutes': 120,
                                'price_text': price_text
                            }
                        )

                        if created:
                            self.stdout.write(self.style.SUCCESS(
                                f"   ✅ Added Sailing: {parsed_date}"))
                        else:
                            self.stdout.write(f"   (Confirmed: {parsed_date})")

                    time.sleep(1)

                except Exception as e:
                    self.stdout.write(self.style.ERROR(f"   Error: {e}"))

        self.stdout.write(self.style.SUCCESS("\n✨ Scrape Complete"))

    def parse_french_date(self, date_str):
        MONTHS = {'jan': 1, 'fév': 2, 'fev': 2, 'mar': 3, 'avr': 4, 'mai': 5, 'juin': 6,
                  'juil': 7, 'aoû': 8, 'aou': 8, 'sep': 9, 'oct': 10, 'nov': 11, 'déc': 12, 'dec': 12}
        try:
            parts = date_str.replace('.', '').split()
            if len(parts) < 3:
                return None
            day = int(parts[1])
            month = MONTHS.get(parts[2].lower()[0:3], 1)
            year = datetime.now().year
            if month < datetime.now().month - 2:
                year += 1
            return datetime(year, month, day).date()
        except:
            return None
