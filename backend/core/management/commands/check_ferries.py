from django.core.management.base import BaseCommand
from core.models import Route, Carrier


class Command(BaseCommand):
    help = 'Inspects the database and lists all discovered ferry routes'

    def handle(self, *args, **kwargs):
        self.stdout.write("🚢 --- FERRY DATABASE REPORT --- 🚢\n")

        # 1. Get the Ferry Carrier
        try:
            lxi = Carrier.objects.get(code='LXI')
        except Carrier.DoesNotExist:
            self.stdout.write(self.style.ERROR(
                "❌ No Ferry Carrier (LXI) found in DB."))
            return

        # 2. Get Routes
        routes = Route.objects.filter(carrier=lxi).order_by(
            'origin__code', 'days_of_operation')

        if not routes.exists():
            self.stdout.write(self.style.WARNING(
                "❌ Carrier found, but NO routes scraped yet."))
            return

        self.stdout.write(self.style.SUCCESS(
            f"✅ Found {routes.count()} Active Routes:\n"))

        # 3. Print Details
        days_map = {'1': 'Mon', '2': 'Tue', '3': 'Wed',
                    '4': 'Thu', '5': 'Fri', '6': 'Sat', '7': 'Sun'}

        for r in routes:
            # Sort days string "135" -> "1, 3, 5" -> "Mon, Wed, Fri"
            sorted_days = sorted(list(r.days_of_operation))
            human_days = ", ".join([days_map[d]
                                   for d in sorted_days if d in days_map])

            # Format: PTP -> DOM
            title = f"{r.origin.code} -> {r.destination.code}"

            self.stdout.write(self.style.MIGRATE_HEADING(f"📍 {title}"))
            self.stdout.write(f"   🕒 {r.departure_time} - {r.arrival_time}")
            self.stdout.write(
                f"   📅 Days: {r.days_of_operation} ({human_days})")
            self.stdout.write(
                f"   🔗 Last Scrape: {r.updated_at.strftime('%Y-%m-%d %H:%M')}")
            self.stdout.write("-" * 40)
