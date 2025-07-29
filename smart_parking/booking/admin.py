from django.contrib import admin
from .models import Category, Slot, Booking, Admin, DriverUser

@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ('name', 'created_at')
    search_fields = ('name',)

@admin.register(Slot)
class SlotAdmin(admin.ModelAdmin):
    list_display = ('slot_number', 'category', 'is_available')
    list_filter = ('category', 'is_available')
    search_fields = ('slot_number',)
    list_editable = ('is_available',)

@admin.register(Booking)
class BookingAdmin(admin.ModelAdmin):
    list_display = ('booking_id', 'driver_name', 'vehicle_no', 'slot', 'booking_time')
    list_filter = ('slot__category', 'booking_time')
    search_fields = ('driver_name', 'vehicle_no')
    readonly_fields = ('booking_id', 'qr_code')

@admin.register(Admin)
class AdminAdmin(admin.ModelAdmin):
    list_display = ('name', 'username', 'email', 'created_at')
    search_fields = ('name', 'username', 'email')
    readonly_fields = ('created_at',)

@admin.register(DriverUser)
class DriverUserAdmin(admin.ModelAdmin):
    list_display = ('name', 'username', 'email', 'vehicle_no', 'vehicle_type', 'created_at')
    search_fields = ('name', 'username', 'email', 'vehicle_no')
    list_filter = ('vehicle_type', 'created_at')
    readonly_fields = ('created_at',)