"""Simple example of two Python functions playing pingpong with messages."""

from AHPGraph import *
from AHPGraph.examples.pingpong.architecture import architecture


class Ping():
    """Example class that sends a ping."""

    def __init__(self, name: str, repeats: int):
        """Init."""
        self.name = name
        self.max = repeats
        self.repeats = 0
        self.output = None

    def start(self):
        """Start the pingpong off by sending ping."""
        print(f'{self.name}: Sending Ping')
        self.output(f'{self.name}: Ping')

    def input(self, string: str):
        """Print input and then send ping if we have more repeats left."""
        print(f'{self.name}: Received {string}')
        self.repeats += 1
        if self.repeats < self.max:
            print(f'{self.name}: Sending Ping')
            self.output(f'{self.name}: Ping')


class Pong():
    """Example class that sends a pong when it recieves input."""

    def __init__(self, name: str):
        """Init."""
        self.name = name
        self.output = None

    def input(self, string: str):
        """Print input and then send pong."""
        print(f'{self.name}: Received {string}')
        print(f'{self.name}: Sending Pong')
        self.output(f'{self.name}: Pong')


def buildPython(graph: 'DeviceGraph') -> None:
    """
    Run the example 'simulation' using the two classes.

    Need to manually build the graph since AHPGraph doesn't support this.
    """
    devs = dict()
    # instantiate all the devices in the graph
    for device in graph.devices:
        if device.type == 'Ping':
            devs[device.name] = eval(f'{device.library.split(".")[1]}('
                                     f'"{device.name}", {args.repeats})')
        elif device.type == 'Pong':
            devs[device.name] = eval(f'{device.library.split(".")[1]}('
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
        def wrapper(dev: 'Device'):
            """Need to wrap the lambda function to protect the device scope."""
            return lambda x: dev.input(x)

        # connect the pingpongs together as specified
        # flip the direction of the one connection since it wraps around
        for (p0, p1) in graph.links:
            n0 = p0.device.name
            n1 = p1.device.name
            if n0 == 'PingPong0.Ping' and n1 == f'PingPong{args.num-1}.Pong':
                devs[n1].output = wrapper(devs[n0])
            else:
                devs[n0].output = wrapper(devs[n1])

    # find the first Ping device and start the 'simulation'
    for device in graph.devices:
        if device.type == 'Ping':
            devs[device.name].start()
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
