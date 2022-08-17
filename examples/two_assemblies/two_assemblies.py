#!/usr/bin/env python3

# Create two assemblies and connect them together via intermediary devices

from ahp_graph.Device import *
from ahp_graph.DeviceGraph import *
from ahp_graph.SSTGraph import *

NDEVC=2    # Number of Device C's
NLINKS=10  # Number of links

#  ----------------------------------
# |            Assembly              | 
# |   __________      __________     |     __________
# |  |          |----|          |    |    |          |
# |  | Device A |----| Device B |----|----| Device C |---- ...
# |  |__________|----|__________|    |    |__________|
# |          \ \ \    __________     |     __________
# |           \ \ \__|          |    |    |          |
# |            \ \___| Device B |----|----| Device C |---- ...
# |             \____|__________|    |    |__________|
# |__________________________________|

class DeviceA(Device):
    library = 'none.DeviceAComponent'
    portinfo = PortInfo()
    portinfo.add('a2b_inout', 'String', limit=NLINKS*NDEVC)

class DeviceB(Device):
    library = 'none.DeviceBComponent'
    portinfo = PortInfo()
    portinfo.add('a2b_inout', 'String', limit=NLINKS)
    portinfo.add('b2c_inout', 'String')

class DeviceC(Device):
    library = 'none.DeviceCComponent'
    portinfo = PortInfo()
    portinfo.add('b2c_inout', 'String', limit=2*NDEVC)

class Assembly(Device):
    portinfo = PortInfo()
    portinfo.add('b2c_inout', 'String', limit=NDEVC)
    
    def expand(self, graph: DeviceGraph) -> None:
        deva = DeviceA('DEVA')
        devb = dict()
        for i in range(NDEVC):
            devb[i] = DeviceB(f'DEVB{i}')
            # Just to demonstrate the issue of duplicate links getting split,
            # we will add more links.            
            for j in range(NLINKS):
                graph.link(deva.a2b_inout(i*NLINKS + j), devb[i].a2b_inout(j))
            graph.link(self.b2c_inout(i), devb[i].b2c_inout)
        
def architecture() -> DeviceGraph:
    graph = DeviceGraph()    
    assemblies = [Assembly(f'Assembly{i}') for i in range(2)]

    for dev in range(NDEVC):
        devc = DeviceC(f'DEVC{dev}')
        for i in range(2):
            graph.link(assemblies[i].b2c_inout(dev), devc.b2c_inout(i))

    return graph

if __name__ == "__main__":
    try:
        import sst
        SST = True
    except ImportError:
        SST = False

    # Construct a DeviceGraph with the specified architecture
    graph = architecture()

    if SST:
        sstgraph = SSTGraph(graph)
        sstgraph.build()

    else:
        graph.write_dot('reproducer', draw=True, ports=True, hierarchy=True)
