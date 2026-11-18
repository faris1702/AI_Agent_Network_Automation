
import os
import requests
from dotenv import load_dotenv

# Load environment variables from .env
load_dotenv()

LIBRENMS_URL = os.getenv("LIBRENMS_URL")
LIBRENMS_API_KEY = os.getenv("LIBRENMS_API_KEY")

# Check environment variables
if not LIBRENMS_URL or not LIBRENMS_API_KEY:
    print("[ERROR] Missing LIBRENMS_URL or LIBRENMS_API_KEY in .env")
    exit(1)

# Configure API request
url = f"{LIBRENMS_URL.rstrip('/')}/api/v0/devices"

headers = {
    "X-Auth-Token": LIBRENMS_API_KEY,
    "Accept": "application/json"
}

print("[INFO] Connecting to LibreNMS API...")
print(f"[INFO] API URL: {url}")

try:
    response = requests.get(
        url,
        headers=headers,
        timeout=15
    )

    # Check HTTP response
    response.raise_for_status()

    data = response.json()

    print("\n[SUCCESS] LibreNMS API connection successful!")
    print(f"HTTP Status Code: {response.status_code}")
    print("\nAPI Response:")

    for device in data.get("devices", []):
        print(
            f"Hostname: {device.get('hostname')} | "
            f"IP: {device.get('ip')} | "
            f"Status: {device.get('status')}"
        )

    print(f"\nTotal devices found: {len(data.get('devices', []))}")

except requests.exceptions.HTTPError as e:
    print(f"\n[ERROR] HTTP Error: {e}")
    print(f"Response: {response.text}")

except requests.exceptions.ConnectionError:
    print("\n[ERROR] Could not connect to LibreNMS.")
    print("Check the URL and network connectivity.")

except requests.exceptions.Timeout:
    print("\n[ERROR] Request timed out.")

except requests.exceptions.RequestException as e:
    print(f"\n[ERROR] Request failed: {e}")

except ValueError:
    print("\n[ERROR] Invalid JSON response from LibreNMS.")
