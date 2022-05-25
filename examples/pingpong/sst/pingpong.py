"""Simple example of two SST components playing pingpong with messages."""

from AHPGraph import *
from AHPGraph.examples.pingpong.architecture import architecture


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