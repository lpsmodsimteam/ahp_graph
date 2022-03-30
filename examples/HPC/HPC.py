"""
Abstract HPC cluster.

This demonstrates how assemblies in PyDL can be used to build systems
out of small components
This example utilizes sst-elements to start with a processor and memory
and then build all the way up to a cluster
"""
from .Devices import *
from PyDL import *


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
            cpuInfo = self.datasheet['BaseCPU']
            cpuInfo['clock'] = info['cpu_freq']
            cpu = BaseCPU(f"{self.name}.BaseCPU{i}", attr=cpuInfo)

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

        memInfo = self.datasheet['MemController']
        memInfo['addr_range_end'] = info['mem_size']
        memCtrl = MemController(f"{self.name}.MemCtrl", attr=memInfo)

        memInfo = self.datasheet['simpleMem']
        memInfo['mem_size'] = info['mem_size']
        mem = simpleMem(f"{self.name}.RAM", attr=memInfo)
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

        router = Router(f"{self.name}.Router",
                        self.datasheet['Router']['ports'])
        graph.add(router)

        # connect the servers to the router
        for i in range(info['number']):
            server = SimpleServer(f"{self.name}.Server{i}",
                                  info['server'], self.datasheet)
            graph.add(server)
            graph.link(router.network(i), server.network)

        # make all the extra ports available outside the rack
        for i in range(self.datasheet['Router']['ports'] - info['number']):
            graph.link(router.network(None), self.network(None))

        return graph


@assembly
class SimpleCluster(Device):
    """Example HPC Cluster built out of racks. Using a 2D mesh network."""

    def __init__(self, name, model, datasheet, **kwargs):
        """Store our name"""
        super().__init__(name, model, kwargs)
        self.datasheet = datasheet

    def expand(self):
        """Expand the cluster into its components."""
        graph = DeviceGraph()  # initialize a Device Graph
        info = self.datasheet['SimpleCluster'][self.attr['model']]

        dimensions = info['mesh'].split('x')
        racks = dict()
        for x in range(dimensions[0]):
            for y in range(dimensions[1]):
                racks[f"{x}x{y}"] = SimpleRack(f"{self.name}.Rack{x}x{y}",
                                               info['rack'], self.datasheet)
                graph.add(racks[f"{x}x{y}"])

        # initialize the four mesh ports
        # order is 0: north, 1: east, 2: south, 3: west
        for x in range(dimensions[0]):
            for y in range(dimensions[1]):
                # connect to rack to the east if available
                if x < (dimensions[0] - 1):
                    graph.link(racks[f"{x}x{y}"].network(1),
                               racks[f"{x}x{y}"].network(3))

                # connect to rack to the north if available
                if y < (dimensions[1] - 1):
                    graph.link(racks[f"{x}x{y}"].network(0),
                               racks[f"{x}x{y}"].network(2))


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
    model = 'small'
    if args.model is not None:
        model = args.model
    graph.add(SimpleCluster('Cluster', model=model, datasheet=datasheet))

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
