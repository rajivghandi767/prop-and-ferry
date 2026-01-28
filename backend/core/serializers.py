from rest_framework import serializers
from .models import Location, Route, Carrier


class LocationSerializer(serializers.ModelSerializer):
    class Meta:
        model = Location
        fields = ['id', 'code', 'name', 'city', 'country', 'location_type']


class CarrierSerializer(serializers.ModelSerializer):
    class Meta:
        model = Carrier
        fields = ['id', 'code', 'name',
                  'carrier_type', 'website']


class RouteSerializer(serializers.ModelSerializer):
    # Nested Serializers: Return full objects instead of IDs
    origin = LocationSerializer(read_only=True)
    destination = LocationSerializer(read_only=True)
    carrier = CarrierSerializer(read_only=True)

    class Meta:
        model = Route
        # 👇 ADD 'days_of_operation' here
        fields = [
            'id',
            'origin',
            'destination',
            'carrier',
            'duration_minutes',
            'is_active',
            'departure_time',
            'arrival_time',
            'days_of_operation'
        ]
