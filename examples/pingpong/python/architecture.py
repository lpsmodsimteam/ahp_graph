#!/usr/bin/env python3

"""ahp_graph architecture describing PingPong."""

from ahp_graph.Device import *
from ahp_graph.DeviceGraph import *


class Ping(Device):
    """Ping Device: has a Name and a Model type."""

    library = 'pingpong.Ping' # this is set in the respective .h file using SST_ELI_REGISTER_COMPONENT
    portinfo = PortInfo()
    portinfo.add('input', 'String')
    portinfo.add('output', 'String')


class Pong(Device):
    """Pong Device."""

    library = 'pingpong.Pong' # this is set in the respective .h file using SST_ELI_REGISTER_COMPONENT
    portinfo = PortInfo()
    portinfo.add('input', 'String')
    portinfo.add('output', 'String')


class pingpong(Device):
    """Assembly of a Ping and Pong device with connections outside."""

    portinfo = PortInfo()
    portinfo.add('input', 'String')
    portinfo.add('output', 'String')

    def expand(self, graph: DeviceGraph) -> None:
        """Expand the overall architecture into its components."""
        # create a Ping Device
        # Device names created by an assembly will automatically have the
        # assembly name prefixed to the name provided.
        ping = Ping('Ping', self.model)
        pong = Pong('Pong')  # create a Pong Device

        # link ping and pong, automatically adds the devices to the graph
        graph.link(ping.output, pong.input, '1s')  # type: ignore[arg-type]

        # Generally you don't want to put latency on the links to assembly
        # ports (ex: self.port) and allow whatever uses the assembly to
        # specify latency for the connection (it will get ignored anyway)

        # Connect pingpong's input to ping's input
        graph.link(ping.input, self.input)  # type: ignore[arg-type]
        # Connect pingpong's output to pong's output
        graph.link(pong.output, self.output)  # type: ignore[arg-type]


def architecture(repeats: int = 10, num: int = 1) -> DeviceGraph:
    """Create pingpong(s) and link them together in a loop."""
    graph = DeviceGraph()
    pingpongs = dict()

    for i in range(num):
        pingpongs[i] = pingpong(f"PingPong{i}", str(repeats))
        pingpongs[i].set_partition(i)

    for i in range(num):
        graph.link(pingpongs[i].output, pingpongs[(i+1) % num].input, '2s')  # type: ignore[arg-type]

    return graph
