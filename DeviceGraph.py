"""
This module implements support for AHP (attributed hierarchical port) graphs.

This class of graph supports attributes on the nodes (devices), links that are
connected to named ports on the nodes, and the non-simple nodes that may be
represented by a hierarchical graph (aka an assembly).
All links are unidirectional.
"""

import os
import gc
import orjson
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
        t0 = devs[0].get_portinfo()[p0.name]['type']
        t1 = devs[1].get_portinfo()[p1.name]['type']

        if t0 != t1:
            raise RuntimeError(
                f"Port type mismatch: {t0} != {t1} between"
                f"{devs[0].name} and {devs[1].name}"
            )
        self.links[linkName] = (p0, p1, latency)

    def add(self, device: 'Device') -> None:
        """
        Add a Device to the graph.

        The device must be a AHPGraph Device. The name must be unique.
        If the device has sub-components, then we add those, as well.
        Do NOT add sub-components to a device after you have added it using
        this function. Add sub-components first, then add the parent.
        """
        if device.name in self.devices:
            raise RuntimeError(f"Name already in graph: {device.name}")
        self.devices[device.name] = device
        for (dev, _, _) in device.subs:
            self.add(dev)

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

    def verify_links(self) -> None:
        """Verify that all required ports are linked up."""
        # Create a map of devices to all ports linked on those devices.
        d2ports = collections.defaultdict(set)
        for (p0, p1, _) in self.links.values():
            d2ports[p0.device].add(p0.name)
            d2ports[p1.device].add(p1.name)

        # Walk all devices and make sure required ports are connected.
        for device in self.devices.values():
            portinfo = device.get_portinfo()
            for name in portinfo:
                if portinfo[name]['required'] and name not in d2ports[device]:
                    raise RuntimeError(f"{device.name} requires port {name}")

    def check_partition(self) -> None:
        """Check to make sure the graph has ranks specified for all devices."""
        for d in self.devices.values():
            if d.partition is None:
                raise RuntimeError(f"No partition for component: {d.name}")

    def follow_links(self, rank: int) -> 'DeviceGraph':
        """
        Chase links between ranks.

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
                if (p0.device.partition[0] == rank
                        or p1.device.partition[0] == rank):
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
        if levels == 0:
            return self

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
                assembly &= rank == dev.partition[0]
            # check to see if the device is in the expand set
            if expand is not None:
                assembly &= dev in expand

            if assembly:
                assemblies.append(dev)

        if not assemblies:
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
            subgraph = device.expand()

            # Expanded devices inherit the partition of the parent.
            # Also prepend the assembly's name to the names of the new devices
            for d in subgraph.devices.values():
                if d != device:
                    d.partition = device.partition
                    d.name = f"{device.name}.{d.name}"

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
                        return (p1, t)
                return (None, None)

            # Update the links. Latency will come from the link defined
            # higher up in the hierarchy
            for (p0, p1, t) in subgraph.links.values():
                if p0.device == device:
                    (p2, t2) = find_other_port(p0)
                    if p2 is not None:
                        links[p1.device].add((p1, p2, t2))
                        links[p2.device].add((p2, p1, t2))
                elif p1.device == device:
                    (p2, t2) = find_other_port(p1)
                    if p2 is not None:
                        links[p0.device].add((p0, p2, t2))
                        links[p2.device].add((p2, p0, t2))
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

    def build_sst(self, nranks: int = 1) -> dict:
        """
        Build the SST graph.

        Return a dictionary of component names to SST component objects.
        If you have an extremely large graph, it is recommended that you use
        AHPGraph to do the graph partitioning instead of letting SST do it. You
        can do this by using the Device.set_partition() function and then
        setting nranks in this function to the total number of ranks used
        """
        # only import sst when we are going to build the graph
        import sst

        # If this is serial or sst is doing the partitioning,
        # generate the entire graph
        if nranks == 1:
            self = self.flatten()
            self.verify_links()
            return self.__build_model(False)

        # Find the partition information and build the model for this rank
        else:
            sst.setProgramOption("partitioner", "sst.self")
            rank = sst.getMyMPIRank()
            # If this is an extra rank, don't do anything
            if rank >= nranks:
                return dict()

            self.check_partition()
            rankGraph = self.flatten(rank=rank).follow_links(rank)
            rankGraph.verify_links()
            return rankGraph.__build_model(True)

    def write_json(self, filename: str, nranks: int = 1,
                   program_options: dict = None) -> None:
        """
        Generate the JSON and write it to the specified filename.

        All output will be stored in a folder called output

        The program_options dictionary provides a way to pass SST
        program options, such as timebase and stopAtCycle.

        If you have an extremely large graph, it is recommended that you use
        AHPGraph to do the graph partitioning instead of letting SST do it. You
        can do this by using the Device.set_partition() function and then
        setting nranks in this function to the total number of ranks used
        """
        if not os.path.exists('output'):
            os.makedirs('output')

        # If this is serial or sst is doing the partitioning,
        # just write the whole thing
        if nranks == 1:
            self = self.flatten()
            self.verify_links()
            self.__write_model(f"output/{filename}", nranks, program_options)

        # Write a JSON file for each rank
        else:
            (base, ext) = os.path.splitext(f"output/{filename}")
            self.check_partition()

            for rank in range(nranks):
                rankGraph = self.flatten(rank=rank).follow_links(rank)
                rankGraph.verify_links()
                rankGraph.__write_model(base + str(rank) + ext,
                                        nranks, program_options)

                # Manually remove each graph to make sure we don't overflow
                del rankGraph
                gc.collect()

    def write_dot(self, name: str, draw: bool = False, ports: bool = False,
                  hierarchy: bool = True) -> None:
        """
        Take a DeviceGraph and write it as a graphviz dot graph.

        All output will be stored in a folder called output

        The draw parameter will automatically generate SVGs if set to True
        The ports parameter will display ports on the graph if set to True

        The hierarchy parameter specifies whether you would like to view the
        graph as a hierarchy of assemblies or if you would like to flatten
        the entire graph and view it as a single file
        hierarchy is True by default, and highly recommended for large graphs
        """
        if not os.path.exists('output'):
            os.makedirs('output')

        if hierarchy:
            self.__write_dot_hierarchy(name, draw, ports)
        else:
            self.__write_dot_flat(name, draw, ports)

    def __write_dot_hierarchy(self, name: str,
                              draw: bool = False, ports: bool = False,
                              assembly: str = None, types: set = None) -> set:
        """
        Take a DeviceGraph and write dot files for each assembly.

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
                    types = expanded.__write_dot_hierarchy(category, draw,
                                                           ports, dev.name,
                                                           types)

        # graph the current graph
        # need to check if the provided assembly name is in the graph
        # and if so make that our cluster
        if assembly is not None:
            for dev in self.devices.values():
                if assembly == dev.name:
                    # this device is the assembly that we just expanded
                    # make this a cluster and add its ports as nodes
                    clusterName = f"cluster_{dev.type}"
                    subgraph = graph.subgraph(name=clusterName, color='green')
                    for port in dev.ports:
                        graph.add_node(f"{dev.type}:{port}",
                                       shape='diamond', label=port,
                                       color='green', fontcolor='green')
        else:
            # no provided assembly, this is most likely the top level
            subgraph = graph

        # Loop through all devices and add them to the graphviz graph
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

        graph.write(f"output/{name}.dot")
        if draw:
            graph.draw(f"output/{name}.svg", format='svg', prog='dot')

        return types

    def __write_dot_flat(self, name: str, draw: bool = False,
                         ports: bool = False) -> None:
        """
        Write the device graph as a DOT file.

        This function will flatten the graph so it is not recommended for using
        on large graphs. It is suggested that you use write_dot_hierarchy for
        large graphs
        """
        self = self.flatten()
        self.verify_links()
        graph = self.__format_graph(name, ports)

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

        graph.write(f"output/{name}.dot")
        if draw:
            graph.draw(f"output/{name}.svg", format='svg', prog='dot')

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
        if not os.path.exists('output'):
            os.makedirs('output')

        if not os.path.exists('output/highlightStyle.css'):
            with open('output/highlightStyle.css', 'w') as f:
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
        for (p0, p1, latency) in self.links.values():
            links.append((port2Node(p0), port2Node(p1)))

        # Setup a counter so we can check for duplicates
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
            # Add edges using the number of links as a label
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

    def __encode(self, attr, stringify: bool = False) -> dict:
        """
        Convert attributes into SST Params.

        SST only supports primitive types (bool, int, float) and lists of those
        types as parameters; everything else we will convert via JSON.
        If the attribute contains a __to_json__ method, then we will call it.
        Ignore bad conversions.
        """

        def supported_f(x) -> bool:
            """Return whether the type is supported by SST."""
            return isinstance(x, (bool, float, int, str))

        params = dict()
        for (key, val) in attr.items():
            native = supported_f(val)
            if not native and isinstance(val, list):
                native = all(map(supported_f, val))

            if native:
                params[key] = val if not stringify else str(val)
            elif hasattr(val, "__to_json__"):
                params[key] = val.__to_json__()
            else:
                try:
                    # serialize the value to json bytes,
                    # then deserialize into a python dict
                    params[key] = orjson.loads(
                        orjson.dumps(val, option=orjson.OPT_INDENT_2)
                    )
                except Exception:
                    pass

        return params

    def __build_model(self, self_partition: bool) -> dict:
        """Generate the model for the SST program."""
        # only import sst when we are going to build the graph inside of sst
        import sst
        n2c = dict()

        # Set up global parameters.
        global_params = self.__encode(self.attr)
        for (key, val) in global_params.items():
            sst.addGlobalParam(key, key, val)

        def recurseSubcomponents(dev: 'Device', comp: 'Component'):
            """Add subcomponents to the Device."""
            for (d1, n1, s1) in dev.subs:
                if d1.sstlib is None:
                    raise RuntimeError(f"No SST library: {d1.name}")
                if s1 is None:
                    c1 = comp.setSubComponent(n1, d1.sstlib)
                else:
                    c1 = comp.setSubComponent(n1, d1.sstlib, s1)
                c1.addParams(self.__encode(d1.attr))
                n2c[d1.name] = c1
                for key in global_params:
                    c1.addGlobalParamSet(key)
                if len(d1.subs) > 0:
                    recurseSubcomponents(d1, c1)

        # First, we instantiate all of the components with
        # their attributes. Ignore Devices that have no sstlib defined
        for d0 in self.devices.values():
            if d0.subOwner is None and d0.sstlib is not None:
                c0 = sst.Component(d0.name, d0.sstlib)
                c0.addParams(self.__encode(d0.attr))
                # Set the component partition if we are self-partitioning
                if self_partition:
                    c0.setRank(d0.partition[0], d0.partition[1])
                n2c[d0.name] = c0
                for key in global_params:
                    c0.addGlobalParamSet(key)
                recurseSubcomponents(d0, c0)

        # Second, link the component ports using graph links.
        for (name, (p0, p1, t)) in self.links.items():
            if p0.device.sstlib is not None and p1.device.sstlib is not None:
                c0 = n2c[p0.device.name]
                c1 = n2c[p1.device.name]
                s0 = p0.get_name()
                s1 = p1.get_name()
                link = sst.Link(name)
                link.connect((c0, s0, t), (c1, s1, t))

        # Return a map of component names to components.
        return n2c

    def __write_model(self, filename: str, nranks: int,
                      program_options: dict) -> None:
        """Write this DeviceGraph out as JSON."""
        model = dict()

        # Write the program options to the model.
        if program_options is None:
            model["program_options"] = dict()
        else:
            model["program_options"] = dict(program_options)

        # If running in parallel, then set up the SST SELF partitioner.
        if nranks > 1:
            model["program_options"]["partitioner"] = "sst.self"

        # Set up global parameters.
        global_params = self.__encode(self.attr, True)
        model["global_params"] = dict()
        for (key, val) in global_params.items():
            model["global_params"][key] = dict({key: val})
        global_set = list(global_params.keys())

        def recurseSubcomponents(dev: 'Device') -> list:
            """Add subcomponents to the Device."""
            subcomponents = list()
            for (d1, n1, s1) in dev.subs:
                if d1.sstlib is None:
                    raise RuntimeError(f"No SST library: {d1.name}")

                item = {
                        "slot_name": n1,
                        "type": d1.sstlib,
                        "slot_number": s1,
                        "params": self.__encode(d1.attr, True),
                        "params_global_sets": global_set,
                    }
                if len(d1.subs) > 0:
                    item["subcomponents"] = recurseSubcomponents(d1)
                subcomponents.append(item)
            return subcomponents

        # Define all the components. We define the name, type, parameters,
        # and global parameters. Ignore Devices that have no sstlib defined
        components = list()
        for d0 in self.devices.values():
            if d0.subOwner is None and d0.sstlib is not None:
                component = {
                    "name": d0.name,
                    "type": d0.sstlib,
                    "params": self.__encode(d0.attr, True),
                    "params_global_sets": global_set,
                }
                if d0.partition is not None:
                    component["partition"] = {
                        "rank": d0.partition[0],
                        "thread": d0.partition[1],
                    }

                subcomponents = recurseSubcomponents(d0)
                if len(subcomponents) > 0:
                    component["subcomponents"] = subcomponents
                components.append(component)

        model["components"] = components

        # Now define the links between components.
        links = list()
        for (name, (p0, p1, t)) in self.links.items():
            if p0.device.sstlib is not None and p1.device.sstlib is not None:
                links.append(
                    {
                        "name": name,
                        "left": {
                            "component": p0.device.name,
                            "port": p0.get_name(),
                            "latency": t,
                        },
                        "right": {
                            "component": p1.device.name,
                            "port": p1.get_name(),
                            "latency": t,
                        },
                    }
                )

        model["links"] = links

        with open(filename, "wb") as jfile:
            jfile.write(orjson.dumps(model, option=orjson.OPT_INDENT_2))
