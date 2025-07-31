import cv2
import easyocr
import re
import numpy as np
from django.core.files.base import ContentFile
from datetime import datetime
from django.db import transaction
from django.utils import timezone
import time
import logging

# Import Django models
from .models import Vehicle, ScanRecord, ParkingSession

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class PlateScanner:
    def __init__(self):
        # Enhanced EasyOCR setup for better accuracy
        try:
            self.reader = easyocr.Reader(
                ['en'], 
                gpu=False,
                model_storage_directory='ocr_models',
                download_enabled=True,
                recog_network='english_g2'
            )
            logger.info("Enhanced EasyOCR initialized successfully")
        except Exception as e:
            logger.error(f"EasyOCR initialization failed: {e}")
            self.reader = None
        
        self.camera = None
        self.scanning = False
        self.camera_index = 0
        self.camera_error = None
        self.last_scan_time = 0
        self.scan_cooldown = 0.1  # Fast scanning
        
        # Enhanced settings for better accuracy
        self.min_confidence = 0.3  # Higher threshold for accuracy
        self.max_processing_time = 0.2  # More processing time for accuracy
        
        # Enhanced patterns for number plates
        self.plate_patterns = [
            r'^[A-Z0-9]{2,8}$',      # Simple alphanumeric (2-8 chars)
            r'^[0-9]{2,6}$',         # Numbers only (2-6 digits)
            r'^[A-Z]{2,6}$',         # Letters only (2-6 letters)
            r'^[A-Z0-9\-]{3,10}$',   # Alphanumeric with hyphens
            r'^[A-Z]{1,2}[0-9]{1,4}[A-Z]{1,2}$',  # Standard plate format
            r'^[0-9]{1,2}[A-Z]{1,3}[0-9]{1,4}$',  # Alternative format
        ]
        
        # Character corrections for better accuracy
        self.char_replacements = {
            'O': '0', 'I': '1', 'L': '1', 'S': '5', 'G': '6', 'B': '8', 'Z': '2',
            '0': 'O', '1': 'I', '5': 'S', '6': 'G', '8': 'B', '2': 'Z'
        }

    def preprocess_image(self, frame):
        """Enhanced image preprocessing for better accuracy"""
        try:
            # Convert to grayscale
            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            
            # Enhanced contrast enhancement
            clahe = cv2.createCLAHE(clipLimit=3.0, tileGridSize=(8,8))
            enhanced = clahe.apply(gray)
            
            # Noise reduction
            denoised = cv2.fastNlMeansDenoising(enhanced, None, 10, 7, 21)
            
            # Multiple thresholding methods
            _, thresh_binary = cv2.threshold(denoised, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
            thresh_adaptive = cv2.adaptiveThreshold(denoised, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY, 11, 2)
            
            # Morphological operations for better text separation
            kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (2, 2))
            morph = cv2.morphologyEx(thresh_binary, cv2.MORPH_CLOSE, kernel)
            
            # Edge enhancement
            edges = cv2.Canny(denoised, 50, 150)
            
            return [
                ('gray', gray),
                ('enhanced', enhanced),
                ('denoised', denoised),
                ('thresh_binary', thresh_binary),
                ('thresh_adaptive', thresh_adaptive),
                ('morph', morph),
                ('edges', edges)
            ]
        except Exception as e:
            logger.error(f"Preprocessing error: {e}")
            return []

    def clean_text(self, text):
        """Enhanced text cleaning for better accuracy"""
        if not text:
            return None
        
        # Convert to uppercase and remove spaces
        text = text.upper().strip()
        text = re.sub(r'\s+', '', text)
        
        # Remove special characters except letters, numbers, and hyphens
        text = re.sub(r'[^A-Z0-9\-]', '', text)
        
        # Filter by length (2-10 characters)
        if len(text) < 2 or len(text) > 10:
            return None
        
        # Apply character corrections
        for old_char, new_char in self.char_replacements.items():
            text = text.replace(old_char, new_char)
        
        return text

    def validate_text(self, text):
        """Enhanced validation for number plates"""
        if not text:
            return None
        
        text = self.clean_text(text)
        if not text:
            return None
        
        # Check if text matches any pattern
        for pattern in self.plate_patterns:
            if re.match(pattern, text):
                logger.info(f"✓ Accurate number plate detected: {text}")
                return text
        
        # Accept any alphanumeric text with reasonable length
        if text.isalnum() and len(text) >= 2 and len(text) <= 8:
            logger.info(f"✓ Text detected: {text}")
            return text
        
        return None

    def find_working_camera(self):
        """Find a working camera"""
        logger.info("Finding camera...")
        
        for idx in range(4):
            try:
                cap = cv2.VideoCapture(idx)
                if cap.isOpened():
                    ret, frame = cap.read()
                    if ret and frame is not None:
                        logger.info(f"✓ Camera {idx} found")
                        cap.release()
                        return idx
                    cap.release()
            except Exception as e:
                continue
        
        logger.error("No camera found!")
        return None

    def start_camera(self, camera_id=None):
        """Start camera with enhanced settings"""
        self.camera_error = None
        
        try:
            if camera_id is not None:
                self.camera_index = camera_id
            else:
                working_camera = self.find_working_camera()
                if working_camera is not None:
                    self.camera_index = working_camera
                else:
                    self.camera_index = 0
            
            logger.info(f"Starting camera on index {self.camera_index}...")
            
            self.camera = cv2.VideoCapture(self.camera_index)
            
            if self.camera.isOpened():
                # Enhanced camera settings for better quality
                self.camera.set(cv2.CAP_PROP_FRAME_WIDTH, 1280)  # Higher resolution
                self.camera.set(cv2.CAP_PROP_FRAME_HEIGHT, 720)
                self.camera.set(cv2.CAP_PROP_FPS, 30)
                self.camera.set(cv2.CAP_PROP_AUTOFOCUS, 1)
                self.camera.set(cv2.CAP_PROP_BRIGHTNESS, 0.5)
                self.camera.set(cv2.CAP_PROP_CONTRAST, 0.5)
                self.camera.set(cv2.CAP_PROP_SATURATION, 0.5)
                
                # Test camera
                ret, frame = self.camera.read()
                if ret and frame is not None:
                    self.scanning = True
                    logger.info("✓ Camera started successfully with enhanced settings")
                    return True
                else:
                    logger.error("Camera cannot read frames")
                    self.camera.release()
                    self.camera = None
            else:
                logger.error("Failed to open camera")
            
            self.camera_error = "Failed to start camera"
            return False
            
        except Exception as e:
            self.camera_error = f"Camera error: {str(e)}"
            logger.error(f"Camera start failed: {e}")
            return False

    def stop_camera(self):
        """Stop camera"""
        self.scanning = False
        
        if self.camera and self.camera.isOpened():
            self.camera.release()
            self.camera = None
        logger.info("Camera stopped")

    def process_frame(self):
        """Enhanced frame processing for better accuracy"""
        if not self.scanning or not self.camera or not self.camera.isOpened():
            return None, []
        
        # Check scan cooldown
        current_time = time.time()
        if current_time - self.last_scan_time < self.scan_cooldown:
            return None, []
        
        try:
            ret, frame = self.camera.read()
            if not ret or frame is None:
                return None, []
            
            # Enhanced preprocessing
            processed_images = self.preprocess_image(frame)
            
            all_results = []
            
            # Enhanced OCR processing with multiple methods
            start_time = time.time()
            for method_name, processed_img in processed_images:
                if time.time() - start_time > self.max_processing_time:
                    break
                
                try:
                    if self.reader:
                        # Enhanced OCR settings for better accuracy
                        results = self.reader.readtext(
                            processed_img,
                            decoder='greedy',
                            width_ths=0.8,  # More lenient for accuracy
                            text_threshold=0.3,  # Higher threshold
                            height_ths=0.6,  # More lenient
                            paragraph=False,
                            detail=1
                        )
                        
                        for (bbox, text, prob) in results:
                            if prob > self.min_confidence:
                                all_results.append((bbox, text, prob, method_name))
                    
                except Exception as e:
                    logger.error(f"OCR error: {e}")
                    continue
            
            # Remove duplicates and sort by confidence
            unique_results = []
            seen_texts = set()
            
            for (bbox, text, prob, method_name) in all_results:
                clean_text = self.clean_text(text)
                if clean_text and clean_text not in seen_texts:
                    seen_texts.add(clean_text)
                    unique_results.append((bbox, clean_text, prob, method_name))
            
            # Sort by confidence
            unique_results.sort(key=lambda x: x[2], reverse=True)
            
            detected_texts = []
            for (bbox, text, prob, method_name) in unique_results:
                validated_text = self.validate_text(text)
                if validated_text:
                    detected_texts.append({
                        'text': validated_text,
                        'confidence': prob,
                        'bbox': bbox,
                        'method': method_name
                    })
                    self.last_scan_time = current_time
            
            return frame, detected_texts
            
        except Exception as e:
            logger.error(f"Frame processing error: {e}")
            return None, []

    def save_scan(self, frame, detected_text, scan_type, confidence=0.8):
        """Save scan record with enhanced details"""
        try:
            # Encode frame with better quality
            encode_param = [int(cv2.IMWRITE_JPEG_QUALITY), 90]
            _, buffer = cv2.imencode('.jpg', frame, encode_param)
            image_file = ContentFile(
                buffer.tobytes(),
                name=f"{scan_type}_{detected_text}_{datetime.now().strftime('%Y%m%d%H%M%S')}.jpg"
            )
            
            with transaction.atomic():
                # Get or create vehicle
                vehicle, created = Vehicle.objects.get_or_create(
                    plate_number=detected_text
                )
                
                if created:
                    logger.info(f"✓ Created new vehicle record: {detected_text}")
                
                # Check if vehicle is registered
                try:
                    from booking.models import Booking
                    booking = Booking.objects.filter(vehicle_no=detected_text).first()
                    if booking:
                        vehicle.is_registered = True
                        vehicle.save()
                        logger.info(f"✓ Vehicle {detected_text} is registered")
                except Exception as e:
                    logger.error(f"Error checking booking: {e}")
                
                # Handle parking session
                parking_session = None
                if scan_type == 'ENTRY':
                    existing_session = ParkingSession.objects.filter(
                        vehicle=vehicle,
                        is_active=True
                    ).first()
                    
                    if existing_session:
                        parking_session = existing_session
                        logger.info(f"✓ Vehicle {detected_text} already has active session")
                    else:
                        parking_session = ParkingSession.objects.create(
                            vehicle=vehicle
                        )
                        logger.info(f"✓ Created new parking session for {detected_text}")
                        
                elif scan_type == 'EXIT':
                    parking_session = ParkingSession.objects.filter(
                        vehicle=vehicle,
                        is_active=True
                    ).first()
                    if parking_session:
                        parking_session.exit_time = timezone.now()
                        parking_session.is_active = False
                        parking_session.total_amount = parking_session.calculate_amount()
                        parking_session.save()
                        logger.info(f"✓ Closed parking session for {detected_text}, amount: {parking_session.total_amount}")
                        # Set slot as available if booking exists
                        try:
                            from booking.models import Booking
                            # Find the most recent booking with a slot for this vehicle
                            booking = Booking.objects.filter(vehicle_no=detected_text, slot__isnull=False).order_by('-booking_time').first()
                            if booking and booking.slot:
                                logger.info(f"[EXIT] Found booking for vehicle {detected_text} with slot {booking.slot.slot_number}")
                                booking.slot.is_available = True
                                booking.slot.save()
                                logger.info(f"[EXIT] Slot {booking.slot.slot_number} set to available after exit")
                            else:
                                logger.warning(f"[EXIT] No booking with slot found for vehicle {detected_text}")
                        except Exception as e:
                            logger.error(f"[EXIT] Error setting slot available for vehicle {detected_text}: {e}")
                
                # Create scan record
                scan_record = ScanRecord.objects.create(
                    vehicle=vehicle,
                    scan_type=scan_type,
                    image=image_file,
                    parking_session=parking_session,
                    confidence_score=confidence
                )
                
                logger.info(f"✓ Enhanced scan saved: {scan_type} - {detected_text} (confidence: {confidence:.2f})")
                
            return True
        except Exception as e:
            logger.error(f"Save error: {e}")
            return False

    def get_parking_status(self, plate_number):
        """Get detailed parking status"""
        try:
            vehicle = Vehicle.objects.get(plate_number=plate_number)
            active_session = ParkingSession.objects.filter(
                vehicle=vehicle,
                is_active=True
            ).first()
            
            if active_session:
                duration = timezone.now() - active_session.entry_time
                hours = duration.total_seconds() / 3600
                return {
                    'is_parked': True,
                    'entry_time': active_session.entry_time,
                    'duration_hours': round(hours, 2),
                    'estimated_cost': active_session.calculate_amount(),
                    'vehicle_registered': vehicle.is_registered
                }
            else:
                return {
                    'is_parked': False,
                    'vehicle_registered': vehicle.is_registered
                }
        except Vehicle.DoesNotExist:
            return {'is_parked': False, 'vehicle_not_found': True}

    def get_camera_error(self):
        """Get camera error"""
        return self.camera_error

    def scan_until_text(self, timeout=0.5):
        """Enhanced scanning with better accuracy"""
        start_time = time.time()
        
        logger.info(f"Starting enhanced text scan with {timeout}s timeout...")
        
        while time.time() - start_time < timeout:
            frame, texts = self.process_frame()
            
            if texts:
                # Return the best detected text
                text_info = texts[0]
                logger.info(f"✓ Enhanced text detected: {text_info['text']} (confidence: {text_info['confidence']:.2f})")
                return frame, text_info
            
            time.sleep(0.05)  # Fast polling
        
        logger.info(f"No text found within {timeout}s timeout")
        return None, None

    def get_system_status(self):
        """Get comprehensive system status"""
        status = {
            'camera_connected': self.camera is not None and self.camera.isOpened(),
            'scanner_active': self.scanning,
            'camera_index': self.camera_index,
            'last_error': self.camera_error,
            'scan_cooldown': self.scan_cooldown,
            'min_confidence': self.min_confidence,
            'easyocr_ready': self.reader is not None,
            'scan_mode': 'enhanced-accuracy',
            'processing_time': self.max_processing_time,
        }
        
        if status['camera_connected'] and self.camera:
            try:
                ret, frame = self.camera.read()
                status['camera_reading'] = ret and frame is not None
                if status['camera_reading']:
                    status['frame_size'] = f"{frame.shape[1]}x{frame.shape[0]}"
                    status['frame_channels'] = frame.shape[2] if len(frame.shape) > 2 else 1
            except Exception as e:
                status['camera_reading'] = False
                status['camera_error'] = str(e)
        
        return status
      