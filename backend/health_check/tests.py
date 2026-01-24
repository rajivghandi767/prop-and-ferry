import pytest
from django.urls import reverse

@pytest.mark.django_db
def test_health_check(client):
    url = reverse('health_check') # Assuming the URL name is 'health_check'. I should verify or just use the path.
    # To be safe and avoid name lookup errors if I'm wrong about the name, I'll use the path '/health/' as seen in docker-compose.
    response = client.get('/health/') 
    assert response.status_code == 200
