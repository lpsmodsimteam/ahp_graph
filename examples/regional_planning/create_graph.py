
from ahp_graph.DeviceGraph import *
from ahp_graph.SSTGraph import *
from assemblies_and_components import regional_plan 

import argparse


if __name__ == "__main__":
    """
    If we are running as a script (either via Python or from SST), then
    proceed.  Check if we are running with SST or from Python.
    """
    try:
        import sst
        SST = True
    except ImportError:
        SST = False

    parser = argparse.ArgumentParser(description='regional planning')
    parser.add_argument('--num', type=int, default=2,
                        help='number of neighborhoods')
    parser.add_argument('--rank', type=int, default=0,
                        help='which rank to generate the JSON file for')
    parser.add_argument('--partitioner', type=str, default='sst',
                        help='which partitioner to use: ahp_graph, sst')
    args = parser.parse_args()

    # Construct a DeviceGraph with the specified architecture
    graph = regional_plan(args.num)
    sstgraph = SSTGraph(graph)

    if SST:
        # If running within SST, generate the SST graph
        # There are multiple ways to run, below are two examples

        # SST partitioner
        # This will work in serial or running SST with MPI in parallel
        if args.partitioner.lower() == 'sst':
            sstgraph.build()

        # MPI mode with ahp_graph graph partitioning. Specifying nranks tells
        # ahp_graph that it is doing the partitioning, not SST
        # For this to work you need to pass --parallel-load=SINGLE to sst
        elif args.partitioner.lower() == 'ahp_graph':
            sstgraph.build(args.num)

    else:
        # SST partitioner
        # This will generate a flat dot graph and a single JSON file
        if args.partitioner.lower() == 'sst':
            graph.flatten()
            graph.write_dot('the_regional_plan_flat', draw=True, ports=True, hierarchy=False)
            sstgraph.write_json('the_regional_plan_flat')

        # If ahp_graph is partitioning, we generate a hierarchical DOT graph
        # and a JSON file for the rank that is specified from the command line
        elif args.partitioner.lower() == 'ahp_graph':
            if args.rank == 0:
                graph.write_dot('the_regional_plan', draw=True, ports=True)
            sstgraph.write_json('the_regional_plan', nranks=args.num, rank=args.rank)

#EOF
