"""
Layer 1 — Enhanced Patient Anonymizer
Uses Microsoft Presidio for NER-based PII detection, synthetic replacement,
age bucketing, and audit log generation.
Falls back to rule-based stripping when Presidio is unavailable.
"""

import hashlib
import re
import json
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional
from faker import Faker

try:
    from presidio_analyzer import AnalyzerEngine
    from presidio_anonymizer import AnonymizerEngine
    PRESIDIO_AVAILABLE = True
except ImportError:
    PRESIDIO_AVAILABLE = False
    print("Warning: Presidio not installed. Using rule-based PII stripping only.")


class AuditLogger:
    """Records every anonymization action with timestamps."""

    def __init__(self):
        self.entries: List[Dict[str, Any]] = []

    def log(self, patient_id: str, field: str, action: str, detail: str = ''):
        self.entries.append({
            'timestamp': datetime.utcnow().isoformat() + 'Z',
            'patient_id': patient_id,
            'field': field,
            'action': action,
            'detail': detail
        })

    def get_log(self) -> List[Dict[str, Any]]:
        return list(self.entries)

    def clear(self):
        self.entries.clear()


class EnhancedAnonymizer:
    """
    PII stripping with Presidio NER + rule-based fallback.
    Produces audit trail for every anonymization decision.
    """

    # Direct identifiers that must always be removed
    PII_FIELDS = [
        'name', 'first_name', 'last_name', 'full_name',
        'ssn', 'social_security', 'phone', 'email',
        'address', 'street', 'line', 'zip_code', 'postalCode',
        'telecom', 'mrn', 'medical_record_number',
        'driver_license', 'passport', 'insurance_id',
        '_source_file'
    ]

    # Fields to keep as-is (clinical relevance)
    PRESERVE_FIELDS = [
        'patient_id', 'gender', 'birth_sex', 'diagnosis', 'diagnosis_codes',
        'medications', 'medication_codes', 'lab_results', 'vital_signs',
        'procedures', 'procedure_codes', 'diagnosis_date', 'ethnicity', 'race'
    ]

    def __init__(self):
        self.fake = Faker()
        self.id_mapping: Dict[str, str] = {}
        self.audit = AuditLogger()
        self._analyzer = None
        self._anonymizer_engine = None
        if PRESIDIO_AVAILABLE:
            try:
                self._analyzer = AnalyzerEngine()
                self._anonymizer_engine = AnonymizerEngine()
            except Exception as e:
                print(f"Warning: Presidio engine init failed: {e}")

    # ── Public API ────────────────────────────────────────────────

    def anonymize(self, patient: Dict[str, Any]) -> Dict[str, Any]:
        """
        Anonymize a patient record.
        Returns anonymized copy; original is not modified.
        """
        self.audit.clear()
        original_id = str(patient.get('patient_id', ''))
        anon = {}

        # 1. Generate consistent anonymous ID
        anon['patient_id'] = self._anon_id(original_id)
        self.audit.log(original_id, 'patient_id', 'hashed',
                       f'Original ID replaced with {anon["patient_id"]}')

        # 2. Remove direct PII fields
        for field in self.PII_FIELDS:
            if field in patient:
                self.audit.log(original_id, field, 'removed',
                               f'PII field stripped')

        # 3. Age bucketing
        if 'age' in patient:
            anon['age_range'] = self._bucket_age(patient['age'])
            self.audit.log(original_id, 'age', 'bucketed',
                           f'{patient["age"]} → {anon["age_range"]}')
        elif 'age_range' in patient:
            anon['age_range'] = patient['age_range']

        # 4. Generalize location to region level
        if 'location' in patient:
            anon['region'] = self._generalize_location(patient.get('location', ''))
            anon['state'] = patient.get('state', '')
            self.audit.log(original_id, 'location', 'generalized',
                           f'Location generalized to region')
        elif 'state' in patient:
            anon['region'] = self._generalize_location(patient.get('state', ''))
            anon['state'] = patient.get('state', '')

        # 5. Generalize diagnosis date
        if 'diagnosis_date' in patient and patient['diagnosis_date']:
            anon['diagnosis_timeframe'] = self._generalize_date(patient['diagnosis_date'])
            self.audit.log(original_id, 'diagnosis_date', 'generalized',
                           f'Date → {anon["diagnosis_timeframe"]}')

        # 6. Preserve clinical fields
        for field in self.PRESERVE_FIELDS:
            if field in patient and field not in anon:
                anon[field] = patient[field]

        # 7. Presidio scan on any remaining string fields
        for key, value in patient.items():
            if key in anon or key in self.PII_FIELDS:
                continue
            if isinstance(value, str) and len(value) > 2:
                clean = self._presidio_scrub(value, original_id, key)
                anon[key] = clean
            elif key not in anon:
                anon[key] = value

        # 8. Metadata
        anon['anonymized_at'] = datetime.utcnow().isoformat() + 'Z'
        anon['anonymization_version'] = '2.0'

        return anon

    def get_audit_log(self) -> List[Dict[str, Any]]:
        """Return audit trail from last anonymization call."""
        return self.audit.get_log()

    def validate(self, original: Dict, anonymized: Dict) -> Dict[str, bool]:
        """Validate anonymization quality."""
        results = {
            'identifiers_removed': True,
            'medical_data_preserved': True,
            'id_mapped': bool(anonymized.get('patient_id', '').startswith('ANON_'))
        }
        for field in self.PII_FIELDS:
            if field in anonymized:
                results['identifiers_removed'] = False
                break
        medical = ['diagnosis', 'medications', 'lab_results']
        for field in medical:
            if field in original and field not in anonymized:
                results['medical_data_preserved'] = False
                break
        return results

    # ── Internals ─────────────────────────────────────────────────

    def _anon_id(self, original_id: str) -> str:
        if original_id in self.id_mapping:
            return self.id_mapping[original_id]
        h = hashlib.sha256(original_id.encode()).hexdigest()[:12].upper()
        anon_id = f"ANON_{h}"
        self.id_mapping[original_id] = anon_id
        return anon_id

    def _bucket_age(self, age) -> str:
        try:
            age = int(age)
        except (ValueError, TypeError):
            return 'unknown'
        if age < 18:
            return 'pediatric'
        elif age < 30:
            return '18-29'
        elif age < 40:
            return '30-39'
        elif age < 50:
            return '40-49'
        elif age < 60:
            return '50-59'
        elif age < 70:
            return '60-69'
        elif age < 80:
            return '70-79'
        else:
            return '80+'

    def _generalize_location(self, location: str) -> str:
        if not location:
            return 'unknown_region'
        loc = location.lower()
        west = ['ca', 'california', 'oregon', 'washington', 'nevada', 'arizona',
                'colorado', 'utah', 'hawaii', 'alaska']
        northeast = ['ny', 'new york', 'massachusetts', 'connecticut', 'new jersey',
                     'pennsylvania', 'rhode island', 'vermont', 'maine', 'new hampshire']
        southeast = ['florida', 'georgia', 'alabama', 'mississippi', 'louisiana',
                     'south carolina', 'north carolina', 'virginia', 'tennessee',
                     'kentucky', 'arkansas']
        midwest = ['illinois', 'ohio', 'michigan', 'indiana', 'wisconsin',
                   'minnesota', 'iowa', 'missouri', 'kansas', 'nebraska',
                   'south dakota', 'north dakota']
        southwest = ['texas', 'oklahoma', 'new mexico']

        for state in west:
            if state in loc:
                return 'west'
        for state in northeast:
            if state in loc:
                return 'northeast'
        for state in southeast:
            if state in loc:
                return 'southeast'
        for state in midwest:
            if state in loc:
                return 'midwest'
        for state in southwest:
            if state in loc:
                return 'southwest'
        return 'other_us'

    def _generalize_date(self, date_str: str) -> str:
        try:
            dt = datetime.fromisoformat(date_str.replace('Z', '+00:00'))
            days = (datetime.now() - dt.replace(tzinfo=None)).days
            if days < 30:
                return 'recent'
            elif days < 90:
                return '1-3_months'
            elif days < 180:
                return '3-6_months'
            elif days < 365:
                return '6-12_months'
            elif days < 730:
                return '1-2_years'
            else:
                return 'over_2_years'
        except Exception:
            return 'unknown_timeframe'

    def _presidio_scrub(self, text: str, patient_id: str, field: str) -> str:
        """Use Presidio to detect and redact PII from free-text fields."""
        if not self._analyzer:
            return self._regex_scrub(text, patient_id, field)
        try:
            results = self._analyzer.analyze(text=text, language='en',
                                             entities=[
                                                 'PERSON', 'PHONE_NUMBER', 'EMAIL_ADDRESS',
                                                 'US_SSN', 'LOCATION', 'DATE_TIME',
                                                 'US_DRIVER_LICENSE', 'US_PASSPORT',
                                                 'MEDICAL_LICENSE', 'IP_ADDRESS'
                                             ])
            if results:
                from presidio_anonymizer.entities import OperatorConfig
                anon_result = self._anonymizer_engine.anonymize(
                    text=text,
                    analyzer_results=results,
                    operators={
                        'DEFAULT': OperatorConfig('replace', {'new_value': '[REDACTED]'})
                    }
                )
                for r in results:
                    self.audit.log(patient_id, field, 'presidio_redacted',
                                   f'Entity {r.entity_type} at [{r.start}:{r.end}]')
                return anon_result.text
            return text
        except Exception:
            return self._regex_scrub(text, patient_id, field)

    def _regex_scrub(self, text: str, patient_id: str, field: str) -> str:
        """Fallback regex-based PII scrubbing."""
        original = text
        # SSN
        text = re.sub(r'\b\d{3}-\d{2}-\d{4}\b', '[SSN_REDACTED]', text)
        # Phone
        text = re.sub(r'\b\d{3}[-.]?\d{3}[-.]?\d{4}\b', '[PHONE_REDACTED]', text)
        # Email
        text = re.sub(r'\b[\w.-]+@[\w.-]+\.\w+\b', '[EMAIL_REDACTED]', text)
        if text != original:
            self.audit.log(patient_id, field, 'regex_redacted', 'PII patterns replaced')
        return text
