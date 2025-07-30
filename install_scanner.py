#!/usr/bin/env python3
"""
Installation script for the Smart Parking Plate Scanner
This script will install required dependencies and test the installation
"""

import subprocess
import sys
import os
from pathlib import Path

def run_command(command, description):
    """Run a command and handle errors"""
    print(f"\n{description}...")
    try:
        result = subprocess.run(command, shell=True, check=True, capture_output=True, text=True)
        print(f"✓ {description} completed successfully")
        return True
    except subprocess.CalledProcessError as e:
        print(f"✗ {description} failed:")
        print(f"Error: {e.stderr}")
        return False

def check_python_version():
    """Check if Python version is compatible"""
    print("Checking Python version...")
    version = sys.version_info
    if version.major < 3 or (version.major == 3 and version.minor < 8):
        print(f"✗ Python {version.major}.{version.minor} is not supported. Please use Python 3.8 or higher.")
        return False
    print(f"✓ Python {version.major}.{version.minor}.{version.micro} is compatible")
    return True

def install_dependencies():
    """Install required dependencies"""
    print("\nInstalling dependencies...")
    
    # Install basic requirements
    if not run_command("pip install -r requirements.txt", "Installing basic requirements"):
        return False
    
    # Install EasyOCR separately if needed
    try:
        import easyocr
        print("✓ EasyOCR is already installed")
    except ImportError:
        print("Installing EasyOCR...")
        if not run_command("pip install easyocr", "Installing EasyOCR"):
            return False
    
    # Install PyTorch if needed
    try:
        import torch
        print("✓ PyTorch is already installed")
    except ImportError:
        print("Installing PyTorch...")
        if not run_command("pip install torch torchvision", "Installing PyTorch"):
            return False
    
    return True

def test_imports():
    """Test if all required modules can be imported"""
    print("\nTesting imports...")
    
    required_modules = [
        'cv2',
        'easyocr',
        'torch',
        'numpy',
        'django',
        'PIL'
    ]
    
    failed_imports = []
    
    for module in required_modules:
        try:
            __import__(module)
            print(f"✓ {module} imported successfully")
        except ImportError as e:
            print(f"✗ Failed to import {module}: {e}")
            failed_imports.append(module)
    
    if failed_imports:
        print(f"\n✗ Failed to import: {', '.join(failed_imports)}")
        return False
    
    print("✓ All modules imported successfully")
    return True

def test_scanner():
    """Test the plate scanner functionality"""
    print("\nTesting plate scanner...")
    
    try:
        # Set up Django environment
        os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'smart_parking.settings')
        
        import django
        django.setup()
        
        from plate_scanner.scanner import PlateScanner
        
        # Create scanner instance
        scanner = PlateScanner()
        print("✓ PlateScanner created successfully")
        
        # Test plate validation
        test_plates = ["ABC-1234", "XYZ-5678", "AB-1234", "A-12345"]
        
        for plate in test_plates:
            result = scanner.validate_plate(plate)
            if result:
                print(f"✓ Plate validation works: {plate} -> {result}")
            else:
                print(f"✗ Plate validation failed: {plate}")
                return False
        
        print("✓ Plate scanner is working correctly")
        return True
        
    except Exception as e:
        print(f"✗ Plate scanner test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def create_sample_data():
    """Create sample data for testing"""
    print("\nCreating sample data...")
    
    try:
        # Set up Django environment
        os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'smart_parking.settings')
        
        import django
        django.setup()
        
        from plate_scanner.models import Vehicle, ParkingRate
        
        # Create sample vehicles
        sample_plates = ["ABC-1234", "XYZ-5678", "DEF-9012", "GHI-3456"]
        
        for plate in sample_plates:
            vehicle, created = Vehicle.objects.get_or_create(plate_number=plate)
            if created:
                print(f"✓ Created sample vehicle: {plate}")
        
        # Create default parking rate
        rate, created = ParkingRate.objects.get_or_create(
            name="Standard Rate",
            defaults={
                'first_hour_rate': 50.00,
                'subsequent_hour_rate': 50.00,
                'max_daily_rate': 500.00
            }
        )
        
        if created:
            print("✓ Created default parking rate")
        
        print("✓ Sample data created successfully")
        return True
        
    except Exception as e:
        print(f"✗ Failed to create sample data: {e}")
        return False

def main():
    """Main installation function"""
    print("Smart Parking Plate Scanner Installation")
    print("=" * 50)
    
    # Check Python version
    if not check_python_version():
        sys.exit(1)
    
    # Install dependencies
    if not install_dependencies():
        print("\n✗ Installation failed. Please check the errors above.")
        sys.exit(1)
    
    # Test imports
    if not test_imports():
        print("\n✗ Import test failed. Please check the errors above.")
        sys.exit(1)
    
    # Test scanner
    if not test_scanner():
        print("\n✗ Scanner test failed. Please check the errors above.")
        sys.exit(1)
    
    # Create sample data
    if not create_sample_data():
        print("\n⚠ Warning: Failed to create sample data, but installation is complete.")
    
    print("\n" + "=" * 50)
    print("✓ Installation completed successfully!")
    print("\nThe plate scanner is now ready to use.")
    print("\nSupported number plate formats:")
    print("- ABC-1234 (3 letters + 4 digits) - Primary format")
    print("- AB-1234 (2 letters + 4 digits) - Alternative format")
    print("- A-12345 (1 letter + 5 digits) - Motorcycle format")
    print("- 123-4567 (3 digits + 4 digits) - Old format")
    
    print("\nTo test the scanner, run:")
    print("python smart_parking/plate_scanner/test_scanner.py")
    
    print("\nTo start the Django server, run:")
    print("python smart_parking/manage.py runserver")

if __name__ == "__main__":
    main() 