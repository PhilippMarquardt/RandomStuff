#!/usr/bin/env python3
"""
Test script to validate the headline extraction functionality
"""

import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), 'app'))

from app.services.pdf_comparison_service import get_first_headline

def test_headline_extraction():
    """Test the headline extraction function with various markdown patterns"""
    
    # Test cases
    test_cases = [
        # Standard markdown heading
        ("# Main Title\nSome content here", "Main Title"),
        
        # Bold standalone line
        ("**Important Notice**\nSome content", "Important Notice"),
        
        # Heading with multiple #
        ("## Section 2.1\nContent follows", "Section 2.1"),
        
        # Multiple lines with heading first
        ("### Sub-section\nLine 1\nLine 2", "Sub-section"),
        
        # Bold line with spaces
        ("  **  Spaced Title  **  \nContent", "Spaced Title"),
        
        # No headline found
        ("Just regular text\nMore text\nNo headlines", None),
        
        # Mixed content with heading
        ("Some intro text\n# Found Heading\nMore content", "Found Heading"),
        
        # Bold not standalone (should not match)
        ("This **bold** text should not match\nMore content", None),
        
        # Heading with whitespace
        ("   ## Financial Report   \nData follows", "Financial Report"),
    ]
    
    print("Testing headline extraction function...")
    print("=" * 50)
    
    passed = 0
    failed = 0
    
    for i, (input_text, expected) in enumerate(test_cases, 1):
        result = get_first_headline(input_text)
        
        if result == expected:
            print(f"✅ Test {i}: PASSED")
            print(f"   Input: {repr(input_text[:50])}...")
            print(f"   Expected: {expected}")
            print(f"   Got: {result}")
            passed += 1
        else:
            print(f"❌ Test {i}: FAILED")
            print(f"   Input: {repr(input_text[:50])}...")
            print(f"   Expected: {expected}")
            print(f"   Got: {result}")
            failed += 1
        print()
    
    print("=" * 50)
    print(f"Results: {passed} passed, {failed} failed")
    return failed == 0

if __name__ == "__main__":
    success = test_headline_extraction()
    if success:
        print("🎉 All tests passed!")
        exit(0)
    else:
        print("💥 Some tests failed!")
        exit(1) 