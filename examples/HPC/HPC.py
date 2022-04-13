"""
Abstract HPC cluster.

This demonstrates how assemblies in PyDL can be used to build systems
out of small components
This example utilizes sst-elements to start with a processor and memory
and then build all the way up to a cluster
"""
from PyDL.examples.HPC.server import Server
from PyDL import *


# remove this eventually
from PyDL.examples.HPC.processor import Processor


@sstlib('merlin.hr_router')
@port('port', Port.Multi, 'network', Port.Optional, '#')
class Router(Device):
    """Router"""

    def __init__(self, name, model, attr):
        """Initialize with a model describing the number of ports."""
        super().__init__(name, model, attr)


@sstlib('merlin.torus')
class TorusTopology(Device):
    """Torus Topology"""

    def __init__(self, name, attr):
        """Initialize."""
        super().__init__(name, attr=attr)


@assembly
@port('network', Port.Multi, 'network', Port.Optional)
class Rack(Device):
    """Rack constructed of a router and some servers."""

    def __init__(self, name, model, networkParams, datasheet):
        """Store our name"""
        super().__init__(name, model)
        self.networkParams = networkParams
        self.datasheet = datasheet

    def expand(self):
        """Expand the rack into its components."""
        graph = DeviceGraph()  # initialize a Device Graph
        # add myself to the graph, useful if the assembly has ports
        graph.add(self)
        info = self.datasheet['SimpleRack'][self.attr['model']]

        # use num_ports as the router model since that can change the
        # overall system graph if it changes
        routerInfo = self.datasheet['Router']
        routerInfo.update(self.networkParams)
        router = Router(f"{self.name}.Router",
                        routerInfo['num_ports'], routerInfo)

        topoInfo = self.datasheet['Topology']
        topoInfo.update(self.networkParams)
        topology = TorusTopology(f"{self.name}.TorusTopology", topoInfo)
        router.add_subcomponent(topology, "topology")

        graph.add(router)

        # make all the torus ports available outside the rack
        for i in range(4):
            graph.link(router.port('port', i), self.network(i))

        # connect the servers to the router
        for i in range(info['number']):
            server = SimpleServer(f"{self.name}.Server{i}",
                                  info['server'], self.datasheet)
            graph.add(server)
            graph.link(router.port('port', None), server.network)

        return graph


def Cluster(name, model, datasheet) -> 'DeviceGraph':
    """Example HPC Cluster built out of racks. Using a 2D torus network."""
    graph = DeviceGraph()  # initialize a Device Graph
    info = datasheet['SimpleCluster'][model]

    # setup some network parameters that we need to pass to the racks
    # which can then inform the routers about the overall network layout
    dimensions = [int(dim) for dim in info['torus'].split('x')]
    servers = datasheet['SimpleRack'][info['rack']]['number']
    networkParams = dict()
    networkParams['num_peers'] = servers * dimensions[0] * dimensions[1]
    networkParams['torus.shape'] = info['torus']
    networkParams['torus.local_ports'] = servers

    racks = dict()
    id = 0
    for x in range(dimensions[0]):
        for y in range(dimensions[1]):
            networkParams['id'] = id
            racks[f"{x}x{y}"] = SimpleRack(f"{name}.Rack{x}x{y}",
                                           info['rack'], networkParams,
                                           datasheet)
            graph.add(racks[f"{x}x{y}"])
            id += 1

    # initialize the four torus ports
    # order is 0: north, 1: east, 2: south, 3: west
    for x in range(dimensions[0]):
        for y in range(dimensions[1]):
            graph.link(racks[f"{x}x{y}"].network(1),
                       racks[f"{(x+1) % dimensions[0]}x{y}"].network(3))

            graph.link(racks[f"{x}x{y}"].network(0),
                       racks[f"{x}x{(y+1) % dimensions[1]}"].network(2))

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

    graph = DeviceGraph()
    cpu = Processor('Processor', 0, 0)
    graph.add(cpu)
    flat = graph.flatten()
    flat.write_dot_file('HPC', draw=True, ports=True)
    builder = BuildSST()
    builder.write(flat, 'HPC.json')

    exit()

    # Construct a DeviceGraph from SimpleCluster, then flatten the graph
    # and make sure the connections are valid
    graph = SimpleCluster('Cluster', model, datasheet)
    # set verbosity as a global SST parameter
    graph.attr['verbose'] = 0
    # graph.verify_links()

    # flatten the graph and verify it is linked properly
    flat = graph.flatten()
    # flat.verify_links()

    builder = BuildSST()

    if SST:
        # If running within SST, generate the SST graph
        builder.build(flat)

    else:
        # generate a graphviz dot file and json output for demonstration
        flat.write_dot_file('HPC_Cluster', draw=True, ports=True)
        graph.write_dot_hierarchy('HPC', draw=True, ports=True)
        builder.write(flat, 'HPC.json')
