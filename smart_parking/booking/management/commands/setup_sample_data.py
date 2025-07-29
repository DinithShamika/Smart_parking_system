from django.core.management.base import BaseCommand
from booking.models import Category, Slot, Driver
from django.utils import timezone

class Command(BaseCommand):
    help = 'Set up sample data for the booking system'

    def handle(self, *args, **options):
        self.stdout.write('Setting up sample data...')
        
        # Create categories
        categories_data = [
            {'name': 'Standard Parking'},
            {'name': 'Premium Parking'},
            {'name': 'Handicap Parking'},
            {'name': 'Motorcycle Parking'},
        ]
        
        for cat_data in categories_data:
            category, created = Category.objects.get_or_create(
                name=cat_data['name']
            )
            if created:
                self.stdout.write(f'Created category: {category.name}')
        
        # Create slots for each category
        categories = Category.objects.all()
        for category in categories:
            if category.name == 'Standard Parking':
                slot_count = 20
            elif category.name == 'Premium Parking':
                slot_count = 10
            elif category.name == 'Handicap Parking':
                slot_count = 5
            elif category.name == 'Motorcycle Parking':
                slot_count = 15
            else:
                slot_count = 5
            
            for i in range(1, slot_count + 1):
                slot_number = f"{category.name[:3].upper()}{i:02d}"
                slot, created = Slot.objects.get_or_create(
                    slot_number=slot_number,
                    category=category,
                    defaults={'is_available': True}
                )
                if created:
                    self.stdout.write(f'Created slot: {slot.slot_number}')
        
        # Create sample drivers
        drivers_data = [
            {
                'name': 'John Doe',
                'mobile_no': '+1234567890',
                'email': 'john.doe@example.com',
                'licence_no': 'DL123456789',
                'vehicle_no': 'ABC123',
                'vehicle_type': 'car',
                'vehicle_model': 'Toyota Camry',
                'vehicle_color': 'Silver'
            },
            {
                'name': 'Jane Smith',
                'mobile_no': '+1987654321',
                'email': 'jane.smith@example.com',
                'licence_no': 'DL987654321',
                'vehicle_no': 'XYZ789',
                'vehicle_type': 'car',
                'vehicle_model': 'Honda Civic',
                'vehicle_color': 'Blue'
            },
            {
                'name': 'Mike Johnson',
                'mobile_no': '+1555666777',
                'email': 'mike.johnson@example.com',
                'licence_no': 'DL555666777',
                'vehicle_no': 'MOT001',
                'vehicle_type': 'motorcycle',
                'vehicle_model': 'Harley Davidson',
                'vehicle_color': 'Black'
            }
        ]
        
        for driver_data in drivers_data:
            driver, created = Driver.objects.get_or_create(
                email=driver_data['email'],
                defaults=driver_data
            )
            if created:
                self.stdout.write(f'Created driver: {driver.name}')
        
        self.stdout.write(
            self.style.SUCCESS('Sample data setup completed successfully!')
        )
        self.stdout.write(f'Created {Category.objects.count()} categories')
        self.stdout.write(f'Created {Slot.objects.count()} slots')
        self.stdout.write(f'Created {Driver.objects.count()} drivers') 