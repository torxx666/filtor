import os
import sys
from unittest.mock import MagicMock

# Mock dependencies for meta_video
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))
sys.modules["cv2"] = MagicMock()
sys.modules["loguru"] = MagicMock()

from analyse.meta_video import extract_all_metadata

def test_extract_general_strings():
    test_file = "test_video_general.mp4"
    fake_path = b"C:\\Users\\hp\\Documents\\Adobe\\Premiere Pro\\22.0\\Untitled99.prproj"
    fake_metadata = b"Core Media Audio v1.2"
    
    # Create a dummy file with both path and general metadata embedded
    with open(test_file, "wb") as f:
        f.write(b"\x00\x00\x00\x18ftypisom\x00\x00\x02\x00isomiso2avc1mp41")
        f.write(b"Some random binary \xff\xfe\xfd ")
        f.write(fake_metadata)
        f.write(b" \x00\x01\x02 random padding ")
        f.write(fake_path)
        f.write(b" End of file \x00")

    try:
        print(f"Analyzing {test_file}...")
        meta = extract_all_metadata(test_file)
        
        found = meta.get('embedded_strings', [])
        print(f"Found strings: {found[:10]}...") # Show first 10
        
        has_path = any("Untitled99.prproj" in s for s in found)
        has_meta = any("Core Media Audio" in s for s in found)
        
        if has_path and has_meta:
            print("[SUCCESS] Found both the Premiere path AND the 'Core Media Audio' string!")
        elif has_path:
            print("[PARTIAL] Found path but failed to find 'Core Media Audio'.")
        elif has_meta:
            print("[PARTIAL] Found 'Core Media Audio' but failed to find path.")
        else:
            print("[FAILURE] Could not find either string.")
            
    finally:
        if os.path.exists(test_file):
            os.remove(test_file)

if __name__ == "__main__":
    test_extract_general_strings()
