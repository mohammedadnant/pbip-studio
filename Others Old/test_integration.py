"""
Integration test - Launch app and test API connectivity
"""
import sys
import time
import subprocess
import requests
from pathlib import Path

def wait_for_backend(max_wait=10):
    """Wait for backend to be ready"""
    print("Waiting for backend to start...", end="", flush=True)
    start = time.time()
    while time.time() - start < max_wait:
        try:
            response = requests.get("http://127.0.0.1:8000/api/health", timeout=1)
            if response.status_code == 200:
                print(" ✓ Backend ready")
                return True
        except:
            pass
        time.sleep(0.5)
        print(".", end="", flush=True)
    print(" ✗ Backend failed to start")
    return False

def test_api_endpoints():
    """Test critical API endpoints"""
    print("\nTesting API Endpoints...")
    endpoints = {
        "/api/health": "Health check",
        "/api/workspaces": "Workspaces list",
        "/api/datasets": "Datasets list",
    }
    
    for endpoint, description in endpoints.items():
        try:
            response = requests.get(f"http://127.0.0.1:8000{endpoint}", timeout=2)
            status = "✓" if response.status_code in [200, 404] else "✗"
            print(f"  {status} {description} - HTTP {response.status_code}")
        except Exception as e:
            print(f"  ✗ {description} - Error: {e}")

if __name__ == "__main__":
    print("=" * 60)
    print("Integration Test - Backend API")
    print("=" * 60)
    print("\nNOTE: Make sure the app is running!")
    print("Start the app with: python src/main.py")
    print()
    
    input("Press Enter when the app window is visible...")
    
    if wait_for_backend():
        test_api_endpoints()
        print("\n✓ Integration test complete")
    else:
        print("\n✗ Integration test failed - backend not responding")
        sys.exit(1)
