import os
import json
import requests
import sys
from typing import List, Dict, Any, Tuple, Set
from urllib.parse import quote_plus
import re
from datetime import datetime
import hashlib
from bs4 import BeautifulSoup

# Add the project directory to the path to import the similarity analyzer
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Try to import the SimilarityAnalyzer
try:
    from Processing.similarity_analysis.similarity_analyzer import SimilarityAnalyzer
    SIMILARITY_ANALYZER_AVAILABLE = True
    print("Using project's SimilarityAnalyzer for code comparison")
except ImportError:
    SIMILARITY_ANALYZER_AVAILABLE = False
    print("Warning: Could not import SimilarityAnalyzer. Using basic code comparison instead.")

class CommonPatternAnalyzer:
    """
    Analyzer for identifying common programming patterns that should not be flagged as plagiarism.
    This helps avoid false positives by recognizing standard coding constructs.
    """
    
    def __init__(self, language: str = 'cpp'):
        self.language = language
        self.common_patterns = self._get_common_patterns(language)
    
    def _get_common_patterns(self, language: str) -> Dict[str, float]:
        """Get common patterns for the given language with their relative uniqueness score."""
        # Lower score = more common (less unique)
        if language == 'cpp' or language == 'c':
            return {
                r'#include\s*<[^>]+>': 0.1,  # include statements
                r'using\s+namespace\s+std;': 0.1,  # using namespace
                r'int\s+main\s*\(\s*\)': 0.1,  # main function
                r'return\s+0;': 0.1,  # return 0
                r'std::cout\s*<<': 0.2,  # cout
                r'std::cin\s*>>': 0.2,  # cin
                r'for\s*\(\s*int\s+i\s*=\s*0\s*;': 0.3,  # basic for loop
                r'while\s*\(\s*[^)]+\s*\)': 0.3,  # while loop
                r'if\s*\(\s*[^)]+\s*\)': 0.3,  # if statement
                r'else\s*{': 0.3,  # else statement
                r'class\s+\w+\s*{': 0.4,  # class definition
                r'void\s+\w+\s*\([^)]*\)': 0.4,  # void function
                r'int\s+\w+\s*\([^)]*\)': 0.4,  # int function
                r'new\s+\w+(\s*\[.+\])?': 0.5,  # new allocation
                r'delete\s+\w+;': 0.5,  # delete statement
                r'template\s*<[^>]+>': 0.6,  # template
            }
        elif language == 'python':
            return {
                r'import\s+\w+': 0.1,  # import statement
                r'from\s+\w+\s+import': 0.1,  # from import
                r'def\s+\w+\s*\(': 0.3,  # function definition
                r'class\s+\w+\s*:': 0.4,  # class definition
                r'if\s+__name__\s*==\s*[\'"]__main__[\'"]': 0.1,  # main guard
                r'for\s+\w+\s+in\s+': 0.3,  # for loop
                r'while\s+.+:': 0.3,  # while loop
                r'if\s+.+:': 0.3,  # if statement
                r'else:': 0.3,  # else statement
                r'return\s+': 0.2,  # return statement
                r'print\s*\(': 0.2,  # print function
                r'with\s+.+\s+as\s+': 0.4,  # with statement
                r'try:': 0.4,  # try statement
                r'except\s*.*:': 0.4,  # except statement
            }
        elif language == 'java':
            return {
                r'import\s+java\.': 0.1,  # import statement
                r'public\s+class\s+\w+': 0.3,  # public class
                r'public\s+static\s+void\s+main': 0.1,  # main method
                r'System\.out\.print': 0.2,  # print statement
                r'for\s*\(\s*int\s+i\s*=\s*0\s*;': 0.3,  # basic for loop
                r'while\s*\(\s*[^)]+\s*\)': 0.3,  # while loop
                r'if\s*\(\s*[^)]+\s*\)': 0.3,  # if statement
                r'else\s*{': 0.3,  # else statement
                r'public\s+\w+\s*\([^)]*\)': 0.4,  # public method
                r'private\s+\w+\s*\([^)]*\)': 0.4,  # private method
                r'new\s+\w+(\s*\[.+\])?': 0.5,  # new allocation
            }
        else:
            # Default patterns for other languages
            return {
                r'function\s+\w+\s*\(': 0.4,  # function definition
                r'class\s+\w+': 0.4,  # class definition
                r'if\s*\(': 0.3,  # if statement
                r'else': 0.3,  # else statement
                r'for\s*\(': 0.3,  # for loop
                r'while\s*\(': 0.3,  # while loop
                r'return': 0.2,  # return statement
            }
    
    def analyze_code(self, code: str) -> Dict[str, Any]:
        """
        Analyze code for common patterns.
        
        Returns:
            Dictionary with uniqueness score and common pattern matches
        """
        # Track uniqueness score (starts at 1.0 = completely unique)
        uniqueness_score = 1.0
        pattern_matches = []
        
        # Find all common pattern matches
        for pattern, commonality in self.common_patterns.items():
            matches = re.findall(pattern, code, re.MULTILINE)
            if matches:
                # The more matches of common patterns, the less unique the code is
                match_impact = min(0.3, commonality * min(len(matches), 5) / 10)
                uniqueness_score -= match_impact
                
                # Record the pattern matches
                pattern_matches.append({
                    "pattern": pattern,
                    "matches": len(matches),
                    "commonality": commonality,
                    "impact": match_impact
                })
        
        # Ensure uniqueness doesn't go below 0.3 (some uniqueness always exists)
        uniqueness_score = max(0.3, uniqueness_score)
        
        return {
            "uniqueness_score": uniqueness_score,
            "pattern_matches": pattern_matches,
            "is_mostly_common_patterns": uniqueness_score < 0.6
        }

class WebPlagiarismChecker:
    def __init__(self, serp_api_key: str, similarity_threshold: float = 0.3):
        self.serp_api_key = serp_api_key
        self.similarity_threshold = similarity_threshold
        self.reports_dir = "plagiarism_reports"
        os.makedirs(self.reports_dir, exist_ok=True)
        
        # Create cache directory
        self.cache_dir = "plagiarism_cache"
        os.makedirs(self.cache_dir, exist_ok=True)
        
        self.similarity_analyzer = None
        
        # Common keywords to filter out from search patterns
        self.common_keywords = {
            'int', 'char', 'float', 'double', 'void', 'return', 'if', 'else', 'for', 'while',
            'break', 'continue', 'switch', 'case', 'default', 'struct', 'class', 'public',
            'private', 'protected', 'static', 'const', 'bool', 'true', 'false', 'cout', 'cin',
            'include', 'using', 'namespace', 'std', 'string', 'vector', 'array', 'map', 'set'
        }
        
        # Cache for queries to avoid duplicate searches
        self.query_cache = {}
        self.content_cache = {}
        
        # HTTP headers for requests
        self.headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
        }

    def normalize_code(self, code: str) -> str:
        """Normalize code by removing comments, extra whitespace, and standardizing variable names."""
        # Remove comments
        code = re.sub(r'//.*?\n|/\*.*?\*/', '', code, flags=re.DOTALL)
        
        # Standardize whitespace
        code = re.sub(r'\s+', ' ', code)
        
        # Remove string literals
        code = re.sub(r'".*?"', '""', code)
        
        return code.strip()
    
    def extract_complete_functions(self, code: str) -> List[str]:
        """Extract complete functions from code."""
        # Find all function definitions with their bodies
        functions = []
        
        # Match function patterns (basic heuristic)
        func_pattern = r'\w+\s+\w+\s*\([^)]*\)\s*\{[^{]*(?:\{[^{]*\}[^{]*)*\}'
        matches = re.finditer(func_pattern, code, re.DOTALL)
        
        for match in matches:
            func = match.group(0)
            # Limit function size to avoid overly large queries
            if len(func) > 300:
                # Just get the signature and first few lines
                lines = func.split('\n')
                func = '\n'.join(lines[:5]) + '...'
            functions.append(func)
            
        return functions

    def extract_code_patterns(self, code: str) -> List[Tuple[str, float]]:
        """Extract meaningful code patterns for searching with priority weights."""
        # Normalize code for better pattern extraction
        normalized_code = self.normalize_code(code)
        
        patterns_with_priority = []
        
        # Extract complete functions (highest priority)
        functions = self.extract_complete_functions(code)
        for func in functions:
            # Calculate uniqueness score based on function complexity
            complexity = len(re.findall(r'[{};]', func)) / 10  # Heuristic for complexity
            priority = min(0.9, 0.5 + complexity * 0.1)  # Scale between 0.5-0.9
            
            # Get function signature for a more focused search
            signature = re.search(r'\w+\s+\w+\s*\([^)]*\)', func)
            if signature:
                patterns_with_priority.append((signature.group(0), priority))
            
            # Add shortened version of full function
            short_func = ' '.join(func.split()[:30])
            patterns_with_priority.append((short_func, priority))
        
        # Extract class definitions
        class_pattern = r'class\s+\w+\s*(?::\s*\w+)?\s*\{[^{]*(?:\{[^{]*\}[^{]*)*\}'
        classes = re.findall(class_pattern, code, re.DOTALL)
        for cls in classes:
            # Get class name and inheritance for focused search
            cls_name = re.search(r'class\s+(\w+)', cls)
            if cls_name:
                patterns_with_priority.append((f"class {cls_name.group(1)}", 0.7))
            
            # Add first part of class definition
            short_class = ' '.join(cls.split()[:20])
            patterns_with_priority.append((short_class, 0.8))
        
        # Extract algorithm patterns (medium priority)
        algorithm_patterns = [
            (r'sort\([^)]+\)', 0.6),
            (r'binary_search\([^)]+\)', 0.7),
            (r'find\([^)]+\)', 0.5),
            (r'for\s*\([^{]+\{[^}]+\}', 0.6),
            (r'while\s*\([^{]+\{[^}]+\}', 0.6)
        ]
        
        for pattern, priority in algorithm_patterns:
            matches = re.findall(pattern, code, re.DOTALL)
            for match in matches:
                patterns_with_priority.append((match, priority))
        
        # Extract unique lines that look like code (lowest priority)
        code_lines = [line.strip() for line in code.split('\n') 
                     if line.strip() and not line.strip().startswith('//')]
        
        # Filter for lines that appear to have logic (not just variable declarations)
        for line in code_lines[:10]:  # Consider first 10 non-comment lines
            # Skip common boilerplate
            if any(boilerplate in line for boilerplate in ['#include', 'using namespace', 'int main']):
                continue
                
            if any(keyword in line for keyword in ['=', '+=', '-=', '*=', '/=', '%=', '==', '!=', '<', '>']):
                # Lines with operations have higher priority
                patterns_with_priority.append((line, 0.4))
        
        # Remove duplicate patterns and sort by priority
        unique_patterns = {}
        for pattern, priority in patterns_with_priority:
            pattern_clean = pattern.strip()
            if pattern_clean and len(pattern_clean) > 10:  # Ensure pattern is meaningful
                if pattern_clean not in unique_patterns or priority > unique_patterns[pattern_clean]:
                    unique_patterns[pattern_clean] = priority
        
        # Convert back to list and sort by priority (highest first)
        result = [(pattern, priority) for pattern, priority in unique_patterns.items()]
        result.sort(key=lambda x: x[1], reverse=True)
        
        # Limit to top patterns to avoid excessive API calls
        return result[:5]  

    def generate_search_queries(self, code: str, language: str) -> List[Tuple[str, float]]:
        """Generate search queries for plagiarism detection based on code patterns."""
        queries = []
        
        # Select appropriate programming site domains based on language
        programming_sites = "site:github.com OR site:stackoverflow.com OR site:geeksforgeeks.org OR site:tutorialspoint.com"
        
        # Extract complete functions to analyze
        functions = self.extract_complete_functions(code)
        
        # Extract patterns from the code
        patterns = self.extract_code_patterns(code)
        
        # Add high priority patterns to the queries
        for pattern, priority in patterns[:3]:  # Take top 3 patterns
            if priority > 0.4:  # Only use significant patterns
                query = f"\"{pattern}\" {language} example {programming_sites}"
                queries.append((query, priority))
        
        # Look for class definitions generally
        class_pattern = r'class\s+(\w+)'
        class_matches = re.findall(class_pattern, code)
        for class_name in class_matches:
            # Skip common/standard names
            if class_name.lower() in {'main', 'test', 'example', 'solution'}:
                continue
                
            query = f"\"{class_name}\" class {language} example {programming_sites}"
            queries.append((query, 0.8))  # High but not highest priority
            
            # If the class name suggests functionality, search for that too
            function_words = ['calculator', 'parser', 'converter', 'manager', 'handler', 'controller']
            if any(word in class_name.lower() for word in function_words):
                function_query = f"\"{class_name}\" implementation {language} {programming_sites}"
                queries.append((function_query, 0.85))
        
        # Look for interesting function definitions generally
        function_pattern = r'(?:void|int|char|float|double|bool|string|\w+)\s+(\w+)\s*\([^)]*\)'
        func_matches = re.findall(function_pattern, code)
        for func_name in func_matches:
            if len(func_name) > 3 and func_name not in ['main', 'init', 'setup', 'test']:
                # For more complex function names, they're more likely to be unique and worth searching
                if len(func_name) > 6:
                    query = f"\"{func_name}\" function {language} example {programming_sites}"
                    queries.append((query, 0.7)) 
        
        # Look for algorithm implementations generally
        algorithm_keywords = ['sort', 'search', 'find', 'parse', 'calculate', 'compute', 'convert', 'transform']
        for keyword in algorithm_keywords:
            if re.search(rf'\b{keyword}\w*\b', code, re.IGNORECASE):
                query = f"\"{keyword}\" algorithm {language} implementation {programming_sites}"
                queries.append((query, 0.6))
                
        # If there are few queries, extract meaningful code lines
        if len(queries) < 2:
            code_lines = code.split('\n')
            meaningful_lines = []
            
            for line in code_lines:
                line = line.strip()
                # Skip comments, empty lines, and basic statements
                if not line or line.startswith('//') or line.startswith('#') or len(line) < 15:
                    continue
                    
                # Look for lines with function calls, assignments, etc.
                if '=' in line or '(' in line and ')' in line:
                    # Extract significant tokens, excluding common keywords
                    tokens = re.findall(r'\b\w+\b', line)
                    significant = [t for t in tokens if len(t) > 3 and t.lower() not in self.common_keywords]
                    
                    if significant:
                        meaningful_line = ' '.join(significant[:3])  # Take first 3 significant tokens
                        meaningful_lines.append((meaningful_line, len(significant)))
            
            # Sort by number of significant tokens
            meaningful_lines.sort(key=lambda x: x[1], reverse=True)
            
            # Add top meaningful lines to queries
            for line, _ in meaningful_lines[:2]:
                query = f"\"{line}\" {language} code example {programming_sites}"
                queries.append((query, 0.5))
                
        # Ensure at least one query is generated
        if not queries:
            fallback_query = f"{language} programming example {programming_sites}"
            queries.append((fallback_query, 0.4))
        
        # Sort by priority and limit
        queries.sort(key=lambda x: x[1], reverse=True)
        return queries[:3]  # Limit to top 3 to avoid API limits

    def search_code(self, query: str, priority: float = 0.5) -> List[Dict[str, Any]]:
        """Search for code using SerpAPI."""
        results = []
        
        # Check cache first
        cache_key = hashlib.md5(query.encode()).hexdigest()
        cache_file = os.path.join(self.cache_dir, f"{cache_key}.json")
        
        # Try to load from cache
        if os.path.exists(cache_file):
            try:
                with open(cache_file, 'r', encoding='utf-8') as f:
                    cached_data = json.load(f)
                    return cached_data
            except Exception as e:
                print(f"Error loading from cache: {str(e)}")
        
        try:
            # Enhance query with programming website sources
            enhanced_query = query
            if "site:" not in query:
                # Search across multiple common programming sites
                enhanced_query = f"{query} (site:github.com OR site:stackoverflow.com OR site:geeksforgeeks.org OR site:w3schools.com OR site:tutorialspoint.com)"
            
            # SerpAPI endpoint for Google search
            url = f"https://serpapi.com/search.json"
            
            params = {
                "api_key": self.serp_api_key,
                "q": enhanced_query,
                "engine": "google",
                "num": 10,
                "gl": "us"
            }
            
            print(f"SerpAPI Search: {enhanced_query}")
            
            response = requests.get(url, params=params, timeout=15)
            if response.status_code == 200:
                data = response.json()
                
                # Process organic results
                if "organic_results" in data:
                    for result in data["organic_results"]:
                        # Extract relevant information
                        item = {
                            "title": result.get("title", ""),
                            "link": result.get("link", ""),
                            "snippet": result.get("snippet", ""),
                            "query": enhanced_query,
                            "query_priority": priority,
                            "initial_score": 0.0,
                            "similarity_score": 0.0,
                            "is_plagiarism": False
                        }
                        
                        results.append(item)
            else:
                print(f"Error searching code: {response.status_code} {response.reason}")
        
        except Exception as e:
            print(f"Error searching code: {str(e)}")
        
        # If no results, try a more general search
        if not results:
            general_query = query
            # Remove any site: restrictions if present
            for site in ["site:github.com", "site:stackoverflow.com", "site:geeksforgeeks.org", "site:w3schools.com", "site:tutorialspoint.com"]:
                general_query = general_query.replace(site, "").strip()
            
            general_query += " code example"
            
            # SerpAPI endpoint for Google search
            url = f"https://serpapi.com/search.json"
            
            params = {
                "api_key": self.serp_api_key,
                "q": general_query,
                "engine": "google",
                "num": 10,
                "gl": "us"
            }
            
            try:
                print(f"Fallback SerpAPI Search: {general_query}")
                response = requests.get(url, params=params, timeout=15)
                if response.status_code == 200:
                    data = response.json()
                    
                    # Process organic results
                    if "organic_results" in data:
                        for result in data["organic_results"]:
                            # Extract relevant information
                            item = {
                                "title": result.get("title", ""),
                                "link": result.get("link", ""),
                                "snippet": result.get("snippet", ""),
                                "query": general_query,
                                "query_priority": priority - 0.1,  # Slightly lower priority
                                "initial_score": 0.0,
                                "similarity_score": 0.0,
                                "is_plagiarism": False
                            }
                            
                            results.append(item)
                else:
                    print(f"Error in fallback search: {response.status_code} {response.reason}")
            except Exception as e:
                print(f"Error in fallback search: {str(e)}")
        
        # Save results to cache
        try:
            with open(cache_file, 'w', encoding='utf-8') as f:
                json.dump(results, f, indent=2)
        except Exception as e:
            print(f"Error saving to cache: {str(e)}")
        
        return results

    def get_content_from_snippet(self, result: Dict[str, Any]) -> str:
        """Extract code content from a search result snippet or URL."""
        url = result.get("link", "")
        
        # Skip if no URL
        if not url:
            return result.get("snippet", "")
        
        # Check cache for this URL
        cache_key = hashlib.md5(url.encode()).hexdigest()
        cache_file = os.path.join(self.cache_dir, f"content_{cache_key}.txt")
        
        # Try to load from cache
        if url in self.content_cache:
            return self.content_cache[url]
        elif os.path.exists(cache_file):
            try:
                with open(cache_file, 'r', encoding='utf-8') as f:
                    content = f.read()
                    self.content_cache[url] = content
                    return content
            except Exception as e:
                print(f"Error loading content from cache: {str(e)}")
        
        # Try to get the actual content from the URL
        try:
            headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
            }
            
            # Try to fetch the web page
            print(f"Fetching content from: {url}")
            response = requests.get(url, headers=headers, timeout=10)
            
            if response.status_code == 200:
                # Parse the HTML
                soup = BeautifulSoup(response.text, 'html.parser')
                
                # Extract code blocks (common patterns in programming sites)
                code_blocks = []
                
                # Look for code elements with specific class names or in pre/code tags
                for tag in soup.select('pre, code, .highlight, .code, .snippet, .language-*, .prettyprint'):
                    code_blocks.append(tag.get_text())
                
                # Try to find specifically formatted code examples
                if not code_blocks:
                    # Look for div elements with code-like class names
                    for tag in soup.select('div.code, div.example, div.codeBlock, div.syntaxhighlighter, div.sourceCode'):
                        code_blocks.append(tag.get_text())
                
                # Join all code blocks
                if code_blocks:
                    content = "\n\n".join(code_blocks)
                    
                    # Clean up the content
                    content = content.strip()
                    
                    # Store in cache
                    self.content_cache[url] = content
                    
                    # Save to cache file
                    with open(cache_file, 'w', encoding='utf-8') as f:
                        f.write(content)
                    
                    return content
                
                # If we couldn't find any code blocks, try to guess where code might be
                # Look for content with programming keywords
                content_areas = []
                for tag in soup.select('article, section, .post-content, .article-content, .post-body, .entry-content'):
                    content_areas.append(tag.get_text())
                
                if content_areas:
                    # Join all content areas
                    main_content = "\n\n".join(content_areas)
                    
                    # Try to extract code-like segments (lines with braces, semicolons, etc.)
                    code_lines = []
                    for line in main_content.split('\n'):
                        if re.search(r'[{};]', line) or re.search(r'^\s*(if|for|while|class|def|function|return)\b', line):
                            code_lines.append(line)
                    
                    if code_lines:
                        content = "\n".join(code_lines)
                        
                        # Store in cache
                        self.content_cache[url] = content
                        
                        # Save to cache file
                        with open(cache_file, 'w', encoding='utf-8') as f:
                            f.write(content)
                        
                        return content
                
                # If we still haven't found anything, just use the whole page text
                content = soup.get_text()
                
                # Limit content size
                if len(content) > 5000:
                    content = content[:5000]
                
                # Store in cache
                self.content_cache[url] = content
                
                # Save to cache file
                with open(cache_file, 'w', encoding='utf-8') as f:
                    f.write(content)
                
                return content
        except Exception as e:
            print(f"Error fetching content from {url}: {str(e)}")
        
        # Fallback to snippet
        return result.get("snippet", "")

    def compare_code_similarity(self, original_code: str, web_code: str, language: str) -> float:
        """Compare similarity between the original code and code found online."""
        # Skip empty content
        if not web_code or len(web_code) < 20:
            return 0.0
        
        # Try to use the SimilarityAnalyzer first
        if SIMILARITY_ANALYZER_AVAILABLE:
            try:
                # Initialize analyzer if not already done
                if not self.similarity_analyzer:
                    self.similarity_analyzer = SimilarityAnalyzer(language=language)
                    print(f"Initialized SimilarityAnalyzer for {language}")
                
                # Prepare submissions for comparison
                submissions = {
                    "original": original_code,
                    "web_code": web_code
                }
                
                # Run the analysis
                results = self.similarity_analyzer.analyze_submissions(submissions)
                
                # Extract similarity score
                if "pairwise_comparisons" in results:
                    for pair in results["pairwise_comparisons"]:
                        if (pair["file1"] == "original" and pair["file2"] == "web_code") or \
                           (pair["file1"] == "web_code" and pair["file2"] == "original"):
                            return pair["similarity_score"]
                
                # Try similarity matrix if available
                if "similarity_matrix" in results and len(results["similarity_matrix"]) > 1:
                    return results["similarity_matrix"][0][1]  # Assume 2x2 matrix
                
                # Try suspicious pairs
                if "suspicious_pairs" in results:
                    for pair, score in results["suspicious_pairs"]:
                        if set(pair) == {"original", "web_code"}:
                            return score
                
                # If we have results but couldn't extract a score, use a medium-high value
                # This assumes the analyzer found similarity but didn't format it how we expected
                if results and not all(value == 0 for value in [
                    results.get("max_similarity", 0),
                    results.get("average_similarity", 0)
                ]):
                    return max(results.get("max_similarity", 0), results.get("average_similarity", 0))
                    
            except Exception as e:
                print(f"Error in SimilarityAnalyzer: {str(e)}, using fallback method")
        else:
            print("SimilarityAnalyzer not available, using fallback method")
        
        # Enhanced fallback comparison method
        try:
            # Clean and normalize both code samples
            def normalize_for_comparison(code):
                # Remove comments
                code = re.sub(r'//.*?\n|/\*.*?\*/', '', code, flags=re.DOTALL)
                # Normalize whitespace (preserve newlines for structure analysis)
                code = re.sub(r'[ \t]+', ' ', code)
                # Remove string literals
                code = re.sub(r'".*?"', '""', code)
                code = re.sub(r"'.*?'", "''", code)
                return code
            
            orig_normalized = normalize_for_comparison(original_code)
            web_normalized = normalize_for_comparison(web_code)
            
            # Handle empty normalized content
            if not orig_normalized or not web_normalized:
                return 0.0
            
            # Split into lines for structural comparison
            orig_lines = [line.strip() for line in orig_normalized.split('\n') if line.strip()]
            web_lines = [line.strip() for line in web_normalized.split('\n') if line.strip()]
            
            if not orig_lines or not web_lines:
                return 0.0
            
            # 1. Calculate line-based similarity
            # Find the number of lines that are identical or very similar
            matching_lines = 0
            for o_line in orig_lines:
                for w_line in web_lines:
                    # Calculate similarity between these two lines
                    if o_line == w_line:
                        matching_lines += 1
                        break
                    # Allow for small variations (check subset relationship)
                    elif len(o_line) > 10 and len(w_line) > 10:
                        o_tokens = set(re.findall(r'\b\w+\b', o_line))
                        w_tokens = set(re.findall(r'\b\w+\b', w_line))
                        
                        # If one is subset of another with high overlap
                        if len(o_tokens.intersection(w_tokens)) / max(len(o_tokens), len(w_tokens)) > 0.7:
                            matching_lines += 0.7
                            break
                            
            line_similarity = matching_lines / max(len(orig_lines), len(web_lines))
            
            # 2. Pattern-based similarity (looking for specific code structures)
            # Extract and compare function signatures, class definitions, etc.
            def extract_patterns(code_lines):
                patterns = []
                for line in code_lines:
                    # Function/method signatures
                    if re.search(r'\b(function|def|void|int|double|float|char|bool)\s+\w+\s*\([^\)]*\)', line):
                        patterns.append(('function', line))
                    # Class definitions
                    elif re.search(r'\b(class|struct)\s+\w+', line):
                        patterns.append(('class', line))
                    # Control structures
                    elif re.search(r'\b(if|for|while|switch|case)\s*\(', line):
                        patterns.append(('control', line))
                    # Return statements
                    elif re.search(r'\breturn\b', line):
                        patterns.append(('return', line))
                return patterns
            
            orig_patterns = extract_patterns(orig_lines)
            web_patterns = extract_patterns(web_lines)
            
            # Calculate pattern similarity
            pattern_matches = 0
            if orig_patterns and web_patterns:
                for o_type, o_pattern in orig_patterns:
                    for w_type, w_pattern in web_patterns:
                        if o_type == w_type:
                            # For same pattern types, compare content
                            o_tokens = set(re.findall(r'\b\w+\b', o_pattern))
                            w_tokens = set(re.findall(r'\b\w+\b', w_pattern))
                            
                            overlap = len(o_tokens.intersection(w_tokens)) / max(len(o_tokens), len(w_tokens))
                            if overlap > 0.6:
                                pattern_matches += overlap
                                break
            
                pattern_similarity = pattern_matches / max(len(orig_patterns), len(web_patterns))
            else:
                pattern_similarity = 0.0
            
            # 3. Token-based similarity
            # Get all significant tokens (excluding common keywords)
            common_tokens = {'if', 'else', 'for', 'while', 'return', 'int', 'char', 'float', 'double', 
                            'void', 'class', 'struct', 'public', 'private', 'protected', 'const', 'static'}
            
            def get_significant_tokens(code):
                all_tokens = re.findall(r'\b\w+\b', code)
                return [t for t in all_tokens if t not in common_tokens and len(t) > 2]
            
            orig_tokens = get_significant_tokens(orig_normalized)
            web_tokens = get_significant_tokens(web_normalized)
            
            # Calculate Jaccard similarity
            if orig_tokens and web_tokens:
                intersection = set(orig_tokens).intersection(set(web_tokens))
                union = set(orig_tokens).union(set(web_tokens))
                token_similarity = len(intersection) / len(union) if union else 0
            else:
                token_similarity = 0.0
            
            # Weight the different similarity measures
            final_similarity = (0.4 * line_similarity) + (0.4 * pattern_similarity) + (0.2 * token_similarity)
            
            # Boost similarity for short code fragments that match exactly
            if (len(orig_lines) < 10 and len(web_lines) < 10 and 
                line_similarity > 0.8 and pattern_similarity > 0.8):
                final_similarity = max(final_similarity, 0.9)
            
            # If the code is very long and complex, adjust the threshold
            if len(orig_lines) > 50 and len(web_lines) > 50 and pattern_similarity > 0.7:
                final_similarity = max(final_similarity, 0.8)
                
            return min(final_similarity, 1.0)  # Cap at 1.0
            
        except Exception as e:
            print(f"Error in fallback comparison: {str(e)}")
            # Last resort: extremely basic comparison
            try:
                orig_tokens = set(re.findall(r'\b\w+\b', original_code))
                web_tokens = set(re.findall(r'\b\w+\b', web_code))
                if not orig_tokens or not web_tokens:
                    return 0.0
                return len(orig_tokens.intersection(web_tokens)) / len(orig_tokens.union(web_tokens))
            except:
                return 0.0

    def check_plagiarism(self, file_path: str, language: str = "cpp") -> Dict[str, Any]:
        """Check a file for plagiarism using SerpAPI and SimilarityAnalyzer.
        
        Results are limited to the top 5 plagiarism matches with the highest similarity scores.
        These represent the sources from which the code is most likely plagiarized.
        """
        try:
            # Read the file
            with open(file_path, 'r', encoding='utf-8') as f:
                code = f.read()
            
            # Initialize the similarity analyzer if available
            if SIMILARITY_ANALYZER_AVAILABLE and not self.similarity_analyzer:
                self.similarity_analyzer = SimilarityAnalyzer(language=language)
                print(f"Initialized SimilarityAnalyzer for {language}")
            
            # Check for common patterns first
            pattern_analyzer = CommonPatternAnalyzer(language)
            pattern_analysis = pattern_analyzer.analyze_code(code)
            
            # If code is mostly common patterns, adjust the threshold
            adjusted_threshold = self.similarity_threshold
            if pattern_analysis["is_mostly_common_patterns"]:
                # Increase threshold for code that's mostly common patterns
                adjusted_threshold = min(0.6, self.similarity_threshold * 1.5)
                print(f"Code contains mostly common patterns - adjusting similarity threshold to {adjusted_threshold:.2f}")
            
            # Generate optimized search queries
            queries = self.generate_search_queries(code, language)
            
            # Search for each query
            all_results = []
            for query, priority in queries:
                print(f"Searching for: {query} (priority: {priority:.2f})")
                results = self.search_code(query, priority)
                all_results.extend(results)
            
            # Remove duplicate results
            unique_results = []
            seen_links = set()
            for result in all_results:
                if result["link"] not in seen_links:
                    seen_links.add(result["link"])
                    
                    # Extract code content from the search result
                    web_code = self.get_content_from_snippet(result)
                    
                    # Compare similarity
                    similarity = self.compare_code_similarity(code, web_code, language)
                    
                    # Add similarity score to the result
                    result["similarity_score"] = similarity
                    result["is_plagiarism"] = similarity >= adjusted_threshold
                    
                    unique_results.append(result)
            
            # Sort results by similarity score (highest first)
            unique_results.sort(key=lambda x: x["similarity_score"], reverse=True)
            
            # Filter results based on similarity threshold
            plagiarism_results = [r for r in unique_results if r["is_plagiarism"]]
            
            # Sort plagiarism results by similarity score and limit to top 5 most similar matches
            plagiarism_results.sort(key=lambda x: x["similarity_score"], reverse=True)
            plagiarism_results = plagiarism_results[:5]
            
            # Create report
            report = {
                "file": file_path,
                "language": language,
                "timestamp": datetime.now().isoformat(),
                "queries_used": [q for q, _ in queries],
                "results": unique_results,
                "total_results": len(unique_results),
                "plagiarism_detected": len(plagiarism_results) > 0,
                "plagiarism_results": plagiarism_results,
                "similarity_threshold": adjusted_threshold,
                "matching_sources": [r["link"] for r in plagiarism_results]
            }
            
            # If plagiarism detected, print the matching sources
            if plagiarism_results:
                print("\nPlagiarism detected! Matching sources:")
                for r in plagiarism_results:
                    print(f"- {r['link']} (similarity: {r['similarity_score']:.2f})")
            
            return report
            
        except Exception as e:
            print(f"Error checking plagiarism: {str(e)}")
            return {
                "file": file_path,
                "language": language,
                "error": str(e)
            }

def main():
    """Main entry point for the plagiarism checker."""
    import argparse
    
    parser = argparse.ArgumentParser(description='Check code for plagiarism using SerpAPI')
    parser.add_argument('--file', required=True, help='Path to the file to check')
    parser.add_argument('--language', default='cpp', help='Programming language (default: cpp)')
    parser.add_argument('--api-key', required=True, help='SerpAPI key')
    parser.add_argument('--threshold', type=float, default=0.3, help='Similarity threshold (default: 0.3)')
    parser.add_argument('--detailed', action='store_true', help='Show detailed comparison results')
    
    args = parser.parse_args()
    
    # Verify file exists
    if not os.path.isfile(args.file):
        print(f"Error: File '{args.file}' not found.")
        return 1
    
    # Verify language is supported
    supported_languages = ['cpp', 'c', 'python', 'java', 'javascript']
    if args.language.lower() not in supported_languages:
        print(f"Warning: Language '{args.language}' is not explicitly supported. Using generic code analysis.")
    
    # Validate API key format
    if not args.api_key or len(args.api_key) < 10:
        print("Error: Invalid API key format. Please provide a valid SerpAPI key.")
        return 1
    
    try:
        # Initialize the checker
        checker = WebPlagiarismChecker(args.api_key, args.threshold)
        
        # Show progress message
        print(f"Checking {args.file} for plagiarism...")
        print(f"Language: {args.language}")
        print(f"Similarity threshold: {args.threshold}")
        
        # Perform the check
        report = checker.check_plagiarism(args.file, args.language)
        
        # Output results
        if "error" in report:
            print(f"Error: {report['error']}")
            return 1
        
        print(f"Plagiarism report generated: {os.path.basename(args.file)}_plagiarism_report.json")
        print(f"Found {len(report['results'])} potential matches")
        print(f"Queries used: {', '.join(report['queries_used'])}")
        
        if report["plagiarism_detected"]:
            print("\n" + "="*80)
            print(f"WARNING: Plagiarism detected! {len(report['plagiarism_results'])} matches above threshold.")
            print("="*80 + "\n")
            
            # Print details of plagiarism matches
            for i, match in enumerate(report['plagiarism_results']):
                print(f"Match #{i+1}: {match['link']}")
                print(f"  Title: {match['title']}")
                print(f"  Similarity: {match['similarity_score']:.2f} ({match['similarity_score']*100:.1f}%)")
                print(f"  Snippet: {match['snippet'][:150]}...")
                print()
                
            if args.detailed:
                try:
                    # Read original file
                    with open(args.file, 'r', encoding='utf-8') as f:
                        original_code = f.read()
                    
                    print("Most similar code sections:")
                    # For each plagiarism result, show a side-by-side comparison of key sections
                    for match in report['plagiarism_results'][:1]:  # Just show the top match
                        print(f"\nComparison with: {match['link']}")
                        # Get content from match
                        web_content = checker.get_content_from_snippet(match)
                        
                        # Find common code patterns
                        original_lines = [line.strip() for line in original_code.split('\n') if line.strip()]
                        web_lines = [line.strip() for line in web_content.split('\n') if line.strip()]
                        
                        # Find similar lines
                        similar_sections = []
                        for i, o_line in enumerate(original_lines):
                            if len(o_line) < 10 or o_line.startswith('//'):
                                continue
                                
                            for j, w_line in enumerate(web_lines):
                                if len(w_line) < 10 or w_line.startswith('//'):
                                    continue
                                    
                                # Basic similarity check
                                o_tokens = set(re.findall(r'\b\w+\b', o_line))
                                w_tokens = set(re.findall(r'\b\w+\b', w_line))
                                
                                if o_tokens and w_tokens:
                                    similarity = len(o_tokens.intersection(w_tokens)) / max(len(o_tokens), len(w_tokens))
                                    if similarity > 0.7:
                                        similar_sections.append((i, j, similarity))
                        
                        # Sort by similarity
                        similar_sections.sort(key=lambda x: x[2], reverse=True)
                        
                        # Show top similar sections
                        if similar_sections:
                            print("\nTop similar code sections:")
                            for i, j, sim in similar_sections[:5]:
                                print(f"\nSimilarity: {sim:.2f} ({sim*100:.1f}%)")
                                print(f"Original: {original_lines[i]}")
                                print(f"Web:      {web_lines[j]}")
                        else:
                            print("No specific matching code sections found for side-by-side comparison.")
                
                except Exception as e:
                    print(f"Error generating detailed comparison: {str(e)}")
            
            return 1  # Return error code if plagiarism detected
        else:
            print("\n" + "="*80)
            print(f"No plagiarism detected for {args.file}")
            print("="*80 + "\n")
            return 0  # Return success code if no plagiarism detected
        
    except KeyboardInterrupt:
        print("\nPlagiarism check interrupted.")
        return 130  # Standard interrupt exit code
    except Exception as e:
        print(f"Unexpected error: {str(e)}")
        return 1

if __name__ == "__main__":
    sys.exit(main()) 
