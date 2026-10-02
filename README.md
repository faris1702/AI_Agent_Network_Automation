# AI Agent Network Automation

An AI agent that helps manage a simulated Cisco network using plain-English instructions. The project focuses on using Ansible, so instead of writing out Ansible playbooks manually, we can automate it using an AI agent. It can read device configurations, write Ansible playbooks to change them (only after you approve), and capture and explain network traffic.

The network is simulated in **GNS3**. The agent runs on an **Ubuntu VM** in **Oracle VirtualBox**, which connects to the GNS3 network over a VirtualBox internal network.

**Demo video:** [https://www.youtube.com/watch?v=SQOBbE-cZoo](https://www.youtube.com/watch?v=SQOBbE-cZoo)

**Setup guide:** [Detailed_setup.md](https://github.com/faris1702/AI_Agent_Network_Automation/blob/main/Detailed_setup.md)

<br>

## Features

### 1. Read device configurations
The agent can run `show` commands on the network devices (for example `show ip int br` or `show run`). It then reads the output and answers your questions about the network's current state.

### 2. Change configurations with Ansible, only with your permission
When you ask for a change, the agent writes an Ansible playbook to make it. **Nothing runs until you approve it:**
- The agent shows you the playbook it wrote.
- You review it and decide whether it is correct.
- The playbook runs only after you give explicit permission.

This keeps a person in control of every change and stops the agent from making changes you did not intend.

### 3. Capture and explain network traffic
The agent can capture traffic on the Ubuntu VM's network interfaces with `tcpdump` and save it as a `.pcap` file. It then reads the capture and explains the traffic in plain language.

<br>

## Architecture

![Network Topology](images/gns3/gns3_2.png)

| Component | Role |
|---|---|
| **GNS3** | Simulates the network: Cisco C7200 routers and a C3725 EtherSwitch router |
| **Oracle VirtualBox** | Hosts the Ubuntu VM |
| **Ubuntu VM** | Runs the AI agent, Ansible and `tcpdump` |
| **OpenAI API** | The language model behind the agent |
| **Ansible** (`cisco.ios`) | Runs commands and pushes configuration to the devices over SSH |
| **Ansible Vault** | Stores the device login details in encrypted files |

### IP addressing

| Device | Interface | IP Address |
|---|---|---|
| Ubuntu VM | `enp0s8` (Internal Network to GNS3) | `10.0.11.2/24` |
| R1 | `g2/0` | `10.0.11.3/24` |
| R1 | `g1/0` | `192.168.0.3/24` |
| R1 | `f0/0` | `172.16.0.5/24` |
| R2 | `g1/0` | `192.168.0.4/24` |
| SW1 | `vlan 1` | `172.16.0.6/24` |

R2 and SW1 use R1 as their default gateway. The Ubuntu VM reaches them through static routes via R1.

<br>

## Project Structure

```
AI_Agent_Network_Automation
├── ai_agent_0.py               # The AI agent
├── ai_agent_1.py
├── ai_agent_2.py
├── ai_agent_3.py
├── ai_agent_4.py
├── ai_agent_5.py             # Full script, with output printed nicely
├── test_api_key.py           # Script to test if API key is working
├── configs/                  # Store the configurations of network devices
├── playbooks/                # Store Ansible playbooks created by AI agent
├── packet_captures/          # Store pcap files that the AI agent captured
├── hosts.ini                 # Ansible inventory (R1, R2, SW1)
├── host_vars/                # Encrypted device logins (Ansible Vault)
│   ├── R1/vault.yaml
│   ├── R2/vault.yaml
│   └── SW1/vault.yaml
├── .env                      # OpenAI API key (not committed)
├── .ansible_vault_password   # Vault password file (not committed)
├── requirements.txt          # Python dependencies
├── Detailed_setup.md         # Step-by-step setup guide
└── images/                   # Screenshots used in the setup guide
```

<br>

## Prerequisites

1. GNS3 with Cisco images that support SSH (IOU images do not support SSH)
2. Oracle VirtualBox with an Ubuntu VM
3. VSCode with the Remote - SSH extension (recommended)
4. An LLM API key (this project uses OpenAI)

<br>

## Quick Start

The full setup is in [Detailed_setup.md](https://github.com/faris1702/AI_Agent_Network_Automation/blob/main/Detailed_setup.md). In short:

1. Build the GNS3 topology, set up IP addressing and enable SSH on all devices.
2. Configure the VirtualBox network adapters so the Ubuntu VM is connected to GNS3.
3. On the Ubuntu VM, install Python, Ansible and `tcpdump`. Allow `tcpdump` to run with `sudo` without asking for a password.
4. Create a Python virtual environment and install the dependencies:
    ```
    python3 -m venv venv
    source venv/bin/activate
    pip install -r requirements.txt
    ```
5. Add your OpenAI API key to `.env`:
    ```
    OPENAI_API_KEY="<API_KEY>"
    ```
6. Set up the Ansible inventory (`hosts.ini`), the Vault files in `host_vars/`, and `.ansible_vault_password`.
7. Add routes to the networks behind R1. This must be repeated every time the VM starts:
    ```
    sudo ip route add 192.168.0.0/24 via 10.0.11.3 dev enp0s8
    sudo ip route add 172.16.0.0/24 via 10.0.11.3 dev enp0s8
    ```
8. Run the agent:
    ```
    python3 ai_agent_5.py
    ```

<br>

## Example Prompts

- *"Show me the interface status of R1."*
- *"What is the IP address configured on SW1's VLAN 1?"*
- *"Configure a loopback interface on R2 with IP 2.2.2.2/32."* → the agent writes a playbook and waits for your approval
- *"Capture 20 packets on enp0s8 and explain what you see."*
