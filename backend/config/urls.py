from django.contrib import admin
from django.urls import path, include
from django.conf.urls.static import static
from django.conf import settings
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from django.views.decorators.cache import cache_control
from rest_framework.routers import DefaultRouter

from core.views import LocationViewSet, RouteViewSet, CarrierViewSet, SailingViewSet

# Import health check views
from health_check.views import health_detailed, health_simple


@require_http_methods(["GET"])
@cache_control(max_age=300)
def api_root(request):
    """
    API Endpoint List
    """
    base_url = request.build_absolute_uri('/')

    return JsonResponse({
        "message": "Port & Ferry Web App API",
        "status": "running",
        "version": "1.0",
        "api_url": f"{base_url}api/",
        "endpoints": {
            "admin": f"{base_url}admin/",
            "api": f"{base_url}api/",
            "health": f"{base_url}health/",
        }
    })


router = DefaultRouter()

# Register viewsets
router.register(r'locations', LocationViewSet, basename='location')
router.register(r'carriers', CarrierViewSet, basename='carrier')
router.register(r'routes', RouteViewSet, basename='route')
# Added this for completeness
router.register(r'sailings', SailingViewSet, basename='sailing')

# URL patterns
urlpatterns = [
    # Root API Endpoint
    path('', api_root, name='api-root'),

    # API Routes (Router now handles 'api/routes/search/')
    path('api/', include(router.urls)),

    # Admin Interface
    path('admin/', admin.site.urls),

    # DRF Authentication
    path('api-auth/', include('rest_framework.urls', namespace='rest_framework')),

    # Health Check Endpoints
    path('health/', health_simple, name='health_simple'),
    path('health/detailed/', health_detailed, name='health_detailed'),

    # Third-Party App URLs
    path('', include('django_prometheus.urls')),   # Prometheus Monitoring
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL,
                          document_root=settings.MEDIA_ROOT)
    urlpatterns += static(settings.STATIC_URL,
                          document_root=settings.STATIC_ROOT)
else:
    urlpatterns += static(settings.MEDIA_URL,
                          document_root=settings.MEDIA_ROOT)
    urlpatterns += static(settings.STATIC_URL,
                          document_root=settings.STATIC_ROOT)
