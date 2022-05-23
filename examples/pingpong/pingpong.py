"""Simple example of two Python functions playing pingpong with messages."""

import os
import sys

from AHPGraph import *


class PingFunction():
    def __init__(self, name: str, repeats: int):
        self.name = name
        self.max = repeats
        self.repeats = 0
        self.output = None

    def start(self):
        print(f'{self.name}: Sending Ping')
        self.output(f'{self.name}: Ping')

    def input(self, string: str):
        print(f'{self.name}: Received {string}')
        self.repeats += 1
        if self.repeats < self.max:
            print(f'{self.name}: Sending Ping')
            self.output(f'{self.name}: Ping')
        else:
            print(f'{self.name}: Done')


class PongFunction():
    def __init__(self, name: str):
        self.name = name
        self.output = None

    def input(self, string: str):
        print(f'{self.name}: Received {string}')
        print(f'{self.name}: Sending Pong')
        self.output(f'{self.name}: Pong')


@library('pingpong.PingFunction')
@port('input', 'str')
@port('output', 'str')
class Ping(Device):
    """Ping Device: has a Name and a Model type."""

    def __init__(self, name: str, size: int = 10,
                 attr: dict = None) -> 'Device':
        """Size parameter is stored as the model attribute of a device."""
        super().__init__(name, size, attr)


@library('pingpong.PongFunction')
@port('input', 'str')
@port('output', 'str')
class Pong(Device):
    """Pong Device."""

    def __init__(self, name: str, attr: dict = None) -> 'Device':
        """No model for Pong."""
        super().__init__(name, attr=attr)


@assembly
@port('input', 'str')
@port('output', 'str')
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
    import argparse
    parser = argparse.ArgumentParser(description='PingPong')
    parser.add_argument('--num', type=int, default=2,
                        help='how many pingpongs to include')
    parser.add_argument('--repeats', type=int, default=5,
                        help='how many message volleys to run')
    args = parser.parse_args()

    # Construct a DeviceGraph with the specified architecture
    graph = architecture(args.repeats, args.num)

    # generate a graphviz dot file and json output for demonstration
    graph.write_dot('pingpongFlat', draw=True, ports=True, hierarchy=False)

    # generate a different view including the hierarchy, and write out
    # the AHPGraph partitioned graph
    graph.write_dot('pingpong', draw=True, ports=True)

    # run the example 'simulation' using the two classes
    # need to manually build the graph since AHPGraph doesn't support this
    flat = graph.flatten()
    instances = dict()
    print('Devices:')
    for device in flat.devices:
        print(device)
        if flat.devices[device].type == 'Ping':
            instances[device] = PingFunction(device, args.repeats)
        elif flat.devices[device].type == 'Pong':
            instances[device] = PongFunction(device)
        else:
            print('ERROR, should only have Ping or Pong Devices')
            exit()

    print('Links:')
    if args.num <= 1:
        pi = instances['PingPong0.Ping']
        po = instances['PingPong0.Pong']
        print('PingPong0.Ping --> PingPong0.Pong')
        pi.output = lambda x: po.input(x)
        print('PingPong0.Pong --> PingPong0.Ping')
        po.output = lambda x: pi.input(x)
    else:
        for link in flat.links.values():
            n0 = link[0].device.name
            n1 = link[1].device.name
            if n0 == 'PingPong0.Ping' and n1 == f'PingPong{args.num-1}.Pong':
                print(f'{n1} --> {n0}')
                instances[n1].output = lambda x: instances[n0].input(x)
            else:
                print(f'{n0} --> {n1}')
                instances[n0].output = lambda x: instances[n1].input(x)

    print('Running:')
    for device in flat.devices:
        if flat.devices[device].type == 'Ping':
            instances[device].start()
            break
