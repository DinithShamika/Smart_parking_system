#!/usr/bin/env python3
"""
Simple test script for the fast text scanner
Tests letter and number recognition (A-Z, 0-9)
"""

import os
import sys
import django
from pathlib import Path

# Add the project root to Python path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'smart_parking.settings')
django.setup()

from plate_scanner.scanner import PlateScanner
import logging

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def test_text_validation():
    """Test text validation with letters and numbers"""
    scanner = PlateScanner()
    
    # Test cases for letters and numbers
    test_cases = [
        # Valid combinations
        ("ABC123", True),
        ("XYZ789", True),
        ("123ABC", True),
        ("ABC", True),
        ("123", True),
        ("ABCDEF", True),
        ("123456", True),
        ("A1B2C3", True),
        ("1A2B3C", True),
        
        # Invalid cases
        ("AB", False),  # Too short
        ("12", False),  # Too short
        ("ABCDEFGHIJK", False),  # Too long
        ("12345678901", False),  # Too long
        ("ABC-123", False),  # Contains special character
        ("ABC 123", False),  # Contains space
        ("", False),  # Empty
        ("ABC@123", False),  # Contains special character
    ]
    
    print("Testing text validation:")
    print("=" * 40)
    
    passed = 0
    total = len(test_cases)
    
    for text, expected in test_cases:
        result = scanner.validate_text(text)
        is_valid = result is not None
        status = "✓ PASS" if is_valid == expected else "✗ FAIL"
        
        if is_valid == expected:
            passed += 1
        
        print(f"{text:15} -> {is_valid:5} (Expected: {expected:5}) {status}")
    
    print(f"\nResults: {passed}/{total} tests passed")
    return passed == total

def test_character_replacements():
    """Test character replacement logic"""
    scanner = PlateScanner()
    
    # Test character replacements
    test_replacements = [
        ("ABCl23", "ABC123"),  # l -> 1
        ("ABC0l23", "ABC0123"),  # O -> 0, l -> 1
        ("ABC8l23", "ABC8123"),  # B -> 8, l -> 1
        ("ABC5l23", "ABC5123"),  # S -> 5, l -> 1
        ("ABC2l23", "ABC2123"),  # Z -> 2, l -> 1
    ]
    
    print("\nTesting character replacements:")
    print("=" * 40)
    
    passed = 0
    total = len(test_replacements)
    
    for input_text, expected in test_replacements:
        result = scanner.clean_text(input_text)
        status = "✓ PASS" if result == expected else "✗ FAIL"
        
        if result == expected:
            passed += 1
        
        print(f"{input_text:15} -> {result:15} (Expected: {expected:15}) {status}")
    
    print(f"\nResults: {passed}/{total} tests passed")
    return passed == total

def test_scanner_initialization():
    """Test scanner initialization"""
    print("\nTesting scanner initialization:")
    print("=" * 40)
    
    try:
        scanner = PlateScanner()
        print("✓ Scanner initialized successfully")
        
        # Check scanner properties
        print(f"✓ Scan cooldown: {scanner.scan_cooldown}s")
        print(f"✓ Min confidence: {scanner.min_confidence}")
        print(f"✓ Frame skip: {scanner.frame_skip}")
        print(f"✓ Max processing time: {scanner.max_processing_time}s")
        print(f"✓ Text patterns: {len(scanner.text_patterns)}")
        print(f"✓ Character replacements: {len(scanner.char_replacements)}")
        
        return True
        
    except Exception as e:
        print(f"✗ Scanner initialization failed: {e}")
        return False

def test_pattern_matching():
    """Test regex pattern matching"""
    scanner = PlateScanner()
    
    print("\nTesting pattern matching:")
    print("=" * 40)
    
    test_patterns = [
        # Pattern 1: Any combination of letters and numbers (3-10 characters)
        ("ABC123", True),
        ("XYZ789", True),
        ("A1B2C3", True),
        ("123ABC", True),
        ("AB", False),  # Too short
        ("ABCDEFGHIJK", False),  # Too long
        
        # Pattern 2: Letters only (2-6 characters)
        ("ABC", True),
        ("XYZ", True),
        ("ABCDEF", True),
        ("A", False),  # Too short
        ("ABCDEFG", False),  # Too long
        ("ABC123", False),  # Contains numbers
        
        # Pattern 3: Numbers only (3-8 digits)
        ("123", True),
        ("456789", True),
        ("12", False),  # Too short
        ("123456789", False),  # Too long
        ("ABC", False),  # Contains letters
    ]
    
    passed = 0
    total = len(test_patterns)
    
    for text, expected in test_patterns:
        result = scanner.validate_text(text)
        is_valid = result is not None
        status = "✓ PASS" if is_valid == expected else "✗ FAIL"
        
        if is_valid == expected:
            passed += 1
        
        print(f"{text:15} -> {is_valid:5} (Expected: {expected:5}) {status}")
    
    print(f"\nResults: {passed}/{total} tests passed")
    return passed == total

def main():
    """Run all tests"""
    print("Fast Text Scanner Test Suite")
    print("=" * 50)
    print("Testing A-Z letters and 0-9 numbers recognition")
    print("=" * 50)
    
    tests = [
        ("Scanner Initialization", test_scanner_initialization),
        ("Text Validation", test_text_validation),
        ("Character Replacements", test_character_replacements),
        ("Pattern Matching", test_pattern_matching),
    ]
    
    passed_tests = 0
    total_tests = len(tests)
    
    for test_name, test_func in tests:
        print(f"\n{'='*20} {test_name} {'='*20}")
        try:
            if test_func():
                passed_tests += 1
                print(f"✓ {test_name} PASSED")
            else:
                print(f"✗ {test_name} FAILED")
        except Exception as e:
            print(f"✗ {test_name} ERROR: {e}")
    
    print("\n" + "=" * 50)
    print(f"OVERALL RESULTS: {passed_tests}/{total_tests} tests passed")
    
    if passed_tests == total_tests:
        print("\n✓ ALL TESTS PASSED!")
        print("\nThe scanner is ready for fast text recognition:")
        print("- Supports A-Z letters and 0-9 numbers")
        print("- Fast real-time processing")
        print("- Simple character corrections")
        print("- Efficient pattern matching")
    else:
        print(f"\n✗ {total_tests - passed_tests} tests failed")
        print("Please check the errors above and fix them.")

if __name__ == "__main__":
    main() 