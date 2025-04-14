"""
Results Merger Module

This module provides functionality for merging results from different
plagiarism detection approaches, including TF-IDF and AST analysis.
"""

import numpy as np
from typing import Dict, List, Any, Tuple, Set


class ResultsMerger:
    """
    Merges results from different plagiarism detection methods.
    """
    
    def __init__(self, 
                high_threshold: float = 0.8, 
                review_threshold: float = 0.3):
        """
        Initialize the results merger.
        
        Args:
            high_threshold: Threshold for high confidence matches
            review_threshold: Threshold for matches needing review
        """
        self.high_threshold = high_threshold
        self.review_threshold = review_threshold
        
        # Weights for combining results from different methods
        self.tfidf_weight = 0.6
        self.ast_weight = 0.4
    
    def merge_results(self, 
                     tfidf_results: Dict[str, Any] = None,
                     ast_results: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        Merge results from TF-IDF and AST analysis.
        
        Args:
            tfidf_results: Results from TF-IDF analysis
            ast_results: Results from AST analysis
            
        Returns:
            Dictionary with merged analysis results
        """
        # Initialize merged results
        merged_results = {
            "high_confidence_pairs": [],
            "needs_review_pairs": [],
            "all_suspicious_pairs": [],
            "detection_methods": [],
        }
        
        # Track all pairs with their similarities for combined analysis
        pair_similarities = {}
        
        # Create pair dictionaries to ensure we track all pairs from both methods
        all_pairs_dict = {}
        
        # Process TF-IDF results
        if tfidf_results:
            merged_results["detection_methods"].append("TF-IDF")
            
            # Add TF-IDF similarity matrix and other metrics
            if "similarity_matrix" in tfidf_results:
                # Convert numpy array to list for JSON serialization
                if isinstance(tfidf_results["similarity_matrix"], np.ndarray):
                    merged_results["tfidf_similarity_matrix"] = tfidf_results["similarity_matrix"].tolist()
                else:
                    merged_results["tfidf_similarity_matrix"] = tfidf_results["similarity_matrix"]
            
            if "average_similarity" in tfidf_results:
                merged_results["tfidf_average_similarity"] = float(tfidf_results["average_similarity"])
            
            if "max_similarity" in tfidf_results:
                merged_results["tfidf_max_similarity"] = float(tfidf_results["max_similarity"])
            
            # Process suspicious pairs from TF-IDF
            if "suspicious_pairs" in tfidf_results:
                for pair, similarity in tfidf_results["suspicious_pairs"]:
                    # Sort pair to ensure consistent keys
                    sorted_pair = tuple(sorted(pair))
                    similarity = float(similarity)
                    
                    # Store with tfidf weight
                    pair_similarities[sorted_pair] = {
                        "tfidf": similarity,
                        "pair": pair,
                        "methods": ["TF-IDF"]
                    }
                    
                    # Track all pairs for cross-method matching
                    all_pairs_dict[sorted_pair] = pair
        
        # Process AST results
        if ast_results:
            merged_results["detection_methods"].append("AST")
            
            # Add AST similarity matrix and other metrics
            if "similarity_matrix" in ast_results:
                # Convert numpy array to list for JSON serialization
                if isinstance(ast_results["similarity_matrix"], np.ndarray):
                    merged_results["ast_similarity_matrix"] = ast_results["similarity_matrix"].tolist()
                else:
                    merged_results["ast_similarity_matrix"] = ast_results["similarity_matrix"]
            
            if "average_similarity" in ast_results:
                merged_results["ast_average_similarity"] = float(ast_results["average_similarity"])
            
            if "max_similarity" in ast_results:
                merged_results["ast_max_similarity"] = float(ast_results["max_similarity"])
            
            # Process suspicious pairs from AST
            if "suspicious_pairs" in ast_results:
                for pair, similarity in ast_results["suspicious_pairs"]:
                    # Sort pair to ensure consistent keys
                    sorted_pair = tuple(sorted(pair))
                    similarity = float(similarity)
                    
                    # Track all pairs for cross-method matching
                    all_pairs_dict[sorted_pair] = pair
                    
                    if sorted_pair in pair_similarities:
                        # Update existing entry
                        pair_similarities[sorted_pair]["ast"] = similarity
                        pair_similarities[sorted_pair]["methods"].append("AST")
                    else:
                        # Create new entry
                        pair_similarities[sorted_pair] = {
                            "ast": similarity,
                            "pair": pair,
                            "methods": ["AST"]
                        }
        
        # Make sure all pairs are represented in both methods if possible
        if tfidf_results and ast_results:
            # For each pair in TF-IDF, make sure we have a corresponding AST entry if available
            tfidf_submission_ids = tfidf_results.get("submission_ids", [])
            ast_submission_ids = ast_results.get("submission_ids", [])
            
            # Get similarity matrices
            tfidf_matrix = tfidf_results.get("similarity_matrix", [])
            ast_matrix = ast_results.get("similarity_matrix", [])
            
            # Add any missing TF-IDF entries for pairs found in AST
            for sorted_pair, original_pair in all_pairs_dict.items():
                if sorted_pair not in pair_similarities and tfidf_submission_ids:
                    # Create a new entry with TF-IDF=0
                    pair_similarities[sorted_pair] = {
                        "tfidf": 0.0,
                        "pair": original_pair,
                        "methods": []
                    }
                
                # If a pair exists in one method but not the other, find its similarity in the other method
                if sorted_pair in pair_similarities:
                    data = pair_similarities[sorted_pair]
                    
                    # If TF-IDF is missing but we have TF-IDF results
                    if "tfidf" not in data and tfidf_submission_ids:
                        # Find the indices in the TF-IDF matrix
                        try:
                            idx1 = tfidf_submission_ids.index(sorted_pair[0])
                            idx2 = tfidf_submission_ids.index(sorted_pair[1])
                            
                            if tfidf_matrix and idx1 < len(tfidf_matrix) and idx2 < len(tfidf_matrix[idx1]):
                                # Get the TF-IDF similarity
                                tfidf_sim = tfidf_matrix[idx1][idx2]
                                data["tfidf"] = float(tfidf_sim)
                                if "TF-IDF" not in data["methods"]:
                                    data["methods"].append("TF-IDF")
                        except (ValueError, IndexError):
                            # If we can't find the indices, set TF-IDF to 0
                            data["tfidf"] = 0.0
                    
                    # If AST is missing but we have AST results
                    if "ast" not in data and ast_submission_ids:
                        # Find the indices in the AST matrix
                        try:
                            idx1 = ast_submission_ids.index(sorted_pair[0])
                            idx2 = ast_submission_ids.index(sorted_pair[1])
                            
                            if ast_matrix and idx1 < len(ast_matrix) and idx2 < len(ast_matrix[idx1]):
                                # Get the AST similarity
                                ast_sim = ast_matrix[idx1][idx2]
                                data["ast"] = float(ast_sim)
                                if "AST" not in data["methods"]:
                                    data["methods"].append("AST")
                        except (ValueError, IndexError):
                            # If we can't find the indices, leave AST as is
                            pass
        
        # Calculate combined similarities
        for sorted_pair, data in pair_similarities.items():
            pair = data["pair"]
            methods = data["methods"]
            
            # Initialize with available values
            tfidf_sim = data.get("tfidf", 0.0)
            ast_sim = data.get("ast", 0.0)
            
            # Calculate weighted similarity
            if "TF-IDF" in methods and "AST" in methods:
                # Both methods available, use weighted average
                combined_similarity = (
                    self.tfidf_weight * tfidf_sim + 
                    self.ast_weight * ast_sim
                )
                detection_method = "Combined"
            elif "TF-IDF" in methods:
                # Only TF-IDF available
                combined_similarity = tfidf_sim
                detection_method = "TF-IDF"
            else:
                # Only AST available
                combined_similarity = ast_sim
                detection_method = "AST"
            
            # Add to all suspicious pairs
            merged_results["all_suspicious_pairs"].append(list(pair))
            
            # Always include TF-IDF and AST values, never set to null
            result_entry = {
                "pair": list(pair),
                "similarity": combined_similarity,
                "tfidf_similarity": tfidf_sim if "TF-IDF" in methods else 0.0,
                "ast_similarity": ast_sim if "AST" in methods else 0.0,
                "detection_method": detection_method
            }
            
            # Categorize based on similarity threshold
            if combined_similarity >= self.high_threshold:
                merged_results["high_confidence_pairs"].append(result_entry)
            elif combined_similarity >= self.review_threshold:
                merged_results["needs_review_pairs"].append(result_entry)
        
        # Calculate combined average and max similarity
        if tfidf_results and ast_results:
            # If both methods are available, combine their averages and maxes
            if "average_similarity" in tfidf_results and "average_similarity" in ast_results:
                merged_results["average_similarity"] = (
                    self.tfidf_weight * float(tfidf_results["average_similarity"]) + 
                    self.ast_weight * float(ast_results["average_similarity"])
                )
            
            if "max_similarity" in tfidf_results and "max_similarity" in ast_results:
                merged_results["max_similarity"] = max(
                    float(tfidf_results["max_similarity"]),
                    float(ast_results["max_similarity"])
                )
        elif tfidf_results:
            # Only TF-IDF available
            if "average_similarity" in tfidf_results:
                merged_results["average_similarity"] = float(tfidf_results["average_similarity"])
            if "max_similarity" in tfidf_results:
                merged_results["max_similarity"] = float(tfidf_results["max_similarity"])
        elif ast_results:
            # Only AST available
            if "average_similarity" in ast_results:
                merged_results["average_similarity"] = float(ast_results["average_similarity"])
            if "max_similarity" in ast_results:
                merged_results["max_similarity"] = float(ast_results["max_similarity"])
        
        # Add summary
        merged_results["summary"] = self._generate_summary(merged_results, tfidf_results, ast_results)
        
        return merged_results
    
    def _generate_summary(self, merged_results: Dict[str, Any], 
                        tfidf_results: Dict[str, Any] = None, 
                        ast_results: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        Generate a summary of the merged results.
        
        Args:
            merged_results: The merged results
            tfidf_results: Results from TF-IDF analysis
            ast_results: Results from AST analysis
            
        Returns:
            Dictionary with summary information
        """
        summary = {
            "total_submissions": 0,  # Will be set by the caller
            "high_confidence_count": len(merged_results["high_confidence_pairs"]),
            "needs_review_count": len(merged_results["needs_review_pairs"]),
            "total_suspicious_pairs": len(merged_results["all_suspicious_pairs"]),
            "detection_methods": merged_results["detection_methods"],
        }
        
        # Count unique suspicious submissions
        suspicious_submissions = set()
        for pair in merged_results["all_suspicious_pairs"]:
            suspicious_submissions.update(pair)
        
        summary["suspicious_submissions_count"] = len(suspicious_submissions)
        
        # Add method-specific metrics
        if "TF-IDF" in merged_results["detection_methods"]:
            if tfidf_results and "average_similarity" in tfidf_results:
                summary["tfidf_avg_similarity"] = float(tfidf_results["average_similarity"])
            if tfidf_results and "max_similarity" in tfidf_results:
                summary["tfidf_max_similarity"] = float(tfidf_results["max_similarity"])
        
        if "AST" in merged_results["detection_methods"]:
            if ast_results and "average_similarity" in ast_results:
                summary["ast_avg_similarity"] = float(ast_results["average_similarity"])
            if ast_results and "max_similarity" in ast_results:
                summary["ast_max_similarity"] = float(ast_results["max_similarity"])
        
        # Add combined metrics if both methods used
        if "TF-IDF" in merged_results["detection_methods"] and "AST" in merged_results["detection_methods"]:
            if "average_similarity" in merged_results:
                summary["combined_avg_similarity"] = merged_results["average_similarity"]
            if "max_similarity" in merged_results:
                summary["combined_max_similarity"] = merged_results["max_similarity"]
        
        return summary
    
    def adjust_for_difficulty(self, difficulty: str) -> None:
        """
        Adjust thresholds based on assignment difficulty.
        
        Args:
            difficulty: Assignment difficulty level ('easy', 'medium', 'difficult')
        """
        if difficulty == 'easy':
            # Higher thresholds for easy assignments
            self.high_threshold = 0.9
            self.review_threshold = 0.4
        elif difficulty == 'medium':
            # Default thresholds
            self.high_threshold = 0.8
            self.review_threshold = 0.3
        else:  # difficult
            # Lower thresholds for difficult assignments
            self.high_threshold = 0.7
            self.review_threshold = 0.2 