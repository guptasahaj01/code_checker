"""
Complete Solution Extractor for C++ Code

This module extracts C++ code solutions from PDF assignments and combines
semantically related code blocks (classes, functions, main) into single complete solutions.
"""

import os
import re
from typing import List, Dict, Tuple, Set
import pdfplumber
from pathlib import Path

class CompleteSolutionExtractor:
    """
    Advanced processor that extracts complete C++ code solutions from PDF assignments.
    
    This class identifies and groups related code blocks (classes, functions, main) 
    into single coherent solutions based on their dependencies and relationships.
    """
    
    def __init__(self, output_base_dir: str = "output"):
        """
        Initialize the solution extractor.
        
        Args:
            output_base_dir: Base directory to save extracted code
        """
        self.output_base_dir = output_base_dir
        
        # Create base output directory if it doesn't exist
        os.makedirs(output_base_dir, exist_ok=True)
        
        # Patterns for identifying different C++ code structures
        self.class_pattern = r'(?:class|struct)\s+(\w+)\s*(?:\s*:\s*(?:public|private|protected)\s+\w+(?:::\w+)*)?\s*\{'
        self.main_function_pattern = r'int\s+main\s*\([^)]*\)\s*\{'
        self.function_pattern = r'(?:void|int|char|float|double|bool|unsigned|long|short|auto|string|std::string|vector|std::vector|map|std::map|\w+::\w+|\w+<[^>]+>)\s+(\w+)\s*\([^)]*\)\s*(?:const|override|final|noexcept)?\s*\{'
        self.namespace_pattern = r'namespace\s+(\w+)\s*\{'
        
        # Solution separator patterns
        self.solution_separator_patterns = [
            r'//\s*(?:Solution|SOLUTION)\s*(?:\d+|[A-Z])?',  # // Solution 1, // SOLUTION A
            r'/\*+\s*(?:Solution|SOLUTION)\s*(?:\d+|[A-Z])?\s*\*+/',  # /* Solution 1 */, /** SOLUTION A **/ 
            r'\/\/\s*-{5,}',  # // ----- (at least 5 dashes)
            r'\/\/\s*={5,}',  # // ===== (at least 5 equal signs)
            r'\/\/\s*\*{5,}',  # // ***** (at least 5 stars)
            r'#\s*(?:Solution|SOLUTION)\s*(?:\d+|[A-Z])?',  # # Solution 1, # SOLUTION A
            r'(?:Solution|SOLUTION)\s*(?:\d+|[A-Z])\s*:',  # Solution 1:, SOLUTION A:
            r'\/\/\s*Student\s*(?:\d+|[A-Z])?\s*:',  # // Student 1:, // Student A:
            r'\/\/\s*Submission\s*(?:\d+|[A-Z])?\s*:',  # // Submission 1:, // Submission A:
            r'\/\/\s*Begin\s*(?:Solution|Code)',  # // Begin Solution, // Begin Code
            r'\/\/\s*End\s*(?:Solution|Code)',  # // End Solution, // End Code
            r'\/\/\s*-{3,}\s*(?:New|Next)\s*(?:Solution|Submission)',  # // --- New Solution, // --- Next Submission
            r'\/\*\s*-{3,}\s*(?:New|Next)\s*(?:Solution|Submission)\s*-{3,}\s*\*\/',  # /* --- New Solution --- */
        ]
    
    def extract_text_from_pdf(self, pdf_path: str) -> str:
        """
        Extract all text from a PDF file.
        
        Args:
            pdf_path: Path to the PDF file
            
        Returns:
            Extracted text as a string
        """
        with pdfplumber.open(pdf_path) as pdf:
            text = ""
            for page in pdf.pages:
                page_text = page.extract_text()
                if page_text:
                    text += page_text + "\n"
            return text
    
    def find_matching_brace(self, text: str, start_pos: int) -> int:
        """
        Find the matching closing brace for an opening brace.
        
        Args:
            text: The text to search in
            start_pos: Position of the opening brace
            
        Returns:
            Position of the matching closing brace or -1 if not found
        """
        brace_count = 1
        pos = start_pos + 1
        
        while brace_count > 0 and pos < len(text):
            if text[pos] == '{':
                brace_count += 1
            elif text[pos] == '}':
                brace_count -= 1
            pos += 1
            
        return pos - 1 if brace_count == 0 else -1
    
    def detect_solution_boundaries(self, text: str) -> List[int]:
        """
        Detect positions in the text that likely represent boundaries between different solutions.
        
        Args:
            text: The text containing code solutions
            
        Returns:
            List of positions where solution boundaries occur
        """
        boundary_positions = []
        
        # Look for solution separator patterns that indicate boundaries between solutions
        combined_pattern = '|'.join(f'({pattern})' for pattern in self.solution_separator_patterns)
        
        for match in re.finditer(combined_pattern, text, re.MULTILINE):
            boundary_pos = match.start()
            # Add some context to make sure we're not in the middle of a code comment
            context_start = max(0, boundary_pos - 50)
            context = text[context_start:boundary_pos + 50]
            
            # If the pattern is not inside a multi-line comment or code block
            if not re.search(r'/\*.*' + re.escape(match.group(0)) + r'.*\*/', context, re.DOTALL) and \
               not (context.count('{') > context.count('}') and '{' in context[:50]):
                boundary_positions.append(boundary_pos)
        
        # Also look for multiple consecutive main functions as boundaries
        # They indicate different solutions since each solution should have only one main
        main_positions = [m.start() for m in re.finditer(self.main_function_pattern, text, re.MULTILINE)]
        
        if len(main_positions) > 1:
            for i in range(len(main_positions) - 1):
                pos1 = main_positions[i]
                pos2 = main_positions[i + 1]
                
                # Find end of first main function
                brace_pos = text.find('{', pos1)
                if brace_pos != -1:
                    end_pos = self.find_matching_brace(text, brace_pos)
                    if end_pos != -1 and end_pos < pos2:
                        # If there's a gap between end of first main and start of second main,
                        # there's likely a solution boundary somewhere in between
                        mid_point = (end_pos + pos2) // 2
                        boundary_positions.append(mid_point)
        
        # Also look for significant gaps between code blocks
        # A large gap (many empty lines) often indicates different solutions
        for match in re.finditer(r'\n\s*\n\s*\n\s*\n\s*\n', text):  # 5+ newlines
            boundary_positions.append(match.start() + 2)  # Add the position after the first newline
            
        return sorted(boundary_positions)
    
    def extract_code_blocks(self, text: str) -> List[Dict]:
        """
        Extract all C++ code blocks and their details from text.
        
        Args:
            text: Text containing C++ code
            
        Returns:
            List of dictionaries with code block details
        """
        code_blocks = []
        
        # First detect solution boundaries
        solution_boundaries = self.detect_solution_boundaries(text)
        
        # Extract classes
        for match in re.finditer(self.class_pattern, text, re.MULTILINE):
            start_pos = match.start()
            class_name = match.group(1) if match.groups() else "Unknown"
            brace_pos = text.find('{', start_pos)
            
            if brace_pos == -1:
                continue
                
            end_pos = self.find_matching_brace(text, brace_pos)
            
            if end_pos == -1:
                continue
                
            code = text[start_pos:end_pos + 1].strip()
            
            if code and len(code) > 10 and '{' in code and '}' in code:
                # Find which solution this code block belongs to
                solution_index = self.determine_solution_index(start_pos, solution_boundaries)
                
                code_blocks.append({
                    'type': 'class',
                    'name': class_name,
                    'code': code,
                    'start_pos': start_pos,
                    'end_pos': end_pos,
                    'solution_index': solution_index
                })
        
        # Extract main functions
        for match in re.finditer(self.main_function_pattern, text, re.MULTILINE):
            start_pos = match.start()
            brace_pos = text.find('{', start_pos)
            
            if brace_pos == -1:
                continue
                
            end_pos = self.find_matching_brace(text, brace_pos)
            
            if end_pos == -1:
                continue
                
            code = text[start_pos:end_pos + 1].strip()
            
            if code and len(code) > 10 and '{' in code and '}' in code:
                # Find which solution this code block belongs to
                solution_index = self.determine_solution_index(start_pos, solution_boundaries)
                
                code_blocks.append({
                    'type': 'main',
                    'name': 'main',
                    'code': code,
                    'start_pos': start_pos,
                    'end_pos': end_pos,
                    'solution_index': solution_index
                })
        
        # Extract other functions
        for match in re.finditer(self.function_pattern, text, re.MULTILINE):
            start_pos = match.start()
            
            # Skip if we match a main function (already handled)
            if "int main" in match.group(0):
                continue
                
            function_name = match.group(1) if match.groups() else "Unknown"
            brace_pos = text.find('{', start_pos)
            
            if brace_pos == -1:
                continue
                
            end_pos = self.find_matching_brace(text, brace_pos)
            
            if end_pos == -1:
                continue
                
            # Skip if this function is already part of a class
            if any(block['type'] == 'class' and 
                  start_pos > block['start_pos'] and 
                  end_pos < block['end_pos'] 
                  for block in code_blocks):
                continue
                
            code = text[start_pos:end_pos + 1].strip()
            
            if code and len(code) > 10 and '{' in code and '}' in code:
                # Find which solution this code block belongs to
                solution_index = self.determine_solution_index(start_pos, solution_boundaries)
                
                code_blocks.append({
                    'type': 'function',
                    'name': function_name,
                    'code': code,
                    'start_pos': start_pos,
                    'end_pos': end_pos,
                    'solution_index': solution_index
                })
                
        # Extract namespaces
        for match in re.finditer(self.namespace_pattern, text, re.MULTILINE):
            start_pos = match.start()
            namespace_name = match.group(1) if match.groups() else "Unknown"
            brace_pos = text.find('{', start_pos)
            
            if brace_pos == -1:
                continue
                
            end_pos = self.find_matching_brace(text, brace_pos)
            
            if end_pos == -1:
                continue
                
            code = text[start_pos:end_pos + 1].strip()
            
            if code and len(code) > 10 and '{' in code and '}' in code:
                # Find which solution this code block belongs to
                solution_index = self.determine_solution_index(start_pos, solution_boundaries)
                
                code_blocks.append({
                    'type': 'namespace',
                    'name': namespace_name,
                    'code': code,
                    'start_pos': start_pos,
                    'end_pos': end_pos,
                    'solution_index': solution_index
                })
        
        # Clean each code block
        for block in code_blocks:
            block['code'] = self.clean_code(block['code'])
            
        return code_blocks
    
    def determine_solution_index(self, position: int, solution_boundaries: List[int]) -> int:
        """
        Determine which solution a code block belongs to based on its position.
        
        Args:
            position: The position of the code block in the text
            solution_boundaries: List of positions where solution boundaries occur
            
        Returns:
            Solution index (0-based)
        """
        if not solution_boundaries:
            return 0
            
        # Find the rightmost boundary that is less than or equal to the position
        for i, boundary in enumerate(solution_boundaries):
            if position < boundary:
                return i
                
        # If position is after all boundaries, it belongs to the last solution
        return len(solution_boundaries)
    
    def identify_dependencies(self, code_blocks: List[Dict]) -> Dict[str, Set[str]]:
        """
        Identify dependencies between code blocks based on class and function usage.
        
        Args:
            code_blocks: List of code block dictionaries
            
        Returns:
            Dictionary mapping block indices to sets of related block indices
        """
        # Create a map of class names to their indices
        class_name_to_index = {}
        for i, block in enumerate(code_blocks):
            if block['type'] == 'class':
                class_name_to_index[block['name']] = i
        
        # Create a map of function names to their indices
        function_name_to_index = {}
        for i, block in enumerate(code_blocks):
            if block['type'] == 'function':
                function_name_to_index[block['name']] = i
        
        # Find references between blocks
        references = {i: set() for i in range(len(code_blocks))}
        
        for i, block in enumerate(code_blocks):            
            # Check for class references
            if block['type'] != 'class':
                for class_name, class_index in class_name_to_index.items():
                    # Skip if blocks are from different solutions
                    if block.get('solution_index', -1) != code_blocks[class_index].get('solution_index', -2):
                        continue
                    
                    # Look for class name followed by :: (static method call)
                    if re.search(r'\b' + re.escape(class_name) + r'::', block['code']):
                        references[i].add(class_index)
                        references[class_index].add(i)
                        
                    # Look for class name followed by space and variable name (object declaration)
                    if re.search(r'\b' + re.escape(class_name) + r'\s+\w+', block['code']):
                        references[i].add(class_index)
                        references[class_index].add(i)
                        
                    # Look for class array declarations
                    if re.search(r'\b' + re.escape(class_name) + r'\s*[\[]', block['code']):
                        references[i].add(class_index)
                        references[class_index].add(i)
            
            # Check for function references
            if block['type'] != 'function':
                for func_name, func_index in function_name_to_index.items():
                    # Skip if blocks are from different solutions
                    if block.get('solution_index', -1) != code_blocks[func_index].get('solution_index', -2):
                        continue
                    
                    if i != func_index:  # Don't link a function to itself
                        # Look for function calls: name followed by parentheses
                        if re.search(r'\b' + re.escape(func_name) + r'\s*\(', block['code']):
                            references[i].add(func_index)
                            references[func_index].add(i)
                            
                        # Other function reference patterns...
                        # ... existing code for function references ...
            
            # Also check for function-to-function dependencies
            if block['type'] == 'function':
                for func_name, func_index in function_name_to_index.items():
                    # Skip if blocks are from different solutions
                    if block.get('solution_index', -1) != code_blocks[func_index].get('solution_index', -2):
                        continue
                    
                    if i != func_index:  # Don't link a function to itself
                        # Look for function calls within other functions
                        if re.search(r'\b' + re.escape(func_name) + r'\s*\(', block['code']):
                            references[i].add(func_index)
                            references[func_index].add(i)
        
        # For blocks with the same solution_index, be more likely to group them together
        for i in range(len(code_blocks)):
            for j in range(len(code_blocks)):
                if i != j and code_blocks[i].get('solution_index', -1) == code_blocks[j].get('solution_index', -2):
                    # Small code fragments in the same solution should be linked
                    i_lines = len(code_blocks[i]['code'].split('\n'))
                    j_lines = len(code_blocks[j]['code'].split('\n'))
                    
                    if i_lines < 10 or j_lines < 10:
                        references[i].add(j)
                        references[j].add(i)
                    
                    # Main functions should be linked to other blocks in the same solution
                    if code_blocks[i]['type'] == 'main' or code_blocks[j]['type'] == 'main':
                        references[i].add(j)
                        references[j].add(i)
        
        return references
    
    def group_related_blocks(self, code_blocks: List[Dict]) -> List[List[int]]:
        """
        Group related code blocks into complete solutions.
        
        Args:
            code_blocks: List of code block dictionaries
            
        Returns:
            List of lists, where each inner list contains indices of related blocks
        """
        # Group blocks by solution_index first
        solution_groups = {}
        for i, block in enumerate(code_blocks):
            solution_idx = block.get('solution_index', 0)
            if solution_idx not in solution_groups:
                solution_groups[solution_idx] = []
            solution_groups[solution_idx].append(i)
        
        # Identify references between blocks
        references = self.identify_dependencies(code_blocks)
        
        final_groups = []
        
        # Process each solution group
        for solution_idx, block_indices in solution_groups.items():
            # Use a graph traversal to find connected components within this solution group
            visited = [False] * len(code_blocks)
            
            # Mark blocks from other solutions as visited to exclude them
            for i in range(len(code_blocks)):
                if i not in block_indices:
                    visited[i] = True
            
            def dfs(node, current_group):
                visited[node] = True
                current_group.append(node)
                
                for neighbor in references[node]:
                    if not visited[neighbor]:
                        dfs(neighbor, current_group)
            
            # Find connected components within this solution
            for i in block_indices:
                if not visited[i]:
                    current_group = []
                    dfs(i, current_group)
                    final_groups.append(current_group)
        
        return final_groups
    
    def assemble_complete_solutions(self, code_blocks: List[Dict]) -> List[str]:
        """
        Assemble complete solutions from grouped code blocks.
        
        Args:
            code_blocks: List of code block dictionaries
            
        Returns:
            List of complete solution strings
        """
        # Group related blocks
        groups = self.group_related_blocks(code_blocks)
        
        # Assemble solutions from each group
        solutions = []
        
        for group in groups:
            # Sort blocks within group: classes first, then functions, then main
            sorted_group = sorted(group, key=lambda i: (
                0 if code_blocks[i]['type'] == 'class' else
                1 if code_blocks[i]['type'] == 'function' else
                2 if code_blocks[i]['type'] == 'namespace' else
                3  # main
            ))
            
            # Combine blocks into a single solution
            solution_parts = [code_blocks[i]['code'] for i in sorted_group]
            complete_solution = '\n\n'.join(solution_parts)
            
            if complete_solution.strip():
                solutions.append(complete_solution)
        
        return solutions
    
    def clean_code(self, code: str) -> str:
        """
        Clean extracted code by removing non-code elements.
        
        Args:
            code: Raw extracted code
            
        Returns:
            Cleaned code
        """
        # Remove page numbers and headers that might have been extracted
        code = re.sub(r'^\s*\d+\s*$', '', code, flags=re.MULTILINE)
        
        # Remove non-printable characters
        code = ''.join(c for c in code if c.isprintable() or c in '\n\t')
        
        # Remove trailing % character that sometimes appears in PDF extraction
        code = code.rstrip('%')
        
        # Fix indentation issues that might occur during PDF extraction
        lines = code.split('\n')
        cleaned_lines = []
        
        for line in lines:
            # Remove excessive whitespace but preserve indentation
            cleaned_line = re.sub(r'\s+', ' ', line.rstrip())
            cleaned_lines.append(cleaned_line)
        
        # Join lines back together
        cleaned_code = '\n'.join(cleaned_lines)
        
        # Check if the code looks reasonable (has proper structure)
        if cleaned_code and not re.match(r'^[{}\s]+$', cleaned_code):
            return cleaned_code
        return ""
    
    def process_pdf(self, pdf_path: str) -> str:
        """
        Process a PDF file and extract complete C++ code solutions.
        
        Args:
            pdf_path: Path to the PDF file
            
        Returns:
            Path to the output directory containing code solutions
        """
        # Create a directory for this PDF's code solutions
        pdf_name = os.path.splitext(os.path.basename(pdf_path))[0]
        output_dir = os.path.join(self.output_base_dir, pdf_name)
        os.makedirs(output_dir, exist_ok=True)
        
        # Extract text from PDF
        text = self.extract_text_from_pdf(pdf_path)
        
        # Extract code blocks
        code_blocks = self.extract_code_blocks(text)
        
        # Assemble complete solutions
        solutions = self.assemble_complete_solutions(code_blocks)
        
        # Save each solution to a separate file
        for i, solution in enumerate(solutions, 1):
            output_file = os.path.join(output_dir, f"solution{i}.txt")
            with open(output_file, 'w', encoding='utf-8') as f:
                f.write(solution)
        
        return output_dir
    
    def process_directory(self, pdf_dir: str) -> List[str]:
        """
        Process all PDF files in a directory.
        
        Args:
            pdf_dir: Directory containing PDF files
            
        Returns:
            List of output directory paths
        """
        output_dirs = []
        pdf_dir = Path(pdf_dir)
        
        for pdf_file in pdf_dir.glob("*.pdf"):
            try:
                output_dir = self.process_pdf(str(pdf_file))
                output_dirs.append(output_dir)
                print(f"Processed {pdf_file} -> {output_dir}")
            except Exception as e:
                print(f"Error processing {pdf_file}: {str(e)}")
                import traceback
                traceback.print_exc()
        
        return output_dirs

def main():
    """Main function to process PDFs."""
    import argparse
    
    parser = argparse.ArgumentParser(description="Process PDF assignments and extract complete C++ code solutions.")
    parser.add_argument("pdf_path", help="Path to PDF file or directory")
    parser.add_argument("--output", "-o", default="complete_output", help="Output directory")
    
    args = parser.parse_args()
    
    processor = CompleteSolutionExtractor(output_base_dir=args.output)
    
    if os.path.isfile(args.pdf_path):
        output_dir = processor.process_pdf(args.pdf_path)
        print(f"Extracted C++ code solutions saved to {output_dir}")
    else:
        output_dirs = processor.process_directory(args.pdf_path)
        print(f"Processed {len(output_dirs)} files")
        for out_dir in output_dirs:
            print(f"- {out_dir}")

if __name__ == "__main__":
    main() 