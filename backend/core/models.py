from django.db import models


class Carrier(models.Model):
    TYPE_CHOICES = (('AIR', 'Airline'), ('SEA', 'Ferry'))
    code = models.CharField(max_length=3, unique=True, db_index=True)
    name = models.CharField(max_length=100)
    carrier_type = models.CharField(
        max_length=3, choices=TYPE_CHOICES, default='AIR')
    website = models.URLField(blank=True, null=True)

    def __str__(self):
        return f"{self.name} ({self.code})"


class Location(models.Model):
    TYPE_CHOICES = (('APT', 'Airport'), ('PRT', 'Ferry Port'))
    code = models.CharField(max_length=5, unique=True, db_index=True)
    name = models.CharField(max_length=100)
    city = models.CharField(max_length=100, blank=True)
    country = models.CharField(max_length=100, blank=True)
    location_type = models.CharField(
        max_length=3, choices=TYPE_CHOICES, default='APT')

    latitude = models.FloatField(null=True, blank=True)
    longitude = models.FloatField(null=True, blank=True)

    parent = models.ForeignKey('self', null=True, blank=True,
                               on_delete=models.SET_NULL, related_name='sub_locations')

    def resolve_aliases(self):
        codes = {self.code}
        for child in self.sub_locations.all():
            codes.add(child.code)
        if self.parent:
            codes.add(self.parent.code)
            for sibling in self.parent.sub_locations.all():
                codes.add(sibling.code)
        return list(codes)

    def __str__(self):
        return f"{self.code} - {self.name}"


class Route(models.Model):
    origin = models.ForeignKey(
        Location, on_delete=models.CASCADE, related_name='departures')
    destination = models.ForeignKey(
        Location, on_delete=models.CASCADE, related_name='arrivals')
    carrier = models.ForeignKey(
        Carrier, on_delete=models.CASCADE, related_name='routes')

    days_of_operation = models.CharField(max_length=7, default="1234567")
    is_active = models.BooleanField(default=True, db_index=True)

    flight_number = models.CharField(max_length=20, blank=True, null=True)
    aircraft_type = models.CharField(max_length=20, blank=True, null=True)

    duration_minutes = models.IntegerField(null=True, blank=True)
    departure_time = models.TimeField(null=True, blank=True)
    arrival_time = models.TimeField(null=True, blank=True)

    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ['origin', 'destination',
                           'carrier', 'departure_time']
        indexes = [
            models.Index(fields=['origin', 'destination', 'is_active']),
        ]

    def __str__(self):
        return f"{self.carrier.code}: {self.origin.code} -> {self.destination.code}"


class FlightInstance(models.Model):
    route = models.ForeignKey(
        Route, on_delete=models.CASCADE, related_name='flight_instances')
    date = models.DateField(db_index=True)
    price_amount = models.DecimalField(
        max_digits=10, decimal_places=2, null=True, blank=True)
    currency = models.CharField(max_length=5, default='USD')
    available_seats = models.IntegerField(null=True, blank=True)
    cabin_class = models.CharField(max_length=30, blank=True)
    last_seen_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ('route', 'date')
        ordering = ['date']

    def __str__(self):
        return f"{self.route.flight_number} on {self.date} - {self.price_amount} {self.currency}"


class Sailing(models.Model):
    route = models.ForeignKey(
        Route, on_delete=models.CASCADE, related_name='sailings')
    date = models.DateField(db_index=True)
    departure_time = models.TimeField()
    arrival_time = models.TimeField()
    duration_minutes = models.IntegerField(default=120)
    price_text = models.CharField(max_length=50, blank=True)

    class Meta:
        unique_together = ('route', 'date', 'departure_time')
        ordering = ['date', 'departure_time']

    def __str__(self):
        return f"{self.route} on {self.date}"


class ReportedIssue(models.Model):
    ISSUE_TYPES = [
        ('routing_error', 'Bad Route or Connection'),
        ('missing_data', 'Missing Airport or Ferry'),
        ('ui_bug', 'UI or Visual Bug'),
        ('other', 'Other'),
    ]
    issue_type = models.CharField(max_length=20, choices=ISSUE_TYPES)
    user_note = models.TextField()
    resolved = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.get_issue_type_display()} - {self.created_at.strftime('%m/%d/%Y')}"
