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
from pathlib import Path

from system_prompt_2 import SYSTEM_PROMPT
from tools.ansible_tools import (
    run_cisco_command,
    run_ping_command,
    backup_cisco_config,
    check_hosts_file,
    validate_yaml,
    save_ansible_playbook,
    display_ansible_script,
    execute_script,
    delete_script
)

from tools.packet_capture_tools import (
    check_network_interfaces,
    capture_packets,
    read_packet_capture
)

from tools.librenms_tools import (
    get_network_devices,
    get_device_health,
    get_device_interfaces,
    get_device_availability,
    get_device_outages,
    get_network_alerts
)

load_dotenv()

class AgentState(TypedDict):
    messages: Annotated[Sequence[BaseMessage], add_messages]

def print_with_label(label, text):
    lines = text.splitlines()
    for line in lines:
        print(f"[{label}] {line}")

@tool
def read_documentation() -> str:
    """
    Reads documentation.txt to understand the network architecture.
    """
    print(f"[read_documentation] 🔧 TOOL CALL: READ_DOCUMENTATION")

    filename = "documentation.txt"

    try:
        with open(filename, "r", encoding="utf-8") as file:
            content = file.read()

        return json.dumps({
            "status": "success",
            "filename": filename,
            "output": content
        })

    except FileNotFoundError:
        return json.dumps({
            "status": "failed",
            "error": f"File '{filename}' does not exist."
        })

    except Exception as e:
        return json.dumps({
            "status": "failed",
            "error": f"Failed to read documentation: {str(e)}"
        })


ansible_tools = [
    run_cisco_command,
    run_ping_command,
    backup_cisco_config,
    check_hosts_file,
    save_ansible_playbook,
    display_ansible_script,
    validate_yaml,
    execute_script,
    delete_script
]

packet_capture_tools = [
    check_network_interfaces,
    capture_packets,
    read_packet_capture
]

librenms_tools = [
    get_network_devices,
    get_device_health,
    get_device_interfaces,
    get_device_availability,
    get_device_outages,
    get_network_alerts
]

tools = [read_documentation, *ansible_tools, *packet_capture_tools, *librenms_tools]
llm = ChatOpenAI(model="gpt-5.4-mini").bind_tools(tools)

def agent(state: AgentState) -> AgentState:
    system_prompt = SystemMessage(content=SYSTEM_PROMPT)

    response = llm.invoke([system_prompt] + state["messages"]) # state["messages"] is the human prompt
    return {"messages": [response]}  # this updates the state

def should_continue(state: AgentState):
    messages = state["messages"]
    last_message = messages[-1]
    if last_message.tool_calls: # if don't need tool call anymore, end
        return "continue"
    else:
        return "end"


## ------------- Graph ---------------
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
## ----------------------------------------


def print_stream(stream, prev_msg_count):
    printed_messages = prev_msg_count

    for s in stream:
        messages = s["messages"]

        for message in messages[printed_messages:]:
            if isinstance(message, ToolMessage):
                if message.name == "run_cisco_command":
                    data = json.loads(message.content)
                    print(f"[{message.name}] Device: {data['device']}")
                    print(f"[{message.name}] Command: {data['command']}")
                    if data.get("status") == "success":
                        # print(data["output"])
                        print_with_label(message.name, data["output"])
                    else:
                        print(f"[{message.name}] Error")
                        print_with_label(message.name, data.get("error", "Unknown error"))  # If 'error' doesnt exist, prints "Unknown error"

                elif message.name == "backup_cisco_config":
                    data = json.loads(message.content)
                    if data.get("status") == "success":
                        print(f"[{message.name}] Filename: {data['filename']}")
                        print_with_label(message.name, data["message"])
                    else:
                        print(f"[{message.name}] Error")
                        print_with_label(message.name, data.get("error", "Unknown error"))

                elif message.name == "check_hosts_file":
                    data = json.loads(message.content)
                    print(f"[{message.name}] 🔧 TOOL CALL: CHECK_HOSTS_FILE ")
                    if data.get("status") == "success":
                        print(f"[{message.name}] Successfully retrieved")
                    else:
                        print(f"[{message.name}] Error")
                        print_with_label(message.name, data.get("error", "Unknown error"))

                elif message.name == "save_ansible_playbook":
                    data = json.loads(message.content)
                    print(f"[{message.name}] 🔧 TOOL CALL: SAVE_ANSIBLE_PLAYBOOK")
                    if data.get("status") == "success":
                        print(f"[{message.name}] Playbook saved to {data["filename"]}")
                    else:
                        print(f"[{message.name}] Error")
                        print_with_label(message.name, data.get("error", "Unknown error"))

                elif message.name == "display_ansible_script":
                    data = json.loads(message.content)
                    print(f"[{message.name}] 🔧 TOOL CALL: DISPLAY_ANSIBLE_SCRIPT")
                    if data.get("status") == "success":
                        print_with_label(message.name, data["output"])
                    else:
                        print(f"[{message.name}] Error")
                        print_with_label(message.name, data.get("error", "Unknown error"))

                elif message.name == "validate_yaml":
                    data = json.loads(message.content)
                    print(f"[{message.name}] 🔧 TOOL CALL: VALIDATE_YAML")
                    if data.get("status") == "success":
                        print(f"[{message.name}] Ansible playbook is valid.")
                    else:
                        print(f"[{message.name}] Error")
                        print_with_label(message.name, data.get("error", "Unknown error"))

                elif message.name == "execute_script":
                    data = json.loads(message.content)
                    if data.get("status") == "success":
                        print(f"[{message.name}] {data["filepath"]} executed successfully")
                    else:
                        print(f"[{message.name}] Error")
                        print_with_label(message.name,data.get("error", "Unknown error"))

                elif message.name == "delete_script":
                    data = json.loads(message.content)
                    print(f"[{message.name}] 🔧 TOOL CALL: DELETE_SCRIPT")
                    if data.get("status") == "success":
                        print(f"[{message.name}] {data["command"]}")
                        print(f"[{message.name}] {data["filepath"]} deleted successfully")
                    else:
                        print(f"[{message.name}] Error")
                        print_with_label(message.name,data.get("error", "Unknown error"))

                elif message.name == "check_network_interfaces":
                    data = json.loads(message.content)
                    print(f"[{message.name}] 🔧 TOOL CALL: CHECK_NETWORK_INTERFACES")
                    print(f"[{message.name}] {data["command"]}")
                    if data.get("status") == "success":
                        print_with_label(message.name, data["output"])
                    else:
                        print(f"[{message.name}] Error")
                        print_with_label(message.name,data.get("error", "Unknown error"))

                elif message.name == "capture_packets":
                    data = json.loads(message.content)
                    if data.get("status") == "success":
                        print(f"[{message.name}] Packet capture successfully saved to {data["filepath"]}")
                    else:
                        print(f"[{message.name}] Error")
                        print_with_label(message.name,data.get("error", "Unknown error"))

                elif message.name == "read_packet_capture":
                    data = json.loads(message.content)
                    print(f"[{message.name}] 🔧 TOOL CALL: READ_PACKET_CAPTURE")
                    if data.get("status") == "success":
                        print(f"[{message.name}] {data["command"]}")
                        print(f"[{message.name}] Reaing {data["filepath"]}")
                    else:
                        print(f"[{message.name}] Error")
                        print_with_label(message.name,data.get("error", "Unknown error"))

                elif message.name == "read_documentation":
                    data = json.loads(message.content)
                    if data.get("status") == "success":
                        print(f"[{message.name}] Documentation read")
                    else:
                        print(f"[{message.name}] Error")
                        print_with_label(message.name,data.get("error", "Unknown error"))


                else:
                    print(f"🔧 TOOL OUTPUT - ({message.name}):")
                    print(message.content)

            elif isinstance(message, AIMessage) and message.content:
                print(f"\n🤖 AI: {message.content}")

        printed_messages = len(messages)


## ---------- Main Conversation loop ----------------
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
# -----------------------------------------------------------
