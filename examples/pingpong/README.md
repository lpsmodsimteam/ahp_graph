This directory implements a simple Ping Pong message passing simulation by utilizing PyDL

In this case, Ping is the initiator of the "ping pong" message bouncing back and forth

Looking at pingpong.py, you can see some basic imports and environment setup at the top.
This is followed by the PyDL definitions of Ping and Pong. Both are simple with a
input and output port. The class pingpong describes an assembly that we are
creating. In this example, pingpong takes one optional argument to describe the number
of messages to send. Our overall architecture is constructed by creating a loop with the
given number of pingpong assemblies.

The end of pingpong.py is unique in that it allows you to run the file both from python3
and from sst. If you run the file from python3, sst will not be able to be imported and
the code will create the PyDL DeviceGraph and then write out a graphviz dot file
representing the architecture. If you run the file from sst, sst can be imported and so
we need to build SST with the graph to begin the simulation.

One important thing to note with running SST simulations is that before actually
simulating anything, SST usually executes a graph partitioning phase. This phase
allows SST to distribute models among MPI ranks (if available). Since our PyDL
architecture is built with hierarchy, it can be trivial to partition the graph and
simply provide SST with this information so it can skip its own partitioning. When
doing the partitioning in PyDL, you have to be careful to include certain flags
when running SST to tell it to load the PyDL file and distribute it among all the
ranks.

When you look at the output of pingpong, each line of output will start with
something like: 'PingPong#.Ping#->'. The number after PingPong represents which
instance of the PingPong assembly the device is coming from. The number following
Ping or Pong represents the mpi rank that the device is running on. Similarly, in
the messages Ping and Pong are followed by a number again representing the rank
that the device was running on.
