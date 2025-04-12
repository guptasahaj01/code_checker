"""
TF-IDF Analyzer for Code Similarity Detection

This module provides functionality for analyzing code submissions
using TF-IDF vectorization and cosine similarity.
"""

import re
import numpy as np
from typing import Dict, List, Tuple, Set, Any
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity


class TFIDFAnalyzer:
    """
    Analyzer for code similarity using TF-IDF and cosine similarity.
    """
    
    def __init__(self, language: str = 'cpp', difficulty: str = 'medium'):
        """
        Initialize the TF-IDF analyzer.
        
        Args:
            language: Programming language to analyze
            difficulty: Assignment difficulty level
        """
        self.language = language
        self.difficulty = difficulty
        self.threshold = self.get_threshold(difficulty)
        
        # Common regexes for code preprocessing
        self.comment_patterns = {
            'cpp': r'\/\/.*?$|\/\*[\s\S]*?\*\/',
            'c': r'\/\/.*?$|\/\*[\s\S]*?\*\/',
            'java': r'\/\/.*?$|\/\*[\s\S]*?\*\/',
            'python': r'#.*?$|\'\'\'[\s\S]*?\'\'\'|"""[\s\S]*?"""'
        }
        
        self.identifier_patterns = {
            'cpp': r'\b[a-zA-Z_][a-zA-Z0-9_]*\b',
            'c': r'\b[a-zA-Z_][a-zA-Z0-9_]*\b',
            'java': r'\b[a-zA-Z_$][a-zA-Z0-9_$]*\b',
            'python': r'\b[a-zA-Z_][a-zA-Z0-9_]*\b'
        }
    
    def tokenize_code(self, code: str) -> str:
        """
        Process and tokenize code for TF-IDF analysis.
        
        Args:
            code: Source code to process
            
        Returns:
            Processed and tokenized code
        """
        # Remove comments
        code = self._remove_comments(code)
        
        # Normalize whitespace
        code = self._normalize_whitespace(code)
        
        # Normalize identifiers (optional)
        # code = self._normalize_identifiers(code)
        
        # Use language-specific tokenization
        return self._tokenize_by_language(code)
    
    def _remove_comments(self, code: str) -> str:
        """Remove comments from code."""
        pattern = self.comment_patterns.get(self.language, r'\/\/.*?$|\/\*[\s\S]*?\*\/')
        return re.sub(pattern, ' ', code, flags=re.MULTILINE)
    
    def _normalize_whitespace(self, code: str) -> str:
        """Normalize whitespace in code."""
        # Replace newlines and tabs with spaces
        code = re.sub(r'[\r\n\t]+', ' ', code)
        # Collapse multiple spaces into one
        return re.sub(r'\s+', ' ', code)
    
    def _normalize_identifiers(self, code: str) -> str:
        """
        Replace identifiers with placeholders to reduce impact of variable naming.
        This is optional and depends on how strict the similarity check should be.
        """
        pattern = self.identifier_patterns.get(self.language, r'\b[a-zA-Z_][a-zA-Z0-9_]*\b')
        
        identifier_map = {}
        counter = 0
        
        def replace_identifier(match):
            nonlocal counter
            identifier = match.group(0)
            
            # Don't replace keywords
            if identifier in {'if', 'else', 'while', 'for', 'return', 'class', 'public', 'private', 
                              'protected', 'int', 'float', 'double', 'char', 'bool', 'void', 'true', 
                              'false', 'null', 'nullptr', 'this', 'super', 'new', 'delete', 'throw', 
                              'try', 'catch', 'finally', 'static'}:
                return identifier
            
            if identifier not in identifier_map:
                identifier_map[identifier] = f"ID_{counter}"
                counter += 1
            
            return identifier_map[identifier]
        
        return re.sub(pattern, replace_identifier, code)
    
    def _tokenize_by_language(self, code: str) -> str:
        """
        Tokenize code based on language-specific rules.
        Currently uses a simple space-based tokenization.
        """
        # This could be expanded with language-specific tokenizers
        return code
    
    def analyze_submissions(self, submissions: Dict[str, str]) -> Dict[str, Any]:
        """
        Analyze code submissions using TF-IDF and cosine similarity.
        
        Args:
            submissions: Dictionary mapping submission ID to code
            
        Returns:
            Dictionary with analysis results
        """
        if len(submissions) < 2:
            return {
                "submission_ids": list(submissions.keys()),
                "similarity_matrix": [],
                "suspicious_pairs": [],
                "average_similarity": 0.0,
                "max_similarity": 0.0
            }
        
        submission_ids = list(submissions.keys())
        tokenized_submissions = []
        
        # Tokenize all submissions
        for submission_id, code in submissions.items():
            tokenized_submissions.append(self.tokenize_code(code))
        
        # Create TF-IDF vectors
        vectorizer = TfidfVectorizer(analyzer='word', ngram_range=(1, 3), min_df=0.01, stop_words='english')
        tfidf_matrix = vectorizer.fit_transform(tokenized_submissions)
        
        # Calculate cosine similarity
        similarity_matrix = cosine_similarity(tfidf_matrix)
        
        # Find suspicious pairs
        suspicious_pairs = self._find_suspicious_pairs(submission_ids, similarity_matrix)
        
        # Calculate average and max similarity (excluding self-comparisons)
        n = similarity_matrix.shape[0]
        similarity_sum = 0.0
        max_similarity = 0.0
        count = 0
        
        for i in range(n):
            for j in range(i+1, n):
                similarity = similarity_matrix[i][j]
                similarity_sum += similarity
                max_similarity = max(max_similarity, similarity)
                count += 1
        
        average_similarity = similarity_sum / count if count > 0 else 0
        
        # Convert NumPy values to native Python types for serialization
        return {
            "submission_ids": submission_ids,
            "similarity_matrix": similarity_matrix.tolist(),  # Convert to list for serialization
            "suspicious_pairs": [(list(pair), float(similarity)) for pair, similarity in suspicious_pairs],
            "average_similarity": float(average_similarity),
            "max_similarity": float(max_similarity)
        }
    
    def _find_suspicious_pairs(self, submission_ids: List[str], similarity_matrix: np.ndarray) -> List[Tuple[Tuple[str, str], float]]:
        """
        Find pairs of submissions with suspiciously high similarity.
        
        Args:
            submission_ids: List of submission IDs
            similarity_matrix: Matrix of similarity scores
            
        Returns:
            List of (submission_pair, similarity) tuples
        """
        suspicious_pairs = []
        n = similarity_matrix.shape[0]
        
        for i in range(n):
            for j in range(i+1, n):
                similarity = similarity_matrix[i][j]
                
                if similarity >= self.threshold:
                    suspicious_pairs.append(
                        ((submission_ids[i], submission_ids[j]), similarity)
                    )
        
        # Sort by similarity (highest first)
        suspicious_pairs.sort(key=lambda x: x[1], reverse=True)
        
        return suspicious_pairs
    
    def get_threshold(self, difficulty: str) -> float:
        """
        Get similarity threshold based on difficulty.
        
        Args:
            difficulty: Assignment difficulty ('easy', 'medium', 'difficult')
            
        Returns:
            Similarity threshold for suspicious code detection
        """
        if difficulty == 'easy':
            return 0.5  # Lower threshold for easier detection
        elif difficulty == 'medium':
            return 0.4  # Lower threshold for medium difficulty
        else:  # difficult
            return 0.3  # Lower threshold for difficult assignments 