"""
Abstract HPC cluster.

This demonstrates how assemblies in PyDL can be used to build systems
out of small components
This example utilizes sst-elements to start with a processor and memory
and then build all the way up to a cluster
"""
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
    """Router"""

    def __init__(self, name, **kwargs):
        """Initialize."""
        super().__init__(name, kwargs)


@assembly
@port('network', Port.Single, 'network')
class SimpleServer(Device):
    """Server constructed of a processor and some memory."""

    def __init__(self, name, model, datasheet, **kwargs):
        """Store our name"""
        super().__init__(name, model, kwargs)
        self.datasheet = datasheet

    def expand(self):
        """Expand the server into its components."""
        graph = DeviceGraph()  # initialize a Device Graph
        # add myself to the graph, useful if the assembly has ports
        graph.add(self)
        info = self.datasheet['SimpleServer'][self.attr['model']]
        cacheInfo = self.datasheet['Cache']

        cacheAttr = cacheInfo['L2']
        cacheAttr['cache_frequency'] = info['L2_freq']
        cacheAttr['cache_size'] = info['L2_size']
        l2 = Cache(f"{self.name}.L2Cache", 'L2', attr=cacheAttr)
        graph.add(l2)

        cacheAttr = cacheInfo['L1']
        cacheAttr['cache_frequency'] = info['L1_freq']
        cacheAttr['cache_size'] = info['L1_size']
        for i in range(info['cpus']):
            cpu = BaseCPU(f"{self.name}.BaseCPU{i}",
                          attr={'clock': info['cpu_freq']})
            rand = RandomGenerator(f"{self.name}.RandomGenerator{i}",
                                   attr={'count': info['randomCount'],
                                   'max_address': info['max_addr']})
                                   # 'max_address': info['mem_size']})
            cpu.add_subcomponent(rand, "generator")
            graph.add(cpu)

            l1 = Cache(f"{self.name}.L1Cache{i}", 'L1', attr=cacheAttr)
            graph.add(l1)

            graph.link(cpu.cache_link, l1.high_network)
            graph.link(l1.low_network, l2.high_network(i))

        memCtrl = MemController(f"{self.name}.MemCtrl",
                                attr={'addr_range_end': info['mem_size']})
        mem = simpleMem(f"{self.name}.RAM",
                        attr={'mem_size': info['mem_size']})
        memCtrl.add_subcomponent(mem, "backend")
        graph.add(memCtrl)

        # link to server
        #graph.link(cpu.src, self.network)
        graph.link(l2.low_network, mem.direct_link)

        return graph


@assembly
@port('network', Port.Multi, 'network', Port.Optional)
class SimpleRack(Device):
    """Rack constructed of a router and some servers."""

    def __init__(self, name, model, datasheet, **kwargs):
        """Store our name"""
        super().__init__(name, model, kwargs)
        self.datasheet = datasheet

    def expand(self):
        """Expand the rack into its components."""
        graph = DeviceGraph()  # initialize a Device Graph
        # add myself to the graph, useful if the assembly has ports
        graph.add(self)
        info = self.datasheet['SimpleRack'][self.attr['model']]

        router = Router(f"{self.name}.Router")
        graph.add(router)

        for i in range(info['number']):
            server = SimpleServer(f"{self.name}.Server{i}",
                                  info['server'], self.datasheet)
            graph.add(server)
            graph.link(router.network(i), server.network)

        return graph


if __name__ == "__main__":
    """
    If we are running as a script (either via Python or from SST), then
    proceed.  Check if we are running with SST or from Python.
    """
    import argparse
    try:
        import sst

        SST = True
    except ImportError:
        SST = False

    parser = argparse.ArgumentParser(
        description='HPC Cluster Simulation')
    parser.add_argument('--model', type=str,
        help='optional top level model to use')
    parser.add_argument('--datasheet', type=str,
        help='optional datasheet file')
    args = parser.parse_args()

    # Read in our DataSheet with parameters for each device
    datasheet_file = 'datasheet.json'
    if args.datasheet is not None:
        datasheet_file = args.datasheet
    # loads a DataSheet and removes comments, result is most likely
    # a Python Dictionary, with dictionaries and lists nested inside
    datasheet = DataSheet.load(datasheet_file)

    # Construct a DeviceGraph and put HPC into it, then flatten the graph
    # and make sure the connections are valid
    # set verbosity as a global SST parameter
    graph = DeviceGraph({'verbose': 0})

    # read in the model if provided
    model = 'half'
    if args.model is not None:
        model = args.model
    graph.add(SimpleRack('Rack', model=model, datasheet=datasheet))

    # flatten the graph and verify it is linked properly
    graph = graph.flatten()
    graph.verify_links()

    builder = BuildSST()

    if SST:
        # If running within SST, generate the SST graph
        builder.build(graph)

    else:
        # generate a graphviz dot file and json output for demonstration
        graph.write_dot_file('HPC', draw=True, ports=True)
        builder.write(graph, 'HPC.json')
