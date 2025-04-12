"""
AST Analyzer for Code Similarity Detection

This module provides AST-based analysis for detecting structural similarities
between code submissions, which can be more effective than text-based comparisons
for detecting plagiarism where variables and formatting have been changed.
"""

import ast
import os
import re
import numpy as np
from collections import Counter
from typing import Dict, List, Any, Set, Tuple


class ASTAnalyzer:
    """
    Analyzer that uses Abstract Syntax Trees for structural code comparison.
    
    This approach is more resistant to simple obfuscation techniques like:
    - Variable renaming
    - Comments modification
    - Whitespace changes
    - Simple statement reordering
    """
    
    def __init__(self, language: str = 'python', difficulty: str = 'medium'):
        """
        Initialize the AST analyzer.
        
        Args:
            language: Programming language ('python' supported natively, others require external parsers)
            difficulty: Assignment difficulty level ('easy', 'medium', 'difficult')
        """
        self.language = language
        self.difficulty = difficulty
        self.threshold = self.get_threshold(difficulty)
        
        # Language-specific patterns and processors
        self._setup_language_processors()
    
    def _setup_language_processors(self):
        """Set up language-specific processors and patterns."""
        # Base processors - Python is natively supported through the ast module
        self.parse_func = self._parse_python if self.language == 'python' else self._parse_other
        
        # Language specific patterns for preprocessing
        if self.language == 'python':
            self.comment_pattern = r'#.*$'
            self.extension = '.py'
        elif self.language in ['c', 'cpp', 'java', 'javascript', 'csharp']:
            # C-style languages
            self.comment_pattern = r'(/\*.*?\*/|//.*?$)'
            if self.language == 'c':
                self.extension = '.c'
            elif self.language == 'cpp':
                self.extension = '.cpp'
            elif self.language == 'java':
                self.extension = '.java'
            elif self.language == 'javascript':
                self.extension = '.js'
            elif self.language == 'csharp':
                self.extension = '.cs'
    
    def analyze_submissions(self, submissions: Dict[str, str]) -> Dict[str, Any]:
        """
        Analyze code submissions using AST-based similarity detection.
        
        Args:
            submissions: Dictionary mapping submission ID to code
            
        Returns:
            Dictionary with analysis results
        """
        if len(submissions) < 2:
            return {
                "suspicious_pairs": [],
                "similarity_matrix": [[1.0]],
                "average_similarity": 0.0,
                "max_similarity": 0.0
            }
        
        submission_ids = list(submissions.keys())
        
        # Parse code into ASTs
        parsed_submissions = {}
        node_types_by_submission = {}
        
        for submission_id, code in submissions.items():
            try:
                # Clean code and prepare for parsing
                cleaned_code = self._preprocess_code(code)
                
                # Parse code to get AST structure
                node_types, node_structure = self.parse_func(cleaned_code)
                
                parsed_submissions[submission_id] = node_structure
                node_types_by_submission[submission_id] = node_types
            except Exception as e:
                print(f"Warning: Could not parse {submission_id}: {str(e)}")
                # Store empty structures for submissions that can't be parsed
                parsed_submissions[submission_id] = []
                node_types_by_submission[submission_id] = Counter()
        
        # Calculate similarity matrix
        n = len(submission_ids)
        similarity_matrix = np.zeros((n, n))
        
        # Calculate node type similarities between all pairs of submissions
        for i in range(n):
            sid1 = submission_ids[i]
            for j in range(n):
                sid2 = submission_ids[j]
                
                if i == j:
                    similarity_matrix[i, j] = 1.0
                    continue
                
                # Calculate similarity based on AST structure
                structure_sim = self._calculate_structure_similarity(
                    parsed_submissions[sid1], 
                    parsed_submissions[sid2]
                )
                
                # Calculate similarity based on node type distribution
                types_sim = self._calculate_types_similarity(
                    node_types_by_submission[sid1],
                    node_types_by_submission[sid2]
                )
                
                # Combined similarity (weighted average)
                similarity_matrix[i, j] = 0.7 * structure_sim + 0.3 * types_sim
        
        # Find suspicious pairs
        suspicious_pairs = []
        for i in range(n):
            for j in range(i+1, n):  # Only upper triangle
                similarity = similarity_matrix[i, j]
                if similarity >= self.threshold:
                    suspicious_pairs.append(([submission_ids[i], submission_ids[j]], similarity))
        
        # Sort suspicious pairs by similarity (descending)
        suspicious_pairs.sort(key=lambda x: x[1], reverse=True)
        
        # Calculate average and max similarity (excluding self-comparisons)
        similarity_values = []
        for i in range(n):
            for j in range(i+1, n):  # Only consider upper triangle
                similarity_values.append(similarity_matrix[i, j])
        
        average_similarity = np.mean(similarity_values) if similarity_values else 0.0
        max_similarity = np.max(similarity_values) if similarity_values else 0.0
        
        return {
            "suspicious_pairs": suspicious_pairs,
            "similarity_matrix": similarity_matrix,
            "average_similarity": float(average_similarity),
            "max_similarity": float(max_similarity)
        }
    
    def _preprocess_code(self, code: str) -> str:
        """
        Preprocess code to prepare for AST parsing.
        
        Args:
            code: Source code string
            
        Returns:
            Preprocessed code
        """
        # Remove comments
        code = re.sub(self.comment_pattern, '', code, flags=re.MULTILINE | re.DOTALL)
        
        # Handle language-specific preprocessing
        if self.language == 'python':
            # Ensure proper indentation for Python
            lines = code.split('\n')
            if not any(line.startswith(' ') or line.startswith('\t') for line in lines if line.strip()):
                # If no indentation found, attempt basic auto-indentation
                indented_lines = []
                indent_level = 0
                for line in lines:
                    stripped = line.strip()
                    if stripped:
                        if stripped.endswith(':'):
                            indented_lines.append('    ' * indent_level + stripped)
                            indent_level += 1
                        elif any(stripped.startswith(x) for x in ['return', 'break', 'continue']):
                            if indent_level > 0:
                                indented_lines.append('    ' * (indent_level - 1) + stripped)
                            else:
                                indented_lines.append(stripped)
                        else:
                            indented_lines.append('    ' * indent_level + stripped)
                    else:
                        indented_lines.append('')
                
                code = '\n'.join(indented_lines)
        
        return code
    
    def _parse_python(self, code: str) -> Tuple[Counter, List]:
        """
        Parse Python code into AST representation.
        
        Args:
            code: Python source code
            
        Returns:
            Tuple of (node type counter, node structure list)
        """
        try:
            # Parse the code
            tree = ast.parse(code)
            
            # Count node types
            node_types = Counter()
            node_structure = []
            
            # Traverse the AST
            for node in ast.walk(tree):
                node_type = type(node).__name__
                node_types[node_type] += 1
                
                # Record only non-trivial nodes for structure comparison
                if node_type not in ['Load', 'Store', 'Del', 'Expr']:
                    # Get node fields to represent structure
                    fields = {}
                    for field, value in ast.iter_fields(node):
                        if isinstance(value, list):
                            fields[field] = len(value)
                        elif isinstance(value, ast.AST):
                            fields[field] = type(value).__name__
                        elif value is not None:
                            # Omit specific values, just store if there is a value
                            fields[field] = True
                    
                    node_structure.append((node_type, fields))
            
            return node_types, node_structure
        
        except SyntaxError as e:
            # If parsing fails, attempt to fix common syntax issues
            # This is a simplified approach - a more robust solution would use a proper parser
            fixed_code = self._attempt_syntax_fixes(code)
            return self._parse_python(fixed_code)
        
        except Exception as e:
            # If all parsing attempts fail, return empty structures
            return Counter(), []
    
    def _attempt_syntax_fixes(self, code: str) -> str:
        """
        Attempt to fix common syntax errors in Python code.
        
        Args:
            code: Python source code with potential syntax errors
            
        Returns:
            Code with attempted fixes
        """
        # Add missing colons after control statements
        code = re.sub(r'(if|while|for|def|class)\s+([^:]+)(?<!\n|\:)\s*\n', r'\1 \2:\n', code)
        
        # Ensure proper indentation
        lines = code.split('\n')
        indented_lines = []
        indent_level = 0
        for line in lines:
            stripped = line.strip()
            if not stripped:
                indented_lines.append('')
                continue
                
            if stripped.endswith(':'):
                indented_lines.append('    ' * indent_level + stripped)
                indent_level += 1
            elif any(stripped.startswith(x) for x in ['return', 'break', 'continue']):
                if indent_level > 0:
                    indented_lines.append('    ' * (indent_level - 1) + stripped)
                else:
                    indented_lines.append(stripped)
            else:
                indented_lines.append('    ' * indent_level + stripped)
        
        return '\n'.join(indented_lines)
    
    def _parse_other(self, code: str) -> Tuple[Counter, List]:
        """
        Parse code for languages other than Python.
        
        For non-Python languages, we use a simplified approach based on regex patterns
        to identify language structures. This is less accurate than a true AST parser
        but provides a reasonable approximation.
        
        Args:
            code: Source code in the specified language
            
        Returns:
            Tuple of (node type counter, node structure list)
        """
        # Simplified structural analysis for other languages
        node_types = Counter()
        node_structure = []
        
        # Define regex patterns for common structures
        # These are simplified approximations of language structures
        patterns = {
            'c': {
                'Function': r'(\w+)\s+(\w+)\s*\([^)]*\)\s*\{',
                'If': r'if\s*\([^)]*\)',
                'For': r'for\s*\([^)]*\)',
                'While': r'while\s*\([^)]*\)',
                'Switch': r'switch\s*\([^)]*\)',
                'StructDef': r'struct\s+(\w+)',
                'Return': r'return\s+[^;]*;'
            },
            'cpp': {
                'Function': r'(\w+)\s+(\w+)\s*\([^)]*\)\s*\{',
                'Class': r'class\s+(\w+)',
                'If': r'if\s*\([^)]*\)',
                'For': r'for\s*\([^)]*\)',
                'While': r'while\s*\([^)]*\)',
                'Try': r'try\s*\{',
                'Catch': r'catch\s*\([^)]*\)',
                'TemplateDecl': r'template\s*<[^>]*>',
                'Return': r'return\s+[^;]*;'
            },
            'java': {
                'Function': r'(\w+)\s+(\w+)\s*\([^)]*\)\s*\{',
                'Class': r'class\s+(\w+)',
                'Interface': r'interface\s+(\w+)',
                'If': r'if\s*\([^)]*\)',
                'For': r'for\s*\([^)]*\)',
                'While': r'while\s*\([^)]*\)',
                'Try': r'try\s*\{',
                'Catch': r'catch\s*\([^)]*\)',
                'Return': r'return\s+[^;]*;'
            }
        }
        
        # Default to C++ patterns if language not specifically handled
        lang_patterns = patterns.get(self.language, patterns['cpp'])
        
        # Count occurrences of each pattern
        for node_type, pattern in lang_patterns.items():
            matches = re.findall(pattern, code, re.MULTILINE)
            count = len(matches)
            if count > 0:
                node_types[node_type] = count
                # For structure analysis, record each match with position
                for match in re.finditer(pattern, code, re.MULTILINE):
                    node_structure.append((node_type, {
                        'position': match.start(),
                        'length': match.end() - match.start(),
                    }))
        
        # For languages other than Python, also consider the bracket depth profile
        # This gives us information about nesting structure
        bracket_depth = 0
        depth_profile = []
        
        for i, char in enumerate(code):
            if char == '{':
                bracket_depth += 1
            elif char == '}':
                bracket_depth -= 1
            
            if i % 20 == 0:  # Sample every 20 characters
                depth_profile.append(bracket_depth)
        
        # Add the depth profile as a structural element
        node_structure.append(('DepthProfile', {'profile': depth_profile}))
        
        return node_types, node_structure
    
    def _calculate_structure_similarity(self, structure1: List, structure2: List) -> float:
        """
        Calculate similarity based on structural elements.
        
        Args:
            structure1: Structural elements from first submission
            structure2: Structural elements from second submission
            
        Returns:
            Similarity score between 0.0 and 1.0
        """
        if not structure1 or not structure2:
            return 0.0
        
        # For Python, we have actual AST node structures
        if self.language == 'python':
            # Create structural fingerprints based on node types and relationship patterns
            fingerprint1 = self._create_structural_fingerprint(structure1)
            fingerprint2 = self._create_structural_fingerprint(structure2)
            
            # Calculate Jaccard similarity of fingerprints
            intersection = len(fingerprint1.intersection(fingerprint2))
            union = len(fingerprint1.union(fingerprint2))
            
            if union == 0:
                return 0.0
            
            return intersection / union
        
        # For other languages, use simpler sequence-based comparison
        else:
            # Extract types in sequence
            types1 = [item[0] for item in structure1 if item[0] != 'DepthProfile']
            types2 = [item[0] for item in structure2 if item[0] != 'DepthProfile']
            
            # Compare depth profiles if available
            depth_profile1 = next((item[1]['profile'] for item in structure1 if item[0] == 'DepthProfile'), [])
            depth_profile2 = next((item[1]['profile'] for item in structure2 if item[0] == 'DepthProfile'), [])
            
            # Calculate similarity of type sequences (using Jaccard)
            types_set1 = set(zip(types1, range(len(types1))))
            types_set2 = set(zip(types2, range(len(types2))))
            
            types_intersection = len(types_set1.intersection(types_set2))
            types_union = len(types_set1.union(types_set2))
            
            types_similarity = types_intersection / types_union if types_union > 0 else 0.0
            
            # Calculate depth profile similarity
            depth_similarity = 0.0
            if depth_profile1 and depth_profile2:
                # Normalize profiles to same length
                max_len = max(len(depth_profile1), len(depth_profile2))
                if max_len > 0:
                    norm_profile1 = self._normalize_profile(depth_profile1, max_len)
                    norm_profile2 = self._normalize_profile(depth_profile2, max_len)
                    
                    # Calculate mean squared error
                    mse = np.mean([(a - b) ** 2 for a, b in zip(norm_profile1, norm_profile2)])
                    # Convert to similarity (1.0 for identical, decreasing for more differences)
                    depth_similarity = 1.0 / (1.0 + mse)
            
            # Combine similarities (weighting types more heavily)
            return 0.7 * types_similarity + 0.3 * depth_similarity
    
    def _normalize_profile(self, profile: List[int], target_len: int) -> List[float]:
        """
        Normalize a profile to the target length using interpolation.
        
        Args:
            profile: List of values to normalize
            target_len: Target length for the normalized profile
            
        Returns:
            Normalized profile with length target_len
        """
        if len(profile) == target_len:
            return profile
        
        result = []
        scale = (len(profile) - 1) / (target_len - 1) if target_len > 1 else 0
        
        for i in range(target_len):
            if scale == 0:
                result.append(profile[0])
                continue
                
            pos = i * scale
            idx = int(pos)
            if idx >= len(profile) - 1:
                result.append(profile[-1])
            else:
                weight = pos - idx
                result.append((1 - weight) * profile[idx] + weight * profile[idx + 1])
        
        return result
    
    def _create_structural_fingerprint(self, structure: List) -> Set[Tuple]:
        """
        Create a fingerprint representing structural patterns.
        
        Args:
            structure: List of (node_type, fields) tuples
            
        Returns:
            Set of structural patterns
        """
        fingerprint = set()
        
        # Add individual node types
        for i, (node_type, _) in enumerate(structure):
            fingerprint.add(('NODE', node_type))
            
            # Add bi-grams of node types (sequential patterns)
            if i < len(structure) - 1:
                next_type = structure[i+1][0]
                fingerprint.add(('SEQ', node_type, next_type))
            
            # Add relationships between parent and child nodes
            # (simplified approximation based on sequence)
            for j in range(i+1, min(i+5, len(structure))):
                child_type = structure[j][0]
                fingerprint.add(('REL', node_type, child_type, j-i))
        
        return fingerprint
    
    def _calculate_types_similarity(self, types1: Counter, types2: Counter) -> float:
        """
        Calculate similarity based on node type distributions.
        
        Args:
            types1: Counter of node types from first submission
            types2: Counter of node types from second submission
            
        Returns:
            Similarity score between 0.0 and 1.0
        """
        if not types1 or not types2:
            return 0.0
        
        # Get all unique node types
        all_types = set(types1.keys()).union(set(types2.keys()))
        
        # Prepare vectors
        vec1 = np.array([types1.get(t, 0) for t in all_types])
        vec2 = np.array([types2.get(t, 0) for t in all_types])
        
        # Normalize vectors (to account for different code sizes)
        norm1 = np.linalg.norm(vec1)
        norm2 = np.linalg.norm(vec2)
        
        if norm1 == 0 or norm2 == 0:
            return 0.0
        
        vec1_norm = vec1 / norm1
        vec2_norm = vec2 / norm2
        
        # Calculate cosine similarity
        return float(np.dot(vec1_norm, vec2_norm))
    
    def get_threshold(self, difficulty: str) -> float:
        """
        Get similarity threshold based on difficulty.
        
        Args:
            difficulty: Assignment difficulty level ('easy', 'medium', 'difficult')
            
        Returns:
            Similarity threshold
        """
        if difficulty == 'easy':
            return 0.8  # Higher threshold for easy assignments
        elif difficulty == 'medium':
            return 0.7  # Default threshold
        else:  # 'difficult'
            return 0.6  # Lower threshold for difficult assignments 