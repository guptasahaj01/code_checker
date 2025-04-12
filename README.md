# WARDEN+ CODE PLAGARISM DETECTOR 

A comprehensive tool for detecting multiple forms of code plagiarism in student assignments.

![Code Plagiarism Detector](https://img.shields.io/badge/Code-Plagiarism%20Detector-blue)
![Version](https://img.shields.io/badge/Version-1.0.0-green)
![License](https://img.shields.io/badge/License-MIT-yellow)

## Overview

The Code Plagiarism Detection System is a powerful tool designed to identify three types of plagiarism in programming assignments:

1. **Student-to-Student Similarity**: Detects similar code between student submissions
2. **AI-Generated Code Detection**: Identifies code likely written by AI tools like ChatGPT
3. **Web Plagiarism Detection**: Finds code copied from online sources

The system features a user-friendly web interface that allows instructors to upload multiple PDF assignments, analyze them using sophisticated detection algorithms, and view detailed results with highlighted similarities.

## Table of Contents

- [Features](#features)
- [System Architecture](#system-architecture)
- [Installation](#installation)
- [Usage](#usage)
- [Detection Methods](#detection-methods)
- [Configuration](#configuration)
- [API Reference](#api-reference)
- [Development](#development)
- [License](#license)

## Features

- **Multi-format Detection**: Identifies plagiarism from peers, AI tools, and web sources
- **PDF Processing**: Extracts code directly from PDF assignment submissions
- **Adjustable Sensitivity**: Select difficulty level (Easy, Medium, Hard) to adjust detection thresholds
- **Interactive UI**: Modern web interface for uploading files and viewing results
- **Multi-language Support**: Primary support for C++ with extensibility for other languages
- **Detailed Reports**: Comprehensive reports showing similarities with confidence levels
- **Web Search Integration**: Uses SerpAPI to search online code repositories
- **Advanced Algorithms**: Combines multiple detection methods including TF-IDF and AST analysis

## System Architecture

The system follows a modular architecture with three main components:

```
code_checker/
├── Frontend/                      # Web interface
│   ├── css/                       # Styling
│   ├── js/                        # JavaScript
│   ├── index.html                 # Upload page
│   └── results.html               # Results display page
│
├── Processing/                    # Backend processing modules
│   ├── core_backend/              # Main backend logic
│   ├── code_extraction/           # Code extraction from PDFs
│   ├── similarity_analysis/       # Code similarity detection
│   ├── AI_plagarism_detector/     # Detects AI-generated code
│   └── web_plagiarism_detector/   # Web plagiarism detection
│
├── plagiarism_cache/              # Cache for web search results
└── plagiarism_reports/            # Storage for report outputs
```

## Installation

### Prerequisites

- Python 3.8+
- Node.js 14+ (for development)
- SerpAPI key (for web plagiarism detection)

### Setup

1. Clone the repository:
   ```bash
   git clone https://github.com/yourusername/code_checker.git
   cd code_checker
   ```

2. Create and activate a virtual environment:
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

4. Configure SerpAPI key:
   ```bash
   echo '{"serp_api_key": "YOUR_API_KEY"}' > Processing/core_backend/config.json
   ```

## Usage

### Running the Application

1. Start the server:
   ```bash
   cd Processing/core_backend
   python api_server.py
   ```

2. Access the web interface:
   Open your browser and navigate to `http://localhost:5003`

### Upload and Analysis

1. **Upload Assignments**:
   - Drag and drop PDF files or use the file browser
   - Up to 50 files can be processed in a batch

2. **Select Difficulty Level**:
   - Easy: Lower threshold, fewer false positives
   - Medium: Balanced detection
   - Hard: Stricter detection, may include more false positives

3. **Process Files**:
   - Click "Process Files" to start analysis
   - Wait for processing to complete

4. **View Results**:
   - Navigate through the three tabs:
     - Student Similarity
     - AI Detection
     - Web Plagiarism
   - Review detailed matches and similarity scores

## Detection Methods

### Student-to-Student Similarity

The system uses multiple techniques to identify similar code between student submissions:

1. **TF-IDF Analysis**: Text-based comparison using Term Frequency-Inverse Document Frequency
2. **AST Analysis**: Structure-based comparison using Abstract Syntax Trees
3. **Combined Scoring**: Results are combined for higher accuracy

Results are categorized as:
- **High Confidence Matches**: Very likely plagiarism
- **Pairs Needing Review**: Potential plagiarism requiring manual review

### AI-Generated Code Detection

Identifies AI-written code using machine learning techniques:

1. **Feature Extraction**: Analyzes code for patterns typical of AI systems
2. **ML Classification**: Uses trained models to calculate likelihood scores
3. **Risk Assessment**: Assigns risk levels (Minimal, Medium, High)

### Web Plagiarism Detection

Detects code copied from online sources:

1. **Intelligent Query Generation**: Creates search queries based on code patterns
2. **Web Search**: Uses SerpAPI to search multiple programming sites
3. **Content Extraction**: Fetches and extracts code from search results
4. **Similarity Comparison**: Compares student code with web content
5. **Threshold-based Detection**: Flags matches above configurable thresholds

## Configuration

### API Keys

Store your SerpAPI key in `Processing/core_backend/config.json`:

```json
{
  "serp_api_key": "YOUR_API_KEY"
}
```

### Detection Thresholds

Adjust detection thresholds in `Processing/similarity_analysis/similarity_analyzer.py`:

```python
def get_threshold(difficulty):
    if difficulty == "easy":
        return 0.7  # 70% similarity required
    elif difficulty == "medium":
        return 0.5  # 50% similarity required
    else:  # difficult
        return 0.3  # 30% similarity required
```

## API Reference

### Endpoints

- `GET /api/health`: Health check endpoint
- `POST /api/plagiarism/process`: Process uploaded files
- `GET /api/results/{session_id}`: Retrieve analysis results

### Request Format

```http
POST /api/plagiarism/process
Content-Type: multipart/form-data

files: [binary]
difficulty: "easy"|"medium"|"hard"
```

### Response Format

```json
{
  "session_id": "session_12345abcde",
  "status": "success",
  "message": "Files processed successfully"
}
```

## Development

### Project Structure

- **Frontend**: HTML/CSS/JavaScript for user interface
- **API Server**: Flask-based server for handling requests
- **Processing Modules**: Python modules for plagiarism detection

### Adding Support for New Languages

1. Update language detection in `code_extraction/complete_solution_extractor.py`
2. Add language-specific patterns in `similarity_analysis/ast_analyzer.py`
3. Configure language in `AI_plagarism_detector/chaicheck.py`

### Running Tests

```bash
pytest tests/
```

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Acknowledgments

- SerpAPI for web search capabilities
- scikit-learn and nltk for NLP and ML functionality
- PDF processing libraries for document analysis

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

1. Fork the repository
2. Create your feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add some amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

---


