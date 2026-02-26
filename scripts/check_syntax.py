import os
import ast

def check_syntax(directory="."):
    print(f"Checking syntax for Python files in {directory}...")
    errors = 0
    checked = 0
    
    for root, _, files in os.walk(directory):
        if "venv" in root or ".git" in root or "__pycache__" in root:
            continue
            
        for file in files:
            if file.endswith(".py"):
                checked += 1
                path = os.path.join(root, file)
                try:
                    with open(path, "r", encoding="utf-8") as f:
                        source = f.read()
                    ast.parse(source)
                except SyntaxError as e:
                    print(f"❌ Syntax Error in {path}: {e}")
                    errors += 1
                except Exception as e:
                    print(f"⚠️ Could not read/parse {path}: {e}")
                    errors += 1
                    
    print(f"\nChecked {checked} files.")
    if errors == 0:
        print("✅ No syntax errors found.")
    else:
        print(f"❌ Found {errors} errors.")

if __name__ == "__main__":
    check_syntax()
