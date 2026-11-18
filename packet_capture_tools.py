import os
import json
import subprocess

from pathlib import Path
from datetime import datetime
from langchain_core.tools import tool

@tool
def check_network_interfaces() -> str:
    """
    Checks the available network interfaces on the local device, not the network devices
    """

    cmd = ["tcpdump", "-D"]
    result = subprocess.run(
        cmd,
        capture_output=True,
        text=True
    )

    if result.returncode != 0:
        return json.dumps({
            "status": "failed",
            "error": result.stderr,
            "output": result.stdout,
            "command": " ".join(cmd)
        })

    output = result.stdout

    return json.dumps({
        "status": "success",
        "command": " ".join(cmd),
        "output": output
    })

@tool
def capture_packets(packet_count: int, interface: str) -> str:
    """
    Start the packet capture using tcpdump for a set number of packets
    and save them to directory 'packet_capture'
    Args:
        packet_count: number of packets to capture
        interface: network interface to capture packets from
    """

    os.makedirs("packet_capture", exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filepath = f"packet_capture/{interface}_{timestamp}.pcap"

    cmd = ["sudo", "tcpdump", "-ni", interface, "-c", f"{packet_count}", "-w", filepath]
    print(f"[capture_packets] 🔧 TOOL CALL: CAPTURE_PACKETS")
    print(f"[capture_packets] {" ".join(cmd)}")
    print(f"[capture_packets] Capturing packets ......")
    result = subprocess.run(cmd, capture_output=True, text=True)

    if result.returncode != 0:
        return json.dumps({
            "status": "failed",
            "error": result.stderr,
            "output": result.stdout
        })

    output = result.stdout

    return json.dumps({
        "status": "success",
        "command": " ".join(cmd),
        "output": output,
        "filepath": filepath
    })

@tool
def read_packet_capture(filepath: str) -> str:
    """
    This tool returns the content of the pcap file
    Args:
        filepath: path to the pcap file
    """

    # Make sure file exist
    if not Path(filepath).is_file():
        return json.dumps({
            "status": "failed",
            "error": f"Path '{filepath}' does not exist"
        })

    # Make sure it is a pcap file
    if not filepath.endswith(".pcap"):
        return json.dumps({
            "status": "failed",
            "error": f"{filepath} is not a pcap file"
        })

    # Run command to view content
    cmd = ["tcpdump", "-r", filepath]
    result = subprocess.run(cmd, capture_output=True, text=True)

    if result.returncode != 0:
        return json.dumps({
            "status": "failed",
            "error": result.stderr,
            "output": result.stdout
        })

    output = result.stdout

    return json.dumps({
        "status": "success",
        "command": " ".join(cmd),
        "output": output,
        "filepath": filepath
    })
