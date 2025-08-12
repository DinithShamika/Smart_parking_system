from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.core.mail import send_mail, EmailMessage
from django.conf import settings
from .models import Category, Slot, Booking, Driver, Admin, DriverUser
from .forms import BookingForm, RegisteredDriverBookingForm, TemporaryBookingForm, DriverRegistrationForm, AdminRegistrationForm, AdminLoginForm, DriverUserRegistrationForm, DriverUserLoginForm
from datetime import datetime
from django.contrib.auth import authenticate, login

def home(request):
    return render(request, 'booking/home.html')

def admin_registration(request):
    """Handle admin registration"""
    if request.method == 'POST':
        form = AdminRegistrationForm(request.POST)
        if form.is_valid():
            admin = form.save(commit=False)
            # In production, use proper password hashing
            admin.save()
            messages.success(request, 'Admin registration successful! Please login.')
            return redirect('booking:admin_login')
    else:
        form = AdminRegistrationForm()
    
    return render(request, 'booking/admin_registration.html', {
        'form': form
    })

def admin_login(request):
    """Handle admin login"""
    if request.method == 'POST':
        form = AdminLoginForm(request.POST)
        if form.is_valid():
            username = form.cleaned_data['username']
            password = form.cleaned_data['password']
            
            try:
                admin = Admin.objects.get(username=username, password=password)
                request.session['admin_id'] = admin.id
                request.session['admin_name'] = admin.name
                request.session['user_type'] = 'admin'
                messages.success(request, f'Welcome, {admin.name}!')
                return redirect('booking:admin_dashboard')
            except Admin.DoesNotExist:
                messages.error(request, 'Invalid username or password.')
    else:
        form = AdminLoginForm()
    
    return render(request, 'booking/admin_login.html', {
        'form': form
    })

def send_welcome_email_driver_user(driver_user):
    """Send welcome email to newly registered driver user"""
    subject = 'Welcome to Smart Parking System'
    message = f"""
    Dear {driver_user.name},
    \nWelcome to our Smart Parking System! Your registration has been successful.\n\nRegistration Details:\n- Name: {driver_user.name}\n- License No: {driver_user.licence_no}\n- Email: {driver_user.email}\n\nYou can now use the \"Registered Driver Booking\" option to book parking slots quickly.\n\nThank you for choosing our service!\n\nBest regards,\nSmart Parking Team\n    """
    try:
        send_mail(
            subject,
            message,
            settings.DEFAULT_FROM_EMAIL,
            [driver_user.email],
            fail_silently=False
        )
    except Exception as e:
        print(f"Failed to send welcome email to driver user: {e}")

def driver_user_registration(request):
    """Handle driver user registration"""
    if request.method == 'POST':
        form = DriverUserRegistrationForm(request.POST)
        if form.is_valid():
            driver_user = form.save(commit=False)
            # In production, use proper password hashing
            driver_user.save()
            send_welcome_email_driver_user(driver_user)
            messages.success(request, 'Driver registration successful! Please login.')
            return redirect('booking:driver_login')
    else:
        form = DriverUserRegistrationForm()
    
    return render(request, 'booking/driver_user_registration.html', {
        'form': form,
        'vehicle_types': ['car', 'motorcycle', 'truck', 'van']
    })

def driver_login(request):
    """Handle driver user login"""
    if request.method == 'POST':
        form = DriverUserLoginForm(request.POST)
        if form.is_valid():
            username = form.cleaned_data['username']
            password = form.cleaned_data['password']
            
            try:
                driver_user = DriverUser.objects.get(username=username, password=password)
                request.session['driver_id'] = driver_user.id
                request.session['driver_name'] = driver_user.name
                request.session['user_type'] = 'driver'
                messages.success(request, f'Welcome, {driver_user.name}!')
                return redirect('booking:driver_dashboard')
            except DriverUser.DoesNotExist:
                messages.error(request, 'Invalid username or password.')
    else:
        form = DriverUserLoginForm()
    
    return render(request, 'booking/driver_login.html', {
        'form': form
    })

def logout(request):
    """Handle logout for both admin and driver"""
    request.session.flush()
    messages.success(request, 'You have been logged out successfully.')
    return redirect('booking:home')

def driver_dashboard(request):
    """Driver dashboard - shows booking options"""
    if 'user_type' not in request.session or request.session['user_type'] != 'driver':
        messages.error(request, 'Please login as a driver to access this page.')
        return redirect('booking:driver_login')
    
    return render(request, 'booking/driver_dashboard.html')

def registered_driver_booking(request):
    """Handle booking for registered drivers"""
    if request.method == 'POST':
        form = RegisteredDriverBookingForm(request.POST)
        if form.is_valid():
            # Store in session to use in next steps
            request.session['booking_data'] = {
                'booking_type': 'registered',
                'vehicle_no': form.cleaned_data['vehicle_no'],
                'booking_time': form.cleaned_data['booking_time'].isoformat(),
            }
            return redirect('booking:select_slot')
    else:
        form = RegisteredDriverBookingForm(initial={
            'booking_time': datetime.now().strftime('%Y-%m-%dT%H:%M')
        })
    
    return render(request, 'booking/registered_driver_booking.html', {
        'form': form
    })

def temporary_booking(request):
    """Handle temporary booking for non-registered users"""
    if request.method == 'POST':
        form = TemporaryBookingForm(request.POST)
        if form.is_valid():
            # Store in session to use in next steps
            request.session['booking_data'] = {
                'booking_type': 'temporary',
                'driver_name': form.cleaned_data['driver_name'],
                'mobile_no': form.cleaned_data['mobile_no'],
                'vehicle_no': form.cleaned_data['vehicle_no'],
                'vehicle_type': form.cleaned_data['vehicle_type'],
                'booking_time': form.cleaned_data['booking_time'].isoformat(),
                'email': form.cleaned_data.get('email'),  # Store email for temporary booking
            }
            return redirect('booking:select_slot')
    else:
        form = TemporaryBookingForm(initial={
            'booking_time': datetime.now().strftime('%Y-%m-%dT%H:%M')
        })
    
    return render(request, 'booking/temporary_booking.html', {
        'form': form,
        'vehicle_types': ['car', 'motorcycle', 'truck', 'van']
    })

def driver_registration(request):
    """Handle driver registration"""
    if request.method == 'POST':
        form = DriverRegistrationForm(request.POST)
        if form.is_valid():
            driver = form.save()
            # Send welcome email
            send_welcome_email(driver)
            return redirect('booking:registration_success')
    else:
        form = DriverRegistrationForm()
    
    return render(request, 'booking/driver_registration.html', {
        'form': form,
        'vehicle_types': ['car', 'motorcycle', 'truck', 'van']
    })

def select_slot(request):
    """Show available slots for booking"""
    if 'booking_data' not in request.session:
        return redirect('booking:home')
    
    categories = Category.objects.prefetch_related('slot_set').all()
    return render(request, 'booking/select_slot.html', {
        'categories': categories
    })

def send_booking_confirmation_email_with_email(booking, email):
    """Send booking confirmation email with slot details to the given email address, attaching the QR code image."""
    subject = 'Parking Booking Confirmation'
    message = f"""
    Dear {booking.driver_name},
    \nYour parking booking has been confirmed!\n\nBooking Details:\n- Booking ID: {booking.booking_id}\n- Parking Slot: {booking.slot.slot_number}\n- Vehicle: {booking.vehicle_no} ({booking.vehicle_type})\n- Date & Time: {booking.booking_time}\n\nPlease arrive on time and present your QR code at the entrance.\n\nThank you for choosing our service!\n\nBest regards,\nSmart Parking Team\n    """
    try:
        email_msg = EmailMessage(
            subject,
            message,
            settings.DEFAULT_FROM_EMAIL,
            [email],
        )
        # Attach QR code if it exists
        if booking.qr_code and hasattr(booking.qr_code, 'path'):
            email_msg.attach_file(booking.qr_code.path)
        email_msg.send(fail_silently=False)
    except Exception as e:
        print(f"Failed to send booking confirmation email: {e}")

def confirm_booking(request, slot_id):
    """Confirm booking and create the booking record"""
    if 'booking_data' not in request.session:
        return redirect('booking:home')
    
    slot = get_object_or_404(Slot, id=slot_id)
    
    if not slot.is_available:
        messages.error(request, "This slot has already been booked!")
        return redirect('booking:select_slot')
    
    if request.method == 'POST':
        booking_data = request.session['booking_data']
        email_to_send = None
        # For registered drivers, get driver details
        if booking_data['booking_type'] == 'registered':
            try:
                # Look up DriverUser by vehicle_no
                driver_user = DriverUser.objects.filter(vehicle_no=booking_data['vehicle_no']).first()
                if driver_user:
                    driver_name = driver_user.name
                    mobile_no = driver_user.mobile_no
                    vehicle_type = driver_user.vehicle_type
                    email_to_send = driver_user.email
                else:
                    driver_name = "Registered Driver"
                    mobile_no = "N/A"
                    vehicle_type = "car"
            except Exception as e:
                messages.error(request, "Error processing registered driver booking.")
                return redirect('booking:registered_driver_booking')
        else:
            driver_name = booking_data['driver_name']
            mobile_no = booking_data['mobile_no']
            vehicle_type = booking_data['vehicle_type']
            email_to_send = booking_data.get('email')  # Get email for temporary booking
        
        booking = Booking(
            driver_name=driver_name,
            mobile_no=mobile_no,
            vehicle_no=booking_data['vehicle_no'],
            vehicle_type=vehicle_type,
            slot=slot,
            booking_time=booking_data['booking_time'],
        )
        booking.save()
        
        # Send booking confirmation email if email is available
        if email_to_send:
            send_booking_confirmation_email_with_email(booking, email_to_send)
        
        # Clear session data
        del request.session['booking_data']
        
        return redirect('booking:booking_success', booking_id=booking.booking_id)
    
    return render(request, 'booking/confirm_booking.html', {
        'slot': slot,
        'booking_data': request.session['booking_data'],
        'category': slot.category
    })

def booking_success(request, booking_id):
    """Show booking success page"""
    booking = get_object_or_404(Booking, booking_id=booking_id)
    return render(request, 'booking/booking_success.html', {
        'booking': booking
    })

def registration_success(request):
    """Show registration success page"""
    return render(request, 'booking/registration_success.html')

def login_view(request):
    """Handle user login"""
    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')
        user = authenticate(request, username=username, password=password)
        if user is not None:
            login(request, user)
            return redirect('booking:home')
        else:
            messages.error(request, 'Invalid username or password.')
    return render(request, 'booking/login.html')

# Email functions
def send_welcome_email(driver):
    """Send welcome email to newly registered driver"""
    subject = 'Welcome to Smart Parking System'
    message = f"""
    Dear {driver.name},
    
    Welcome to our Smart Parking System! Your registration has been successful.
    
    Registration Details:
    - Name: {driver.name}
    - License No: {driver.licence_no}
    - Email: {driver.email}
    
    You can now use the "Registered Driver Booking" option to book parking slots quickly.
    
    Thank you for choosing our service!
    
    Best regards,
    Smart Parking Team
    """
    
    try:
        send_mail(
            subject,
            message,
            settings.DEFAULT_FROM_EMAIL,
            [driver.email],
            fail_silently=False
        )
    except Exception as e:
        print(f"Failed to send welcome email: {e}")

def send_booking_confirmation_email(booking):
    """Send booking confirmation email with slot details"""
    subject = 'Parking Booking Confirmation'
    message = f"""
    Dear {booking.driver_name},
    
    Your parking booking has been confirmed!
    
    Booking Details:
    - Booking ID: {booking.booking_id}
    - Parking Slot: {booking.slot.slot_number}
    - Vehicle: {booking.vehicle_no} ({booking.vehicle_type})
    - Date & Time: {booking.booking_time}
    
    Please arrive on time and present your QR code at the entrance.
    
    Thank you for choosing our service!
    
    Best regards,
    Smart Parking Team
    """
    
    # Note: Since Booking model doesn't have email field, we can't send email
    # This function is kept for future use if email field is added
    print(f"Booking confirmation for {booking.driver_name}")

# Admin views for slot and booking management
def admin_dashboard(request):
    """Admin dashboard for managing slots, bookings, and categories"""
    if 'user_type' not in request.session or request.session['user_type'] != 'admin':
        messages.error(request, 'Please login as an admin to access this page.')
        return redirect('booking:admin_login')
    
    categories = Category.objects.all()
    slots = Slot.objects.all()
    available_slots = slots.filter(is_available=True)
    occupied_slots = slots.filter(is_available=False)
    bookings = Booking.objects.all().order_by('-booking_time')
    
    return render(request, 'booking/admin_dashboard.html', {
        'categories': categories,
        'slots': slots,
        'available_slots': available_slots,
        'occupied_slots': occupied_slots,
        'bookings': bookings
    })

def delete_booking(request, booking_id):
    """Delete a booking and free up the slot"""
    if 'user_type' not in request.session or request.session['user_type'] != 'admin':
        messages.error(request, 'Please login as an admin to access this page.')
        return redirect('booking:admin_login')
    
    if request.method == 'POST':
        booking = get_object_or_404(Booking, booking_id=booking_id)
        slot_number = booking.slot.slot_number
        booking.delete()  # This will automatically free up the slot
        messages.success(request, f'Booking deleted successfully. Slot {slot_number} is now available.')
        return redirect('booking:admin_dashboard')
    
    return redirect('booking:admin_dashboard')
