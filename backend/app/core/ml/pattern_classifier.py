"""Pattern classifier combining structural features with TF-IDF text vectors."""

import json
import logging
import pickle
import re
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import numpy as np
from sklearn.ensemble import RandomForestClassifier
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics import accuracy_score, classification_report, confusion_matrix
from sklearn.model_selection import cross_val_score, train_test_split
from sklearn.preprocessing import LabelEncoder

from app.core.constants import PATTERN_LABELS
from app.core.language.ast import Program

logger = logging.getLogger(__name__)


class PatternClassifier:
    """
    Classifier for algorithmic patterns in pseudocode using AST features and TF-IDF.
    Uses a Random Forest model for classification.
    """

    PATTERN_LABELS = PATTERN_LABELS

    def __init__(self, model_path: Optional[str] = None):
        """
        Initialize the PatternClassifier.
        """
        self.model = RandomForestClassifier(
            n_estimators=100,
            max_depth=15,
            min_samples_split=5,
            random_state=42,
            n_jobs=-1,
        )
        self.text_vectorizer = TfidfVectorizer(
            max_features=50,
            ngram_range=(1, 2),
            stop_words=None,
        )
        self.label_encoder = LabelEncoder()
        self.is_trained = False
        self.structural_feature_names = [
            "line_count",
            "loop_count",
            "conditional_count",
            "has_recursion",
            "has_memoization",
            "call_count",
            "nested_loop_depth",
            "has_graph_ops",
        ]

        if model_path and Path(model_path).exists():
            self.load_model(model_path)

    def extract_ast_features(self, program_ast: Program) -> Dict[str, int]:
        """
        Extract features from the AST of the pseudocode.
        """
        features = {
            "total_statements": 0,
            "recursive_calls": 0,
            "loop_count": 0,
            "nested_loop_depth": 0,
            "conditional_count": 0,
            "return_count": 0,
            "array_operations": 0,
            "function_count": 0,
            "has_memoization": 0,
            "has_graph_ops": 0,
            "max_recursion_depth": 0,
            "variable_count": 0,
        }

        def traverse_ast(node, depth=0, loop_depth=0):
            """Recursively traverse AST to count features."""
            node_type = type(node).__name__

            features["total_statements"] += 1
            features["nested_loop_depth"] = max(
                features["nested_loop_depth"], loop_depth
            )

            if node_type == "SubroutineDef":
                features["function_count"] += 1
                for stmt in node.body:
                    traverse_ast(stmt, depth + 1, loop_depth)

            elif node_type == "ForLoop":
                features["loop_count"] += 1
                for stmt in node.body:
                    traverse_ast(stmt, depth + 1, loop_depth + 1)

            elif node_type == "WhileLoop":
                features["loop_count"] += 1
                for stmt in node.body:
                    traverse_ast(stmt, depth + 1, loop_depth + 1)

            elif node_type == "RepeatUntilLoop":
                features["loop_count"] += 1
                for stmt in node.body:
                    traverse_ast(stmt, depth + 1, loop_depth + 1)

            elif node_type == "IfStatement":
                features["conditional_count"] += 1
                for stmt in node.true_branch:
                    traverse_ast(stmt, depth + 1, loop_depth)
                if node.false_branch:
                    for stmt in node.false_branch:
                        traverse_ast(stmt, depth + 1, loop_depth)

            elif node_type == "ReturnStatement":
                features["return_count"] += 1

            elif node_type == "FunctionCall":
                call_name = str(node.function).lower()
                if "memo" in call_name or "cache" in call_name:
                    features["has_memoization"] = 1
                if (
                    "graph" in call_name
                    or "neighbor" in call_name
                    or "edge" in call_name
                ):
                    features["has_graph_ops"] = 1

            elif node_type == "ArrayAccess":
                features["array_operations"] += 1

            elif node_type == "VarDecl":
                features["variable_count"] += len(node.items)

            if hasattr(node, "__dict__"):
                for attr_value in node.__dict__.values():
                    if isinstance(attr_value, list):
                        for item in attr_value:
                            if hasattr(item, "__class__"):
                                traverse_ast(item, depth + 1, loop_depth)

        for stmt in program_ast.statements:
            traverse_ast(stmt)

        return features

    def extract_text_features(self, pseudocode: str) -> np.ndarray:
        """
        Extract TF-IDF text features from the pseudocode.
        """
        if not hasattr(self.text_vectorizer, "vocabulary_"):
            return np.zeros(50)

        try:
            features = self.text_vectorizer.transform([pseudocode])
            return features.toarray()[0]
        except Exception as e:
            logger.warning("TF-IDF extraction failed: %s", str(e))
            return np.zeros(self.text_vectorizer.max_features or 50)

    def combine_features(
        self, ast_features: Dict[str, float], text_features: np.ndarray
    ) -> np.ndarray:
        """
        Combine AST and text features into a single feature vector.
        """
        ast_array = np.array(list(ast_features.values()))
        combined = np.concatenate([ast_array, text_features])
        return combined

    def train(
        self, dataset_path: str, test_size: float = 0.2, cv_folds: int = 5
    ) -> Dict[str, Any]:
        """
        Train the classifier on the dataset.
        """
        logger.info("Loading dataset from %s", dataset_path)

        with open(dataset_path, "r", encoding="utf-8") as f:
            dataset = json.load(f)

        if not dataset:
            raise ValueError("Dataset is empty")

        x_text = [item["pseudocode"] for item in dataset]
        y_labels = [item["pattern"] for item in dataset]

        logger.info("Fitting TF-IDF vectorizer...")
        self.text_vectorizer.fit(x_text)
        x_text_features = self.text_vectorizer.transform(x_text).toarray()

        structural = [self._extract_structural_features(code) for code in x_text]
        structural_matrix = np.array(
            [
                [feat[name] for name in self.structural_feature_names]
                for feat in structural
            ]
        )

        x = np.concatenate([structural_matrix, x_text_features], axis=1)

        self.label_encoder.fit(PATTERN_LABELS)
        y = self.label_encoder.transform(y_labels)

        x_train, x_test, y_train, y_test = train_test_split(
            x, y, test_size=test_size, random_state=42, stratify=y
        )

        logger.info("Training on %d examples, testing on %d", len(x_train), len(x_test))

        self.model.fit(x_train, y_train)
        self.is_trained = True

        y_pred = self.model.predict(x_test)
        accuracy = accuracy_score(y_test, y_pred)

        cv_scores = cross_val_score(self.model, x_train, y_train, cv=cv_folds)

        report = classification_report(
            y_test,
            y_pred,
            target_names=self.label_encoder.classes_,
            output_dict=True,
        )

        conf_matrix = confusion_matrix(y_test, y_pred)

        results = {
            "accuracy": accuracy,
            "cv_mean": cv_scores.mean(),
            "cv_std": cv_scores.std(),
            "classification_report": report,
            "confusion_matrix": conf_matrix.tolist(),
            "train_size": len(x_train),
            "test_size": len(x_test),
        }

        logger.info(
            "Training complete: Accuracy = %f, CV = %f +/- %f",
            round(accuracy, 3),
            round(cv_scores.mean(), 3),
            round(cv_scores.std(), 3),
        )

        return results

    def predict_top_k(self, pseudocode: str, k: int = 3) -> List[Tuple[str, float]]:
        """
        Predict the top K algorithmic patterns for given pseudocode.
        """
        if not self.is_trained:
            raise ValueError("Model must be trained before prediction")

        combined_vector = self._build_feature_vector(pseudocode)
        probabilities = self.model.predict_proba(combined_vector)[0]

        top_k_indices = np.argsort(probabilities)[-k:][::-1]

        results = []
        for idx in top_k_indices:
            pattern = self.label_encoder.inverse_transform([idx])[0]
            prob = probabilities[idx]
            results.append((pattern, prob))

        return results

    def save_model(self, model_path: str):
        """
        Save trained model to disk.
        """
        if not self.is_trained:
            raise ValueError("Cannot save untrained model")

        model_file = Path(model_path)
        model_file.parent.mkdir(parents=True, exist_ok=True)

        model_data = {
            "model": self.model,
            "vectorizer": self.text_vectorizer,
            "label_encoder": self.label_encoder,
            "is_trained": self.is_trained,
        }

        with open(model_file, "wb") as f:
            pickle.dump(model_data, f)

        logger.info("Model saved to %s", model_path)

    def load_model(self, model_path: str):
        """
        Load trained model from disk.
        """
        with open(model_path, "rb") as f:
            model_data = pickle.load(f)

        self.model = model_data["model"]
        self.text_vectorizer = model_data["vectorizer"]
        self.label_encoder = model_data["label_encoder"]
        self.is_trained = model_data["is_trained"]

        logger.info("Model loaded from %s", model_path)

    def get_feature_importance(self, top_n: int = 10) -> List[Tuple[str, float]] | Any:
        """
        Get top N important features from the trained model.
        """
        if not self.is_trained:
            raise ValueError("Model must be trained first")

        importances = self.model.feature_importances_
        feature_names = [f"struct_{name}" for name in self.structural_feature_names]
        feature_names.extend(list(self.text_vectorizer.get_feature_names_out()))
        indices = np.argsort(importances)[-top_n:][::-1]

        results = [
            (
                feature_names[idx] if idx < len(feature_names) else f"feature_{idx}",
                importances[idx],
            )
            for idx in indices
        ]

        return results

    def _extract_structural_features(self, pseudocode: str) -> Dict[str, float]:
        lower = pseudocode.lower()
        features = {
            "line_count": float(
                len([ln for ln in pseudocode.splitlines() if ln.strip()])
            ),
            "loop_count": float(len(re.findall(r"\b(for|while|repeat)\b", lower))),
            "conditional_count": float(len(re.findall(r"\bif\b", lower))),
            "has_recursion": 1.0 if self._has_recursion(pseudocode) else 0.0,
            "has_memoization": (
                1.0 if any(token in lower for token in ["memo", "cache", "dp"]) else 0.0
            ),
            "call_count": float(len(re.findall(r"\bcall\s+[a-z_][a-z0-9_]*", lower))),
            "nested_loop_depth": float(self._estimate_nested_loops(lower)),
            "has_graph_ops": (
                1.0
                if any(
                    word in lower for word in ["graph", "neighbor", "edge", "vertex"]
                )
                else 0.0
            ),
        }
        return features

    def _estimate_nested_loops(self, pseudocode: str) -> int:
        depth = 0
        max_depth = 0
        for line in pseudocode.splitlines():
            if re.search(r"\b(for|while|repeat)\b", line):
                depth += 1
                max_depth = max(max_depth, depth)
            if line.strip().lower() == "end":
                depth = max(0, depth - 1)
        return max_depth

    def _build_feature_vector(self, pseudocode: str) -> np.ndarray:
        structural = self._extract_structural_features(pseudocode)
        structural_vector = np.array(
            [[structural[name] for name in self.structural_feature_names]]
        )
        text_features = self.extract_text_features(pseudocode)
        text_vector = text_features.reshape(1, -1)
        if structural_vector.shape[1] == 0:
            return text_vector
        return np.concatenate([structural_vector, text_vector], axis=1)

    def _heuristic_predict(self, pseudocode: str) -> Tuple[str, float]:
        lower = pseudocode.lower()
        heuristics = [
            ("dynamic_programming", ["memo", "cache", "dp", "table"]),
            ("divide_and_conquer", ["pivot", "partition", "divid", "merge"]),
            ("graph_algorithms", ["graph", "edge", "vertex", "neighbor", "queue"]),
            ("backtracking", ["backtrack", "n_queens", "constraint", "search tree"]),
            ("greedy", ["greedy", "best", "priority", "select"]),
            ("sorting", ["sort", "swap", "array", "compare"]),
        ]

        for label, keywords in heuristics:
            if any(keyword in lower for keyword in keywords):
                return label, 0.55
        return "brute_force", 0.4

    def _has_recursion(self, pseudocode: str) -> bool:
        lowered = pseudocode.lower()
        if re.search(r"\bcall\s+[a-z_][a-z0-9_]*", lowered):
            return True
        header = re.search(r"^\s*([a-z_][a-z0-9_]*)\s*\(", lowered, re.MULTILINE)
        if not header:
            return False
        func_name = header.group(1)
        occurrences = re.findall(rf"\b{re.escape(func_name)}\s*\(", lowered)
        return len(occurrences) > 1

    def predict(
        self, pseudocode: str, program_ast: Optional[Program] = None
    ) -> Tuple[str, float] | Any:
        """Predict algorithmic pattern; fall back to heuristics if untrained."""
        if not self.is_trained:
            logger.warning("Model not trained; reverting to heuristics")
            return self._heuristic_predict(pseudocode)

        return self._predict_with_model(pseudocode)

    def _predict_with_model(self, pseudocode: str) -> Tuple[str, float]:
        combined_vector = self._build_feature_vector(pseudocode)

        prediction = self.model.predict(combined_vector)[0]
        probabilities = self.model.predict_proba(combined_vector)[0]

        pattern = self.label_encoder.inverse_transform([prediction])[0]
        confidence = probabilities[prediction]

        return pattern, confidence
