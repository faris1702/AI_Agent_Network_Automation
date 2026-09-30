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

tools = [run_cisco_command, backup_cisco_config, check_hosts_file]
llm = ChatOpenAI(model="gpt-4o").bind_tools(tools)

def agent(state: AgentState) -> AgentState:
    system_prompt = SystemMessage(content=f"""
    You are a network automation assistant and will be helping me run commands to Cisco network device
    - If a particular device needs to be checked, always run the check_hosts_file tool to make sure that the device exists.
    The tool can also be used to determine what devices are in the network
    - If the user wants to view details about the Cisco device, user the run_cisco_command tool. Understand what the user
    wants and give the correct command to the tool. The actual output from the Cisco command will be shown, so just summarise
    what is given instead of displaying the whole output again.
    - If the user wants to save the running configuration of the cisco device to a text file, use the tool backup_cisco_config()
    and pass the device hostname. If you are unsure whether if the user wants to save the config on the device or to save the config 
    to a text file, ask the user.
    - If the user wants to do something other than mentioned functions, tell the user it is currently not possible
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
                    print(f"Filename: {data['filename']}")
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
                        print(data["content"])
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


