import os
import json
import subprocess
import yaml

from pathlib import Path
from datetime import datetime
from langchain_core.tools import tool

@tool
def run_cisco_command(device: str, command: str) -> str:
    """
    Run a 'show' command on a Cisco device by running an Ansible command
    and returning the output.

    Args:
       device: The hostname of the Cisco device
       command: The CLI command required to run on the Cisco device
    """

    print(f"[run_cisco_command] 🔧 TOOL CALL: RUN_CISCO_COMMAND")
    # Validate the command
    if "show" not in command:
        return json.dumps({
            "status": "failed",
            "device": device,
            "command": command,
            "error": "Invalid command",
            "output": "Only 'show' commands allowed"
        })

    cmd = [
        "ansible",
        device,
        "-i",
        "hosts.ini",
        "--vault-password-file",
        ".ansible_vault_password",
        "-m",
        "cisco.ios.ios_command",
        "-a",
        f"commands='{command}'"
    ]

    print(f"[run_cisco_command] {" ".join(cmd)}")
    print(f"[run_cisco_command] {device}# {command}")
    result = subprocess.run(cmd, capture_output=True, text=True)

    if result.returncode != 0:
        return json.dumps({
            "status": "failed",
            "device": device,
            "command": command,
            "error": result.stderr,
            "output": result.stdout
        })

    try:
        output = result.stdout.split("=>", 1)[1].strip() # Remove: R1 | SUCCESS =>
        data = json.loads(output)  # Convert Ansible output into dictionary
        stdout_lines = data["stdout_lines"]  # Extract stdout_lines
        lines = stdout_lines[0]  # First command's output

        return json.dumps({
            "status": "success",
            "device": device,
            "command": command,
            "output": "\n".join(lines)
        })

    except Exception as e:
        return json.dumps({
            "status": "failed",
            "device": device,
            "command": command,
            "error": f"Failed to parse Ansible output: {str(e)}",
            "raw_output": result.stdout
        })

@tool
def run_ping_command(device: str, ip: str) -> str:
    """
    Runs a ping command on the network device.

    Args:
        device: Hostname of the device from which the ping command will be run from
        ip: IP address of the destination host
    """

    print(f"[run_cisco_command] 🔧 TOOL CALL: RUN_PING_COMMAND")
    command = f"ping {ip}"

    cmd = [
        "ansible",
        device,
        "-i",
        "hosts.ini",
        "--vault-password-file",
        ".ansible_vault_password",
        "-m",
        "cisco.ios.ios_command",
        "-a",
        f"commands='{command}'"
    ]

    print(f"[run_cisco_command] {" ".join(cmd)}")
    print(f"[run_cisco_command] {device}# {command}")
    result = subprocess.run(cmd, capture_output=True, text=True)

    if result.returncode != 0:
        return json.dumps({
            "status": "failed",
            "device": device,
            "command": command,
            "error": result.stderr,
            "output": result.stdout
        })

    try:
        output = result.stdout.split("=>", 1)[1].strip() # Remove: R1 | SUCCESS =>
        data = json.loads(output)  # Convert Ansible output into dictionary
        stdout_lines = data["stdout_lines"]  # Extract stdout_lines
        lines = stdout_lines[0]  # First command's output

        return json.dumps({
            "status": "success",
            "device": device,
            "command": command,
            "output": "\n".join(lines)
        })

    except Exception as e:
        return json.dumps({
            "status": "failed",
            "device": device,
            "command": command,
            "error": f"Failed to parse Ansible output: {str(e)}",
            "raw_output": result.stdout
        })

@tool
def backup_cisco_config(device: str) -> str:
    """
    Saves the running configuration of the given cisco device to a local
    file in the directory 'configs'
    """

    print(f"[backup_cisco_config] 🔧 TOOL CALL: BACKUP_CISCO_CONFIG")
    result = run_cisco_command.invoke({
        "device": device,
        "command": "show running-config"
    })

    data = json.loads(result)
    if data.get("status") != "success":
        return json.dumps({
            "status": "failed",
            "device": device,
            "error": data.get("error", "Unable to retrieve configuration.")
        })

    os.makedirs("configs", exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"configs/{device}_running_config_{timestamp}.txt"

    with open(filename, "w") as file:
        file.write(data["output"])

    return json.dumps({
        "status": "success",
        "device": device,
        "filename": filename,
        "message": f"Running configuration successfully saved to {filename}."
    })

@tool
def check_hosts_file() -> str:
    """
    Reads the 'hosts.ini' file and returns the content of the file. Does not take any arguments
    """
    filename = "hosts.ini"
    try:
        with open (filename, "r") as file:
            lines = file.readlines()
        host_file_content = "".join(lines)

        return json.dumps({
            "status": "success",
            "content": host_file_content
        })

    except Exception as e:
        return json.dumps({
            "status": "failed",
            "error": f"Failed to check {filename}: {str(e)}"
        })

@tool
def validate_yaml(script: str) -> str:
    """
    Validates the yaml script
    Args:
        script: the actual content of the ansible yaml script
    """

    try:
        yaml.safe_load(script)
        return json.dumps({
            "status": "success",
        })

    except yaml.YAMLError as exc:
        return json.dumps({
            "status": "failed",
            "error": f"Invalid YAML syntax: {exc}"
        })

@tool
def save_ansible_playbook(content: str, filename: str) -> str:
    """
    Saves an ansible playbook in the directory 'playbook/'
    Args:
        content: The actual script itself
        filename: the filename of the script without .yaml
    """

    result = validate_yaml.invoke({"script": content})
    data = json.loads(result)
    if data.get("status") != "success":
        return json.dumps({
            "status": "failed",
            "error": f"{data["error"]}"
        })

    os.makedirs("playbooks", exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    new_filename = f"playbooks/{filename}_{timestamp}.yaml"

    try:
        with open(new_filename, "w") as file:
            file.write(content)

        return json.dumps({
            "status": "success",
            "filename": new_filename,
            "content": content
        })

    except Exception as e:
        return json.dumps({
            "status": "failed",
            "error": f"Failed to save {filename}: {str(e)}"
        })

@tool
def display_ansible_script(script: str) -> str:
    """
    Displays the ansible yaml script for the user to view.
    Args:
        script: the content of the script
    """

    try:
        return json.dumps({
            "status": "success",
            "output": script
        })

    except Exception as e:
        return json.dumps({
            "status": "failed",
            "error": f"Unable to display script: {e}"
        })

@tool
def execute_script(filepath: str) -> str:
    """
    Previews an Ansible playbook using --check --diff.
    If the preview succeeds, asks the user for permission
    before applying the actual configuration changes.
    """

    print("[execute_script] 🔧 TOOL CALL: EXECUTE_SCRIPT")

    # Step 1: Preview changes
    preview_cmd = [
        "ansible-playbook",
        filepath,
        "-i", "hosts.ini",
        "--vault-password-file", ".ansible_vault_password",
        "--check",
        "--diff"
    ]

    print("[execute_script] Previewing proposed changes...")
    print(f"[execute_script] {' '.join(preview_cmd)}")

    preview = subprocess.run(
        preview_cmd,
        capture_output=True,
        text=True
    )

    if preview.returncode != 0:
        return json.dumps({
            "status": "failed",
            "stage": "preview",
            "error": preview.stderr,
            "output": preview.stdout
        })

    # Step 2: Display preview to user
    print("\n========== CONFIGURATION PREVIEW ==========")
    print(preview.stdout)
    print("===========================================\n")

    # Step 3: Request permission
    while True:
        permission = input(
            "[Permission required] Apply these changes? (y/n): "
        ).strip().lower()

        if permission == "y":
            break

        elif permission == "n":
            return json.dumps({
                "status": "cancelled",
                "message": "Configuration changes were not applied."
            })

        else:
            print("Invalid input. Enter 'y' or 'n'.")

    # Step 4: Execute actual playbook
    execute_cmd = [
        "ansible-playbook",
        filepath,
        "-i", "hosts.ini",
        "--vault-password-file", ".ansible_vault_password"
    ]

    print("[execute_script] Applying configuration changes...")
    print(f"[execute_script] {' '.join(execute_cmd)}")

    result = subprocess.run(
        execute_cmd,
        capture_output=True,
        text=True
    )

    if result.returncode != 0:
        return json.dumps({
            "status": "failed",
            "stage": "execution",
            "error": result.stderr,
            "output": result.stdout
        })

    return json.dumps({
        "status": "success",
        "filepath": filepath,
        "output": result.stdout,
        "message": "Playbook executed successfully."
    })

@tool
def delete_script(filepath: str) -> str:
    """
    Delete the ansible script located in directory 'playbooks'
    Args:
        filepath: Path to the file that is to be deleted
    """

    directory = filepath.split("/")[-2]
    if directory != "playbooks":
        return json.dumps({
            "status": "failed",
            "error": "Permission denied as wrong path"
        })

    while True:
        permission = input(f"[Permission required] Delete '{filepath}' permenantly? (y/n): ")
        if permission == "y":
            break

        elif permission == "n":
            return json.dumps({
                "status": "failed",
                "error": "Permission denied by user"
            })

        else:  # Invalid input
            print("[Permission required] Invalid input. Enter 'y' or 'n' only.")

    cmd = ["rm", "-f", f"{filepath}"]
    result = subprocess.run(
        cmd,
        capture_output=True,
        text=True
    )

    if result.returncode != 0:
        return json.dumps({
            "status": "failed",
            "error": result.stderr,
            "output": result.stdout
        })

    output = result.stdout

    return json.dumps({
        "status": "success",
        "filepath": filepath,
        "command": " ".join(cmd),
        "output": output
    })


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
