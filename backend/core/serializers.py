from rest_framework import serializers
from .models import Location, Route, Carrier, Sailing


class LocationSerializer(serializers.ModelSerializer):
    class Meta:
        model = Location
        fields = ['code', 'name', 'city', 'country', 'location_type']


class CarrierSerializer(serializers.ModelSerializer):
    class Meta:
        model = Carrier
        fields = ['code', 'name', 'carrier_type', 'website']


class RouteSerializer(serializers.ModelSerializer):
    # Nested Serializers ensure rich data (Origin is an object, not just an ID)
    origin = LocationSerializer(read_only=True)
    destination = LocationSerializer(read_only=True)
    carrier = CarrierSerializer(read_only=True)
    is_ferry = serializers.SerializerMethodField()

    class Meta:
        model = Route
        fields = [
            'id', 'origin', 'destination', 'carrier',
            'duration_minutes', 'departure_time', 'arrival_time',
            'days_of_operation', 'is_ferry'
        ]

    def get_is_ferry(self, obj):
        return obj.carrier.carrier_type == 'SEA'


class SailingSerializer(serializers.ModelSerializer):
    # We flatten the Route data into the Sailing response
    origin = LocationSerializer(source='route.origin', read_only=True)
    destination = LocationSerializer(
        source='route.destination', read_only=True)
    carrier = CarrierSerializer(source='route.carrier', read_only=True)
    is_ferry = serializers.SerializerMethodField()

    class Meta:
        model = Sailing
        fields = [
            'id', 'origin', 'destination', 'carrier',
            'duration_minutes', 'departure_time', 'arrival_time',
            'date', 'price_text', 'is_ferry'
        ]

    def get_is_ferry(self, obj):
        return True
