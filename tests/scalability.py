"""Generate a large graph using a recursive tree method."""

from ahp_graph.DeviceGraph import *
from ahp_graph.SSTGraph import *
from Devices import *


def generateGraph(levels: int, assemblies: int = 2) -> DeviceGraph:
    """
    Generate a DeviceGraph using a psuedo - Binary Tree.

    The number of components in the fully flattened graph will be
    assemblies + ( (2 ** (levels + 1)) * assemblies )
    """
    graph = DeviceGraph()

    ratd = list()
    lptd = list()
    for i in range(assemblies):
        ratd.append(RecursiveAssemblyTestDevice(levels, i))
        lptd.append(LibraryPortTestDevice(i))

    # connect everything
    for i in range(assemblies):
        graph.link(ratd[(i+1)%assemblies].input, ratd[i].output)
        graph.link(lptd[(i+1)%assemblies].input, lptd[i].output)

        for j in range(2 ** (levels+1)):
            graph.link(lptd[i].optional(None), ratd[i].optional(None))

    # set partitions
    for i in range(assemblies):
        ratd[i].set_partition(i)
        lptd[i].set_partition(assemblies)

    return graph


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(
        description='AHPGraph DeviceGraph unittests')
    parser.add_argument('-l', '--levels', type=int, default=0,
                        help='how many levels to recurse')
    parser.add_argument('-a', '--assemblies', type=int, default=2,
                        help='how many ratd assemblies to include')
    args = parser.parse_args()

    graph = generateGraph(args.levels, args.assemblies)

    # Various tests to run
    #graph.flatten()
    graph.follow_links(0, True)
