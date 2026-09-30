from typing import Annotated, Sequence, TypedDict
from dotenv import load_dotenv  
from langchain_core.messages import BaseMessage, HumanMessage, AIMessage, ToolMessage, SystemMessage
from langchain_openai import ChatOpenAI
from langchain_core.tools import tool
from langgraph.graph.message import add_messages
from langgraph.graph import StateGraph, END
from langgraph.prebuilt import ToolNode
import subprocess
import json

load_dotenv()

class AgentState(TypedDict):
    messages: Annotated[Sequence[BaseMessage], add_messages]


@tool
def run_cisco_command(device: str, command: str) -> str:
    """Run a command on a Cisco device by running an Ansible command
    and returning the output.

    Args:
       device: The hostname of the Cisco device
       command: The CLI command required to run on the Cisco device
    """

    cmd = [
        "ansible",
        device,
        "-i",
        "hosts.ini",
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
        return f"Ansible error:\n{result.stderr}"

    # Remove "R1 | SUCCESS => "
    output = result.stdout.split("=>", 1)[1].strip()

    # Convert Ansible output into Python dictionary
    data = json.loads(output)

    # Extract stdout_lines
    stdout_lines = data["stdout_lines"]

    # Flatten the list
    lines = stdout_lines[0]

    return "\n".join(lines)


tools = [run_cisco_command]
llm = ChatOpenAI(model="gpt-4o").bind_tools(tools)

def agent(state: AgentState) -> AgentState:
    system_prompt = SystemMessage(content=f"""
    You are a network automation assistant and will be helping me run commands to Cisco network device
    - If the user wants to view details about the Cisco device, user the run_cisco_command tool
    - If the user wants to do something other than 'show' commands, tell the user it is currently not possible
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

app = graph.compile()

def print_stream(stream):
    for s in stream:
        message = s["messages"][-1]

        if isinstance(message, ToolMessage):
            print("\n🔧 TOOL OUTPUT:")
            print(message.content)

        elif isinstance(message, AIMessage) and message.content:
            print("\n🤖 AI:")
            print(message.content)


while True:

    user_input = input("\nUser: ")

    if user_input.lower() in ["exit", "quit"]:
        print("Exiting...")
        break

    inputs = {"messages": [HumanMessage(content=user_input)]}

    print_stream(
        app.stream(
            inputs,
            stream_mode="values"
        )
    )


