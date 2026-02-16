"""
License Key Generator for PowerBI Desktop App
Run this script to generate license keys for customers

Usage:
    python generate_license.py customer@email.com
    python generate_license.py customer@email.com --days 365
"""

import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / 'src'))

from utils.license_manager import LicenseManager

def main():
    if len(sys.argv) < 2:
        print("Usage: python generate_license.py customer@email.com [--days 365] [--machine-id MACHINE_ID]")
        print("\nExamples:")
        print("  python generate_license.py john@example.com")
        print("  python generate_license.py john@example.com --days 730  # 2 years")
        print("  python generate_license.py john@example.com --machine-id 3fd26d46a6cf64ae  # Machine-locked")
        sys.exit(1)
    
    email = sys.argv[1]
    days = 365  # Default 1 year
    machine_id = None  # Optional machine locking
    
    # Parse arguments
    i = 2
    while i < len(sys.argv):
        if sys.argv[i] == '--days':
            if i + 1 >= len(sys.argv):
                print("Error: --days requires a value")
                sys.exit(1)
            try:
                days = int(sys.argv[i + 1])
                i += 2
            except ValueError:
                print("Error: days must be a number")
                sys.exit(1)
        elif sys.argv[i] == '--machine-id':
            if i + 1 >= len(sys.argv):
                print("Error: --machine-id requires a value")
                sys.exit(1)
            machine_id = sys.argv[i + 1]
            i += 2
        else:
            print(f"Error: Unknown argument '{sys.argv[i]}'")
            sys.exit(1)
    
    # Generate license
    print(f"\n{'='*60}")
    print("PowerBI Desktop App - License Key Generator")
    print(f"{'='*60}\n")
    
    manager = LicenseManager()
    license_key = manager.generate_license_key(email, days=days, machine_id=machine_id)
    
    # Calculate expiry date
    from datetime import datetime, timedelta
    expiry_date = (datetime.now() + timedelta(days=days)).strftime('%Y-%m-%d')
    
    print(f"Customer Email: {email}")
    print(f"License Duration: {days} days ({days//365} year{'s' if days//365 != 1 else ''})")
    print(f"Expiry Date: {expiry_date}")
    if machine_id:
        print(f"Machine-Locked: YES (ID: {machine_id})")
    else:
        print(f"Machine-Locked: NO (activates on first use)")
    print(f"\n{'='*60}")
    print("LICENSE KEY (send this to customer):")
    print(f"{'='*60}")
    print(f"\n{license_key}\n")
    print(f"{'='*60}\n")
    
    # Validate it works
    validation = manager.validate_license_key(license_key)
    if validation['valid']:
        print("✓ License key validated successfully")
        print(f"✓ Valid for {validation['days_remaining']} days")
    else:
        print(f"✗ Validation failed: {validation.get('error')}")
    
    print(f"\n{'='*60}\n")

if __name__ == '__main__':
    main()
