from django.db import models


class Carrier(models.Model):
    TYPE_CHOICES = (('AIR', 'Airline'), ('SEA', 'Ferry'))
    code = models.CharField(max_length=3, unique=True)
    name = models.CharField(max_length=100)
    carrier_type = models.CharField(
        max_length=3, choices=TYPE_CHOICES, default='AIR')
    website = models.URLField(blank=True)

    def __str__(self):
        return f"{self.name} ({self.code})"


class Location(models.Model):
    TYPE_CHOICES = (('APT', 'Airport'), ('PRT', 'Ferry Port'))
    code = models.CharField(max_length=5, unique=True)
    name = models.CharField(max_length=100)
    city = models.CharField(max_length=100)
    country = models.CharField(max_length=100)
    location_type = models.CharField(
        max_length=3, choices=TYPE_CHOICES, default='APT')
    latitude = models.FloatField(null=True, blank=True)
    longitude = models.FloatField(null=True, blank=True)

    def __str__(self):
        return f"{self.code} - {self.name}"


class Route(models.Model):
    origin = models.ForeignKey(
        Location, on_delete=models.CASCADE, related_name='departures')
    destination = models.ForeignKey(
        Location, on_delete=models.CASCADE, related_name='arrivals')
    carrier = models.ForeignKey(
        Carrier, on_delete=models.CASCADE, related_name='routes')
    is_active = models.BooleanField(default=True)
    duration_minutes = models.IntegerField(null=True, blank=True)

    class Meta:
        unique_together = ('origin', 'destination', 'carrier')

    def __str__(self):
        return f"{self.carrier.code}: {self.origin.code} ➝ {self.destination.code}"
