import os
import sys
import unittest
from pathlib import Path

# Add backend to path
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from unittest.mock import MagicMock
sys.modules["loguru"] = MagicMock()
sys.modules["magic"] = MagicMock()

from indexing import extract_text_content
from analyse.forensic import DataExfiltrationAnalyzer

class TestEnhancements(unittest.TestCase):
    def test_hebrew_extraction(self):
        # Create temp file with Hebrew (cp1255 or utf8)
        content = "שלום עולם"
        path = "temp_hebrew.txt"
        with open(path, "w", encoding="utf-8") as f:
            f.write(content)
            
        try:
            extracted = extract_text_content(path, "text/plain")
            self.assertIn("שלום", extracted)
            print("[OK] Hebrew extraction (UTF-8) passed")
        finally:
            if os.path.exists(path): os.remove(path)

    def test_forensic_patterns(self):
        analyzer = DataExfiltrationAnalyzer()
        
        # Test PII
        content = "My SSN is 123-45-6789 and IP is 192.168.1.1"
        path = "temp_pii.txt"
        with open(path, "w") as f: f.write(content)
            
        try:
            res = analyzer.analyze_file(path)
            detections = res.detections.get('sensitive_content', {}).get('findings', {})
            self.assertIn('ssn_us', detections)
            self.assertIn('ipv4', detections)
            print("[OK] Forensic PII patterns passed")
        finally:
            if os.path.exists(path): os.remove(path)

        # Test Crypto
        content = "bc1qar0srrr7xfkvy5l643lydnw9re59gtzzwf5mdq" # Bitcoin address
        path = "temp_crypto.txt"
        with open(path, "w") as f: f.write(content)
            
        try:
            res = analyzer.analyze_file(path)
            detections = res.detections.get('sensitive_content', {}).get('findings', {})
            self.assertIn('crypto_address', detections)
            print("[OK] Forensic Crypto patterns passed")
        finally:
            if os.path.exists(path): os.remove(path)

if __name__ == '__main__':
    unittest.main()
