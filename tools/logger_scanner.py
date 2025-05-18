#!/usr/bin/env python3
"""
Logger Scanner - Analyzes Python files for non-compliant logger usage patterns

This tool scans the entire codebase to identify:
1. Direct get_logger() calls that should use get_logger()
2. Custom handler setup that bypasses centralized configuration
3. Local variable shadowing that could cause UnboundLocalError
4. Wildcard imports that might pull in logging functions
"""

import ast
import os
import sys
import csv
from pathlib import Path
from typing import Dict, List, Tuple, Set, Optional, Any

class LoggerVisitor(ast.NodeVisitor):
    """AST visitor that tracks logger initialization and usage patterns."""
    
    def __init__(self, filename: str):
        self.filename = filename
        self.direct_getlogger_calls = []  # logging.getLogger calls
        self.custom_getlogger_calls = []  # get_logger calls
        self.logger_assignments = []      # logger = x assignments
        self.logger_usages = []           # logger.x() calls
        self.logger_shadowing = []        # Function-level logger assignments that shadow module loggers
        self.handler_additions = []       # .addHandler calls
        self.wildcard_imports = []        # from x import *
        self.current_function = None
        self.module_loggers = set()       # Module-level logger variables
        self.current_class = None
        
    def visit_ClassDef(self, node):
        old_class = self.current_class
        self.current_class = node.name
        self.generic_visit(node)
        self.current_class = old_class
        
    def visit_FunctionDef(self, node):
        old_function = self.current_function
        self.current_function = node.name
        self.generic_visit(node)
        self.current_function = old_function
        
    def visit_AsyncFunctionDef(self, node):
        old_function = self.current_function
        self.current_function = node.name
        self.generic_visit(node)
        self.current_function = old_function
        
    def visit_ImportFrom(self, node):
        # Check for wildcard imports
        if any(name.name == '*' for name in node.names):
            self.wildcard_imports.append((
                node.lineno, 
                f"from {node.module} import *",
                self.current_function or self.current_class or "module"
            ))
        
        self.generic_visit(node)
        
    def visit_Call(self, node):
        # Check for logging.getLogger calls
        if (isinstance(node.func, ast.Attribute) and 
            isinstance(node.func.value, ast.Name) and
            node.func.value.id == 'logging' and 
            node.func.attr == 'getLogger'):
            
            # Extract the argument if available
            logger_name = None
            if node.args:
                if isinstance(node.args[0], ast.Name):
                    logger_name = node.args[0].id
                elif isinstance(node.args[0], ast.Constant):
                    logger_name = node.args[0].value
                    
            self.direct_getlogger_calls.append((
                node.lineno, 
                logger_name, 
                self.current_function or self.current_class or "module"
            ))
            
        # Check for get_logger calls
        elif (isinstance(node.func, ast.Name) and 
              node.func.id == 'get_logger'):
            
            # Extract the argument if available
            logger_name = None
            if node.args:
                if isinstance(node.args[0], ast.Name):
                    logger_name = node.args[0].id
                elif isinstance(node.args[0], ast.Constant):
                    logger_name = node.args[0].value
                    
            self.custom_getlogger_calls.append((
                node.lineno, 
                logger_name, 
                self.current_function or self.current_class or "module"
            ))
            
        # Check for logger usages (logger.info, logger.debug, etc.)
        elif (isinstance(node.func, ast.Attribute) and 
              isinstance(node.func.value, ast.Name) and
              node.func.value.id == 'logger'):
            
            self.logger_usages.append((
                node.lineno, 
                self.current_function or self.current_class or "module", 
                node.func.attr
            ))
            
        # Check for addHandler calls
        elif (isinstance(node.func, ast.Attribute) and 
              node.func.attr == 'addHandler'):
            
            target_name = None
            if isinstance(node.func.value, ast.Name):
                target_name = node.func.value.id
                
            self.handler_additions.append((
                node.lineno, 
                target_name,
                self.current_function or self.current_class or "module"
            ))
            
        self.generic_visit(node)
        
    def visit_Assign(self, node):
        # Check for logger assignments
        for target in node.targets:
            if isinstance(target, ast.Name) and target.id == 'logger':
                if self.current_function:
                    # Check if this shadows a module-level logger
                    if 'logger' in self.module_loggers:
                        self.logger_shadowing.append((
                            target.lineno, 
                            self.current_function
                        ))
                else:
                    # This is a module-level logger assignment
                    self.module_loggers.add('logger')
                
                self.logger_assignments.append((
                    target.lineno, 
                    self.current_function or self.current_class or "module"
                ))
        
        self.generic_visit(node)

def analyze_file(file_path: str) -> Dict:
    """Analyze a Python file for logger usage."""
    with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
        try:
            source = f.read()
            tree = ast.parse(source)
            visitor = LoggerVisitor(file_path)
            visitor.visit(tree)
            
            return {
                'file': file_path,
                'direct_getlogger_calls': visitor.direct_getlogger_calls,
                'custom_getlogger_calls': visitor.custom_getlogger_calls,
                'logger_assignments': visitor.logger_assignments,
                'logger_usages': visitor.logger_usages,
                'logger_shadowing': visitor.logger_shadowing,
                'handler_additions': visitor.handler_additions,
                'wildcard_imports': visitor.wildcard_imports,
                'module_loggers': list(visitor.module_loggers)
            }
        except SyntaxError as e:
            return {
                'file': file_path,
                'error': f"Syntax error: {str(e)}"
            }
        except Exception as e:
            return {
                'file': file_path,
                'error': f"Error analyzing file: {str(e)}"
            }

def find_python_files(start_dir: str) -> List[str]:
    """Find all Python files in a directory structure."""
    python_files = []
    for root, _, files in os.walk(start_dir):
        # Skip virtual environment directories
        if 'sports_venv' in root.split(os.path.sep):
            continue
            
        # Skip __pycache__ directories
        if '__pycache__' in root.split(os.path.sep):
            continue
            
        for file in files:
            if file.endswith('.py'):
                python_files.append(os.path.join(root, file))
    return python_files

def export_to_csv(results: List[Dict], output_file: str):
    """Export analysis results to CSV for easy viewing."""
    with open(output_file, 'w', newline='') as f:
        writer = csv.writer(f)
        writer.writerow(['File', 'Issue Type', 'Line', 'Context', 'Details'])
        
        for result in results:
            file_path = result['file']
            
            # Write direct getLogger calls
            for line, name, context in result.get('direct_getlogger_calls', []):
                writer.writerow([
                    file_path, 
                    'Direct logging.getLogger', 
                    line, 
                    context, 
                    f'name="{name}"'
                ])
                
            # Write handler additions
            for line, target, context in result.get('handler_additions', []):
                writer.writerow([
                    file_path, 
                    'Custom Handler Setup', 
                    line, 
                    context, 
                    f'target="{target}"'
                ])
                
            # Write logger shadowing
            for line, func in result.get('logger_shadowing', []):
                writer.writerow([
                    file_path, 
                    'Logger Shadowing', 
                    line, 
                    func, 
                    'Shadows module-level logger'
                ])
                
            # Write wildcard imports
            for line, import_stmt, context in result.get('wildcard_imports', []):
                writer.writerow([
                    file_path, 
                    'Wildcard Import', 
                    line, 
                    context, 
                    import_stmt
                ])

def generate_report(results: List[Dict]) -> str:
    """Generate a human-readable report of the analysis results."""
    report = []
    report.append("# Logger Usage Analysis Report")
    report.append(f"Generated on: {__import__('datetime').datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    report.append(f"Total files analyzed: {len(results)}")
    
    # Count issues
    direct_calls = sum(len(r.get('direct_getlogger_calls', [])) for r in results)
    custom_calls = sum(len(r.get('custom_getlogger_calls', [])) for r in results)
    shadowing = sum(len(r.get('logger_shadowing', [])) for r in results)
    handler_adds = sum(len(r.get('handler_additions', [])) for r in results)
    wildcard_imports = sum(len(r.get('wildcard_imports', [])) for r in results)
    
    report.append("\n## Summary")
    report.append(f"- Direct logging.getLogger calls: {direct_calls}")
    report.append(f"- Custom get_logger calls: {custom_calls}")
    report.append(f"- Logger variable shadowing: {shadowing}")
    report.append(f"- Custom handler setup: {handler_adds}")
    report.append(f"- Wildcard imports: {wildcard_imports}")
    
    # Report files with issues
    if direct_calls > 0:
        report.append("\n## Files with Direct logging.getLogger Calls")
        for result in results:
            calls = result.get('direct_getlogger_calls', [])
            if calls:
                report.append(f"\n### {result['file']}")
                for line, name, context in calls:
                    context_str = f" in {context}" if context != "module" else " at module level"
                    report.append(f"- Line {line}{context_str}: get_logger({name})")
    
    if shadowing > 0:
        report.append("\n## Files with Logger Shadowing")
        for result in results:
            shadows = result.get('logger_shadowing', [])
            if shadows:
                report.append(f"\n### {result['file']}")
                for line, func in shadows:
                    report.append(f"- Line {line} in function {func}: shadows module-level logger")
    
    if handler_adds > 0:
        report.append("\n## Files with Custom Handler Setup")
        for result in results:
            handlers = result.get('handler_additions', [])
            if handlers:
                report.append(f"\n### {result['file']}")
                for line, target, context in handlers:
                    context_str = f" in {context}" if context != "module" else " at module level"
                    report.append(f"- Line {line}{context_str}: {target}.addHandler()")
    
    return "\n".join(report)

def main():
    """Main function to analyze logger usage in Python files."""
    # Ensure tools directory exists
    Path(__file__).parent.mkdir(exist_ok=True)
    
    # Use current directory if no argument is provided
    start_dir = sys.argv[1] if len(sys.argv) > 1 else '.'
    
    print(f"Analyzing Python files in {start_dir} for logger usage...")
    
    # Find all Python files
    python_files = find_python_files(start_dir)
    print(f"Found {len(python_files)} Python files")
    
    # Analyze each file
    results = []
    for file_path in python_files:
        results.append(analyze_file(file_path))
    
    # Export results to CSV
    output_csv = os.path.join(Path(__file__).parent, 'logger_issues.csv')
    export_to_csv(results, output_csv)
    print(f"Exported issues to {output_csv}")
    
    # Generate report
    report = generate_report(results)
    report_path = os.path.join(Path(__file__).parent, 'logger_report.md')
    with open(report_path, 'w') as f:
        f.write(report)
    print(f"Generated report at {report_path}")
    
    # Print summary to console
    print("\nSummary of logger usage issues:")
    direct_calls = sum(len(r.get('direct_getlogger_calls', [])) for r in results)
    shadowing = sum(len(r.get('logger_shadowing', [])) for r in results)
    handler_adds = sum(len(r.get('handler_additions', [])) for r in results)
    print(f"- Direct logging.getLogger calls: {direct_calls}")
    print(f"- Logger variable shadowing: {shadowing}")
    print(f"- Custom handler setup: {handler_adds}")
    
    # List files that need the most attention (most issues)
    print("\nFiles needing most attention:")
    file_issues = []
    for result in results:
        issues = (
            len(result.get('direct_getlogger_calls', [])) +
            len(result.get('logger_shadowing', [])) +
            len(result.get('handler_additions', []))
        )
        if issues > 0:
            file_issues.append((result['file'], issues))
    
    # Sort by issue count and print top 5
    for file_path, count in sorted(file_issues, key=lambda x: x[1], reverse=True)[:5]:
        print(f"- {file_path}: {count} issues")

if __name__ == "__main__":
    main()
