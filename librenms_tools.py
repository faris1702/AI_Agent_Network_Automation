
import os
import requests
from dotenv import load_dotenv
from langchain_core.tools import tool

load_dotenv()

LIBRENMS_URL = os.getenv("LIBRENMS_URL")
LIBRENMS_API_KEY = os.getenv("LIBRENMS_API_KEY")

HEADERS = {
    "Authorization": f"Bearer {LIBRENMS_API_KEY}",
    "Accept": "application/json"
}


def librenms_request(endpoint, params=None):
    """Send a GET request to the LibreNMS API."""

    url = f"{LIBRENMS_URL.rstrip('/')}/api/v0/{endpoint.lstrip('/')}"

    try:
        response = requests.get(
            url,
            headers=HEADERS,
            params=params,
            timeout=15
        )

        response.raise_for_status()
        return response.json()

    except requests.RequestException as e:
        return {"error": str(e)}


@tool
def get_network_devices() -> dict:
    """
    Retrieve all network devices monitored by LibreNMS.
    Returns hostname, IP address and device status.
    """

    return librenms_request("devices")


@tool
def get_device_health(hostname: str) -> dict:
    """
    Retrieve health information for a network device.
    Includes available CPU, memory and hardware sensors.

    Args:
        hostname: Device hostname or device ID.
    """

    return librenms_request(
        f"devices/{hostname}/health"
    )


@tool
def get_device_interfaces(ip_addr: str) -> dict:
    """
    Retrieve interface and port information
    for a specified network device.

    Args:
        ip_addr: Device IP address
    """

    return librenms_request(
        f"devices/{ip_addr}/ports"
    )


@tool
def get_device_availability(hostname: str) -> dict:
    """
    Retrieve device availability statistics.

    Args:
        hostname: Device hostname or device ID.
    """

    return librenms_request(
        f"devices/{hostname}/availability"
    )


@tool
def get_device_outages(hostname: str) -> dict:
    """
    Retrieve historical outages for a network device.

    Args:
        hostname: Device hostname or device ID.
    """

    return librenms_request(
        f"devices/{hostname}/outages"
    )


@tool
def get_network_alerts() -> dict:
    """
    Retrieve active network alerts from LibreNMS.
    Returns alert information including severity,
    affected devices and timestamps.
    """

    return librenms_request(
        "faults",
        params={"state": 1}
    )
