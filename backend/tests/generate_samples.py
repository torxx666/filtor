import os
import random

# Directory for samples
TARGET_DIR = os.path.join(os.path.dirname(__file__), '../../incoming/forensic_samples')
os.makedirs(TARGET_DIR, exist_ok=True)

def create_file(filename, content=b""):
    path = os.path.join(TARGET_DIR, filename)
    with open(path, "wb") as f:
        f.write(content)
    try:
        print(f"Created: {path.encode('ascii', errors='replace').decode()}")
    except:
        print("Created file (name has hidden chars)")

# 1. Hacking Tool (Filename detection)
create_file("mimikatz_tool.exe", b"Normal PE header but suspicious name")

# 2. Double Extension (Obfuscation)
create_file("invoice_2024.pdf.exe", b"MZ..............")

# 3. Header Mismatch (Fake Image)
# Claiming to be JPG, but starts with 'MZ' (Executable signature)
create_file("funny_cat.jpg", b"MZ900000000000")

# 4. RTLO (Right-to-Left Override) Spoofing
# Filename looks like 'annexe_cod.exe' but characters are flipped
# \u202e is the override char. "annexe_\u202excod.exe" -> displays as "annexe_exe.docx" roughly
create_file("annexe_\u202ecod.exe", b"MZ.....")

# 5. High Entropy (Encrypted/Exfiltration)
# Generate 4KB of random bytes (Entropy ~8.0)
random_data = os.urandom(4096)
create_file("secret_data.dat", random_data)

print("\nDone! Files created in 'incoming/forensic_samples'.")
print("You can now trigger a scan (e.g. login or manual) to see the detections.")
