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

    # Coordinates for future map features
    latitude = models.FloatField(null=True, blank=True)
    longitude = models.FloatField(null=True, blank=True)

    # Smart Linking (e.g., SLU and UVF are both St. Lucia)
    parent = models.ForeignKey('self', null=True, blank=True,
                               on_delete=models.SET_NULL, related_name='sub_locations')

    def resolve_aliases(self):
        """Returns all codes associated with this location (self + children + siblings)."""
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
    # Foreign Keys are indexed by default in Django, but explicit related_names help
    origin = models.ForeignKey(
        Location, on_delete=models.CASCADE, related_name='departures')
    destination = models.ForeignKey(
        Location, on_delete=models.CASCADE, related_name='arrivals')
    carrier = models.ForeignKey(
        Carrier, on_delete=models.CASCADE, related_name='routes')

    # Recurring Schedule (Flights)
    # 1=Mon, 7=Sun. Default is daily.
    days_of_operation = models.CharField(max_length=7, default="1234567")
    is_active = models.BooleanField(default=True, db_index=True)

    # Baselines (Actual times for ferries come from Sailing model)
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


class Sailing(models.Model):
    """
    Represents a specific Ferry trip on a specific date.
    Unlike flights, ferries often vary wildly by season/date.
    """
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
