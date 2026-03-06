#!/usr/bin/env python3
"""
Test script for file upload functionality.
"""

import requests
import os

BASE_URL = "http://localhost:5000/api"

def test_csv_upload():
    """Test CSV file upload and processing."""
    try:
        csv_file_path = os.path.join(os.path.dirname(__file__), 'python-api', 'data', 'sample_patients.csv')
        
        if not os.path.exists(csv_file_path):
            print(f"❌ CSV file not found: {csv_file_path}")
            return False
        
        with open(csv_file_path, 'rb') as f:
            files = {'file': ('sample_patients.csv', f, 'text/csv')}
            response = requests.post(f"{BASE_URL}/upload-patients", files=files)
        
        if response.status_code == 200:
            data = response.json()
            print(f"✅ CSV upload: PASSED ({data['total_patients']} patients processed)")
            print(f"   File: {data['file_info']['filename']} ({data['file_info']['file_type']} format)")
            return True
        else:
            print(f"❌ CSV upload: FAILED ({response.status_code})")
            print(f"   Error: {response.json().get('message', 'Unknown error')}")
            return False
    except Exception as e:
        print(f"❌ CSV upload: ERROR - {e}")
        return False

def test_csv_upload_and_match():
    """Test CSV file upload with immediate matching."""
    try:
        csv_file_path = os.path.join(os.path.dirname(__file__), 'python-api', 'data', 'sample_patients.csv')
        
        if not os.path.exists(csv_file_path):
            print(f"❌ CSV file not found: {csv_file_path}")
            return False
        
        with open(csv_file_path, 'rb') as f:
            files = {'file': ('sample_patients.csv', f, 'text/csv')}
            response = requests.post(f"{BASE_URL}/upload-and-match", files=files)
        
        if response.status_code == 200:
            data = response.json()
            print(f"✅ CSV upload & match: PASSED ({data['total_patients']} patients matched)")
            
            # Show first patient's top match
            if data['matching_results']:
                first_result = data['matching_results'][0]
                if first_result['ranked_trials']:
                    top_trial = first_result['ranked_trials'][0]
                    score = round(top_trial['eligibility_score'] * 100)
                    print(f"   Top match for {first_result['patient_id']}: {score}% - {top_trial['title']}")
            
            return True
        else:
            print(f"❌ CSV upload & match: FAILED ({response.status_code})")
            print(f"   Error: {response.json().get('message', 'Unknown error')}")
            return False
    except Exception as e:
        print(f"❌ CSV upload & match: ERROR - {e}")
        return False

def main():
    """Run file upload tests."""
    print("🧪 Testing File Upload Functionality")
    print("=" * 50)
    
    tests_passed = 0
    total_tests = 2
    
    if test_csv_upload():
        tests_passed += 1
    
    if test_csv_upload_and_match():
        tests_passed += 1
    
    print("=" * 50)
    print(f"📊 File Upload Test Results: {tests_passed}/{total_tests} tests passed")
    
    if tests_passed == total_tests:
        print("🎉 All file upload tests PASSED! File upload feature is ready.")
        return 0
    else:
        print("⚠️  Some tests FAILED. Check the API server and file paths.")
        return 1

if __name__ == "__main__":
    import sys
    sys.exit(main())
