from librenms_tools import (
    get_network_devices,
    get_device_health,
    get_device_interfaces,
    get_device_availability,
    get_device_outages,
    get_network_alerts
)

def test_tool(name, tool, args=None):
    print(f"\n{'=' * 60}")
    print(f"Testing: {name}")
    print('=' * 60)

    try:
        result = tool.invoke(args or {})
        print(result)

        if isinstance(result, dict) and "error" in result:
            print(f"\n[FAILED] {name}: {result['error']}")
        else:
            print(f"\n[SUCCESS] {name}")

        return result

    except Exception as e:
        print(f"\n[FAILED] {name}: {e}")
        return None

# R1 10.0.11.3
# R2 192.168.0.4
# SW1 172.16.0.6
hostname = "SW1"
ip_addr = "172.16.0.6"
# Test 1: Retrieve all monitored devices
devices = test_tool(
    "Get Network Devices",
    get_network_devices
)

# Test 2: Retrieve device health
test_tool(
    "Get Device Health",
    get_device_health,
    {"hostname": hostname}
)

# Test 3: Retrieve device interfaces
test_tool(
    "Get Device Interfaces",
    get_device_interfaces,
    {"hostname": ip_addr}
)

# Test 4: Retrieve device availability
test_tool(
    "Get Device Availability",
    get_device_availability,
    {"hostname": hostname}
)

# Test 5: Retrieve device outages
test_tool(
    "Get Device Outages",
    get_device_outages,
    {"hostname": hostname}
)

# Test 6: Retrieve network alerts
test_tool(
    "Get Network Alerts",
    get_network_alerts
)

print("\nAll LibreNMS tool tests completed.")
