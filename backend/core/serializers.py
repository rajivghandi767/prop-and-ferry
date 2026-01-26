from rest_framework import serializers
from .models import Location, Route, Carrier


class LocationSerializer(serializers.ModelSerializer):
    class Meta:
        model = Location
        fields = ['id', 'code', 'name', 'city', 'country', 'location_type']


class CarrierSerializer(serializers.ModelSerializer):
    class Meta:
        model = Carrier
        fields = ['id', 'code', 'name', 'carrier_type']


class RouteSerializer(serializers.ModelSerializer):
    # Nested Serializers: Instead of just returning the ID (e.g. "origin": 1),
    # we return the full object (e.g. "origin": {"code": "MIA", "name":...})
    # This saves the frontend from making extra API calls.
    origin = LocationSerializer(read_only=True)
    destination = LocationSerializer(read_only=True)
    carrier = CarrierSerializer(read_only=True)

    class Meta:
        model = Route
        fields = ['id', 'origin', 'destination',
                  'carrier', 'duration_minutes', 'is_active']
