#!/usr/bin/env python3
"""
API Server for Plagiarism Detection System

This Flask API server connects the frontend to the backend plagiarism detection system.
It provides endpoints for processing PDF files and retrieving analysis results.
"""

import os
import json
import uuid
import logging
from pathlib import Path
from typing import List, Dict, Any
from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
from werkzeug.utils import secure_filename
from datetime import datetime


# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Import the main module functions
try:
    from main import (
        process_pdf_files,
        analyze_similarity,
        analyze_ai_plagiarism,
        analyze_web_plagiarism,
        generate_comprehensive_report,
        load_api_key
    )
    logger.info("Successfully imported functions from main module")
    USING_FALLBACK = False
except ImportError as e:
    logger.error(f"Error importing from main module: {e}")
    logger.warning("Using fallback functions for testing")
    USING_FALLBACK = True

# Configure the Flask application
app = Flask(__name__, static_folder='../../Frontend', template_folder='../../frontend')
CORS(app)  # Enable CORS for all origins

# Configure upload parameters
SESSIONS_FOLDER = os.path.join(os.path.dirname(__file__), 'sessions')
ALLOWED_EXTENSIONS = {'pdf'}
MAX_CONTENT_LENGTH = 50 * 1024 * 1024  # 50MB limit

# Ensure directory exist

os.makedirs(SESSIONS_FOLDER, exist_ok=True)

# Set upload limit
app.config['MAX_CONTENT_LENGTH'] = MAX_CONTENT_LENGTH

# Helper functions
def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

# Fallback functions for testing (when main module is not available)
class FallbackFunctions:
    """Provides fallback implementations of key functions for testing."""
    
    @staticmethod
    def process_pdf_files(pdf_files, output_dir, extract_only=False):
        """Fallback implementation for processing PDF files."""
        logger.info(f"[FALLBACK] Processing {len(pdf_files)} PDF files")
        
        # Create output directory
        os.makedirs(output_dir, exist_ok=True)
        solutions_dir = os.path.join(output_dir, "solutions")
        os.makedirs(solutions_dir, exist_ok=True)
        
        # Create simulated solution structure
        for i, pdf_file in enumerate(pdf_files):
            base_name = os.path.basename(pdf_file)
            txt_name = base_name.rsplit('.', 1)[0] + '.txt'
            
            # Create a text file with sample content
            with open(os.path.join(solutions_dir, txt_name), 'w') as f:
                f.write(f"// Sample extracted code from {base_name}\n")
                f.write("int main() {\n")
                f.write("    printf(\"Hello, World!\");\n")
                f.write("    return 0;\n")
                f.write("}\n")
        
        return solutions_dir
    
    @staticmethod
    def analyze_similarity(solutions_dir, language="cpp", difficulty="medium", use_ast=True):
        """Fallback implementation for similarity analysis."""
        logger.info(f"[FALLBACK] Analyzing similarity in {solutions_dir}")
        
        # Find all text files in the solutions directory
        text_files = []
        if os.path.exists(solutions_dir):
            text_files = [f for f in os.listdir(solutions_dir) if f.endswith('.txt')]
        
        # Create dummy similarity groups
        similarity_groups = []
        if len(text_files) >= 2:
            # Group all files with medium similarity
            similarity_groups.append({
                "similarity": 0.655,
                "files": text_files
            })
            
            # If we have enough files, create a second group with high similarity
            if len(text_files) >= 3:
                similarity_groups.append({
                    "similarity": 0.853,
                    "files": text_files[:2]  # Just the first two files
                })
        
        return similarity_groups
    
    @staticmethod
    def analyze_ai_plagiarism(solutions_dir, language="cpp"):
        """Fallback implementation for AI plagiarism detection."""
        logger.info(f"[FALLBACK] Analyzing AI plagiarism in {solutions_dir}")
        
        # Find all text files in the solutions directory
        results = {}
        if os.path.exists(solutions_dir):
            text_files = [f for f in os.listdir(solutions_dir) if f.endswith('.txt')]
            
            for i, filename in enumerate(text_files):
                # Assign varying AI scores based on file index
                if i % 3 == 0:
                    score = 0.82
                    likelihood = "High"
                elif i % 3 == 1:
                    score = 0.45
                    likelihood = "Medium"
                else:
                    score = 0.15
                    likelihood = "Low"
                
                # Convert filename from .txt to .pdf for consistency with frontend
                pdf_filename = filename.replace('.txt', '.pdf')
                results[pdf_filename] = {
                    "overall_score": score,
                    "likelihood": likelihood
                }
        
        return results
    
    @staticmethod
    def analyze_web_plagiarism(solutions_dir, api_key=None, language="cpp", threshold=0.3):
        """Fallback implementation for web plagiarism detection."""
        logger.info(f"[FALLBACK] Analyzing web plagiarism in {solutions_dir}")
        
        # Find all text files in the solutions directory
        results = {}
        if os.path.exists(solutions_dir):
            text_files = [f for f in os.listdir(solutions_dir) if f.endswith('.txt')]
            
            for i, filename in enumerate(text_files):
                # Create different web match patterns based on file index
                pdf_filename = filename.replace('.txt', '.pdf')
                
                if i % 3 == 0:
                    # Multiple matches
                    results[pdf_filename] = [
                        {
                            "url": "https://github.com/example/algorithms/tree/master/examples", 
                            "title": "Example Algorithm Repository",
                            "similarity": 0.75
                        },
                        {
                            "url": "https://stackoverflow.com/questions/12345/optimizing-algorithms", 
                            "title": "Stack Overflow - Optimizing Algorithms",
                            "similarity": 0.62
                        },
                        {
                            "url": "https://www.geeksforgeeks.org/standard-algorithms/", 
                            "title": "GeeksforGeeks - Standard Algorithms",
                            "similarity": 0.58
                        }
                    ]
                elif i % 3 == 1:
                    # Single match
                    results[pdf_filename] = [
                        {
                            "url": "https://github.com/example/student-code/blob/main/sample.cpp", 
                            "title": "Student Code Repository",
                            "similarity": 0.81
                        }
                    ]
                else:
                    # No matches
                    results[pdf_filename] = []
            
        return results
    
    @staticmethod
    def load_api_key():
        """Fallback implementation for loading API key."""
        return "dummy_api_key_for_testing"


# API endpoints
@app.route('/api/health', methods=['GET'])
def health_check():
    """Health check endpoint to verify if the server is running."""
    return jsonify({
        "status": "ok",
        "backend_mode": "fallback" if USING_FALLBACK else "normal"
    })

@app.route('/api/plagiarism/check', methods=['GET'])
def check_plagiarism_service():
    """Simple check to verify if plagiarism detection service is available."""
    return jsonify({
        "status": "ok",
        "backend_mode": "fallback" if USING_FALLBACK else "normal"
    })

@app.route('/api/plagiarism/process', methods=['POST'])
def process_files():
    """
    Process PDF files to detect plagiarism.
    
    Expects multipart/form-data with:
    - files: Multiple PDF files (required)
    - difficulty: The difficulty level (easy, medium, hard)
    - session_id: Optional session ID to track results
    """
    # Check if files were uploaded
    if 'files' not in request.files:
        return jsonify({"status": "error", "message": "No files provided"}), 400
    
    # Get the uploaded files
    files = request.files.getlist('files')
    if not files or all(not file.filename for file in files):
        return jsonify({"status": "error", "message": "No selected files"}), 400
    
    # Validate file types
    invalid_files = [file.filename for file in files if not allowed_file(file.filename)]
    if invalid_files:
        return jsonify({
            "status": "error", 
            "message": f"Invalid file types: {', '.join(invalid_files)}. Only PDF files are allowed."
        }), 400
    
    # Get processing parameters
    difficulty = request.form.get('difficulty', 'medium')
    if difficulty not in ['easy', 'medium', 'hard']:
        difficulty = 'medium'  # Default to medium if invalid
    
    # Generate a session ID if not provided
    session_id = request.form.get('session_id')
    if not session_id:
        session_id = f"session_{uuid.uuid4().hex}"
    
    # Create session directory
    session_dir = os.path.join(SESSIONS_FOLDER, session_id)
    os.makedirs(session_dir, exist_ok=True)
    
    # Create directories for this processing task
    upload_dir = os.path.join(session_dir, "uploads")
    results_dir = os.path.join(session_dir, "results")
    os.makedirs(upload_dir, exist_ok=True)
    os.makedirs(results_dir, exist_ok=True)
    
    # Save uploaded files
    saved_files = []
    for file in files:
        if file and allowed_file(file.filename):
            filename = secure_filename(file.filename)
            file_path = os.path.join(upload_dir, filename)
            file.save(file_path)
            saved_files.append(file_path)
    
    # Save metadata
    metadata = {
        "session_id": session_id,
        "difficulty": difficulty,
        "file_count": len(saved_files),
        "timestamp": datetime.fromtimestamp(os.path.getctime(session_dir)).isoformat(),
        "status": "processing"
    }
    
    with open(os.path.join(session_dir, "metadata.json"), "w") as f:
        json.dump(metadata, f, indent=2)
    
    # Log the processing request
    logger.info(f"Processing request: session={session_id}, files={len(saved_files)}, difficulty={difficulty}")
    
    try:
        # Process files
        if USING_FALLBACK:
            solutions_dir = FallbackFunctions.process_pdf_files(saved_files, results_dir)
        else:
            solutions_dir = process_pdf_files(saved_files, results_dir)
        
        
        logger.info(f"Files processed, solutions in: {solutions_dir}")
        
        # Run similarity analysis
        if USING_FALLBACK:
            similarity_results = FallbackFunctions.analyze_similarity(solutions_dir, difficulty=difficulty)
        else:
            similarity_results = analyze_similarity(solutions_dir, difficulty=difficulty)
        
        logger.info(f"Similarity analysis completed")
        
        # Run AI plagiarism detection
        try:
            if USING_FALLBACK:
                ai_results = FallbackFunctions.analyze_ai_plagiarism(solutions_dir)
            else:
                ai_results = analyze_ai_plagiarism(solutions_dir)
            logger.info(f"AI plagiarism detection completed")
        except Exception as e:
            logger.error(f"Error in AI plagiarism detection: {e}")
            ai_results = {}
        
        # Run web plagiarism detection
        try:
            if USING_FALLBACK:
                api_key = FallbackFunctions.load_api_key()
                web_results = FallbackFunctions.analyze_web_plagiarism(solutions_dir, api_key=api_key)
            else:
                api_key = load_api_key()
                web_results = analyze_web_plagiarism(solutions_dir, api_key=api_key)
            logger.info(f"Web plagiarism detection completed")
        except Exception as e:
            logger.error(f"Error in web plagiarism detection: {e}")
            web_results = {}
        
        # Generate comprehensive report
        comprehensive_analysis=generate_comprehensive_report(similarity_results=similarity_results,ai_results=ai_results,web_results=web_results)
        
        # Update metadata status
        metadata["status"] = "completed"
        with open(os.path.join(session_dir, "metadata.json"), "w") as f:
            json.dump(metadata, f, indent=2)
        
        # Save results for frontend
        with open(os.path.join(session_dir, "comprehensive_analysis.json"), "w") as f:
            json.dump(comprehensive_analysis, f, indent=2)
        
        # Return success response with session ID
        return jsonify({
            "status": "success",
            "message": "Files processed successfully",
            "session_id": session_id
        })
        
    except Exception as e:
        logger.error(f"Error processing files: {e}")
        
        # Update metadata to reflect error
        metadata["status"] = "error"
        metadata["error"] = str(e)
        with open(os.path.join(session_dir, "metadata.json"), "w") as f:
            json.dump(metadata, f, indent=2)
        
        return jsonify({
            "status": "error",
            "message": f"Error processing files: {str(e)}",
            "session_id": session_id
        }), 500

@app.route('/api/results/<session_id>', methods=['GET'])
def get_results(session_id):
    """Get results for a specific processing session."""
    session_dir = os.path.join(SESSIONS_FOLDER, session_id)
    
    # Check if session exists
    if not os.path.exists(session_dir):
        return jsonify({
            "status": "error",
            "message": "Session not found"
        }), 404
    
    # Check for results
    results_file = os.path.join(session_dir, "comprehensive_analysis.json")
    if os.path.exists(results_file):
        with open(results_file, "r") as f:
            results = json.load(f)
        
    
    # Check metadata for status
    metadata_file = os.path.join(session_dir, "metadata.json")
    if os.path.exists(metadata_file):
        with open(metadata_file, "r") as f:
            metadata = json.load(f)
        
        if metadata.get("status") == "error":
            return jsonify({
                "status": "error",
                "message": metadata.get("error", "An unknown error occurred")
            })
        
        # Still processing
        elif metadata.get("status") == "processing":
            return jsonify({
                "status": "processing",
                "message": "Files are still being processed"
            }), 202
        
        elif metadata.get("status") == "completed":
            return jsonify({
                "status": "completed",
                "message": "Files Analysis completed",
                "results": results,
                "metadata":metadata
            }), 200
       
    
    # Something went wrong
    return jsonify({
        "status": "error",
        "message": "Results not found for this session"
    }), 404

@app.route('/', defaults={'path': 'index.html'})
@app.route('/<path:path>')
def serve_static(path):
    """Serve static files from the frontend directory."""
    return send_from_directory(app.static_folder, path)

# Start the server if run directly
if __name__ == '__main__':
    import argparse
    
    parser = argparse.ArgumentParser(description='Start the plagiarism detection API server')
    parser.add_argument('--port', type=int, default=5003, help='Port to run the server on')
    parser.add_argument('--debug', action='store_true', help='Run in debug mode')
    args = parser.parse_args()
    
    print(f"Starting API server on port {args.port}")
    app.run(port=args.port, debug=True) 