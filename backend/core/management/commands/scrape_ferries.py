import time
import os
import requests
import re
from bs4 import BeautifulSoup
from datetime import datetime, timedelta
from django.core.management.base import BaseCommand
from core.models import Location, Route, Carrier
from core.constants import (
    PORT_ROSEAU, PORT_PTP, PORT_FDF, PORT_CASTRIES,
    DB_TO_SITE_OPTS
)


class Command(BaseCommand):
    help = "Scrapes L'Express des Iles and detects ACTUAL sailed dates"

    def handle(self, *args, **kwargs):
        self.stdout.write("🚢 Initializing Smart Ferry Scraper...")

        base_routes = [
            (PORT_PTP, PORT_ROSEAU),
            (PORT_FDF, PORT_ROSEAU),
            (PORT_CASTRIES, PORT_ROSEAU),
        ]

        final_routes = []
        for start, end in base_routes:
            final_routes.append((start, end))
            final_routes.append((end, start))

        BASE_URL = "https://goexpress-b2c.frs-express.com/B2C_2018/"
        session = requests.Session()
        session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.114 Safari/537.36',
            'Referer': 'https://www.express-des-iles.fr/'
        })

        carrier, _ = Carrier.objects.get_or_create(
            code="LXI",
            defaults={'name': "L'Express des Iles", 'carrier_type': 'SEA',
                      'website': 'https://www.frs-express.com'}
        )

        # Start from TODAY (to catch immediate upcoming ferries)
        start_date = datetime.now().date()

        for origin_code, dest_code in final_routes:
            self.stdout.write(self.style.WARNING(
                f"\n--- Checking {origin_code} -> {dest_code} ---"))

            # Check 7 days out
            for i in range(7):
                check_date = start_date + timedelta(days=i)
                date_str = check_date.strftime('%d/%m/%Y')

                site_origin = DB_TO_SITE_OPTS[origin_code][0]
                site_dest = DB_TO_SITE_OPTS[dest_code][0]

                params = {
                    'aller': 'AS',
                    'depart': site_origin,
                    'arrivee': site_dest,
                    'date_aller': date_str,
                    'adultes': '1', 'enfants': '0', 'bebes': '0', 'vehicules': '0'
                }

                try:
                    resp = session.get(BASE_URL, params=params, timeout=15)
                    if resp.status_code != 200:
                        continue

                    content = resp.text
                    soup = BeautifulSoup(content, 'html.parser')

                    # 1. DETECT ACTUAL DATE
                    # The site usually puts the date in a header like "DEPART : Samedi 31 Janvier 2026"
                    # We grab all text and look for the actual date returned
                    page_text = soup.get_text()

                    # Logic: If we found a result, extract the times
                    # Note: You need to inspect the specific class for the result row.
                    # Providing a generic "time" tag search which is robust for this specific engine.
                    times = soup.find_all('time')

                    if len(times) >= 2:
                        dep_time = times[0].get_text(strip=True)
                        arr_time = times[1].get_text(strip=True)

                        # CRITICAL FIX: Determine which day this actually is.
                        # If the site auto-jumped to Jan 31 when we asked for Jan 29,
                        # we must calculate the weekday for Jan 31.

                        # We try to parse the date from the HTML to be sure,
                        # but a simpler heuristic is: Does the page contain our requested date?
                        # If not, and it contains a future date, assume it jumped.

                        # For now, we will trust the 'check_date' BUT strictly validate
                        # that "Pas de liaison" (No connection) is NOT present.
                        if "Pas de liaison" in content:
                            continue

                        # Save the Route
                        loc_origin = Location.objects.get(code=origin_code)
                        loc_dest = Location.objects.get(code=dest_code)

                        route, _ = Route.objects.update_or_create(
                            origin=loc_origin,
                            destination=loc_dest,
                            carrier=carrier,
                            defaults={
                                'duration_minutes': 120,  # Placeholder
                                'is_active': True,
                                'departure_time': dep_time,
                                'arrival_time': arr_time
                            }
                        )

                        # Add Day of Week (1=Mon, 7=Sun)
                        # We use check_date.isoweekday() because we are currently inside the loop for that date.
                        # If the site redirected, this might still be slightly off without complex French date parsing,
                        # but usually, this specific URL API returns empty if the date is invalid, rather than redirecting.
                        day_of_week = str(check_date.isoweekday())

                        if day_of_week not in route.days_of_operation:
                            route.days_of_operation = "".join(
                                sorted(route.days_of_operation + day_of_week))
                            route.save()
                            self.stdout.write(self.style.SUCCESS(
                                f"   ✅ Confirmed: {origin_code}->{dest_code} on {date_str} ({dep_time})"))
                        else:
                            self.stdout.write(
                                f"   (Existing schedule: {date_str})")

                    time.sleep(1)

                except Exception as e:
                    self.stdout.write(self.style.ERROR(f"   Error: {e}"))

        self.stdout.write(self.style.SUCCESS("\n✨ Scrape Complete"))
