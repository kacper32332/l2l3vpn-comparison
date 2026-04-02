#!/usr/bin/python

from mininet.topo import Topo
from mininet.net import Mininet
from mininet.node import Node, OVSSwitch
from mininet.log import setLogLevel, info
from mininet.cli import CLI

#    KONFIGURACJA PARAMETRÓW SYMULACJI
HOSTS_PER_VPN = 2   # Liczba hostów na jeden VPN w jednej lokalizacji
NUM_SITES = 4       # Liczba lokalizacji

#    DEFINICJA ROUTERA
class LinuxRouter(Node):
    def config(self, **params):
        super(LinuxRouter, self).config(**params)
        
        self.cmd('sysctl -w net.ipv4.ip_forward=1')
        
        self.cmd('sysctl -w net.ipv4.conf.all.rp_filter=0')
        self.cmd('sysctl -w net.ipv4.conf.default.rp_filter=0')
        
        for intf in self.intfList():
            if intf.name != 'lo':
                self.cmd('sysctl -w net.ipv4.conf.{}.rp_filter=0'.format(intf.name))
                self.cmd('ethtool -K {} tx off rx off'.format(intf.name))
        
        self.cmd('modprobe vxlan') 

    def terminate(self):
        self.cmd('sysctl -w net.ipv4.ip_forward=0')
        super(LinuxRouter, self).terminate()

#   DEFINICJA TOPOLOGII SIECI
class CoreOverlayTopo(Topo):
    def build(self):
        # Routery Szkieletowe
        r1 = self.addNode('r1', cls=LinuxRouter)
        r2 = self.addNode('r2', cls=LinuxRouter)
        r3 = self.addNode('r3', cls=LinuxRouter)
        r4 = self.addNode('r4', cls=LinuxRouter)

        # Routery Brzegowe
        edge_routers = {}
        for i in range(1, NUM_SITES + 1):
            name = 'rs{}'.format(i)
            edge_routers[i] = self.addNode(name, cls=LinuxRouter)

        # Warstwa Dostępowa - Switch + Hosty
        for i in range(1, NUM_SITES + 1):
            sw_name = 's{}'.format(i)
            rs_name = 'rs{}'.format(i)
            
            # Standardowy switch OVS
            current_switch = self.addSwitch(sw_name)
            
            uplink_port = (HOSTS_PER_VPN * 2) + 1
            self.addLink(current_switch, edge_routers[i], port1=uplink_port, intfName2='{}-eth0'.format(rs_name))

            # Generowanie Hostów VPN A
            for h_idx in range(1, HOSTS_PER_VPN + 1):
                h_name = 'H{}_A{}'.format(i, h_idx)
                h_ip = '192.168.0.{}/24'.format(i*10 + h_idx)
                h_mac = '00:00:00:0a:{:02x}:{:02x}'.format(i, h_idx)
                
                host = self.addHost(h_name, ip=h_ip, mac=h_mac)
                self.addLink(host, current_switch, port2=h_idx)

            # Generowanie Hostów VPN B
            for h_idx in range(1, HOSTS_PER_VPN + 1):
                h_name = 'H{}_B{}'.format(i, h_idx)
                h_ip = '192.168.1.{}/24'.format(i*10 + h_idx)
                h_mac = '00:00:00:0b:{:02x}:{:02x}'.format(i, h_idx)

                host = self.addHost(h_name, ip=h_ip, mac=h_mac)
                switch_port = h_idx + HOSTS_PER_VPN
                self.addLink(host, current_switch, port2=switch_port)

        # Połączenia Fizyczne w rdzeniu
        self.addLink(edge_routers[1], r1, intfName1='rs1-eth1', intfName2='r1-eth0')
        self.addLink(edge_routers[3], r1, intfName1='rs3-eth1', intfName2='r1-eth3')
        self.addLink(edge_routers[2], r2, intfName1='rs2-eth1', intfName2='r2-eth0')
        self.addLink(edge_routers[4], r2, intfName1='rs4-eth1', intfName2='r2-eth3')

        self.addLink(r1, r3, intfName1='r1-eth1', intfName2='r3-eth1')
        self.addLink(r1, r4, intfName1='r1-eth2', intfName2='r4-eth1')
        self.addLink(r3, r2, intfName1='r3-eth2', intfName2='r2-eth1')
        self.addLink(r4, r2, intfName1='r4-eth2', intfName2='r2-eth2')

#   RUN
def run():
    topo = CoreOverlayTopo()
    net = Mininet(topo=topo, switch=OVSSwitch, controller=None)
    net.start()

    # ADRESACJA IP
    info( '*** Configuring IP Addresses for Core and Edge links\n' )
    
    net['rs1'].cmd('ip addr add 192.168.101.2/24 dev rs1-eth1')
    net['rs1'].cmd('ip link set dev rs1-eth1 up')
    net['r1'].cmd('ip addr add 192.168.101.1/24 dev r1-eth0')
    net['r1'].cmd('ip link set dev r1-eth0 up')
    
    net['rs3'].cmd('ip addr add 192.168.103.2/24 dev rs3-eth1')
    net['rs3'].cmd('ip link set dev rs3-eth1 up')
    net['r1'].cmd('ip addr add 192.168.103.1/24 dev r1-eth3')
    net['r1'].cmd('ip link set dev r1-eth3 up')
    
    net['rs2'].cmd('ip addr add 192.168.102.2/24 dev rs2-eth1')
    net['rs2'].cmd('ip link set dev rs2-eth1 up')
    net['r2'].cmd('ip addr add 192.168.102.1/24 dev r2-eth0')
    net['r2'].cmd('ip link set dev r2-eth0 up')
    
    net['rs4'].cmd('ip addr add 192.168.104.2/24 dev rs4-eth1')
    net['rs4'].cmd('ip link set dev rs4-eth1 up')
    net['r2'].cmd('ip addr add 192.168.104.1/24 dev r2-eth3')
    net['r2'].cmd('ip link set dev r2-eth3 up')

    net['r1'].cmd('ip addr add 192.168.13.1/24 dev r1-eth1')
    net['r1'].cmd('ip addr add 192.168.14.1/24 dev r1-eth2')
    net['r1'].cmd('ip link set dev r1-eth1 up')
    net['r1'].cmd('ip link set dev r1-eth2 up')

    net['r2'].cmd('ip addr add 192.168.32.2/24 dev r2-eth1')
    net['r2'].cmd('ip addr add 192.168.42.2/24 dev r2-eth2')
    net['r2'].cmd('ip link set dev r2-eth1 up')
    net['r2'].cmd('ip link set dev r2-eth2 up')

    net['r3'].cmd('ip addr add 192.168.13.3/24 dev r3-eth1')
    net['r3'].cmd('ip addr add 192.168.32.3/24 dev r3-eth2')
    net['r3'].cmd('ip link set dev r3-eth1 up')
    net['r3'].cmd('ip link set dev r3-eth2 up')

    net['r4'].cmd('ip addr add 192.168.14.4/24 dev r4-eth1')
    net['r4'].cmd('ip addr add 192.168.42.4/24 dev r4-eth2')
    net['r4'].cmd('ip link set dev r4-eth1 up')
    net['r4'].cmd('ip link set dev r4-eth2 up')

    # KONFIGURACJA ROUTINGU STATYCZNEGO W RDZENIU
    info( '*** Configuring Static IP Routing in Core\n' )
    
    net['rs1'].cmd('ip route add default via 192.168.101.1')
    net['rs3'].cmd('ip route add default via 192.168.103.1')
    net['rs2'].cmd('ip route add default via 192.168.102.1')
    net['rs4'].cmd('ip route add default via 192.168.104.1')

    net['r1'].cmd('ip route add 192.168.102.0/24 via 192.168.13.3')
    net['r1'].cmd('ip route add 192.168.104.0/24 via 192.168.13.3')
    
    net['r3'].cmd('ip route add 192.168.102.0/24 via 192.168.32.2')
    net['r3'].cmd('ip route add 192.168.104.0/24 via 192.168.32.2')

    net['r2'].cmd('ip route add 192.168.101.0/24 via 192.168.42.4')
    net['r2'].cmd('ip route add 192.168.103.0/24 via 192.168.42.4')
    
    net['r4'].cmd('ip route add 192.168.101.0/24 via 192.168.14.1')
    net['r4'].cmd('ip route add 192.168.103.0/24 via 192.168.14.1')

    # KONFIGURACJA VXLAN
    info( '*** Configuring VXLAN on Edge Routers (Single Bridge Mode)\n' )
    
    rs_ips = {
        'rs1': '192.168.101.2',
        'rs3': '192.168.103.2',
        'rs2': '192.168.102.2',
        'rs4': '192.168.104.2'
    }

    def config_edge_vxlan(r_name):
        phy_intf = '{}-eth0'.format(r_name)
        net[r_name].cmd('ip link set dev {} up'.format(phy_intf))
        
        # Tworzenie wspólnego mostka
        net[r_name].cmd('ip link add br-edge type bridge')
        net[r_name].cmd('ip link set dev br-edge up')
        net[r_name].cmd('ip link set dev {} master br-edge'.format(phy_intf))

        local_ip = rs_ips[r_name]
        
        # Tworzenie interfejsów VXLAN
        net[r_name].cmd('ip link add vxlan10 type vxlan id 10 local {} dstport 4789'.format(local_ip))
        net[r_name].cmd('ip link set dev vxlan10 master br-edge')
        net[r_name].cmd('ip link set dev vxlan10 up')
        
        net[r_name].cmd('ip link add vxlan20 type vxlan id 20 local {} dstport 4789'.format(local_ip))
        net[r_name].cmd('ip link set dev vxlan20 master br-edge')
        net[r_name].cmd('ip link set dev vxlan20 up')

    for i in range(1, NUM_SITES + 1):
        config_edge_vxlan('rs{}'.format(i))

    # KONFIGURACJA PRZEŁĄCZNIKÓW
    info( '*** Configuring Switches with Simple L2 Forwarding (No VLANs)\n' )
    uplink_port = (HOSTS_PER_VPN * 2) + 1

    for i in range(1, NUM_SITES + 1):
        sw_name = 's{}'.format(i)
        net[sw_name].cmd('ovs-vsctl set bridge', sw_name, 'protocols=OpenFlow13')
        net[sw_name].cmd('ovs-ofctl -O OpenFlow13 del-flows', sw_name) 

        # Reguły dla wszystkich hostów
        for src_idx in range(1, (HOSTS_PER_VPN * 2) + 1):
            
            # Reguła 1: Uplink
            net[sw_name].cmd('ovs-ofctl -O OpenFlow13 add-flow', sw_name, 'priority=100,in_port={},actions=output:{}'.format(src_idx, uplink_port))

            # Z routera do hosta
            net[sw_name].cmd('ovs-ofctl -O OpenFlow13 add-flow', sw_name, 'priority=150,in_port={},actions=NORMAL'.format(uplink_port))

            # Ruch lokalny
            net[sw_name].cmd('ovs-ofctl -O OpenFlow13 add-flow', sw_name, 'priority=200,in_port={},actions=NORMAL'.format(src_idx))

    # STATYCZNY ARP
    info( '*** Configuring Static ARP on Hosts\n' )
    all_hosts = [net[h] for h in net.keys() if 'H' in h and 'eth' not in h]

    for h_src in all_hosts:
        for h_dst in all_hosts:
            if h_src == h_dst: continue
            src_subnet = h_src.IP().split('.')[2]
            dst_subnet = h_dst.IP().split('.')[2]
            if src_subnet == dst_subnet:
                h_src.setARP(h_dst.IP(), h_dst.MAC())

    # STATYCZNY FDB / VXLAN
    info( '*** Configuring MAC-Based Tunnel Routing via FDB\n' )
    for h in all_hosts:
        h_name = h.name
        parts = h_name.split('_') 
        if len(parts) < 2: continue 
        
        site_id = int(parts[0].replace('H', ''))
        router_name = 'rs{}'.format(site_id)
        
        h_mac = h.MAC()
        h_ip = h.IP()
        is_vpnA = '192.168.0' in h_ip 
        target_ip = rs_ips[router_name] 

        for curr_r_name in rs_ips.keys():
            if curr_r_name == router_name: continue 

            if is_vpnA: tun_intf = 'vxlan10'
            else: tun_intf = 'vxlan20'

            net[curr_r_name].cmd('bridge fdb add {} dev {} master static'.format(h_mac, tun_intf))
            net[curr_r_name].cmd('bridge fdb add {} dev {} dst {} self permanent'.format(h_mac, tun_intf, target_ip))

    info( '*** Setup Complete.\n' )
    net.pingAll(timeout=0.1) 
    CLI(net)                 
    net.stop()               

if __name__ == '__main__':
    setLogLevel('info')
    run()