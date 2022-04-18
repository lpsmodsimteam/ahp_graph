"""
Abstract HPC cluster.

This demonstrates how assemblies in PyDL can be used to build systems
out of small components
This example utilizes sst-elements to start with a processor and memory
and then build all the way up to a cluster
"""
from PyDL.examples.HPC.server import *
from PyDL import *


@sstlib('merlin.torus')
class TorusTopology(Device):
    """Torus Topology"""

    def __init__(self, name: str, shape: str = '2x2', nodes: int = 1,
                 attr: dict = None) -> 'Device':
        """Initialize."""
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
        """Store our name"""
        super().__init__(name, f"{nodes}Node_{cores}Core", attr)
        self.attr['shape'] = shape
        self.attr['rack'] = rack
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
        graph.add(router)

        # make all the torus ports available outside the rack
        for i in range(4):
            graph.link(router.port('port', i), self.network(i))

        # connect the servers to the router
        for node in range(self.attr['nodes']):
            server = Server(f"{self.name}.Server{node}",
                            (self.attr['rack'] * self.attr['nodes']) + node,
                            self.attr['cores'])
            graph.add(server)
            graph.link(router.port('port', None), server.network)

        return graph


def Cluster(dimX: int = 2, dimY: int = 2, nodes: int = 1,
            cores: int = 1) -> 'DeviceGraph':
    """Example HPC Cluster built out of racks. Using a 2D torus network."""
    graph = DeviceGraph()  # initialize a Device Graph
    shape = f"{dimX}x{dimY}"

    racks = dict()
    for x in range(dimX):
        for y in range(dimY):
            racks[f"{x}x{y}"] = Rack(f"Rack{x}x{y}", shape, (x * dimY) + y,
                                     nodes, cores)
            graph.add(racks[f"{x}x{y}"])

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
    args = parser.parse_args()

    # read in the model if provided
    model = 'small'
    if args.model is not None:
        model = args.model

    builder = BuildSST()

    # graph = DeviceGraph()
    # cpu = Processor('CPU', 0)
    # graph.add(cpu)
    # flat = graph.flatten()
    # flat.write_dot_file('CPU', draw=True, ports=True)
    # builder.write(flat, 'CPU.json')
    #
    # graph = DeviceGraph()
    # server = Server('server', 0, 1)
    # graph.add(server)
    # flat = graph.flatten()
    # graph.write_dot_hierarchy('server', draw=True, ports=True)
    # flat.write_dot_file('serverFlat', draw=True, ports=True)
    # builder.write(flat, 'server.json')
    #
    # graph = DeviceGraph()
    # rack = Rack('rack', '2x2', 0, 1, 1)
    # graph.add(rack)
    # flat = graph.flatten()
    # graph.write_dot_hierarchy('rack', draw=True, ports=True)
    # flat.write_dot_file('rackFlat', draw=True, ports=True)
    # builder.write(flat, 'rack.json')

    graph = Cluster(2, 2, 16, 4)
    flat = graph.flatten()
    graph.write_dot_hierarchy('cluster', draw=True, ports=True)
    builder.write(flat, 'cluster.json')

    exit()

    if SST:
        # If running within SST, generate the SST graph
        builder.build(flat)

    else:
        # generate a graphviz dot file and json output for demonstration
        flat.write_dot_file('HPC_Cluster', draw=True, ports=True)
        graph.write_dot_hierarchy('HPC', draw=True, ports=True)
        builder.write(flat, 'HPC.json')
