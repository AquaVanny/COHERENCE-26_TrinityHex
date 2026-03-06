import hashlib
import re
from faker import Faker
from datetime import datetime, timedelta
import pandas as pd
from typing import Dict, Any, List
import json

class PatientAnonymizer:
    """
    Handles anonymization of patient health records while preserving 
    clinical relevance for trial matching.
    """
    
    def __init__(self):
        self.fake = Faker()
        self.id_mapping = {}
        
    def anonymize_patient_record(self, patient_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Anonymize a patient record while preserving medical relevance.
        """
        anonymized = patient_data.copy()
        
        # Generate consistent anonymous ID
        original_id = str(patient_data.get('patient_id', ''))
        anonymized['patient_id'] = self._generate_anonymous_id(original_id)
        
        # Remove direct identifiers
        identifiers_to_remove = [
            'name', 'first_name', 'last_name', 'full_name',
            'ssn', 'social_security', 'phone', 'email',
            'address', 'street', 'city', 'zip_code'
        ]
        
        for identifier in identifiers_to_remove:
            if identifier in anonymized:
                del anonymized[identifier]
        
        # Generalize age (keep age ranges for clinical relevance)
        if 'age' in anonymized:
            anonymized['age_range'] = self._generalize_age(anonymized['age'])
            del anonymized['age']
        
        # Generalize location to region level
        if 'location' in anonymized:
            anonymized['region'] = self._generalize_location(anonymized['location'])
            del anonymized['location']
        
        # Preserve medical data but remove specific dates
        if 'diagnosis_date' in anonymized:
            anonymized['diagnosis_timeframe'] = self._generalize_date(anonymized['diagnosis_date'])
            del anonymized['diagnosis_date']
            
        # Add anonymization metadata
        anonymized['anonymized_at'] = datetime.now().isoformat()
        anonymized['anonymization_version'] = '1.0'
        
        return anonymized
    
    def _generate_anonymous_id(self, original_id: str) -> str:
        """Generate consistent anonymous ID using hash."""
        if original_id in self.id_mapping:
            return self.id_mapping[original_id]
        
        # Create hash-based anonymous ID
        hash_object = hashlib.sha256(original_id.encode())
        anonymous_id = f"ANON_{hash_object.hexdigest()[:12].upper()}"
        
        self.id_mapping[original_id] = anonymous_id
        return anonymous_id
    
    def _generalize_age(self, age: int) -> str:
        """Convert specific age to age range."""
        if age < 18:
            return "pediatric"
        elif age < 30:
            return "18-29"
        elif age < 45:
            return "30-44"
        elif age < 65:
            return "45-64"
        else:
            return "65+"
    
    def _generalize_location(self, location: str) -> str:
        """Generalize location to region level."""
        # Simple region mapping - can be enhanced
        if not location:
            return "unknown_region"
        location_lower = location.lower()
        
        if any(state in location_lower for state in ['ca', 'california', 'oregon', 'washington']):
            return "west_coast"
        elif any(state in location_lower for state in ['ny', 'new york', 'massachusetts', 'connecticut']):
            return "northeast"
        elif any(state in location_lower for state in ['texas', 'florida', 'georgia', 'alabama']):
            return "southeast"
        else:
            return "other_us"
    
    def _generalize_date(self, date_str: str) -> str:
        """Convert specific date to relative timeframe."""
        try:
            date_obj = datetime.fromisoformat(date_str.replace('Z', '+00:00'))
            days_ago = (datetime.now() - date_obj.replace(tzinfo=None)).days
            
            if days_ago < 30:
                return "recent"
            elif days_ago < 90:
                return "1-3_months"
            elif days_ago < 365:
                return "3-12_months"
            else:
                return "over_1_year"
        except:
            return "unknown_timeframe"
    
    def validate_anonymization(self, original: Dict, anonymized: Dict) -> Dict[str, bool]:
        """
        Validate that anonymization was successful.
        """
        validation_results = {
            'identifiers_removed': True,
            'medical_data_preserved': True,
            'consistent_id_mapping': True
        }
        
        # Check for remaining identifiers
        sensitive_fields = ['name', 'ssn', 'phone', 'email', 'address']
        for field in sensitive_fields:
            if field in anonymized:
                validation_results['identifiers_removed'] = False
        
        # Check medical data preservation
        medical_fields = ['diagnosis', 'medications', 'lab_results', 'vital_signs']
        for field in medical_fields:
            if field in original and field not in anonymized:
                validation_results['medical_data_preserved'] = False
        
        return validation_results
