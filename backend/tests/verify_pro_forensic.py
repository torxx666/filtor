import os
import sys
import unittest
import math
from unittest.mock import MagicMock

# Mock dependencies
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))
sys.modules["loguru"] = MagicMock()
sys.modules["magic"] = MagicMock()

from analyse.forensic import DataExfiltrationAnalyzer

class TestProForensic(unittest.TestCase):
    def setUp(self):
        self.analyzer = DataExfiltrationAnalyzer()
        self.test_files = []

    def tearDown(self):
        for f in self.test_files:
            if os.path.exists(f): os.remove(f)

    def create_dummy_file(self, name, content=b"test"):
        path = os.path.abspath(name)
        with open(path, "wb") as f: f.write(content)
        self.test_files.append(path)
        return path

    def test_hacking_tool_filename(self):
        # Test detection of mimikatz
        path = self.create_dummy_file("mimikatz.exe")
        res = self.analyzer.analyze_file(path)
        findings = res.detections.get('sensitive_content', {}).get('findings', {})
        self.assertIn('hacking_tool', findings)
        print("[OK] Detected 'mimikatz.exe'")

    def test_double_extension(self):
        # Test invoice.pdf.exe
        path = self.create_dummy_file("invoice.pdf.exe")
        res = self.analyzer.analyze_file(path)
        findings = res.detections.get('sensitive_content', {}).get('findings', {})
        self.assertIn('double_extension', findings)
        print("[OK] Detected 'invoice.pdf.exe'")

    def test_high_entropy(self):
        # Create random high entropy content
        high_entropy_data = os.urandom(1024) 
        path = self.create_dummy_file("suspicious.dat", high_entropy_data)
        
        res = self.analyzer.analyze_file(path)
        findings = res.detections.get('sensitive_content', {}).get('findings', {})
        self.assertIn('high_entropy', findings)
        print("[OK] Detected High Entropy file")

    def test_header_mismatch(self):
        # Create a Fake JPG (starts with 'MZ' instead of FF D8)
        path = self.create_dummy_file("fake_image.jpg", b"MZ9000")
        res = self.analyzer.analyze_file(path)
        findings = res.detections.get('sensitive_content', {}).get('findings', {})
        self.assertIn('header_mismatch', findings)
        print("[OK] Detected Header Mismatch (MZ in .jpg)")

if __name__ == '__main__':
    unittest.main()
