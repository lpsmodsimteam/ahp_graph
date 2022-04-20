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
        # add myself to the graph, useful if the assembly has ports
        graph.add(self)

        router = Router(f"{self.name}.Router", 'Interconnect',
                        self.attr['rack'], self.attr['nodes'] + 4)
        topology = TorusTopology(f"{self.name}.TorusTopology",
                                 self.attr['shape'], self.attr['nodes'])
        router.add_subcomponent(topology, "topology")
        # graph.add(router)

        # make all the torus ports available outside the rack
        for i in range(4):
            graph.link(router.port('port', i), self.network(i))

        # connect the servers to the router
        for node in range(self.attr['nodes']):
            server = Server(f"{self.name}.Server{node}",
                            (self.attr['rack'] * self.attr['nodes']) + node,
                            self.attr['racks'], self.attr['nodes'],
                            self.attr['cores'])
            # graph.add(server)
            graph.link(router.port('port', None), server.network)

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
                       racks[f"{(x+1) % dimX}x{y}"].network(3))

            graph.link(racks[f"{x}x{y}"].network(0),
                       racks[f"{x}x{(y+1) % dimY}"].network(2))

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
    args = parser.parse_args()

    # read in the variables if provided
    shape = '2x2'
    nodes = 1
    cores = 1
    if args.shape is not None:
        shape = args.shape
    if args.nodes is not None:
        nodes = args.nodes
    if args.cores is not None:
        cores = args.cores

    graph = Cluster(shape, nodes, cores)
    flat = graph.flatten()
    flat.verify_links()

    builder = BuildSST()

    if SST:
        # If running within SST, generate the SST graph
        builder.build(flat)

    else:
        # generate a graphviz dot file and json output for demonstration
        graph.write_dot_hierarchy('cluster', draw=True, ports=True)
        graph.write_dot_file("clusterFlat", draw=True, ports=True)
        builder.write(flat, 'cluster.json')
