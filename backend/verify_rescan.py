import urllib.request
import json
import time

API_URL = "http://localhost:9000"
KEYWORD = "TEST_AUTO_SCAN_" + str(int(time.time()))

def add_keyword_and_check():
    print(f"Adding keyword: {KEYWORD}")
    req = urllib.request.Request(
        f"{API_URL}/keywords",
        data=json.dumps({"keyword": KEYWORD}).encode('utf-8'),
        headers={'Content-Type': 'application/json'}
    )
    
    try:
        with urllib.request.urlopen(req) as response:
            data = json.load(response)
            print(f"Response: {data}")
            
        print("Checking status immediately (expecting 'scanning' or 'idle' but recently triggered)...")
        time.sleep(1) # Give it a moment to start
        
        with urllib.request.urlopen(f"{API_URL}/status") as response:
            status = json.load(response)
            print(f"Current Status: {status['status']}")
            print(f"Message: {status.get('message', '')}")
            
            if status['status'] == 'scanning' or "Analyzing" in status.get('message', ''):
                print("SUCCESS: Indexing triggered!")
            else:
                print("WARNING: Status is idle. It might have finished very quickly or not started.")
                
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    add_keyword_and_check()
