import urllib.request
import json
import socket

# Check if port 9000 is open
s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
result = s.connect_ex(('localhost', 9000))

if result == 0:
    print("Port 9000 is open")
    try:
        with urllib.request.urlopen("http://localhost:9000/recent") as response:
            if response.getcode() == 200:
                print("Endpoint /recent returned 200 OK")
                data = json.load(response)
                print(f"Received {len(data)} items")
            else:
                print(f"Error: {response.getcode()}")
    except Exception as e:
        print(f"Request failed: {e}")
else:
    print("Port 9000 is closed")
s.close()
