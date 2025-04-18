#!/usr/bin/env python3
"""
Comprehensive Code Plagiarism Detection System

This script processes PDF assignments, extracts code, and analyzes similarity using multiple detection methods:
1. Student-to-student similarity analysis
2. AI-generated code detection
3. Web plagiarism checking
"""

import os
import sys
import json
import argparse
import shutil
from pathlib import Path
from typing import List, Dict, Tuple, Any

# Add aiplagarism directory to path
Code_Checker=os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
sys.path.append(Code_Checker)
# Local imports
from Processing.code_extraction.batch_processor import BatchProcessor
from Processing.code_extraction.complete_solution_extractor import CompleteSolutionExtractor
from Processing.similarity_analysis.similarity_analyzer import SimilarityAnalyzer

# Import AI plagiarism detector
try:
    from Processing.AI_plagarism_detector.chaicheck import CppAIDetector
    AI_DETECTOR_AVAILABLE = True
except ImportError:
    print("Warning: AI detection module not available. AI plagiarism detection will be disabled.")
    AI_DETECTOR_AVAILABLE = False

# Import web plagiarism checker
try:
    from Processing.web_plagiarism_detector.web_plagiarism_checker import WebPlagiarismChecker
    WEB_CHECKER_AVAILABLE = True
except ImportError:
    print("Warning: Web plagiarism checker not available. Web plagiarism detection will be disabled.")
    WEB_CHECKER_AVAILABLE = False

# Config file for storing API key
CONFIG_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'config.json')

# you dont really need save_api_key and load_api_key as the api is being provided directlyby api_server.py
def save_api_key(api_key: str) -> None:
    """
    Save the API key to a local configuration file.
    
    Args:
        api_key: The SerpAPI key to save
    """
    config = {}
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, 'r') as f:
                config = json.load(f)
        except:
            pass
    
    config['serp_api_key'] = api_key
    
    with open(CONFIG_FILE, 'w') as f:
        json.dump(config, f, indent=2)
    
    # Set permissions to restrict access (optional)
    try:
        os.chmod(CONFIG_FILE, 0o600)  # Only the owner can read/write
    except:
        pass


def load_api_key() -> str:
    """
    Load the API key from the local configuration file.
    
    Returns:
        The stored API key or an empty string if not found
    """
    if not os.path.exists(CONFIG_FILE):
        return ""
    
    try:
        with open(CONFIG_FILE, 'r') as f:
            config = json.load(f)
            return config.get('serp_api_key', "")
    except:
        return ""


def process_pdf_files(pdf_files: List[str], output_dir: str, extract_only: bool = False) -> str:
    
    print(f"Processing {len(pdf_files)} PDF files...")
    
    # Create batch processor
    batch_processor = BatchProcessor(output_base_dir=output_dir)
    
    # Process PDFs
    organized_solutions = batch_processor.process_pdfs(pdf_files)
    
    print(f"\nExtracted code organized by solution number in {os.path.join(output_dir, 'organized')}/")
    return os.path.join(output_dir, "organized")


def analyze_similarity(solutions_dir, language="cpp", difficulty="medium", use_ast=True):
   
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


def analyze_ai_plagiarism(solutions_dir, language="cpp"):
  
    if not AI_DETECTOR_AVAILABLE:
        print("AI plagiarism detection skipped - module not available")
        return {}
    
    results = {}
    solution_dirs = []
    
    if os.path.exists(solutions_dir):
        solution_dirs = [d for d in os.listdir(solutions_dir) if d.startswith("solution")]
        solution_dirs.sort()
    else:
        print(f"No organized solutions found at {solutions_dir}.")
        return results
    
    print("\n" + "=" * 50)
    print("AI PLAGIARISM DETECTION")
    print("=" * 50)
    
    # Initialize AI detector
    detector = CppAIDetector()
    
    # Create results directory
    ai_reports_dir = os.path.join(os.path.dirname(solutions_dir), "ai_reports")
    os.makedirs(ai_reports_dir, exist_ok=True)
    
    # Analyze each solution
    for solution_dir in solution_dirs:
        solution_path = os.path.join(solutions_dir, solution_dir)
        solution_results = {}
        
        # Get all .txt files in the solution directory
        submission_files = [f for f in os.listdir(solution_path) if f.endswith('.txt')]
        
        print(f"\nAnalyzing {solution_dir} for AI-generated code ({len(submission_files)} submissions)...")
        
        # Analyze each submission
        for file in submission_files:
            file_path = os.path.join(solution_path, file)
            
            print(f"  Analyzing {file}...")
            
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    code = f.read()
                
                # Analyze the code
                is_ai, detailed_results = detector.is_ai_generated(code)
                
                # Calculate human-readable likelihood
                score = detailed_results.get('overall_score', 0)
                if score < 0.25:
                    likelihood = "5%"
                elif score < 0.30:
                    likelihood = "20%"
                elif score < 0.35:
                    likelihood = "40%"
                elif score < 0.40:
                    likelihood = "60%"
                elif score < 0.45:
                    likelihood = "80%"
                else:
                    likelihood = "95%"
                
                # Determine risk level
                if score < 0.25:
                    risk_level = "MINIMAL RISK"
                elif score < 0.35:
                    risk_level = "MEDIUM RISK"
                else:
                    risk_level = "HIGH RISK"
                
                # Create result object
                result = {
                    "file": file,
                    "is_ai_generated": is_ai,
                    "technical_score": score * 100,  # Convert to percentage
                    "ai_likelihood": likelihood,
                    "risk_level": risk_level,
                    "detailed_results": detailed_results
                }
                
                # Get top indicators
                indicators = sorted(
                    [(k, v) for k, v in detailed_results.items() if k != 'overall_score'], 
                    key=lambda x: x[1], 
                    reverse=True
                )
                result["top_indicators"] = [{"name": k, "value": v} for k, v in indicators[:5] if v > 0.05]
                
                # Add to solution results
                solution_results[file] = result
                
                # Print summary
                print(f"    Result: {'AI-GENERATED' if is_ai else 'HUMAN-WRITTEN'}")
                print(f"    Technical Score: {score * 100:.2f}%")
                print(f"    AI Likelihood: {likelihood}")
                print(f"    Risk Level: {risk_level}")
                
            except Exception as e:
                print(f"    Error analyzing {file}: {str(e)}")
                solution_results[file] = {"error": str(e)}
        
        # Save results to file
        report_file = os.path.join(ai_reports_dir, f"{solution_dir}_ai_report.json")
        with open(report_file, 'w') as f:
            json.dump(solution_results, f, indent=2)
        
        print(f"  AI detection report saved to {report_file}")
        
        # Add to overall results
        results[solution_dir] = solution_results
    
    return results


def analyze_web_plagiarism(solutions_dir, api_key, language="cpp", threshold=0.3):
    # Skip web plagiarism detection for now
    print("Web plagiarism detection skipped - disabled by user request")
    return {}
    
    # The following code is kept but will not execute
    if not WEB_CHECKER_AVAILABLE:
        print("Web plagiarism detection skipped - module not available")
        return {}
    
    if not api_key:
        print("Web plagiarism detection skipped - API key not provided")
        return {}
    
    results = {}
    solution_dirs = []
    
    if os.path.exists(solutions_dir):
        solution_dirs = [d for d in os.listdir(solutions_dir) if d.startswith("solution")]
        solution_dirs.sort()
    else:
        print(f"No organized solutions found at {solutions_dir}.")
        return results
    
    print("\n" + "=" * 50)
    print("WEB PLAGIARISM DETECTION")
    print("=" * 50)
    
    # Initialize web plagiarism checker
    checker = WebPlagiarismChecker(api_key, threshold)
    
    # Create results directory
    plagiarism_reports_dir = os.path.join(os.path.dirname(solutions_dir), "plagiarism_reports")
    os.makedirs(plagiarism_reports_dir, exist_ok=True)
    
    # Analyze each solution
    for solution_dir in solution_dirs:
        solution_path = os.path.join(solutions_dir, solution_dir)
        solution_results = {}
        
        # Get all .txt files in the solution directory
        submission_files = [f for f in os.listdir(solution_path) if f.endswith('.txt')]
        
        print(f"\nChecking {solution_dir} for web plagiarism ({len(submission_files)} submissions)...")
        
        # Analyze each submission
        for file in submission_files:
            file_path = os.path.join(solution_path, file)
            
            print(f"  Checking {file}...")
            
            try:
                # Check for plagiarism
                result = checker.check_plagiarism(file_path, language)
                solution_results[file] = result
                
                # Print summary
                if result["plagiarism_detected"]:
                    print(f"    Plagiarism detected! {len(result['plagiarism_results'])} matches found.")
                    for match in result["plagiarism_results"]:  # Shows only the top 5 matches (already limited in WebPlagiarismChecker)
                        print(f"      - {match['link']} (similarity: {match['similarity_score']:.2f})")
                else:
                    print(f"    No plagiarism detected.")
                
            except Exception as e:
                print(f"    Error checking {file}: {str(e)}")
                solution_results[file] = {"error": str(e)}
        
        # Save combined report
        report_file = os.path.join(plagiarism_reports_dir, f"{solution_dir}_web_report.json")
        with open(report_file, 'w') as f:
            json.dump(solution_results, f, indent=2)
        
        print(f"  Web plagiarism report saved to {report_file}")
        
        # Add to overall results
        results[solution_dir] = solution_results
    
    return results


def generate_comprehensive_report(similarity_results, ai_results, web_results):
   
    report = {
        "similarity_analysis": similarity_results,
        "ai_detection": ai_results,
        "web_plagiarism": web_results
    }
    
    return report


def main():
    parser = argparse.ArgumentParser(description="Comprehensive Code Plagiarism Detection Tool")
    
    # Main parameters
    parser.add_argument("--output", "-o", default="final_batch_output", help="Output directory")
    parser.add_argument("--extract-only", action="store_true", help="Only extract code, don't analyze")
    parser.add_argument("--language", "-l", default="cpp", help="Programming language of submissions")
    parser.add_argument("--difficulty", "-d", default="medium", choices=["easy", "medium", "difficult"], 
                        help="Assignment difficulty level")
    parser.add_argument("--no-ast", action="store_true", help="Disable AST analysis (use only TF-IDF)")
    
    # Additional analysis options
    parser.add_argument("--check-ai", action="store_true", help="Enable AI-generated code detection")
    parser.add_argument("--check-web", action="store_true", help="Enable web plagiarism detection")
    parser.add_argument("--api-key", help="SerpAPI key for web plagiarism detection")
    parser.add_argument("--threshold", type=float, default=0.3, 
                        help="Similarity threshold for web plagiarism detection")
    
    # Positional arguments for PDF files
    parser.add_argument("pdf_files", nargs='+', help="PDF files to process")
    
    args = parser.parse_args()
    
    # Handle API key
    api_key = args.api_key
    
    # If API key is provided, save it for future use
    if api_key:
        save_api_key(api_key)
        print("SerpAPI key has been saved for future use. You won't need to provide it again.")
    elif args.check_web:
        # If no API key provided but web checking is enabled, try to load from config
        stored_key = load_api_key()
        if stored_key:
            api_key = stored_key
            print("Using stored SerpAPI key.")
        else:
            print("Warning: No SerpAPI key provided and none found in configuration.")
            print("Web plagiarism detection will be disabled.")
            args.check_web = False
    
    # Create output directory if it doesn't exist
    os.makedirs(args.output, exist_ok=True)
    
    # Process PDF files
    organized_dir = process_pdf_files(args.pdf_files, args.output, args.extract_only)
    
    # If extract-only, stop here
    if args.extract_only:
        return
        

if __name__ == "__main__":
    main() 