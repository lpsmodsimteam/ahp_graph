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
something like: `PingPong#.Ping:`. The number after PingPong represents which
instance of the PingPong assembly the device is coming from. You can then see
where messages are sent from and where they are received.


```bash
$ make test
python3 pingpong.py
PingPong0.Ping: Sending Ping
PingPong0.Pong: Received PingPong0.Ping: Ping
PingPong0.Pong: Sending Pong
PingPong1.Ping: Received PingPong0.Pong: Pong
PingPong1.Ping: Sending Ping
PingPong1.Pong: Received PingPong1.Ping: Ping
PingPong1.Pong: Sending Pong
```
Help is available
```bash
$ python3 pingpong.py -h
usage: pingpong.py [-h] [--num NUM] [--repeats REPEATS]

PingPong

optional arguments:
  -h, --help         show this help message and exit
  --num NUM          how many pingpongs to include
  --repeats REPEATS  how many message volleys to run
```
Using the command-line arguments,
```bash
$ python3 pingpong.py --num 3 --repeats 2
PingPong1.Ping: Sending Ping
PingPong1.Pong: Received PingPong1.Ping: Ping
PingPong1.Pong: Sending Pong
PingPong2.Ping: Received PingPong1.Pong: Pong
PingPong2.Ping: Sending Ping
PingPong2.Pong: Received PingPong2.Ping: Ping
PingPong2.Pong: Sending Pong
PingPong0.Ping: Received PingPong2.Pong: Pong
PingPong0.Ping: Sending Ping
PingPong0.Pong: Received PingPong0.Ping: Ping
PingPong0.Pong: Sending Pong
PingPong1.Ping: Received PingPong0.Pong: Pong
PingPong1.Ping: Sending Ping
PingPong1.Pong: Received PingPong1.Ping: Ping
PingPong1.Pong: Sending Pong
PingPong2.Ping: Received PingPong1.Pong: Pong
```

When the command `python3 pingpong.py --num 2 --repeats 2` is run, there is an image produced: `output/pingpong.svg`. 
That SVG contains two nodes: `PingPong0` and `PingPong1`. If you've opened the SVG using Firefox, the nodes are hyperlinked so that you can click on them. Each `PingPong` is an assembly that is expended to components with ports and links that are internal to the assembly.
