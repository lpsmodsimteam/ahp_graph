"""
This module implements support for AHP (Attributed Hierarchical Port) graphs.

This class of graph supports attributes on the nodes (Devices), links
that are connected to named ports on the nodes, and nodes that may be
represented by a hierarchical graph (aka an assembly).  All links are
bidirectional.
"""

import os
import collections
import pygraphviz
from .Device import *

def _orderedtuple(p0, p1):
    "generate a tuple ordered by member id()"
    if id(p0) < id(p1):
        return (p0, p1)
    else:
        return (p1, p0)

class DeviceGraph:
    """
    A DeviceGraph is a graph of Devices and their connections to one another.

    The Devices are nodes and the links connect the DevicePorts on the nodes.
    This implements an AHP (Attributed Hierarchical Port) graph.
    """

    def __init__(self, attr: dict = None) -> None:
        """
        Define an empty DeviceGraph.

        The attributes are considered global parameters shared by all
        instances in the graph. They are only supported at the top-level
        graph, not intemediate graphs (e.g., assemblies).  The dictionary
        of links uses a frozenset of DevicePorts as the key
        """
        self.attr = attr if attr is not None else dict()
        self.devices = dict()
        self.links = dict()
        self.ports = set()

        self.expanding = None
        self.expand_new_links = None
        self.expand_new_devices = None

        self.debug = False

    def dealloc(self):
        """
        Deallocate the device graph.  This method explicitly walks
        through the various dictionaries and sets and unwinds the
        graph.  This might help speed up garbage collection but there
        are no examples of it actually speeding up a run.  Note that 
        this method will delete all devices, ports, and links, so 
        do not call dealloc() if you intend to reference any of these
        objects later.
        """
        self.links.clear()

        for device in self.devices.values():
            device.dealloc()
        self.devices.clear()

        for port in self.ports:
            port.device = None
            port.link = None
        self.ports.clear()

    def __repr__(self) -> str:
        """
        Pretty print a DeviceGraph with Devices followed by links.
        """
        lines = list()
        for device in self.devices.values():
            lines.append(str(device))
        for p0, p1 in self.links:
            lines.append(f"{p0} <--{self.links[(p0, p1)]}--> {p1}")
        return "\n".join(lines)

    def _link_other_port(self, p0: DevicePort, p1: DevicePort) -> None:
        """Link a matching port through an expanding assembly."""
        if p0.link is not None:
            p2 = p0.link
            if not self.check_port_types(p1, p2):
                raise RuntimeError(f'Port type mismatch {p1}, {p2}')
            # remove p0 from the links and connect p1 to p2
            p0.link = None
            p2.link = p1
            p1.link = p2
            self.ports.remove(p0)
            self.ports.add(p1)
            latency = self.links.pop(_orderedtuple(p0, p2))
            # add the other device to the graph
            if p1.device.name not in self.devices:
                self.add(p1.device)
            self.links[_orderedtuple(p1, p2)] = latency
            if self.expand_new_links is not None:
                self.expand_new_links.append((p1,p2))

    def link(self, p0: DevicePort, p1: DevicePort,
             latency: str = '0s') -> None:
        """
        Link two DevicePorts with latency if provided.

        Links are bidirectional and the key is a frozenset of the two
        DevicePorts. Duplicate links (links between the same DevicePorts)
        are not permitted. Keep in mind that a unique DevicePort is created
        for each port number in a multi-port style port. If the link
        types to not match, then throw an exception. Devices that are linked
        to will be added to the graph automatically.  Latency is expressed
        as a string with time units (ps, ns, us...)
        """
        if callable(p0) or callable(p1):
            raise RuntimeError(f"{p0} or {p1} is callable. This probably means"
                               f" you have a multi port and didn't pick a port"
                               f" number (ex. Device.portX(portNum))")

        if self.expanding is not None:
            if p0.device == self.expanding:
                self._link_other_port(p0, p1)
                return
            elif p1.device == self.expanding:
                self._link_other_port(p1, p0)
                return

        if p0 in self.ports or p1 in self.ports:
            raise RuntimeError(f'{p0} or {p1} already linked to')

        if not self.check_port_types(p0, p1):
            raise RuntimeError(f'Port type mismatch {p0}, {p1}')

        #
        # Add devices to the graph if not already there
        #
        if p0.device.name not in self.devices:
            self.add(p0.device)
        if p1.device.name not in self.devices:
            self.add(p1.device)

        # Storing the ports in a set so that we can quickly see if they
        # are linked to already
        self.ports.add(p0)
        self.ports.add(p1)
        # Only update the links if neither are connected
        # otherwise we are most likely doing a separate graph expansion and
        # don't want to overwrite the port links that exist
        if p0.link is None and p1.link is None:
            p0.link = p1
            p1.link = p0
        key = _orderedtuple(p0, p1)
        self.links[key] = latency
        if self.expand_new_links is not None:
            self.expand_new_links.append(key)

    def add(self, device: Device, sub: bool = False) -> None:
        """
        Add a Device to the graph.

        The Device must be a ahp_graph Device. The name must be unique.
        If the Device has submodules, then we add those, as well.
        Do NOT add submodules to a Device after you have added it using
        this function, they will not be included in the DeviceGraph.
        """
        if device.name in self.devices:
            raise RuntimeError(f'Device name {device.name} already in graph')

        if self.expanding is not None:
            device.name = f"{self.expanding.name}.{device.name}"
            if (self.expanding.partition is not None
                    and device.partition is None):
                device.partition = self.expanding.partition

        self.devices[device.name] = device
        if self.expand_new_devices is not None:
            self.expand_new_devices.add(device)

        if device.subOwner is not None and not sub:
            dev = device
            while dev.subOwner is not None:
                dev = dev.subOwner
            self.add(dev)

        if device.subs:
            for (dev, _, _) in device.subs:
                self.add(dev, True)

    def count_devices(self) -> dict:
        """
        Count the Devices in a graph.

        Return a map of Devices to integer counts. The keys are of the
        form "CLASS_MODEL".
        """
        counter = collections.defaultdict(int)
        for device in self.devices.values():
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
        for device in self.devices.values():
            for name, info in device.portinfo.items():
                if info[2] and name not in d2ports[device]:
                    raise RuntimeError(f"{device.name} requires port {name}")

    def check_partition(self) -> None:
        """
        Check to make sure the graph has ranks specified for all Devices.
        """
        for d in self.devices.values():
            if d.partition is None:
                raise RuntimeError(f"No partition for Device: {d.name}")

    def prune(self, rank: int) -> None:
        """
        Prune links and devices that are not (1) on this rank or (2) linked
        to this rank.  This operation can save memory when instantiating
        graphs in parallel.
        """
        self.check_partition()

        links_to_remove = list()
        devices_to_keep = set()

        #
        # If either of the endpoints are on the link, then keep the
        # link and devices.
        #
        for p0, p1 in self.links:
            d0 = p0.device
            d1 = p1.device

            if d0.partition[0] == rank or d1.partition[0] == rank:
                devices_to_keep.add(d0)
                devices_to_keep.add(d1)

                d0_so = d0.subOwner
                while d0_so:
                    devices_to_keep.add(d0_so)
                    d0_so=d0_so.subOwner
            
                d1_so = d1.subOwner
                while d1_so:
                    devices_to_keep.add(d1_so)
                    d1_so=d1_so.subOwner

                if d0.subs:
                    for s0 in d0.subs:
                        devices_to_keep.add(s0)
                if d1.subs:
                    for s1 in d1.subs:
                        devices_to_keep.add(s1)
            else:
                links_to_remove.append((p0, p1))

        #
        # Remove the unnecessary links and associated ports.
        #
        for p0, p1 in links_to_remove:
            del self.links[(p0, p1)]
            p0.link = None
            p1.link = None
            self.ports.remove(p0)
            self.ports.remove(p1)

        #
        # Remove all devices we do not need to keep
        #
        for device in set(self.devices.values()).difference(devices_to_keep):
            del self.devices[device.name]
            device.dealloc()

    def _expand_device(self, device):
        """
        Expand a device and do some basic sanity checking.

        """
        self.expanding = device
        device.expand(self)
        self.expanding = None

        del self.devices[device.name]
        device.dealloc()

        #
        # Check that all of the links associated with the device have
        # been expanded.
        #
        if self.debug:
            name = device.name
            for p0, p1 in self.links:
                if p0.device.name == name or p1.device.name == name:
                    raise RuntimeError(f"Unexpanded link {name}: {p0} <-> {p1}")

    def follow_links(self, rank: int, prune: bool = False) -> None:
        """
        Chase links between ranks.

        Follow links from the specified rank and expand assemblies until links
        are fully defined (links touch library devices on both sides).  The
        optional prune flag will remove unnecessary devices and links from
        the graph. This will result in a different overall graph but will
        save memory
        """
        self.check_partition()

        if prune:
            self.prune(rank)

        #
        # Loop until there are no more devies to expand.
        #
        more_to_expand = True
        while more_to_expand:

            #
            # Find devices that need expanding, defined as those devices that
            # are assemblies and are on this rank or are linked to this rank.
            #
            devices_to_expand = set()
            for p0, p1 in self.links:
                d0 = p0.device
                d1 = p1.device

                if d0.partition[0] == rank or d1.partition[0] == rank:
                    if d0.library is None:
                        devices_to_expand.add(d0)
                    if d1.library is None:
                        devices_to_expand.add(d1)

            #
            # If the set of devices to expand is empty, then we are done.
            # Otherwise, iterate over the devices and expand them one-by-one.
            #
            more_to_expand = len(devices_to_expand) > 0

            for device in devices_to_expand:
                if prune:
                    self.expand_new_links = list()
                    self.expand_new_devices = set()
                self._expand_device(device)

                #
                # If pruning, then remove newly expanded devices
                # and links that do not belong on this rank.
                #
                if prune:
                    for p0, p1 in self.expand_new_links:
                        d0 = p0.device
                        d1 = p1.device
                        r0 = d0.partition[0]
                        r1 = d1.partition[0]

                        if r0 == rank or r1 == rank:
                            self.expand_new_devices.discard(d0)
                            self.expand_new_devices.discard(d1)
                            self.expand_new_devices.discard(d0.subOwner)
                            self.expand_new_devices.discard(d1.subOwner)
                            if d0.subs:
                                for s0 in d0.subs:
                                    self.expand_new_devices.discard(s0)
                            if d1.subs:
                                for s1 in d1.subs:
                                    self.expand_new_devices.discard(s1)
                        else:
                            del self.links[(p0, p1)]
                            p0.link = None
                            p1.link = None
                            self.ports.remove(p0)
                            self.ports.remove(p1)

                    for device in self.expand_new_devices:
                        del self.devices[device.name]
                        device.dealloc()

                self.expand_new_links = None
                self.expand_new_devices = None
                self.expanding = None

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
            devs = self.devices.values()

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
            self._expand_device(device)

        if expand is None:
            # Recursively flatten
            self.flatten(None if levels is None else levels-1, name, rank)

    def write_dot(self,
                  name: str,
                  output: str = "output",
                  draw: bool = False,
                  ports: bool = False,
                  hierarchy: bool = True) -> None:
        """
        Take a DeviceGraph and write it as a graphviz dot graph.

        All output will be stored in a folder called output
        The draw parameter will automatically generate SVGs if set to True
        The ports parameter will display ports on the graph if set to True

        The hierarchy parameter specifies whether you would like to view the
        graph as a hierarchy of assemblies or if you would like get a flat
        view of the graph as it is.
        hierarchy is True by default, and highly recommended for large graphs
        """
        if not os.path.exists(output):
            os.makedirs(output)

        if hierarchy:
            self.__write_dot_hierarchy(name, output, draw, ports)
        else:
            self.__write_dot_flat(name, output, draw, ports)

    def __write_dot_hierarchy(self,
                              name: str,
                              output: str,
                              draw: bool = False,
                              ports: bool = False, assembly: str = None,
                              types: set = None) -> set:
        """
        Take a DeviceGraph and write dot files for each assembly.

        Write a graphviz dot file for each unique assembly (type, model) in the
        graph.
        assembly and types should NOT be specified by the user, they are
        soley used for recursion of this function
        """
        graph = self.__format_graph(name, output, ports)
        if types is None:
            types = set()

        splitName = None
        splitNameLen = None
        if assembly is not None:
            splitName = assembly.split('.')
            splitNameLen = len(splitName)

        # Expand all unique assembly types and write separate graphviz files
        for dev in self.devices.values():
            if dev.library is None:
                category = dev.get_category()
                if category not in types:
                    types.add(category)
                    expanded = DeviceGraph()
                    dev.expand(expanded)
                    types = expanded.__write_dot_hierarchy(
                        category, output, draw, ports, dev.name, types
                    )

        # Need to check if the provided assembly name is in the graph
        # and if so make that our cluster
        if assembly is not None:
            dev = self.devices.get(assembly)
            if dev is not None:
                # This device is the assembly that we just expanded
                # make this a cluster and add its ports as nodes
                clusterName = f"cluster_{dev.type}"
                subgraph = graph.subgraph(name=clusterName, color='green')
                for port in dev.ports:
                    if isinstance(port, tuple):
                        label = port[0]
                        graph.add_node(
                            f"{dev.type}:{label}",
                            shape='diamond',
                            label=label,
                            color='green',
                            fontcolor='green'
                        ) 
        else:
            # No provided assembly, this is most likely the top level
            subgraph = graph

        # Loop through all Devices and add them to the graphviz graph
        for dev in self.devices.values():
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

        graph.write(f"{output}/{name}.dot")
        if draw:
            graph.draw(f"{output}/{name}.svg", format='svg', prog='dot')

        return types

    def __write_dot_flat(self,
                         name: str,
                         output: str,
                         draw: bool = False,
                         ports: bool = False) -> None:
        """
        Write the DeviceGraph as a DOT file.

        It is suggested that you use write_dot_hierarchy for large graphs
        """
        graph = self.__format_graph(name, output, ports)

        for dev in self.devices.values():
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

        graph.write(f"{output}/{name}.dot")
        if draw:
            graph.draw(f"{output}/{name}.svg", format='svg', prog='dot')

    @staticmethod
    def __format_graph(name: str,
                       output: str,
                       record: bool = False) -> pygraphviz.AGraph:
        """Format a new graph."""
        h = ('.edge:hover text {\n'
             '\tfill: red;\n'
             '}\n'
             '.edge:hover path, .node:hover polygon, .node:hover ellipse {\n'
             '\tstroke: red;\n'
             '\tstroke-width: 10;\n'
             '}')
        if not os.path.exists(f"{output}/highlightStyle.css"):
            with open(f"{output}/highlightStyle.css", 'w') as f:
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
            links.append(_orderedtuple(port2Node(p0), port2Node(p1)))

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
        for dev in self.devices.values():
            if dev.subOwner is not None:
                graph.add_edge(device2Node(dev), device2Node(dev.subOwner),
                               color='purple', style='dashed')