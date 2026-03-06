#!/usr/bin/env python3
"""
Quick API test script to verify all endpoints are working correctly.
Run this to test the clinical trial matching system.
"""

import requests
import json
import sys

BASE_URL = "http://localhost:5000/api"

def test_health():
    """Test health endpoint"""
    try:
        response = requests.get(f"{BASE_URL}/health")
        if response.status_code == 200:
            print("✅ Health check: PASSED")
            return True
        else:
            print(f"❌ Health check: FAILED ({response.status_code})")
            return False
    except Exception as e:
        print(f"❌ Health check: ERROR - {e}")
        return False

def test_sample_data():
    """Test sample data endpoint"""
    try:
        response = requests.get(f"{BASE_URL}/sample-data")
        if response.status_code == 200:
            data = response.json()
            print(f"✅ Sample data: PASSED ({data['total_patients']} patients, {data['total_trials']} trials)")
            return data
        else:
            print(f"❌ Sample data: FAILED ({response.status_code})")
            return None
    except Exception as e:
        print(f"❌ Sample data: ERROR - {e}")
        return None

def test_demo_match():
    """Test demo matching endpoint"""
    try:
        response = requests.get(f"{BASE_URL}/demo-match")
        if response.status_code == 200:
            data = response.json()
            print(f"✅ Demo match: PASSED (Patient {data['demo_patient']['patient_id']}, {len(data['top_matches'])} matches)")
            
            # Show top match details
            if data['top_matches']:
                top_match = data['top_matches'][0]
                score = round(top_match['eligibility_score'] * 100)
                confidence = round(top_match['confidence'] * 100)
                print(f"   Top match: {top_match['title']} ({score}% match, {confidence}% confidence)")
            
            return True
        else:
            print(f"❌ Demo match: FAILED ({response.status_code})")
            return False
    except Exception as e:
        print(f"❌ Demo match: ERROR - {e}")
        return False

def test_anonymization():
    """Test patient anonymization"""
    sample_patient = {
        "patient_id": "TEST001",
        "name": "John Test",
        "age": 45,
        "gender": "male",
        "location": "San Francisco, CA",
        "diagnosis": ["Type 2 Diabetes"]
    }
    
    try:
        response = requests.post(f"{BASE_URL}/anonymize-patient", json=sample_patient)
        if response.status_code == 200:
            data = response.json()
            anon_patient = data['anonymized_patient']
            print(f"✅ Anonymization: PASSED")
            print(f"   Original ID: {sample_patient['patient_id']} → Anonymous ID: {anon_patient['patient_id']}")
            print(f"   Age: {sample_patient['age']} → Age Range: {anon_patient.get('age_range', 'N/A')}")
            return True
        else:
            print(f"❌ Anonymization: FAILED ({response.status_code})")
            return False
    except Exception as e:
        print(f"❌ Anonymization: ERROR - {e}")
        return False

def main():
    """Run all API tests"""
    print("🧪 Testing AI-Powered Clinical Trial Matching Engine API")
    print("=" * 60)
    
    tests_passed = 0
    total_tests = 4
    
    # Run tests
    if test_health():
        tests_passed += 1
    
    sample_data = test_sample_data()
    if sample_data:
        tests_passed += 1
    
    if test_demo_match():
        tests_passed += 1
    
    if test_anonymization():
        tests_passed += 1
    
    # Results
    print("=" * 60)
    print(f"📊 Test Results: {tests_passed}/{total_tests} tests passed")
    
    if tests_passed == total_tests:
        print("🎉 All tests PASSED! System is ready for hackathon demo.")
        return 0
    else:
        print("⚠️  Some tests FAILED. Check the API server.")
        return 1

if __name__ == "__main__":
    sys.exit(main())
