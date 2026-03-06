"""
Layer 4 — Ranking & Explanation Module
Generates per-criterion justifications, SHAP-based feature contributions,
confidence tiers, and geographic distance estimates for every match result.
"""

import math
import re
from typing import Dict, List, Any, Optional, Tuple

try:
    import shap
    import numpy as np
    SHAP_AVAILABLE = True
except ImportError:
    SHAP_AVAILABLE = False

try:
    import numpy as np
except ImportError:
    pass


# ── Geographic utilities ──────────────────────────────────────────

# Approximate lat/lon for major US cities (for distance estimation)
CITY_COORDS = {
    'san francisco': (37.7749, -122.4194),
    'los angeles': (34.0522, -118.2437),
    'new york': (40.7128, -74.0060),
    'boston': (42.3601, -71.0589),
    'chicago': (41.8781, -87.6298),
    'houston': (29.7604, -95.3698),
    'miami': (25.7617, -80.1918),
    'seattle': (47.6062, -122.3321),
    'philadelphia': (39.9526, -75.1652),
    'phoenix': (33.4484, -112.0740),
    'san diego': (32.7157, -117.1611),
    'dallas': (32.7767, -96.7970),
    'tampa': (27.9506, -82.4572),
    'orlando': (28.5383, -81.3792),
    'atlanta': (33.7490, -84.3880),
    'denver': (39.7392, -104.9903),
    'portland': (45.5152, -122.6784),
    'san antonio': (29.4241, -98.4936),
    'detroit': (42.3314, -83.0458),
    'minneapolis': (44.9778, -93.2650),
    'pittsburgh': (40.4406, -79.9959),
    'baltimore': (39.2904, -76.6122),
    'salt lake city': (40.7608, -111.8910),
    'nashville': (36.1627, -86.7816),
    'indianapolis': (39.7684, -86.1581),
    'cleveland': (41.4993, -81.6944),
    'st louis': (38.6270, -90.1994),
    'kansas city': (39.0997, -94.5786),
    'las vegas': (36.1699, -115.1398),
    'columbus': (39.9612, -82.9988),
    'charlotte': (35.2271, -80.8431),
    'raleigh': (35.7796, -78.6382),
    'richmond': (37.5407, -77.4360),
    'louisville': (38.2527, -85.7585),
    'memphis': (35.1495, -90.0490),
    'new orleans': (29.9511, -90.0715),
    'milwaukee': (43.0389, -87.9065),
    'oklahoma city': (35.4676, -97.5164),
    'tucson': (32.2226, -110.9747),
    'jacksonville': (30.3322, -81.6557),
    'sacramento': (38.5816, -121.4944),
    'austin': (30.2672, -97.7431),
}


def _haversine(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Calculate distance in miles between two lat/lon points."""
    R = 3959  # Earth radius in miles
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = (math.sin(dlat / 2) ** 2 +
         math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) *
         math.sin(dlon / 2) ** 2)
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    return R * c


def _find_city_coords(location_str: str) -> Optional[Tuple[float, float]]:
    """Find approximate coordinates for a location string."""
    if not location_str:
        return None
    loc = location_str.lower()
    for city, coords in CITY_COORDS.items():
        if city in loc:
            return coords
    return None


def estimate_distance(patient_location: str, trial_location: str) -> Optional[Dict]:
    """
    Estimate distance between patient and nearest trial site.
    Returns dict with distance_miles and nearest_site, or None if unknown.
    """
    patient_coords = _find_city_coords(patient_location)
    if not patient_coords:
        return None

    # Trial location may contain multiple sites separated by ; or ,
    sites = re.split(r'[;,]', trial_location)
    min_dist = float('inf')
    nearest = ''

    for site in sites:
        site = site.strip()
        coords = _find_city_coords(site)
        if coords:
            dist = _haversine(patient_coords[0], patient_coords[1],
                              coords[0], coords[1])
            if dist < min_dist:
                min_dist = dist
                nearest = site

    if min_dist < float('inf'):
        return {
            'distance_miles': round(min_dist, 1),
            'nearest_site': nearest
        }
    return None


class ExplanationGenerator:
    """
    Generates human-readable explanations for match results.
    Combines rule-based justifications with SHAP-based feature contributions.
    """

    def __init__(self, ml_model=None):
        self._ml_model = ml_model
        self._shap_explainer = None
        if SHAP_AVAILABLE and ml_model is not None:
            try:
                self._shap_explainer = shap.TreeExplainer(ml_model)
            except Exception:
                pass

    def set_ml_model(self, model):
        """Set / update the ML model for SHAP explanations."""
        self._ml_model = model
        if SHAP_AVAILABLE and model is not None:
            try:
                self._shap_explainer = shap.TreeExplainer(model)
            except Exception:
                self._shap_explainer = None

    def explain(self, match_result: Dict, patient: Dict) -> Dict[str, Any]:
        """
        Generate full explanation for a single match result.

        Returns enhanced match_result with:
        - rule_explanations: list of per-criterion plain-English statements
        - shap_explanations: top contributing features with SHAP values
        - geographic_info: distance to nearest trial site
        - confidence_breakdown: detailed confidence explanation
        - match_summary: one-sentence summary
        """
        explanation = {}

        # 1. Rule-based explanations
        explanation['rule_explanations'] = self._rule_explanations(match_result)

        # 2. SHAP explanations
        explanation['shap_explanations'] = self._shap_explanations(match_result)

        # 3. Geographic distance
        patient_loc = patient.get('location', '') or patient.get('region', '')
        trial_loc = match_result.get('location', '')
        geo = estimate_distance(patient_loc, trial_loc)
        explanation['geographic_info'] = geo

        # 4. Confidence breakdown
        explanation['confidence_breakdown'] = self._confidence_breakdown(match_result)

        # 5. Summary
        explanation['match_summary'] = self._generate_summary(match_result, geo)

        # Merge into match result
        enhanced = dict(match_result)
        enhanced.update(explanation)
        return enhanced

    # ── Rule explanations ─────────────────────────────────────────

    def _rule_explanations(self, match_result: Dict) -> List[Dict[str, str]]:
        """
        Generate per-criterion plain-English explanations.
        Each entry has: text, status_icon, status
        """
        explanations = []
        for cr in match_result.get('criteria_results', []):
            status = cr.get('status', 'UNKNOWN')
            explanation_text = cr.get('explanation', '')
            is_exclusion = cr.get('is_exclusion', False)

            if status == 'ELIGIBLE':
                icon = '✓'
            elif status == 'INELIGIBLE':
                icon = '✗'
            else:
                icon = '⚠'

            explanations.append({
                'text': explanation_text,
                'status': status,
                'icon': icon,
                'is_exclusion': is_exclusion,
                'criterion_type': cr.get('criterion', {}).get('field', 'unknown')
            })

        return explanations

    # ── SHAP explanations ─────────────────────────────────────────

    def _shap_explanations(self, match_result: Dict) -> Dict[str, Any]:
        """
        Compute SHAP values for the ML prediction.
        Returns top 3 positive and top 3 negative contributing features.
        """
        feature_vector = match_result.get('ml_feature_vector', {})
        feature_importance = match_result.get('feature_importance', {})

        if not feature_vector:
            return {'positive': [], 'negative': [], 'available': False}

        # Try SHAP if available
        if self._shap_explainer is not None and SHAP_AVAILABLE:
            try:
                from models.matching_engine import MLScorer
                feature_names = MLScorer.FEATURE_NAMES
                X = np.array([feature_vector.get(f, 0.0) for f in feature_names]).reshape(1, -1)
                shap_values = self._shap_explainer.shap_values(X)

                # Handle multi-output
                if isinstance(shap_values, list):
                    sv = shap_values[1][0] if len(shap_values) > 1 else shap_values[0][0]
                else:
                    sv = shap_values[0]

                contributions = list(zip(feature_names, sv))
                contributions.sort(key=lambda x: x[1], reverse=True)

                positive = [
                    {'feature': name, 'shap_value': round(float(val), 4),
                     'description': self._feature_description(name, feature_vector.get(name, 0))}
                    for name, val in contributions if val > 0
                ][:3]

                negative = [
                    {'feature': name, 'shap_value': round(float(val), 4),
                     'description': self._feature_description(name, feature_vector.get(name, 0))}
                    for name, val in contributions if val < 0
                ][-3:]

                return {'positive': positive, 'negative': negative, 'available': True}

            except Exception:
                pass

        # Fallback: use feature importance as proxy
        if feature_importance:
            sorted_features = sorted(feature_importance.items(), key=lambda x: x[1], reverse=True)
            positive = [
                {'feature': name, 'importance': round(imp, 4),
                 'description': self._feature_description(name, feature_vector.get(name, 0))}
                for name, imp in sorted_features[:3]
            ]
            return {'positive': positive, 'negative': [], 'available': False,
                    'note': 'SHAP not available, showing feature importance instead'}

        return {'positive': [], 'negative': [], 'available': False}

    @staticmethod
    def _feature_description(feature_name: str, value) -> str:
        """Human-readable description of a feature contribution."""
        descriptions = {
            'age': f'Patient age ({int(value) if value else "unknown"})',
            'gender_match': 'Gender matches trial requirements' if value else 'Gender may not match',
            'num_diagnoses': f'Patient has {int(value)} diagnoses',
            'num_medications': f'Patient is on {int(value)} medications',
            'has_lab_results': 'Lab results available' if value else 'No lab results',
            'num_lab_values': f'{int(value)} lab values recorded',
            'condition_overlap': f'Condition overlap score: {value:.0%}' if value else 'No condition overlap',
            'medication_overlap': f'Medication overlap: {value:.0%}' if value else 'No medication overlap',
            'num_inclusion': f'{int(value)} inclusion criteria in trial',
            'num_exclusion': f'{int(value)} exclusion criteria in trial',
            'age_in_range': 'Age within trial range' if value else 'Age outside trial range',
            'has_vital_signs': 'Vital signs available' if value else 'No vital signs',
            'missing_data_count': f'{int(value)} key fields missing',
        }
        return descriptions.get(feature_name, feature_name)

    # ── Confidence breakdown ──────────────────────────────────────

    @staticmethod
    def _confidence_breakdown(match_result: Dict) -> Dict[str, Any]:
        """Detailed confidence explanation."""
        rule_score = match_result.get('rule_score', 0)
        ml_score = match_result.get('ml_score', 0)
        fused = match_result.get('fused_score', 0)
        tier = match_result.get('confidence_tier', 'LOW')
        hard_exc = match_result.get('hard_exclusion', False)

        criteria_results = match_result.get('criteria_results', [])
        eligible_count = sum(1 for c in criteria_results if c.get('status') == 'ELIGIBLE')
        ineligible_count = sum(1 for c in criteria_results if c.get('status') == 'INELIGIBLE')
        unknown_count = sum(1 for c in criteria_results if c.get('status') == 'UNKNOWN')
        total = len(criteria_results)

        return {
            'confidence_tier': tier,
            'fused_score': fused,
            'fused_score_pct': round(fused * 100, 1),
            'rule_score': rule_score,
            'rule_score_pct': round(rule_score * 100, 1),
            'ml_score': ml_score,
            'ml_score_pct': round(ml_score * 100, 1),
            'rule_weight': 0.6,
            'ml_weight': 0.4,
            'hard_exclusion': hard_exc,
            'criteria_summary': {
                'total': total,
                'eligible': eligible_count,
                'ineligible': ineligible_count,
                'unknown': unknown_count
            }
        }

    # ── Summary ───────────────────────────────────────────────────

    @staticmethod
    def _generate_summary(match_result: Dict, geo: Optional[Dict]) -> str:
        """One-sentence match summary."""
        title = match_result.get('title', 'Unknown trial')
        fused = match_result.get('fused_score', 0)
        tier = match_result.get('confidence_tier', 'LOW')
        overall = match_result.get('overall_status', 'UNKNOWN')

        pct = round(fused * 100)

        if overall == 'INELIGIBLE' and match_result.get('hard_exclusion'):
            summary = f"Patient is INELIGIBLE for \"{title}\" due to a hard exclusion criterion."
        elif overall == 'INELIGIBLE':
            summary = f"Patient is unlikely eligible for \"{title}\" (score: {pct}%, confidence: {tier})."
        elif overall == 'ELIGIBLE':
            summary = f"Patient appears ELIGIBLE for \"{title}\" with {pct}% match score ({tier} confidence)."
        else:
            summary = f"Eligibility for \"{title}\" is UNCERTAIN (score: {pct}%, confidence: {tier}). Manual review recommended."

        if geo:
            summary += f" Nearest trial site: {geo['nearest_site']} ({geo['distance_miles']} miles)."

        return summary


class RankingModule:
    """
    Ranks all match results for a patient and attaches full explanations.
    """

    def __init__(self, ml_model=None):
        self.explainer = ExplanationGenerator(ml_model)

    def set_ml_model(self, model):
        self.explainer.set_ml_model(model)

    def rank_and_explain(self, match_results: List[Dict],
                         patient: Dict) -> List[Dict]:
        """
        Take raw match results, add explanations, and return sorted list.
        """
        explained = []
        for result in match_results:
            enhanced = self.explainer.explain(result, patient)
            explained.append(enhanced)

        # Sort by fused_score descending
        explained.sort(key=lambda x: x.get('fused_score', 0), reverse=True)

        # Add rank
        for i, item in enumerate(explained):
            item['rank'] = i + 1

        return explained
