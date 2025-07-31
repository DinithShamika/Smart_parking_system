from django.db import models
from django.contrib.auth.models import AbstractUser
import qrcode
from io import BytesIO
from django.core.files import File
import uuid
from datetime import datetime

class Category(models.Model):
    name = models.CharField(max_length=100)
    # Removed description field since it's causing errors
    created_at = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return self.name

class Slot(models.Model):
    slot_number = models.CharField(max_length=10, unique=True)
    category = models.ForeignKey(Category, on_delete=models.CASCADE)
    is_available = models.BooleanField(default=True)
    
    def __str__(self):
        return f"{self.slot_number} ({self.category.name})"

class Booking(models.Model):
    booking_id = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)
    driver_name = models.CharField(max_length=100)
    mobile_no = models.CharField(max_length=15)
    vehicle_no = models.CharField(max_length=20)
    vehicle_type = models.CharField(max_length=50)
    slot = models.ForeignKey(Slot, on_delete=models.CASCADE)
    booking_time = models.DateTimeField(default=datetime.now)
    qr_code = models.ImageField(upload_to='qr_codes/', blank=True)
    
    fee = models.DecimalField(max_digits=10, decimal_places=2, default=0.00, help_text="Parking fee for this booking")
    is_free = models.BooleanField(default=False, help_text="Mark this booking as free parking")

    def __str__(self):
        return f"{self.driver_name} - {self.slot.slot_number}"

    def save(self, *args, **kwargs):
        if not self.qr_code:
            self.generate_qr_code()
        super().save(*args, **kwargs)
        # Update slot availability
        self.slot.is_available = False
        self.slot.save()

    def generate_qr_code(self):
        qr = qrcode.QRCode(
            version=1,
            error_correction=qrcode.constants.ERROR_CORRECT_L,
            box_size=10,
            border=4,
        )
        qr.add_data(f"""
            Booking ID: {self.booking_id}
            Driver: {self.driver_name}
            Vehicle: {self.vehicle_no}
            Slot: {self.slot.slot_number}
            Time: {self.booking_time}
        """)
        qr.make(fit=True)
        img = qr.make_image(fill_color="black", back_color="white")
        buffer = BytesIO()
        img.save(buffer)
        filename = f'qr_{self.booking_id}.png'
        self.qr_code.save(filename, File(buffer), save=False)

class Admin(models.Model):
    name = models.CharField(max_length=100)
    email = models.EmailField(unique=True)
    username = models.CharField(max_length=50, unique=True)
    password = models.CharField(max_length=128)  # In production, use proper password hashing
    created_at = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return f"{self.name} ({self.username})"

class DriverUser(models.Model):
    name = models.CharField(max_length=100)
    email = models.EmailField(unique=True)
    username = models.CharField(max_length=50, unique=True)
    password = models.CharField(max_length=128)  # In production, use proper password hashing
    mobile_no = models.CharField(max_length=15)
    licence_no = models.CharField(max_length=50)
    vehicle_no = models.CharField(max_length=20)
    vehicle_type = models.CharField(max_length=50)
    created_at = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return f"{self.name} ({self.username})"

class Driver(models.Model):
    name = models.CharField(max_length=100)
    mobile_no = models.CharField(max_length=15)
    email = models.EmailField()
    licence_no = models.CharField(max_length=50)

    def __str__(self):
        return f"{self.name} ({self.licence_no})"

    