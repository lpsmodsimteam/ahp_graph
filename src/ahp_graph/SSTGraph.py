#!/usr/bin/env python3

"""
This module extends a DeviceGraph to enable SST Simulation output.
"""

import os
import orjson
import sys
from .Device import *
from .DeviceGraph import *


class SSTGraph(DeviceGraph):
    """
    SSTGraph is an extension to DeviceGraph that lets you build or
    write JSON.  SSTGraph will flatten the graph when building or
    writing JSON. You probably want to do these last since they
    modify the DeviceGraph itself
    """

    def __init__(self, graph: DeviceGraph) -> None:
        """
        Point at the DeviceGraph variables.
        """
        super().__init__()
        self.attr = graph.attr
        self.devices = graph.devices
        self.links = graph.links
        self.ports = graph.ports
        self.flattened = False

    def _flatten(self, rank : int = 0, nranks : int = 1):
        """
        Flatten the SST graph.  If running on one rank, just flatten
        and verify.  If running on multiple ranks, then flatten on this
        rank, verify links, follow links and prune.  We only flatten
        once.
        """
        if not self.flattened:
            if nranks == 1:
                self.flatten()
                self.verify_links()
            else:
                self.check_partition()
                self.flatten(rank=rank)
                self.verify_links()
                self.follow_links(rank, True)
            self.flattened = True

    def build(self, nranks: int = 1):
        """
        Build the SST graph.

        If you have an extremely large graph, it is recommended that you use
        ahp_graph to do the graph partitioning instead of letting SST do it.
        You can do this by using the Device.set_partition() function and then
        setting nranks in this function to the total number of ranks used
        """
        if nranks == 1:
            self._flatten()
            self.__build_model(False)
        else:
            import sst
            rank = sst.getMyMPIRank()
            self._flatten(rank, nranks)
            sst.setProgramOption("partitioner", "sst.self")
            self.__build_model(True)

    def write_json(self,
                   filename: str,
                   output: str = "output",
                   nranks: int = 1,
                   rank: int = 0,
                   program_options: dict = None):
        """
        Generate the JSON and write it to the specified filename.

        All JSON output will be stored in the specified output folder.
        The program_options dictionary provides a way to pass SST program
        options, such as timebase and stopAtCycle.

        If the number of ranks is one, then we will output the entire graph
        to the single JSON file.  If the number of ranks is greater than one,
        then we partition the graph by rank and only output the portion of
        the graph with the specified rank.

        If you have an extremely large graph, it is recommended that you use
        ahp_graph to do the graph partitioning instead of letting SST do it.
        You can do this by using the Device.set_partition() function and then
        setting nranks in this function to the total number of ranks used
        """
        if not os.path.exists(output):
            os.makedirs(output)

        self._flatten(rank, nranks)
        if nranks == 1:
            self.__write_model(
                f"{output}/{filename}",
                nranks,
                program_options)
        else:
            (base, ext) = os.path.splitext(f"{output}/{filename}")
            self.__write_model(
                base + str(rank) + ext,
                nranks,
                program_options)

    @staticmethod
    def __encode(attr: dict, stringify: bool = False) -> dict:
        """
        Convert attributes into SST Params.

        SST only supports primitive types (bool, int, float) and lists of those
        types as parameters; everything else we will convert via JSON.
        If the attribute contains a __to_json__ method, then we will call it.
        Ignore bad conversions.
        """

        def supported_f(x) -> bool:
            """Return whether the type is supported by SST."""
            return isinstance(x, (bool, float, int, str))

        params = dict()
        for (key, val) in attr.items():
            if val is None:
                params[key] = "" if stringify else None
            else:
                native = supported_f(val)
                if not native and isinstance(val, list):
                    native = all(map(supported_f, val))

                if native:
                    params[key] = val if not stringify else str(val)
                elif hasattr(val, "__to_json__"):
                    params[key] = val.__to_json__()
                else:
                    try:
                        # serialize the value to json bytes,
                        # then deserialize into a python dict
                        params[key] = orjson.loads(
                            orjson.dumps(val, option=orjson.OPT_INDENT_2)
                        )
                    except Exception:
                        pass

        return params

    def __build_model(self, self_partition: bool) -> dict:
        """
        Generate the model for the SST program.
        """
        import sst
        n2c = dict()

        # Set up global parameters.
        global_params = self.__encode(self.attr)
        for (key, val) in global_params.items():
            sst.addGlobalParam(key, key, val)

        rank = sst.getMyMPIRank()
        def recurseSubcomponents(dev: Device, comp: 'sst.Component') -> None:
            """Add subcomponents to the Device."""
            if not dev.subs:
                return
            for (d1, n1, s1) in dev.subs:
                if d1.library is None:
                    raise RuntimeError(f"No SST library: {d1.name}")
                if s1 is None:
                    c1 = comp.setSubComponent(n1, d1.library)
                else:
                    c1 = comp.setSubComponent(n1, d1.library, s1)
                d1.attr.update(type=d1.type, model=d1.model)
                c1.addParams(self.__encode(d1.attr))
                n2c[d1.name] = c1
                for key in global_params:
                    c1.addGlobalParamSet(key)
                if d1.subs:
                    recurseSubcomponents(d1, c1)

        # First, we instantiate all of the components with
        # their attributes. Ignore Devices that have no library defined
        for d0 in self.devices.values():
            if d0.subOwner is None and d0.library is not None:
                c0 = sst.Component(d0.name, d0.library)
                d0.attr.update(type=d0.type, model=d0.model)
                c0.addParams(self.__encode(d0.attr))
                # Set the component partition if we are self-partitioning
                if self_partition:
                    thread = (0 if d0.partition[1] is None
                              else d0.partition[1])
                    c0.setRank(d0.partition[0], thread)
                n2c[d0.name] = c0
                for key in global_params:
                    c0.addGlobalParamSet(key)
                recurseSubcomponents(d0, c0)

        # Second, link the component ports using graph links
        for ((p0,p1),t) in self.links.items():
            if p0.device.library is not None \
                    and p1.device.library is not None:
                c0 = n2c[p0.device.name]
                c1 = n2c[p1.device.name]
                s0 = p0.get_name()
                s1 = p1.get_name()
                if str(p0) < str(p1):
                    link = sst.Link(f'{p0}__{t}__{p1}')
                else:
                    link = sst.Link(f'{p1}__{t}__{p0}')
                latency = t if t != '0s' else '1ps'
                link.connect((c0, s0, latency), (c1, s1, latency))

    def __write_model(self,
                      filename: str,
                      nranks: int,
                      program_options: dict = None) -> None:
        """
        Write this DeviceGraph out as JSON.
        """
        model = dict()

        #
        # Write the program options to the model.
        #
        if program_options is None:
            model["program_options"] = dict()
        else:
            model["program_options"] = dict(program_options)

        #
        # If running in parallel, then set up the SST SELF partitioner.
        #
        if nranks > 1:
            model["program_options"]["partitioner"] = "sst.self"

        #
        # Set up global parameters.
        #
        global_params = self.__encode(self.attr, True)
        model["global_params"] = dict()
        for (key, val) in global_params.items():
            model["global_params"][key] = dict({key: val})
        global_set = list(global_params.keys())

        def recurseSubcomponents(dev: Device) -> list:
            """Add subcomponents to the Device."""
            subcomponents = list()
            if not dev.subs:
                return subcomponents
            for (d1, n1, s1) in dev.subs:
                if d1.library is None:
                    raise RuntimeError(f"No library: {d1.name}")
                
                d1.attr.update(type=d1.type, model=d1.model)
                item = {
                    "slot_name" : n1,
                    "type" : d1.library,
                    "slot_number" : s1,
                    "params" : self.__encode(d1.attr, True),
                    "params_global_sets" : global_set,
                }
                if d1.subs:
                    item["subcomponents"] = recurseSubcomponents(d1)
                subcomponents.append(item)
            return subcomponents

        #
        # Define all the components. We define the name, type, parameters,
        # and global parameters. Ignore Devices that have no library defined
        #
        components = list()
        for d0 in self.devices.values():
            if d0.subOwner is None and d0.library is not None:
                d0.attr.update(type=d0.type, model=d0.model)
                component = {
                    "name" : d0.name,
                    "type" : d0.library,
                    "params" : self.__encode(d0.attr, True),
                    "params_global_sets" : global_set,
                }
                if d0.partition is not None:
                    component["partition"] = {
                        "rank": d0.partition[0],
                        "thread": (0 if d0.partition[1] is None
                                   else d0.partition[1]),
                    }

                subcomponents = recurseSubcomponents(d0)
                if len(subcomponents) > 0:
                    component["subcomponents"] = subcomponents
                components.append(component)

        model["components"] = components

        #
        # Now define the links between components.
        #
        links = list()
        for ((p0,p1),t) in self.links.items():
            #assert p0.device.library is not None
            #assert p1.device.library is not None
            if p0.device.library is None:
                raise RuntimeError(f"No SST library: {p0.device.name}")
            if p1.device.library is None:
                raise RuntimeError(f"No SST library: {p1.device.name}")

            latency = t if t != '0s' else '1ps'
            if str(p0) < str(p1):
                name = f'{p0}__{t}__{p1}'
            else:
                name = f'{p1}__{t}__{p0}'
            links.append({
                "name" : name,
                "left" : {
                    "component" : p0.device.name,
                    "port" : p0.get_name(),
                    "latency" : latency
                },
                "right" : {
                    "component" : p1.device.name,
                    "port" : p1.get_name(),
                    "latency" : latency
                },
            })

        model["links"] = links

        #
        # Write the output JSON file
        #
        with open(filename, "wb") as jfile:
            jfile.write(orjson.dumps(model, option=orjson.OPT_INDENT_2))
