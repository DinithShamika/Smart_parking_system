from django.urls import path
from . import views

app_name = 'booking'

urlpatterns = [
    path('', views.home, name='home'),
    
    # Authentication URLs
    path('admin-registration/', views.admin_registration, name='admin_registration'),
    path('admin-login/', views.admin_login, name='admin_login'),
    path('driver-registration/', views.driver_user_registration, name='driver_user_registration'),
    path('driver-login/', views.driver_login, name='driver_login'),
    path('logout/', views.logout, name='logout'),
    
    # Dashboard URLs
    path('driver-dashboard/', views.driver_dashboard, name='driver_dashboard'),
    path('admin-dashboard/', views.admin_dashboard, name='admin_dashboard'),
    
    # Booking URLs
    path('registered-driver-booking/', views.registered_driver_booking, name='registered_driver_booking'),
    path('temporary-booking/', views.temporary_booking, name='temporary_booking'),
    path('driver-registration-old/', views.driver_registration, name='driver_registration'),
    path('select-slot/', views.select_slot, name='select_slot'),
    path('confirm-booking/<int:slot_id>/', views.confirm_booking, name='confirm_booking'),
    path('booking-success/<uuid:booking_id>/', views.booking_success, name='booking_success'),
    path('registration-success/', views.registration_success, name='registration_success'),
    path('login/', views.login_view, name='login'),
    path('delete-booking/<uuid:booking_id>/', views.delete_booking, name='delete_booking'),
    path('update-fee/<uuid:booking_id>/', views.update_fee, name='update_fee'),
    path('update-free/<uuid:booking_id>/', views.update_free, name='update_free'),
]