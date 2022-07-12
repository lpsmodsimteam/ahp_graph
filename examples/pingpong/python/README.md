This is the python 'simulation' implementation of the pingpong architecture.

This is intended to be a simple demonstration, and not a suggested method for
simulation. If you look at pingpong.py in this folder, you will see two classes
at the top called Ping and Pong. These classes are the implementation of our
architecture described up a folder. The idea here is that Ping and Pong both have
an input 'handler' function and an output variable that points to a function. In
the most basic case with one pingpong, you would have the output of Ping connect
to the input of Pong, and the output of Pong connect to the input of Ping. To do
this with our python classes, we simply use a lambda function so that we can pass
strings to the input 'handler' when we reference the correct output function. Since
this is not a standard simulation method ahp_graph does not support this and we need
to build the graph manually in the buildPython function. Another catch with this
'simulation' is that we are in python and are single threaded, so not all of the
devices are 'running' and we are just chaining function calls.

When you look at the output of pingpong, each line of output will start with
something like: 'PingPong#.Ping:'. The number after PingPong represents which
instance of the PingPong assembly the device is coming from. You can then see
where messages are sent from and where they are received.
