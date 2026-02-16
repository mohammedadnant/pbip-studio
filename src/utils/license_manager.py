"""
Simple Offline License Manager for PowerBI Desktop App
- 1-year licenses
- Machine-locked
- Offline validation
- No server dependency
"""

import hashlib
import hmac
import base64
import json
import uuid
import platform
import subprocess
from datetime import datetime, timedelta
from pathlib import Path
from cryptography.fernet import Fernet
import logging

logger = logging.getLogger(__name__)

# Master secret key - CHANGE THIS TO YOUR OWN SECRET!
# Generate with: python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
MASTER_SECRET = b'6YtWNULcyVrmYOCtZbLnI8MSyZpmYEkwRZY7pxC4X9M='

class LicenseManager:
    """Manages offline license validation and activation"""
    
    def __init__(self):
        """Initialize license manager"""
        self.app_data = Path.home() / '.pbip_studio'
        self.app_data.mkdir(exist_ok=True)
        self.license_file = self.app_data / 'license.dat'
        self.machine_id_file = self.app_data / 'machine.id'
        self.machine_id = self._get_machine_fingerprint()
    
    def _get_machine_fingerprint(self) -> str:
        """Generate unique machine fingerprint (cached for consistency)"""
        # Check if we have a cached machine ID
        if self.machine_id_file.exists():
            try:
                cached_id = self.machine_id_file.read_text().strip()
                if cached_id and len(cached_id) == 16:
                    logger.info(f"Using cached machine fingerprint: {cached_id}")
                    return cached_id
            except:
                pass
        
        # Generate new machine ID
        try:
            import wmi
            identifiers = []
            
            try:
                # Use WMI directly (no PowerShell windows)
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
                        
            except Exception as e:
                logger.warning(f"WMI query failed: {e}")
            
            # Fallback to MAC address if nothing else works
            if not identifiers:
                mac = ':'.join(['{:02x}'.format((uuid.getnode() >> elements) & 0xff)
                              for elements in range(0, 2*6, 2)][::-1])
                identifiers.append(mac)
            
            # Combine and hash
            combined = '|'.join(identifiers)
            fingerprint = hashlib.sha256(combined.encode()).hexdigest()[:16]
            
            # Cache the machine ID for future use
            try:
                self.machine_id_file.write_text(fingerprint)
                logger.info(f"Machine fingerprint cached: {fingerprint}")
            except:
                logger.warning("Failed to cache machine fingerprint")
            
            return fingerprint
            
        except Exception as e:
            logger.error(f"Error generating machine fingerprint: {e}")
            # Fallback to basic UUID (also cached)
            fallback = hashlib.sha256(str(uuid.getnode()).encode()).hexdigest()[:16]
            try:
                self.machine_id_file.write_text(fallback)
            except:
                pass
            return fallback
    
    def generate_license_key(self, email: str, days: int = 365, machine_id: str = None) -> str:
        """
        Generate a license key (used by you to create keys for customers)
        
        Args:
            email: Customer email address
            days: License validity in days (default 365 = 1 year)
            machine_id: Optional machine ID to lock license to specific machine
            
        Returns:
            License key string in format: PBMT-<data>-<signature>
        """
        expiry = (datetime.now() + timedelta(days=days)).isoformat()
        
        # Create license payload
        payload = {
            'email': email.lower().strip(),
            'expiry': expiry,
            'version': '1.0'
        }
        
        # Add machine_id if provided (for machine-locked licenses)
        if machine_id:
            payload['machine_id'] = machine_id.strip()
        
        # Encode payload
        payload_json = json.dumps(payload, separators=(',', ':'))
        payload_b64 = base64.urlsafe_b64encode(payload_json.encode()).decode().rstrip('=')
        
        # Generate HMAC signature
        signature = hmac.new(
            MASTER_SECRET,
            payload_b64.encode(),
            hashlib.sha256
        ).hexdigest()[:12]
        
        # Format as readable key
        license_key = f"PBMT-{payload_b64}-{signature}"
        return license_key
    
    def validate_license_key(self, license_key: str) -> dict:
        """
        Validate license key format and signature (offline)
        
        Args:
            license_key: License key string
            
        Returns:
            dict with validation result: {'valid': bool, 'email': str, 'expiry': str, 'error': str}
        """
        try:
            # Parse key format
            if not license_key.startswith('PBMT-'):
                return {'valid': False, 'error': 'Invalid key format'}
            
            parts = license_key.split('-')
            if len(parts) != 3:
                return {'valid': False, 'error': 'Invalid key structure'}
            
            _, payload_b64, signature = parts
            
            # Verify signature
            expected_signature = hmac.new(
                MASTER_SECRET,
                payload_b64.encode(),
                hashlib.sha256
            ).hexdigest()[:12]
            
            if signature != expected_signature:
                return {'valid': False, 'error': 'Invalid signature - key may be tampered'}
            
            # Decode payload
            # Add padding back
            padding = 4 - (len(payload_b64) % 4)
            if padding != 4:
                payload_b64 += '=' * padding
            
            payload_json = base64.urlsafe_b64decode(payload_b64).decode()
            payload = json.loads(payload_json)
            
            # Check machine ID if present in license (machine-locked licenses)
            if 'machine_id' in payload:
                if payload['machine_id'] != self.machine_id:
                    return {
                        'valid': False,
                        'error': f"License is locked to a different machine. This license is for machine ID: {payload['machine_id'][:8]}..."
                    }
            
            # Check expiry
            expiry_date = datetime.fromisoformat(payload['expiry'])
            if datetime.now() > expiry_date:
                return {
                    'valid': False,
                    'error': f"License expired on {expiry_date.strftime('%Y-%m-%d')}",
                    'email': payload.get('email', ''),
                    'expiry': payload['expiry']
                }
            
            return {
                'valid': True,
                'email': payload.get('email', ''),
                'expiry': payload['expiry'],
                'days_remaining': (expiry_date - datetime.now()).days,
                'machine_locked': 'machine_id' in payload
            }
            
        except Exception as e:
            logger.error(f"License validation error: {e}")
            return {'valid': False, 'error': f'Validation error: {str(e)}'}
    
    def activate_license(self, license_key: str) -> dict:
        """
        Activate license on this machine
        
        Args:
            license_key: License key to activate
            
        Returns:
            dict with activation result
        """
        # Validate key first
        validation = self.validate_license_key(license_key)
        if not validation['valid']:
            return validation
        
        # Check if already activated
        existing = self.get_current_license()
        if existing and existing.get('valid'):
            if existing.get('machine_id') == self.machine_id:
                return {'valid': False, 'error': 'License already activated on this machine'}
            else:
                return {'valid': False, 'error': 'License already activated on another machine. Contact support for revocation.'}
        
        # Save activation
        activation_data = {
            'license_key': license_key,
            'machine_id': self.machine_id,
            'activated_at': datetime.now().isoformat(),
            'email': validation['email'],
            'expiry': validation['expiry']
        }
        
        self._save_license(activation_data)
        
        return {
            'valid': True,
            'message': 'License activated successfully',
            'email': validation['email'],
            'expiry': validation['expiry'],
            'days_remaining': validation['days_remaining']
        }
    
    def get_current_license(self) -> dict:
        """
        Get current license status
        
        Returns:
            dict with license info or None if not activated
        """
        if not self.license_file.exists():
            return {'valid': False, 'error': 'No license found'}
        
        try:
            # Load encrypted license
            activation_data = self._load_license()
            
            # Verify machine binding
            if activation_data.get('machine_id') != self.machine_id:
                return {'valid': False, 'error': 'License bound to different machine'}
            
            # Validate the stored key
            license_key = activation_data.get('license_key')
            validation = self.validate_license_key(license_key)
            
            if validation['valid']:
                validation['activated_at'] = activation_data.get('activated_at', '')
                validation['machine_id'] = self.machine_id
            
            return validation
            
        except Exception as e:
            logger.error(f"Error loading license: {e}")
            return {'valid': False, 'error': 'License file corrupted'}
    
    def revoke_license(self) -> bool:
        """
        Revoke current license (allows activation on new machine)
        
        Returns:
            bool: True if revoked successfully
        """
        try:
            if self.license_file.exists():
                self.license_file.unlink()
                logger.info("License revoked successfully")
                return True
            return False
        except Exception as e:
            logger.error(f"Error revoking license: {e}")
            return False
    
    def _save_license(self, data: dict):
        """Save encrypted license data"""
        try:
            # Simple encryption using Fernet
            cipher = Fernet(base64.urlsafe_b64encode(MASTER_SECRET[:32]))
            json_data = json.dumps(data)
            encrypted = cipher.encrypt(json_data.encode())
            self.license_file.write_bytes(encrypted)
        except Exception as e:
            logger.error(f"Error saving license: {e}")
            raise
    
    def _load_license(self) -> dict:
        """Load and decrypt license data"""
        try:
            cipher = Fernet(base64.urlsafe_b64encode(MASTER_SECRET[:32]))
            encrypted = self.license_file.read_bytes()
            decrypted = cipher.decrypt(encrypted)
            return json.loads(decrypted)
        except Exception as e:
            logger.error(f"Error loading license: {e}")
            raise
    
    def check_license_or_raise(self):
        """
        Check if valid license exists, raise exception if not
        Use this at app startup
        """
        license_info = self.get_current_license()
        if not license_info.get('valid'):
            raise LicenseError(license_info.get('error', 'Invalid license'))
        return license_info


class LicenseError(Exception):
    """Raised when license validation fails"""
    pass


# Convenience functions
def is_licensed() -> bool:
    """Quick check if app is licensed"""
    try:
        manager = LicenseManager()
        license_info = manager.get_current_license()
        return license_info.get('valid', False)
    except:
        return False


def get_license_info() -> dict:
    """Get current license information"""
    try:
        manager = LicenseManager()
        return manager.get_current_license()
    except:
        return {'valid': False, 'error': 'License check failed'}
