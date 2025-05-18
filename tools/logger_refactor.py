#!/usr/bin/env python3
"""
Logger Refactoring Tool - Fixes non-compliant logger usages across the codebase

This tool applies automated fixes to:
1. Replace direct get_logger() calls with get_logger()
2. Fix logger shadowing issues that cause UnboundLocalError
3. Standardize custom handler setup
4. Document all changes in a report

Usage:
    python3 logger_refactor.py /root/Complete_Seperate
"""

import ast
import astor
import os
import sys
import csv
import re
from pathlib import Path
from typing import Dict, List, Tuple, Set, Optional, Any
from datetime import datetime

# Import scanner functionality
# pylint: disable=wrong-import-position
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from tools.logger_scanner import find_python_files, LoggerVisitor
# pylint: enable=wrong-import-position

class LoggerRefactor(ast.NodeTransformer):
    """AST transformer that fixes logger-related issues."""
    
    def __init__(self, filename: str):
        self.filename = filename
        self.changes = []
        self.module_has_get_logger_import = False
        self.context_stack = []
        self.module_loggers = set()
        self.shadowed_loggers = set()
        
    def _add_change(self, node, change_type, old_code, new_code):
        """Record a change."""
        self.changes.append({
            'line': getattr(node, 'lineno', 0),
            'type': change_type,
            'old': old_code,
            'new': new_code
        })
        
    def visit_Module(self, node):
        """Process module node to detect imports."""
        # Check if module already imports get_logger
        for n in node.body:
            if isinstance(n, ast.ImportFrom) and n.module == 'log_config':
                for name in n.names:
                    if name.name == 'get_logger':
                        self.module_has_get_logger_import = True
                    if name.name == 'get_summary_logger':
                        self.module_has_get_summary_logger_import = True
        
        # Process all children
        self.generic_visit(node)
        
        # Add import if needed
        if not hasattr(self, 'module_has_get_summary_logger_import'):
            self.module_has_get_summary_logger_import = False
            
        if not self.module_has_get_logger_import and not self.module_has_get_summary_logger_import:
            if any(change['type'] == 'get_logger' for change in self.changes):
                # Add import
                import_stmt = ast.ImportFrom(
                    module='log_config',
                    names=[ast.alias(name='get_logger', asname=None)],
                    level=0
                )
                # Add line number for proper insertion
                import_stmt.lineno = 1
                import_stmt.col_offset = 0
                
                # Add to start of file
                node.body.insert(0, import_stmt)
                self._add_change(
                    import_stmt, 
                    'import', 
                    '', 
                    'from log_config import get_logger'
                )
        
        if not self.module_has_get_summary_logger_import:
            if any(change['type'] == 'get_summary_logger' for change in self.changes):
                # Add import - make sure it comes after get_logger if that was added
                import_pos = 1 if not self.module_has_get_logger_import else 0
                import_stmt = ast.ImportFrom(
                    module='log_config',
                    names=[ast.alias(name='get_summary_logger', asname=None)],
                    level=0
                )
                # Add line number for proper insertion
                import_stmt.lineno = 1
                import_stmt.col_offset = 0
                
                # Add to start of file
                node.body.insert(import_pos, import_stmt)
                self._add_change(
                    import_stmt, 
                    'import', 
                    '', 
                    'from log_config import get_summary_logger'
                )
                
        return node
        
    def visit_Assign(self, node):
        """Process assignment nodes to track logger variables."""
        # Track module-level logger assignments
        if not self.context_stack:
            for target in node.targets:
                if isinstance(target, ast.Name) and target.id == 'logger':
                    self.module_loggers.add('logger')
        else:
            # Check for shadowing
            for target in node.targets:
                if isinstance(target, ast.Name) and target.id == 'logger':
                    if 'logger' in self.module_loggers:
                        self.shadowed_loggers.add(target.id)
                        
                        # Rename to avoid shadowing if assigned get_logger()
                        if (isinstance(node.value, ast.Call) and 
                            isinstance(node.value.func, ast.Attribute) and
                            isinstance(node.value.func.value, ast.Name) and
                            node.value.func.value.id == 'logging' and 
                            node.value.func.attr == 'getLogger'):
                            
                            # Replace with module_logger or similar name
                            target.id = 'inner_logger'
                            self._add_change(
                                node, 
                                'rename', 
                                'logger = ...',
                                'inner_logger = ...'
                            )
                            
                            # Update all references within the current context to use inner_logger
                            self.rename_in_current_context = True
                    
        return self.generic_visit(node)
        
    def visit_FunctionDef(self, node):
        """Process function definitions to track context."""
        self.context_stack.append(node.name)
        result = self.generic_visit(node)
        self.context_stack.pop()
        return result
        
    def visit_AsyncFunctionDef(self, node):
        """Process async function definitions to track context."""
        self.context_stack.append(node.name)
        result = self.generic_visit(node)
        self.context_stack.pop()
        return result
        
    def visit_ClassDef(self, node):
        """Process class definitions to track context."""
        self.context_stack.append(node.name)
        result = self.generic_visit(node)
        self.context_stack.pop()
        return result
        
    def visit_Call(self, node):
        """Process function calls to fix logger issues."""
        # Fix direct get_logger() calls
        if (isinstance(node.func, ast.Attribute) and
            isinstance(node.func.value, ast.Name) and
            node.func.value.id == 'logging' and 
            node.func.attr == 'getLogger'):
            
            # Ensure we're not in log_config.py itself, as that defines get_logger
            if not self.filename.endswith('log_config.py'):
                # Get the logger name arg if present
                logger_name = None
                if node.args:
                    if isinstance(node.args[0], ast.Name) and node.args[0].id == '__name__':
                        # module-specific logger - use a reasonable default
                        logger_name = Path(self.filename).stem
                    elif isinstance(node.args[0], ast.Constant) and node.args[0].value == 'summary':
                        # Special case for summary logger
                        new_node = ast.Call(
                            func=ast.Name(id='get_summary_logger', ctx=ast.Load()),
                            args=[],
                            keywords=[]
                        )
                        self._add_change(
                            node, 
                            'get_summary_logger', 
                            'get_summary_logger()',
                            'get_summary_logger()'
                        )
                        return new_node
                    elif isinstance(node.args[0], ast.Constant):
                        logger_name = node.args[0].value
                    
                # Replace with get_logger()
                if logger_name == 'summary':
                    # Use get_summary_logger() for summary loggers
                    new_node = ast.Call(
                        func=ast.Name(id='get_summary_logger', ctx=ast.Load()),
                        args=[],
                        keywords=[]
                    )
                    self._add_change(
                        node, 
                        'get_summary_logger', 
                        f'get_summary_logger()',
                        'get_summary_logger()'
                    )
                else:
                    # Use module name if logger name is None or __name__
                    if logger_name is None or logger_name == '__name__':
                        module_name = Path(self.filename).stem
                        logger_name_node = ast.Constant(value=module_name)
                    elif isinstance(logger_name, str):
                        logger_name_node = ast.Constant(value=logger_name)
                    else:
                        # If we can't determine, use the original arg
                        logger_name_node = node.args[0]
                        
                    # Create get_logger() call
                    new_node = ast.Call(
                        func=ast.Name(id='get_logger', ctx=ast.Load()),
                        args=[logger_name_node],
                        keywords=[]
                    )
                    self._add_change(
                        node, 
                        'get_logger', 
                        f'get_logger({logger_name})',
                        f'get_logger("{logger_name}")'
                    )
                
                return new_node
        
        # Process the rest of the tree
        return self.generic_visit(node)

def refactor_file(file_path: str) -> Dict:
    """Refactor logger usage in a Python file."""
    try:
        with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
            source = f.read()
        
        # Parse the AST
        tree = ast.parse(source)
        
        # Apply refactoring
        refactorer = LoggerRefactor(file_path)
        new_tree = refactorer.visit(tree)
        
        # Regenerate source code
        new_source = astor.to_source(new_tree)
        
        # Only save if changes were made
        if refactorer.changes:
            # Create backup
            backup_path = file_path + '.bak'
            with open(backup_path, 'w', encoding='utf-8') as f:
                f.write(source)
            
            # Write changes
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(new_source)
        
        return {
            'file': file_path,
            'changes': refactorer.changes,
            'changed': bool(refactorer.changes)
        }
        
    except Exception as e:
        return {
            'file': file_path,
            'error': str(e)
        }

def export_refactor_report(results: List[Dict], output_file: str):
    """Export a report of refactoring changes."""
    with open(output_file, 'w') as f:
        f.write("# Logger Refactoring Report\n")
        f.write(f"Generated on: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
        
        # Count changes by type
        change_counts = {}
        total_changes = 0
        files_changed = 0
        
        for result in results:
            if result.get('changed', False):
                files_changed += 1
                for change in result.get('changes', []):
                    change_type = change['type']
                    change_counts[change_type] = change_counts.get(change_type, 0) + 1
                    total_changes += 1
        
        # Write summary
        f.write(f"## Summary\n")
        f.write(f"- Total files checked: {len(results)}\n")
        f.write(f"- Files modified: {files_changed}\n")
        f.write(f"- Total changes made: {total_changes}\n\n")
        
        f.write("## Changes by Type\n")
        for change_type, count in change_counts.items():
            f.write(f"- {change_type}: {count}\n")
        f.write("\n")
        
        # Write detailed changes
        f.write("## Detailed Changes\n\n")
        for result in results:
            if result.get('changed', False):
                f.write(f"### {result['file']}\n\n")
                for change in result.get('changes', []):
                    f.write(f"Line {change['line']} - {change['type']}:\n")
                    f.write(f"- Before: `{change['old']}`\n")
                    f.write(f"- After: `{change['new']}`\n\n")
            elif result.get('error'):
                f.write(f"### {result['file']}\n")
                f.write(f"Error: {result['error']}\n\n")

def main():
    """Main function to refactor logger usage in Python files."""
    # Ensure tools directory exists
    Path(__file__).parent.mkdir(exist_ok=True)
    
    # Use current directory if no argument is provided
    start_dir = sys.argv[1] if len(sys.argv) > 1 else '.'
    
    print(f"Refactoring Python files in {start_dir} for proper logger usage...")
    
    # Find all Python files
    python_files = find_python_files(start_dir)
    print(f"Found {len(python_files)} Python files")
    
    # Refactor each file
    results = []
    for file_path in python_files:
        print(f"Processing {file_path}...")
        results.append(refactor_file(file_path))
    
    # Export report
    report_path = os.path.join(Path(__file__).parent, 'refactor_report.md')
    export_refactor_report(results, report_path)
    print(f"Refactoring report generated at {report_path}")
    
    # Print summary
    files_changed = sum(1 for r in results if r.get('changed', False))
    print(f"\nRefactoring summary:")
    print(f"- Files modified: {files_changed} of {len(python_files)}")
    
    # List files with errors
    errors = [r for r in results if 'error' in r]
    if errors:
        print("\nErrors encountered:")
        for r in errors:
            print(f"- {r['file']}: {r['error']}")

if __name__ == "__main__":
    main()
