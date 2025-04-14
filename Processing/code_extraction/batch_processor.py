"""
Batch Processor for Multiple PDF Assignments

This module handles the processing of multiple PDF files and organizes
the extracted solutions for easy comparison between corresponding solutions.
"""

import os
import re
import shutil
from typing import List, Dict, Tuple
from pathlib import Path
from .complete_solution_extractor import CompleteSolutionExtractor

class BatchProcessor:
    """
    Processor for handling multiple PDF assignments.
    
    This class processes multiple PDF files, extracts C++ code solutions from each,
    and organizes them to facilitate comparison between corresponding solutions.
    """
    
    def __init__(self, output_base_dir: str = "batch_output"):
        """
        Initialize the batch processor.
        
        Args:
            output_base_dir: Base directory to save organized solutions
        """
        self.output_base_dir = output_base_dir
        
        # Create base output directory if it doesn't exist
        os.makedirs(output_base_dir, exist_ok=True)
        
        # Create subdirectories for raw solutions and organized solutions
        self.raw_dir = os.path.join(output_base_dir, "raw")
        self.organized_dir = os.path.join(output_base_dir, "organized")
        
        os.makedirs(self.raw_dir, exist_ok=True)
        os.makedirs(self.organized_dir, exist_ok=True)
        
        # Initialize solution extractor
        self.extractor = CompleteSolutionExtractor(output_base_dir=self.raw_dir)
    
    def extract_solutions_from_pdfs(self, pdf_files: List[str]) -> Dict[str, str]:
        """
        Extract solutions from multiple PDF files.
        
        Args:
            pdf_files: List of paths to PDF files
            
        Returns:
            Dictionary mapping PDF names to their output directories
        """
        pdf_outputs = {}
        
        for pdf_path in pdf_files:
            try:
                # Get the PDF name without extension
                pdf_name = os.path.splitext(os.path.basename(pdf_path))[0]
                print(f"Processing {pdf_name}...")
                
                # Process the PDF and get the output directory
                output_dir = self.extractor.process_pdf(pdf_path)
                pdf_outputs[pdf_name] = output_dir
                
                print(f"  → Extracted solutions saved to {output_dir}")
            except Exception as e:
                print(f"Error processing {pdf_path}: {str(e)}")
                import traceback
                traceback.print_exc()
        
        return pdf_outputs
    
    def analyze_solution_file(self, solution_path: str) -> Dict:
        """
        Analyze a solution file to extract its characteristics.
        
        Args:
            solution_path: Path to the solution file
            
        Returns:
            Dictionary with solution characteristics
        """
        with open(solution_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Extract basic metrics
        lines = content.count('\n') + 1
        size = len(content)
        
        # Extract code characteristics
        contains_class = "class" in content or "struct" in content
        contains_main = "int main" in content
        
        # Count structures
        class_count = len(re.findall(r'class\s+\w+|struct\s+\w+', content))
        function_count = len(re.findall(r'(?:void|int|char|float|double|bool|unsigned|long|short|auto|string)\s+\w+\s*\(', content))
        
        # Extract class names
        class_names = re.findall(r'class\s+(\w+)|struct\s+(\w+)', content)
        class_names = [name[0] or name[1] for name in class_names]
        
        return {
            'content': content,
            'lines': lines,
            'size': size,
            'contains_class': contains_class,
            'contains_main': contains_main,
            'class_count': class_count,
            'function_count': function_count,
            'class_names': class_names,
            'path': solution_path
        }
    
    def collect_solutions_info(self, pdf_outputs: Dict[str, str]) -> Dict[str, List[Dict]]:
        """
        Collect information about all extracted solutions.
        
        Args:
            pdf_outputs: Dictionary mapping PDF names to their output directories
            
        Returns:
            Dictionary mapping PDF names to lists of solution information
        """
        all_solutions = {}
        
        for pdf_name, output_dir in pdf_outputs.items():
            solution_files = sorted([
                f for f in os.listdir(output_dir) 
                if f.startswith("solution") and f.endswith(".txt")
            ])
            
            solutions_info = []
            
            for solution_file in solution_files:
                solution_path = os.path.join(output_dir, solution_file)
                solution_info = self.analyze_solution_file(solution_path)
                
                # Extract solution number
                solution_num = int(solution_file.replace("solution", "").replace(".txt", ""))
                solution_info['solution_num'] = solution_num
                
                solutions_info.append(solution_info)
            
            all_solutions[pdf_name] = solutions_info
        
        return all_solutions
    
    def organize_solutions(self, all_solutions: Dict[str, List[Dict]]) -> Dict[int, Dict[str, str]]:
        """
        Organize solutions for comparison.
        
        Args:
            all_solutions: Dictionary mapping PDF names to lists of solution information
            
        Returns:
            Dictionary mapping solution numbers to dictionaries mapping PDF names to solution paths
        """
        # Create a mapping from solution number to dictionary of {pdf_name: solution_path}
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
            
            # Copy solutions to organized directory with unique names
            for pdf_name, solution_path in pdf_solutions.items():
                # Create a unique filename that includes both student name and solution number
                unique_filename = f"{pdf_name}_sol{solution_num}.txt"
                target_path = os.path.join(solution_dir, unique_filename)
                shutil.copy(solution_path, target_path)
        
        return organized_solutions
    
    def process_pdfs(self, pdf_files: List[str]) -> Dict[int, Dict[str, str]]:
        """
        Process multiple PDF files and organize solutions for comparison.
        
        Args:
            pdf_files: List of paths to PDF files
            
        Returns:
            Dictionary mapping solution numbers to dictionaries mapping PDF names to solution paths
        """
        print(f"Processing {len(pdf_files)} PDF files...")
        
        # Extract solutions from PDFs
        pdf_outputs = self.extract_solutions_from_pdfs(pdf_files)
        
        # Collect information about all solutions
        all_solutions = self.collect_solutions_info(pdf_outputs)
        
        # Organize solutions for comparison
        organized_solutions = self.organize_solutions(all_solutions)
        
        # Generate summary
        print("\nOrganized Solutions Summary:")
        for solution_num, pdf_solutions in organized_solutions.items():
            print(f"  Solution {solution_num}: {len(pdf_solutions)} implementations")
            for pdf_name in pdf_solutions.keys():
                print(f"    - {pdf_name}")
        
        print(f"\nSolutions organized in: {self.organized_dir}")
        
        return organized_solutions
    
    def process_directory(self, pdf_dir: str) -> Dict[int, Dict[str, str]]:
        """
        Process all PDF files in a directory.
        
        Args:
            pdf_dir: Directory containing PDF files
            
        Returns:
            Dictionary mapping solution numbers to dictionaries mapping PDF names to solution paths
        """
        pdf_files = [
            str(path) for path in Path(pdf_dir).glob("*.pdf")
        ]
        
        if not pdf_files:
            print(f"No PDF files found in {pdf_dir}")
            return {}
        
        return self.process_pdfs(pdf_files)

def main():
    """Main function to process multiple PDFs."""
    import argparse
    
    parser = argparse.ArgumentParser(description="Process multiple PDF assignments and organize solutions for comparison.")
    parser.add_argument("input", help="Path to PDF file, directory, or comma-separated list of PDF files")
    parser.add_argument("--output", "-o", default="batch_output", help="Output directory")
    
    args = parser.parse_args()
    
    processor = BatchProcessor(output_base_dir=args.output)
    
    if os.path.isdir(args.input):
        # Process all PDFs in a directory
        processor.process_directory(args.input)
    elif ',' in args.input:
        # Process comma-separated list of PDF files
        pdf_files = [file.strip() for file in args.input.split(',')]
        processor.process_pdfs(pdf_files)
    elif os.path.isfile(args.input):
        # Process a single PDF file
        processor.process_pdfs([args.input])
    else:
        print(f"Input not recognized: {args.input}")
        return 1
    
    return 0

if __name__ == "__main__":
    main() 