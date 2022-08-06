#!/usr/bin/env python3

"""Simple example of two Python functions playing pingpong with messages."""

from ahp_graph.DeviceGraph import *
from ahp_graph.SSTGraph import *
from architecture import architecture
from typing import Callable, Optional


class Ping():
    """Example class that sends a ping."""

    def __init__(self, name: str, repeats: int) -> None:
        """Init."""
        self.name: str = name
        self.max: int = repeats
        self.repeats: int = 0
        self.output: Optional[Callable[[str], None]] = None

    def start(self) -> None:
        """Start the pingpong off by sending ping."""
        print(f'{self.name}: Sending Ping')
        self.output(f'{self.name}: Ping')  # type: ignore[misc]

    def input(self, string: str) -> None:
        """Print input and then send ping if we have more repeats left."""
        print(f'{self.name}: Received {string}')
        self.repeats += 1
        if self.repeats < self.max:
            print(f'{self.name}: Sending Ping')
            self.output(f'{self.name}: Ping')  # type: ignore[misc]


class Pong():
    """Example class that sends a pong when it recieves input."""

    def __init__(self, name: str) -> None:
        """Init."""
        self.name: str = name
        self.output: Optional[Callable[[str], None]] = None

    def input(self, string: str) -> None:
        """Print input and then send pong."""
        print(f'{self.name}: Received {string}')
        print(f'{self.name}: Sending Pong')
        self.output(f'{self.name}: Pong')  # type: ignore[misc]


def buildPython(graph: DeviceGraph) -> None:
    """
    Run the example 'simulation' using the two classes.

    Need to manually build the graph since ahp_graph doesn't support this.
    """
    devs: dict[str, Union[Ping, Pong]] = dict()
    # instantiate all the devices in the graph
    for device in graph.devices:
        if device.type == 'Ping':
            devs[device.name] = eval(f'{device.library.split(".")[1]}('  # type: ignore[union-attr]
                                     f'"{device.name}", {args.repeats})')
        elif device.type == 'Pong':
            devs[device.name] = eval(f'{device.library.split(".")[1]}('  # type: ignore[union-attr]
                                     f'"{device.name}")')
        else:
            print('ERROR, should only have Ping or Pong Devices')
            exit()

    # if we only have one pingpong, manually connect them
    if args.num <= 1:
        pi = devs['PingPong0.Ping']
        po = devs['PingPong0.Pong']
        pi.output = lambda x: po.input(x)
        po.output = lambda x: pi.input(x)
    else:
        def wrapper(dev: Union[Ping, Pong]) -> Callable[[str], None]:
            """Need to wrap the lambda function to protect the device scope."""
            return lambda x: dev.input(x)

        # connect the pingpongs together as specified
        # flip the direction of the one connection since it wraps around
        for p0, p1 in graph.links:
            name0 = p0.device.name
            name1 = p1.device.name
            n0 = int(''.join(filter(str.isdigit, name0)))
            n1 = int(''.join(filter(str.isdigit, name1)))
            t0 = name0.split('.')[1]
            t1 = name1.split('.')[1]
            # by default, we are going to have the first device as output and
            # the second as the input, switch name0 and name1 if that is wrong
            if n0 == n1:
                if t0 == 'Ping' and t1 == 'Pong':
                    pass
                elif t1 == 'Ping' and t0 == 'Pong':
                    (name0, name1) = (name1, name0)
                else:
                    print(f'Numbers equal {n0}, but types'
                          ' do not match {t0}, {t1}')
            else:
                # different PingPong assemblies
                # handle the wrap around case connecting to PingPong0.Ping
                if name0 == 'PingPong0.Ping' and n1 == args.num-1:
                    (name0, name1) = (name1, name0)
                elif name1 == 'PingPong0.Ping' and n0 == args.num-1:
                    pass
                elif n1 > n0:
                    pass
                else:
                    (name0, name1) = (name1, name0)
            devs[name0].output = wrapper(devs[name1])

    # find the first Ping device and start the 'simulation'
    for device in graph.devices:
        if device.type == 'Ping':
            devs[device.name].start()  # type: ignore[union-attr]
            break


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

    # generate a graphviz dot file including the hierarchy
    graph.write_dot('pingpong', draw=True, ports=True)

    # flatten the graph and generate a graphviz dot file
    graph.flatten()
    graph.write_dot('pingpongFlat', draw=True, ports=True, hierarchy=False)

    buildPython(graph)
