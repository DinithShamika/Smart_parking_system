from django import forms
from .models import Booking, Driver, Admin, DriverUser
from datetime import datetime

class AdminRegistrationForm(forms.ModelForm):
    confirm_password = forms.CharField(widget=forms.PasswordInput())
    
    class Meta:
        model = Admin
        fields = ['name', 'email', 'username', 'password']
        widgets = {
            'password': forms.PasswordInput(),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields:
            self.fields[field].widget.attrs.update({
                'class': 'form-control',
                'placeholder': f'Enter {field.replace("_", " ").title()}'
            })

    def clean(self):
        cleaned_data = super().clean()
        password = cleaned_data.get('password')
        confirm_password = cleaned_data.get('confirm_password')
        
        if password and confirm_password and password != confirm_password:
            raise forms.ValidationError("Passwords do not match")
        
        return cleaned_data

class AdminLoginForm(forms.Form):
    username = forms.CharField(widget=forms.TextInput(attrs={
        'class': 'form-control',
        'placeholder': 'Enter Username'
    }))
    password = forms.CharField(widget=forms.PasswordInput(attrs={
        'class': 'form-control',
        'placeholder': 'Enter Password'
    }))

class DriverUserRegistrationForm(forms.ModelForm):
    confirm_password = forms.CharField(widget=forms.PasswordInput())
    
    class Meta:
        model = DriverUser
        fields = ['name', 'email', 'username', 'password', 'mobile_no', 'licence_no', 'vehicle_no', 'vehicle_type']
        widgets = {
            'password': forms.PasswordInput(),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields:
            self.fields[field].widget.attrs.update({
                'class': 'form-control',
                'placeholder': f'Enter {field.replace("_", " ").title()}'
            })
        self.fields['vehicle_type'].widget.attrs.update({
            'class': 'form-select'
        })

    def clean(self):
        cleaned_data = super().clean()
        password = cleaned_data.get('password')
        confirm_password = cleaned_data.get('confirm_password')
        
        if password and confirm_password and password != confirm_password:
            raise forms.ValidationError("Passwords do not match")
        
        return cleaned_data

class DriverUserLoginForm(forms.Form):
    username = forms.CharField(widget=forms.TextInput(attrs={
        'class': 'form-control',
        'placeholder': 'Enter Username'
    }))
    password = forms.CharField(widget=forms.PasswordInput(attrs={
        'class': 'form-control',
        'placeholder': 'Enter Password'
    }))

class BookingForm(forms.ModelForm):
    class Meta:
        model = Booking
        fields = ['driver_name', 'mobile_no', 'vehicle_no', 'vehicle_type', 'booking_time']
        widgets = {
            'booking_time': forms.DateTimeInput(attrs={'type': 'datetime-local'}),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields:
            self.fields[field].widget.attrs.update({
                'class': 'form-control',
                'placeholder': f'Enter {field.replace("_", " ")}'
            })
        self.fields['vehicle_type'].widget.attrs.update({
            'class': 'form-select'
        })

class RegisteredDriverBookingForm(forms.ModelForm):
    class Meta:
        model = Booking
        fields = ['vehicle_no', 'booking_time']
        widgets = {
            'booking_time': forms.DateTimeInput(attrs={'type': 'datetime-local'}),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields:
            self.fields[field].widget.attrs.update({
                'class': 'form-control',
                'placeholder': f'Enter {field.replace("_", " ")}'
            })

class TemporaryBookingForm(forms.ModelForm):
    email = forms.EmailField(
        required=False,
        widget=forms.EmailInput(attrs={
            'class': 'form-control',
            'placeholder': 'Enter Email Address (optional)'
        }),
        help_text='If you provide an email, you will receive a confirmation with QR code. Otherwise, you can retrieve your booking details on the website.'
    )
    class Meta:
        model = Booking
        fields = ['driver_name', 'mobile_no', 'email', 'vehicle_no', 'vehicle_type', 'booking_time']
        widgets = {
            'booking_time': forms.DateTimeInput(attrs={'type': 'datetime-local'}),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields:
            self.fields[field].widget.attrs.update({
                'class': 'form-control',
                'placeholder': f'Enter {field.replace("_", " ")}'
            })
        self.fields['vehicle_type'].widget.attrs.update({
            'class': 'form-select'
        })
        self.fields['email'].widget.attrs['placeholder'] = 'Enter Email Address (optional)'
        self.fields['email'].help_text = 'If you provide an email, you will receive a confirmation with QR code. Otherwise, you can retrieve your booking details on the website.'

class DriverRegistrationForm(forms.ModelForm):
    class Meta:
        model = Driver
        fields = ['name', 'mobile_no', 'email', 'licence_no']

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields:
            self.fields[field].widget.attrs.update({
                'class': 'form-control',
                'placeholder': f'Enter {field.replace("_", " ").title()}'
            })     