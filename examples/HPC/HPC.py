"""
Abstract HPC cluster.

This demonstrates how assemblies in ahp_graph can be used to build systems
out of small components.
This example utilizes sst-elements to start with a processor and memory
and then build all the way up to a cluster.
"""
from ahp_graph.Device import *
from ahp_graph.DeviceGraph import *
from ahp_graph.SSTGraph import *
from server import *


class TorusTopology(Device):
    """Torus Topology."""

    library = 'merlin.torus'
    attr = {
        "width": "1x1"
    }

    def __init__(self, name: str, shape: str = '2x2', nodes: int = 1,
                 attr: dict = None) -> None:
        """Initialize using the shape as the model."""
        super().__init__(name, shape, attr)
        self.attr['shape'] = shape
        self.attr['local_ports'] = nodes


class Rack(Device):
    """Rack constructed of a router and some servers."""

    portinfo = PortInfo()
    portinfo.add('network', 'simpleNet', None, False)

    def __init__(self, name: str, shape: str = '2x2', rack: int = 0,
                 nodes: int = 1, cores: int = 1,
                 attr: dict = None) -> None:
        """Store our name and the model describing nodes and cores per node."""
        super().__init__(name, f"{nodes}Node_{cores}Core", attr)
        self.attr['shape'] = shape
        self.attr['rack'] = rack
        dimX = int(shape.split('x')[0])
        dimY = int(shape.split('x')[1])
        self.attr['racks'] = dimX * dimY
        self.attr['nodes'] = nodes
        self.attr['cores'] = cores

    def expand(self, graph: DeviceGraph) -> None:
        """Expand the rack into its components."""
        # Device names created by an assembly will automatically have the
        # assembly name prefixed to the name provided.
        router = Router("Router", 'Interconnect',
                        self.attr['rack'], self.attr['nodes'] + 4)
        topology = TorusTopology("TorusTopology",
                                 self.attr['shape'], self.attr['nodes'])
        router.add_submodule(topology, "topology")
        router.set_partition(self.partition[0], 0)

        # make all the torus ports available outside the rack
        for i in range(4):
            # Generally you don't want to put latency on the links to assembly
            # ports (ex: self.port) and allow whatever uses the assembly to
            # specify latency for the connection (it will get ignored anyway)
            graph.link(router.port('port', i), self.network(i))

        # connect the servers to the router
        for node in range(self.attr['nodes']):
            server = Server(f"Server{node}",
                            (self.attr['rack'] * self.attr['nodes']) + node,
                            self.attr['racks'], self.attr['nodes'],
                            self.attr['cores'])
            server.set_partition(self.partition[0], node+1)
            graph.link(router.port('port', None), server.network, '10ns')


def Cluster(shape: str = '2x2', nodes: int = 1,
            cores: int = 1) -> DeviceGraph:
    """HPC Cluster built out of racks. Using a 2D torus network."""
    graph = DeviceGraph()  # initialize a Device Graph
    dimX = int(shape.split('x')[0])
    dimY = int(shape.split('x')[1])

    racks = dict()
    for x in range(dimX):
        for y in range(dimY):
            racks[f"{x}x{y}"] = Rack(f"Rack{x}x{y}", shape, (x * dimY) + y,
                                     nodes, cores)
            racks[f"{x}x{y}"].set_partition((x * dimY) + y)

    # initialize the four torus ports
    # order is 0: north, 1: east, 2: south, 3: west
    for x in range(dimX):
        for y in range(dimY):
            graph.link(racks[f"{x}x{y}"].network(1),
                       racks[f"{(x+1) % dimX}x{y}"].network(3), '10ns')

            graph.link(racks[f"{x}x{y}"].network(0),
                       racks[f"{x}x{(y+1) % dimY}"].network(2), '10ns')

    return graph


if __name__ == "__main__":
    """
    If we are running as a script (either via Python or from SST), then
    proceed. Check if we are running with SST or from Python.
    """
    import argparse
    try:
        import sst
        SST = True
    except ImportError:
        SST = False

    parser = argparse.ArgumentParser(
        description='HPC Cluster Simulation')
    parser.add_argument('--shape', type=str, default='2x2',
                        help='optional shape to use for the topology')
    parser.add_argument('--nodes', type=int, default=1,
                        help='optional number of nodes per rack')
    parser.add_argument('--cores', type=int, default=1,
                        help='optional number of cores per server')
    parser.add_argument('--rank', type=int, default=0,
                        help='which rank to generate the JSON file for')
    parser.add_argument('--partitioner', type=str, default='sst',
                        help='which partitioner to use: ahp_graph, sst')
    args = parser.parse_args()

    dims = [int(x) for x in args.shape.split('x')]
    racks = dims[0] * dims[1]

    # Create a cluster with the given parameters
    graph = Cluster(args.shape, args.nodes, args.cores)
    sstgraph = SSTGraph(graph)

    if SST:
        # If running within SST, generate the SST graph
        # There are multiple ways to run, below are a few common examples

        # SST partitioner
        # This will work in serial or running SST with MPI in parallel
        if args.partitioner.lower() == 'sst':
            sstgraph.build()

        # MPI mode with ahp_graph graph partitioning. Specifying nranks tells
        # BuildSST that it is doing the partitioning, not SST
        # For this to work you need to pass --parallel-load=SINGLE to sst
        elif args.partitioner.lower() == 'ahp_graph':
            sstgraph.build(racks)

    else:
        # generate a graphviz dot file and json output for demonstration
        if args.rank == 0:
            graph.write_dot('cluster', draw=True, ports=True)
        sstgraph.write_json('cluster', racks, rank=args.rank)
