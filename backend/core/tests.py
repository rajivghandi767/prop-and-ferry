from unittest.mock import patch, MagicMock
from datetime import date, datetime, time, timezone
import requests
from django.core.cache import cache
from django.core.management import call_command
from django.core.management.base import CommandError
from django.test import TestCase, override_settings
from django.urls import reverse
from rest_framework.test import APITestCase

from core.management.commands.fetch_duffel_routes import Command as FetchDuffelCommand
from core.management.commands.run_scheduler import (
    _USEasternTZ,
    compute_next_run,
    execute_pipeline_once,
    post_discord_alert,
)
from core.models import FlightInstance, Route, Carrier, Location, Sailing, ReportedIssue
from core.views import get_sliding_window


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

    def test_search_routes_includes_sold_out_itinerary(self) -> None:
        carrier = Carrier.objects.create(code="AA", name="American Airlines", carrier_type="AIR")

        route = Route.objects.create(
            origin=self.mia,
            destination=self.dom,
            carrier=carrier,
            flight_number="AA 3774",
            departure_time=time(10, 0),
            arrival_time=time(14, 0),
            is_active=True,
        )

        FlightInstance.objects.create(
            route=route,
            date=date(2026, 9, 25),
            available_seats=0,
            price_amount=None,
            cabin_class="Sold Out",
        )

        response = self.client.get('/api/routes/search/?origin=MIA&destination=DOM&date=2026-09-25')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data.get("results", [])), 1)
        itinerary = response.data["results"][0]
        self.assertTrue(itinerary.get("is_sold_out"))
        self.assertEqual(itinerary["legs"][0]["price_text"], "Sold Out")
        self.assertEqual(itinerary["legs"][0]["available_seats"], 0)

    def test_locations_excludes_child_ferry_terminals(self) -> None:
        response = self.client.get("/api/locations/")
        self.assertEqual(response.status_code, 200)
        codes = {loc["code"] for loc in response.data}
        self.assertIn("DOM", codes)
        self.assertIn("PTP", codes)
        self.assertIn("ORY", codes)
        # Child PRT terminals with a parent airport are filtered out on the server
        self.assertNotIn("DMROS", codes)
        self.assertNotIn("GPPTP", codes)

    def test_reports_endpoint_is_post_only_and_read_only_fields_protected(self) -> None:
        get_res = self.client.get("/api/reports/")
        self.assertEqual(get_res.status_code, 405)

        with patch.object(ReportedIssue, "send_notifications") as mock_notify:
            post_res = self.client.post(
                "/api/reports/",
                {
                    "issue_type": "routing_error",
                    "user_note": "Test report",
                    "resolved": True,
                },
                format="json",
            )
            self.assertEqual(post_res.status_code, 201)
            mock_notify.assert_called_once()
            issue = ReportedIssue.objects.get(pk=post_res.data["id"])
            self.assertFalse(issue.resolved)

    def test_sliding_window_matches_wed_sun_schedule(self) -> None:
        # Wednesday 2026-09-16 -> window is Thu 2026-09-17 .. Sun 2026-09-20
        w_start, w_end = get_sliding_window(date(2026, 9, 16))
        self.assertEqual(w_start, date(2026, 9, 17))
        self.assertEqual(w_end, date(2026, 9, 20))

        # Sunday 2026-09-20 -> window is Mon 2026-09-21 .. Wed 2026-09-23
        s_start, s_end = get_sliding_window(date(2026, 9, 20))
        self.assertEqual(s_start, date(2026, 9, 21))
        self.assertEqual(s_end, date(2026, 9, 23))

    def test_search_routes_without_date_auto_resolves_date(self) -> None:
        response = self.client.get("/api/routes/search/?origin=MIA&destination=DOM")
        self.assertEqual(response.status_code, 200)
        self.assertIn("found_date", response.data)
        self.assertIn("available_dates", response.data)
        self.assertIn("window_start", response.data)
        self.assertIn("window_end", response.data)


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
        assert flight.price_amount is not None
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
        self.assertIn(("MIA", "DOM"), queried_pairs)
        self.assertIn(("DOM", "MIA"), queried_pairs)

        # Verify active regional hubs are checked in both directions (EIS pruned)
        for hub in ["ANU", "BGI", "SXM", "SJU", "SKB"]:
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
        self.assertNotIn(("MIA", "EIS"), queried_pairs)
        self.assertNotIn(("EIS", "DOM"), queried_pairs)

    def test_enrich_locations_populates_eis_metadata(self) -> None:
        from django.core.management import call_command

        call_command("enrich_locations")
        eis = Location.objects.get(code="EIS")
        self.assertEqual(eis.city, "Tortola")
        self.assertEqual(eis.country, "British Virgin Islands")
        self.assertEqual(eis.name, "Terrance B. Lettsome Intl")

    @patch("core.management.commands.fetch_duffel_routes.time.sleep")
    @patch("core.management.commands.fetch_duffel_routes.requests.post")
    def test_fetch_and_save_empty_offers_marks_known_route_sold_out(
        self, mock_post: MagicMock, mock_sleep: MagicMock
    ) -> None:
        # Wednesday date (2026-09-16 is ISO weekday 3)
        target_date_str = "2026-09-16"
        target_date = date(2026, 9, 16)

        carrier = Carrier.objects.create(code="UA", name="United Airlines", carrier_type="AIR")
        ewr = Location.objects.create(code="EWR", name="Newark Liberty", city="Newark", country="USA")
        dom = Location.objects.create(code="DOM", name="Douglas-Charles", city="Marigot", country="Dominica")

        # Existing verified route operating on Wednesday (3) and Saturday (6)
        route = Route.objects.create(
            origin=ewr,
            destination=dom,
            carrier=carrier,
            flight_number="UA 1234",
            departure_time=time(8, 45),
            arrival_time=time(14, 17),
            days_of_operation="36",
            is_active=True,
        )

        # Duffel returns 200 with 0 offers (sold out)
        mock_res = MagicMock()
        mock_res.status_code = 200
        mock_res.json.return_value = {"data": {"offers": []}}
        mock_post.return_value = mock_res

        result = self.cmd.fetch_and_save("EWR", "DOM", target_date_str)
        self.assertTrue(result)

        # Verify a FlightInstance was created with available_seats=0 and "Sold Out"
        instance = FlightInstance.objects.filter(route=route, date=target_date).first()
        self.assertIsNotNone(instance)
        assert instance is not None
        self.assertEqual(instance.available_seats, 0)
        self.assertIsNone(instance.price_amount)
        self.assertEqual(instance.cabin_class, "Sold Out")


class PipelineAndSchedulerTests(TestCase):
    @patch.dict("os.environ", {"DUFFEL_ACCESS_TOKEN": ""}, clear=False)
    def test_fetch_duffel_routes_requires_token(self) -> None:
        with self.assertRaises(CommandError):
            call_command("fetch_duffel_routes", days=1)

    @override_settings(DISCORD_DATAPIPES_WEBHOOK_URL="https://discord.example.com/datapipes")
    @patch("core.management.commands.notify_unenriched.requests.post")
    def test_notify_unenriched_posts_to_datapipes_webhook(
        self, mock_post: MagicMock
    ) -> None:
        Location.objects.create(code="XYZ", name="XYZ Airport", city="")
        Carrier.objects.create(code="ZZ", name="Airline ZZ", carrier_type="AIR")
        mock_resp = MagicMock()
        mock_post.return_value = mock_resp

        call_command("notify_unenriched")

        mock_post.assert_called_once()
        self.assertEqual(
            mock_post.call_args.args[0], "https://discord.example.com/datapipes"
        )
        payload = mock_post.call_args.kwargs["json"]
        self.assertEqual(payload["allowed_mentions"], {"parse": []})
        mock_resp.raise_for_status.assert_called_once()

    def test_compute_next_run_selects_wed_and_sun_et(self) -> None:
        # Mon Nov 16 2026 -> Wed Nov 18 02:30 EST == 07:30 UTC
        mon_utc = datetime(2026, 11, 16, 12, 0, tzinfo=timezone.utc)
        self.assertEqual(
            compute_next_run(mon_utc),
            datetime(2026, 11, 18, 7, 30, tzinfo=timezone.utc),
        )

        # Wed Nov 18 02:35 EST == 07:35 UTC -> Sun Nov 22 02:30 EST == 07:30 UTC
        wed_after_utc = datetime(2026, 11, 18, 7, 35, tzinfo=timezone.utc)
        self.assertEqual(
            compute_next_run(wed_after_utc),
            datetime(2026, 11, 22, 7, 30, tzinfo=timezone.utc),
        )

        # Sun Jul 5 2026 01:00 EDT == 05:00 UTC -> same day 02:30 EDT == 06:30 UTC
        sun_edt_utc = datetime(2026, 7, 5, 5, 0, tzinfo=timezone.utc)
        self.assertEqual(
            compute_next_run(sun_edt_utc),
            datetime(2026, 7, 5, 6, 30, tzinfo=timezone.utc),
        )

    def test_us_eastern_fallback_dst_names(self) -> None:
        tz = _USEasternTZ()
        self.assertEqual(
            datetime(2026, 1, 15, 12, 0, tzinfo=timezone.utc).astimezone(tz).tzname(),
            "EST",
        )
        self.assertEqual(
            datetime(2026, 7, 15, 12, 0, tzinfo=timezone.utc).astimezone(tz).tzname(),
            "EDT",
        )

    @patch("core.management.commands.run_scheduler.requests.post")
    def test_execute_pipeline_once_posts_success_and_failure_embeds(
        self, mock_post: MagicMock
    ) -> None:
        mock_post.return_value = MagicMock()
        calls: list[str] = []
        times = iter(
            [
                datetime(2026, 11, 18, 7, 30, 0, tzinfo=timezone.utc),
                datetime(2026, 11, 18, 7, 32, 5, tzinfo=timezone.utc),
            ]
        )

        execute_pipeline_once(
            scheduled_utc=datetime(2026, 11, 18, 7, 30, 0, tzinfo=timezone.utc),
            runner=lambda name: calls.append(name),
            now_fn=lambda: next(times),
            webhook_url="https://discord.example.com/datapipes",
        )
        self.assertEqual(
            calls, ["fetch_duffel_routes", "notify_unenriched", "scrape_ferries"]
        )
        ok_embed = mock_post.call_args.kwargs["json"]["embeds"][0]
        self.assertEqual(ok_embed["title"], "✅ Prop & Ferry Data Pipeline Complete")
        self.assertEqual(ok_embed["color"], 3066993)

        def fail_on_scrape(name: str) -> None:
            if name == "scrape_ferries":
                raise CommandError("FRS HTTP 503")

        fail_times = iter(
            [
                datetime(2026, 11, 18, 7, 30, 0, tzinfo=timezone.utc),
                datetime(2026, 11, 18, 7, 30, 9, tzinfo=timezone.utc),
            ]
        )
        with self.assertRaises(CommandError):
            execute_pipeline_once(
                scheduled_utc=datetime(2026, 11, 18, 7, 30, 0, tzinfo=timezone.utc),
                runner=fail_on_scrape,
                now_fn=lambda: next(fail_times),
                webhook_url="https://discord.example.com/datapipes",
            )
        fail_embed = mock_post.call_args.kwargs["json"]["embeds"][0]
        self.assertEqual(fail_embed["title"], "🚨 Prop & Ferry Data Pipeline Alert")
        self.assertEqual(fail_embed["color"], 15158332)
        self.assertIn("scrape_ferries", fail_embed["description"])
        self.assertIn("FRS HTTP 503", fail_embed["description"])

    @patch("core.management.commands.run_scheduler.requests.post")
    def test_post_discord_alert_handles_request_exception(
        self, mock_post: MagicMock
    ) -> None:
        mock_post.side_effect = requests.RequestException("network unreachable")
        self.assertFalse(
            post_discord_alert(
                "https://discord.example.com/datapipes",
                title="test",
                description="desc",
                color=123,
                timestamp_iso="2026-11-18T07:30:00Z",
            )
        )



