from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from django.views.decorators.csrf import csrf_exempt
from django.db import connection
from django.core.cache import cache
from django.conf import settings
import time
import os


@csrf_exempt
@require_http_methods(["GET"])
def health_detailed(request):
    """
    Comprehensive health check for production monitoring
    """
    health_data = {
        "status": "healthy",
        "timestamp": time.time(),
        "service": "portfolio-backend",
        "checks": {}
    }

    overall_status = 200

    # Database check
    try:
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1")
            cursor.fetchone()
        health_data["checks"]["database"] = {"status": "healthy"}
    except Exception as e:
        health_data["checks"]["database"] = {
            "status": "unhealthy", "error": str(e)}
        overall_status = 503

    # Static files check
    try:
        static_root = getattr(settings, 'STATIC_ROOT', None)
        if static_root and os.path.exists(static_root):
            health_data["checks"]["static_files"] = {"status": "healthy"}
        else:
            health_data["checks"]["static_files"] = {
                "status": "warning", "message": "static files not found"}
    except Exception as e:
        health_data["checks"]["static_files"] = {
            "status": "unhealthy", "error": str(e)}

    # Set overall status
    if overall_status != 200:
        health_data["status"] = "unhealthy"

    return JsonResponse(health_data, status=overall_status)


@csrf_exempt
@require_http_methods(["GET"])
def health_simple(request):
    """
    Simple health check for load balancers
    """
    return JsonResponse({"status": "ok"}, status=200)
