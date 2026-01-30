from django.db import models


class Carrier(models.Model):
    TYPE_CHOICES = (('AIR', 'Airline'), ('SEA', 'Ferry'))
    code = models.CharField(max_length=3, unique=True)
    name = models.CharField(max_length=100)
    carrier_type = models.CharField(
        max_length=3, choices=TYPE_CHOICES, default='AIR')
    website = models.URLField(blank=True, null=True)

    def __str__(self):
        return f"{self.name} ({self.code})"


class Location(models.Model):
    TYPE_CHOICES = (('APT', 'Airport'), ('PRT', 'Ferry Port'))

    # Core Fields
    code = models.CharField(max_length=5, unique=True)  # UN/LOCODE
    name = models.CharField(max_length=100)
    city = models.CharField(max_length=100, blank=True)
    country = models.CharField(max_length=100, blank=True)
    location_type = models.CharField(
        max_length=3, choices=TYPE_CHOICES, default='APT')

    # Coordinates
    latitude = models.FloatField(null=True, blank=True)
    longitude = models.FloatField(null=True, blank=True)

    # NEW: Smart Linking
    # Example: 'DMROS' (Roseau Ferry) has parent 'DOM' (Dominica Generic)
    parent = models.ForeignKey(
        'self',
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='sub_locations'
    )

    def resolve_aliases(self):
        """
        Returns a list of location codes that should be included when searching 
        for this location. (e.g., Searching 'DOM' returns ['DOM', 'DMROS'])
        """
        # Start with self
        codes = {self.code}

        # 1. If I am a parent (e.g., DOM), include my children (DMROS)
        for child in self.sub_locations.all():
            codes.add(child.code)

        # 2. If I am a child (e.g., DMROS), include my parent (DOM)
        if self.parent:
            codes.add(self.parent.code)
            # And include my siblings (e.g., if there was a 2nd ferry port)
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

    # "135" means Mon/Wed/Fri
    days_of_operation = models.CharField(
        max_length=7,
        default="1234567",
        help_text="Days this route runs (1=Monday, 7=Sunday)"
    )
    is_active = models.BooleanField(default=True)

    duration_minutes = models.IntegerField(null=True, blank=True)
    departure_time = models.TimeField(null=True, blank=True)
    arrival_time = models.TimeField(null=True, blank=True)

    updated_at = models.DateTimeField(auto_now=True, db_index=True)

    class Meta:
        unique_together = ('origin', 'destination', 'carrier')

    def __str__(self):
        return f"{self.carrier.code}: {self.origin.code} -> {self.destination.code}"
