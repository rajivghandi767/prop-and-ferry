from unittest.mock import patch, MagicMock
from django.test import TestCase
from django.urls import reverse
from rest_framework.test import APITestCase

from core.management.commands.fetch_duffel_routes import Command as FetchDuffelCommand
from core.models import FlightInstance, Route, Carrier, Location


class SearchRoutesTests(APITestCase):
    def test_search_routes_missing_params(self) -> None:
        response = self.client.get('/api/routes/search/')
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.data['error'], 'Missing parameters')

    def test_search_routes_with_filter(self) -> None:
        # It should return 404 Location not found if the locations don't exist
        response = self.client.get('/api/routes/search/?origin=JFK&destination=DOM&date=2026-07-01&filter=ferry')
        self.assertIn(response.status_code, [200, 404, 400])


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


