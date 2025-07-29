from django.db import models
from django.utils import timezone
from django.core.mail import send_mail
from django.conf import settings
from decimal import Decimal
import uuid

class Vehicle(models.Model):
    plate_number = models.CharField(max_length=20, unique=True)
    registered_at = models.DateTimeField(default=timezone.now)
    is_registered = models.BooleanField(default=False)  # For pre-registered vehicles
    
    def __str__(self):
        return self.plate_number

class ParkingSession(models.Model):
    session_id = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)
    vehicle = models.ForeignKey(Vehicle, on_delete=models.CASCADE)
    entry_time = models.DateTimeField(default=timezone.now)
    exit_time = models.DateTimeField(null=True, blank=True)
    is_active = models.BooleanField(default=True)
    total_amount = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal('0.00'))
    is_paid = models.BooleanField(default=False)
    payment_time = models.DateTimeField(null=True, blank=True)
    
    def __str__(self):
        return f"{self.vehicle.plate_number} - {self.session_id}"
    
    def calculate_amount(self):
        """Calculate parking fee based on duration"""
        if not self.exit_time:
            return Decimal('0.00')
        
        duration = self.exit_time - self.entry_time
        hours = duration.total_seconds() / 3600
        
        # Sri Lankan parking rates (adjust as needed)
        if hours <= 1:
            return Decimal('50.00')  # First hour: Rs. 50
        elif hours <= 3:
            return Decimal('100.00')  # Up to 3 hours: Rs. 100
        elif hours <= 6:
            return Decimal('200.00')  # Up to 6 hours: Rs. 200
        else:
            # Additional hours after 6 hours: Rs. 50 per hour
            additional_hours = hours - 6
            return Decimal('200.00') + (Decimal(str(additional_hours)) * Decimal('50.00'))
    
    def send_payment_email(self):
        """Send payment notification email to driver"""
        if not self.vehicle.is_registered:
            return False
        
        try:
            # Get driver info from booking app
            from booking.models import Booking
            booking = Booking.objects.filter(vehicle_no=self.vehicle.plate_number).first()
            
            if booking:
                subject = f'Parking Payment Due - {self.vehicle.plate_number}'
                message = f"""
                Dear {booking.driver_name},
                
                Your vehicle ({self.vehicle.plate_number}) has exited the parking facility.
                
                Parking Details:
                - Entry Time: {self.entry_time.strftime('%Y-%m-%d %H:%M:%S')}
                - Exit Time: {self.exit_time.strftime('%Y-%m-%d %H:%M:%S')}
                - Total Amount Due: Rs. {self.total_amount}
                
                Please make the payment at the parking office or through our online portal.
                
                Thank you for using our parking service.
                
                Best regards,
                Smart Parking System
                """
                
                send_mail(
                    subject,
                    message,
                    settings.DEFAULT_FROM_EMAIL,
                    [booking.driver_name],  # You might want to add email field to Driver model
                    fail_silently=False,
                )
                return True
        except Exception as e:
            print(f"Email error: {e}")
            return False

class ScanRecord(models.Model):
    ENTRY = 'ENTRY'
    EXIT = 'EXIT'
    SCAN_TYPES = [
        (ENTRY, 'Entry'),
        (EXIT, 'Exit'),
    ]
    
    vehicle = models.ForeignKey(Vehicle, on_delete=models.CASCADE)
    scan_type = models.CharField(max_length=5, choices=SCAN_TYPES)
    timestamp = models.DateTimeField(default=timezone.now)
    image = models.ImageField(upload_to='scans/', blank=True)
    parking_session = models.ForeignKey(ParkingSession, on_delete=models.CASCADE, null=True, blank=True)
    confidence_score = models.FloatField(default=0.0)
    
    class Meta:
        ordering = ['-timestamp']

class ParkingRate(models.Model):
    """Configurable parking rates"""
    name = models.CharField(max_length=100)
    first_hour_rate = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal('50.00'))
    subsequent_hour_rate = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal('50.00'))
    max_daily_rate = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal('500.00'))
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return self.name
