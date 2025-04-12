"""
Similarity Analyzer Module for Code Plagiarism Detection

This module provides a unified interface for analyzing code submissions
using different similarity detection methods including TF-IDF and AST analysis.
"""

import os
from typing import Dict, List, Any, Optional

from .tfidf_analyzer import TFIDFAnalyzer
from .ast_analyzer import ASTAnalyzer
from .results_merger import ResultsMerger

class SimilarityAnalyzer:
    """
    A unified interface for analyzing code submissions for plagiarism.
    
    Supports multiple detection methods and combines their results.
    """
    
    def __init__(self, 
                 language: str = 'cpp', 
                 difficulty: str = 'medium',
                 use_ast: bool = True):
        """
        Initialize the similarity analyzer.
        
        Args:
            language: Programming language ('cpp', 'c', 'java', 'python', etc.)
            difficulty: Assignment difficulty ('easy', 'medium', 'difficult')
            use_ast: Whether to use AST analysis (if language supports it)
        """
        self.language = language
        self.difficulty = difficulty
        self.use_ast = use_ast
        
        # Initialize analyzers
        self.tfidf_analyzer = TFIDFAnalyzer(language, difficulty)
        self.results_merger = ResultsMerger()
        self.results_merger.adjust_for_difficulty(difficulty)
        
        # Initialize AST analyzer if requested and the language is supported
        self.ast_analyzer = None
        if use_ast:
            self.ast_analyzer = ASTAnalyzer(language, difficulty)
    
    def analyze_submissions(self, 
                           submissions: Dict[str, str], 
                           base_files: List[str] = None) -> Dict[str, Any]:
        """
        Analyze code submissions using available methods.
        
        Args:
            submissions: Dictionary mapping submission ID to code
            base_files: List of base files (starter code) to exclude from comparison
            
        Returns:
            Dictionary with merged analysis results
        """
        # Run TF-IDF analysis
        tfidf_results = self.tfidf_analyzer.analyze_submissions(submissions)
        
        # Run AST analysis if available
        ast_results = None
        if self.ast_analyzer:
            try:
                ast_results = self.ast_analyzer.analyze_submissions(submissions)
            except Exception as e:
                print(f"Warning: AST analysis failed: {str(e)}")
        
        # Merge results
        return self.results_merger.merge_results(tfidf_results, ast_results)
    
    def update_difficulty(self, difficulty: str) -> None:
        """
        Update the difficulty setting across all analyzers.
        
        Args:
            difficulty: Assignment difficulty ('easy', 'medium', 'difficult')
        """
        self.difficulty = difficulty
        self.tfidf_analyzer.difficulty = difficulty
        self.tfidf_analyzer.threshold = self.tfidf_analyzer.get_threshold(difficulty)
        self.results_merger.adjust_for_difficulty(difficulty)
        
        if self.ast_analyzer:
            self.ast_analyzer.difficulty = difficulty
            self.ast_analyzer.threshold = self.ast_analyzer.get_threshold(difficulty)
    
    def update_language(self, language: str) -> None:
        """
        Update the language setting across all analyzers.
        
        Args:
            language: Programming language ('cpp', 'c', 'java', 'python', etc.)
        """
        self.language = language
        self.tfidf_analyzer.language = language
        
        # Recreate AST analyzer if language changes
        if self.use_ast:
            self.ast_analyzer = ASTAnalyzer(language, self.difficulty) 