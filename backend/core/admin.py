from django.contrib import admin
from .models import Location, Carrier, Route


@admin.register(Location)
class LocationAdmin(admin.ModelAdmin):
    list_display = ('code', 'name', 'city', 'country', 'location_type')
    search_fields = ('code', 'name')


@admin.register(Carrier)
class CarrierAdmin(admin.ModelAdmin):
    list_display = ('name', 'code', 'carrier_type')
    list_filter = ('carrier_type',)
    search_fields = ('name', 'code')


@admin.register(Route)
class RouteAdmin(admin.ModelAdmin):
    list_display = ('carrier', 'origin', 'destination', 'is_active')
    autocomplete_fields = ['origin', 'destination', 'carrier']
