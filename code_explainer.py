import ast
import re
import json
from collections import defaultdict
import plotly.graph_objects as go

class ProCodeExplainer:
    def __init__(self):
        self.templates = {
            'FunctionDef': "Function '{name}' with params ({args}) -> {returns}. Complexity: O({complexity}). Purpose: {purpose}",
            'ClassDef': "Class '{name}' with {method_count} methods. Implements {concept}. Inheritance: {bases}",
            'For': "Loop over '{iterable}' using '{target}' - {type} iteration, {nested} nested level",
            'While': "While loop with condition '{condition}' - Potential infinite loop risk: {risk}",
            'If': "Conditional branching: if {condition} - Checks {check_type}",
            'Assign': "Variable '{target}' assigned value '{value}' | Type inferred: {dtype} | Scope: {scope}",
            'Call': "Function call '{func}' - Built-in: {is_builtin} | Args: {args}",
            'Import': "Import: {module} - Used for: {purpose}",
            'Try': "Exception handling block - Handles: {exceptions} - Robustness: High",
            'ListComp': "List comprehension - Optimized loop, faster than for-loop"
        }

        self.concept_map = {
            'np': 'Numerical Computing', 'pd': 'Data Processing', 'torch': 'Deep Learning',
            'tensorflow': 'Deep Learning', 'sklearn': 'Machine Learning', 'flask': 'Web Development',
            'django': 'Web Development', 'requests': 'API Calls', 'os': 'System Operations'
        }

    def analyze_python(self, code):
        try:
            tree = ast.parse(code)
            lines = code.split('\n')

            # Full analysis
            functions, classes, variables, imports, loops, conditions = [], [], [], [], [], []
            line_explanations = {}
            complexity = 1
            concepts = set()

            for node in ast.walk(tree):
                if isinstance(node, ast.FunctionDef):
                    args = [a.arg for a in node.args.args]
                    has_return = any(isinstance(n, ast.Return) for n in ast.walk(node))
                    purpose = self.guess_purpose(node.name)
                    func_data = {
                        'name': node.name,
                        'args': args,
                        'line': node.lineno,
                        'docstring': ast.get_docstring(node) or "No docstring",
                        'is_recursive': node.name in [n.func.id for n in ast.walk(node) if isinstance(n, ast.Call) and hasattr(n.func, 'id')],
                        'explanation': f"Function '{node.name}' takes {', '.join(args) or 'no args'} and returns {'value' if has_return else 'None'}. Purpose: {purpose}"
                    }
                    functions.append(func_data)
                    concepts.add('Function Definition')
                    complexity += 1

                elif isinstance(node, ast.ClassDef):
                    methods = [n.name for n in node.body if isinstance(n, ast.FunctionDef)]
                    bases = [ast.unparse(b) for b in node.bases] if node.bases else ['object']
                    classes.append({
                        'name': node.name,
                        'methods': methods,
                        'bases': bases,
                        'line': node.lineno,
                        'explanation': f"Class '{node.name}' defines {len(methods)} methods: {', '.join(methods)}. Inherits from {', '.join(bases)}"
                    })
                    concepts.add('OOP')

                elif isinstance(node, ast.Import):
                    for alias in node.names:
                        purpose = self.concept_map.get(alias.name.split('.')[0], 'General Utility')
                        imports.append({'module': alias.name, 'purpose': purpose, 'line': node.lineno})
                        concepts.add(f"Library: {purpose}")

                elif isinstance(node, ast.ImportFrom):
                    module = node.module or 'local'
                    purpose = self.concept_map.get(module.split('.')[0], 'General Utility')
                    imports.append({'module': f"{module}.{', '.join([n.name for n in node.names])}", 'purpose': purpose, 'line': node.lineno})

            # Line-by-line with real logic
            for i, line in enumerate(lines, 1):
                stripped = line.strip()
                if not stripped or stripped.startswith('#'):
                    continue
                if stripped.startswith('def '):
                    line_explanations[i] = f"Line {i}: Defines function - Entry point for reusable logic block"
                elif stripped.startswith('class '):
                    line_explanations[i] = f"Line {i}: Defines class blueprint for OOP structure"
                elif stripped.startswith('for '):
                    line_explanations[i] = f"Line {i}: Starts iteration - O(n) complexity loop"
                elif stripped.startswith('if '):
                    line_explanations[i] = f"Line {i}: Conditional check - Branching logic"
                elif '=' in stripped and not stripped.startswith(('if','for','while')):
                    var = stripped.split('=')[0].strip()
                    dtype = self.infer_type(stripped.split('=')[1])
                    line_explanations[i] = f"Line {i}: Assignment - Creates variable '{var}' of inferred type {dtype}"
                elif 'import ' in stripped:
                    line_explanations[i] = f"Line {i}: Imports dependency for external functionality"
                elif 'return ' in stripped:
                    line_explanations[i] = f"Line {i}: Returns result to caller - Function exit point"
                elif 'print(' in stripped:
                    line_explanations[i] = f"Line {i}: Output statement - Displays data for debugging"

            # Quality Assessment
            quality_score = 100
            issues = []
            if len(lines) > 50 and not any('"""' in l or "'''" in l for l in lines):
                quality_score -= 20
                issues.append("Missing docstrings")
            if any(len(l) > 100 for l in lines):
                quality_score -= 10
                issues.append("Long lines (>100 chars) - PEP8 violation")
            if len(functions) > 0 and not any(f['docstring']!= "No docstring" for f in functions):
                quality_score -= 15
                issues.append("Functions lack documentation")

            # Flow Diagram Data for Visual
            flow_nodes = []
            for f in functions:
                flow_nodes.append(f['name'])

            summary = f"This code has {len(functions)} function(s), {len(classes)} class(es), {len(imports)} import(s). Main purpose: {self.guess_overall_purpose(functions, classes, imports)}. Complexity Score: {complexity}. Maintainability: {'High' if quality_score > 80 else 'Medium'}"

            return {
                'summary': summary,
                'functions': functions,
                'classes': classes,
                'imports': imports,
                'line_explanations': line_explanations,
                'concepts': list(concepts),
                'quality_score': quality_score,
                'issues': issues,
                'complexity': complexity,
                'loc': len([l for l in lines if l.strip()]),
                'flow_nodes': flow_nodes
            }
        except SyntaxError as e:
            return {'error': f"Syntax Error at line {e.lineno}: {e.msg}"}
        except Exception as e:
            return {'error': str(e)}

    def infer_type(self, value_str):
        v = value_str.strip()
        if v.startswith('"') or v.startswith("'"): return "str"
        if v.startswith('['): return "list"
        if v.startswith('{'): return "dict"
        if v.startswith('('): return "tuple"
        if re.match(r'^\d+$', v): return "int"
        if re.match(r'^\d+\.\d+$', v): return "float"
        if 'pd.' in v or 'DataFrame' in v: return "DataFrame"
        if 'np.' in v: return "ndarray"
        return "unknown/object"

    def guess_purpose(self, name):
        name = name.lower()
        if 'clean' in name or 'process' in name: return "Data Cleaning"
        if 'train' in name or 'model' in name: return "ML Training"
        if 'calc' in name or 'compute' in name: return "Calculation"
        if 'get' in name or 'fetch' in name: return "Data Retrieval"
        if 'main' in name: return "Program Entry Point"
        return "General Utility"

    def guess_overall_purpose(self, funcs, classes, imports):
        mods = ' '.join([i['module'] for i in imports]).lower()
        if 'pandas' in mods or 'numpy' in mods: return "Data Analysis / Data Science"
        if 'flask' in mods or 'django' in mods: return "Web Application"
        if 'torch' in mods or 'tensorflow' in mods: return "Deep Learning Model"
        if len(classes) > 0: return "Object-Oriented Application"
        return "General Purpose Script"

    def explain_multi_language(self, code, lang):
        if lang == 'python':
            return self.analyze_python(code)
        elif lang in ['javascript', 'java', 'cpp']:
            # Basic heuristic for demo - Real-time multi-language
            return {
                'summary': f"{lang.upper()} code detected - {len(code.splitlines())} lines. Using heuristic analysis (Tree-sitter ready for production)",
                'functions': [{'name': m, 'explanation': f"Function {m} in {lang}"} for m in re.findall(r'function (\w+)|def (\w+)', code)][:5],
                'classes': [],
                'imports': [],
                'line_explanations': {i+1: f"Line {i+1}: {lang} statement" for i in range(min(5, len(code.splitlines())))},
                'concepts': [lang, 'Multi-language'],
                'quality_score': 75,
                'issues': [],
                'complexity': 2,
                'loc': len(code.splitlines()),
                'flow_nodes': []
            }
        else:
            return {'error': 'Language not supported'}