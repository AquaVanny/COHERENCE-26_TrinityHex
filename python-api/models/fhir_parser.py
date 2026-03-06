"""
Layer 1 — FHIR R4 Bundle Parser
Extracts normalized patient records from HL7 FHIR R4 / STU3 JSON bundles.
Handles Patient, Condition, MedicationRequest, Observation, and Procedure resources.
"""

import json
import os
from datetime import datetime, date
from typing import Dict, List, Any, Optional


class FHIRParser:
    """Parse FHIR R4/STU3 bundles into the normalized patient schema."""

    # Common LOINC codes for lab values
    LOINC_LAB_MAP = {
        '4548-4': 'hba1c',
        '2345-7': 'glucose',
        '2160-0': 'creatinine',
        '33914-3': 'egfr',
        '2093-3': 'total_cholesterol',
        '2571-8': 'triglycerides',
        '2085-9': 'hdl',
        '2089-1': 'ldl',
        '6690-2': 'wbc',
        '789-8': 'rbc',
        '718-7': 'hemoglobin',
        '4544-3': 'hematocrit',
        '777-3': 'platelets',
        '26515-7': 'platelets',
        '2951-2': 'sodium',
        '2823-3': 'potassium',
        '17861-6': 'calcium',
        '1742-6': 'alt',
        '1920-8': 'ast',
        '1975-2': 'bilirubin',
        '6768-6': 'alkaline_phosphatase',
        '2885-2': 'protein_total',
        '1751-7': 'albumin',
        '3094-0': 'bun',
        '39156-5': 'bmi',
        '29463-7': 'weight',
        '8302-2': 'height',
        '8480-6': 'systolic_bp',
        '8462-4': 'diastolic_bp',
        '8867-4': 'heart_rate',
        '8310-5': 'body_temperature',
        '9279-1': 'respiratory_rate',
        '26464-8': 'eosinophils',
        '19123-9': 'ige_total',
    }

    def parse_bundle(self, bundle: Dict) -> Dict[str, Any]:
        """
        Parse a single FHIR Bundle into a normalized patient record.
        Returns the normalized patient dict.
        """
        if bundle.get('resourceType') != 'Bundle':
            raise ValueError("Input is not a FHIR Bundle")

        entries = bundle.get('entry', [])
        if not entries:
            raise ValueError("Bundle contains no entries")

        # Classify resources by type
        resources_by_type: Dict[str, List[Dict]] = {}
        for entry in entries:
            resource = entry.get('resource', {})
            rtype = resource.get('resourceType', '')
            if rtype:
                resources_by_type.setdefault(rtype, []).append(resource)

        # Extract patient demographics
        patients = resources_by_type.get('Patient', [])
        if not patients:
            raise ValueError("No Patient resource found in bundle")
        patient_resource = patients[0]
        normalized = self._extract_patient(patient_resource)

        # Extract conditions (diagnoses)
        conditions = resources_by_type.get('Condition', [])
        normalized['diagnosis'] = self._extract_conditions(conditions)
        normalized['diagnosis_codes'] = self._extract_condition_codes(conditions)

        # Extract medications
        med_requests = resources_by_type.get('MedicationRequest', [])
        med_statements = resources_by_type.get('MedicationStatement', [])
        normalized['medications'] = self._extract_medications(med_requests + med_statements)
        normalized['medication_codes'] = self._extract_medication_codes(med_requests + med_statements)

        # Extract lab results from Observations
        observations = resources_by_type.get('Observation', [])
        labs, vitals = self._extract_observations(observations)
        normalized['lab_results'] = labs
        normalized['vital_signs'] = vitals

        # Extract procedures
        procedures = resources_by_type.get('Procedure', [])
        normalized['procedures'] = self._extract_procedures(procedures)
        normalized['procedure_codes'] = self._extract_procedure_codes(procedures)

        # Extract earliest diagnosis date
        normalized['diagnosis_date'] = self._extract_earliest_condition_date(conditions)

        return normalized

    def parse_bundle_file(self, filepath: str) -> Dict[str, Any]:
        """Parse a single FHIR bundle JSON file."""
        with open(filepath, 'r', encoding='utf-8') as f:
            bundle = json.load(f)
        return self.parse_bundle(bundle)

    def parse_bundle_directory(self, dirpath: str, limit: Optional[int] = None) -> List[Dict[str, Any]]:
        """Parse all FHIR bundle JSON files in a directory."""
        patients = []
        files = sorted([
            f for f in os.listdir(dirpath)
            if f.endswith('.json')
        ])
        if limit:
            files = files[:limit]

        for filename in files:
            filepath = os.path.join(dirpath, filename)
            try:
                patient = self.parse_bundle_file(filepath)
                patient['_source_file'] = filename
                patients.append(patient)
            except Exception as e:
                print(f"Warning: Failed to parse {filename}: {e}")
                continue

        return patients

    # ── Patient demographics ──────────────────────────────────────

    def _extract_patient(self, resource: Dict) -> Dict[str, Any]:
        patient: Dict[str, Any] = {}

        # ID
        patient['patient_id'] = resource.get('id', '')

        # Name
        names = resource.get('name', [])
        if names:
            name_obj = names[0]
            given = ' '.join(name_obj.get('given', []))
            family = name_obj.get('family', '')
            patient['name'] = f"{given} {family}".strip()

        # Gender
        patient['gender'] = resource.get('gender', '')

        # Age from birthDate
        birth_date_str = resource.get('birthDate', '')
        if birth_date_str:
            try:
                birth_date = datetime.strptime(birth_date_str, '%Y-%m-%d').date()
                # Check if deceased
                deceased_dt = resource.get('deceasedDateTime')
                if deceased_dt:
                    try:
                        ref_date = datetime.fromisoformat(deceased_dt.replace('Z', '+00:00')).date()
                    except Exception:
                        ref_date = date.today()
                else:
                    ref_date = date.today()
                age = (ref_date - birth_date).days // 365
                patient['age'] = age
            except Exception:
                pass

        # Location from address
        addresses = resource.get('address', [])
        if addresses:
            addr = addresses[0]
            city = addr.get('city', '')
            state = addr.get('state', '')
            postal = addr.get('postalCode', '')
            patient['location'] = ', '.join(filter(None, [city, state]))
            patient['zip_code'] = postal
            patient['state'] = state
            patient['city'] = city

        # Ethnicity (US Core extension)
        for ext in resource.get('extension', []):
            url = ext.get('url', '')
            if 'us-core-race' in url:
                for sub in ext.get('extension', []):
                    if sub.get('url') == 'text':
                        patient['race'] = sub.get('valueString', '')
            if 'us-core-ethnicity' in url:
                for sub in ext.get('extension', []):
                    if sub.get('url') == 'text':
                        patient['ethnicity'] = sub.get('valueString', '')
            if 'us-core-birthsex' in url:
                patient['birth_sex'] = ext.get('valueCode', '')

        return patient

    # ── Conditions / Diagnoses ────────────────────────────────────

    def _extract_conditions(self, conditions: List[Dict]) -> List[str]:
        """Extract human-readable diagnosis names."""
        diagnoses = []
        seen = set()
        for cond in conditions:
            code_obj = cond.get('code', {})
            text = code_obj.get('text', '')
            if not text:
                codings = code_obj.get('coding', [])
                if codings:
                    text = codings[0].get('display', '')
            if text and text not in seen:
                seen.add(text)
                diagnoses.append(text)
        return diagnoses

    def _extract_condition_codes(self, conditions: List[Dict]) -> List[Dict[str, str]]:
        """Extract structured diagnosis codes (ICD-10, SNOMED)."""
        codes = []
        seen = set()
        for cond in conditions:
            code_obj = cond.get('code', {})
            for coding in code_obj.get('coding', []):
                system = coding.get('system', '')
                code = coding.get('code', '')
                display = coding.get('display', '')
                key = f"{system}|{code}"
                if key not in seen and code:
                    seen.add(key)
                    code_system = 'SNOMED' if 'snomed' in system.lower() else \
                                  'ICD10' if 'icd' in system.lower() else system
                    codes.append({
                        'system': code_system,
                        'code': code,
                        'display': display
                    })
        return codes

    def _extract_earliest_condition_date(self, conditions: List[Dict]) -> Optional[str]:
        """Find earliest onset date among conditions."""
        dates = []
        for cond in conditions:
            onset = cond.get('onsetDateTime') or cond.get('recordedDate', '')
            if onset:
                try:
                    dt = datetime.fromisoformat(onset.replace('Z', '+00:00'))
                    dates.append(dt)
                except Exception:
                    pass
        if dates:
            return min(dates).isoformat()
        return None

    # ── Medications ───────────────────────────────────────────────

    def _extract_medications(self, med_resources: List[Dict]) -> List[str]:
        """Extract medication names."""
        meds = []
        seen = set()
        for med in med_resources:
            med_code = med.get('medicationCodeableConcept', {})
            text = med_code.get('text', '')
            if not text:
                codings = med_code.get('coding', [])
                if codings:
                    text = codings[0].get('display', '')
            if text and text not in seen:
                seen.add(text)
                meds.append(text)
        return meds

    def _extract_medication_codes(self, med_resources: List[Dict]) -> List[Dict[str, str]]:
        """Extract structured medication codes (RxNorm)."""
        codes = []
        seen = set()
        for med in med_resources:
            med_code = med.get('medicationCodeableConcept', {})
            for coding in med_code.get('coding', []):
                system = coding.get('system', '')
                code = coding.get('code', '')
                display = coding.get('display', '')
                key = f"{system}|{code}"
                if key not in seen and code:
                    seen.add(key)
                    code_system = 'RxNorm' if 'rxnorm' in system.lower() else system
                    codes.append({
                        'system': code_system,
                        'code': code,
                        'display': display
                    })
        return codes

    # ── Observations (labs + vitals) ──────────────────────────────

    def _extract_observations(self, observations: List[Dict]):
        """Split observations into labs and vitals based on LOINC codes."""
        labs = {}
        vitals = {}
        vital_codes = {'29463-7', '8302-2', '39156-5', '8480-6', '8462-4',
                       '8867-4', '8310-5', '9279-1'}

        for obs in observations:
            code_obj = obs.get('code', {})
            codings = code_obj.get('coding', [])
            loinc_code = ''
            display = code_obj.get('text', '')
            for c in codings:
                if 'loinc' in c.get('system', '').lower():
                    loinc_code = c.get('code', '')
                    if not display:
                        display = c.get('display', '')
                    break

            # Get value
            value = None
            if 'valueQuantity' in obs:
                value = obs['valueQuantity'].get('value')
            elif 'valueString' in obs:
                value = obs['valueString']
            elif 'valueCodeableConcept' in obs:
                value = obs['valueCodeableConcept'].get('text', '')

            if value is None:
                continue

            # Map to known name
            name = self.LOINC_LAB_MAP.get(loinc_code, '')
            if not name:
                name = display.lower().replace(' ', '_') if display else loinc_code

            if loinc_code in vital_codes:
                vitals[name] = value
            else:
                labs[name] = value

        return labs, vitals

    # ── Procedures ────────────────────────────────────────────────

    def _extract_procedures(self, procedures: List[Dict]) -> List[str]:
        """Extract procedure names."""
        procs = []
        seen = set()
        for proc in procedures:
            code_obj = proc.get('code', {})
            text = code_obj.get('text', '')
            if not text:
                codings = code_obj.get('coding', [])
                if codings:
                    text = codings[0].get('display', '')
            if text and text not in seen:
                seen.add(text)
                procs.append(text)
        return procs

    def _extract_procedure_codes(self, procedures: List[Dict]) -> List[Dict[str, str]]:
        """Extract structured procedure codes (CPT, SNOMED)."""
        codes = []
        seen = set()
        for proc in procedures:
            code_obj = proc.get('code', {})
            for coding in code_obj.get('coding', []):
                system = coding.get('system', '')
                code = coding.get('code', '')
                display = coding.get('display', '')
                key = f"{system}|{code}"
                if key not in seen and code:
                    seen.add(key)
                    code_system = 'CPT' if 'cpt' in system.lower() else \
                                  'SNOMED' if 'snomed' in system.lower() else system
                    codes.append({
                        'system': code_system,
                        'code': code,
                        'display': display
                    })
        return codes
