This is the SST specific simulation implementation of the pingpong architecture.

pingpong.py is unique in that it allows you to run the file both from python3
and from sst. If you run the file from python3, sst will not be able to be imported and
the code will create the ahp_graph DeviceGraph and then write out a graphviz dot file
representing the architecture. If you run the file from sst, sst can be imported and so
we need to build SST with the graph to begin the simulation.

Since we are simulating with SST, we have to have SST components defined for each
device in the ahp_graph. In this case, we have Ping and Pong created already in cpp
and hpp files which you can review. The makefile will compile these and register
them with SST so that you can run an ahp_graph simulation.

One important thing to note with running SST simulations is that before actually
simulating anything, SST usually executes a graph partitioning phase. This phase
allows SST to distribute models among MPI ranks (if available). Since our ahp_graph
architecture is built with hierarchy, it can be trivial to partition the graph and
simply provide SST with this information so it can skip its own partitioning. When
doing the partitioning in ahp_graph, you have to be careful to include certain flags
when running SST to tell it to load the ahp_graph file and distribute it among all the
ranks.

When you look at the output of pingpong, each line of output will start with
something like: 'PingPong#.Ping#->'. The number after PingPong represents which
instance of the PingPong assembly the device is coming from. The number following
Ping or Pong represents the mpi rank that the device is running on. Similarly, in
the messages Ping and Pong are followed by a number again representing the rank
that the device was running on.


```bash
$ python3 pingpong.py -h
usage: pingpong.py [-h] [--num NUM] [--repeats REPEATS]
                   [--partitioner PARTITIONER]

PingPong

optional arguments:
  -h, --help            show this help message and exit
  --num NUM             how many pingpongs to include
  --repeats REPEATS     how many message volleys to run
  --partitioner PARTITIONER
                        which partitioner to use: ahp_graph, sst
```
