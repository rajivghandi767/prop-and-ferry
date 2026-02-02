import time
import logging
import requests
import re
from bs4 import BeautifulSoup
from datetime import datetime, timedelta
from django.core.management.base import BaseCommand
from core.models import Location, Route, Carrier, Sailing
from core.constants import (
    PORT_ROSEAU, PORT_PTP, PORT_FDF, PORT_CASTRIES,
    DB_TO_SITE_OPTS
)

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = "FRS - Express Ferry Schedule Scraper: Extracts Exact Times, Durations & Prices"

    def handle(self, *args, **kwargs):
        self.stdout.write(
            "🚢 Initializing FRS-Express Ferry Schedule Scraper...")

        # 1. SETUP
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
            'Referer': 'https://www.express-des-iles.fr/',
            'Accept-Language': 'fr-FR,fr;q=0.9,en-US;q=0.8,en;q=0.7'
        })

        carrier, _ = Carrier.objects.get_or_create(
            code="LXI", defaults={'name': "L'Express des Iles", 'carrier_type': 'SEA', 'website': 'https://www.frs-express.com'}
        )

        # 2. SCRAPE LOOP (Check 3 weeks out)
        check_intervals = [0, 7, 14]
        start_date_base = datetime.now().date()

        for origin_code, dest_code in final_routes:
            logger.info(f"Checking Route: {origin_code} -> {dest_code}")

            try:
                # Identify the base Route object
                loc_origin = Location.objects.get(code=origin_code)
                loc_dest = Location.objects.get(code=dest_code)
                route_obj, _ = Route.objects.get_or_create(
                    origin=loc_origin, destination=loc_dest, carrier=carrier,
                    defaults={'is_active': True}
                )
            except Location.DoesNotExist:
                logger.error(
                    f"Skipping {origin_code}->{dest_code}: Location not found in DB")
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
                        logger.warning(
                            f"HTTP {resp.status_code} for {origin_code}->{dest_code}")
                        continue

                    soup = BeautifulSoup(resp.content, 'html.parser')

                    # STEP A: READ CALENDAR BUTTONS TO FIND VALID DATES & PRICES
                    valid_dates_in_week = []
                    all_buttons = soup.find_all("button")

                    for btn in all_buttons:
                        if "à partir de" in btn.get_text():
                            p_tags = btn.find_all("p")
                            if len(p_tags) >= 3:
                                date_text = p_tags[0].get_text(
                                    strip=True)  # e.g. "Lun. 02 Fév."
                                price_text = p_tags[2].get_text(
                                    strip=True)  # e.g. "39,00 €"

                                if any(c.isdigit() for c in price_text):
                                    parsed_date = self.parse_french_date(
                                        date_text)
                                    if parsed_date:
                                        valid_dates_in_week.append(
                                            (parsed_date, price_text))

                    if not valid_dates_in_week:
                        continue

                    # STEP B: FETCH DETAILS FOR EACH VALID DATE
                    for target_date, day_price in valid_dates_in_week:
                        if target_date in processed_dates:
                            continue

                        is_current_page = False
                        header_div = soup.find(text=re.compile("DATE DEPART"))
                        if header_div:
                            header_date = self.parse_french_date(header_div)
                            if header_date == target_date:
                                is_current_page = True

                        if is_current_page:
                            self.parse_daily_schedule(
                                soup, route_obj, target_date, day_price)
                        else:
                            sub_params = params.copy()
                            sub_params['date_aller'] = target_date.strftime(
                                '%d/%m/%Y')

                            sub_resp = session.get(
                                BASE_URL, params=sub_params, timeout=20)
                            sub_resp.encoding = 'utf-8'
                            sub_soup = BeautifulSoup(
                                sub_resp.content, 'html.parser')
                            self.parse_daily_schedule(
                                sub_soup, route_obj, target_date, day_price)

                        processed_dates.add(target_date)
                        time.sleep(1)

                except Exception as e:
                    logger.error(
                        f"Scrape Error {origin_code}->{dest_code}: {e}")

        self.stdout.write(self.style.SUCCESS("\n✨ Scrape Complete"))

    def parse_daily_schedule(self, soup, route_obj, date_obj, price_text="Available"):
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

                while depth < 8:
                    if not container:
                        break
                    times = container.find_all('time')
                    if len(times) >= 2:
                        break
                    container = container.parent
                    depth += 1

                if len(times) >= 2:
                    dep_time = times[0].get_text(strip=True)
                    arr_time = times[1].get_text(strip=True)
                    dur_text = dur_node.strip()
                    duration_mins = 120
                    match = re.search(r'(\d+)h(\d+)', dur_text)
                    if match:
                        duration_mins = (int(match.group(1))
                                         * 60) + int(match.group(2))

                    _, created = Sailing.objects.update_or_create(
                        route=route_obj,
                        date=date_obj,
                        departure_time=dep_time,
                        defaults={
                            'arrival_time': arr_time,
                            'duration_minutes': duration_mins,
                            'price_text': price_text
                        }
                    )
                    if created:
                        logger.info(
                            f"Saved Sailing: {date_obj} {dep_time}->{arr_time} ({price_text})")

        except Exception as e:
            logger.error(f"Parse Error on {date_obj}: {e}")

    def fallback_parse_times(self, soup, route_obj, date_obj, price_text):
        times = soup.find_all('time')
        for i in range(0, len(times), 2):
            if i + 1 < len(times):
                dep = times[i].get_text(strip=True)
                arr = times[i+1].get_text(strip=True)

                _, created = Sailing.objects.update_or_create(
                    route=route_obj,
                    date=date_obj,
                    departure_time=dep,
                    defaults={
                        'arrival_time': arr,
                        'duration_minutes': 120,
                        'price_text': price_text
                    }
                )
                if created:
                    logger.info(
                        f"Saved Sailing (Fallback): {date_obj} {dep}->{arr}")

    def parse_french_date(self, date_str):
        if not date_str:
            return None
        MONTHS = {'jan': 1, 'fév': 2, 'fev': 2, 'mar': 3, 'avr': 4, 'mai': 5, 'juin': 6,
                  'juil': 7, 'aoû': 8, 'aou': 8, 'sep': 9, 'oct': 10, 'nov': 11, 'déc': 12, 'dec': 12}
        try:
            clean = date_str.lower().replace('.', '').replace(
                ':', '').replace('date depart', '').strip()
            parts = clean.split()
            day = None
            month_idx = -1
            for i, part in enumerate(parts):
                if part.isdigit():
                    day = int(part)
                    month_idx = i + 1
                    break
            if not day or month_idx >= len(parts):
                return None

            month_str = parts[month_idx][0:3]
            month = MONTHS.get(month_str, 1)
            today = datetime.now().date()
            year = today.year
            if month < today.month - 2:
                year += 1
            return datetime(year, month, day).date()
        except:
            return None
