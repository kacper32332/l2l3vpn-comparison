#!/usr/bin/python

from mininet.net import Mininet
from mininet.node import OVSKernelSwitch, RemoteController
from mininet.cli import CLI
from mininet.log import setLogLevel, info
from mininet.link import TCLink
import os

def run_final_mpls():
    net = Mininet( switch=OVSKernelSwitch, link=TCLink )

    number_of_switches = 1
    number_of_hosts_per_sw = 2
    number_of_hosts = number_of_switches * number_of_hosts_per_sw

    def create_hosts_r1(number_of_switches, number_of_hosts_per_sw):
        for i in range(1, number_of_switches + 1):
            sw = net.addSwitch('s%d' % i, protocols='OpenFlow13')
            net.addLink(sw, net['r1'], port1=1, port2=3+i)
            for j in range(1, number_of_hosts_per_sw + 1):
                hostname = 'h%d%d' % (i, j)
                ip_address = '192.168.%d.%d/24' % (i, j)
                net.addHost(hostname, ip=ip_address)
                net.addLink(hostname, sw, port2=j+1)


    def create_hosts_r4(number_of_switches, number_of_hosts_per_sw):
        for i in range(1, number_of_switches + 1):
            placeholder = number_of_switches + i
            sw = net.addSwitch('s%d' % placeholder, protocols='OpenFlow13')
            net.addLink(sw, net['r4'], port1=1, port2=3+i)
            for j in range(1, number_of_hosts_per_sw + 1):
                hostname = 'h%d%d' % (placeholder, j)
                ip_address = '192.168.%d.%d/24' % (number_of_switches+i, j)
                net.addHost(hostname, ip=ip_address)
                net.addLink(hostname, sw, port2=j+1)


    def create_core_routers():
        for i in range(1, 5):
            net.addSwitch('r%d' % i, protocols='OpenFlow13')


    def create_topology(x,y):
        create_core_routers()
        create_hosts_r1(x,y)
        create_hosts_r4(x,y)


    info( '*** Starting network\n' )

    create_topology(number_of_switches, number_of_hosts_per_sw)

    net.addLink(net['r1'], net['r2'], port1=2, port2=1)
    net.addLink(net['r1'], net['r3'], port1=3, port2=1)
    net.addLink(net['r4'], net['r2'], port1=2, port2=2)
    net.addLink(net['r4'], net['r3'], port1=3, port2=2)

    net.start()

    info( '*** Configuring Host Routing and ARP\n' )

    enumerated_switches = [s for s in net.switches if s.name.startswith('s')]
    print(len(enumerated_switches))

    for i in range(1, len(enumerated_switches) + 1):
        for j in range(1, number_of_hosts_per_sw + 1):
            for k in range(1, len(enumerated_switches) + 1):
                if i != k:
                    net['h%d%d' % (i, j)].cmd("ip route add 192.168.%d.0/24 dev h%d%d-eth0" % (k, i, j))

    net.staticArp()

    info( '*** Pushing Flows...\n' )

    def add(sw, flow):
        # Added -O OpenFlow13 to ensure MPLS support
        # Added explicit priorities to prevent ambiguity
        os.system('ovs-ofctl -O OpenFlow13 add-flow {} "{}"'.format(sw, flow))

    subnet_map = {}
    for i in range(1, len(enumerated_switches) + 1):
        subnet_map['192.168.%d.0/24' % i] = i*100

    VPN_ODD = 11
    VPN_EVEN = 12

    def config_edge_switch(sw, my_subnet):
        for i in range(1, len(enumerated_switches) + 1):
            for j in range(1, number_of_hosts_per_sw + 1):
                if j % 2 == 1:
                    vpn_id = VPN_ODD
                else:
                    vpn_id = VPN_EVEN
                if ('192.168.%d.0/24' % i) == my_subnet:
                    add('s%d' % sw, 'table:0, priority=100, ip, nw_src=192.168.%d.%d, actions=write_metadata:%d goto_table:1' % (i, j, vpn_id))
        add('s%d' % sw, 'table:0, priority=100, in_port=1, eth_type=0x8847, actions=pop_mpls:0x8847,goto_table:2')

        for vpn_id in [VPN_ODD, VPN_EVEN]:
            add('s%d' % sw, 'table:1, priority=200, metadata=%d, arp, actions=flood' % (vpn_id))

            for remote_subnet in subnet_map.keys():
                if my_subnet not in remote_subnet:
                    outer_label = subnet_map[remote_subnet]
                    add('s%d' % sw, 'table:1, priority=100, metadata=%d, ip, nw_dst=%s, actions=push_mpls:0x8847,set_field:%d->mpls_label,'
                        'push_mpls:0x8847,set_field:%d->mpls_label,output:1' % (vpn_id, remote_subnet, vpn_id, outer_label))

        # local switching
        for i in range(1, len(enumerated_switches) + 1):
            for j in range(1, number_of_hosts_per_sw + 1):
                if ('192.168.%d.0/24' % i) == my_subnet:
                    if j % 2 == 1:
                        vpn_id = VPN_ODD
                    else:
                        vpn_id = VPN_EVEN
                    add('s%d' % sw, 'table:1, priority=150, metadata=%d, ip, nw_dst=192.168.%d.%d, actions=output:%d' % (vpn_id, i, j, j+1))

        # table 2. pop mpls label and go to table 3
        for j in range(1, number_of_hosts_per_sw + 1):
            if j % 2 == 1:
                vpn_id = VPN_ODD
                add('s%d' % sw, 'table:2, priority=100, mpls, mpls_label=%d, actions=pop_mpls:0x0800, write_metadata:%d goto_table:3' % (vpn_id, vpn_id))
                add('s%d' % sw, 'table:3, priority=100, metadata=%d, ip, nw_dst=192.168.%d.%d, actions=output:%d' % (vpn_id, sw, j, j+1))
            else:
                vpn_id = VPN_EVEN
                add('s%d' % sw, 'table:2, priority=100, mpls, mpls_label=%d, actions=pop_mpls:0x0800, write_metadata:%d goto_table:4' % (vpn_id, vpn_id))
                add('s%d' % sw, 'table:4, priority=100, metadata=%d, ip, nw_dst=192.168.%d.%d, actions=output:%d' % (vpn_id, sw, j, j+1))


    for i in range(1, len(enumerated_switches) + 1):
        config_edge_switch(i, '192.168.%d.0/24' % i)

    def config_core_switches():
        total_pe_switches = 2 * number_of_switches

        for i in range(1, total_pe_switches + 1):
            label = i * 100

            if i <= number_of_switches:
                add('r2', 'priority=100, mpls, mpls_label=%d, actions=output:1' % label)
                add('r3', 'priority=100, mpls, mpls_label=%d, actions=output:1' % label)
            else:
                add('r2', 'priority=100, mpls, mpls_label=%d, actions=output:2' % label)
                add('r3', 'priority=100, mpls, mpls_label=%d, actions=output:2' % label)

            if i <= number_of_switches:
                out_port = 3 + i
                add('r1', 'priority=100, mpls, mpls_label=%d, actions=output:%d' % (label, out_port))
            else:
                if label % 200 != 0:
                    add('r1', 'priority=100, mpls, mpls_label=%d, actions=output:2' % label) # Via R2
                else:
                    add('r1', 'priority=100, mpls, mpls_label=%d, actions=output:3' % label) # Via R3

            if i > number_of_switches:
                k = i - number_of_switches
                out_port = 3 + k
                add('r4', 'priority=100, mpls, mpls_label=%d, actions=output:%d' % (label, out_port))
            else:
                if label % 200 != 0:
                    add('r4', 'priority=100, mpls, mpls_label=%d, actions=output:2' % label) # Via R2
                else:
                    add('r4', 'priority=100, mpls, mpls_label=%d, actions=output:3' % label) # Via R3

    config_core_switches()

    net.pingAll(timeout=0.1)

    CLI( net )
    net.stop()

if __name__ == '__main__':
    setLogLevel( 'info' )
    run_final_mpls()
