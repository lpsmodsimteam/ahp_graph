#!/usr/bin/env python3
"""
Example demonstrating arbitrary key/value attributes on links.

This example shows how to add custom attributes to links in addition to
the standard latency attribute. This provides flexibility for modeling
various link properties such as bandwidth, protocol, reliability, etc.
"""

import sys
sys.path.insert(0, '../src')

from ahp_graph.Device import *
from ahp_graph.DeviceGraph import *


class NetworkSwitch(Device):
    """A simple network switch device."""
    library = 'network.Switch'
    portinfo = PortInfo()
    portinfo.add('port', limit=None, required=False)  # Multi-port

    def __init__(self, name: str):
        super().__init__(name, attr={'switch_type': '10G'})


class Server(Device):
    """A server device."""
    library = 'compute.Server'
    portinfo = PortInfo()
    portinfo.add('nic')  # Network interface

    def __init__(self, name: str):
        super().__init__(name, attr={'cores': 32, 'memory': '256GB'})


def main():
    """Create a simple network topology with diverse link attributes."""
    print("Creating network topology with link attributes...\n")

    graph = DeviceGraph()

    # Create devices
    switch1 = NetworkSwitch('switch1')
    switch2 = NetworkSwitch('switch2')
    server1 = Server('server1')
    server2 = Server('server2')

    # Link servers to switches with different link properties
    # Server 1 has a high-speed, low-latency connection
    graph.link(
        server1.nic,
        switch1.port('port', 0),
        attr={
            'latency': '1ns',
            'bandwidth': '100GB/s',
            'protocol': 'InfiniBand',
            'mtu': 9000,
            'reliability': 0.99999
        }
    )

    # Server 2 has a standard Ethernet connection
    graph.link(
        server2.nic,
        switch1.port('port', 1),
        attr={
            'latency': '10ns',
            'bandwidth': '10GB/s',
            'protocol': 'Ethernet',
            'mtu': 1500,
            'reliability': 0.9999
        }
    )

    # Inter-switch link with high bandwidth
    graph.link(
        switch1.port('port', 2),
        switch2.port('port', 0),
        attr={
            'latency': '5ns',
            'bandwidth': '400GB/s',
            'protocol': 'Ethernet',
            'trunk': True,
            'vlan_ids': [100, 200, 300]
        }
    )

    # Display the graph
    print(graph)
    print("\n" + "="*80 + "\n")

    # Demonstrate accessing link attributes
    print("Link Attributes Summary:")
    print("-" * 80)
    for (p0, p1), attr in graph.links.items():
        print(f"\nLink: {p0} <--> {p1}")
        for key, value in sorted(attr.items()):
            print(f"  {key}: {value}")

    print("\n" + "="*80)
    print("Example complete! Link attributes provide rich metadata for modeling.")


if __name__ == '__main__':
    main()
