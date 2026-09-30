from typing import Annotated, Sequence, TypedDict
from dotenv import load_dotenv  
from langchain_core.messages import BaseMessage, HumanMessage, AIMessage, ToolMessage, SystemMessage
from langchain_openai import ChatOpenAI
from langchain_core.tools import tool
from langgraph.graph.message import add_messages
from langgraph.graph import StateGraph, END
from langgraph.prebuilt import ToolNode
from langgraph.checkpoint.memory import MemorySaver
from datetime import datetime
import subprocess
import json
import os
import yaml

load_dotenv()

class AgentState(TypedDict):
    messages: Annotated[Sequence[BaseMessage], add_messages]
    

@tool
def run_cisco_command(device: str, command: str) -> str:
    """
    Run a command on a Cisco device by running an Ansible command
    and returning the output.

    Args:
       device: The hostname of the Cisco device
       command: The CLI command required to run on the Cisco device
    """
    
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

    result = subprocess.run(
        cmd,
        capture_output=True,
        text=True
    )

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
def display_script(script: str) -> str:
    """
    Displays the ansible yaml script for the user to view.
    Args:
        script: the content of the script
    """

    try:
        print(script)
        return json.dumps({
            "status": "success"
        })

    except Exception as e:
        return json.dumps({
            "status": "failed",
            "error": f"Unable to display script: {e}"
        })

@tool
def execute_script(filepath: str) -> str:
    """
    Executes the ansible yaml script in the stated path
    Args:
        filepath: Path to the script that will be ran
    """

    print()
    print("[Permission required]")
    while True:
        permission = input(f"Do you want to run {filepath}? (y/n): ")
        if permission == "y":
            break
        
        elif permission == "n":
            return json.dumps({
                "status": "failed",
                "error": "Permission denied by user"
            })

        else:  # Invalid input
            print("Invalid input. Enter 'y' or 'n' only.")

    cmd = [
        "ansible-playbook",
        filepath,
        "-i",
        "hosts.ini",
        "--vault-password-file",
        ".ansible_vault_password"
    ]

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
        "command": cmd,
        "output": output
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
    
    print()
    print("[Permission required]")
    while True:
        permission = input(f"Delete '{filepath}' permenantly? (y/n): ")
        if permission == "y":
            break
        
        elif permission == "n":
            return json.dumps({
                "status": "failed",
                "error": "Permission denied by user"
            })

        else:  # Invalid input
            print("Invalid input. Enter 'y' or 'n' only.")

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
        "command": cmd,
        "output": output
    })



tools = [run_cisco_command, backup_cisco_config, check_hosts_file, 
        save_ansible_playbook, validate_yaml, execute_script, delete_script]
llm = ChatOpenAI(model="gpt-4o").bind_tools(tools)

def agent(state: AgentState) -> AgentState:
    system_prompt = SystemMessage(content="""
    You are a network automation assistant and will be helping me run commands to Cisco network device
    - If the user wants to end the session, he needs to enter 'exit'
    - If a particular device needs to be checked, always run the check_hosts_file tool to make sure that the device exists.
    The tool can also be used to determine what devices are in the network
    - If the user wants to view details about the Cisco device, user the run_cisco_command tool. Understand what the user
    wants and give the correct command to the tool. The actual output from the Cisco command will be shown, so just summarise
    what is given instead of displaying the whole output again.
    - If the user wants to save the running configuration of the cisco device to a text file, use the tool backup_cisco_config()
    and pass the device hostname. If you are unsure whether if the user wants to save the config on the device or to save the config 
    to a text file, ask the user.
    - If the user wants to create an ansible script or change a configuration, 
    - If the user wants to create an ansible script or change a configuration:
    1. Check the existing configuration of the device using run_cisco_command.
    2. Determine whether the requested change is required.
    3. Generate the Ansible YAML playbook.
    4. The playbook MUST use:
       connection: network_cli
       gather_facts: false
       and fully qualified Cisco module names such as:
       cisco.ios.ios_interfaces
    5. Validate the YAML using validate_yaml.
    6. Display the generated playbook to the user.
    7. Ask the user whether they are satisfied with the playbook.
    8. If the user requests changes, modify the playbook and repeat validation.
    9. If the user is satisfied, call save_ansible_playbook.
    10. IMPORTANT: save_ansible_playbook generates the actual filename, including the timestamp.
    11. After save_ansible_playbook succeeds, ALWAYS use the exact "filename" value returned by that tool as the filepath for execute_script.
    12. NEVER construct, guess, reuse, or modify the filepath for execute_script.
    13. NEVER execute a filename that was generated before save_ansible_playbook returned its result.
    14. If save_ansible_playbook returns: {"status": "success", "filename": "playbooks/example_20260928_183000.yaml"}
        then execute_script MUST receive exactly:
        filepath="playbooks/example_20260928_183000.yaml"
    15. Save the current config of the device before executing the script
    16. Only execute the exact file returned by save_ansible_playbook.
    17. After execution, check the device configuration using run_cisco_command to verify that the requested change was successful.
    18. If the execution fails and there is a need to create a new script, delete the old one using delete_script tool amd repeat the process
    19. Once the script is successfully executed, unless the user specifically asks to create the script, delete the script.
    EXAMPLE 1:

    User request:
    "Shutdown G2/0 on R2"

    Correct output:

    ---
    - name: Shut down interface G2/0 on R2
    hosts: R2
    gather_facts: false
    connection: network_cli

    tasks:
        - name: Shutdown G2/0
        cisco.ios.ios_interfaces:
            config:
            - name: GigabitEthernet2/0
                enabled: false

    EXAMPLE 2:

    User request:
    "Enable G2/0 on R2"

    Correct output:

    ---
    - name: Enable interface G2/0 on R2
    hosts: R2
    gather_facts: falseckear

    connection: network_cli

    tasks:
        - name: Enable G2/0
        cisco.ios.ios_interfaces:
            config:
            - name: GigabitEthernet2/0
                enabled: true

    EXAMPLE 3:

    User request:
    "Show the interface status on R2"

    Correct output:

    ---
    - name: Show interface status on R2
    hosts: R2
    gather_facts: false
    connection: network_cli

    tasks:
        - name: Show IP interface brief
        cisco.ios.ios_command:
            commands:
            - show ip interface brief
    """)

    response = llm.invoke([system_prompt] + state["messages"]) # state["messages"] is the human prompt
    return {"messages": [response]}  # this updates the state

def should_continue(state: AgentState): 
    messages = state["messages"]
    last_message = messages[-1]
    if last_message.tool_calls: # if don't need tool call anymore, end
        return "continue"
    else:
        return "end"

graph = StateGraph(AgentState)
graph.add_node("agent", agent)
graph.add_node("tools", ToolNode(tools))

graph.set_entry_point("agent")
graph.add_conditional_edges(
    "agent",
    should_continue,
    {
        "continue": "tools",
        "end": END
    }
)
graph.add_edge("tools", "agent")

memory = MemorySaver()
app = graph.compile(checkpointer=memory)

def print_stream(stream, prev_msg_count):
    printed_messages = prev_msg_count

    for s in stream:
        messages = s["messages"]

        for message in messages[printed_messages:]:
            if isinstance(message, ToolMessage):
                if message.name == "run_cisco_command":
                    data = json.loads(message.content)
                    print(f"\n===== 🔧 TOOL - RUN_CISCO_COMMAND =====")
                    print(f"Device: {data['device']}")
                    print(f"Command: {data['command']}")
                    if data.get("status") == "success":
                        print(data["output"])
                    else:
                        print(data.get("error", "Unknown error"))  # If 'error' doesnt exist, prints "Unknown error"
                    print("==========================================================")

                elif message.name == "backup_cisco_config":
                    data = json.loads(message.content)
                    print(f"\n===== 🔧 TOOL - BACKUP_CISCO_CONFIG =====")
                    print(f"Device: {data['device']}")
                    if data.get("status") == "success":
                        print(f"Filename: {data['filename']}")
                        print(data["message"])
                    else:
                        print(data.get("error", "Unknown error"))
                    print("==========================================================")

                elif message.name == "check_hosts_file":
                    data = json.loads(message.content)
                    print(f"\n===== 🔧 TOOL - CHECK_HOSTS_FILE =====")
                    if data.get("status") == "success":
                        # print(data["content"])
                        print("Successfully retrieved")
                    else:
                        print(data.get("error", "Unknown error"))
                    print("==========================================================")
                
                elif message.name == "save_ansible_playbook":
                    data = json.loads(message.content)
                    print(f"\n===== 🔧 TOOL - SAVE_ANSIBLE_PLAYBOOK =====")
                    if data.get("status") == "success":
                        print(f"Playbook saved to {data["filename"]}")
                    else:
                        print(data.get("error", "Unknown error"))
                    print("==========================================================")

                elif message.name == "validate_yaml":
                    data = json.loads(message.content)
                    print(f"\n===== 🔧 TOOL - VALIDATE_YAML =====")
                    if data.get("status") == "success":
                        print(f"Ansible playbook is valid.")
                    else:
                        print(data.get("error", "Unknown error"))
                    print("==========================================================")

                elif message.name == "execute_script":
                    data = json.loads(message.content)
                    print(f"\n===== 🔧 TOOL - EXECUTE_SCRIPT =====")
                    if data.get("status") == "success":
                        print(f"Script {data["filepath"]}")
                    else:
                        print(data.get("error", "Unknown error"))
                    print("==========================================================")

                else:
                    print(f"\n🔧 TOOL OUTPUT - ({message.name}):")
                    print(message.content)

            elif isinstance(message, AIMessage) and message.content:
                print(f"\n🤖 AI: {message.content}")

        printed_messages = len(messages)

while True:
    user_input = input("\n🧑 User: ")

    if user_input.lower() in ["exit", "quit"]:
        print("Exiting...")
        break

    inputs = {"messages": [HumanMessage(content=user_input)]}
    config = {"configurable": {"thread_id": "cisco-session"}}

    # Get the current number of messages before this request
    current_state = app.get_state(config)
    prev_msg_count = len(current_state.values.get("messages", []))

    print_stream(
        app.stream(
            inputs,
            config=config,
            stream_mode="values"
        ),
        prev_msg_count
    )


