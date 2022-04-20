"""
This module implements support for AHP (attributed hierarchical port) graphs.

This class of graph supports attributes on the nodes (devices), links that are
connected to named ports on the nodes, and the non-simple nodes that may be
represented by a hierarchical graph (aka an assembly).
All links are unidirectional.
"""

import collections
import pygraphviz
from .Device import *


class DeviceGraph:
    """
    A DeviceGraph is a graph of devices and their connections to one another.

    The devices are nodes and the links connect the ports on the nodes.
    This implements an AHP (annotated hierarchical port) graph.
    """

    def __init__(self, attr=None) -> 'DeviceGraph':
        """
        Define an empty device graph.

        The attributes are considered global parameters shared by all instances
        in the graph. They are only supported at the top-level graph,
        not intemediate graphs (e.g., assemblies).
        """
        self.attr = dict(attr) if attr is not None else dict()
        self.devices = dict()
        self.links = collections.defaultdict(tuple)

    def __repr__(self) -> str:
        """Pretty print graph with devices followed by links."""
        lines = list()
        for device in self.devices.values():
            lines.append(str(device))
        for (p0, p1, _) in self.links.values():
            lines.append(f"{p0} <---> {p1}")
        return "\n".join(lines)

    def add(self, device: 'Device') -> None:
        """
        Add a Device to the graph.

        The device must be a PyDL Device. The name must be unique.
        If the device has sub-components, then we add those, as well.
        Do NOT add sub-components to a device after you have added it using
        this function. Add sub-components first, then add the parent.
        """
        if device.name in self.devices:
            raise RuntimeError(f"Name already in graph: {device.name}")
        self.devices[device.name] = device
        for (dev, _, _) in device.subs:
            self.add(dev)

    def link(self, p0: 'DevicePort', p1: 'DevicePort',
             latency: str = '1ps') -> None:
        """
        Link two ports on two different devices.

        Links are undirected, so we normalize the link direction by the names
        of the two device endpoints. If the link types to not match,
        then throw an exception. Devices that are linked to will be added
        to the graph automatically.

        The latency is expressed as a string with time units (ps, ns, us...)
        """
        if p1 < p0:
            (p0, p1) = (p1, p0)
        linkName = f"{p0}__{latency}__{p1}"
        if linkName in self.links:
            raise RuntimeError(f"Link already in graph: {linkName}")

        devs = [p0.device, p1.device]
        # Add devices to the graph if they aren't already included
        for dev in devs:
            if dev.name not in self.devices:
                while dev.subOwner is not None:
                    dev = dev.subOwner
                self.add(dev)

        # Check to make sure the port types match
        t0 = devs[0].get_portinfo()[p0.name][1]
        t1 = devs[1].get_portinfo()[p1.name][1]

        if t0 != t1:
            raise RuntimeError(
                f"Port type mismatch: {t0} != {t1} between"
                f"{devs[0].name} and {devs[1].name}"
            )
        self.links[linkName] = (p0, p1, latency)

    def verify_links(self) -> None:
        """
        Verify that all required ports are linked up.

        Throw an exception if there is an error.
        """
        # Create a map of devices to all ports linked on those devices.
        d2ports = collections.defaultdict(set)
        for (p0, p1, _) in self.links.values():
            d2ports[p0.device].add(p0.name)
            d2ports[p1.device].add(p1.name)

        # Walk all devices and make sure required ports are connected.
        for device in self.devices.values():
            portinfo = device.get_portinfo()
            for name in portinfo:
                if portinfo[name][2] and name not in d2ports[device]:
                    raise RuntimeError(f"{device.name} requires port {name}")

    def follow_links(self, rank: int) -> 'DeviceGraph':
        """
        Chase links betweeen ranks.

        Given a graph, follow links from the specified rank and expand
        assemblies until links are fully defined (links touch sstlib
        Devices on both sides)
        """
        graph = self
        while True:
            devices = set()
            for (p0, p1, _) in graph.links.values():
                # one of the devices is on the rank that we are
                # following links on
                if p0.device.rank == rank or p1.device.rank == rank:
                    for p in [p0, p1]:
                        if p.device.sstlib is None:
                            # link on the rank we want, device needs expanded
                            devices.add(p.device)
            if devices:
                graph = graph.flatten(1, expand=devices)
            else:
                break
        return graph

    def flatten(self, levels: int = None, name: str = None,
                rank: int = None, expand: set = None) -> 'DeviceGraph':
        """
        Recursively flatten the graph by the specified number of levels.

        For example, if levels is one, then only one level of the hierarchy
        will be expanded.  If levels is None, then the graph will be fully
        expanded.  If levels is zero or no devices are an assembly, then just
        return self.

        The name parameter lets you flatten the graph only under a specified
        device. If the assemblies keep the name of the parent for the devices
        in the expanded graph as a prefix, this expansion allows for multilevel
        expansion of an assembly of assemblies.  The deliminter must be a '.'
        for the name to function, e.g., Assembly.subassembly.device.

        The rank parameter lets you flatten the graph for all devices in the
        specified rank

        You can also provide a set of devices to expand instead of looking
        through the entire graph
        """
        # Build up a list of devices that don't need expanded
        # and a list of devices to be expanded
        #
        # non-assembly devices automatically are added to the devices list
        # Devices must have a matching name if provided, a matching
        # rank if provided, and be within the expand set if provided
        # if they are to be added to the assemblies list of devices to expand
        assemblies = list()

        if name is not None:
            splitName = name.split(".")

        for dev in self.devices.values():
            assembly = dev.assembly

            # check to see if the name matches
            if name is not None:
                assembly &= splitName == dev.name.split(".")[0: len(splitName)]
            # rank to check
            if rank is not None:
                assembly &= rank == dev.rank
            # check to see if the device is in the expand set
            if expand is not None:
                assembly &= dev in expand

            if assembly:
                assemblies.append(dev)

        if levels == 0 or not assemblies:
            return self

        # Start by creating a link map.  This will allow us quick lookup
        # of the links in the graph.  We add both directions, since we will
        # need to look up by both the first and second device.
        links = collections.defaultdict(set)
        for (p0, p1, t) in self.links.values():
            links[p0.device].add((p0, p1, t))
            links[p1.device].add((p1, p0, t))

        # Expand the required devices
        for device in assemblies:
            oldPorts = device.ports
            device.ports = collections.defaultdict(dict)
            subgraph = device.expand()

            # Update the list of devices from the subgraph.  We
            # throw away the node we just expanded.  Expanded
            # devices inherit the partition of the parent.
            for d in subgraph.devices.values():
                if d != device and d.subOwner is None:
                    d.rank = device.rank
                    d.thread = device.thread

            def find_other_port(port):
                """
                Find a matching port.

                Define a subroutine to find the matching port and
                remove the associated link.  If we were not able to
                find a matching port, then return None.
                """
                for (p0, p1, t) in links[port.device]:
                    if p0 == port:
                        links[p0.device].remove((p0, p1, t))
                        links[p1.device].remove((p1, p0, t))
                        return p1
                print(f'Not finding port {port}')
                return None

            # Update the links
            for (p0, p1, t) in subgraph.links.values():
                if p0.device == device:
                    p2 = find_other_port(p0)
                    if p2 is not None:
                        links[p1.device].add((p1, p2, t))
                        links[p2.device].add((p2, p1, t))
                elif p1.device == device:
                    p2 = find_other_port(p1)
                    if p2 is not None:
                        links[p0.device].add((p0, p2, t))
                        links[p2.device].add((p2, p0, t))
                else:
                    links[p0.device].add((p0, p1, t))
                    links[p1.device].add((p1, p0, t))

            # Sanity check that we removed all the links
            for (p0, p1, _) in links[device]:
                raise RuntimeError(f"Unexpanded port: {p0}, {p1}")

        # Reconstruct the new graph from the devices and links.
        graph = DeviceGraph(self.attr)

        for linkset in links.values():
            for (p0, p1, t) in linkset:
                if p0 < p1:
                    graph.link(p0, p1, t)

        # Recursively flatten
        return graph.flatten(None if levels is None else levels - 1,
                             name, rank, expand)

    def count_devices(self) -> dict:
        """
        Count the devices in a graph.

        Return a map of components to integer counts. The keys are of the
        form "CLASS_MODEL".
        """
        counter = collections.defaultdict(int)
        for device in self.devices():
            counter[device.get_category()] += 1
        return counter

    @staticmethod
    def __format_graph(name: str, record: bool = False) -> pygraphviz.AGraph:
        """Format a new graph."""
        h = ('.edge:hover text {\n'
             '\tfill: red;\n'
             '}\n'
             '.edge:hover path, .node:hover polygon, .node:hover ellipse {\n'
             '\tstroke: red;\n'
             '\tstroke-width: 10;\n'
             '}')
        with open('highlightStyle.css', 'w') as f:
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

    def __dot_add_links(self, graph: pygraphviz.AGraph,
                        ports: bool = False, assembly: str = None,
                        splitName: str = None, splitNameLen: int = 0) -> None:
        """Add edges to the graph with a label for the number of edges."""
        def port2Node(port: 'DevicePort') -> str:
            """Return a node name given a DevicePort."""
            node = port.device.name
            if node == assembly:
                return f"{port.device.attr['type']}:{port.name}"
            elif assembly is not None:
                if splitName == node.split('.')[0:splitNameLen]:
                    node = '.'.join(node.split('.')[splitNameLen:])
            if ports:
                return (node, port.name)
            else:
                return node

        links = list()
        for (p0, p1, latency) in self.links.values():
            links.append((port2Node(p0), port2Node(p1)))

        duplicates = collections.Counter(links)
        for key in duplicates:
            label = ''
            if duplicates[key] > 1:
                label = duplicates[key]

            graphNodes = [key[0], key[1]]
            graphPorts = ['', '']
            for i in range(2):
                if type(key[i]) is tuple:
                    graphNodes[i] = key[i][0]
                    graphPorts[i] = key[i][1]

            graph.add_edge(graphNodes[0], graphNodes[1], label=label,
                           tailport=graphPorts[0], headport=graphPorts[1])

        def device2Node(dev: 'Device') -> str:
            """Return a node name given a Device."""
            node = dev.name
            if assembly is not None:
                if splitName == node.split('.')[0:splitNameLen]:
                    node = '.'.join(node.split('.')[splitNameLen:])
            return node

        # add "links" to subcomponents so they don't just float around
        for dev in self.devices.values():
            if dev.subOwner is not None:
                graph.add_edge(device2Node(dev), device2Node(dev.subOwner),
                               color='purple', style='dashed')

    def write_dot_hierarchy(self, name: str,
                            draw: bool = False, ports: bool = False,
                            assembly: str = None, types: set = None) -> set:
        """
        Take an un-flattened DeviceGraph and write dot files for each assembly.

        Write a graphviz dot file for each unique assembly (type, model) in the
        graph
        The draw parameter will automatically generate SVGs if set to True
        The ports parameter will display ports on the graph if set to True
        assembly and types should NOT be specified by the user, they are
        soley used for recursion of this function
        """
        graph = self.__format_graph(name, ports)
        if types is None:
            types = set()

        if assembly is not None:
            splitName = assembly.split('.')
            splitNameLen = len(splitName)

        # expand all unique assembly types and write separate graphviz files
        for dev in self.devices.values():
            if dev.assembly:
                category = dev.get_category()
                if category not in types:
                    types.add(category)
                    expanded = dev.expand()
                    types = expanded.write_dot_hierarchy(category, draw, ports,
                                                         dev.name, types)

        # graph the current graph
        # need to check if the provided assembly name is in the graph
        # and if so make that our cluster
        if assembly is not None:
            for dev in self.devices.values():
                if assembly == dev.name:
                    # this device is the PyDL assembly that we just expanded
                    # make this a cluster and add its ports as nodes
                    clusterName = f"cluster_{dev.attr['type']}"
                    subgraph = graph.subgraph(name=clusterName, color='green')
                    for port in dev.ports:
                        graph.add_node(f"{dev.attr['type']}:{port}",
                                       shape='diamond', label=port,
                                       color='green', fontcolor='green')
        else:
            # no provided assembly, this is most likely the top level
            subgraph = graph

        for dev in self.devices.values():
            if assembly != dev.name:
                label = dev.name
                nodeName = dev.name
                if assembly is not None:
                    if splitName == dev.name.split('.')[0:splitNameLen]:
                        nodeName = '.'.join(dev.name.split('.')[splitNameLen:])
                        label = nodeName
                if 'model' in dev.attr:
                    label += f"\\nmodel={dev.attr['model']}"
                if ports:
                    portLabels = dev.label_ports()
                    if portLabels != '':
                        label += f"|{portLabels}"

                # if the device is an assembly, put a link to its SVG
                if dev.assembly:
                    subgraph.add_node(nodeName, label=label,
                                      href=f"{dev.get_category()}.svg",
                                      color='blue', fontcolor='blue')
                elif dev.subOwner is not None:
                    subgraph.add_node(nodeName, label=label,
                                      color='purple', fontcolor='purple')
                else:
                    subgraph.add_node(nodeName, label=label)

        if assembly is not None:
            self.__dot_add_links(graph, ports, assembly,
                                 splitName, splitNameLen)
        else:
            self.__dot_add_links(graph, ports)

        graph.write(f"{name}.dot")
        if draw:
            graph.draw(f"{name}.svg", format='svg', prog='dot')

        return types

    def write_dot_file(self, name: str,
                       draw: bool = False, ports: bool = False) -> None:
        """Write the device graph as a DOT file."""
        graph = self.__format_graph(name, ports)

        for dev in self.devices.values():
            label = dev.name
            if 'model' in dev.attr:
                label += f"\\nmodel={dev.attr['model']}"
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

        graph.write(f"{name}.dot")
        if draw:
            graph.draw(f"{name}.svg", format='svg', prog='dot')
