from __future__ import annotations

from typing import Any
from rest_framework import serializers

from .constants import MAX_ISSUE_NOTE_LENGTH, SOLD_OUT_LABEL
from .models import Carrier, FlightInstance, Location, ReportedIssue, Route, Sailing

type TransitLeg = FlightInstance | Sailing


class LocationSerializer(serializers.ModelSerializer):
    parent_code = serializers.CharField(
        source="parent.code", read_only=True, default=None
    )
    has_children = serializers.SerializerMethodField()

    class Meta:
        model = Location
        fields = [
            "id",
            "code",
            "name",
            "city",
            "country",
            "location_type",
            "parent_code",
            "has_children",
        ]

    def get_has_children(self, obj: Location) -> bool:
        # Prevent N+1 query by checking the prefetched cache
        return len(obj.sub_locations.all()) > 0


class CarrierSerializer(serializers.ModelSerializer):
    class Meta:
        model = Carrier
        fields = ["code", "name", "carrier_type", "website"]


class RouteSerializer(serializers.ModelSerializer):
    origin = LocationSerializer(read_only=True)
    destination = LocationSerializer(read_only=True)
    carrier = CarrierSerializer(read_only=True)

    class Meta:
        model = Route
        fields = [
            "id",
            "origin",
            "destination",
            "carrier",
            "flight_number",
            "aircraft_type",
            "duration_minutes",
            "departure_time",
            "arrival_time",
        ]


class SailingSerializer(serializers.ModelSerializer):
    route = RouteSerializer(read_only=True)

    class Meta:
        model = Sailing
        fields = [
            "id",
            "route",
            "date",
            "departure_time",
            "arrival_time",
            "duration_minutes",
            "price_text",
        ]


class ItineraryLegSerializer(serializers.Serializer):
    """
    Normalizes heterogeneous FlightInstance and Sailing records into a unified
    transit leg contract for the frontend client.
    """

    is_ferry = serializers.SerializerMethodField()
    origin = serializers.SerializerMethodField()
    destination = serializers.SerializerMethodField()
    carrier = serializers.SerializerMethodField()
    departure_date = serializers.SerializerMethodField()
    arrival_date = serializers.SerializerMethodField()
    departure_time = serializers.SerializerMethodField()
    arrival_time = serializers.SerializerMethodField()
    duration_minutes = serializers.SerializerMethodField()
    flight_number = serializers.SerializerMethodField()
    aircraft_type = serializers.SerializerMethodField()
    days_of_operation = serializers.SerializerMethodField()
    price_text = serializers.SerializerMethodField()
    available_seats = serializers.SerializerMethodField()
    is_sold_out = serializers.SerializerMethodField()
    last_seen_at = serializers.SerializerMethodField()

    def get_is_ferry(self, obj: TransitLeg) -> bool:
        return isinstance(obj, Sailing)

    def get_origin(self, obj: TransitLeg) -> dict[str, Any]:
        return {
            "code": obj.route.origin.code,
            "name": obj.route.origin.name,
            "city": obj.route.origin.city,
        }

    def get_destination(self, obj: TransitLeg) -> dict[str, Any]:
        return {
            "code": obj.route.destination.code,
            "name": obj.route.destination.name,
            "city": obj.route.destination.city,
        }

    def get_carrier(self, obj: TransitLeg) -> dict[str, Any]:
        return {
            "code": obj.route.carrier.code,
            "name": obj.route.carrier.name,
            "website": obj.route.carrier.website,
        }

    def get_departure_date(self, obj: TransitLeg) -> str:
        return obj.date.strftime("%Y-%m-%d")

    def get_arrival_date(self, obj: TransitLeg) -> str:
        return obj.date.strftime("%Y-%m-%d")

    def get_departure_time(self, obj: TransitLeg) -> str:
        dep_time = (
            obj.departure_time if isinstance(obj, Sailing) else obj.route.departure_time
        )
        return dep_time.strftime("%H:%M") if dep_time else "00:00"

    def get_arrival_time(self, obj: TransitLeg) -> str:
        arr_time = (
            obj.arrival_time if isinstance(obj, Sailing) else obj.route.arrival_time
        )
        return arr_time.strftime("%H:%M") if arr_time else "00:00"

    def get_duration_minutes(self, obj: TransitLeg) -> int | None:
        return (
            obj.duration_minutes
            if isinstance(obj, Sailing)
            else obj.route.duration_minutes
        )

    def get_flight_number(self, obj: TransitLeg) -> str | None:
        return obj.route.flight_number

    def get_aircraft_type(self, obj: TransitLeg) -> str | None:
        return obj.route.aircraft_type

    def get_days_of_operation(self, obj: TransitLeg) -> str | None:
        return None if isinstance(obj, Sailing) else obj.route.days_of_operation

    def get_price_text(self, obj: TransitLeg) -> str | None:
        if isinstance(obj, Sailing):
            return obj.price_text
        if obj.available_seats == 0:
            return SOLD_OUT_LABEL
        if obj.price_amount is not None:
            return f"{obj.currency} {obj.price_amount}"
        return None

    def get_available_seats(self, obj: TransitLeg) -> int | None:
        if isinstance(obj, Sailing):
            return None
        return obj.available_seats

    def get_is_sold_out(self, obj: TransitLeg) -> bool:
        if isinstance(obj, Sailing):
            return False
        return obj.available_seats is not None and obj.available_seats <= 0

    def get_last_seen_at(self, obj: TransitLeg) -> str | None:
        if isinstance(obj, FlightInstance) and obj.last_seen_at:
            return obj.last_seen_at.strftime("%b %d, %H:%M")
        return None


class ReportedIssueSerializer(serializers.ModelSerializer):
    user_note = serializers.CharField(max_length=MAX_ISSUE_NOTE_LENGTH)

    class Meta:
        model = ReportedIssue
        fields = ["id", "issue_type", "user_note", "resolved", "created_at"]
        read_only_fields = ["id", "resolved", "created_at"]
