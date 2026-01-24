from django.contrib import admin
from django.urls import path, include
from django.conf.urls.static import static
from django.conf import settings
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from django.views.decorators.cache import cache_control
from django.utils.decorators import method_decorator
from rest_framework.routers import DefaultRouter

# Import viewsets


# Import health check views
from health_check.views import health_detailed, health_simple


@require_http_methods(["GET"])
@cache_control(max_age=300)  # Cache for 5 minutes
def api_root(request):
    """
    API Endpoint List
    """
    base_url = request.build_absolute_uri('/')

    return JsonResponse({
        "message": "Portfolio API",
        "status": "running",
        "version": "1.0",
        "api_url": f"{base_url}api/",
        "endpoints": {
            "admin": f"{base_url}admin/",
            "api": f"{base_url}api/",
            "auth": f"{base_url}api-auth/",

        }
    })


router = DefaultRouter()

# Register viewsets with explicit basename for better URL naming


# URL patterns
urlpatterns = [
    # Root API Endpoint
    path('', api_root, name='api-root'),

    # API Routes
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

# Static and media file serving fallback
if settings.DEBUG:
    # Development: Serve media files through Django
    urlpatterns += static(settings.MEDIA_URL,
                          document_root=settings.MEDIA_ROOT)
    urlpatterns += static(settings.STATIC_URL,
                          document_root=settings.STATIC_ROOT)
else:
    # Production: Add media and static URL patterns for URL resolution.
    # Nginx will serve the files, but Django needs to be aware of the URLs.
    urlpatterns += static(settings.MEDIA_URL,
                          document_root=settings.MEDIA_ROOT)
    urlpatterns += static(settings.STATIC_URL,
                          document_root=settings.STATIC_ROOT)
