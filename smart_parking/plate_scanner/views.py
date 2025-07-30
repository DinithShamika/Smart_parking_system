from django.shortcuts import render, redirect
from django.http import JsonResponse
from django.contrib.auth.decorators import login_required
from django.contrib.admin.views.decorators import staff_member_required
from django.db.models import Sum, Count
from django.utils import timezone
from datetime import datetime, timedelta
from .scanner import PlateScanner
import base64
import numpy as np
from plate_scanner.models import Vehicle, ScanRecord, ParkingSession, ParkingRate
from booking.models import Booking
from django.views.decorators.csrf import csrf_exempt
import traceback
import logging

logger = logging.getLogger(__name__)
scanner = PlateScanner()

def entrance_view(request):
    return render(request, 'plate_scanner/entrance.html')

def exit_view(request):
    return render(request, 'plate_scanner/exit.html')

def qr_scanner_view(request):
    """View for QR code scanner page"""
    return render(request, 'plate_scanner/qr_scanner.html')

@csrf_exempt
def start_scan(request):
    if request.method == 'POST':
        try:
            success = scanner.start_camera()
            if success:
                return JsonResponse({
                    'success': True, 
                    'message': f'Number plate scanner started successfully on camera {scanner.camera_index}',
                    'camera_index': scanner.camera_index,
                    'scan_mode': 'fast-simple'
                })
            else:
                error_message = scanner.get_camera_error() or 'Failed to start camera. Please check camera permissions and try again.'
                return JsonResponse({
                    'success': False, 
                    'message': error_message
                })
        except Exception as e:
            logger.error(f"Error starting scanner: {e}")
            logger.error(traceback.format_exc())
            return JsonResponse({
                'success': False, 
                'message': f'Camera error: {str(e)}'
            })

@csrf_exempt
def stop_scan(request):
    if request.method == 'POST':
        try:
            scanner.stop_camera()
            return JsonResponse({'success': True, 'message': 'Number plate scanner stopped'})
        except Exception as e:
            logger.error(f"Error stopping scanner: {e}")
            return JsonResponse({'success': False, 'message': str(e)})

@csrf_exempt
def process_scan(request, scan_type):
    if request.method == 'POST':
        try:
            # Check if camera is working
            if not scanner.scanning or not scanner.camera:
                return JsonResponse({
                    'status': 'error', 
                    'message': 'Camera not started. Please start the number plate scanner first.'
                })
            
            # Process frame for text detection
            frame, texts = scanner.process_frame()
            
            if frame is None:
                return JsonResponse({
                    'status': 'error', 
                    'message': 'Cannot read from camera. Please check camera connection.'
                })
            
            if texts:
                # Get the best detected text
                text_info = texts[0]
                detected_text = text_info['text']
                confidence = text_info['confidence']
                
                if scanner.save_scan(frame, detected_text, scan_type, confidence):
                    # Get additional info for response
                    response_data = {
                        'status': 'success',
                        'text': detected_text,
                        'confidence': confidence,
                        'scan_type': scan_type,
                        'timestamp': datetime.now().isoformat(),
                        'scan_mode': 'fast-simple'
                    }
                    
                    # Check if vehicle is registered
                    try:
                        booking = Booking.objects.filter(vehicle_no=detected_text).first()
                        if booking:
                            response_data['is_registered'] = True
                            response_data['driver_name'] = booking.driver_name
                            response_data['slot_number'] = booking.slot.slot_number
                        else:
                            response_data['is_registered'] = False
                    except Exception as e:
                        logger.error(f"Error checking booking: {e}")
                        response_data['is_registered'] = False
                    
                    # For exit scans, include payment info
                    if scan_type == 'EXIT':
                        try:
                            parking_session = ParkingSession.objects.filter(
                                vehicle__plate_number=detected_text,
                                is_active=False
                            ).order_by('-exit_time').first()
                            
                            if parking_session:
                                response_data['amount_due'] = str(parking_session.total_amount)
                                response_data['duration'] = str(parking_session.exit_time - parking_session.entry_time)
                        except Exception as e:
                            logger.error(f"Error getting payment info: {e}")
                    
                    return JsonResponse(response_data)
                else:
                    return JsonResponse({
                        'status': 'error', 
                        'message': 'Failed to save scan record'
                    })
            
            return JsonResponse({'status': 'no_text', 'message': 'No number plate detected'})
        except Exception as e:
            logger.error(f"Error processing scan: {e}")
            logger.error(traceback.format_exc())
            return JsonResponse({
                'status': 'error', 
                'message': f'Processing error: {str(e)}'
            })

@csrf_exempt
def process_entry(request):
    return process_scan(request, 'ENTRY')

@csrf_exempt
def process_exit(request):
    return process_scan(request, 'EXIT')

@csrf_exempt
def quick_scan(request):
    """Fast scanning endpoint for immediate number plate detection"""
    if request.method == 'POST':
        try:
            # Check if camera is working
            if not scanner.scanning or not scanner.camera:
                return JsonResponse({
                    'status': 'error', 
                    'message': 'Camera not started'
                })
            
            # Fast scan (0.5 second timeout)
            frame, text_info = scanner.scan_until_text(timeout=0.5)
            
            if frame is None:
                return JsonResponse({
                    'status': 'error', 
                    'message': 'Camera error'
                })
            
            if text_info:
                detected_text = text_info['text']
                confidence = text_info['confidence']
                
                return JsonResponse({
                    'status': 'success',
                    'text': detected_text,
                    'confidence': confidence,
                    'timestamp': datetime.now().isoformat(),
                    'scan_mode': 'fast-simple'
                })
            
            return JsonResponse({'status': 'no_text'})
            
        except Exception as e:
            logger.error(f"Error in quick scan: {e}")
            return JsonResponse({
                'status': 'error', 
                'message': str(e)
            })

@csrf_exempt
def real_time_scan(request):
    """Real-time scanning endpoint"""
    if request.method == 'POST':
        try:
            # Check if camera is working
            if not scanner.scanning or not scanner.camera:
                return JsonResponse({
                    'status': 'error', 
                    'message': 'Camera not started'
                })
            
            # Process frame
            frame, texts = scanner.process_frame()
            
            if frame is None:
                return JsonResponse({
                    'status': 'error', 
                    'message': 'Camera error'
                })
            
            if texts:
                # Return all detected texts
                detected_texts = []
                for text_info in texts:
                    detected_texts.append({
                        'text': text_info['text'],
                        'confidence': text_info['confidence']
                    })
                
                return JsonResponse({
                    'status': 'success',
                    'texts': detected_texts,
                    'timestamp': datetime.now().isoformat(),
                    'scan_mode': 'fast-simple'
                })
            
            return JsonResponse({'status': 'no_text'})
            
        except Exception as e:
            logger.error(f"Error in real-time scan: {e}")
            return JsonResponse({
                'status': 'error', 
                'message': str(e)
            })

@staff_member_required
def admin_dashboard(request):
    """Admin dashboard showing parking statistics and payments"""
    
    # Get date range for filtering
    today = timezone.now().date()
    start_date = request.GET.get('start_date', today.strftime('%Y-%m-%d'))
    end_date = request.GET.get('end_date', today.strftime('%Y-%m-%d'))
    
    try:
        start_date = datetime.strptime(start_date, '%Y-%m-%d').date()
        end_date = datetime.strptime(end_date, '%Y-%m-%d').date()
    except ValueError:
        start_date = today
        end_date = today
    
    # Get parking sessions for the date range
    sessions = ParkingSession.objects.filter(
        entry_time__date__range=[start_date, end_date]
    )
    
    # Calculate statistics
    total_sessions = sessions.count()
    active_sessions = sessions.filter(is_active=True).count()
    completed_sessions = sessions.filter(is_active=False).count()
    total_revenue = sessions.filter(is_paid=True).aggregate(
        total=Sum('total_amount')
    )['total'] or 0
    pending_payments = sessions.filter(is_active=False, is_paid=False).aggregate(
        total=Sum('total_amount')
    )['total'] or 0
    
    # Get recent activities
    recent_scans = ScanRecord.objects.select_related('vehicle', 'parking_session').order_by('-timestamp')[:10]
    
    # Get vehicles currently parked
    currently_parked = ParkingSession.objects.filter(
        is_active=True
    ).select_related('vehicle').order_by('-entry_time')
    
    # Get payment history
    payment_history = ParkingSession.objects.filter(
        is_paid=True
    ).select_related('vehicle').order_by('-payment_time')[:20]
    
    context = {
        'start_date': start_date,
        'end_date': end_date,
        'total_sessions': total_sessions,
        'active_sessions': active_sessions,
        'completed_sessions': completed_sessions,
        'total_revenue': total_revenue,
        'pending_payments': pending_payments,
        'recent_scans': recent_scans,
        'currently_parked': currently_parked,
        'payment_history': payment_history,
        'now': timezone.now(),
    }
    
    return render(request, 'plate_scanner/admin_dashboard.html', context)

@staff_member_required
def mark_payment_received(request, session_id):
    """Mark a parking session as paid"""
    if request.method == 'POST':
        try:
            session = ParkingSession.objects.get(session_id=session_id)
            session.is_paid = True
            session.payment_time = timezone.now()
            session.save()
            logger.info(f"Payment marked as received for session {session_id}")
            return JsonResponse({'status': 'success'})
        except ParkingSession.DoesNotExist:
            return JsonResponse({'status': 'error', 'message': 'Session not found'})
    
    return JsonResponse({'status': 'error', 'message': 'Invalid request'})

@staff_member_required
def vehicle_details(request, plate_number):
    """Get detailed information about a specific vehicle"""
    try:
        vehicle = Vehicle.objects.get(plate_number=plate_number)
        parking_sessions = ParkingSession.objects.filter(vehicle=vehicle).order_by('-entry_time')
        scan_records = ScanRecord.objects.filter(vehicle=vehicle).order_by('-timestamp')
        booking = Booking.objects.filter(vehicle_no=plate_number).first()
        
        context = {
            'vehicle': vehicle,
            'parking_sessions': parking_sessions,
            'scan_records': scan_records,
            'booking': booking,
        }
        
        return render(request, 'plate_scanner/vehicle_details.html', context)
    except Vehicle.DoesNotExist:
        return JsonResponse({'status': 'error', 'message': 'Vehicle not found'})

def get_parking_status(request, plate_number):
    """API endpoint to get parking status for a vehicle"""
    try:
        status = scanner.get_parking_status(plate_number)
        return JsonResponse(status)
    except Exception as e:
        logger.error(f"Error getting parking status: {e}")
        return JsonResponse({'status': 'error', 'message': str(e)})

def camera_status(request):
    """Check camera status and return available cameras"""
    try:
        working_cameras = []
        camera_details = []
        
        for i in range(4):
            try:
                import cv2
                cap = cv2.VideoCapture(i)
                if cap.isOpened():
                    ret, frame = cap.read()
                    if ret and frame is not None:
                        working_cameras.append(i)
                        camera_details.append({
                            'index': i,
                            'resolution': f"{frame.shape[1]}x{frame.shape[0]}",
                            'channels': frame.shape[2] if len(frame.shape) > 2 else 1
                        })
                    cap.release()
            except Exception as e:
                logger.error(f"Error testing camera {i}: {e}")
                continue
        
        return JsonResponse({
            'status': 'success',
            'working_cameras': working_cameras,
            'camera_details': camera_details,
            'current_camera': scanner.camera_index if scanner.camera else None,
            'scanner_status': 'active' if scanner.scanning else 'inactive',
            'scan_mode': 'fast-simple'
        })
    except Exception as e:
        logger.error(f"Error checking camera status: {e}")
        return JsonResponse({
            'status': 'error',
            'message': str(e)
        })

def system_status(request):
    """Get comprehensive system status"""
    try:
        # Get scanner status
        scanner_status = scanner.get_system_status()
        
        # Get database statistics
        total_vehicles = Vehicle.objects.count()
        total_scans = ScanRecord.objects.count()
        active_sessions = ParkingSession.objects.filter(is_active=True).count()
        
        # Get today's statistics
        today = timezone.now().date()
        today_scans = ScanRecord.objects.filter(timestamp__date=today).count()
        today_sessions = ParkingSession.objects.filter(entry_time__date=today).count()
        today_revenue = ParkingSession.objects.filter(
            payment_time__date=today,
            is_paid=True
        ).aggregate(total=Sum('total_amount'))['total'] or 0
        
        status = {
            'scanner': scanner_status,
            'database': {
                'total_vehicles': total_vehicles,
                'total_scans': total_scans,
                'active_sessions': active_sessions,
                'today_scans': today_scans,
                'today_sessions': today_sessions,
                'today_revenue': float(today_revenue)
            },
            'system': {
                'timestamp': timezone.now().isoformat(),
                'uptime': 'System running',
                'version': '1.0.0',
                'scan_mode': 'fast-simple'
            }
        }
        
        return JsonResponse(status)
    except Exception as e:
        logger.error(f"Error getting system status: {e}")
        return JsonResponse({
            'status': 'error',
            'message': str(e)
        })

def get_today_stats(request):
    """Get today's statistics for real-time updates"""
    try:
        today = timezone.now().date()
        
        # Today's entries and exits
        today_entries = ScanRecord.objects.filter(
            scan_type='ENTRY',
            timestamp__date=today
        ).count()
        
        today_exits = ScanRecord.objects.filter(
            scan_type='EXIT',
            timestamp__date=today
        ).count()
        
        # Today's revenue
        today_revenue = ParkingSession.objects.filter(
            payment_time__date=today,
            is_paid=True
        ).aggregate(total=Sum('total_amount'))['total'] or 0
        
        # Currently parked
        currently_parked = ParkingSession.objects.filter(is_active=True).count()
        
        return JsonResponse({
            'today_entries': today_entries,
            'today_exits': today_exits,
            'today_revenue': float(today_revenue),
            'currently_parked': currently_parked,
            'timestamp': timezone.now().isoformat()
        })
    except Exception as e:
        logger.error(f"Error getting today's stats: {e}")
        return JsonResponse({
            'status': 'error',
            'message': str(e)
        })

@csrf_exempt
def test_camera(request):
    """Test camera functionality"""
    if request.method == 'POST':
        try:
            # Try to start camera temporarily
            success = scanner.start_camera()
            if success:
                # Read a test frame
                ret, frame = scanner.camera.read()
                if ret and frame is not None:
                    scanner.stop_camera()
                    return JsonResponse({
                        'success': True,
                        'message': f'Camera test successful. Frame size: {frame.shape[1]}x{frame.shape[0]}',
                        'frame_size': f"{frame.shape[1]}x{frame.shape[0]}",
                        'scan_mode': 'fast-simple'
                    })
                else:
                    scanner.stop_camera()
                    return JsonResponse({
                        'success': False,
                        'message': 'Camera opened but cannot read frames'
                    })
            else:
                return JsonResponse({
                    'success': False,
                    'message': scanner.get_camera_error() or 'Failed to start camera'
                })
        except Exception as e:
            logger.error(f"Error testing camera: {e}")
            return JsonResponse({
                'success': False,
                'message': f'Camera test failed: {str(e)}'
            })
    
    return JsonResponse({'success': False, 'message': 'Invalid request method'})

