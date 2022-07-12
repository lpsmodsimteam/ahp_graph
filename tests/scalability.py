"""Generate a large graph using a recursive binary tree method."""

from ahp_graph.Device import *
from ahp_graph.DeviceGraph import *
from Devices import *


def generateGraph(levels: int) -> DeviceGraph:
    """
    Generate a DeviceGraph using a psuedo - Binary Tree.

    The number of components in the fully flattened graph will be
    2 + 2 ** (levels + 2)
    """
    graph = DeviceGraph()

    ratd0 = RecursiveAssemblyTestDevice(levels, 0)
    ratd1 = RecursiveAssemblyTestDevice(levels, 1)
    lptd0 = LibraryPortTestDevice(0)
    lptd1 = LibraryPortTestDevice(1)

    # complete the rings
    graph.link(ratd0.input, ratd0.output)
    graph.link(ratd1.input, ratd1.output)

    graph.link(lptd0.input, lptd1.output)
    graph.link(lptd1.input, lptd0.output)
    for i in range(2 ** (levels+1)):
        graph.link(lptd0.optional(None), ratd0.optional(None))
        graph.link(lptd1.optional(None), ratd1.optional(None))

    ratd0.set_partition(0)
    ratd1.set_partition(1)
    lptd0.set_partition(2)
    lptd1.set_partition(2)

    return graph


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(
        description='AHPGraph DeviceGraph unittests')
    parser.add_argument('-l', '--levels', type=int,
                        help='how many levels to recurse')
    args = parser.parse_args()

    graph = generateGraph(args.levels)
    graph.flatten()
