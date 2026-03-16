from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.response import Response
from datetime import datetime, timedelta
import requests
import os

from .models import Location, Route, Carrier, Sailing, ReportedIssue
from .serializers import LocationSerializer, RouteSerializer, CarrierSerializer, SailingSerializer, ReportedIssueSerializer

# --- HELPERS ---


def resolve_location(code):
    if not code:
        return []

    code = code.upper().strip()

    try:
        location = Location.objects.get(code=code)
        # Pulls the smart linking logic from your model
        return location.resolve_aliases()
    except Location.DoesNotExist:
        # Fallback if the code isn't in our DB yet
        return [code]


def get_seconds(t):
    """Safely convert time object to seconds, returning None if time is missing."""
    if t is None:
        return None
    return (t.hour * 3600) + (t.minute * 60) + t.second


# --- VIEWSETS ---

class LocationViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Location.objects.all()
    serializer_class = LocationSerializer


class CarrierViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Carrier.objects.all()
    serializer_class = CarrierSerializer


class SailingViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Sailing.objects.all()
    serializer_class = SailingSerializer


class RouteViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Route.objects.all()
    serializer_class = RouteSerializer

    @action(detail=False, methods=['get'])
    def search(self, request):
        origin_input = request.query_params.get('origin')
        dest_input = request.query_params.get('destination')
        date_str = request.query_params.get('date')

        if not (origin_input and dest_input and date_str):
            return Response({'error': 'Missing parameters'}, status=400)

        origins = resolve_location(origin_input)
        dests = resolve_location(dest_input)

        try:
            start_date = datetime.strptime(date_str, '%Y-%m-%d').date()
        except ValueError:
            return Response({'error': 'Invalid date format'}, status=400)

        final_itineraries = []
        found_on_requested_date = False

        # Check 3 days window
        for i in range(3):
            search_date = start_date + timedelta(days=i)
            day_of_week_today = str(search_date.isoweekday())

            next_day = search_date + timedelta(days=1)
            day_of_week_tomorrow = str(next_day.isoweekday())

            # --- 1. FIND DIRECT ROUTES (Both Flights and Ferries) ---

            # A. Look for Flights
            direct_flights = Route.objects.filter(
                origin__code__in=origins, destination__code__in=dests,
                is_active=True, days_of_operation__contains=day_of_week_today,
                carrier__carrier_type='AIR'  # Safety: Ignore base ferry routes
            )

            # B. Look for Ferries
            direct_ferries = Sailing.objects.filter(
                route__origin__code__in=origins, route__destination__code__in=dests,
                date=search_date
            )

            for f in direct_flights:
                if f.departure_time is None or f.duration_minutes is None:
                    continue

                f_data = RouteSerializer(f).data
                f_data['departure_date'] = search_date.strftime('%Y-%m-%d')
                arr_dt = datetime.combine(
                    search_date, f.departure_time) + timedelta(minutes=f.duration_minutes)
                f_data['arrival_date'] = arr_dt.date().strftime('%Y-%m-%d')

                final_itineraries.append({
                    'id': f.id, 'legs': [f_data],
                    'total_duration': f.duration_minutes, 'search_date': search_date
                })
                if i == 0:
                    found_on_requested_date = True

            for s in direct_ferries:
                if s.departure_time is None:
                    continue

                s_data = SailingSerializer(s).data
                s_data['departure_date'] = s.date.strftime('%Y-%m-%d')
                arr_dt = datetime.combine(
                    s.date, s.departure_time) + timedelta(minutes=s.duration_minutes)
                s_data['arrival_date'] = arr_dt.date().strftime('%Y-%m-%d')

                final_itineraries.append({
                    'id': s.id + 900000, 'legs': [s_data],
                    'total_duration': s.duration_minutes, 'search_date': search_date
                })
                if i == 0:
                    found_on_requested_date = True

            # --- 2. FIND CONNECTING ROUTES (The Stitcher) ---
            possible_leg1s = Route.objects.filter(
                origin__code__in=origins, is_active=True,
                days_of_operation__contains=day_of_week_today,
                carrier__carrier_type='AIR'
            ).exclude(destination__code__in=dests)

            for leg1 in possible_leg1s:
                if leg1.arrival_time is None or leg1.duration_minutes is None:
                    continue

                l1_arr_dt = datetime.combine(
                    search_date, leg1.arrival_time) + timedelta(minutes=leg1.duration_minutes)
                hub = leg1.destination
                hub_codes = resolve_location(hub.code)

                leg2_flights_today = Route.objects.filter(
                    origin__code__in=hub_codes, destination__code__in=dests,
                    is_active=True, days_of_operation__contains=day_of_week_today,
                    carrier__carrier_type='AIR'
                )
                leg2_flights_tomorrow = Route.objects.filter(
                    origin__code__in=hub_codes, destination__code__in=dests,
                    is_active=True, days_of_operation__contains=day_of_week_tomorrow,
                    carrier__carrier_type='AIR'
                )

                leg2_ferries = Sailing.objects.filter(
                    route__origin__code__in=hub_codes, route__destination__code__in=dests,
                    date__in=[search_date, next_day]
                )

                candidates = []
                for f in leg2_flights_today:
                    if f.departure_time:
                        candidates.append((f, datetime.combine(
                            search_date, f.departure_time), False))
                for f in leg2_flights_tomorrow:
                    if f.departure_time:
                        candidates.append((f, datetime.combine(
                            next_day, f.departure_time), False))
                for s in leg2_ferries:
                    if s.departure_time:
                        candidates.append(
                            (s, datetime.combine(s.date, s.departure_time), True))

                MIN_CONNECT_FLIGHT = 3600
                MIN_CONNECT_FERRY = 7200
                MAX_CONNECT = 86400

                for leg2_obj, l2_dep_dt, is_ferry in candidates:
                    gap_seconds = (l2_dep_dt - l1_arr_dt).total_seconds()
                    min_req = MIN_CONNECT_FERRY if is_ferry else MIN_CONNECT_FLIGHT

                    if min_req <= gap_seconds <= MAX_CONNECT:
                        leg1_data = RouteSerializer(leg1).data
                        leg1_data['departure_date'] = search_date.strftime(
                            '%Y-%m-%d')
                        leg1_data['arrival_date'] = l1_arr_dt.date().strftime(
                            '%Y-%m-%d')

                        hours = int(gap_seconds // 3600)
                        mins = int((gap_seconds % 3600) // 60)

                        is_overnight = l2_dep_dt.date() > l1_arr_dt.date()

                        if is_overnight or hours >= 12:
                            mode = "Ferry" if is_ferry else "Flight"
                            time_str = l2_dep_dt.strftime(
                                "%I:%M %p").lstrip("0")
                            day_phrase = "next morning" if l2_dep_dt.hour < 12 else "next day"
                            leg1_data['layover_text'] = f"🌙 Overnight layover in {hub.city}. Accommodation required. {mode} {day_phrase} at {time_str}."
                        else:
                            if is_ferry:
                                leg1_data['layover_text'] = f"🚕 {hours}h {mins}m Transfer to {leg2_obj.route.origin.name}"
                            else:
                                leg1_data['layover_text'] = f"{hours}h {mins}m Layover in {hub.city}"

                        l2_arr_dt = l2_dep_dt + \
                            timedelta(minutes=leg2_obj.duration_minutes)

                        if is_ferry:
                            sailing_data = SailingSerializer(leg2_obj).data
                            sailing_data['departure_date'] = l2_dep_dt.date().strftime(
                                '%Y-%m-%d')
                            sailing_data['arrival_date'] = l2_arr_dt.date().strftime(
                                '%Y-%m-%d')

                            final_itineraries.append({
                                'id': int(f"{leg1.id}{leg2_obj.id}9"),
                                'legs': [leg1_data, sailing_data],
                                'total_duration': leg1.duration_minutes + leg2_obj.duration_minutes + int(gap_seconds // 60),
                                'search_date': search_date
                            })
                        else:
                            leg2_data = RouteSerializer(leg2_obj).data
                            leg2_data['departure_date'] = l2_dep_dt.date().strftime(
                                '%Y-%m-%d')
                            leg2_data['arrival_date'] = l2_arr_dt.date().strftime(
                                '%Y-%m-%d')

                            final_itineraries.append({
                                'id': int(f"{leg1.id}{leg2_obj.id}8"),
                                'legs': [leg1_data, leg2_data],
                                'total_duration': leg1.duration_minutes + leg2_obj.duration_minutes + int(gap_seconds // 60),
                                'search_date': search_date
                            })

                        if i == 0:
                            found_on_requested_date = True

            if found_on_requested_date and i == 0:
                break

        return Response({
            'results': final_itineraries,
            'search_date': date_str,
            'found_date': final_itineraries[0]['search_date'] if final_itineraries else date_str,
            'date_was_changed': not found_on_requested_date and bool(final_itineraries)
        })


class ReportedIssueViewSet(viewsets.ModelViewSet):
    queryset = ReportedIssue.objects.all().order_by('-created_at')
    serializer_class = ReportedIssueSerializer

    def perform_create(self, serializer):
        # 1. Save the record to the PostgreSQL database
        issue = serializer.save()

        # 2. Fire the Discord Webhook silently in the background
        webhook_url = os.environ.get('DISCORD_WEBHOOK_URL')

        if webhook_url:
            payload = {
                "content": f"**🚨 New Report - Prop & Ferry**\n**Type:** {issue.get_issue_type_display()}\n**Note:** {issue.user_note}",
                "username": "Prop & Ferry Bot",
                "avatar_url": "https://emojipedia-us.s3.amazonaws.com/source/skype/289/ship_1f6a2.png"
            }
            try:
                requests.post(webhook_url, json=payload, timeout=5)
            except Exception as e:
                # Log the error, but don't break the user's API response
                print(f"Failed to send Discord webhook: {e}")
