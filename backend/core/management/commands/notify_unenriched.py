import requests
from django.conf import settings
from django.core.management.base import BaseCommand
from core.models import Location, Carrier


class Command(BaseCommand):
    help = 'Scans for stubbed locations/carriers and triggers a Discord webhook.'

    def handle(self, *args, **kwargs):
        webhook_url = getattr(settings, 'DISCORD_WEBHOOK_URL', None)
        if not webhook_url:
            self.stdout.write(self.style.ERROR(
                "No DISCORD_WEBHOOK_URL configured."))
            return

        # Identify stubs: Locations with no city, Carriers with the default fetch_routes name
        unenriched_locs = Location.objects.filter(city__exact='')
        unenriched_carriers = Carrier.objects.filter(
            name__startswith='Airline ')

        if not unenriched_locs.exists() and not unenriched_carriers.exists():
            self.stdout.write(self.style.SUCCESS(
                "All data is fully enriched!"))
            return

        # Format lists
        loc_text = "\n".join(
            [f"• **{loc.code}**" for loc in unenriched_locs]) or "All locations enriched."
        carrier_text = "\n".join(
            [f"• **{c.code}**" for c in unenriched_carriers]) or "All carriers enriched."

        # Discord Embed Payload
        payload = {
            "content": "🚨 **Prop & Ferry Data Alert: Enrichment Required** 🚨",
            "embeds": [
                {
                    "title": "📍 Unenriched Locations",
                    "description": f"The following airports/ports were discovered by the scraper but lack metadata (City, Country):\n\n{loc_text}",
                    "color": 16711680  # Red
                },
                {
                    "title": "✈️ Unenriched Carriers",
                    "description": f"The following carrier codes need proper names in enrich_carriers.py:\n\n{carrier_text}",
                    "color": 16753920  # Orange
                }
            ]
        }

        try:
            requests.post(webhook_url, json=payload, timeout=5)
            self.stdout.write(self.style.SUCCESS("Webhook sent successfully."))
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"Webhook failed: {e}"))
