from django.urls import path
from . import views

app_name = 'plate_scanner'

urlpatterns = [
    path('entrance/', views.entrance_view, name='entrance'),
    path('exit/', views.exit_view, name='exit'),
    path('api/start-scan/', views.start_scan, name='start_scan'),
    path('api/stop-scan/', views.stop_scan, name='stop_scan'),
    path('api/process-entrance/', views.process_entry, name='process_entrance'),
    path('api/process-exit/', views.process_exit, name='process_exit'),
    path('api/parking-status/<str:plate_number>/', views.get_parking_status, name='parking_status'),
    path('api/camera-status/', views.camera_status, name='camera_status'),
    path('api/system-status/', views.system_status, name='system_status'),
    path('api/today-stats/', views.get_today_stats, name='today_stats'),
    path('api/test-camera/', views.test_camera, name='test_camera'),
    
    # Admin views
    path('admin/dashboard/', views.admin_dashboard, name='admin_dashboard'),
    path('admin/payment/<uuid:session_id>/mark-paid/', views.mark_payment_received, name='mark_payment'),
    path('admin/vehicle/<str:plate_number>/', views.vehicle_details, name='vehicle_details'),
]