Create an HPC using components from SST elements

This is still a work in progress. The simulation will not run
successfully yet but the graph construction works.


Run the command
```bash
$ python3 HPC.py
```
and then open `output/cluster.svg` in Firefox. The nodes are hyperlinked to the assembly expansion.


Help is available:
```bash
$ python3 HPC.py -h 
usage: HPC.py [-h] [--shape SHAPE] [--nodes NODES] [--cores CORES]
              [--partitioner PARTITIONER]

HPC Cluster Simulation

optional arguments:
  -h, --help            show this help message and exit
  --shape SHAPE         optional shape to use for the topology
  --nodes NODES         optional number of nodes per rack
  --cores CORES         optional number of cores per server
  --partitioner PARTITIONER
                        which partitioner to use: ahp_graph, sst
```
