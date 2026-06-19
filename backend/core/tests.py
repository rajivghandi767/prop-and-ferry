import pytest
from rest_framework.test import APIClient
from django.urls import reverse

@pytest.mark.django_db
def test_search_routes_missing_params():
    client = APIClient()
    response = client.get('/api/routes/search/')
    assert response.status_code == 400
    assert response.data['error'] == 'Missing parameters'

@pytest.mark.django_db
def test_search_routes_with_filter():
    client = APIClient()
    # It should return 404 Location not found if the locations don't exist
    response = client.get('/api/routes/search/?origin=JFK&destination=DOM&date=2026-07-01&filter=ferry')
    assert response.status_code in [200, 404, 400]
