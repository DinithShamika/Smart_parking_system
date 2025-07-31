from django.urls import path
from . import views

app_name = 'plate_scanner'

urlpatterns = [
    path('api/latest-scans/', views.api_latest_scans, name='api_latest_scans'),
    path('entrance/', views.entrance_view, name='entrance'),
    path('exit/', views.exit_view, name='exit'),
    path('api/start-scan/', views.start_scan, name='start_scan'),
    path('api/stop-scan/', views.stop_scan, name='stop_scan'),
    path('api/process-entrance/', views.process_entry, name='process_entrance'),
    path('api/process-exit/', views.process_exit, name='process_exit'),
    path('api/quick-scan/', views.quick_scan, name='quick_scan'),
    path('api/real-time-scan/', views.real_time_scan, name='real_time_scan'),
    path('api/parking-status/<str:plate_number>/', views.get_parking_status, name='parking_status'),
    path('api/camera-status/', views.camera_status, name='camera_status'),
    path('api/system-status/', views.system_status, name='system_status'),
    path('api/today-stats/', views.get_today_stats, name='today_stats'),
    path('api/test-camera/', views.test_camera, name='test_camera'),
    
    # Admin views
    path('admin/dashboard/', views.admin_dashboard, name='admin_dashboard'),
    path('admin/payment/<uuid:session_id>/mark-paid/', views.mark_payment_received, name='mark_payment'),
    path('admin/vehicle/<str:plate_number>/', views.vehicle_details, name='vehicle_details'),
    path('qr-scanner/', views.qr_scanner_view, name='qr_scanner'),
    path('qr-scanner/entrance/', views.qr_scanner_entrance_view, name='qr_scanner_entrance'),
    path('qr-scanner/exit/', views.qr_scanner_exit_view, name='qr_scanner_exit'),
]