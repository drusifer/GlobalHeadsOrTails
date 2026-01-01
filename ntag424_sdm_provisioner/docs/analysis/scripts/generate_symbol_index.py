import os
import ast
from pathlib import Path

def get_docstring(node):
    """Extract docstring from AST node."""
    if (isinstance(node, (ast.FunctionDef, ast.ClassDef, ast.Module)) and 
        node.body and 
        isinstance(node.body[0], ast.Expr) and 
        isinstance(node.body[0].value, ast.Constant) and 
        isinstance(node.body[0].value.value, str)):
        return node.body[0].value.value
    return None

def get_symbols(file_path):
    with open(file_path, "r", encoding="utf-8") as f:
        try:
            source = f.read()
            tree = ast.parse(source, filename=file_path)
        except SyntaxError:
            return []

    symbols = []
    for node in tree.body:
        if isinstance(node, ast.ClassDef):
            class_docstring = get_docstring(node)
            methods = []
            for n in node.body:
                if isinstance(n, ast.FunctionDef):
                    method_docstring = get_docstring(n)
                    methods.append({
                        "name": n.name,
                        "lineno": n.lineno,
                        "docstring": method_docstring
                    })
            symbols.append({
                "type": "class",
                "name": node.name,
                "lineno": node.lineno,
                "docstring": class_docstring,
                "methods": methods
            })
        elif isinstance(node, ast.FunctionDef):
            func_docstring = get_docstring(node)
            symbols.append({
                "type": "function",
                "name": node.name,
                "lineno": node.lineno,
                "docstring": func_docstring
            })
    return symbols

def generate_index(root_dir, output_file):
    root_path = Path(root_dir)
    lines = [
        "# Codebase Symbol Index\n",
        "\nThis document lists all classes and functions in the `src/` directory with line numbers and docstrings.\n",
        "Generated via AST parsing for easy code navigation.\n"
    ]
    
    files = sorted(root_path.rglob("*.py"))
    
    for file_path in files:
        if "__init__.py" in file_path.name:
            continue
            
        rel_path = file_path.relative_to(root_path.parent).as_posix()
        symbols = get_symbols(file_path)
        
        if not symbols:
            continue
            
        lines.append(f"\n## `{rel_path}`")
        for sym in symbols:
            if sym["type"] == "class":
                lines.append(f"- `class {sym['name']}` (Line {sym['lineno']})")
                if sym["docstring"]:
                    # Format docstring as indented quote
                    doclines = sym["docstring"].strip().split('\n')
                    lines.append(f"  > {doclines[0]}")
                    for docline in doclines[1:]:
                        if docline.strip():
                            lines.append(f"  > {docline.strip()}")
                for method in sym["methods"]:
                    lines.append(f"    - `def {method['name']}` (Line {method['lineno']})")
                    if method["docstring"]:
                        # Format method docstring
                        doc_first = method["docstring"].strip().split('\n')[0]
                        lines.append(f"      > {doc_first}")
            elif sym["type"] == "function":
                lines.append(f"- `def {sym['name']}` (Line {sym['lineno']})")
                if sym["docstring"]:
                    doc_first = sym["docstring"].strip().split('\n')[0]
                    lines.append(f"  > {doc_first}")

    with open(output_file, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))
    print(f"Index generated at {output_file}")

if __name__ == "__main__":
    generate_index("src", "docs/SYMBOL_INDEX.md")
