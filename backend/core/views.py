from rest_framework import viewsets
from .models import Location, Route, Carrier
from .serializers import LocationSerializer, RouteSerializer, CarrierSerializer


class LocationViewSet(viewsets.ReadOnlyModelViewSet):
    """
    API endpoint that allows Locations (Airports/Ports) to be viewed.
    """
    queryset = Location.objects.all()
    serializer_class = LocationSerializer
    lookup_field = 'code'  # Allows accessing via /api/locations/JFK/ instead of IDs


class CarrierViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Carrier.objects.all()
    serializer_class = CarrierSerializer


class RouteViewSet(viewsets.ReadOnlyModelViewSet):
    """
    API endpoint for Routes. 
    Supports filtering: /api/routes/?origin=MIA&destination=DOM
    """
    serializer_class = RouteSerializer

    def get_queryset(self):
        """
        Optionally restricts the returned routes by filtering against
        'origin' and 'destination' query parameters in the URL.
        """
        queryset = Route.objects.filter(is_active=True)

        # Grab params from URL
        origin = self.request.query_params.get('origin')
        destination = self.request.query_params.get('destination')

        # Apply filters if params exist
        if origin:
            queryset = queryset.filter(origin__code__iexact=origin)
        if destination:
            queryset = queryset.filter(destination__code__iexact=destination)

        return queryset
