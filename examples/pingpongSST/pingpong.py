"""Simple example of two SST components playing pingpong with messages."""

import os
import sys

from AHPGraph import *


@library('pingpong.Ping')
@port('input', 'StringEvent')
@port('output', 'StringEvent')
class Ping(Device):
    """Ping Device: has a Name and a Model type."""

    def __init__(self, name: str, size: int = 10,
                 attr: dict = None) -> 'Device':
        """Size parameter is stored as the model attribute of a device."""
        super().__init__(name, size, attr)


@library('pingpong.Pong')
@port('input', 'StringEvent')
@port('output', 'StringEvent')
class Pong(Device):
    """Pong Device."""

    def __init__(self, name: str, attr: dict = None) -> 'Device':
        """No model for Pong."""
        super().__init__(name, attr=attr)


@assembly
@port('input', 'StringEvent')
@port('output', 'StringEvent')
class pingpong(Device):
    """Assembly of a ping and pong device with connections outside."""

    def __init__(self, name: str, size: int = 10,
                 attr: dict = None) -> 'Device':
        """Size parameter is stored as the model attribute of a device."""
        super().__init__(name, size, attr)

    def expand(self) -> 'DeviceGraph':
        """Expand the overall architecture into its components."""
        graph = DeviceGraph()  # initialize a Device Graph

        # create a Ping Device
        # Device names created by an assembly will automatically have the
        # assembly name prefixed to the name provided.
        ping = Ping('Ping', self.model)
        pong = Pong('Pong')  # create a Pong Device

        # link ping and pong, automatically adds the devices to the graph
        graph.link(ping.output, pong.input, '1s')

        # Generally you don't want to put latency on the links to assembly
        # ports (ex: self.port) and allow whatever uses the assembly to
        # specify latency for the connection (it will get ignored anyway)

        # Connect pingpong's input to ping's input
        graph.link(ping.input, self.input)
        # Connect pingpong's output to pong's output
        graph.link(pong.output, self.output)

        return graph


def architecture(repeats: int = 10, num: int = 1) -> 'DeviceGraph':
    """Create pingpong(s) and link them together in a loop."""
    graph = DeviceGraph()
    pingpongs = dict()

    for i in range(num):
        pingpongs[i] = pingpong(f"PingPong{i}", repeats)
        pingpongs[i].set_partition(i)

    for i in range(num):
        graph.link(pingpongs[i].output, pingpongs[(i+1) % num].input, '2s')

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

    parser = argparse.ArgumentParser(description='PingPong')
    parser.add_argument('--num', type=int, default=2,
                        help='how many pingpongs to include')
    parser.add_argument('--repeats', type=int, default=5,
                        help='how many message volleys to run')
    parser.add_argument('--partitioner', type=str, default='sst',
                        help='which partitioner to use: ahpgraph, sst')
    args = parser.parse_args()

    # Construct a DeviceGraph with the specified architecture
    graph = architecture(args.repeats, args.num)
    sstgraph = SSTGraph(graph)

    if SST:
        # If running within SST, generate the SST graph
        # There are multiple ways to run, below are a few common examples

        # SST partitioner
        # This will work in serial or running SST with MPI in parallel
        if args.partitioner.lower() == 'sst':
            sstgraph.build()

        # MPI mode with AHPGraph graph partitioning. Specifying nranks tells
        # AHPGraph that it is doing the partitioning, not SST
        # For this to work you need to pass --parallel-load=SINGLE to sst
        elif args.partitioner.lower() == 'ahpgraph':
            sstgraph.build(args.num)

    else:
        # generate a graphviz dot file and json output for demonstration
        graph.write_dot('pingpongFlat', draw=True, ports=True, hierarchy=False)
        sstgraph.write_json('pingpongFlat.json')

        # generate a different view including the hierarchy, and write out
        # the AHPGraph partitioned graph
        graph.write_dot('pingpong', draw=True, ports=True)
        sstgraph.write_json('pingpong.json', nranks=args.num)
