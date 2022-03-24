This directory implements a simple Ping Pong message passing simulation by utilizing PyDL

In this case, Ping is the initiator of the "ping pong" message bouncing back and forth

Looking at pingpong.py, you can see some basic imports and environment setup at the top.
This is followed by the PyDL definitions of Ping and Pong. Both are simple with a single
inout port. The class pingpong describes the overall "architecture" that we are
creating. In this example, pingpong takes one optional argument to describe the number
of messages to send. First a PyDL DeviceGraph is made followed by the construction of
Ping and Pong devices. Ping and Pong devices are then added to the graph and linked
appropriately to one another.

The end of pingpong.py is unique in that it allows you to run the file both from python3
and from sst. If you run the file from python3, sst will not be able to be imported and
the code will create the PyDL DeviceGraph and then write out a graphviz dot file
representing the architecture. If you run the file from sst, sst can be imported and so
we need to build SST with the graph to begin the simulation.
