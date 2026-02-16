"""
Get Machine ID for PowerBI Desktop App License Activation

This is a simple standalone script to get your Machine ID
without needing to install the full application.

Usage:
    python get_machine_id.py

The script will display your unique Machine ID and copy it to your clipboard.
Send this ID to support@taik18.com to receive your license key.
"""

import hashlib
import uuid
import sys
from pathlib import Path


def get_machine_id() -> str:
    """Generate unique machine fingerprint"""
    try:
        # Try to use WMI for Windows systems (more reliable)
        try:
            import wmi
            identifiers = []
            
            c = wmi.WMI()
            
            # System UUID
            for system in c.Win32_ComputerSystemProduct():
                if system.UUID and system.UUID.strip() and system.UUID.strip().upper() != 'FFFFFFFF-FFFF-FFFF-FFFF-FFFFFFFFFFFF':
                    identifiers.append(system.UUID.strip())
                    break
            
            # CPU ID
            for cpu in c.Win32_Processor():
                if cpu.ProcessorId and cpu.ProcessorId.strip():
                    identifiers.append(cpu.ProcessorId.strip())
                    break
            
            # Motherboard Serial
            for board in c.Win32_BaseBoard():
                if board.SerialNumber and board.SerialNumber.strip():
                    identifiers.append(board.SerialNumber.strip())
                    break
            
            # If we got identifiers, use them
            if identifiers:
                combined = '|'.join(identifiers)
                fingerprint = hashlib.sha256(combined.encode()).hexdigest()[:16]
                return fingerprint
                
        except ImportError:
            print("Note: WMI module not found. Installing it will provide more reliable Machine ID.")
            print("To install: pip install wmi")
            print("\nUsing fallback method...\n")
        except Exception as e:
            print(f"Note: WMI query failed ({e}). Using fallback method...\n")
        
        # Fallback to MAC address based ID
        mac = ':'.join(['{:02x}'.format((uuid.getnode() >> elements) & 0xff)
                      for elements in range(0, 2*6, 2)][::-1])
        fingerprint = hashlib.sha256(mac.encode()).hexdigest()[:16]
        return fingerprint
        
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)


def copy_to_clipboard(text: str) -> bool:
    """Copy text to clipboard"""
    try:
        # Try using pyperclip (cross-platform)
        import pyperclip
        pyperclip.copy(text)
        return True
    except ImportError:
        try:
            # Windows fallback using win32clipboard
            import win32clipboard
            win32clipboard.OpenClipboard()
            win32clipboard.EmptyClipboard()
            win32clipboard.SetClipboardText(text)
            win32clipboard.CloseClipboard()
            return True
        except ImportError:
            # Last resort: PowerShell on Windows
            try:
                import subprocess
                subprocess.run(['powershell', '-command', f'Set-Clipboard -Value "{text}"'], 
                             check=True, capture_output=True)
                return True
            except:
                return False


def main():
    print("="*60)
    print("PowerBI Desktop App - Machine ID Generator")
    print("="*60)
    print()
    
    # Get machine ID
    print("Generating your unique Machine ID...")
    machine_id = get_machine_id()
    
    print()
    print("="*60)
    print("YOUR MACHINE ID:")
    print("="*60)
    print()
    print(f"    {machine_id}")
    print()
    print("="*60)
    print()
    
    # Try to copy to clipboard
    if copy_to_clipboard(machine_id):
        print("✓ Machine ID has been copied to your clipboard!")
        print()
        print("Next Steps:")
        print("1. Email this Machine ID to: support@taik18.com")
        print("2. Subject: 'License Request - [Your Name]'")
        print("3. You'll receive your license key within 1-2 hours")
        print()
    else:
        print("Note: Could not auto-copy to clipboard.")
        print("Please manually copy the Machine ID above.")
        print()
        print("To enable auto-copy, install pyperclip:")
        print("  pip install pyperclip")
        print()
        print("Next Steps:")
        print("1. Copy the Machine ID above")
        print("2. Email it to: support@taik18.com")
        print("3. Subject: 'License Request - [Your Name]'")
        print("4. You'll receive your license key within 1-2 hours")
        print()
    
    print("="*60)
    print()
    
    # Wait for user to press Enter
    input("Press Enter to exit...")


if __name__ == '__main__':
    main()
