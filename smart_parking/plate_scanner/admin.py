from django.contrib import admin
from .models import Vehicle, ScanRecord, ParkingSession, ParkingRate

@admin.register(Vehicle)
class VehicleAdmin(admin.ModelAdmin):
    list_display = ['plate_number', 'is_registered', 'registered_at']
    list_filter = ['is_registered', 'registered_at']
    search_fields = ['plate_number']
    ordering = ['-registered_at']


@admin.register(ScanRecord)
class ScanRecordAdmin(admin.ModelAdmin):
    list_display = ['vehicle', 'scan_type', 'timestamp', 'confidence_score', 'image']
    list_filter = ['scan_type', 'timestamp']
    search_fields = ['vehicle__plate_number']
    readonly_fields = ['confidence_score']
    ordering = ['-timestamp']
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related('vehicle', 'parking_session')

@admin.register(ParkingRate)
class ParkingRateAdmin(admin.ModelAdmin):
    list_display = ['name', 'first_hour_rate', 'subsequent_hour_rate', 'max_daily_rate', 'is_active']
    list_filter = ['is_active', 'created_at']
    ordering = ['-created_at']


    