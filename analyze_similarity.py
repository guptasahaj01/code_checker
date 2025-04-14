#!/usr/bin/env python3
"""
Similarity Analysis Script

This script analyzes the similarity between solutions organized in the specified directory.
"""

import os
import json
import sys
from pathlib import Path

# Add parent directory to path to ensure imports work correctly
current_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.append(current_dir)

# Import the similarity analyzer
from Processing.similarity_analysis.similarity_analyzer import SimilarityAnalyzer


def analyze_similarity(solutions_dir, language="cpp", difficulty="medium", use_ast=True):
    """
    Analyze similarity between solutions.
    
    Args:
        solutions_dir: Directory containing organized solutions
        language: Programming language of the solutions
        difficulty: Difficulty level ('easy', 'medium', 'difficult')
        use_ast: Whether to use AST analysis
        
    Returns:
        Dictionary containing analysis results
    """
    # Find all solution directories
    solution_dirs = []
    results = {}
    
    if os.path.exists(solutions_dir):
        print(f"Found organized solutions in {solutions_dir}/")
        solution_dirs = [d for d in os.listdir(solutions_dir) if d.startswith("solution")]
        solution_dirs.sort()
        print(f"Found {len(solution_dirs)} solution directories")
    else:
        print(f"No organized solutions found at {solutions_dir}.")
        return results
    
    # Analyze each solution
    for solution_dir in solution_dirs:
        solution_path = os.path.join(solutions_dir, solution_dir)
        
        # Get all .txt files in the solution directory
        submission_files = [f for f in os.listdir(solution_path) if f.endswith('.txt')]
        
        if len(submission_files) < 2:
            print(f"Skipping {solution_dir} - Not enough submissions for comparison.")
            continue
        
        print(f"\nAnalyzing {solution_dir} ({len(submission_files)} submissions)...")
        
        # Read all submissions
        submissions = {}
        for file in submission_files:
            with open(os.path.join(solution_path, file), 'r') as f:
                submissions[file] = f.read()
        
        # Create similarity analyzer
        analyzer = SimilarityAnalyzer(language, difficulty, use_ast)
        
        # Analyze submissions
        similarity_results = analyzer.analyze_submissions(submissions)
        
        # Save results to file
        results_file = os.path.join(solution_path, "similarity_results.json")
        with open(results_file, 'w') as f:
            json.dump(similarity_results, f, indent=2)
        
        # Print summary
        print(f"  Detection methods: {', '.join(similarity_results['detection_methods'])}")
        print(f"  Suspicious pairs: {len(similarity_results['all_suspicious_pairs'])}")
        print(f"  High confidence matches: {len(similarity_results['high_confidence_pairs'])}")
        print(f"  Pairs needing review: {len(similarity_results['needs_review_pairs'])}")
        print(f"  Detailed results saved to {results_file}")
        
        # Store results
        results[solution_dir] = similarity_results
    
    return results


def main():
    """Main function to analyze similarity."""
    import argparse
    
    parser = argparse.ArgumentParser(description="Analyze similarity between code solutions.")
    parser.add_argument("solutions_dir", help="Directory containing organized solutions")
    parser.add_argument("--language", "-l", default="cpp", help="Programming language")
    parser.add_argument("--difficulty", "-d", default="medium", choices=['easy', 'medium', 'difficult'], 
                        help="Assignment difficulty")
    parser.add_argument("--no-ast", dest="use_ast", action="store_false", 
                        help="Disable AST analysis")
    
    args = parser.parse_args()
    
    # Analyze similarity
    results = analyze_similarity(
        args.solutions_dir, 
        language=args.language,
        difficulty=args.difficulty,
        use_ast=args.use_ast
    )
    
    # Save overall results
    output_file = os.path.join(args.solutions_dir, "similarity_analysis.json")
    with open(output_file, 'w') as f:
        json.dump(results, f, indent=2)
    
    print(f"\nOverall similarity analysis saved to {output_file}")


if __name__ == "__main__":
    main() 