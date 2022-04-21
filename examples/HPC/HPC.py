"""
Abstract HPC cluster.

This demonstrates how assemblies in PyDL can be used to build systems
out of small components.
This example utilizes sst-elements to start with a processor and memory
and then build all the way up to a cluster.
"""
from PyDL import *
from server import *


@sstlib('merlin.torus')
class TorusTopology(Device):
    """Torus Topology."""

    def __init__(self, name: str, shape: str = '2x2', nodes: int = 1,
                 attr: dict = None) -> 'Device':
        """Initialize using the shape as the model."""
        parameters = {
            "shape": shape,
            "width": "1x1",
            "local_ports": nodes
        }
        if attr is not None:
            parameters.update(attr)
        super().__init__(name, shape, parameters)


@assembly
@port('network', Port.Multi, 'simpleNet', Port.Optional)
class Rack(Device):
    """Rack constructed of a router and some servers."""

    def __init__(self, name: str, shape: str = '2x2', rack: int = 0,
                 nodes: int = 1, cores: int = 1,
                 attr: dict = None) -> 'Device':
        """Store our name and the model describing nodes and cores per node."""
        super().__init__(name, f"{nodes}Node_{cores}Core", attr)
        self.attr['shape'] = shape
        self.attr['rack'] = rack
        dimX = int(shape.split('x')[0])
        dimY = int(shape.split('x')[1])
        self.attr['racks'] = dimX * dimY
        self.attr['nodes'] = nodes
        self.attr['cores'] = cores

    def expand(self) -> 'DeviceGraph':
        """Expand the rack into its components."""
        graph = DeviceGraph()  # initialize a Device Graph

        router = Router(f"{self.name}.Router", 'Interconnect',
                        self.attr['rack'], self.attr['nodes'] + 4)
        topology = TorusTopology(f"{self.name}.TorusTopology",
                                 self.attr['shape'], self.attr['nodes'])
        router.add_subcomponent(topology, "topology")

        # make all the torus ports available outside the rack
        for i in range(4):
            # Generally you don't want to put latency on the links to assembly
            # ports (ex: self.port) and allow whatever uses the assembly to
            # specify latency for the connection (it will get ignored anyway)
            graph.link(router.port('port', i), self.network(i))

        # connect the servers to the router
        for node in range(self.attr['nodes']):
            server = Server(f"{self.name}.Server{node}",
                            (self.attr['rack'] * self.attr['nodes']) + node,
                            self.attr['racks'], self.attr['nodes'],
                            self.attr['cores'])
            graph.link(router.port('port', None), server.network, '10ns')

        return graph


def Cluster(shape: str = '2x2', nodes: int = 1,
            cores: int = 1) -> 'DeviceGraph':
    """HPC Cluster built out of racks. Using a 2D torus network."""
    graph = DeviceGraph()  # initialize a Device Graph
    dimX = int(shape.split('x')[0])
    dimY = int(shape.split('x')[1])

    racks = dict()
    for x in range(dimX):
        for y in range(dimY):
            racks[f"{x}x{y}"] = Rack(f"Rack{x}x{y}", shape, (x * dimY) + y,
                                     nodes, cores)
            # graph.add(racks[f"{x}x{y}"])

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
    parser.add_argument('--shape', type=str,
                        help='optional shape to use for the topology')
    parser.add_argument('--nodes', type=int,
                        help='optional number of nodes per rack')
    parser.add_argument('--cores', type=int,
                        help='optional number of cores per server')
    parser.add_argument('--partitioner', type=str,
                        help='which partitioner to use: pydl, sst')
    args = parser.parse_args()

    # read in the variables if provided
    shape = '2x2'
    nodes = 1
    cores = 1
    partitioner = 'sst'
    if args.partitioner is not None:
        partitioner = args.partitioner
    if args.shape is not None:
        shape = args.shape
    if args.nodes is not None:
        nodes = args.nodes
    if args.cores is not None:
        cores = args.cores

    dims = [int(x) for x in shape.split('x')]
    racks = dims[0] * dims[1]

    # Create a cluster with the given parameters
    graph = Cluster(shape, nodes, cores)
    # Make each rack its own partition (rank)
    for rack in graph.devices.values():
        rack.set_partition(rack.attr['rack'])

    builder = BuildSST()

    if SST:
        # If running within SST, generate the SST graph
        # There are multiple ways to run, below are a few common examples

        # SST partitioner
        # This will work in serial or running SST with MPI in parallel
        if partitioner.lower() == 'sst':
            builder.build(graph)

        # MPI mode with PyDL graph partitioning. Specifying nranks tells
        # BuildSST that it is doing the partitioning, not SST
        # For this to work you need to pass --parallel-load=SINGLE to sst
        elif partitioner.lower() == 'pydl':
            builder.build(graph, nranks=racks)

    else:
        # generate a graphviz dot file and json output for demonstration
        graph.write_dot_hierarchy('cluster', draw=True, ports=True)
        # partially expanding the graph only expands the portions of the graph
        # relevant to the rank being output at that time, therefore saving
        # memory by not flattening the entire graph all at once
        builder.write(graph, 'cluster.json', racks, partialExpand=True)
