from __future__ import annotations

import requests
from django.conf import settings
from django.db import models

from .constants import (
    DEFAULT_CURRENCY,
    DEFAULT_FERRY_DURATION_MINS,
    DISCORD_TIMEOUT_SECONDS,
    MAX_ISSUE_NOTE_LENGTH,
)


class Carrier(models.Model):
    """
    Represents a transportation company (e.g., an Airline or a Ferry Operator).

    Fields:
    - code: The unique 2 or 3 letter designator (e.g., 'AA' for American Airlines).
    - carrier_type: Differentiates between air and sea operators.
    """

    class CarrierType(models.TextChoices):
        AIR = "AIR", "Airline"
        SEA = "SEA", "Ferry"

    TYPE_CHOICES = CarrierType.choices

    code = models.CharField(max_length=3, unique=True, db_index=True)
    name = models.CharField(max_length=100)
    carrier_type = models.CharField(
        max_length=3,
        choices=CarrierType.choices,
        default=CarrierType.AIR,
    )
    website = models.URLField(blank=True, null=True)

    def __str__(self) -> str:
        return f"{self.name} ({self.code})"


class Location(models.Model):
    """
    Represents a geographic transit hub, such as an Airport or Ferry Port.

    Self-Referencing Relationship:
    The `parent` ForeignKey allows creating a hierarchical structure. For example,
    a Ferry Port might be a child of a larger Airport on the same island. This
    is critical for resolving aliases when users search for a general destination.
    """

    class LocationType(models.TextChoices):
        APT = "APT", "Airport"
        PRT = "PRT", "Ferry Port"

    TYPE_CHOICES = LocationType.choices

    code = models.CharField(max_length=5, unique=True, db_index=True)
    name = models.CharField(max_length=100)
    city = models.CharField(max_length=100, blank=True)
    country = models.CharField(max_length=100, blank=True)
    location_type = models.CharField(
        max_length=3,
        choices=LocationType.choices,
        default=LocationType.APT,
    )

    latitude = models.FloatField(null=True, blank=True)
    longitude = models.FloatField(null=True, blank=True)

    parent = models.ForeignKey(
        "self",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="sub_locations",
    )

    def resolve_aliases(self) -> list[str]:
        """
        Resolves all related location codes for a given location.

        In the Caribbean, airports and ferry ports often serve the same island
        and are treated interchangeably for routing purposes. This method returns
        a list of location codes that includes:
        1. The location's own code
        2. Its children (e.g., Ferry ports attached to an Airport)
        3. Its parent (if it is a child)
        4. Its siblings (other children of the same parent)

        This enables flexible routing where a flight might land at DOM (Airport)
        and a ferry might depart from DMROS (Port) on the same island.
        """
        codes: set[str] = {self.code}
        for child in self.sub_locations.all():
            codes.add(child.code)
        if self.parent:
            codes.add(self.parent.code)
            for sibling in self.parent.sub_locations.all():
                codes.add(sibling.code)
        return list(codes)

    def __str__(self) -> str:
        return f"{self.code} - {self.name}"


class Route(models.Model):
    """
    Defines a generic path between an origin and destination serviced by a specific carrier.

    A Route serves as a template. It does not represent a specific trip on a specific date;
    instead, it defines the schedule, aircraft/vessel, and standard times. Concrete trips
    are instantiated as FlightInstance or Sailing models.
    """

    origin = models.ForeignKey(
        Location, on_delete=models.CASCADE, related_name="departures"
    )
    destination = models.ForeignKey(
        Location, on_delete=models.CASCADE, related_name="arrivals"
    )
    carrier = models.ForeignKey(
        Carrier, on_delete=models.CASCADE, related_name="routes"
    )

    days_of_operation = models.CharField(max_length=7, default="1234567")
    is_active = models.BooleanField(default=True, db_index=True)

    flight_number = models.CharField(max_length=20, blank=True, null=True)
    aircraft_type = models.CharField(max_length=20, blank=True, null=True)

    duration_minutes = models.IntegerField(null=True, blank=True)
    departure_time = models.TimeField(null=True, blank=True)
    arrival_time = models.TimeField(null=True, blank=True)

    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ["origin", "destination", "carrier", "departure_time"]
        indexes = [
            models.Index(fields=["origin", "destination", "is_active"]),
        ]

    def __str__(self) -> str:
        return f"{self.carrier.code}: {self.origin.code} -> {self.destination.code}"


class FlightInstance(models.Model):
    route = models.ForeignKey(
        Route, on_delete=models.CASCADE, related_name="flight_instances"
    )
    date = models.DateField(db_index=True)
    price_amount = models.DecimalField(
        max_digits=10, decimal_places=2, null=True, blank=True
    )
    currency = models.CharField(max_length=5, default=DEFAULT_CURRENCY)
    available_seats = models.IntegerField(null=True, blank=True)
    cabin_class = models.CharField(max_length=30, blank=True)
    last_seen_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ("route", "date")
        ordering = ["date"]

    def __str__(self) -> str:
        return f"{self.route.flight_number} on {self.date} - {self.price_amount} {self.currency}"


class Sailing(models.Model):
    route = models.ForeignKey(Route, on_delete=models.CASCADE, related_name="sailings")
    date = models.DateField(db_index=True)
    departure_time = models.TimeField()
    arrival_time = models.TimeField()
    duration_minutes = models.IntegerField(default=DEFAULT_FERRY_DURATION_MINS)
    price_text = models.CharField(max_length=50, blank=True)

    class Meta:
        unique_together = ("route", "date", "departure_time")
        ordering = ["date", "departure_time"]

    def __str__(self) -> str:
        return f"{self.route} on {self.date}"


class ReportedIssue(models.Model):
    class IssueType(models.TextChoices):
        ROUTING_ERROR = "routing_error", "Bad Route or Connection"
        MISSING_DATA = "missing_data", "Missing Airport or Ferry"
        UI_BUG = "ui_bug", "UI or Visual Bug"
        OTHER = "other", "Other"

    ISSUE_TYPES = IssueType.choices

    issue_type = models.CharField(max_length=20, choices=IssueType.choices)
    user_note = models.TextField()
    resolved = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self) -> str:
        return (
            f"{self.get_issue_type_display()} - {self.created_at.strftime('%m/%d/%Y')}"
        )

    def send_notifications(self) -> bool:
        """
        Dispatches a Discord webhook notification for newly reported issues.
        Truncates user input and disables @everyone/@here mention parsing for security.
        """
        webhook_url = getattr(settings, "DISCORD_WEBHOOK_URL", None)
        if webhook_url:
            try:
                safe_note = self.user_note[:MAX_ISSUE_NOTE_LENGTH]
                payload: dict[str, object] = {
                    "content": (
                        "🚨 **New Prop & Ferry Issue Reported** 🚨\n"
                        f"**Type:** {self.get_issue_type_display()}\n"
                        f"**Note:** {safe_note}"
                    ),
                    "allowed_mentions": {"parse": []},
                }
                requests.post(webhook_url, json=payload, timeout=DISCORD_TIMEOUT_SECONDS)
                return True
            except Exception:
                pass
        return False
