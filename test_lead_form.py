#!/usr/bin/env python
"""
Test script for lead form validation without contact information
"""
import os
import sys
import django

# Add project to path
sys.path.append('/home/shuubb/Desktop/Main Codebase/CRM Project')

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
django.setup()

from apps.crm.forms import LeadForm
from core.models import User


def test_lead_form_without_contact():
    """Test that lead form validates without contact information"""
    print("Testing Lead Form Validation without Contact Information")
    print("=" * 60)
    
    try:
        # Get a user for testing (assuming one exists)
        user = User.objects.first()
        if not user:
            print("Error: No users found. Cannot test form.")
            return
        
        # Test data with only required fields (title and company)
        test_data = {
            'title': 'Test Lead Without Contact',
            'company': 'Test Company Inc',
            'estimated_value': '10000.00',
            'probability': '50',
            'stage': '1',  # Assuming first stage exists
        }
        
        # Test form with minimal data
        form = LeadForm(data=test_data, user=user)
        
        print(f"Form data: {test_data}")
        print(f"Form is valid: {form.is_valid()}")
        
        if not form.is_valid():
            print("Form validation errors:")
            for field, errors in form.errors.items():
                print(f"  {field}: {errors}")
        else:
            print("✅ SUCCESS: Form validates without contact information!")
            
            # Test saving the form
            try:
                lead = form.save()
                print(f"✅ Lead created successfully: {lead}")
                print(f"   - Title: {lead.title}")
                print(f"   - Company: {lead.company}")
                print(f"   - Full Name: '{lead.full_name}' (should be empty)")
                print(f"   - Email: '{lead.email}' (should be empty)")
            except Exception as e:
                print(f"❌ Error saving lead: {e}")
                
    except Exception as e:
        print(f"❌ Test failed with error: {e}")
        import traceback
        traceback.print_exc()


def test_lead_form_with_partial_contact():
    """Test that lead form validates with partial contact information"""
    print("\nTesting Lead Form with Partial Contact Information")
    print("=" * 60)
    
    try:
        user = User.objects.first()
        if not user:
            print("Error: No users found. Cannot test form.")
            return
        
        # Test data with only email, no name
        test_data = {
            'title': 'Test Lead With Email Only',
            'company': 'Another Test Company',
            'email': 'test@example.com',
            'estimated_value': '15000.00',
            'probability': '75',
            'stage': '1',
        }
        
        form = LeadForm(data=test_data, user=user)
        
        print(f"Form data: {test_data}")
        print(f"Form is valid: {form.is_valid()}")
        
        if not form.is_valid():
            print("Form validation errors:")
            for field, errors in form.errors.items():
                print(f"  {field}: {errors}")
        else:
            print("✅ SUCCESS: Form validates with email but no name!")
            
            try:
                lead = form.save()
                print(f"✅ Lead created successfully: {lead}")
                print(f"   - Title: {lead.title}")
                print(f"   - Email: {lead.email}")
                print(f"   - Full Name: '{lead.full_name}' (should be empty)")
                print(f"   - Contact should NOT be created (no name)")
            except Exception as e:
                print(f"❌ Error saving lead: {e}")
                
    except Exception as e:
        print(f"❌ Test failed with error: {e}")
        import traceback
        traceback.print_exc()


if __name__ == '__main__':
    test_lead_form_without_contact()
    test_lead_form_with_partial_contact()
    print("\nTest completed!")