This directory implements a simple Ping Pong message passing simulation by utilizing ahp_graph

In this case, Ping is the initiator of the "ping pong" message bouncing back and forth

architecture.py is defined in the python directory and simply linked to in the sst
directory. This is to show the same graph can be used for multiple different output
types. In architecture.py you can see some basic imports and environment setup at the top.
This is followed by the ahp_graph definitions of Ping and Pong. Both are simple with a
input and output port. The class pingpong describes an assembly that we are
creating. In this example, pingpong takes one optional argument to describe the number
of messages to send. Our overall architecture is constructed by creating a loop with
the given number of pingpong assemblies.

architecture.py by itself is a simple ahp_graph description of pingpong. We can
build a graphviz graph using this description, but we have no way to simulate the
graph at this point. There are two simulation methods included here, python and sst.
The python simulation is included in the python folder and is a very basic set of
function calls to mimic running a simulation. The sst simulation is included in the
sst folder and has SST components for Ping and Pong in cpp and hpp files. ahp_graph
has an extension to DeviceGraph for SST, called SSTGraph, which allows the ahp_graph
to be built directly in SST or to generate a JSON file formatted for SST. Further
descriptions can be found in each folder.
