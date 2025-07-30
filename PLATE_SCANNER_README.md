# Smart Parking Plate Scanner

A high-accuracy license plate recognition system specifically designed for Sri Lankan number plates in the format **ABC-1234**.

## Features

- **High Accuracy OCR**: Uses EasyOCR with optimized settings for Sri Lankan plates
- **Multiple Plate Formats**: Supports various Sri Lankan number plate formats
- **Real-time Processing**: Live camera feed with instant plate detection
- **Smart Corrections**: Automatically corrects common OCR misreadings
- **Confidence Scoring**: Advanced confidence calculation for reliable results
- **Database Integration**: Seamless integration with Django models

## Supported Number Plate Formats

### Primary Format (Most Common)
- **ABC-1234**: 3 letters + hyphen + 4 digits
- **ABC1234**: 3 letters + 4 digits (without hyphen)

### Alternative Formats
- **AB-1234**: 2 letters + hyphen + 4 digits
- **AB1234**: 2 letters + 4 digits (without hyphen)

### Motorcycle Format
- **A-12345**: 1 letter + hyphen + 5 digits
- **A12345**: 1 letter + 5 digits (without hyphen)

### Old Format
- **123-4567**: 3 digits + hyphen + 4 digits
- **1234567**: 3 digits + 4 digits (without hyphen)

## Installation

### Prerequisites
- Python 3.8 or higher
- Webcam or camera device
- At least 4GB RAM (8GB recommended)

### Quick Installation

1. **Clone the repository** (if not already done):
   ```bash
   git clone <repository-url>
   cd smart-parking-system
   ```

2. **Run the installation script**:
   ```bash
   python install_scanner.py
   ```

3. **Or install manually**:
   ```bash
   pip install -r requirements.txt
   pip install easyocr torch torchvision
   ```

### Manual Setup

1. **Install Python dependencies**:
   ```bash
   pip install Django==5.0.6
   pip install opencv-python==4.9.0.80
   pip install easyocr==1.7.0
   pip install torch==2.1.0 torchvision==0.16.0
   pip install numpy==1.26.4 Pillow==10.2.0
   ```

2. **Run Django migrations**:
   ```bash
   cd smart_parking
   python manage.py makemigrations
   python manage.py migrate
   ```

3. **Create a superuser** (optional):
   ```bash
   python manage.py createsuperuser
   ```

## Usage

### Starting the Scanner

1. **Start the Django server**:
   ```bash
   cd smart_parking
   python manage.py runserver
   ```

2. **Access the scanner interface**:
   - Open your browser and go to: `http://localhost:8000/plate-scanner/entrance/`
   - For exit scanner: `http://localhost:8000/plate-scanner/exit/`

3. **Start scanning**:
   - Click "Start Scanner" to begin camera capture
   - Position the license plate clearly in the camera view
   - The system will automatically detect and process plates

### Testing the Scanner

Run the test suite to verify everything is working:

```bash
python smart_parking/plate_scanner/test_scanner.py
```

This will test:
- Plate validation for all supported formats
- OCR corrections for common misreadings
- Character replacement logic
- Confidence scoring

## Configuration

### Scanner Settings

The scanner can be configured by modifying the `PlateScanner` class in `scanner.py`:

```python
# Confidence thresholds
self.min_confidence = 0.3        # Minimum confidence to accept a plate
self.high_confidence = 0.7       # High confidence threshold
self.excellent_confidence = 0.85 # Excellent confidence threshold

# Processing settings
self.scan_cooldown = 1.0         # Seconds between scans
self.max_processing_time = 0.5   # Maximum processing time per frame
self.frame_skip = 2              # Process every Nth frame
```

### Camera Settings

Camera properties can be adjusted in the `start_camera` method:

```python
# Camera resolution
self.camera.set(cv2.CAP_PROP_FRAME_WIDTH, 1920)
self.camera.set(cv2.CAP_PROP_FRAME_HEIGHT, 1080)

# Camera settings
self.camera.set(cv2.CAP_PROP_FPS, 30)
self.camera.set(cv2.CAP_PROP_AUTOFOCUS, 1)
self.camera.set(cv2.CAP_PROP_BRIGHTNESS, 128)
self.camera.set(cv2.CAP_PROP_CONTRAST, 128)
```

## Troubleshooting

### Common Issues

#### 1. Camera Not Found
**Problem**: "No working cameras found" error
**Solution**:
- Check camera connections
- Ensure camera is not being used by another application
- Try different camera indices (0, 1, 2, 3)
- Check camera permissions

#### 2. Poor Recognition Accuracy
**Problem**: Plates are not being recognized correctly
**Solution**:
- Ensure good lighting conditions
- Position plate clearly in camera view
- Clean the camera lens
- Adjust camera focus
- Check plate is clean and readable

#### 3. EasyOCR Installation Issues
**Problem**: EasyOCR fails to install or import
**Solution**:
```bash
# Install PyTorch first
pip install torch torchvision

# Then install EasyOCR
pip install easyocr

# Or use conda
conda install -c conda-forge easyocr
```

#### 4. Memory Issues
**Problem**: System runs out of memory
**Solution**:
- Reduce camera resolution
- Increase frame_skip value
- Close other applications
- Add more RAM if possible

#### 5. Slow Performance
**Problem**: Scanner is slow or laggy
**Solution**:
- Reduce camera resolution
- Increase frame_skip value
- Use GPU acceleration (if available)
- Optimize lighting conditions

### Performance Optimization

1. **GPU Acceleration** (if available):
   ```python
   # In scanner.py, change gpu=False to gpu=True
   self.reader = easyocr.Reader(['en'], gpu=True)
   ```

2. **Reduce Processing Load**:
   ```python
   # Increase frame skip for better performance
   self.frame_skip = 3  # Process every 3rd frame
   
   # Reduce resolution
   self.camera.set(cv2.CAP_PROP_FRAME_WIDTH, 1280)
   self.camera.set(cv2.CAP_PROP_FRAME_HEIGHT, 720)
   ```

3. **Optimize Confidence Thresholds**:
   ```python
   # Lower thresholds for more detections (may increase false positives)
   self.min_confidence = 0.2
   self.high_confidence = 0.6
   ```

## API Endpoints

### Scanner Control
- `POST /plate-scanner/start-scan/` - Start the scanner
- `POST /plate-scanner/stop-scan/` - Stop the scanner
- `POST /plate-scanner/process-entry/` - Process entry scan
- `POST /plate-scanner/process-exit/` - Process exit scan

### Status and Information
- `GET /plate-scanner/camera-status/` - Check camera status
- `GET /plate-scanner/system-status/` - Get system status
- `GET /plate-scanner/today-stats/` - Get today's statistics

### Admin Functions
- `GET /plate-scanner/admin-dashboard/` - Admin dashboard
- `POST /plate-scanner/mark-payment/<session_id>/` - Mark payment received
- `GET /plate-scanner/vehicle/<plate_number>/` - Vehicle details

## Database Models

### Vehicle
- `plate_number`: License plate number
- `registered_at`: Registration timestamp
- `is_registered`: Whether vehicle is pre-registered

### ParkingSession
- `session_id`: Unique session identifier
- `vehicle`: Associated vehicle
- `entry_time`: Entry timestamp
- `exit_time`: Exit timestamp
- `is_active`: Whether session is active
- `total_amount`: Parking fee
- `is_paid`: Payment status

### ScanRecord
- `vehicle`: Associated vehicle
- `scan_type`: ENTRY or EXIT
- `timestamp`: Scan timestamp
- `image`: Captured image
- `confidence_score`: OCR confidence

## Development

### Adding New Plate Formats

To add support for new plate formats, modify the `plate_patterns` list in `scanner.py`:

```python
# Add new regex pattern
re.compile(r'^[A-Z]{2}-\d{3}[A-Z]$'),  # AB-123C format
```

### Customizing OCR Settings

Modify the EasyOCR reader settings in the `__init__` method:

```python
self.reader = easyocr.Reader(
    ['en'], 
    gpu=False,
    model_storage_directory='ocr_models',
    download_enabled=True,
    recog_network='english_g2'  # Try different networks
)
```

### Adding New Preprocessing Methods

Add new preprocessing methods in the `preprocess_image` method:

```python
# Add new preprocessing technique
new_method = cv2.bilateralFilter(gray, 9, 75, 75)
processed_images.append(('bilateral_filter', new_method))
```

## Support

For issues and questions:
1. Check the troubleshooting section above
2. Run the test suite to verify functionality
3. Check the logs for detailed error messages
4. Ensure all dependencies are properly installed

## License

This project is part of the Smart Parking System and follows the same license terms. 