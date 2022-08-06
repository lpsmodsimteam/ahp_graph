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

Using SST components:
```bash
$ make sst
g++  -std=c++1y -D__STDC_FORMAT_MACROS -fPIC -DHAVE_CONFIG_H -I/home/sst/sst-core/include -MMD -c Pong.cpp -o .build/Pong.o
g++  -std=c++1y -D__STDC_FORMAT_MACROS -fPIC -DHAVE_CONFIG_H -I/home/sst/sst-core/include -MMD -c Ping.cpp -o .build/Ping.o
g++  -std=c++1y -D__STDC_FORMAT_MACROS -fPIC -DHAVE_CONFIG_H -I/home/sst/sst-core/include -shared -fno-common -Wl,-undefined -Wl,dynamic_lookup -o libpingpong.so .build/Pong.o .build/Ping.o
sst-register pingpong pingpong_LIBDIR=/scratch/examples/pingpong/sst
sst pingpong.py
PingPong1.Ping0-> Maximum Repeats: 5
PingPong0.Ping0-> Maximum Repeats: 5
PingPong0.Pong0-> Received message: Ping0
PingPong0.Pong0-> Sent message: Ping0-Pong0
PingPong1.Pong0-> Received message: Ping0
PingPong1.Pong0-> Sent message: Ping0-Pong0
PingPong0.Ping0-> Received message: Ping0-Pong0
PingPong0.Ping0-> Repeats: 1
PingPong0.Ping0-> Sent message: Ping0-Pong0-Ping0
PingPong1.Ping0-> Received message: Ping0-Pong0
PingPong1.Ping0-> Repeats: 1
PingPong1.Ping0-> Sent message: Ping0-Pong0-Ping0
PingPong0.Pong0-> Received message: Ping0-Pong0-Ping0
PingPong0.Pong0-> Sent message: Ping0-Pong0-Ping0-Pong0
PingPong1.Pong0-> Received message: Ping0-Pong0-Ping0
PingPong1.Pong0-> Sent message: Ping0-Pong0-Ping0-Pong0
PingPong0.Ping0-> Received message: Ping0-Pong0-Ping0-Pong0
PingPong0.Ping0-> Repeats: 2
PingPong0.Ping0-> Sent message: Ping0-Pong0-Ping0-Pong0-Ping0
PingPong1.Ping0-> Received message: Ping0-Pong0-Ping0-Pong0
PingPong1.Ping0-> Repeats: 2
PingPong1.Ping0-> Sent message: Ping0-Pong0-Ping0-Pong0-Ping0
PingPong0.Pong0-> Received message: Ping0-Pong0-Ping0-Pong0-Ping0
PingPong0.Pong0-> Sent message: Ping0-Pong0-Ping0-Pong0-Ping0-Pong0
PingPong1.Pong0-> Received message: Ping0-Pong0-Ping0-Pong0-Ping0
PingPong1.Pong0-> Sent message: Ping0-Pong0-Ping0-Pong0-Ping0-Pong0
PingPong0.Ping0-> Received message: Ping0-Pong0-Ping0-Pong0-Ping0-Pong0
PingPong0.Ping0-> Repeats: 3
PingPong0.Ping0-> Sent message: Ping0-Pong0-Ping0-Pong0-Ping0-Pong0-Ping0
PingPong1.Ping0-> Received message: Ping0-Pong0-Ping0-Pong0-Ping0-Pong0
PingPong1.Ping0-> Repeats: 3
PingPong1.Ping0-> Sent message: Ping0-Pong0-Ping0-Pong0-Ping0-Pong0-Ping0
PingPong0.Pong0-> Received message: Ping0-Pong0-Ping0-Pong0-Ping0-Pong0-Ping0
PingPong0.Pong0-> Sent message: Ping0-Pong0-Ping0-Pong0-Ping0-Pong0-Ping0-Pong0
PingPong1.Pong0-> Received message: Ping0-Pong0-Ping0-Pong0-Ping0-Pong0-Ping0
PingPong1.Pong0-> Sent message: Ping0-Pong0-Ping0-Pong0-Ping0-Pong0-Ping0-Pong0
PingPong0.Ping0-> Received message: Ping0-Pong0-Ping0-Pong0-Ping0-Pong0-Ping0-Pong0
PingPong0.Ping0-> Repeats: 4
PingPong0.Ping0-> Sent message: Ping0-Pong0-Ping0-Pong0-Ping0-Pong0-Ping0-Pong0-Ping0
PingPong1.Ping0-> Received message: Ping0-Pong0-Ping0-Pong0-Ping0-Pong0-Ping0-Pong0
PingPong1.Ping0-> Repeats: 4
PingPong1.Ping0-> Sent message: Ping0-Pong0-Ping0-Pong0-Ping0-Pong0-Ping0-Pong0-Ping0
PingPong0.Pong0-> Received message: Ping0-Pong0-Ping0-Pong0-Ping0-Pong0-Ping0-Pong0-Ping0
PingPong0.Pong0-> Sent message: Ping0-Pong0-Ping0-Pong0-Ping0-Pong0-Ping0-Pong0-Ping0-Pong0
PingPong1.Pong0-> Received message: Ping0-Pong0-Ping0-Pong0-Ping0-Pong0-Ping0-Pong0-Ping0
PingPong1.Pong0-> Sent message: Ping0-Pong0-Ping0-Pong0-Ping0-Pong0-Ping0-Pong0-Ping0-Pong0
PingPong0.Ping0-> Received message: Ping0-Pong0-Ping0-Pong0-Ping0-Pong0-Ping0-Pong0-Ping0-Pong0
PingPong0.Ping0-> Repeats: 5
PingPong1.Ping0-> Received message: Ping0-Pong0-Ping0-Pong0-Ping0-Pong0-Ping0-Pong0-Ping0-Pong0
PingPong1.Ping0-> Repeats: 5
Simulation is complete, simulated time: 15 s
```
