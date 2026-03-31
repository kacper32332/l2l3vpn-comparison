Implementation, testing, and demonstration of L2VPN and L3VPN virtual networks using Open vSwitch in a Mininet environment.
# L2VPN and L3VPN Implementation using Open vSwitch & Mininet

## Project Overview
This project focuses on the implementation and analysis of Virtual Private Networks (VPN) at both Layer 2 and Layer 3. Using **Mininet** for network emulation and **Open vSwitch (OVS)** for software-defined switching, the project's main focus is to compare the scalability of L2VPN and L3VPN by analyzing the increase of routing entries in the VRF tables depending on the number of servers (switches) and number of containers (hosts) on each server (switch).

### Objectives:
* **L2VPN (VXLAN/MPLS):** Establishing Ethernet-level connectivity between remote sites.
* **L3VPN:** Implementing MPLS Label Stacking and routing isolation using VRF (Virtual Routing and Forwarding) concepts.
* **Validation:** Comprehensive testing of connectivity and number of routing entries in VRF tables.

---

## Tech Stack
* **Emulation:** Mininet
* **Switching:** Open vSwitch (OVS)
* **Language:** Python (Mininet scripts)
* **Tools:** Wireshark

---

## Network Topology in L3
The project implements a Spine-Leaf topology designed to simulate a provider core network supporting multi-tenant VPN services. The infrastructure is divided into four distinct functional layers:
1. Core Layer (P-routers: r2, r3)
Role: Transit routers (Provider routers).
Mechanism: These nodes operate purely on MPLS label switching.
Design Choice: To maintain simplicity and high performance, the core is "VPN-unaware." It swaps external MPLS transport labels without inspecting customer-specific data, bypassing the need for complex protocols like MP-BGP.

2. Aggregation/Edge Layer (PE-routers: r1, r4)
Role: Provider Edge routers.
Function: Act as the gateway between the access switches and the MPLS core.

3. Access Layer (OVS Edge Switches)
Role: Service classification and encapsulation.
Operations:
Push: Encapsulates incoming Ethernet frames/IP packets with MPLS labels.
Pop: Removes labels from outgoing traffic before delivering it to the destination host.
Isolation: This layer enforces the logical separation of different VPN instances.

4. Host Layer (End Users)
Addressing Scheme: 192.168.i.j/24 (where i = switch ID, j = host ID).
Multi-tenancy (Segmentation):
VPN A (ID 11): Assigned to hosts with an odd index j.
VPN B (ID 12): Assigned to hosts with an even index j.
This setup demonstrates how multiple virtual private networks can securely coexist on the same physical (or emulated) infrastructure.


---

## Getting Started

### Prerequisites
Python, Mininet and Open vSwitch installed on Linux machine.
