"""Simple example of two SST components playing pingpong with messages."""

import os
import sys

from PyDL import *


@sstlib("pingpong.Ping")
@port("input", Port.Single, 'StringEvent', Port.Required)
@port("output", Port.Single, 'StringEvent', Port.Required)
class Ping(Device):
    """Ping Device: has a Name and a Model type."""

    def __init__(self, name: str, size: int = 10,
                 attr: dict = None) -> 'Device':
        """Size parameter is stored as the model attribute of a device."""
        super().__init__(name, size, attr)


@sstlib("pingpong.Pong")
@port("input", Port.Single, 'StringEvent', Port.Required)
@port("output", Port.Single, 'StringEvent', Port.Required)
class Pong(Device):
    """Pong Device."""

    def __init__(self, name: str, attr: dict = None) -> 'Device':
        """No model for Pong."""
        super().__init__(name, attr=attr)


@assembly
@port("input", Port.Single, 'StringEvent', Port.Optional)
@port("output", Port.Single, 'StringEvent', Port.Optional)
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
        ping = Ping("Ping", self.attr["model"])
        pong = Pong("Pong")  # create a Pong Device

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
    parser.add_argument('--num', type=int,
                        help='how many pingpongs to include')
    parser.add_argument('--partitioner', type=str,
                        help='which partitioner to use: pydl, sst')
    args = parser.parse_args()

    # read in the variables if provided
    num = 2
    partitioner = 'sst'
    if args.num is not None:
        num = args.num
    if args.partitioner is not None:
        partitioner = args.partitioner

    # Construct a DeviceGraph with the specified architecture
    graph = architecture(5, num)
    # partition the graph
    for p in graph.devices.values():
        p.set_partition(int(p.name.split('PingPong')[1]))

    if SST:
        # If running within SST, generate the SST graph
        # There are multiple ways to run, below are a few common examples

        # SST partitioner
        # This will work in serial or running SST with MPI in parallel
        if partitioner.lower() == 'sst':
            graph.build_sst()

        # MPI mode with PyDL graph partitioning. Specifying nranks tells
        # PyDL that it is doing the partitioning, not SST
        # For this to work you need to pass --parallel-load=SINGLE to sst
        elif partitioner.lower() == 'pydl':
            graph.build_sst(num)

    else:
        # generate a graphviz dot file and json output for demonstration
        graph.write_dot("pingpongFlat", draw=True, ports=True, hierarchy=False)
        graph.write_json("pingpongFlat.json")

        # generate a different view including the hierarchy, and write out
        # the PyDL partitioned graph
        graph.write_dot("pingpong", draw=True, ports=True)
        graph.write_json("pingpong.json", nranks=num)
