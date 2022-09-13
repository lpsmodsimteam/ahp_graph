#!/usr/bin/env python3

"""
This module implements support for AHP (Attributed Hierarchical Port) graphs.

This class of graph supports attributes on the nodes (Devices), links that are
connected to named ports on the nodes, and nodes that may be represented by a
hierarchical graph (aka an assembly).
All links are bidirectional.
"""

import os
import collections
import pygraphviz
from .Device import *


class DeviceGraph:
    """
    A DeviceGraph is a graph of Devices and their connections to one another.

    The Devices are nodes and the links connect the DevicePorts on the nodes.
    This implements an AHP (Attributed Hierarchical Port) graph.
    """

    def __init__(self, attr: dict = None) -> None:
        """
        Define an empty DeviceGraph.

        The attributes are considered global parameters shared by all instances
        in the graph. They are only supported at the top-level graph,
        not intemediate graphs (e.g., assemblies).
        The dictionary of links uses a frozenset of DevicePorts as the key
        """
        self.expanding = None
        self.attr = attr if attr is not None else dict()
        self.devices = set()
        self.names = set()
        self.links = dict()
        self.ports = set()

    def __repr__(self) -> str:
        """Pretty print a DeviceGraph with Devices followed by links."""
        lines = list()
        for device in self.devices:
            lines.append(str(device))
        for p0, p1 in self.links:
            lines.append(f"{p0} <--{self.links[frozenset({p0, p1})]}--> {p1}")
        return "\n".join(lines)

    def link(self, p0: DevicePort, p1: DevicePort,
             latency: str = '0s') -> None:
        """
        Link two DevicePorts with latency if provided.

        Links are bidirectional and the key is a frozenset of the two
        DevicePorts. Duplicate links (links between the same DevicePorts)
        are not permitted. Keep in mind that a unique DevicePort is created
        for each port number in a multi-port style port. If the link
        types to not match, then throw an exception. Devices that are linked
        to will be added to the graph automatically.
        Latency is expressed as a string with time units (ps, ns, us...)
        """
        if callable(p0) or callable(p1):
            raise RuntimeError(f"{p0} or {p1} is callable. This probably means"
                               f" you have a multi port and didn't pick a port"
                               f" number (ex. Device.portX(portNum))")

        def link_other_port(p0: DevicePort, p1: DevicePort) -> None:
            """Link a matching port through an expanding assembly."""
            if p0.link is not None:
                p2 = p0.link
                if not self.check_port_types(p1, p2):
                    raise RuntimeError(f'Port type mismatch {p1}, {p2}')
                # remove p0 from the links and connect p1 to p2
                p0.link = None
                p2.link = p1
                p1.link = p2
                self.ports.discard(p0)
                self.ports.add(p1)
                latency = self.links.pop(frozenset({p0, p2}))
                # add the other device to the graph
                self.add(p1.device)
                self.links[frozenset({p1, p2})] = latency

        if self.expanding is not None:
            if p0.device == self.expanding:
                link_other_port(p0, p1)
                return
            elif p1.device == self.expanding:
                link_other_port(p1, p0)
                return

        if p0 in self.ports or p1 in self.ports:
            raise RuntimeError(f'{p0} or {p1} already linked to')

        if not self.check_port_types(p0, p1):
            raise RuntimeError(f'Port type mismatch {p0}, {p1}')

        # Add devices to the graph
        self.add(p0.device)
        self.add(p1.device)

        # Storing the ports in a set so that we can quickly see if they
        # are linked to already
        self.ports |= {p0, p1}
        # Only update the links if neither are connected
        # otherwise we are most likely doing a separate graph expansion and
        # don't want to overwrite the port links that exist
        if p0.link is None and p1.link is None:
            p0.link = p1
            p1.link = p0
        self.links[frozenset({p0, p1})] = latency

    def add(self, device: Device, sub: bool = False) -> None:
        """
        Add a Device to the graph.

        The Device must be a ahp_graph Device. The name must be unique.
        If the Device has submodules, then we add those, as well.
        Do NOT add submodules to a Device after you have added it using
        this function, they will not be included in the DeviceGraph.
        """
        if device in self.devices:
            return

        if self.expanding is not None:
            device.name = f"{self.expanding.name}.{device.name}"
            if (self.expanding.partition is not None
                    and device.partition is None):
                device.partition = self.expanding.partition

        if device.name in self.names:
            raise RuntimeError(f'Device name {device.name} already in graph')

        self.devices.add(device)
        self.names.add(device.name)

        if device.subOwner is not None and not sub:
            dev = device
            while dev.subOwner is not None:
                dev = dev.subOwner
            self.add(dev)

        for (dev, _, _) in device.subs:
            self.add(dev, True)

    def count_devices(self) -> dict:
        """
        Count the Devices in a graph.

        Return a map of Devices to integer counts. The keys are of the
        form "CLASS_MODEL".
        """
        counter = collections.defaultdict(int)
        for device in self.devices:
            counter[device.get_category()] += 1
        return counter

    @staticmethod
    def check_port_types(p0: DevicePort, p1: DevicePort) -> bool:
        """Check that the port types for the two ports match."""
        t0 = p0.device.portinfo[p0.name][1]
        t1 = p1.device.portinfo[p1.name][1]
        return t0 == t1

    def verify_links(self) -> None:
        """Verify that all required ports are linked up."""
        # Create a map of Devices to all ports linked on those Devices.
        d2ports = collections.defaultdict(set)
        for p0, p1 in self.links:
            d2ports[p0.device].add(p0.name)
            d2ports[p1.device].add(p1.name)

        # Walk all Devices and make sure required ports are connected.
        for device in self.devices:
            for name, info in device.portinfo.items():
                if info[2] and name not in d2ports[device]:
                    raise RuntimeError(f"{device.name} requires port {name}")

    def check_partition(self) -> None:
        """Check to make sure the graph has ranks specified for all Devices."""
        for d in self.devices:
            if d.partition is None:
                raise RuntimeError(f"No partition for Device: {d.name}")

    def follow_links(self, rank: int, prune: bool = False) -> None:
        """
        Chase links between ranks.

        Follow links from the specified rank and expand assemblies until links
        are fully defined (links touch library Devices on both sides).
        Optional prune flag will remove unnecessary Devices and links from
        the graph. This will result in a different overall graph but will
        potentially save memory
        """
        self.check_partition()
        while True:
            expand = set()
            keep = set()
            linksToRemove = list()
            for p0, p1 in self.links:
                # One of the Devices is on the rank that we are
                # following links on
                if (p0.device.partition[0] == rank
                        or p1.device.partition[0] == rank):
                    for p in [p0, p1]:
                        if p.device.library is None:
                            expand.add(p.device)
                        if prune:
                            keep.add(p.device)
                # This link is not used on our rank, remove it
                elif prune:
                    linksToRemove.append(frozenset({p0, p1}))

            # Can't remove items from the dictionary while we are iterating
            # through it, so we store them in a set and remove them after
            # should be better than copying the dictionary
            for p0, p1 in linksToRemove:
                del self.links[frozenset({p0, p1})]
                p0.link = None
                p1.link = None
                self.ports -= {p0, p1}
            
            # Remove devices that haven't been marked for keeping
            if prune:
                self.devices = keep
                self.names = {dev.name for dev in keep}

            if expand:
                self.flatten(expand=expand)
            else:
                break

    def flatten(self, levels: int = None, name: str = None,
                rank: int = None, expand: set = None) -> None:
        """
        Recursively flatten the graph by the specified number of levels.

        For example, if levels is one, then only one level of the hierarchy
        will be expanded. If levels is None, then the graph will be fully
        expanded.

        The name parameter lets you flatten the graph only under a specified
        Device. This expansion allows for multilevel expansion of an assembly
        of assemblies since Devices that are created during expansion have
        the parent assembly's name prepended to their own

        The rank parameter lets you flatten the graph for all Devices in the
        specified rank

        You can also provide a set of Devices to expand instead of looking
        through the entire graph
        """
        # Devices must have a matching name if provided, a matching
        # rank if provided, and be within the expand set if provided
        if levels == 0:
            return

        assemblies = set()
        if name is not None:
            splitName = name.split(".")

        # only check the expand set if provided
        if expand is not None:
            devs = expand
        else:
            devs = self.devices

        for dev in devs:
            assembly = dev.library is None
            if not assembly:
                continue

            # check to see if the name matches
            if name is not None:
                assembly &= splitName == dev.name.split(".")[0: len(splitName)]
            # rank to check
            if rank is not None:
                assembly &= rank == dev.partition[0]

            if assembly:
                assemblies.add(dev)

        if not assemblies:
            return

        # Expand the required Devices
        for device in assemblies:
            self.expanding = device
            device.expand(self)
            self.names.discard(device.name)
            self.devices.discard(device)
        self.expanding = None

        if expand is None:
            # Recursively flatten
            self.flatten(None if levels is None else levels-1, name, rank)

    def write_dot(self, name: str, draw: bool = False, ports: bool = False,
                  hierarchy: bool = True, directory: str = 'output') -> None:
        """
        Take a DeviceGraph and write it as a graphviz dot graph.

        All output will be stored in a folder specified by the directory parameter
        The draw parameter will automatically generate SVGs if set to True
        The ports parameter will display ports on the graph if set to True

        The hierarchy parameter specifies whether you would like to view the
        graph as a hierarchy of assemblies or if you would like get a flat
        view of the graph as it is.
        hierarchy is True by default, and highly recommended for large graphs
        """
        if not os.path.exists(directory):
            os.makedirs(directory)

        if hierarchy:
            self.__write_dot_hierarchy(name, draw, ports, directory)
        else:
            self.__write_dot_flat(name, draw, ports, directory)

    def __write_dot_hierarchy(self, name: str, draw: bool = False,
                              ports: bool = False, directory: str = 'output',
                              assembly: str = None,
                              types: set = None) -> set:
        """
        Take a DeviceGraph and write dot files for each assembly.

        Write a graphviz dot file for each unique assembly (type, model) in the
        graph.
        assembly and types should NOT be specified by the user, they are
        soley used for recursion of this function
        """
        graph = self.__format_graph(name, ports, directory)
        if types is None:
            types = set()

        splitName = None
        splitNameLen = None
        if assembly is not None:
            splitName = assembly.split('.')
            splitNameLen = len(splitName)

        # Expand all unique assembly types and write separate graphviz files
        for dev in self.devices:
            if dev.library is None:
                category = dev.get_category()
                if category not in types:
                    types.add(category)
                    expanded = DeviceGraph()
                    dev.expand(expanded)
                    types = expanded.__write_dot_hierarchy(category, draw,
                                                           ports, directory,
                                                           dev.name, types)

        # Need to check if the provided assembly name is in the graph
        # and if so make that our cluster
        if assembly is not None:
            for dev in self.devices:
                if assembly == dev.name:
                    # This device is the assembly that we just expanded
                    # make this a cluster and add its ports as nodes
                    clusterName = f"cluster_{dev.type}"
                    subgraph = graph.subgraph(name=clusterName, color='green')
                    for port in dev.ports:
                        graph.add_node(f"{dev.type}:{port}",
                                       shape='diamond', label=port,
                                       color='green', fontcolor='green')
                    break
        else:
            # No provided assembly, this is most likely the top level
            subgraph = graph

        # Loop through all Devices and add them to the graphviz graph
        for dev in self.devices:
            if assembly != dev.name:
                label = dev.name
                nodeName = dev.name
                if assembly is not None:
                    if splitName == dev.name.split('.')[0:splitNameLen]:
                        nodeName = '.'.join(dev.name.split('.')[splitNameLen:])
                        label = nodeName
                if dev.model is not None:
                    label += f"\\nmodel={dev.model}"
                if ports:
                    portLabels = dev.label_ports()
                    if portLabels != '':
                        label += f"|{portLabels}"

                # If the Device is an assembly, put a link to its SVG
                if dev.library is None:
                    subgraph.add_node(nodeName, label=label,
                                      href=f"{dev.get_category()}.svg",
                                      color='blue', fontcolor='blue')
                elif dev.subOwner is not None:
                    subgraph.add_node(nodeName, label=label,
                                      color='purple', fontcolor='purple')
                else:
                    subgraph.add_node(nodeName, label=label)

        self.__dot_add_links(graph, ports, assembly, splitName, splitNameLen)

        graph.write(f"{directory}/{name}.dot")
        if draw:
            graph.draw(f"{directory}/{name}.svg", format='svg', prog='dot')

        return types

    def __write_dot_flat(self, name: str, draw: bool = False,
                         ports: bool = False, directory: str = 'output') -> None:
        """
        Write the DeviceGraph as a DOT file.

        It is suggested that you use write_dot_hierarchy for large graphs
        """
        graph = self.__format_graph(name, ports, directory)
        for dev in self.devices:
            label = dev.name
            if dev.model is not None:
                label += f"\\nmodel={dev.model}"
            if ports:
                portLabels = dev.label_ports()
                if portLabels != '':
                    label += f"|{portLabels}"
            if dev.subOwner is not None:
                graph.add_node(dev.name, label=label,
                               color='purple', fontcolor='purple')
            else:
                graph.add_node(dev.name, label=label)

        self.__dot_add_links(graph, ports)

        graph.write(f"{directory}/{name}.dot")
        if draw:
            graph.draw(f"{directory}/{name}.svg", format='svg', prog='dot')

    @staticmethod
    def __format_graph(name: str, record: bool = False,
                       directory: str = 'output') -> pygraphviz.AGraph:
        """Format a new graph."""
        h = ('.edge:hover text {\n'
             '\tfill: red;\n'
             '}\n'
             '.edge:hover path, .node:hover polygon, .node:hover ellipse {\n'
             '\tstroke: red;\n'
             '\tstroke-width: 10;\n'
             '}')
        if not os.path.exists(f"{directory}/highlightStyle.css"):
            with open(f"{directory}/highlightStyle.css", 'w') as f:
                f.write(h)

        graph = pygraphviz.AGraph(strict=False, name=name)
        graph.graph_attr['stylesheet'] = 'highlightStyle.css'
        graph.node_attr['style'] = 'filled'
        graph.node_attr['fillcolor'] = '#EEEEEE'  # light gray fill
        graph.edge_attr['penwidth'] = '2'
        if record:
            graph.node_attr['shape'] = 'record'
            graph.graph_attr['rankdir'] = 'LR'

        return graph

    def __dot_add_links(self, graph, ports: bool = False,
                        assembly: str = None, splitName: list = None,
                        splitNameLen: int = None) -> None:
        """Add edges to the graph with a label for the number of edges."""
        def port2Node(port: DevicePort) -> str:
            """Return a node name given a DevicePort."""
            node = port.device.name
            if node == assembly:
                return f"{port.device.type}:{port.name}"
            elif assembly is not None:
                if splitName == node.split('.')[0:splitNameLen]:
                    node = '.'.join(node.split('.')[splitNameLen:])
            if ports:
                return (node, port.name)
            else:
                return node

        # Create a list of all of the links
        links = list()
        for p0, p1 in self.links:
            links.append(frozenset({port2Node(p0), port2Node(p1)}))

        # Setup a counter so we can check for duplicates
        duplicates = collections.Counter(links)
        for key in duplicates:
            label = ''
            if duplicates[key] > 1:
                label = str(duplicates[key])

            key0, key1 = key
            graphNodes = [key0, key1]
            graphPorts = ['', '']
            if type(key0) is tuple:
                graphNodes[0] = key0[0]
                graphPorts[0] = key0[1]
            if type(key1) is tuple:
                graphNodes[1] = key1[0]
                graphPorts[1] = key1[1]
            # Add edges using the number of links as a label
            graph.add_edge(graphNodes[0], graphNodes[1], label=label,
                           tailport=graphPorts[0], headport=graphPorts[1])

        def device2Node(dev: Device) -> str:
            """Return a node name given a Device."""
            node = dev.name
            if assembly is not None:
                if splitName == node.split('.')[0:splitNameLen]:
                    node = '.'.join(node.split('.')[splitNameLen:])
            return node

        # Add "links" to submodules so they don't just float around
        for dev in self.devices:
            if dev.subOwner is not None:
                graph.add_edge(device2Node(dev), device2Node(dev.subOwner),
                               color='purple', style='dashed')
