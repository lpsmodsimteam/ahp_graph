#!/usr/bin/env python3

from ahp_graph.Device import *
from ahp_graph.DeviceGraph import *

class House(Device):
    """
	driveway0     +-------+    driveway1
        	------+ house +-----
	              +-------+

    https://asciiflow.com/
    """
    library = 'house.HouseComponent'  # this is set in the respective .hpp file using SST_ELI_REGISTER_COMPONENT
    portinfo = PortInfo()
    portinfo.add('driveway0', 'String') # this corresponds to SST_ELI_DOCUMENT_PORTS in .hpp and configureLink in .cpp 
    portinfo.add('driveway1', 'String') # this corresponds to SST_ELI_DOCUMENT_PORTS in .hpp and configureLink in .cpp

class neighborhood(Device):
    """
	road0      +--------------+      road1
	  ---------+ neighborhood +---------
	           +--------------+
    """
    library = 'neighborhood.NeighborhoodComponent' # this is set in the respective .h file using SST_ELI_REGISTER_COMPONENT
    portinfo = PortInfo()
    portinfo.add('road0', 'String')
    portinfo.add('road1', 'String')

    def expand(self, graph: DeviceGraph) -> None:
        """
        Expand the overall architecture into its components.

	+--------------------------------------------------------------------------------------------+
	|                     driveway0      +--------+    driveway1                                 |   road0
	|                              +-----+ house0 +----------------------------------------------+------------
	|                              |     +--------+                                              |
	|                              |                                                             |
	|                              |                                                             |
	|    driveway0     +--------+  | driveway1            driveway0     +--------+    driveway1  |    road1
	|         +--------+ house1 +--+                 +------------------+ house2 +---------------+-----------
	|         |        +--------+                    |                  +--------+               |
	|         +--------------------------------------+                                           |
	+--------------------------------------------------------------------------------------------+

        """
        # Device names created by an assembly will automatically have the
        # assembly name prefixed to the name provided.
        house_0 = House('house0', self.model)
        house_1 = House('house1')
        house_2 = House('house2')

        # link houses, automatically adds the devices to the graph
        graph.link(house_0.driveway0, house_1.driveway1, '1s')
        graph.link(house_1.driveway0, house_2.driveway0, '1s')

        # Generally you don't want to put latency on the links to assembly
        # ports (ex: self.port) and allow whatever uses the assembly to
        # specify latency for the connection (it will get ignored anyway)
        graph.link(house_0.driveway1, self.input)
        graph.link(house_2.driveway1, self.output)

class city(Device):
    """
        highway0     +------+    highway1
               ------+ city +-----
                     +------+

    https://asciiflow.com/
    """
    library = 'city.CityComponent' # this is set in the respective .h file using SST_ELI_REGISTER_COMPONENT
    portinfo = PortInfo()
    portinfo.add('highway0', 'String')
    portinfo.add('highway1', 'String')

    def expand(self, graph: DeviceGraph) -> None:
        """
        Expand the overall architecture into its components.

        +----------------------------------------------------------------------------------------------------+
        |                          road0      +---------------+    road1                                     |   highway0
        |                               +-----+ neighborhood0 +----------------------------------------------+------------
        |                               |     +---------------+                                              |
        |                               |                                                                    |
        |                               |                                                                    |
        |   road0    +---------------+  | road1                    road0     +---------------+    road1      |   highway1
        |     +------+ neighborhood1 +--+                 +------------------+ neighborhood2 +---------------+-----------
        |     |      +---------------+                    |                  +---------------+               |
        |     +-------------------------------------------+                                                  |
        +----------------------------------------------------------------------------------------------------+

        """
        # Device names created by an assembly will automatically have the
        # assembly name prefixed to the name provided.
        neighborhood_0 = neighbhorhood('n0', self.model)
        neighborhood_0 = neighbhorhood('n1')
        neighborhood_0 = neighbhorhood('n2')

        # link houses, automatically adds the devices to the graph
        graph.link(neighborhood_0.road0, neighborhood_1.road1, '1s')
        graph.link(neighborhood_1.road0, neighborhood_2.road0, '1s')

        # Generally you don't want to put latency on the links to assembly
        # ports (ex: self.port) and allow whatever uses the assembly to
        # specify latency for the connection (it will get ignored anyway)
        graph.link(neighborhood_0.road1, self.input)
        graph.link(neighborhood_2.road1, self.output)

def regional_plan(number_of_neighborhoods: int = 2) -> DeviceGraph:
    graph = DeviceGraph()
    neighborhoods_dict = dict()

    for index in range(number_of_neighborhoods):
        neighborhoods_dict[index] = neighborhood(f"neighboooorhood{index}", str(index))
        neighborhoods_dict[index].set_partition(index)

    for index in range(number_of_neighborhoods):
        graph.link(neighborhoods_dict[index].road0, neighborhoods_dict[(index+1) % number_of_neighborhoods].road1, '2s')

    return graph
