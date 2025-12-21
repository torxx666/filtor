import os
import sys
import unittest
from unittest.mock import MagicMock, patch

# Add backend to path
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

# Mock dependencies that might be hard to load in test
sys.modules["cv2"] = MagicMock()
sys.modules["loguru"] = MagicMock()

from analyse.meta_video import extract_binary_strings, extract_all_metadata
from indexing import process_indexing, indexing_state

class TestAnalysisModes(unittest.TestCase):

    def setUp(self):
        # Reset indexing state
        indexing_state["status"] = "idle"
        indexing_state["message"] = ""
        
        # Create a dummy video file
        self.test_file = "test_video_critical.mp4"
        with open(self.test_file, "wb") as f:
            f.write(b"ftypisom")
            f.write(b"Some interesting strings like C:\\Users\\Admin\\Desktop\\secret.txt\n")
            f.write(b"And another one: Core Media Audio\n")
            f.write(b"PADDING" * 100)

    def tearDown(self):
        if os.path.exists(self.test_file):
            os.remove(self.test_file)

    @patch('indexing.get_db_connection')
    @patch('indexing.DeepFileAnalyzer')
    def test_fast_mode_early_exit(self, MockAnalyzer, mock_get_db):
        # Setup mock DB
        mock_conn = MagicMock()
        mock_get_db.return_value = mock_conn
        
        # Setup mock analyzer to return 95 score for the first file
        mock_analyzer_instance = MockAnalyzer.return_value
        mock_res = MagicMock()
        mock_res.security_issues = ["Critical Vulnerability Found"]
        mock_res.risk_indicators = ["High Entropy"]
        mock_res.hidden_content = {'polyglot': True} # 40 points
        mock_res.findings = {
            'text': {'secrets_found': [{'type': 'password'}, {'type': 'key'}]} # 60 points
        } # Total score will be > 90
        mock_res.metadata_extracted = {}
        mock_res.file_type = "video/mp4"
        mock_analyzer_instance.analyze.return_value = mock_res
        
        # We need a list of files. We'll mock os.walk to return our test file twice
        with patch('os.walk') as mock_walk:
            mock_walk.return_value = [('.', [], [self.test_file, "second_file.mp4"])]
            
            # Run indexing in FAST mode
            process_indexing(".", mode="FAST")
            
            # Verify it stopped (it should have aborted after the first file)
            # In Phase 2, it should have returned early
            self.assertEqual(indexing_state["status"], "idle")
            self.assertIn("Stopped", indexing_state["message"])
            
            # Verify analyze was called only once in Phase 2 for the critical file
            # Actually, os.walk returned 2 files.
            # Phase 1 indexes both. Phase 2 starts with the first one.
            self.assertLessEqual(mock_analyzer_instance.analyze.call_count, 1)

    def test_string_logging(self):
        # Test that extract_binary_strings logs the "trouve" message
        from loguru import logger
        
        # Create a file with both good and bad strings
        with open(self.test_file, "wb") as f:
            f.write(b"Adobe Premiere Pro CC 2022\n") # Good (Length > 7)
            f.write(b"qK-FKL\n") # Junk (Length < 7)
            f.write(b"3SsG\n") # Junk (Length < 7)
            f.write(b"tEXl\n") # Junk (Length < 7)
            f.write(b"o*zLJ[\n") # Junk (Low ratio/weird)
            f.write(b"C:\\Users\\Admin\\Documents\\Project.prproj\n") # Path (Good)
            f.write(b"9'LPUe8N\n") # Junk (Length 8 but weird ratio/entropy)
            f.write(b"CoreMediaAudio\n") # Good

        # Capture logs
        logs = []
        def custom_logger(msg):
            logs.append(msg)
            
        with patch.object(logger, 'info', side_effect=custom_logger):
            extract_binary_strings(self.test_file, depth="FAST")
            
        # Check results
        good_found = any("Adobe Premiere" in str(line) for line in logs)
        path_found = any("Project.prproj" in str(line) for line in logs)
        core_media_found = any("CoreMediaAudio" in str(line) for line in logs)
        
        # Strings that SHOULD be filtered out
        junk_strings = ["qK-FKL", "3SsG", "tEXl", "o*zLJ[", "9'LPUe8N"]
        found_junk = []
        for l in logs:
            for j in junk_strings:
                if j in str(l):
                    found_junk.append(l)
        
        self.assertTrue(good_found, "Should find Adobe Premiere")
        self.assertTrue(path_found, "Should find the path")
        self.assertTrue(core_media_found, "Should find CoreMediaAudio")
        self.assertEqual(len(found_junk), 0, f"Should NOT find junk strings, but found: {found_junk}")
        
        print("\nCaptured logs sample (Verified Clean):")
        for l in logs:
            print(f"  {l}")

if __name__ == "__main__":
    unittest.main()
