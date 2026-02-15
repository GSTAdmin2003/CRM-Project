#!/usr/bin/env python
"""
Test script for lead form field requirements (no database access)
"""
import os
import sys
import django

# Add project to path
sys.path.append('/home/shuubb/Desktop/Main Codebase/CRM Project')

# Setup Django (minimal settings to avoid database)
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')

# Import form class
from apps.crm.forms import LeadForm


class MockUser:
    """Mock user object for testing"""
    def __init__(self):
        self.sales_team = None
        self.id = 1
    
    def is_sales_executive(self):
        return False
    
    def is_sales_manager(self):
        return False


def test_form_field_requirements():
    """Test that contact fields are optional in form definition"""
    print("Testing Lead Form Field Requirements")
    print("=" * 50)
    
    try:
        # Create form instance with mock user
        user = MockUser()
        form = LeadForm(user=user)
        
        # Check field requirements
        print("Field requirements:")
        print(f"  company.required: {form.fields['company'].required}")
        print(f"  title.required: {form.fields['title'].required}")
        print(f"  full_name.required: {form.fields['full_name'].required}")
        print(f"  email.required: {form.fields['email'].required}")
        print(f"  phone.required: {form.fields['phone'].required}")
        print(f"  position.required: {form.fields['position'].required}")
        
        # Verify contact fields are optional
        contact_fields = ['full_name', 'email', 'phone', 'position']
        all_optional = all(not form.fields[field].required for field in contact_fields)
        
        if all_optional:
            print("\n✅ SUCCESS: All contact fields are optional!")
        else:
            print("\n❌ FAILURE: Some contact fields are still required:")
            for field in contact_fields:
                if form.fields[field].required:
                    print(f"  - {field} is required")
        
        # Check if title and company are still required
        required_fields = ['title', 'company']
        still_required = all(form.fields[field].required for field in required_fields)
        
        if still_required:
            print("✅ SUCCESS: Required fields (title, company) are still required!")
        else:
            print("❌ WARNING: Some required fields are no longer required:")
            for field in required_fields:
                if not form.fields[field].required:
                    print(f"  - {field} is not required")
        
        return all_optional and still_required
        
    except Exception as e:
        print(f"❌ Test failed with error: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_form_validation_logic():
    """Test form validation without database"""
    print("\nTesting Form Validation Logic")
    print("=" * 50)
    
    try:
        user = MockUser()
        
        # Test data with only required fields
        test_data = {
            'title': 'Test Lead',
            'company': 'Test Company',
            # No contact fields
        }
        
        form = LeadForm(data=test_data, user=user)
        
        # Note: This will still fail validation due to missing stage, but we can check
        # that contact fields are not causing validation errors
        is_valid = form.is_valid()
        errors = form.errors
        
        print(f"Form validation result: {is_valid}")
        print("Form errors:")
        for field, error_list in errors.items():
            print(f"  {field}: {error_list}")
        
        # Check if contact fields cause validation errors
        contact_fields = ['full_name', 'email', 'phone', 'position']
        contact_errors = any(field in errors for field in contact_fields)
        
        if not contact_errors:
            print("\n✅ SUCCESS: No validation errors for contact fields!")
            return True
        else:
            print("\n❌ FAILURE: Contact fields are causing validation errors")
            return False
            
    except Exception as e:
        print(f"❌ Test failed with error: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == '__main__':
    print("Testing Lead Form Changes")
    print("=" * 70)
    
    test1_passed = test_form_field_requirements()
    test2_passed = test_form_validation_logic()
    
    print("\n" + "=" * 70)
    print("SUMMARY:")
    print(f"  Field Requirements Test: {'✅ PASSED' if test1_passed else '❌ FAILED'}")
    print(f"  Validation Logic Test: {'✅ PASSED' if test2_passed else '❌ FAILED'}")
    
    if test1_passed and test2_passed:
        print("\n🎉 ALL TESTS PASSED! Contact creation is now optional for leads.")
    else:
        print("\n⚠️  Some tests failed. Please review the implementation.")