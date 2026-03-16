import time
import logging
import requests
import re
from bs4 import BeautifulSoup
from datetime import datetime, timedelta
from django.core.management.base import BaseCommand
from core.models import Location, Route, Carrier, Sailing
from core.constants import PORT_ROSEAU, PORT_PTP, PORT_FDF, PORT_CASTRIES, DB_TO_SITE_OPTS

logger = logging.getLogger(__name__)

FRENCH_MONTHS = {
    'jan': 1, 'fév': 2, 'fev': 2, 'mar': 3, 'avr': 4, 'mai': 5, 'juin': 6,
    'juil': 7, 'aoû': 8, 'aou': 8, 'sep': 9, 'oct': 10, 'nov': 11, 'déc': 12, 'dec': 12
}


class Command(BaseCommand):
    help = "FRS - Express Ferry Schedule Scraper: Extracts Exact Times, Durations & Prices"

    def handle(self, *args, **kwargs):
        self.stdout.write(
            "🚢 Initializing FRS-Express Ferry Schedule Scraper...")

        # DB BLOAT PROTECTION: Wipe future sailings for fresh replacement
        today = datetime.now().date()
        deleted_count, _ = Sailing.objects.filter(date__gte=today).delete()
        self.stdout.write(
            f"🗑️ Cleared {deleted_count} upcoming sailings for fresh data update.")

        base_routes = [(PORT_PTP, PORT_ROSEAU), (PORT_FDF,
                                                 PORT_ROSEAU), (PORT_CASTRIES, PORT_ROSEAU)]
        final_routes = []
        for start, end in base_routes:
            final_routes.append((start, end))
            final_routes.append((end, start))

        BASE_URL = "https://goexpress-b2c.frs-express.com/B2C_2018/"
        session = requests.Session()
        session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36',
            'Referer': 'https://www.frs-express.com/',
            'Accept-Language': 'fr-FR,fr;q=0.9,en-US;q=0.8,en;q=0.7'
        })

        carrier, _ = Carrier.objects.get_or_create(
            code="LXI",
            defaults={'name': "L'Express des Iles", 'carrier_type': 'SEA',
                      'website': 'https://www.frs-express.com'}
        )

        check_intervals = [0, 7, 14]
        start_date_base = today

        for origin_code, dest_code in final_routes:
            logger.info(f"Checking Route: {origin_code} -> {dest_code}")
            try:
                loc_origin = Location.objects.get(code=origin_code)
                loc_dest = Location.objects.get(code=dest_code)
                route_obj, _ = Route.objects.get_or_create(
                    origin=loc_origin, destination=loc_dest, carrier=carrier, defaults={
                        'is_active': True}
                )
            except Location.DoesNotExist:
                continue

            processed_dates = set()

            for days_offset in check_intervals:
                check_date = start_date_base + timedelta(days=days_offset)
                date_str = check_date.strftime('%d/%m/%Y')
                params = {
                    'aller': 'AS', 'depart': DB_TO_SITE_OPTS[origin_code][0],
                    'arrivee': DB_TO_SITE_OPTS[dest_code][0],
                    'date_aller': date_str, 'adultes': '1', 'enfants': '0'
                }

                try:
                    resp = session.get(BASE_URL, params=params, timeout=20)
                    resp.encoding = 'utf-8'
                    if resp.status_code != 200:
                        continue
                    soup = BeautifulSoup(resp.content, 'html.parser')

                    valid_dates_in_week = []
                    for btn in soup.find_all("button"):
                        if "à partir de" in btn.get_text():
                            p_tags = btn.find_all("p")
                            if len(p_tags) >= 3:
                                parsed_date = self.parse_french_date(
                                    p_tags[0].get_text(strip=True))
                                price_text = p_tags[2].get_text(strip=True)
                                if parsed_date and any(c.isdigit() for c in price_text):
                                    valid_dates_in_week.append(
                                        (parsed_date, price_text))

                    for target_date, day_price in valid_dates_in_week:
                        if target_date in processed_dates:
                            continue

                        is_current_page = False
                        header_div = soup.find(text=re.compile("DATE DEPART"))
                        if header_div and self.parse_french_date(header_div) == target_date:
                            is_current_page = True

                        target_soup = soup
                        if not is_current_page:
                            sub_params = params.copy()
                            sub_params['date_aller'] = target_date.strftime(
                                '%d/%m/%Y')
                            sub_resp = session.get(
                                BASE_URL, params=sub_params, timeout=20)
                            sub_resp.encoding = 'utf-8'
                            target_soup = BeautifulSoup(
                                sub_resp.content, 'html.parser')

                        self.parse_daily_schedule(
                            target_soup, route_obj, target_date, day_price)
                        processed_dates.add(target_date)
                        time.sleep(1)

                except Exception as e:
                    logger.error(f"Scrape Error: {e}")

        self.stdout.write(self.style.SUCCESS("✨ Ferry scraping complete!"))

    def parse_daily_schedule(self, soup, route_obj, date_obj, price_text):
        try:
            duration_nodes = soup.find_all(text=re.compile("Durée du voyage"))
            if not duration_nodes:
                self.fallback_parse_times(
                    soup, route_obj, date_obj, price_text)
                return

            for dur_node in duration_nodes:
                container = dur_node.parent
                times = []
                depth = 0
                while depth < 8 and container:
                    times = container.find_all('time')
                    if len(times) >= 2:
                        break
                    container = container.parent
                    depth += 1

                if len(times) >= 2:
                    dep_time = times[0].get_text(strip=True)
                    arr_time = times[1].get_text(strip=True)
                    duration_mins = 120
                    if match := re.search(r'(\d+)h(\d+)', dur_node.strip()):
                        duration_mins = (int(match.group(1))
                                         * 60) + int(match.group(2))

                    Sailing.objects.update_or_create(
                        route=route_obj, date=date_obj, departure_time=dep_time,
                        defaults={
                            'arrival_time': arr_time, 'duration_minutes': duration_mins, 'price_text': price_text}
                    )
        except Exception as e:
            logger.error(f"Parse Error on {date_obj}: {e}")

    def fallback_parse_times(self, soup, route_obj, date_obj, price_text):
        times = soup.find_all('time')
        for i in range(0, len(times), 2):
            if i + 1 < len(times):
                Sailing.objects.update_or_create(
                    route=route_obj, date=date_obj, departure_time=times[i].get_text(
                        strip=True),
                    defaults={'arrival_time': times[i+1].get_text(
                        strip=True), 'duration_minutes': 120, 'price_text': price_text}
                )

    def parse_french_date(self, date_str):
        if not date_str:
            return None
        try:
            parts = date_str.lower().replace('.', '').replace(
                ':', '').replace('date depart', '').strip().split()
            day, month_idx = next(
                ((int(p), i+1) for i, p in enumerate(parts) if p.isdigit()), (None, -1))
            if not day or month_idx >= len(parts):
                return None

            month = FRENCH_MONTHS.get(parts[month_idx][0:3], 1)
            today = datetime.now().date()
            year = today.year + 1 if month < today.month - 2 else today.year
            return datetime(year, month, day).date()
        except:
            return None
