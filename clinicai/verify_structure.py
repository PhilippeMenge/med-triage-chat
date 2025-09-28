#!/usr/bin/env python3
"""
Structure verification script for ClinicAI.
Verifies that all files and directories are in place.
"""

import os
from pathlib import Path

def verify_project_structure():
    """Verify that all required files and directories exist."""
    print("🏥 ClinicAI Project Structure Verification")
    print("=" * 50)
    
    required_files = [
        "pyproject.toml",
        "requirements.txt",
        "Dockerfile",
        "docker-compose.yml",
        "Makefile",
        "README.md",
        "init-mongo.js",
        "env.example",
        "app/__init__.py",
        "app/main.py",
        "app/config.py",
        "app/schemas.py",
        "app/db.py",
        "app/whatsapp.py",
        "app/llm.py",
        "app/graph/__init__.py",
        "app/graph/state.py",
        "app/graph/nodes.py",
        "app/graph/prompts.py",
        "app/graph/workflow.py",
        "app/utils/__init__.py",
        "app/utils/security.py",
        "app/utils/emergency.py",
        "app/utils/logging.py",
        "tests/__init__.py",
        "tests/test_emergency.py",
        "tests/test_extraction.py",
        "tests/test_webhook.py",
    ]
    
    required_dirs = [
        "app",
        "app/graph",
        "app/utils",
        "tests",
    ]
    
    missing_files = []
    missing_dirs = []
    
    # Check directories
    for dir_path in required_dirs:
        if not Path(dir_path).is_dir():
            missing_dirs.append(dir_path)
        else:
            print(f"✅ Directory: {dir_path}")
    
    # Check files
    for file_path in required_files:
        if not Path(file_path).is_file():
            missing_files.append(file_path)
        else:
            print(f"✅ File: {file_path}")
    
    # Report results
    print("\n" + "=" * 50)
    
    if missing_dirs:
        print("❌ Missing directories:")
        for dir_path in missing_dirs:
            print(f"   - {dir_path}")
    
    if missing_files:
        print("❌ Missing files:")
        for file_path in missing_files:
            print(f"   - {file_path}")
    
    if not missing_files and not missing_dirs:
        print("🎉 All required files and directories are present!")
        print("\n📋 Project Statistics:")
        
        # Count Python files
        py_files = list(Path(".").rglob("*.py"))
        print(f"   - Python files: {len(py_files)}")
        
        # Count lines of code
        total_lines = 0
        for py_file in py_files:
            try:
                with open(py_file, 'r', encoding='utf-8') as f:
                    total_lines += len(f.readlines())
            except:
                pass
        
        print(f"   - Total lines of code: {total_lines}")
        
        print("\n🚀 Next steps:")
        print("   1. Install dependencies: pip install -r requirements.txt")
        print("   2. Copy env.example to .env and configure")
        print("   3. Run: make up")
        print("   4. Setup ngrok and WhatsApp webhook")
        
        return True
    else:
        print(f"\n❌ Project structure incomplete: {len(missing_files + missing_dirs)} items missing")
        return False

def check_syntax():
    """Check Python syntax in all files."""
    print("\n🔍 Checking Python syntax...")
    
    py_files = list(Path(".").rglob("*.py"))
    syntax_errors = []
    
    for py_file in py_files:
        try:
            with open(py_file, 'r', encoding='utf-8') as f:
                compile(f.read(), py_file, 'exec')
            print(f"✅ Syntax OK: {py_file}")
        except SyntaxError as e:
            syntax_errors.append((py_file, e))
            print(f"❌ Syntax Error: {py_file} - {e}")
        except Exception:
            # Ignore other errors (like import errors)
            print(f"⚠️  Cannot check: {py_file}")
    
    if not syntax_errors:
        print("✅ All Python files have valid syntax!")
        return True
    else:
        print(f"❌ Found {len(syntax_errors)} syntax errors")
        return False

def main():
    """Run all verifications."""
    structure_ok = verify_project_structure()
    syntax_ok = check_syntax()
    
    print("\n" + "=" * 50)
    if structure_ok and syntax_ok:
        print("✅ ClinicAI project is ready!")
        return 0
    else:
        print("❌ Project verification failed")
        return 1

if __name__ == "__main__":
    exit(main())

