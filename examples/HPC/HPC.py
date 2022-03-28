"""
Abstract HPC cluster.

This demonstrates how assemblies in PyDL can be used to build systems
out of small components
This example utilizes sst-elements to start with a processor and memory
and then build all the way up to a cluster
"""

import os
import sys

from PyDL import *


@sstlib('miranda.BaseCPU')
@port('cache_link', Port.Single, 'simpleMem')
@port('src', Port.Single, 'network')
class BaseCPU(Device):
    """Miranda base CPU."""

    def __init__(self, name, **kwargs):
        """Initialize."""
        super().__init__(name, kwargs)


@sstlib('miranda.RandomGenerator')
class RandomGenerator(Device):
    """Random Generator for the miranda base CPU."""

    def __init__(self, name, **kwargs):
        """Initialize with the maxAddress set."""
        super().__init__(name, kwargs)


@sstlib('memHierarchy.Cache')
@port('high_network', Port.Single, 'simpleMem')
@port('low_network', Port.Single, 'simpleMem')
class Cache(Device):
    """Cache"""

    def __init__(self, name, model, **kwargs):
        """Initialize."""
        super().__init__(name, model, kwargs)


@sstlib('memHierarchy.MemController')
@port('direct_link', Port.Single, 'simpleMem')
class MemController(Device):
    """MemController"""

    def __init__(self, name, **kwargs):
        """Initialize."""
        super().__init__(name, kwargs)


@sstlib('memHierarchy.simpleMem')
class simpleMem(Device):
    """simpleMem"""

    def __init__(self, name, **kwargs):
        """Initialize."""
        super().__init__(name, kwargs)


@sstlib('merlin.hr_router')
@port('network', Port.Multi, 'network')
class Router(Device):
    """Router."""

    def __init__(self, name, **kwargs):
        """Initialize."""
        super().__init__(name, kwargs)


@assembly
@port('network', Port.Single, 'network')
class SimpleServer(Device):
    """Server constructed of a processor and some memory."""

    def __init__(self, name, **kwargs):
        """Store our name"""
        super().__init__(name, kwargs)

    def expand(self):
        """Expand the server into its components."""
        graph = DeviceGraph()  # initialize a Device Graph
        # add myself to the graph, useful if the assembly has ports
        graph.add(self)

        cpu = BaseCPU(f"{self.name}.BaseCPU")
        rand = RandomGenerator(f"{self.name}.RandomGenerator")
        cpu.add_subcomponent(rand, "generator")

        l1 = Cache(f"{self.name}.L1Cache", "L1")

        memCtrl = MemController(f"{self.name}.MemCtrl")
        mem = simpleMem(f"{self.name}.RAM")
        memCtrl.add_subcomponent(mem, "backend")

        graph.add(cpu)
        graph.add(l1)
        graph.add(memCtrl)

        # link to server
        graph.link(cpu.src, self.network)

        # links internal to server
        graph.link(cpu.cache_link, l1.high_network)
        graph.link(l1.low_network, mem.direct_link)

        return graph


@assembly
@port('network', Port.Multi, 'network', Port.Optional)
class SimpleRack(Device):
    """Rack constructed of a router and some servers."""

    def __init__(self, name, model, **kwargs):
        """Store our name"""
        super().__init__(name, model, kwargs)

    def expand(self):
        """Expand the rack into its components."""
        graph = DeviceGraph()  # initialize a Device Graph
        # add myself to the graph, useful if the assembly has ports
        graph.add(self)

        router = Router(f"{self.name}.Router")
        graph.add(router)

        servers = []
        for i in range(self.attr['model']):
            print(i)
            servers.append(SimpleServer(f"{self.name}.Server{i}"))
            graph.add(servers[i])
            graph.link(router.network(i), servers[i].network)

        return graph


if __name__ == "__main__":
    """
    If we are running as a script (either via Python or from SST), then
    proceed.  Check if we are running with SST or from Python.
    """
    try:
        import sst

        SST = True
    except ImportError:
        SST = False

    # Construct a DeviceGraph and put HPC into it, then flatten the graph
    # and make sure the connections are valid
    graph = DeviceGraph()
    graph.add(SimpleRack("Rack", 5))
    graph = graph.flatten()
    graph.verify_links()

    builder = BuildSST()

    if SST:
        # Read in our DataSheet with parameters for each device
        datasheet = DataSheet.load('datasheet.json')

        # If running within SST, generate the SST graph
        builder.build(graph)

    else:
        # generate a graphviz dot file and json output for demonstration
        graph.write_dot_file("HPC.gv", title="HPC Cluster")
        builder.write(graph, "HPC.json")
