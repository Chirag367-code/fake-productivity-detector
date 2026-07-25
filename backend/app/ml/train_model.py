"""
ML Model Training Script.

This script trains and evaluates machine learning models for productivity classification.
It supports training on CSV data or synthetic data for demonstration.
"""

import argparse
import logging
import os
import sys
from datetime import datetime
from typing import Optional

import numpy as np
import pandas as pd

# Add parent directory to path for imports when running as script
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

try:
    from app.services.ml_model import MLClassifier
    from app.services.preprocessing import DataPreprocessor
    from app.services.scoring import ProductivityScorer
    from app.config import ScoringConfig, ProductivityCategory
except ImportError:
    from ..services.ml_model import MLClassifier
    from ..services.preprocessing import DataPreprocessor
    from ..services.scoring import ProductivityScorer
    from ..config import ScoringConfig, ProductivityCategory

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def generate_synthetic_data(n_samples: int = 1000, random_state: int = 42) -> pd.DataFrame:
    """
    Generate synthetic productivity data for training.
    
    This creates realistic training data based on the productivity formula
    with controlled noise and variety.
    
    Args:
        n_samples: Number of samples to generate
        random_state: Random seed for reproducibility
        
    Returns:
        DataFrame with synthetic productivity data
    """
    np.random.seed(random_state)
    
    data = {
        'task_hours': [],
        'tasks_completed': [],
        'idle_hours': [],
        'social_media_usage': [],
        'break_frequency': []
    }
    
    # Generate three clusters of data (one for each productivity category)
    samples_per_category = n_samples // 3
    
    # Highly Productive profiles
    for _ in range(samples_per_category):
        data['task_hours'].append(np.random.uniform(6, 10))
        data['tasks_completed'].append(np.random.randint(5, 15))
        data['idle_hours'].append(np.random.uniform(0, 2))
        data['social_media_usage'].append(np.random.uniform(0, 1.5))
        data['break_frequency'].append(np.random.randint(1, 4))
    
    # Moderately Productive profiles
    for _ in range(samples_per_category):
        data['task_hours'].append(np.random.uniform(3, 6))
        data['tasks_completed'].append(np.random.randint(2, 8))
        data['idle_hours'].append(np.random.uniform(1, 4))
        data['social_media_usage'].append(np.random.uniform(1, 3))
        data['break_frequency'].append(np.random.randint(3, 7))
    
    # Fake Productivity profiles
    remaining = n_samples - (2 * samples_per_category)
    for _ in range(remaining):
        data['task_hours'].append(np.random.uniform(0, 3))
        data['tasks_completed'].append(np.random.randint(0, 3))
        data['idle_hours'].append(np.random.uniform(3, 8))
        data['social_media_usage'].append(np.random.uniform(2, 6))
        data['break_frequency'].append(np.random.randint(5, 12))
    
    df = pd.DataFrame(data)
    
    # Shuffle the data
    df = df.sample(frac=1, random_state=random_state).reset_index(drop=True)
    
    # Calculate productivity scores using the scoring service
    scorer = ProductivityScorer()
    scores = []
    categories = []
    
    for _, row in df.iterrows():
        metrics = row.to_dict()
        result = scorer.calculate_score(
            metrics["task_hours"],
            metrics["idle_hours"],
            metrics.get("social_media_usage", metrics.get("social_media_hours", 0)),
            metrics["break_frequency"],
            metrics["tasks_completed"]
        )
        scores.append(result.score)
        categories.append(result.category)
    
    df['productivity_score'] = scores
    df['category'] = categories
    
    logger.info(f"Generated {len(df)} synthetic samples")
    logger.info(f"Category distribution:\n{df['category'].value_counts()}")
    
    return df


def load_csv_data(filepath: str) -> pd.DataFrame:
    """
    Load training data from CSV file.
    
    Args:
        filepath: Path to CSV file
        
    Returns:
        DataFrame with productivity data
    """
    logger.info(f"Loading data from {filepath}")
    
    df = pd.read_csv(filepath)
    
    # Required columns
    required_cols = [
        'task_hours', 'tasks_completed', 'idle_hours',
        'social_media_usage', 'break_frequency'
    ]
    
    # Check for required columns (case-insensitive)
    df.columns = df.columns.str.lower().str.strip().str.replace(' ', '_')
    
    missing = [col for col in required_cols if col not in df.columns]
    if missing:
        raise ValueError(f"Missing required columns: {missing}")
    
    # Add scores and categories if not present
    if 'category' not in df.columns:
        scorer = ProductivityScorer()
        scores = []
        categories = []
        
        for _, row in df.iterrows():
            metrics = {col: row[col] for col in required_cols}
            result = scorer.calculate_score(
                metrics["task_hours"],
                metrics["idle_hours"],
                metrics.get("social_media_usage", metrics.get("social_media_hours", 0)),
                metrics["break_frequency"],
                metrics["tasks_completed"]
            )
            scores.append(result.score)
            categories.append(result.category)
        
        df['productivity_score'] = scores
        df['category'] = categories
    
    logger.info(f"Loaded {len(df)} samples from CSV")
    logger.info(f"Category distribution:\n{df['category'].value_counts()}")
    
    return df


def train_and_evaluate(
    data: pd.DataFrame,
    model_type: str = 'random_forest',
    model_dir: str = 'models',
    test_size: float = 0.2
) -> dict:
    """
    Train and evaluate a productivity classification model.
    
    Args:
        data: Training DataFrame
        model_type: Type of model to train
        model_dir: Directory to save the trained model
        test_size: Fraction of data for testing
        
    Returns:
        Dict with training results and metrics
    """
    logger.info(f"Training {model_type} model...")
    
    # Preprocess data
    preprocessor = DataPreprocessor()
    processed_df = preprocessor.clean_data(data)
    
    # Feature columns
    feature_cols = [
        'task_hours', 'tasks_completed', 'idle_hours',
        'social_media_usage', 'break_frequency'
    ]
    
    # Prepare features and labels
    X = processed_df[feature_cols].values
    y = processed_df['category'].values
    
    # Train-test split
    from sklearn.model_selection import train_test_split
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=test_size, random_state=42, stratify=y
    )
    
    # Train model
    classifier = MLClassifier(model_type=model_type)
    train_results = classifier.train(X_train, y_train)
    
    # Evaluate on test set
    from sklearn.metrics import classification_report, confusion_matrix, accuracy_score
    
    y_pred = classifier.model.predict(X_test)
    
    accuracy = accuracy_score(y_test, y_pred)
    report = classification_report(y_test, y_pred, output_dict=True)
    conf_matrix = confusion_matrix(y_test, y_pred).tolist()
    
    logger.info(f"Test Accuracy: {accuracy:.4f}")
    logger.info(f"Classification Report:\n{classification_report(y_test, y_pred)}")
    
    # Save model
    os.makedirs(model_dir, exist_ok=True)
    model_path = os.path.join(model_dir, f'{model_type}_model.joblib')
    classifier.save_model(model_path)
    logger.info(f"Model saved to {model_path}")
    
    return {
        'model_type': model_type,
        'train_samples': len(X_train),
        'test_samples': len(X_test),
        'train_accuracy': train_results['accuracy'],
        'test_accuracy': accuracy,
        'classification_report': report,
        'confusion_matrix': conf_matrix,
        'model_path': model_path
    }


def compare_models(data: pd.DataFrame, model_dir: str = 'models') -> dict:
    """
    Train and compare multiple model types.
    
    Args:
        data: Training DataFrame
        model_dir: Directory to save models
        
    Returns:
        Dict with comparison results
    """
    logger.info("Comparing multiple models...")
    
    # Preprocess data
    preprocessor = DataPreprocessor()
    processed_df = preprocessor.clean_data(data)
    
    # Feature columns
    feature_cols = [
        'task_hours', 'tasks_completed', 'idle_hours',
        'social_media_usage', 'break_frequency'
    ]
    
    X = processed_df[feature_cols].values
    y = processed_df['category'].values
    
    # Train-test split
    from sklearn.model_selection import train_test_split
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, random_state=42, stratify=y
    )
    
    # Train multiple models
    classifier = MLClassifier()
    comparison = classifier.train_and_compare(X_train, y_train)
    
    results = {}
    
    for model_name, metrics in comparison.items():
        # Save each trained model
        os.makedirs(model_dir, exist_ok=True)
        
        # Get the model and evaluate on test set
        temp_classifier = MLClassifier(model_type=model_name)
        temp_classifier.train(X_train, y_train)
        
        y_pred = temp_classifier.model.predict(X_test)
        
        from sklearn.metrics import accuracy_score
        test_accuracy = accuracy_score(y_test, y_pred)
        
        # Save model
        model_path = os.path.join(model_dir, f'{model_name}_model.joblib')
        temp_classifier.save_model(model_path)
        
        results[model_name] = {
            'train_accuracy': metrics['accuracy'],
            'test_accuracy': test_accuracy,
            'model_path': model_path
        }
        
        logger.info(f"{model_name}: Train={metrics['accuracy']:.4f}, Test={test_accuracy:.4f}")
    
    # Find best model
    best_model = max(results.items(), key=lambda x: x[1]['test_accuracy'])
    
    logger.info(f"\nBest Model: {best_model[0]} (Test Accuracy: {best_model[1]['test_accuracy']:.4f})")
    
    return {
        'results': results,
        'best_model': best_model[0],
        'best_test_accuracy': best_model[1]['test_accuracy']
    }


def main():
    """Main entry point for training script."""
    parser = argparse.ArgumentParser(
        description='Train ML models for Fake Productivity Detection'
    )
    
    parser.add_argument(
        '--data',
        type=str,
        default=None,
        help='Path to training CSV file. If not provided, uses synthetic data.'
    )
    
    parser.add_argument(
        '--model',
        type=str,
        default='random_forest',
        choices=['logistic_regression', 'random_forest', 'decision_tree'],
        help='Model type to train (default: random_forest)'
    )
    
    parser.add_argument(
        '--compare',
        action='store_true',
        help='Compare all model types and select the best'
    )
    
    parser.add_argument(
        '--samples',
        type=int,
        default=1000,
        help='Number of synthetic samples to generate (default: 1000)'
    )
    
    parser.add_argument(
        '--output-dir',
        type=str,
        default='models',
        help='Directory to save trained models (default: models)'
    )
    
    parser.add_argument(
        '--test-size',
        type=float,
        default=0.2,
        help='Fraction of data for testing (default: 0.2)'
    )
    
    args = parser.parse_args()
    
    # Load or generate data
    if args.data:
        data = load_csv_data(args.data)
    else:
        logger.info(f"Generating {args.samples} synthetic training samples...")
        data = generate_synthetic_data(n_samples=args.samples)
    
    # Train models
    if args.compare:
        results = compare_models(data, model_dir=args.output_dir)
        print("\n" + "="*50)
        print("MODEL COMPARISON RESULTS")
        print("="*50)
        for model_name, metrics in results['results'].items():
            print(f"\n{model_name}:")
            print(f"  Train Accuracy: {metrics['train_accuracy']:.4f}")
            print(f"  Test Accuracy:  {metrics['test_accuracy']:.4f}")
            print(f"  Model Path:     {metrics['model_path']}")
        print(f"\nBest Model: {results['best_model']}")
        print(f"Best Test Accuracy: {results['best_test_accuracy']:.4f}")
    else:
        results = train_and_evaluate(
            data,
            model_type=args.model,
            model_dir=args.output_dir,
            test_size=args.test_size
        )
        print("\n" + "="*50)
        print("TRAINING RESULTS")
        print("="*50)
        print(f"Model Type:      {results['model_type']}")
        print(f"Train Samples:   {results['train_samples']}")
        print(f"Test Samples:    {results['test_samples']}")
        print(f"Train Accuracy:  {results['train_accuracy']:.4f}")
        print(f"Test Accuracy:   {results['test_accuracy']:.4f}")
        print(f"Model Path:      {results['model_path']}")


if __name__ == '__main__':
    main()
