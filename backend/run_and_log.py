import subprocess
import time
import requests

# Start server on a different port
proc = subprocess.Popen(["uvicorn", "app.main:app", "--port", "8001"], stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)

time.sleep(3) # Wait for server to start

# Run smoke test against port 8001
import os
os.environ["BASE_URL"] = "http://localhost:8001/api/v1"

smoke_proc = subprocess.run(["python3", "scripts/smoke_test.py"], capture_output=True, text=True)
print("SMOKE TEST OUTPUT:")
print(smoke_proc.stdout)
print(smoke_proc.stderr)

# Kill server
proc.terminate()
stdout, _ = proc.communicate()

print("SERVER LOGS:")
print(stdout)
