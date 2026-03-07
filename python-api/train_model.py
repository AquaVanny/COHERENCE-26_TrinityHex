"""
ML Model Training Pipeline using Synthea Patient Data
Generates labeled training examples from real patient-trial matches
and retrains the XGBoost model for improved accuracy.
"""

import json
import os
import pickle
import numpy as np
from typing import List, Dict, Tuple
from sklearn.model_selection import train_test_split
from sklearn.metrics import accuracy_score, precision_score, recall_score, f1_score, roc_auc_score
from models.criteria_parser import CriteriaParser
from models.matching_engine import MatchingEngine, MLScorer

try:
    from xgboost import XGBClassifier
    XGBOOST_AVAILABLE = True
except ImportError:
    from sklearn.ensemble import RandomForestClassifier
    XGBOOST_AVAILABLE = False


class ModelTrainer:
    """
    Trains ML model using real Synthea patient data and clinical trials.
    Creates labeled examples based on rule-based matching results.
    """
    
    def __init__(self):
        self.criteria_parser = CriteriaParser()
        # Create a fresh matching engine without loading pre-trained model
        # to avoid interference during training data generation
        from models.matching_engine import RuleEngine
        self.rule_engine = RuleEngine()
        self.ml_scorer = MLScorer(model_path='__skip__')  # Skip loading existing model
        self.feature_names = MLScorer.FEATURE_NAMES
        
    def load_data(self) -> Tuple[List[Dict], List[Dict]]:
        """Load Synthea patients and clinical trials."""
        patients_file = os.path.join(os.path.dirname(__file__), 'data', 'real_patients.json')
        trials_file = os.path.join(os.path.dirname(__file__), 'data', 'sample_trials.json')
        
        with open(patients_file, 'r') as f:
            patients = json.load(f)
        
        with open(trials_file, 'r') as f:
            trials = json.load(f)
        
        print(f"✓ Loaded {len(patients)} Synthea patients")
        print(f"✓ Loaded {len(trials)} clinical trials")
        
        return patients, trials
    
    def generate_training_examples(self, patients: List[Dict], trials: List[Dict],
                                   max_examples: int = 500) -> Tuple[np.ndarray, np.ndarray]:
        """
        Generate labeled training examples from patient-trial pairs.
        
        Label strategy (relaxed thresholds for better balance):
        - 1 (match) if: fused_score >= 0.5 OR overall_status == 'ELIGIBLE'
        - 0 (no match) if: fused_score < 0.3 OR overall_status == 'INELIGIBLE'
        - Skip ambiguous cases (0.3 <= score < 0.5 and status == 'UNKNOWN')
        """
        X_positive = []
        y_positive = []
        X_negative = []
        y_negative = []
        
        print(f"\n🔄 Generating training examples...")
        
        # Use all patients for better coverage
        for patient in patients:
            for trial in trials:
                try:
                    # Parse criteria
                    criteria_text = trial.get('eligibility_criteria', '')
                    parsed_criteria = self.criteria_parser.parse(criteria_text)
                    
                    # Get rule-based evaluation
                    rule_result = self.rule_engine.evaluate(patient, parsed_criteria)
                    
                    # Extract features using ML scorer
                    features = self.ml_scorer._extract_features(patient, trial, parsed_criteria, rule_result)
                    X = np.array([features.get(f, 0.0) for f in self.feature_names])
                    
                    # Determine label based on rule-based result (relaxed thresholds)
                    rule_score = rule_result.get('rule_score', 0.0)
                    overall_status = rule_result.get('overall_status', 'UNKNOWN')
                    hard_exclusion = rule_result.get('hard_exclusion', False)
                    
                    # Positive match (relaxed criteria)
                    if (rule_score >= 0.5 or overall_status == 'ELIGIBLE' or 
                        (rule_score >= 0.6 and not hard_exclusion)):
                        X_positive.append(X)
                        y_positive.append(1)
                    # Negative match
                    elif (rule_score < 0.3 or overall_status == 'INELIGIBLE' or hard_exclusion):
                        X_negative.append(X)
                        y_negative.append(0)
                    # Skip ambiguous cases
                    
                except Exception as e:
                    print(f"⚠ Error processing patient-trial pair: {e}")
                    continue
        
        # Balance classes by undersampling majority class
        n_positive = len(X_positive)
        n_negative = len(X_negative)
        
        print(f"  - Raw positive examples: {n_positive}")
        print(f"  - Raw negative examples: {n_negative}")
        
        # Undersample negative class to balance (keep at most 3x negatives)
        if n_negative > n_positive * 3 and n_positive > 0:
            indices = np.random.choice(n_negative, size=min(n_positive * 3, n_negative), replace=False)
            X_negative = [X_negative[i] for i in indices]
            y_negative = [y_negative[i] for i in indices]
            print(f"  - Undersampled negatives to: {len(X_negative)}")
        
        # Combine
        X_train = np.array(X_positive + X_negative)
        y_train = np.array(y_positive + y_negative)
        
        # Shuffle
        shuffle_idx = np.random.permutation(len(X_train))
        X_train = X_train[shuffle_idx]
        y_train = y_train[shuffle_idx]
        
        print(f"\n✓ Generated {len(X_train)} balanced labeled examples")
        print(f"  - Positive matches (eligible): {np.sum(y_train == 1)}")
        print(f"  - Negative matches (ineligible): {np.sum(y_train == 0)}")
        print(f"  - Class balance: {np.sum(y_train == 1) / len(y_train) * 100:.1f}% positive")
        
        return X_train, y_train
    
    def train_model(self, X_train: np.ndarray, y_train: np.ndarray,
                   test_size: float = 0.2) -> Dict:
        """
        Train XGBoost model with train/test split and evaluation.
        """
        # Split data
        X_tr, X_val, y_tr, y_val = train_test_split(
            X_train, y_train, test_size=test_size, random_state=42, stratify=y_train
        )
        
        print(f"\n🤖 Training model...")
        print(f"  - Training set: {len(X_tr)} examples")
        print(f"  - Validation set: {len(X_val)} examples")
        
        # Initialize model
        if XGBOOST_AVAILABLE:
            model = XGBClassifier(
                n_estimators=150,
                max_depth=5,
                learning_rate=0.1,
                subsample=0.8,
                colsample_bytree=0.8,
                random_state=42,
                use_label_encoder=False,
                eval_metric='logloss'
            )
            print("  - Using XGBoost Classifier")
        else:
            from sklearn.ensemble import RandomForestClassifier
            model = RandomForestClassifier(
                n_estimators=150,
                max_depth=5,
                random_state=42
            )
            print("  - Using Random Forest Classifier (XGBoost not available)")
        
        # Train
        model.fit(X_tr, y_tr)
        
        # Evaluate
        y_pred_train = model.predict(X_tr)
        y_pred_val = model.predict(X_val)
        y_proba_val = model.predict_proba(X_val)[:, 1]
        
        metrics = {
            'train_accuracy': accuracy_score(y_tr, y_pred_train),
            'val_accuracy': accuracy_score(y_val, y_pred_val),
            'val_precision': precision_score(y_val, y_pred_val, zero_division=0),
            'val_recall': recall_score(y_val, y_pred_val, zero_division=0),
            'val_f1': f1_score(y_val, y_pred_val, zero_division=0),
            'val_auc': roc_auc_score(y_val, y_proba_val)
        }
        
        print(f"\n📊 Model Performance:")
        print(f"  - Training Accuracy: {metrics['train_accuracy']:.3f}")
        print(f"  - Validation Accuracy: {metrics['val_accuracy']:.3f}")
        print(f"  - Validation Precision: {metrics['val_precision']:.3f}")
        print(f"  - Validation Recall: {metrics['val_recall']:.3f}")
        print(f"  - Validation F1 Score: {metrics['val_f1']:.3f}")
        print(f"  - Validation AUC-ROC: {metrics['val_auc']:.3f}")
        
        # Feature importance
        if hasattr(model, 'feature_importances_'):
            importances = model.feature_importances_
            feature_importance = sorted(
                zip(self.feature_names, importances),
                key=lambda x: x[1],
                reverse=True
            )
            print(f"\n🔍 Top 5 Most Important Features:")
            for feat, imp in feature_importance[:5]:
                print(f"  - {feat}: {imp:.4f}")
        
        return model, metrics
    
    def save_model(self, model, metrics: Dict, output_path: str = 'models/trained_model.pkl'):
        """Save trained model to disk."""
        model_dir = os.path.dirname(output_path)
        if model_dir and not os.path.exists(model_dir):
            os.makedirs(model_dir)
        
        full_path = os.path.join(os.path.dirname(__file__), output_path)
        
        with open(full_path, 'wb') as f:
            pickle.dump({
                'model': model,
                'metrics': metrics,
                'feature_names': self.feature_names,
                'trained_on': 'synthea_patients',
                'timestamp': __import__('datetime').datetime.now().isoformat()
            }, f)
        
        print(f"\n💾 Model saved to: {output_path}")
        
        # Also save metrics as JSON
        metrics_path = full_path.replace('.pkl', '_metrics.json')
        with open(metrics_path, 'w') as f:
            json.dump(metrics, f, indent=2)
        
        print(f"📈 Metrics saved to: {metrics_path}")
    
    def run_training_pipeline(self, max_examples: int = 500):
        """Execute full training pipeline."""
        print("=" * 60)
        print("🚀 ML Model Training Pipeline - Synthea Patient Data")
        print("=" * 60)
        
        # Load data
        patients, trials = self.load_data()
        
        # Generate training examples
        X_train, y_train = self.generate_training_examples(patients, trials, max_examples)
        
        if len(X_train) < 50:
            print("\n❌ Error: Not enough training examples generated.")
            print("   Need at least 50 examples. Try adjusting labeling thresholds.")
            return
        
        # Train model
        model, metrics = self.train_model(X_train, y_train)
        
        # Save model
        self.save_model(model, metrics)
        
        print("\n" + "=" * 60)
        print("✅ Training Complete!")
        print("=" * 60)
        print("\nNext steps:")
        print("1. Review model metrics above")
        print("2. Update matching_engine.py to load the trained model")
        print("3. Restart Flask server to use the new model")
        print("4. Test matching accuracy with real patients")


def main():
    """Run training pipeline."""
    trainer = ModelTrainer()
    trainer.run_training_pipeline(max_examples=600)


if __name__ == '__main__':
    main()
