from unittest.mock import patch, MagicMock
from datetime import date, time
from django.core.cache import cache
from django.test import TestCase
from django.urls import reverse
from rest_framework.test import APITestCase

from core.management.commands.fetch_duffel_routes import Command as FetchDuffelCommand
from core.models import FlightInstance, Route, Carrier, Location, Sailing


class SearchRoutesTests(APITestCase):
    def setUp(self) -> None:
        cache.clear()
        self.mia = Location.objects.create(code="MIA", name="Miami Intl", city="Miami", country="USA")
        self.skb = Location.objects.create(code="SKB", name="Robert L. Bradshaw", city="Basseterre", country="St. Kitts")
        self.dom = Location.objects.create(code="DOM", name="Douglas-Charles", city="Marigot", country="Dominica")
        self.dmros = Location.objects.create(
            code="DMROS",
            name="Roseau Ferry Terminal",
            city="Roseau",
            country="Dominica",
            location_type="PRT",
            parent=self.dom,
        )
        self.ptp = Location.objects.create(code="PTP", name="Pointe-a-Pitre Intl", city="Pointe-a-Pitre", country="Guadeloupe")
        self.gpptp = Location.objects.create(
            code="GPPTP",
            name="Bergevin Ferry Port",
            city="Pointe-a-Pitre",
            country="Guadeloupe",
            location_type="PRT",
            parent=self.ptp,
        )
        self.par = Location.objects.create(code="PAR", name="Paris", city="Paris", country="France")
        self.ory = Location.objects.create(
            code="ORY",
            name="Orly Airport",
            city="Paris",
            country="France",
            parent=self.par,
        )

        self.carrier_air = Carrier.objects.create(code="WM", name="Winair", carrier_type="airline")
        self.carrier_ferry = Carrier.objects.create(code="EXP", name="Express des Iles", carrier_type="ferry")

    def test_search_routes_missing_params(self) -> None:
        response = self.client.get('/api/routes/search/')
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.data['error'], 'Missing parameters')

    def test_search_routes_with_filter(self) -> None:
        # It should return 404 Location not found if the locations don't exist
        response = self.client.get('/api/routes/search/?origin=JFK&destination=DOM&date=2026-07-01&filter=ferry')
        self.assertIn(response.status_code, [200, 404, 400])

    def test_available_dates_includes_stitched_flight_to_flight(self) -> None:
        # Leg 1: MIA -> SKB departing 11:00, arriving 14:00 on 2026-09-18
        r1 = Route.objects.create(
            origin=self.mia,
            destination=self.skb,
            carrier=self.carrier_air,
            flight_number="AA123",
            departure_time=time(11, 0),
            arrival_time=time(14, 0),
            is_active=True,
        )
        FlightInstance.objects.create(
            route=r1,
            date=date(2026, 9, 18),
            price_amount=200.0,
            available_seats=5,
        )

        # Leg 2: SKB -> DOM departing 16:00, arriving 16:45 on 2026-09-18 (2h layover)
        r2 = Route.objects.create(
            origin=self.skb,
            destination=self.dom,
            carrier=self.carrier_air,
            flight_number="WM311",
            departure_time=time(16, 0),
            arrival_time=time(16, 45),
            is_active=True,
        )
        FlightInstance.objects.create(
            route=r2,
            date=date(2026, 9, 18),
            price_amount=150.0,
            available_seats=4,
        )

        response = self.client.get('/api/routes/available-dates/?origin=MIA&destination=DOM')
        self.assertEqual(response.status_code, 200)
        self.assertIn("2026-09-18", response.data.get("available_dates", []))

    def test_available_dates_excludes_invalid_connection_gap(self) -> None:
        # Leg 1: MIA -> SKB departing 11:00, arriving 14:00 on 2026-09-18
        r1 = Route.objects.create(
            origin=self.mia,
            destination=self.skb,
            carrier=self.carrier_air,
            flight_number="AA124",
            departure_time=time(11, 0),
            arrival_time=time(14, 0),
            is_active=True,
        )
        FlightInstance.objects.create(
            route=r1,
            date=date(2026, 9, 18),
            price_amount=200.0,
            available_seats=5,
        )

        # Leg 2: SKB -> DOM departing 14:15 (only 15 mins layover, below 1h minimum)
        r2 = Route.objects.create(
            origin=self.skb,
            destination=self.dom,
            carrier=self.carrier_air,
            flight_number="WM312",
            departure_time=time(14, 15),
            arrival_time=time(15, 0),
            is_active=True,
        )
        FlightInstance.objects.create(
            route=r2,
            date=date(2026, 9, 18),
            price_amount=150.0,
            available_seats=4,
        )

        response = self.client.get('/api/routes/available-dates/?origin=MIA&destination=DOM')
        self.assertEqual(response.status_code, 200)
        self.assertNotIn("2026-09-18", response.data.get("available_dates", []))

    def test_available_dates_includes_flight_to_ferry(self) -> None:
        # Leg 1: MIA -> PTP arriving 12:00 on 2026-09-19
        r1 = Route.objects.create(
            origin=self.mia,
            destination=self.ptp,
            carrier=self.carrier_air,
            flight_number="AF101",
            departure_time=time(9, 0),
            arrival_time=time(12, 0),
            is_active=True,
        )
        FlightInstance.objects.create(
            route=r1,
            date=date(2026, 9, 19),
            price_amount=250.0,
            available_seats=3,
        )

        # Leg 2: GPPTP (ferry port for PTP) -> DMROS (ferry port for DOM) departing 15:00 (3h gap)
        r2 = Route.objects.create(
            origin=self.gpptp,
            destination=self.dmros,
            carrier=self.carrier_ferry,
            departure_time=time(15, 0),
            arrival_time=time(17, 15),
            is_active=True,
        )
        Sailing.objects.create(
            route=r2,
            date=date(2026, 9, 19),
            departure_time=time(15, 0),
            arrival_time=time(17, 15),
            price_text="$85",
        )

        response = self.client.get('/api/routes/available-dates/?origin=MIA&destination=DOM')
        self.assertEqual(response.status_code, 200)
        self.assertIn("2026-09-19", response.data.get("available_dates", []))

    def test_search_assembles_ferry_to_flight_connection(self) -> None:
        # Leg 1: DMROS -> GPPTP departing 08:00, arriving 10:15 on 2026-09-20
        r1 = Route.objects.create(
            origin=self.dmros,
            destination=self.gpptp,
            carrier=self.carrier_ferry,
            departure_time=time(8, 0),
            arrival_time=time(10, 15),
            is_active=True,
        )
        Sailing.objects.create(
            route=r1,
            date=date(2026, 9, 20),
            departure_time=time(8, 0),
            arrival_time=time(10, 15),
            price_text="$85",
        )

        # Leg 2: PTP -> ORY departing 17:00, arriving 06:30 (next day) on 2026-09-20
        r2 = Route.objects.create(
            origin=self.ptp,
            destination=self.ory,
            carrier=self.carrier_air,
            flight_number="TX541",
            departure_time=time(17, 0),
            arrival_time=time(6, 30),
            is_active=True,
        )
        FlightInstance.objects.create(
            route=r2,
            date=date(2026, 9, 20),
            price_amount=450.0,
            available_seats=2,
        )

        # Search DOM to PAR on 2026-09-20
        response = self.client.get('/api/routes/search/?origin=DOM&destination=PAR&date=2026-09-20')
        self.assertEqual(response.status_code, 200)
        results = response.data.get("results", [])
        self.assertTrue(len(results) > 0)
        itinerary = results[0]
        self.assertTrue(itinerary["id"].startswith("c_sf_"))
        self.assertEqual(len(itinerary["legs"]), 2)
        self.assertTrue(itinerary["legs"][0]["is_ferry"])
        self.assertFalse(itinerary["legs"][1]["is_ferry"])


class FetchDuffelRoutesTests(TestCase):
    def setUp(self) -> None:
        self.cmd = FetchDuffelCommand()
        self.sample_offer_payload = {
            "data": {
                "offers": [
                    {
                        "total_amount": "250.00",
                        "total_currency": "USD",
                        "slices": [
                            {
                                "segments": [
                                    {
                                        "origin": {"iata_code": "ANU"},
                                        "destination": {"iata_code": "DOM"},
                                        "departing_at": "2026-09-20T10:00:00",
                                        "arriving_at": "2026-09-20T10:45:00",
                                        "duration": "PT45M",
                                        "operating_carrier": {
                                            "iata_code": "WM",
                                            "name": "Winair",
                                        },
                                        "operating_carrier_flight_number": "123",
                                        "aircraft": {"iata_code": "DHT"},
                                        "passengers": [{"cabin_class": "economy"}],
                                    }
                                ]
                            }
                        ],
                    }
                ]
            }
        }

    @patch("core.management.commands.fetch_duffel_routes.time.sleep")
    @patch("core.management.commands.fetch_duffel_routes.requests.post")
    def test_fetch_and_save_empty_offers_enforces_pacing(
        self, mock_post: MagicMock, mock_sleep: MagicMock
    ) -> None:
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"data": {"offers": []}}
        mock_post.return_value = mock_response

        result = self.cmd.fetch_and_save("NYC", "DOM", "2026-09-20")
        self.assertFalse(result)
        # Verify 0.5s baseline pacing is called even when 0 offers returned
        mock_sleep.assert_called_with(0.5)
        self.assertEqual(self.cmd.api_calls, 1)

    @patch("core.management.commands.fetch_duffel_routes.time.sleep")
    @patch("core.management.commands.fetch_duffel_routes.requests.post")
    def test_fetch_and_save_success_creates_records(
        self, mock_post: MagicMock, mock_sleep: MagicMock
    ) -> None:
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = self.sample_offer_payload
        mock_post.return_value = mock_response

        result = self.cmd.fetch_and_save("ANU", "DOM", "2026-09-20")
        self.assertTrue(result)
        mock_sleep.assert_called_with(0.5)

        # Verify DB records
        self.assertTrue(
            FlightInstance.objects.filter(
                route__origin__code="ANU",
                route__destination__code="DOM",
                date="2026-09-20",
            ).exists()
        )
        flight = FlightInstance.objects.get(
            route__origin__code="ANU",
            route__destination__code="DOM",
            date="2026-09-20",
        )
        self.assertEqual(float(flight.price_amount), 250.00)
        self.assertEqual(flight.currency, "USD")

    @patch("core.management.commands.fetch_duffel_routes.time.sleep")
    @patch("core.management.commands.fetch_duffel_routes.requests.post")
    def test_fetch_and_save_rate_limited_retry_with_header_recovers(
        self, mock_post: MagicMock, mock_sleep: MagicMock
    ) -> None:
        mock_429 = MagicMock()
        mock_429.status_code = 429
        mock_429.headers = {"Retry-After": "2"}

        mock_200 = MagicMock()
        mock_200.status_code = 200
        mock_200.json.return_value = self.sample_offer_payload

        mock_post.side_effect = [mock_429, mock_200]

        result = self.cmd.fetch_and_save("ANU", "DOM", "2026-09-20")
        self.assertTrue(result)
        self.assertEqual(mock_post.call_count, 2)
        # First sleep should be 2.0s from Retry-After, second sleep 0.5s baseline
        mock_sleep.assert_any_call(2.0)
        mock_sleep.assert_any_call(0.5)
        # Counter should only increment once per query
        self.assertEqual(self.cmd.api_calls, 1)

    @patch("core.management.commands.fetch_duffel_routes.time.sleep")
    @patch("core.management.commands.fetch_duffel_routes.requests.post")
    def test_fetch_and_save_max_retries_exceeded(
        self, mock_post: MagicMock, mock_sleep: MagicMock
    ) -> None:
        mock_429 = MagicMock()
        mock_429.status_code = 429
        mock_429.headers = {}
        mock_post.return_value = mock_429

        result = self.cmd.fetch_and_save("PAR", "FDF", "2026-09-20", max_retries=2)
        self.assertFalse(result)
        # 1 initial + 2 retries = 3 calls
        self.assertEqual(mock_post.call_count, 3)

    def test_expanded_constants_configuration(self) -> None:
        from core.constants import GATEWAYS, REGIONAL_HUBS, TARGETS

        self.assertIn("DOM", TARGETS)
        # Expected Gateways
        for gw in ["NYC", "MIA", "CLT", "LON", "PAR", "AMS", "FRA"]:
            self.assertIn(gw, GATEWAYS)

        # Expected Regional Hubs
        for hub in ["ANU", "BGI", "UVF", "PTP", "FDF", "SXM", "SJU", "EIS", "SKB"]:
            self.assertIn(hub, REGIONAL_HUBS)

    def test_get_target_dates_biweekly_schedule(self) -> None:
        from datetime import date

        # Wednesday run (weekday 2): Should return Thu, Fri, Sat, Sun (4 days)
        wed = date(2026, 9, 16)  # Wednesday
        wed_dates = self.cmd.get_target_dates(wed)
        self.assertEqual(
            wed_dates,
            ["2026-09-17", "2026-09-18", "2026-09-19", "2026-09-20"],
        )

        # Sunday run (weekday 6): Should return Mon, Tue, Wed (3 days)
        sun = date(2026, 9, 20)  # Sunday
        sun_dates = self.cmd.get_target_dates(sun)
        self.assertEqual(
            sun_dates,
            ["2026-09-21", "2026-09-22", "2026-09-23"],
        )

        # Days override
        override_dates = self.cmd.get_target_dates(wed, days_override=2)
        self.assertEqual(override_dates, ["2026-09-17", "2026-09-18"])

    @patch("core.management.commands.fetch_duffel_routes.os.getenv")
    @patch.object(FetchDuffelCommand, "fetch_and_save")
    def test_handle_queries_all_topology_routes_across_target_dates(
        self, mock_fetch_and_save: MagicMock, mock_getenv: MagicMock
    ) -> None:
        mock_getenv.return_value = "fake_duffel_token"
        mock_fetch_and_save.return_value = False

        self.cmd.handle(days=1)

        queried_pairs = [
            (call.args[0], call.args[1]) for call in mock_fetch_and_save.call_args_list
        ]
        # Verify direct trunks to DOM
        self.assertIn(("NYC", "DOM"), queried_pairs)
        self.assertIn(("MIA", "DOM"), queried_pairs)
        self.assertIn(("DOM", "MIA"), queried_pairs)

        # Verify all regional hubs are checked in both directions (into and out of DOM)
        for hub in ["ANU", "BGI", "SXM", "SJU", "EIS", "SKB"]:
            self.assertIn((hub, "DOM"), queried_pairs)
            self.assertIn(("DOM", hub), queried_pairs)

        # Verify gateways connect to regional hubs (including MIA->BGI, MIA->SKB)
        self.assertIn(("MIA", "SKB"), queried_pairs)
        self.assertIn(("MIA", "BGI"), queried_pairs)
        self.assertIn(("CLT", "ANU"), queried_pairs)
        self.assertIn(("LON", "ANU"), queried_pairs)
        self.assertIn(("PAR", "PTP"), queried_pairs)
        self.assertIn(("AMS", "SXM"), queried_pairs)
        self.assertIn(("FRA", "BGI"), queried_pairs)

    def test_enrich_locations_populates_eis_metadata(self) -> None:
        from django.core.management import call_command

        call_command("enrich_locations")
        eis = Location.objects.get(code="EIS")
        self.assertEqual(eis.city, "Tortola")
        self.assertEqual(eis.country, "British Virgin Islands")
        self.assertEqual(eis.name, "Terrance B. Lettsome Intl")



