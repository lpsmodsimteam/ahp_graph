"""
This module implements support for AHP (Attributed Hierarchical Port) graphs.

This class of graph supports attributes on the nodes (Devices), links
that are connected to named ports on the nodes, and nodes that may be
represented by a hierarchical graph (aka an assembly).  All links are
bidirectional.
"""

import os
import glob
import collections
import pygraphviz
try:
    import networkx
except ImportError:
    networkx = None
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
            attr = self.links[(p0, p1)]
            attr_str = ', '.join(f"{k}={v}" for k, v in sorted(attr.items()))
            lines.append(f"{p0} <--[{attr_str}]--> {p1}")
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
            attr = self.links.pop(_orderedtuple(p0, p2))
            # add the other device to the graph
            if p1.device.name not in self.devices:
                self.add(p1.device)
            self.links[_orderedtuple(p1, p2)] = attr
            if self.expand_new_links is not None:
                self.expand_new_links.append((p1,p2))

    def link(self, p0: DevicePort, p1: DevicePort,
             latency: str = None, attr: dict = None) -> None:
        """
        Link two DevicePorts with optional attributes.

        Links are bidirectional and the key is a frozenset of the two
        DevicePorts. Duplicate links (links between the same DevicePorts)
        are not permitted. Keep in mind that a unique DevicePort is created
        for each port number in a multi-port style port. If the link
        types to not match, then throw an exception. Devices that are linked
        to will be added to the graph automatically.

        Args:
            p0: First DevicePort to link
            p1: Second DevicePort to link
            latency: Optional latency string (e.g., '0s', '10ns'). If provided,
                     added to attr as 'latency' key. For backward compatibility.
            attr: Optional dictionary of link attributes. If not provided,
                  defaults to {'latency': '0s'} or {'latency': latency} if
                  latency is specified.
        """
        # Process attributes
        if attr is None:
            attr = {}
        else:
            attr = dict(attr)  # Make a copy to avoid modifying caller's dict

        # Handle backward compatibility: if latency is provided, add it to attr
        if latency is not None:
            attr['latency'] = latency
        elif 'latency' not in attr:
            attr['latency'] = '0s'

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
        self.links[key] = attr
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
            self.ports.discard(p0)
            self.ports.discard(p1)

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
                            self.ports.discard(p0)
                            self.ports.discard(p1)

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

    def write_networkx(self,
                       name: str,
                       output: str = "output",
                       draw: bool = False,
                       ports: bool = False,
                       hierarchy: bool = True,
                       save_graph: str = None,
                       color_by_partition: bool = False,
                       highlight_inter_rank: bool = False,
                       self_links: bool = True,
                       full_labels: bool = False,
                       layout=None,
                       node_label=None) -> None:
        """
        Take a DeviceGraph and render it as an image using NetworkX.

        This is the NetworkX/matplotlib analog of write_dot.  Instead of
        writing graphviz DOT/SVG files, it builds a networkx graph and
        renders a PNG image using matplotlib.

        All output will be stored in a folder called output
        The draw parameter will additionally display the figure
        interactively if set to True
        The ports parameter is accepted for API symmetry with write_dot,
        but ports are not rendered in the NetworkX output

        The hierarchy parameter specifies whether you would like to view the
        graph as a hierarchy of assemblies (one image per unique assembly
        type) or if you would like to get a flat view of the graph as it is.
        hierarchy is True by default, and highly recommended for large graphs

        The save_graph parameter, if provided, saves the underlying networkx
        graph object to a file in addition to rendering the image.  The file
        format is chosen from the file extension: '.pickle'/'.pkl'/'.gpickle'
        write a Python pickle, '.graphml' writes GraphML, and '.gexf' writes
        GEXF.  A bare filename (no directory) is written into the output
        folder.

        The color_by_partition parameter colors each node according to its
        partition (rank).  This is useful when rendering a flat image of the
        global partition so that you can see how Devices are distributed
        across ranks.

        The highlight_inter_rank parameter highlights links that cross a rank
        boundary (i.e., connect Devices assigned to different partitions).

        The self_links parameter controls whether self-links (a Device linked
        to itself) are drawn.  Self-links are drawn by default; set this to
        False to remove them from the rendering.

        The full_labels parameter draws each node using its full name (e.g.,
        'SubGrid0.comp_0_0'), matching the labels produced by write_dot.  When
        full_labels is False, the node_label callback (if provided) is used to
        compute a compact display label for each node.

        The layout parameter lets the caller control node placement.  It may
        be a callable that takes the networkx graph and returns a dict mapping
        node -> (x, y) position.  If it is None (or returns nothing), nodes
        that carry an explicit 'pos' attribute are placed accordingly,
        otherwise a graphviz (and finally spring) layout is used.  This keeps
        domain-specific placement (e.g., laying a mesh out on a grid) in the
        caller instead of hard-coding it in the graph library.

        The node_label parameter is a callable that takes a node name and
        returns a compact display label (or None to fall back to the full
        label).  It is only consulted when full_labels is False.
        """
        if networkx is None:
            raise ImportError(
                "networkx is required for write_networkx; "
                "install it with 'pip install networkx matplotlib'"
            )

        if not os.path.exists(output):
            os.makedirs(output)

        if hierarchy:
            self.__write_networkx_hierarchy(
                name, output, draw, ports,
                save_graph=save_graph,
                color_by_partition=color_by_partition,
                highlight_inter_rank=highlight_inter_rank,
                self_links=self_links,
                full_labels=full_labels,
                layout=layout,
                node_label=node_label,
            )
        else:
            self.__write_networkx_flat(
                name, output, draw, ports,
                save_graph=save_graph,
                color_by_partition=color_by_partition,
                highlight_inter_rank=highlight_inter_rank,
                self_links=self_links,
                full_labels=full_labels,
                layout=layout,
                node_label=node_label,
            )

    def __write_networkx_hierarchy(self,
                                   name: str,
                                   output: str,
                                   draw: bool = False,
                                   ports: bool = False, assembly: str = None,
                                   types: set = None,
                                   save_graph: str = None,
                                   color_by_partition: bool = False,
                                   highlight_inter_rank: bool = False,
                                   self_links: bool = True,
                                   full_labels: bool = False,
                                   layout=None,
                                   node_label=None) -> set:
        """
        Take a DeviceGraph and render an image for each assembly.

        Render a NetworkX image for each unique assembly (type, model) in the
        graph.
        assembly and types should NOT be specified by the user, they are
        soley used for recursion of this function
        """
        graph = networkx.Graph()
        if types is None:
            types = set()

        splitName = None
        splitNameLen = None
        if assembly is not None:
            splitName = assembly.split('.')
            splitNameLen = len(splitName)

        # Expand all unique assembly types and render separate images
        for dev in self.devices.values():
            if dev.library is None:
                category = dev.get_category()
                if category not in types:
                    types.add(category)
                    expanded = DeviceGraph()
                    dev.expand(expanded)
                    types = expanded.__write_networkx_hierarchy(
                        category, output, draw, ports, dev.name, types,
                        save_graph=None,
                        color_by_partition=color_by_partition,
                        highlight_inter_rank=highlight_inter_rank,
                        self_links=self_links,
                        full_labels=full_labels,
                        layout=layout,
                        node_label=node_label,
                    )

        # Loop through all Devices and add them to the networkx graph
        for dev in self.devices.values():
            if assembly != dev.name:
                label = dev.name
                nodeName = dev.name
                if assembly is not None:
                    if splitName == dev.name.split('.')[0:splitNameLen]:
                        nodeName = '.'.join(dev.name.split('.')[splitNameLen:])
                        label = nodeName
                if dev.model is not None:
                    label += f"\nmodel={dev.model}"

                # Color by partition if requested, otherwise color assemblies
                # blue and submodules purple
                if color_by_partition:
                    color = self.__partition_color(dev.partition)
                elif dev.library is None:
                    color = 'blue'
                elif dev.subOwner is not None:
                    color = 'purple'
                else:
                    color = 'lightblue'
                display = label if full_labels else \
                    self.__networkx_label(nodeName, label, node_label)
                graph.add_node(nodeName, color=color, display=display)

        self.__networkx_add_links(graph, assembly, splitName, splitNameLen,
                                  highlight_inter_rank=highlight_inter_rank,
                                  self_links=self_links,
                                  full_labels=full_labels)
        self.__render_networkx(graph, name, output, draw,
                               save_graph=save_graph, layout=layout)

        return types

    def __write_networkx_flat(self,
                              name: str,
                              output: str,
                              draw: bool = False,
                              ports: bool = False,
                              save_graph: str = None,
                              color_by_partition: bool = False,
                              highlight_inter_rank: bool = False,
                              self_links: bool = True,
                              full_labels: bool = False,
                              layout=None,
                              node_label=None) -> None:
        """
        Render the DeviceGraph as a flat NetworkX image.

        It is suggested that you use the hierarchy view for large graphs
        """
        graph = networkx.Graph()

        for dev in self.devices.values():
            label = dev.name
            if dev.model is not None:
                label += f"\nmodel={dev.model}"
            if color_by_partition:
                color = self.__partition_color(dev.partition)
            elif dev.subOwner is not None:
                color = 'purple'
            else:
                color = 'lightblue'
            display = label if full_labels else \
                self.__networkx_label(dev.name, label, node_label)
            graph.add_node(dev.name, color=color, display=display)

        self.__networkx_add_links(graph,
                                  highlight_inter_rank=highlight_inter_rank,
                                  self_links=self_links,
                                  full_labels=full_labels)
        self.__render_networkx(graph, name, output, draw,
                               save_graph=save_graph, layout=layout)

    @staticmethod
    def __networkx_label(nodeName: str, fallback: str = None,
                         node_label=None) -> str:
        """Return a short display label for a node.

        If a node_label callable is provided, use its result (when it returns
        a non-None value); otherwise fall back to the provided fallback or the
        full node name.  This keeps domain-specific labeling in the caller
        rather than hard-coding a naming scheme in the graph library.
        """
        if callable(node_label):
            try:
                result = node_label(nodeName)
            except Exception:
                result = None
            if result is not None:
                return str(result)
        return fallback if fallback is not None else str(nodeName)

    @staticmethod
    def __partition_color(partition) -> str:
        """Return a stable color for a Device partition (rank).

        partition may be a (rank, thread) tuple, a bare rank, or None.
        Devices with no partition are colored light gray.
        """
        if partition is None:
            return '#cccccc'
        if isinstance(partition, (tuple, list)):
            rank = partition[0]
        else:
            rank = partition
        if rank is None:
            return '#cccccc'
        # A qualitative palette that repeats for large rank counts.
        palette = [
            '#1f77b4', '#ff7f0e', '#2ca02c', '#d62728', '#9467bd',
            '#8c564b', '#e377c2', '#7f7f7f', '#bcbd22', '#17becf',
        ]
        return palette[int(rank) % len(palette)]

    @staticmethod
    def __networkx_layout(graph, layout=None) -> dict:
        """Compute node positions for a networkx graph.

        If a layout callable is provided, use its result (falling back to the
        automatic layout when it returns nothing).  Otherwise, if every node
        carries an explicit 'pos' attribute, use those coordinates; finally
        fall back to a graphviz layout and then a spring layout.  Domain
        specific placement (e.g. laying a mesh out on a grid) is supplied by
        the caller instead of being hard-coded here.
        """
        if callable(layout):
            try:
                coords = layout(graph)
            except Exception:
                coords = None
            if coords:
                return coords

        # Use explicit per-node 'pos' attributes if every node provides one.
        coords = dict()
        for node in graph.nodes():
            pos = graph.nodes[node].get('pos')
            if pos is None:
                coords = None
                break
            coords[node] = tuple(pos)

        if coords:
            return coords

        try:
            return networkx.nx_agraph.graphviz_layout(graph, prog='dot')
        except Exception:
            return networkx.spring_layout(graph, seed=42)

    def __networkx_add_links(self, graph, assembly: str = None,
                             splitName: list = None,
                             splitNameLen: int = None,
                             highlight_inter_rank: bool = False,
                             self_links: bool = True,
                             full_labels: bool = False) -> None:
        """Add edges to the graph with a label for the number of edges."""
        def port2Node(port: DevicePort) -> str:
            """Return a node name given a DevicePort."""
            node = port.device.name
            if node == assembly:
                return f"{port.device.type}:{port.name}"
            elif assembly is not None:
                if splitName == node.split('.')[0:splitNameLen]:
                    node = '.'.join(node.split('.')[splitNameLen:])
            return node

        # Create a list of all of the links.  Self-links are included by
        # default and can be toggled off via self_links.
        links = list()
        inter_rank_keys = set()
        for p0, p1 in self.links:
            n0 = port2Node(p0)
            n1 = port2Node(p1)
            if not self_links and n0 == n1:
                continue
            key = tuple(sorted((n0, n1)))
            links.append(key)
            # Flag links that cross a rank boundary for highlighting.
            if highlight_inter_rank:
                pa0 = getattr(p0.device, 'partition', None)
                pa1 = getattr(p1.device, 'partition', None)
                if (pa0 is not None and pa1 is not None
                        and pa0[0] != pa1[0]):
                    inter_rank_keys.add(key)

        # Setup a counter so we can check for duplicates
        duplicates = collections.Counter(links)
        for key in duplicates:
            label = ''
            if duplicates[key] > 1:
                label = str(duplicates[key])

            key0, key1 = key
            for node in (key0, key1):
                if node not in graph:
                    display = node if full_labels else \
                        self.__networkx_label(node, node)
                    graph.add_node(node, color='lightblue', display=display)
            # Add edges using the number of links as a label
            graph.add_edge(key0, key1, label=label,
                           inter_rank=key in inter_rank_keys)

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
                               label='', submodule=True)

    @staticmethod
    def __render_networkx(graph, name: str, output: str,
                          draw: bool = False, save_graph: str = None,
                          layout=None) -> None:
        """Render a networkx graph to a PNG image using matplotlib.

        If save_graph is provided, the networkx graph object is also written
        to disk (pickle/GraphML/GEXF, chosen by file extension).
        """
        if save_graph is not None:
            DeviceGraph.__save_networkx_graph(graph, save_graph, output)

        try:
            import matplotlib.pyplot as plt
        except ImportError:
            raise ImportError(
                "matplotlib is required for rendering NetworkX images; "
                "install it with 'pip install matplotlib'"
            )

        pos = DeviceGraph.__networkx_layout(graph, layout)

        fig, ax = plt.subplots(figsize=(12, 10))

        node_colors = [
            graph.nodes[n].get('color', 'lightblue') for n in graph.nodes()
        ]
        networkx.draw_networkx_nodes(graph, pos, ax=ax,
                                     node_color=node_colors,
                                     node_size=500, alpha=0.9)

        # Categorize edges: submodule (dashed purple), inter-rank
        # (highlighted red), and normal (gray).
        submodule_edges = [
            (u, v) for u, v, d in graph.edges(data=True)
            if d.get('submodule')
        ]
        inter_rank_edges = [
            (u, v) for u, v, d in graph.edges(data=True)
            if d.get('inter_rank') and not d.get('submodule')
        ]
        normal_edges = [
            (u, v) for u, v, d in graph.edges(data=True)
            if not d.get('submodule') and not d.get('inter_rank')
        ]
        networkx.draw_networkx_edges(graph, pos, ax=ax, edgelist=normal_edges,
                                     edge_color='gray', alpha=0.5)
        if inter_rank_edges:
            networkx.draw_networkx_edges(graph, pos, ax=ax,
                                         edgelist=inter_rank_edges,
                                         edge_color='red', width=2.0,
                                         alpha=0.8)
        if submodule_edges:
            networkx.draw_networkx_edges(graph, pos, ax=ax,
                                         edgelist=submodule_edges,
                                         edge_color='purple', style='dashed',
                                         alpha=0.6)

        labels = {n: graph.nodes[n].get('display', n) for n in graph.nodes()}
        networkx.draw_networkx_labels(graph, pos, labels, ax=ax, font_size=8)

        # Label parallel links with their count
        edge_labels = {
            (u, v): d['label'] for u, v, d in graph.edges(data=True)
            if d.get('label')
        }
        if edge_labels:
            networkx.draw_networkx_edge_labels(graph, pos,
                                               edge_labels=edge_labels,
                                               ax=ax, font_size=7)

        ax.set_title(
            f"{name}\nNodes: {graph.number_of_nodes()}, "
            f"Edges: {graph.number_of_edges()}"
        )
        ax.axis('off')
        fig.tight_layout()
        fig.savefig(f"{output}/{name}.png", dpi=150, bbox_inches='tight')
        if draw:
            try:
                plt.show()
            except Exception:
                pass
        plt.close(fig)

    @staticmethod
    def render_networkx_graph(graph, name: str, output: str = "output",
                              draw: bool = False,
                              save_graph: str = None,
                              layout=None,
                              node_label=None) -> None:
        """Render a standalone networkx graph object to a PNG image.

        This is the public entry point for rendering a networkx graph that did
        not come directly from a live DeviceGraph, such as one reloaded from a
        pickle/GraphML/GEXF file saved via write_networkx(save_graph=...).  It
        uses the same node colors and inter-rank/submodule edge styling as
        write_networkx, reading each node's optional 'color' and 'display'
        attributes and each edge's optional 'label', 'inter_rank', and
        'submodule' attributes.

        The layout parameter (a callable graph -> {node: (x, y)}) and the
        node_label parameter (a callable node -> label) mirror the same
        options on write_networkx, keeping any domain-specific placement or
        labeling in the caller.  When node_label is provided it overrides each
        node's stored 'display' attribute.
        """
        if networkx is None:
            raise ImportError(
                "networkx is required for render_networkx_graph; "
                "install it with 'pip install networkx matplotlib'"
            )
        if not os.path.exists(output):
            os.makedirs(output)
        if callable(node_label):
            for node in graph.nodes():
                graph.nodes[node]['display'] = DeviceGraph.__networkx_label(
                    node, graph.nodes[node].get('display', str(node)),
                    node_label)
        DeviceGraph.__render_networkx(graph, name, output, draw,
                                      save_graph=save_graph, layout=layout)

    @staticmethod
    def __save_networkx_graph(graph, save_graph: str,
                              output: str = None) -> None:
        """Save a networkx graph object to disk.

        The file format is chosen from the file extension of save_graph:
        '.pickle'/'.pkl'/'.gpickle' write a Python pickle, '.graphml' writes
        GraphML, and '.gexf' writes GEXF.  Any other (or missing) extension
        defaults to a Python pickle.  A bare filename (no directory) is
        written into the output folder when one is provided.
        """
        # Resolve the destination path, defaulting bare names to output/.
        if output and not os.path.dirname(save_graph):
            path = os.path.join(output, save_graph)
        else:
            path = save_graph
        directory = os.path.dirname(path)
        if directory and not os.path.exists(directory):
            os.makedirs(directory)

        ext = os.path.splitext(path)[1].lower()

        if ext in ('.graphml', '.gexf'):
            # GraphML/GEXF only support scalar attributes, so stringify any
            # complex values (e.g., partition tuples) on a copy.
            clean = graph.copy()
            for _, data in clean.nodes(data=True):
                for k, v in list(data.items()):
                    if v is not None and not isinstance(
                            v, (str, int, float, bool)):
                        data[k] = str(v)
            for _, _, data in clean.edges(data=True):
                for k, v in list(data.items()):
                    if v is not None and not isinstance(
                            v, (str, int, float, bool)):
                        data[k] = str(v)
            if ext == '.graphml':
                networkx.write_graphml(clean, path)
            else:
                networkx.write_gexf(clean, path)
        else:
            import pickle
            with open(path, 'wb') as f:
                pickle.dump(graph, f)

    @staticmethod
    def dot_to_networkx(paths, output: str = None, combine: bool = False,
                        pattern: str = '*.dot', suffix: str = '_from_dot',
                        combined_name: str = 'combined',
                        layout=None, node_label=None) -> None:
        """
        Read graphviz DOT files and render them as NetworkX images.

        This is the companion to write_dot/write_networkx: instead of building
        images from a live DeviceGraph, it reads existing .dot files (such as
        those produced by write_dot), converts each into a networkx graph, and
        renders a PNG using the same styling.

        paths may be a single path or a list of paths.  Each path can be a
        directory (searched using pattern) or an individual .dot file.

        If output is None, images are written alongside their source .dot
        files; otherwise they are written into the output directory.  The
        suffix is appended to each image filename to avoid overwriting any
        existing PNGs.  When combine is True, all DOT files are merged into a
        single image named combined_name + suffix.

        The layout parameter (a callable graph -> {node: (x, y)}) and the
        node_label parameter (a callable node -> label) mirror the same
        options on write_networkx, keeping any domain-specific placement or
        labeling in the caller instead of hard-coded in this library.
        """
        if networkx is None:
            raise ImportError(
                "networkx is required for dot_to_networkx; "
                "install it with 'pip install networkx matplotlib'"
            )

        try:
            from networkx.drawing.nx_agraph import read_dot as _read_dot
        except ImportError:
            try:
                from networkx.drawing.nx_pydot import read_dot as _read_dot
            except ImportError:
                raise ImportError(
                    "reading DOT files requires either pygraphviz or pydot; "
                    "install one with 'pip install pygraphviz' or "
                    "'pip install pydot'"
                )

        if isinstance(paths, str):
            paths = [paths]

        # Expand directories/files into a sorted list of .dot files.
        dot_files = list()
        for entry in paths:
            if os.path.isdir(entry):
                dot_files.extend(
                    sorted(glob.glob(os.path.join(entry, pattern)))
                )
            elif entry.endswith('.dot') and os.path.isfile(entry):
                dot_files.append(entry)
            else:
                print(f"Skipping {entry}: not a .dot file or directory")
        if not dot_files:
            raise SystemExit("No .dot files found.")

        def _prepare(raw):
            """Normalize a DOT-read graph for rendering."""
            graph = networkx.Graph(raw)
            # Drop self-loops for a cleaner visualization.
            graph.remove_edges_from(networkx.selfloop_edges(graph))
            # Compute compact display labels and clean node colors.
            for node in graph.nodes():
                graph.nodes[node]['display'] = \
                    DeviceGraph.__networkx_label(node, str(node), node_label)
                color = graph.nodes[node].get('color')
                if color:
                    graph.nodes[node]['color'] = str(color).strip().strip('"')
            # Clean any edge count labels carried over from write_dot.
            for _, _, data in graph.edges(data=True):
                label = data.get('label')
                if label is not None:
                    data['label'] = str(label).strip().strip('"')
            return graph

        if combine:
            merged = networkx.Graph()
            for dot_file in dot_files:
                merged = networkx.compose(merged, _prepare(_read_dot(dot_file)))
            out_dir = output if output else (os.path.dirname(dot_files[0]) or '.')
            if not os.path.exists(out_dir):
                os.makedirs(out_dir)
            DeviceGraph.__render_networkx(
                merged, f"{combined_name}{suffix}", out_dir, False, layout=layout
            )
        else:
            for dot_file in dot_files:
                graph = _prepare(_read_dot(dot_file))
                out_dir = output if output else (os.path.dirname(dot_file) or '.')
                if not os.path.exists(out_dir):
                    os.makedirs(out_dir)
                stem = os.path.splitext(os.path.basename(dot_file))[0]
                DeviceGraph.__render_networkx(
                    graph, f"{stem}{suffix}", out_dir, False, layout=layout
                )