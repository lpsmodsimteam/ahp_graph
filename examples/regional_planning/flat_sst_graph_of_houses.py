#!/usr/bin/env python3
import sst

link_delay = "1ns"  # has to be non-zero to enable ordering of events
clock = "1GHz"      # Simulation clock rate
clockTicks = "2"    # Number of clock ticks before the simulation ends
debug = "2"         # debug level
                    # 0 = FATAL, 1 = WARN, 2 = INFO, 3 = DEBUG, 4 = TRACE, 5 = ALL


house0 = sst.Component("house_0", "house.HouseComponent")
house0.addParams({"clock": clock, "clockTicks": clockTicks, "debug": debug})

house1 = sst.Component("house_1", "house.HouseComponent")
house0.addParams({"clock": clock, "clockTicks": clockTicks, "debug": debug})

house2 = sst.Component("house_2", "house.HouseComponent")
house0.addParams({"clock": clock, "clockTicks": clockTicks, "debug": debug})

sst.Link("link_house1_to_house0").connect((house0, "port_b", link_delay),
                                         (house1, "port_b", link_delay))

sst.Link("link_house1_to_house2").connect((house2, "port_a", link_delay),
                                         (house1, "port_a", link_delay))
