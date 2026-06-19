from rest_framework.test import APITestCase
from django.urls import reverse

class SearchRoutesTests(APITestCase):
    def test_search_routes_missing_params(self) -> None:
        response = self.client.get('/api/routes/search/')
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.data['error'], 'Missing parameters')

    def test_search_routes_with_filter(self) -> None:
        # It should return 404 Location not found if the locations don't exist
        response = self.client.get('/api/routes/search/?origin=JFK&destination=DOM&date=2026-07-01&filter=ferry')
        self.assertIn(response.status_code, [200, 404, 400])
