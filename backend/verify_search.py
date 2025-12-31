import urllib.request
import json
import urllib.parse

BASE_URL = "http://localhost:9000"

def test_search():
    print("Testing search for 'pass'...")
    try:
        params = urllib.parse.urlencode({"q": "pass"})
        url = f"{BASE_URL}/files?{params}"
        with urllib.request.urlopen(url) as response:
            data = json.load(response)
            files = data.get('files', [])
            print(f"Found {len(files)} files matching 'pass'")
            for f in files:
                print(f"- {f['filename']}")
                
            if len(files) > 0:
                print("SUCCESS: Search returned results.")
            else:
                print("WARNING: No results found.")
            
    except Exception as e:
        print(f"FAILED: {e}")

if __name__ == "__main__":
    test_search()
