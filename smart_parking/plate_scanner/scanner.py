import cv2
import easyocr
import re
import numpy as np
from django.core.files.base import ContentFile
from datetime import datetime
from django.db import transaction
from django.utils import timezone
import time
import os
import logging
import threading
from collections import deque
import math

# Import Django models properly
from .models import Vehicle, ScanRecord, ParkingSession

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class PlateScanner:
    def __init__(self):
        # Initialize EasyOCR with optimized settings for Sri Lankan plates
        self.reader = easyocr.Reader(
            ['en'], 
            gpu=False,
            model_storage_directory='ocr_models',
            download_enabled=True,
            recog_network='english_g2'
        )
        
        self.camera = None
        self.scanning = False
        self.camera_index = 0
        self.camera_error = None
        self.last_scan_time = 0
        self.scan_cooldown = 1.0  # Increased cooldown to prevent duplicates
        
        # Enhanced frame buffer for better processing
        self.frame_buffer = deque(maxlen=5)  # Increased buffer size
        self.processing_thread = None
        self.stop_processing = False
        
        # Enhanced Sri Lankan number plate patterns with more variations
        self.plate_patterns = [
            # Standard format: ABC-1234
            re.compile(r'^[A-Z]{2,3}-\d{4}$'),
            # Without hyphen: ABC1234
            re.compile(r'^[A-Z]{2,3}\d{4}$'),
            # Old format: 123-4567
            re.compile(r'^\d{3}-\d{4}$'),
            # Without hyphen: 1234567
            re.compile(r'^\d{7}$'),
            # New format with letters and numbers: ABC-123
            re.compile(r'^[A-Z]{2,3}-\d{3}$'),
            # Without hyphen: ABC123
            re.compile(r'^[A-Z]{2,3}\d{3}$'),
            # Motorcycles: A-12345 or A12345
            re.compile(r'^[A-Z]{1,2}-\d{5}$'),
            re.compile(r'^[A-Z]{1,2}\d{5}$'),
            # Special formats
            re.compile(r'^[A-Z]{2}-\d{3}[A-Z]$'),
            re.compile(r'^[A-Z]{2}\d{3}[A-Z]$'),
            # Additional patterns for better coverage
            re.compile(r'^[A-Z]{1}-\d{6}$'),  # Single letter + 6 digits
            re.compile(r'^[A-Z]{1}\d{6}$'),
            re.compile(r'^[A-Z]{4}-\d{3}$'),  # 4 letters + 3 digits
            re.compile(r'^[A-Z]{4}\d{3}$'),
            # More variations
            re.compile(r'^[A-Z]{2}-\d{2}[A-Z]{2}$'),  # AB-12CD
            re.compile(r'^[A-Z]{2}\d{2}[A-Z]{2}$'),
            re.compile(r'^[A-Z]{3}-\d{2}[A-Z]$'),  # ABC-12D
            re.compile(r'^[A-Z]{3}\d{2}[A-Z]$'),
            re.compile(r'^\d{2}-[A-Z]{3}\d{2}$'),  # 12-ABC34
            re.compile(r'^\d{2}[A-Z]{3}\d{2}$'),
        ]
        
        # Enhanced character replacements for common OCR errors
        self.char_replacements = {
            'O': '0', 'Q': '0', 'D': '0', 'G': '0', 'C': '0',
            'I': '1', 'L': '1', 'T': '1', 'J': '1',
            'B': '8', 'S': '5', 'Z': '2', 'A': '4',
            'E': '3', 'F': '3',
            'H': '4', 'M': '4',
            'N': '7', 'P': '7',
            'R': '2', 'U': '2',
            'V': '7', 'W': '7',
            'X': '4', 'Y': '4',
            'K': '8', 'G': '6',
            # Additional common confusions
            'Ø': '0', 'Ö': '0', 'Ó': '0',
            'Í': '1', 'Ì': '1', 'Î': '1',
            'É': '3', 'È': '3', 'Ê': '3',
            'Á': '4', 'À': '4', 'Â': '4',
            'Ñ': '7', 'Ń': '7',
            'Ü': '2', 'Û': '2',
        }
        
        # Common OCR noise characters to remove
        self.noise_chars = ['|', '/', '\\', '(', ')', '[', ']', '{', '}', '<', '>', '=', '+', '*', '&', '^', '%', '$', '#', '@', '!', '?', '.', ',', ';', ':', '"', "'", '`', '~', '_', '-']
        
        # Enhanced plate confidence thresholds
        self.min_confidence = 0.2  # Increased for better quality
        self.high_confidence = 0.7  # Higher threshold for high confidence
        self.excellent_confidence = 0.85  # Excellent confidence threshold
        
        # Real-time processing settings
        self.max_processing_time = 0.5  # Increased for better accuracy
        self.frame_skip = 2  # Process every 2nd frame for better performance
        
        # Plate detection history for consistency
        self.plate_history = deque(maxlen=10)
        self.consistent_detection_threshold = 3  # Need 3 consistent detections
        
        # Enhanced preprocessing parameters
        self.preprocessing_methods = [
            'clahe_gray',
            'otsu_binary',
            'adaptive_gaussian',
            'inverted_binary',
            'morphological',
            'edge_enhanced',
            'contrast_stretched',
            'gaussian_blur'
        ]

    def preprocess_image(self, frame):
        """Enhanced image preprocessing with multiple techniques for better plate detection"""
        try:
            # Convert to grayscale
            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            
            processed_images = []
            
            # 1. CLAHE enhanced grayscale
            clahe = cv2.createCLAHE(clipLimit=3.0, tileGridSize=(8,8))
            clahe_gray = clahe.apply(gray)
            processed_images.append(('clahe_gray', clahe_gray))
            
            # 2. Otsu thresholding
            _, otsu = cv2.threshold(clahe_gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
            processed_images.append(('otsu_binary', otsu))
            
            # 3. Adaptive thresholding with Gaussian
            adaptive_gaussian = cv2.adaptiveThreshold(
                clahe_gray, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY, 15, 3
            )
            processed_images.append(('adaptive_gaussian', adaptive_gaussian))
            
            # 4. Inverted binary for dark plates on light background
            _, inverted = cv2.threshold(clahe_gray, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)
            processed_images.append(('inverted_binary', inverted))
            
            # 5. Morphological operations
            kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (3,3))
            morphological = cv2.morphologyEx(otsu, cv2.MORPH_CLOSE, kernel)
            morphological = cv2.morphologyEx(morphological, cv2.MORPH_OPEN, kernel)
            processed_images.append(('morphological', morphological))
            
            # 6. Edge enhanced
            edges = cv2.Canny(clahe_gray, 50, 150)
            edge_enhanced = cv2.addWeighted(clahe_gray, 0.7, edges, 0.3, 0)
            _, edge_enhanced = cv2.threshold(edge_enhanced, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
            processed_images.append(('edge_enhanced', edge_enhanced))
            
            # 7. Contrast stretching
            p5 = np.percentile(clahe_gray, 5)
            p95 = np.percentile(clahe_gray, 95)
            contrast_stretched = np.clip((clahe_gray - p5) * 255 / (p95 - p5), 0, 255).astype(np.uint8)
            _, contrast_stretched = cv2.threshold(contrast_stretched, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
            processed_images.append(('contrast_stretched', contrast_stretched))
            
            # 8. Gaussian blur for noise reduction
            gaussian_blur = cv2.GaussianBlur(clahe_gray, (5, 5), 0)
            _, gaussian_blur = cv2.threshold(gaussian_blur, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
            processed_images.append(('gaussian_blur', gaussian_blur))
            
            return processed_images
            
        except Exception as e:
            logger.error(f"Error in image preprocessing: {e}")
            return [('basic_gray', gray)] if 'gray' in locals() else []

    def clean_text(self, text):
        """Enhanced text cleaning for better plate recognition"""
        if not text:
            return None
            
        # Convert to uppercase and remove whitespace
        text = text.upper().strip()
        
        # Remove noise characters
        for char in self.noise_chars:
            text = text.replace(char, '')
        
        # Remove extra spaces and normalize
        text = re.sub(r'\s+', '', text)
        
        # Apply character replacements for common OCR errors
        for wrong, right in self.char_replacements.items():
            text = text.replace(wrong, right)
        
        # Additional cleaning for common OCR issues
        text = re.sub(r'[^\w-]', '', text)  # Remove any remaining special chars
        
        # Remove leading/trailing hyphens
        text = text.strip('-')
        
        # Additional filtering for very short or very long texts
        if len(text) < 3 or len(text) > 12:
            return None
            
        return text

    def validate_plate(self, text):
        """Enhanced plate validation with better pattern matching and corrections"""
        if not text:
            return None
            
        text = self.clean_text(text)
        if not text or len(text) < 3:
            return None
        
        logger.info(f"Validating plate: '{text}'")
        
        # Check if it matches any pattern
        for pattern in self.plate_patterns:
            if pattern.fullmatch(text):
                # Format with hyphen if missing
                if '-' not in text:
                    formatted = self.format_plate_with_hyphen(text)
                    if formatted:
                        logger.info(f"  ✓ Formatted as: {formatted}")
                        return formatted
                
                logger.info(f"  ✓ Valid plate: {text}")
                return text
        
        # If no pattern matches, try enhanced OCR corrections
        corrected_text = self.try_enhanced_ocr_corrections(text)
        if corrected_text:
            logger.info(f"  ✓ Corrected to: {corrected_text}")
            return corrected_text
        
        logger.info(f"  ✗ Invalid plate format: {text}")
        return None

    def format_plate_with_hyphen(self, text):
        """Enhanced plate formatting with hyphen in appropriate position"""
        if len(text) < 4:
            return None
            
        # Try different hyphen positions based on common patterns
        if text[:2].isalpha() and len(text) >= 6:
            return f"{text[:2]}-{text[2:]}"
        elif text[:3].isalpha() and len(text) >= 7:
            return f"{text[:3]}-{text[3:]}"
        elif text[:3].isdigit() and len(text) >= 7:
            return f"{text[:3]}-{text[3:]}"
        elif text[:1].isalpha() and len(text) >= 6:
            return f"{text[:1]}-{text[1:]}"
        elif text[:2].isalpha() and len(text) >= 7:
            return f"{text[:2]}-{text[2:]}"
        elif text[:4].isalpha() and len(text) >= 7:
            return f"{text[:4]}-{text[4:]}"
        elif text[:2].isdigit() and len(text) >= 6:
            return f"{text[:2]}-{text[2:]}"
        
        return None

    def try_enhanced_ocr_corrections(self, text):
        """Enhanced OCR corrections for better plate recognition"""
        if len(text) < 5:
            return None
            
        # Enhanced corrections for Sri Lankan plates
        corrections = [
            # Fix common letter/number confusions
            ('0', 'O'), ('1', 'I'), ('1', 'L'), ('5', 'S'), ('8', 'B'), ('2', 'Z'),
            ('O', '0'), ('I', '1'), ('L', '1'), ('S', '5'), ('B', '8'), ('Z', '2'),
            # Fix spacing issues
            (' ', ''), ('  ', ''),
            # Additional common corrections
            ('G', '6'), ('G', '9'), ('6', 'G'), ('9', 'G'),
            ('A', '4'), ('4', 'A'),
            ('E', '3'), ('3', 'E'),
            ('N', '7'), ('7', 'N'),
            ('R', '2'), ('2', 'R'),
        ]
        
        # Try different combinations
        for old, new in corrections:
            corrected = text.replace(old, new)
            for pattern in self.plate_patterns:
                if pattern.fullmatch(corrected):
                    return corrected
        
        # Try adding/removing hyphens at different positions
        if '-' not in text and len(text) >= 6:
            # Try adding hyphen at different positions
            for i in range(2, min(6, len(text)-2)):
                test_text = text[:i] + '-' + text[i:]
                for pattern in self.plate_patterns:
                    if pattern.fullmatch(test_text):
                        return test_text
        
        # Try removing hyphens and checking
        if '-' in text:
            test_text = text.replace('-', '')
            for pattern in self.plate_patterns:
                if pattern.fullmatch(test_text):
                    return test_text
        
        # Try character insertion/deletion for common OCR errors
        if len(text) >= 6:
            # Try removing one character at different positions
            for i in range(len(text)):
                test_text = text[:i] + text[i+1:]
                for pattern in self.plate_patterns:
                    if pattern.fullmatch(test_text):
                        return test_text
        
        return None

    def find_working_camera(self):
        """Find a working camera by trying different indices"""
        logger.info("Searching for working cameras...")
        
        # Try Camera 0 first (most common)
        try:
            logger.info("Testing camera index 0...")
            cap = cv2.VideoCapture(0, cv2.CAP_ANY)
            
            if cap.isOpened():
                logger.info("  Camera 0 opened successfully")
                
                # Try to read a frame to make sure it's working
                ret, frame = cap.read()
                if ret and frame is not None:
                    logger.info(f"  ✓ Camera 0 can read frames (size: {frame.shape})")
                    cap.release()
                    return 0
                else:
                    logger.info("  ✗ Camera 0 opened but cannot read frames")
                cap.release()
            else:
                logger.info("  ✗ Camera 0 failed to open")
                
        except Exception as e:
            logger.error(f"  ✗ Error testing camera 0: {e}")
        
        # Try other indices
        for idx in range(1, 4):
            try:
                logger.info(f"Testing camera index {idx}...")
                cap = cv2.VideoCapture(idx)
                
                if cap.isOpened():
                    logger.info(f"  Camera {idx} opened successfully")
                    
                    ret, frame = cap.read()
                    if ret and frame is not None:
                        logger.info(f"  ✓ Camera {idx} can read frames (size: {frame.shape})")
                        cap.release()
                        return idx
                    else:
                        logger.info(f"  ✗ Camera {idx} opened but cannot read frames")
                    cap.release()
                else:
                    logger.info(f"  ✗ Camera {idx} failed to open")
                    
            except Exception as e:
                logger.error(f"  ✗ Error testing camera {idx}: {e}")
                continue
        
        logger.error("No working cameras found!")
        return None

    def start_camera(self, camera_id=None):
        """Start camera with automatic fallback to working camera"""
        self.camera_error = None
        
        try:
            if camera_id is not None:
                self.camera_index = camera_id
            else:
                working_camera = self.find_working_camera()
                if working_camera is not None:
                    self.camera_index = working_camera
                else:
                    logger.warning("No cameras found in search, trying Camera 0 directly...")
                    self.camera_index = 0
            
            logger.info(f"Attempting to start camera on index {self.camera_index}...")
            
            # Try different backends
            backends = [
                cv2.CAP_ANY,
                cv2.CAP_DSHOW,
                cv2.CAP_MSMF,
            ]
            
            for backend in backends:
                try:
                    logger.info(f"Trying backend: {backend}")
                    self.camera = cv2.VideoCapture(self.camera_index, backend)
                    
                    if self.camera.isOpened():
                        logger.info(f"Camera opened with backend {backend}")
                        
                        # Set camera properties for better performance
                        self.camera.set(cv2.CAP_PROP_FRAME_WIDTH, 1920)  # Higher resolution
                        self.camera.set(cv2.CAP_PROP_FRAME_HEIGHT, 1080)
                        self.camera.set(cv2.CAP_PROP_FPS, 30)
                        self.camera.set(cv2.CAP_PROP_AUTOFOCUS, 1)  # Enable autofocus
                        self.camera.set(cv2.CAP_PROP_BRIGHTNESS, 128)  # Set brightness
                        self.camera.set(cv2.CAP_PROP_CONTRAST, 128)  # Set contrast
                        self.camera.set(cv2.CAP_PROP_SATURATION, 128)  # Set saturation
                        
                        # Test if we can actually read frames
                        ret, frame = self.camera.read()
                        if ret and frame is not None:
                            self.scanning = True
                            logger.info(f"✓ Camera started successfully on index {self.camera_index} with backend {backend}")
                            return True
                        else:
                            logger.warning(f"Camera opened but cannot read frames with backend {backend}")
                            self.camera.release()
                            self.camera = None
                    else:
                        logger.warning(f"Failed to open camera with backend {backend}")
                        if self.camera:
                            self.camera.release()
                            self.camera = None
                            
                except Exception as e:
                    logger.error(f"Error with backend {backend}: {e}")
                    if self.camera:
                        self.camera.release()
                        self.camera = None
                    continue
            
            self.camera_error = f"Failed to open camera on index {self.camera_index}. Check camera permissions and connections."
            logger.error(f"Camera start failed: {self.camera_error}")
            return False
            
        except Exception as e:
            self.camera_error = f"Unexpected error starting camera: {str(e)}"
            logger.error(f"Unexpected error: {e}")
            return False

    def stop_camera(self):
        """Stop camera and release resources"""
        self.scanning = False
        self.stop_processing = True
        
        if self.processing_thread and self.processing_thread.is_alive():
            self.processing_thread.join(timeout=2.0)
        
        if self.camera and self.camera.isOpened():
            self.camera.release()
            self.camera = None
        logger.info("Camera stopped")

    def process_frame(self):
        """Enhanced frame processing with multiple preprocessing approaches and better OCR"""
        if not self.scanning or not self.camera or not self.camera.isOpened():
            return None, []
        
        # Check scan cooldown to prevent duplicate scans
        current_time = time.time()
        if current_time - self.last_scan_time < self.scan_cooldown:
            return None, []
        
        try:
            ret, frame = self.camera.read()
            if not ret or frame is None:
                logger.warning("Failed to read frame from camera")
                return None, []
            
            # Add frame to buffer
            self.frame_buffer.append(frame)
            
            # Preprocess image with multiple approaches
            processed_images = self.preprocess_image(frame)
            
            all_results = []
            
            # Try OCR on each preprocessed image with timeout
            start_time = time.time()
            for method_name, processed_img in processed_images:
                if time.time() - start_time > self.max_processing_time:
                    logger.warning("Processing timeout reached")
                    break
                    
                try:
                    # Enhanced OCR settings for better accuracy
                    results = self.reader.readtext(
                        processed_img,
                        decoder='greedy',
                        allowlist='ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789-',
                        width_ths=0.3,  # More sensitive to text width
                        text_threshold=0.3,  # Higher threshold for better quality
                        height_ths=0.2,  # More sensitive to text height
                        paragraph=False,
                        detail=1
                    )
                    
                    logger.info(f"Processing method {method_name} found {len(results)} text regions")
                    for (bbox, text, prob) in results:
                        logger.info(f"  Raw text: '{text}' (confidence: {prob:.2f})")
                        all_results.append((bbox, text, prob, method_name))
                        
                except Exception as e:
                    logger.error(f"Error in processing method {method_name}: {e}")
                    continue
            
            # Remove duplicates and sort by confidence
            unique_results = []
            seen_texts = set()
            
            for (bbox, text, prob, method_name) in all_results:
                clean_text = self.clean_text(text)
                if clean_text and clean_text not in seen_texts and len(clean_text) >= 3:
                    seen_texts.add(clean_text)
                    unique_results.append((bbox, clean_text, prob, method_name))
            
            # Sort by confidence
            unique_results.sort(key=lambda x: x[2], reverse=True)
            
            plates = []
            for (bbox, text, prob, method_name) in unique_results:
                if prob > self.min_confidence:
                    plate = self.validate_plate(text)
                    if plate:
                        # Enhanced confidence scoring based on method and consistency
                        enhanced_confidence = self.calculate_enhanced_confidence(prob, method_name, plate)
                        
                        plates.append({
                            'text': plate,
                            'confidence': enhanced_confidence,
                            'bbox': bbox,
                            'method': method_name,
                            'raw_confidence': prob
                        })
                        logger.info(f"✓ Valid plate detected: {plate} (confidence: {enhanced_confidence:.2f}, method: {method_name})")
                        
                        # Update last scan time to prevent duplicates
                        self.last_scan_time = current_time
                    else:
                        logger.debug(f"✗ Invalid plate format: {text} (confidence: {prob:.2f})")
            
            if not plates:
                logger.debug("No valid plates detected. All detected texts:")
                for (bbox, text, prob, method_name) in unique_results[:5]:
                    logger.debug(f"  '{text}' (confidence: {prob:.2f}, method: {method_name})")
            
            return frame, plates
            
        except Exception as e:
            logger.error(f"Error processing frame: {e}")
            return None, []

    def calculate_enhanced_confidence(self, base_confidence, method_name, plate_text):
        """Calculate enhanced confidence score based on multiple factors"""
        # Base confidence from OCR
        enhanced_confidence = base_confidence
        
        # Method-specific confidence adjustments
        method_weights = {
            'clahe_gray': 1.0,
            'otsu_binary': 1.1,
            'adaptive_gaussian': 1.05,
            'inverted_binary': 0.95,
            'morphological': 1.15,
            'edge_enhanced': 1.1,
            'contrast_stretched': 1.05,
            'gaussian_blur': 0.9
        }
        
        method_weight = method_weights.get(method_name, 1.0)
        enhanced_confidence *= method_weight
        
        # Length-based confidence (optimal length for Sri Lankan plates)
        if 6 <= len(plate_text) <= 9:
            enhanced_confidence *= 1.1
        elif len(plate_text) < 5 or len(plate_text) > 10:
            enhanced_confidence *= 0.9
        
        # Hyphen presence confidence
        if '-' in plate_text:
            enhanced_confidence *= 1.05
        
        # Character distribution confidence
        alpha_count = sum(1 for c in plate_text if c.isalpha())
        digit_count = sum(1 for c in plate_text if c.isdigit())
        
        if alpha_count >= 2 and digit_count >= 3:
            enhanced_confidence *= 1.1
        elif alpha_count == 0 or digit_count == 0:
            enhanced_confidence *= 0.8
        
        # Consistency with previous detections
        if plate_text in self.plate_history:
            enhanced_confidence *= 1.2
        
        # Cap confidence at 1.0
        return min(enhanced_confidence, 1.0)

    def save_scan(self, frame, plate_number, scan_type, confidence=0.8):
        """Enhanced scan saving with better error handling"""
        try:
            # Encode frame as JPEG with better quality
            encode_param = [int(cv2.IMWRITE_JPEG_QUALITY), 90]
            _, buffer = cv2.imencode('.jpg', frame, encode_param)
            image_file = ContentFile(
                buffer.tobytes(),
                name=f"{scan_type}_{plate_number}_{datetime.now().strftime('%Y%m%d%H%M%S')}.jpg"
            )
            
            # Use Django's transaction.atomic properly
            with transaction.atomic():
                # Get or create vehicle
                vehicle, created = Vehicle.objects.get_or_create(
                    plate_number=plate_number
                )
                
                if created:
                    logger.info(f"Created new vehicle record: {plate_number}")
                
                # Check if vehicle is registered (has booking)
                try:
                    from booking.models import Booking
                    booking = Booking.objects.filter(vehicle_no=plate_number).first()
                    if booking:
                        vehicle.is_registered = True
                        vehicle.save()
                        logger.info(f"Vehicle {plate_number} is registered with booking")
                except Exception as e:
                    logger.error(f"Error checking booking: {e}")
                
                # Handle parking session
                parking_session = None
                if scan_type == 'ENTRY':
                    # Check if vehicle is already parked
                    existing_session = ParkingSession.objects.filter(
                        vehicle=vehicle,
                        is_active=True
                    ).first()
                    
                    if existing_session:
                        logger.warning(f"Vehicle {plate_number} already has active parking session")
                        parking_session = existing_session
                    else:
                        # Create new parking session
                        parking_session = ParkingSession.objects.create(
                            vehicle=vehicle
                        )
                        logger.info(f"Created new parking session for {plate_number}")
                        
                elif scan_type == 'EXIT':
                    # Find active parking session
                    parking_session = ParkingSession.objects.filter(
                        vehicle=vehicle,
                        is_active=True
                    ).first()
                    
                    if parking_session:
                        parking_session.exit_time = timezone.now()
                        parking_session.is_active = False
                        parking_session.total_amount = parking_session.calculate_amount()
                        parking_session.save()
                        
                        logger.info(f"Completed parking session for {plate_number}, amount: Rs. {parking_session.total_amount}")
                        
                        # Send payment email if vehicle is registered
                        if vehicle.is_registered:
                            try:
                                parking_session.send_payment_email()
                                logger.info(f"Payment email sent for {plate_number}")
                            except Exception as e:
                                logger.error(f"Failed to send payment email: {e}")
                    else:
                        logger.warning(f"No active parking session found for {plate_number}")
                
                # Create scan record
                scan_record = ScanRecord.objects.create(
                    vehicle=vehicle,
                    scan_type=scan_type,
                    image=image_file,
                    parking_session=parking_session,
                    confidence_score=confidence
                )
                
                logger.info(f"Scan record saved: {scan_type} for {plate_number}")
                
            return True
        except Exception as e:
            logger.error(f"Save error: {e}")
            return False

    def get_parking_status(self, plate_number):
        """Get current parking status for a vehicle"""
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
                    'estimated_cost': active_session.calculate_amount()
                }
            else:
                return {'is_parked': False}
        except Vehicle.DoesNotExist:
            return {'is_parked': False, 'vehicle_not_found': True}

    def get_camera_error(self):
        """Get the last camera error message"""
        return self.camera_error

    def scan_until_plate(self, timeout=20):
        """
        Enhanced plate scanning with consistency checking and better accuracy.
        Continuously scan frames for up to `timeout` seconds until a valid plate is detected.
        Returns (frame, plate_dict) or (None, None) if not found.
        """
        start_time = time.time()
        plate_candidates = {}  # Track candidates with their confidence scores
        best_frame = None
        frame_count = 0

        logger.info(f"Starting enhanced plate scan with {timeout}s timeout...")

        while time.time() - start_time < timeout:
            frame_count += 1
            
            # Skip frames for performance
            if frame_count % self.frame_skip != 0:
                time.sleep(0.033)  # ~30 FPS
                continue
                
            frame, plates = self.process_frame()
            if plates:
                # Track all plate candidates
                for plate_info in plates:
                    plate_text = plate_info['text']
                    confidence = plate_info['confidence']
                    
                    if plate_text not in plate_candidates:
                        plate_candidates[plate_text] = {
                            'count': 0,
                            'total_confidence': 0,
                            'max_confidence': 0,
                            'frame': frame,
                            'plate_info': plate_info
                        }
                    
                    plate_candidates[plate_text]['count'] += 1
                    plate_candidates[plate_text]['total_confidence'] += confidence
                    plate_candidates[plate_text]['max_confidence'] = max(
                        plate_candidates[plate_text]['max_confidence'], confidence
                    )
                    plate_candidates[plate_text]['frame'] = frame
                    plate_candidates[plate_text]['plate_info'] = plate_info
                    
                    # Add to history for consistency checking
                    self.plate_history.append(plate_text)
                    
                    logger.info(f"Plate candidate: {plate_text} (count: {plate_candidates[plate_text]['count']}, confidence: {confidence:.2f})")
                
                # Check for consistent detections
                for plate_text, candidate_info in plate_candidates.items():
                    count = candidate_info['count']
                    avg_confidence = candidate_info['total_confidence'] / count
                    max_confidence = candidate_info['max_confidence']
                    
                    # Criteria for accepting a plate:
                    # 1. High confidence single detection
                    # 2. Multiple consistent detections with good average confidence
                    # 3. Excellent confidence regardless of count
                    
                    if (max_confidence > self.excellent_confidence or
                        (count >= 2 and avg_confidence > self.high_confidence) or
                        (count >= 3 and avg_confidence > self.min_confidence)):
                        
                        logger.info(f"✓ Plate accepted: {plate_text} (count: {count}, avg_conf: {avg_confidence:.2f}, max_conf: {max_confidence:.2f})")
                        
                        # Update the plate info with enhanced confidence
                        final_plate_info = candidate_info['plate_info'].copy()
                        final_plate_info['confidence'] = max_confidence
                        final_plate_info['detection_count'] = count
                        final_plate_info['avg_confidence'] = avg_confidence
                        
                        return candidate_info['frame'], final_plate_info
                    
            # Progress update every 5 seconds
            elapsed = time.time() - start_time
            if int(elapsed) % 5 == 0 and int(elapsed) > 0:
                logger.info(f"Scanning... {elapsed:.1f}s elapsed, candidates: {len(plate_candidates)}")
                for plate_text, info in plate_candidates.items():
                    logger.info(f"  {plate_text}: count={info['count']}, avg_conf={info['total_confidence']/info['count']:.2f}")
            
            time.sleep(0.033)  # ~30 FPS

        logger.info(f"No consistent plate found within {timeout}s timeout")
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
            'high_confidence': self.high_confidence,
            'excellent_confidence': self.excellent_confidence,
            'frame_buffer_size': len(self.frame_buffer),
            'plate_history_size': len(self.plate_history),
            'preprocessing_methods': len(self.preprocessing_methods)
        }
        
        # Test camera if connected
        if status['camera_connected'] and self.camera:
            try:
                ret, frame = self.camera.read()
                status['camera_reading'] = ret and frame is not None
                if status['camera_reading']:
                    status['frame_size'] = f"{frame.shape[1]}x{frame.shape[0]}"
            except Exception as e:
                status['camera_reading'] = False
                status['camera_error'] = str(e)
        
        return status
      