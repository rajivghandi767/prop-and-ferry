import time
import os
import urllib.parse
from datetime import datetime, timedelta
from bs4 import BeautifulSoup
from django.core.management.base import BaseCommand
from playwright.sync_api import sync_playwright
from core.models import Location, Route, Carrier
from core.constants import (
    PORT_ROSEAU, PORT_PTP, PORT_FDF, PORT_CASTRIES,
    DB_TO_SITE_OPTS
)

# 🛑 CRITICAL FIX: Allow DB access from Playwright's internal threads
# Without this, Django blocks the ORM save inside the scraping loop.
os.environ["DJANGO_ALLOW_ASYNC_UNSAFE"] = "true"


class Command(BaseCommand):
    help = 'Scrapes L\'Express des Iles (FRS) using Direct URL Injection & HTML Parsing'

    def handle(self, *args, **kwargs):
        # --- CONFIGURATION ---
        env = os.getenv('DJANGO_ENV', 'development')
        is_headless = (env == 'production')

        self.stdout.write(
            f"🚢 Initializing Ferry Scraper (Env: {env} | Headless: {is_headless})...")

        # 1. DEFINE BASE ROUTES
        # We define one-way pairs here; the loop below automatically generates the return legs.
        base_routes = [
            (PORT_PTP, PORT_ROSEAU),      # Guadeloupe -> Dominica
            (PORT_FDF, PORT_ROSEAU),      # Martinique -> Dominica
            (PORT_CASTRIES, PORT_ROSEAU),  # St. Lucia -> Dominica
        ]

        # 2. GENERATE BIDIRECTIONAL ROUTES
        # Ensure we check A->B and B->A explicitly
        final_routes = []
        for start, end in base_routes:
            final_routes.append((start, end))
            final_routes.append((end, start))

        self.stdout.write(
            f"   ℹ️  Generated {len(final_routes)} route pairs to check.")

        # Base URL for the booking engine (found in <form action="...">)
        BASE_URL = "https://goexpress-b2c.frs-express.com/B2C_2018/"

        with sync_playwright() as p:
            # 1. LAUNCH BROWSER
            browser = p.chromium.launch(headless=is_headless)

            # Optimized Viewport: 800x600 fits nicely on Mac split-screen while keeping elements visible
            context = browser.new_context(
                viewport={'width': 800, 'height': 600})
            page = context.new_page()

            try:
                # 🗓️ DATE STRATEGY: Start from TOMORROW (days=1)
                # This ensures your frontend '7-day lookahead' actually finds data immediately.
                start_date = datetime.now() + timedelta(days=1)

                for origin_code, dest_code in final_routes:
                    self.stdout.write(self.style.WARNING(
                        f"\n--- Checking {origin_code} -> {dest_code} ---"))

                    for i in range(7):
                        check_date = start_date + timedelta(days=i)
                        date_str = check_date.strftime('%d/%m/%Y')

                        # Map internal codes (GPPTP) to site codes (PTP)
                        site_origin = DB_TO_SITE_OPTS[origin_code][0]
                        site_dest = DB_TO_SITE_OPTS[dest_code][0]

                        # URL Parameters (Bypasses the "One Way" click and Date Picker)
                        params = {
                            'aller': 'AS',          # One Way
                            'depart': site_origin,
                            'arrivee': site_dest,
                            'date_aller': date_str,
                            'adultes': '1',
                            'enfants': '0', 'bebes': '0', 'vehicules': '0'
                        }
                        full_url = f"{BASE_URL}?{urllib.parse.urlencode(params)}"

                        try:
                            # 2. NAVIGATE (The Nuclear Option ☢️)
                            # We go straight to results. 'domcontentloaded' prevents waiting for slow ads/trackers.
                            try:
