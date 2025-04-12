# Code Plagiarism Detection System

## Introduction

This system detects programming plagiarism by analyzing PDF assignments through three methods:
1. Student-to-student code similarity
2. AI-generated code detection 
3. Web plagiarism identification

This README explains the technical implementation and workflow of each component.

## System Architecture and Workflow

The system follows this operational workflow:

1. User uploads PDF files through the frontend UI
2. Files are received by the Flask API server
3. PDFs are processed and code is extracted
4. Three parallel analysis pipelines run
5. Results are combined into a unified JSON report
6. Frontend fetches and displays the structured results

## Components and Technical Implementation

### Frontend Implementation

#### Upload Mechanism (`index.html`, `app.js`)
The upload interface uses a combination of HTML5 drag-and-drop and traditional file input:

```javascript
// Key parts of the file upload implementation
document.getElementById('uploadArea').addEventListener('drop', handleDrop);
document.getElementById('fileInput').addEventListener('change', handleFileSelect);

function handleFileSelect(e) {
    const files = Array.from(e.target.files).filter(file => file.type === 'application/pdf');
    addFilesToList(files);
}

function processFiles() {
    const formData = new FormData();
    selectedFiles.forEach(file => formData.append('files', file));
    formData.append('difficulty', getSelectedDifficulty());
    
    // AJAX request to process endpoint
    fetch('/api/plagiarism/process', {
        method: 'POST',
        body: formData
    })
    .then(response => response.json())
    .then(data => {
        window.location.href = `results.html?session=${data.session_id}`;
    });
}
```

#### Results Visualization (`results.html`, `results.js`)
The results page fetches data and dynamically populates three tabs:

```javascript
// Key parts of the results handling implementation
async function loadResults(sessionId) {
    const response = await fetch(`/api/results/${sessionId}`);
    const data = await response.json();
    
    populateSummary(data);
    populateSimilarityTab(data.similarity_analysis);
    populateAITab(data.ai_detection);
    populateWebTab(data.web_plagiarism);
}

function populateSimilarityTab(data) {
    // Creates card groups with similarity percentages 
    // and interactive code comparison views
    Object.entries(data).forEach(([solution, results]) => {
        const solutionElement = createSolutionCard(solution, results);
        similarityContainer.appendChild(solutionElement);
    });
}
```

### Backend Server (`api_server.py`)

The Flask server implements RESTful endpoints and manages sessions:

```python
@app.route('/api/plagiarism/process', methods=['POST'])
def process_files():
    # Generate unique session ID
    session_id = f"session_{uuid.uuid4().hex}"
    
    # Create session directories
    session_dir = os.path.join(SESSIONS_FOLDER, session_id)
    uploads_dir = os.path.join(session_dir, "uploads")
    results_dir = os.path.join(session_dir, "results")
    os.makedirs(uploads_dir, exist_ok=True)
    os.makedirs(results_dir, exist_ok=True)
    
    # Process uploaded files
    files = request.files.getlist('files')
    pdf_paths = []
    
    for file in files:
        if file and allowed_file(file.filename):
            filename = secure_filename(file.filename)
            file_path = os.path.join(uploads_dir, filename)
            file.save(file_path)
            pdf_paths.append(file_path)
    
    # Get difficulty level
    difficulty = request.form.get('difficulty', 'medium')
    
    # Process files in the background through orchestration
    # in main.py which coordinates all analysis pipelines
    try:
        # Run PDF processing
        solutions_dir = process_pdf_files(pdf_paths, results_dir)
        
        # Run different analysis methods
        similarity_results = analyze_similarity(solutions_dir, difficulty=difficulty)
        ai_results = analyze_ai_plagiarism(solutions_dir)
        api_key = load_api_key()
        web_results = analyze_web_plagiarism(solutions_dir, api_key=api_key)
        
        # Create comprehensive report
        report = generate_comprehensive_report(
            similarity_results, ai_results, web_results
        )
        
        # Save report
        report_path = os.path.join(session_dir, "comprehensive_analysis.json")
        with open(report_path, 'w') as f:
            json.dump(report, f, indent=2)
            
        return jsonify({
            "session_id": session_id,
            "status": "success",
            "message": "Files processed successfully"
        })
    except Exception as e:
        return jsonify({
            "status": "error",
            "message": str(e)
        }), 500
```

### PDF Processing Implementation (`code_extraction/`)

#### PDF to Text Extraction
The system uses pdfplumber to extract text and then applies regex patterns to identify code blocks:

```python
def extract_code_from_pdf(pdf_path):
    # Open PDF with pdfplumber
    with pdfplumber.open(pdf_path) as pdf:
        all_text = ""
        
        # Extract text from each page
        for page in pdf.pages:
            text = page.extract_text()
            if text:
                all_text += text + "\n"
    
    # Find code blocks using language-specific patterns
    code_blocks = []
    
    # C++ pattern matching
    cpp_patterns = [
        r'#include\s*<[^>]+>.*?;',  # Include statements
        r'int\s+main\s*\([^)]*\)\s*\{.*?\}',  # Main function
        r'class\s+\w+\s*\{.*?\};',  # Class definitions
        r'void\s+\w+\s*\([^)]*\)\s*\{.*?\}',  # Function definitions
    ]
    
    for pattern in cpp_patterns:
        matches = re.findall(pattern, all_text, re.DOTALL)
        code_blocks.extend(matches)
    
    # Group into complete solutions based on proximity and context
    solutions = group_into_solutions(code_blocks)
    return solutions
```

#### Solution Organization (`batch_processor.py`)
The system organizes extracted solutions for comparison:

```python
def organize_solutions(self, all_solutions):
    # Create mapping: solution_num -> {pdf_name: solution_path}
    organized_solutions = {}
    
    for pdf_name, solutions_info in all_solutions.items():
        for solution_info in solutions_info:
            solution_num = solution_info['solution_num']
            
            if solution_num not in organized_solutions:
                organized_solutions[solution_num] = {}
            
            organized_solutions[solution_num][pdf_name] = solution_info['path']
    
    # Create organized directory structure
    for solution_num, pdf_solutions in organized_solutions.items():
        solution_dir = os.path.join(self.organized_dir, f"solution{solution_num}")
        os.makedirs(solution_dir, exist_ok=True)
        
        # Copy solutions to organized directory
        for pdf_name, solution_path in pdf_solutions.items():
            target_path = os.path.join(solution_dir, f"{pdf_name}.txt")
            shutil.copy(solution_path, target_path)
    
    return organized_solutions
```

### Similarity Analysis Implementation

#### TF-IDF Analysis (`tfidf_analyzer.py`)
The system uses scikit-learn's TF-IDF implementation to vectorize code:

```python
def analyze_submissions(self, submissions):
    # Preprocess code (normalize whitespace, remove comments)
    preprocessed = {name: self.preprocess_code(code) for name, code in submissions.items()}
    
    # Create document matrix using TF-IDF vectorization
    vectorizer = TfidfVectorizer(
        analyzer='word',
        token_pattern=r'\b\w+\b',
        ngram_range=(1, 3),  # Use 1-3 word n-grams
        stop_words=self.get_stop_words(self.language)
    )
    
    # Convert submissions to TF-IDF vectors
    submission_names = list(preprocessed.keys())
    submission_texts = [preprocessed[name] for name in submission_names]
    
    # Create TF-IDF matrix
    try:
        tfidf_matrix = vectorizer.fit_transform(submission_texts)
    except ValueError:
        # Handle empty documents
        return {"error": "Empty or invalid documents"}
    
    # Compute cosine similarity between all documents
    similarity_matrix = cosine_similarity(tfidf_matrix)
    
    # Find suspicious pairs based on threshold
    suspicious_pairs = self.find_suspicious_pairs(
        submission_names, similarity_matrix, self.threshold
    )
    
    return {
        "method": "TF-IDF",
        "submission_names": submission_names,
        "similarity_matrix": similarity_matrix.tolist(),
        "suspicious_pairs": suspicious_pairs,
        "threshold": self.threshold
    }
```

#### AST Analysis (`ast_analyzer.py`)
For structural analysis, the system parses code into Abstract Syntax Trees:

```python
def analyze_cpp_code(self, code, filename):
    # Parse C++ code into AST
    try:
        # Use pycparser or custom parser for C++
        ast = self.cpp_parser.parse(code)
        
        # Extract features from AST
        features = {}
        
        # Count variable declarations
        features['variable_count'] = len(self.find_nodes(ast, 'VariableDecl'))
        
        # Count function definitions
        features['function_count'] = len(self.find_nodes(ast, 'FunctionDecl'))
        
        # Extract control flow structures
        features['for_loops'] = len(self.find_nodes(ast, 'ForStmt'))
        features['while_loops'] = len(self.find_nodes(ast, 'WhileStmt'))
        features['if_statements'] = len(self.find_nodes(ast, 'IfStmt'))
        
        # Extract function call sequences
        features['call_sequence'] = self.extract_call_sequence(ast)
        
        # Calculate structural hash based on AST structure
        features['structural_hash'] = self.calculate_structural_hash(ast)
        
        return features
    except Exception as e:
        print(f"Error parsing {filename}: {str(e)}")
        return None
```

### AI Plagiarism Detection (`chaicheck.py`)

The AI detector uses feature extraction and machine learning classification:

```python
def is_ai_generated(self, code):
    # Extract features from the code
    features = self.extract_features(code)
    
    # Calculate individual indicator scores
    indicators = {
        'complexity_score': self.analyze_complexity(features),
        'comment_style_score': self.analyze_comments(features),
        'variable_naming_score': self.analyze_variable_naming(features),
        'error_handling_score': self.analyze_error_handling(features),
        'structure_score': self.analyze_structure(features),
        'idiomaticity_score': self.analyze_idiomaticity(features)
    }
    
    # Calculate overall score (weighted average)
    weights = {
        'complexity_score': 0.2,
        'comment_style_score': 0.15,
        'variable_naming_score': 0.15,
        'error_handling_score': 0.1,
        'structure_score': 0.2,
        'idiomaticity_score': 0.2
    }
    
    overall_score = sum(score * weights[key] for key, score in indicators.items())
    
    # Determine if AI-generated based on threshold
    is_ai = overall_score > 0.65  # 65% threshold
    
    # Include overall score in results
    indicators['overall_score'] = overall_score
    
    return is_ai, indicators
```

### Web Plagiarism Detection (`web_plagiarism_checker.py`)

The web plagiarism detector implements these key functions:

#### Search Query Generation
```python
def generate_search_queries(self, code, language):
    queries = []
    
    # Select appropriate programming site domains
    programming_sites = "site:github.com OR site:stackoverflow.com OR site:geeksforgeeks.org OR site:tutorialspoint.com"
    
    # Extract patterns from the code
    patterns = self.extract_code_patterns(code)
    
    # Add high priority patterns to the queries
    for pattern, priority in patterns[:3]:  # Take top 3 patterns
        if priority > 0.4:  # Only use significant patterns
            query = f"\"{pattern}\" {language} example {programming_sites}"
            queries.append((query, priority))
    
    # Look for class definitions
    class_matches = re.findall(r'class\s+(\w+)', code)
    for class_name in class_matches:
        if class_name.lower() not in {'main', 'test', 'example', 'solution'}:
            query = f"\"{class_name}\" class {language} example {programming_sites}"
            queries.append((query, 0.8))
    
    # Sort by priority and limit to top 3
    queries.sort(key=lambda x: x[1], reverse=True)
    return queries[:3]
```

#### Web Search Integration
```python
def search_code(self, query, priority=0.5):
    results = []
    
    # Check cache first
    cache_key = hashlib.md5(query.encode()).hexdigest()
    cache_file = os.path.join(self.cache_dir, f"{cache_key}.json")
    
    if os.path.exists(cache_file):
        with open(cache_file, 'r', encoding='utf-8') as f:
            return json.load(f)
    
    # Perform search using SerpAPI
    url = "https://serpapi.com/search.json"
    params = {
        "api_key": self.serp_api_key,
        "q": query,
        "engine": "google",
        "num": 10,
        "gl": "us"
    }
    
    response = requests.get(url, params=params, timeout=15)
    if response.status_code == 200:
        data = response.json()
        
        # Process search results
        if "organic_results" in data:
            for result in data["organic_results"]:
                item = {
                    "title": result.get("title", ""),
                    "link": result.get("link", ""),
                    "snippet": result.get("snippet", ""),
                    "query": query,
                    "query_priority": priority,
                    "initial_score": 0.0,
                    "similarity_score": 0.0,
                    "is_plagiarism": False
                }
                results.append(item)
    
    # Save to cache
    with open(cache_file, 'w', encoding='utf-8') as f:
        json.dump(results, f, indent=2)
    
    return results
```

#### Code Similarity Comparison
```python
def compare_code_similarity(self, original_code, web_code, language):
    # Skip empty content
    if not web_code or len(web_code) < 20:
        return 0.0
    
    # Clean and normalize both code samples
    def normalize_for_comparison(code):
        # Remove comments
        code = re.sub(r'//.*?\n|/\*.*?\*/', '', code, flags=re.DOTALL)
        # Normalize whitespace
        code = re.sub(r'[ \t]+', ' ', code)
        # Remove string literals
        code = re.sub(r'".*?"', '""', code)
        return code
    
    orig_normalized = normalize_for_comparison(original_code)
    web_normalized = normalize_for_comparison(web_code)
    
    # Split into lines for structural comparison
    orig_lines = [line.strip() for line in orig_normalized.split('\n') if line.strip()]
    web_lines = [line.strip() for line in web_normalized.split('\n') if line.strip()]
    
    # Calculate line-based similarity
    matching_lines = 0
    for o_line in orig_lines:
        for w_line in web_lines:
            if o_line == w_line:
                matching_lines += 1
                break
    
    line_similarity = matching_lines / max(len(orig_lines), len(web_lines))
    
    # Pattern-based similarity (extract and compare function signatures, etc.)
    pattern_similarity = self.calculate_pattern_similarity(orig_lines, web_lines)
    
    # Token-based similarity
    token_similarity = self.calculate_token_similarity(orig_normalized, web_normalized)
    
    # Weighted final similarity
    final_similarity = (0.4 * line_similarity) + (0.4 * pattern_similarity) + (0.2 * token_similarity)
    
    return min(final_similarity, 1.0)  # Cap at 1.0
```

## Data Flow Details

### Session Management

The system uses session-based storage with a unique UUID for each processing run:

```
sessions/
└── session_[uuid]/
    ├── uploads/              # Original PDF files
    ├── results/              # Analysis outputs
    │   ├── raw/              # Raw extracted code
    │   ├── organized/        # Organized by solution number
    │   ├── ai_reports/       # AI detection reports
    │   └── plagiarism_reports/ # Web plagiarism reports
    └── comprehensive_analysis.json  # Combined results
```

### Result Structure

The comprehensive result JSON format:

```json
{
  "similarity_analysis": {
    "solution1": {
      "detection_methods": ["TF-IDF", "AST"],
      "all_suspicious_pairs": [
        [["student1.txt", "student2.txt"], 0.85]
      ],
      "high_confidence_pairs": [
        [["student1.txt", "student2.txt"], 0.85]
      ],
      "needs_review_pairs": []
    }
  },
  "ai_detection": {
    "solution1": {
      "student1.txt": {
        "is_ai_generated": false,
        "technical_score": 28.5,
        "ai_likelihood": "20%",
        "risk_level": "MEDIUM RISK"
      }
    }
  },
  "web_plagiarism": {
    "solution1": {
      "student1.txt": {
        "plagiarism_detected": false,
        "matches": []
      }
    }
  }
}
```

## Installation and Configuration

### Dependencies
```
Flask==2.0.1
pdfplumber==0.7.6
scikit-learn==1.0.2
nltk==3.6.5
beautifulsoup4==4.10.0
requests==2.28.1
```

### Setup Steps
1. Clone the repository
2. Install dependencies: `pip install -r requirements.txt`
3. Download NLTK data: 
   ```python
   import nltk
   nltk.download('punkt')
   nltk.download('stopwords')
   ```
4. Configure SerpAPI key:
   ```bash
   echo '{"serp_api_key": "YOUR_API_KEY"}' > Processing/core_backend/config.json
   ```
5. Start the server:
   ```bash
   cd Processing/core_backend
   python api_server.py
   ```
6. Access the UI at http://localhost:5003

## Customization

### Adding Support for New Languages
To add support for a new language (e.g., Python):

1. Add extraction patterns in `complete_solution_extractor.py`:
   ```python
   elif language == 'python':
       patterns = [
           r'def\s+\w+\s*\([^)]*\)\s*:.*?(?=\n\S|\Z)',  # Python function
           r'class\s+\w+.*?(?=\n\S|\Z)'  # Python class
       ]
   ```

2. Update preprocessing in `tfidf_analyzer.py`:
   ```python
   def get_stop_words(self, language):
       if language == 'python':
           return ['def', 'class', 'import', 'from', 'as', 'if', 'else', 'for', 'while']
   ```

3. Add language parsing in `ast_analyzer.py`

## Troubleshooting

### Common Issues

#### PDF Extraction Issues
If code extraction fails:
- Check PDF text extraction: `pdfplumber` requires text-based PDFs, not scanned images
- Try the `--debug` flag to see extraction details: `python main.py --debug file.pdf`

#### SerpAPI Rate Limiting
If web detection stops working:
- Check for rate limit errors in logs
- Implement request throttling in `web_plagiarism_checker.py`:
  ```python
  import time
  # Add delay between requests
  time.sleep(1.0)  # 1 second delay
  ```

## License
MIT License
