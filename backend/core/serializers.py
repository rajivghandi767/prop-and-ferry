from rest_framework import serializers
from .models import Location, Carrier, Route, FlightInstance, Sailing

# --- STANDARD CRUD SERIALIZERS ---


class LocationSerializer(serializers.ModelSerializer):
    class Meta:
        model = Location
        fields = ['code', 'name', 'city', 'country', 'location_type']


class CarrierSerializer(serializers.ModelSerializer):
    class Meta:
        model = Carrier
        fields = ['code', 'name', 'carrier_type', 'website']


class RouteSerializer(serializers.ModelSerializer):
    origin = LocationSerializer(read_only=True)
    destination = LocationSerializer(read_only=True)
    carrier = CarrierSerializer(read_only=True)

    class Meta:
        model = Route
        fields = [
            'id', 'origin', 'destination', 'carrier',
            'flight_number', 'aircraft_type',
            'duration_minutes', 'departure_time', 'arrival_time'
        ]


class FlightInstanceSerializer(serializers.ModelSerializer):
    route = RouteSerializer(read_only=True)

    class Meta:
        model = FlightInstance
        fields = [
            'id', 'route', 'date', 'price_amount',
            'currency', 'available_seats', 'cabin_class', 'last_seen_at'
        ]


class SailingSerializer(serializers.ModelSerializer):
    route = RouteSerializer(read_only=True)

    class Meta:
        model = Sailing
        fields = [
            'id', 'route', 'date', 'departure_time',
            'arrival_time', 'duration_minutes', 'price_text'
        ]


# --- NEW: CUSTOM SEARCH SERIALIZERS ---

class ItineraryLegSerializer(serializers.Serializer):
    """Dynamically shapes either a FlightInstance or a Sailing into the frontend ApiLeg contract"""
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

    def get_is_ferry(self, obj):
        return isinstance(obj, Sailing)

    def get_origin(self, obj):
        return {"code": obj.route.origin.code, "name": obj.route.origin.name, "city": obj.route.origin.city}

    def get_destination(self, obj):
        return {"code": obj.route.destination.code, "name": obj.route.destination.name, "city": obj.route.destination.city}

    def get_carrier(self, obj):
        return {"code": obj.route.carrier.code, "name": obj.route.carrier.name, "website": obj.route.carrier.website}

    def get_departure_date(self, obj):
        return obj.date.strftime('%Y-%m-%d')

    def get_arrival_date(self, obj):
        return obj.date.strftime('%Y-%m-%d')

    def get_departure_time(self, obj):
        time = obj.departure_time if isinstance(
            obj, Sailing) else obj.route.departure_time
        return time.strftime('%H:%M') if time else "00:00"

    def get_arrival_time(self, obj):
        time = obj.arrival_time if isinstance(
            obj, Sailing) else obj.route.arrival_time
        return time.strftime('%H:%M') if time else "00:00"

    def get_duration_minutes(self, obj):
        return obj.duration_minutes if isinstance(obj, Sailing) else obj.route.duration_minutes

    def get_flight_number(self, obj):
        return obj.route.flight_number

    def get_aircraft_type(self, obj):
        return obj.route.aircraft_type

    def get_days_of_operation(self, obj):
        return None if isinstance(obj, Sailing) else obj.route.days_of_operation

    def get_price_text(self, obj):
        if isinstance(obj, Sailing):
            return obj.price_text
        if getattr(obj, 'price_amount', None):
            return f"${obj.price_amount} {obj.currency}"
        return None


class ItinerarySerializer(serializers.Serializer):
    id = serializers.CharField()
    legs = ItineraryLegSerializer(many=True)


class SearchResponseSerializer(serializers.Serializer):
    date_was_changed = serializers.BooleanField()
    found_date = serializers.CharField()
    results = ItinerarySerializer(many=True)
