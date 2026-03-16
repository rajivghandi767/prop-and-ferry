from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.response import Response
from datetime import timedelta, datetime

from .models import Location, Route, Sailing, FlightInstance, Carrier, ReportedIssue
from .serializers import LocationSerializer, RouteSerializer, SailingSerializer, SearchResponseSerializer, CarrierSerializer

# Standard ViewSets for basic CRUD operations


class LocationViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Location.objects.all()
    serializer_class = LocationSerializer


class CarrierViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Carrier.objects.all()
    serializer_class = CarrierSerializer


class SailingViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Sailing.objects.all()
    serializer_class = SailingSerializer


class ReportedIssueViewSet(viewsets.ModelViewSet):
    queryset = ReportedIssue.objects.all()
    # Assuming you have a ReportedIssueSerializer, otherwise remove this ViewSet or create the serializer
    # serializer_class = ReportedIssueSerializer

# Advanced ViewSet containing custom actions for the React App


class RouteViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Route.objects.all()
    serializer_class = RouteSerializer

    # Translates to: GET /api/routes/available-dates/
    @action(detail=False, methods=['get'], url_path='available-dates')
    def available_dates(self, request):
        origin_query = request.GET.get('origin')
        dest_query = request.GET.get('destination')

        if not origin_query or not dest_query:
            return Response({'error': 'Missing parameters'}, status=400)

        try:
            origin_loc = Location.objects.get(code=origin_query)
            dest_loc = Location.objects.get(code=dest_query)
        except Location.DoesNotExist:
            return Response({'error': 'Location not found'}, status=404)

        origin_aliases = origin_loc.resolve_aliases()
        dest_aliases = dest_loc.resolve_aliases()

        flight_dates = FlightInstance.objects.filter(
            route__origin__code__in=origin_aliases,
            route__destination__code__in=dest_aliases,
            route__is_active=True
        ).values_list('date', flat=True).distinct()

        ferry_dates = Sailing.objects.filter(
            route__origin__code__in=origin_aliases,
            route__destination__code__in=dest_aliases,
            route__is_active=True
        ).values_list('date', flat=True).distinct()

        all_dates = sorted(list(set(flight_dates) | set(ferry_dates)))
        return Response({'available_dates': [d.strftime('%Y-%m-%d') for d in all_dates]})

    # Translates to: GET /api/routes/search/
    @action(detail=False, methods=['get'])
    def search(self, request):
        origin_query = request.GET.get('origin')
        dest_query = request.GET.get('destination')
        target_date_str = request.GET.get('date')

        if not origin_query or not dest_query or not target_date_str:
            return Response({'error': 'Missing parameters'}, status=400)

        try:
            origin_loc = Location.objects.get(code=origin_query)
            dest_loc = Location.objects.get(code=dest_query)
            target_date = datetime.strptime(target_date_str, '%Y-%m-%d').date()
        except (Location.DoesNotExist, ValueError):
            return Response({'error': 'Invalid parameters'}, status=400)

        origin_aliases = origin_loc.resolve_aliases()
        dest_aliases = dest_loc.resolve_aliases()

        found_date = target_date
        date_was_changed = False
        flights, ferries = [], []

        # Look up to 3 days ahead for availability
        for i in range(4):
            check_date = target_date + timedelta(days=i)

            flights = list(FlightInstance.objects.filter(
                route__origin__code__in=origin_aliases,
                route__destination__code__in=dest_aliases,
                date=check_date,
                route__is_active=True
            ).select_related('route', 'route__carrier', 'route__origin', 'route__destination'))

            ferries = list(Sailing.objects.filter(
                route__origin__code__in=origin_aliases,
                route__destination__code__in=dest_aliases,
                date=check_date,
                route__is_active=True
            ).select_related('route', 'route__carrier', 'route__origin', 'route__destination'))

            if flights or ferries:
                if i > 0:
                    date_was_changed = True
                    found_date = check_date
                break

        # Shape the raw data for the Serializer
        results = []
        for flight in flights:
            results.append({"id": f"f_{flight.id}", "legs": [flight]})
        for ferry in ferries:
            results.append({"id": f"s_{ferry.id}", "legs": [ferry]})

        # Let the Serializer cleanly format the final output
        response_data = {
            "date_was_changed": date_was_changed,
            "found_date": found_date.strftime('%Y-%m-%d'),
            "results": results
        }

        serializer = SearchResponseSerializer(response_data)
        return Response(serializer.data)
