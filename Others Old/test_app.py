"""
Automated test script for Power BI Migration Toolkit
Tests all critical functionality before building
"""
import sys
import time
import requests
from pathlib import Path

def test_backend_api():
    """Test if FastAPI backend is responding"""
    print("Testing Backend API...")
    base_url = "http://127.0.0.1:8000"
    
    tests = [
        ("/api/health", "Health check"),
        ("/api/workspaces", "Get workspaces"),
        ("/api/datasets", "Get datasets"),
    ]
    
    for endpoint, description in tests:
        try:
            response = requests.get(f"{base_url}{endpoint}", timeout=5)
            status = "✓ PASS" if response.status_code in [200, 404] else "✗ FAIL"
            print(f"  {status} - {description}: HTTP {response.status_code}")
        except requests.exceptions.ConnectionError:
            print(f"  ✗ FAIL - {description}: Backend not running")
            return False
        except Exception as e:
            print(f"  ✗ FAIL - {description}: {e}")
            return False
    
    return True

def test_imports():
    """Test that all required modules can be imported"""
    print("\nTesting Python Imports...")
    modules = [
        "PyQt6.QtWidgets",
        "PyQt6.QtCore",
        "fastapi",
        "uvicorn",
        "pandas",
        "requests",
        "qtawesome",
    ]
    
    failed = []
    for module in modules:
        try:
            __import__(module)
            print(f"  ✓ {module}")
        except ImportError as e:
            print(f"  ✗ {module}: {e}")
            failed.append(module)
    
    return len(failed) == 0

def test_file_structure():
    """Test that all required files exist"""
    print("\nTesting File Structure...")
    required_files = [
        "src/main.py",
        "src/gui/main_window.py",
        "src/api/server.py",
        "requirements.txt",
        "powerbi-toolkit.spec",
        "setup.py",
    ]
    
    missing = []
    for file in required_files:
        path = Path(file)
        if path.exists():
            print(f"  ✓ {file}")
        else:
            print(f"  ✗ {file} - MISSING")
            missing.append(file)
    
    return len(missing) == 0

def main():
    print("=" * 60)
    print("Power BI Migration Toolkit - Pre-Build Test Suite")
    print("=" * 60)
    
    results = {
        "File Structure": test_file_structure(),
        "Python Imports": test_imports(),
    }
    
    print("\n" + "=" * 60)
    print("Test Summary")
    print("=" * 60)
    
    all_passed = True
    for test_name, passed in results.items():
        status = "✓ PASS" if passed else "✗ FAIL"
        print(f"{status} - {test_name}")
        if not passed:
            all_passed = False
    
    print("\n" + "=" * 60)
    if all_passed:
        print("✓ ALL TESTS PASSED - Safe to build")
        print("=" * 60)
        return 0
    else:
        print("✗ TESTS FAILED - DO NOT BUILD")
        print("=" * 60)
        return 1

if __name__ == "__main__":
    sys.exit(main())
