"""
This module creates an SST graph from the device graph.

We can do it live (build) or write a JSON file (write).
"""

import io
import os
import gc
import orjson


class BuildSST(object):
    """
    The BuildSST class builds an SST component graph from a device graph.

    We can build a live graph (build) or write a JSON file (write).
    """

    def __init__(self) -> 'BuildSST':
        """Create the SST builder object. The default time base is 1ps."""
        self._TIMEBASE = "1ps"

    def __encode(self, attr, stringify: bool = False) -> dict:
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

    def build(self, graph: 'DeviceGraph') -> dict:
        """
        Build the SST graph.

        Return a dictionary of component names to SST component objects.
        Sorting devices and links is optional, but when debugging,
        it assures deterministic ordering from run to run.
        """
        # only import sst when we are going to build the graph inside of sst
        import sst

        components = dict()
        n2c = dict()
        deterministic = False  # Enable this for deterministic ordering.

        # Set up global parameters.
        global_params = self.__encode(graph.attr)
        for (key, val) in global_params.items():
            sst.addGlobalParam(key, key, val)

        # If we have specified partition information, then
        # set up the self partitioner.
        if any([d0._rank is not None for d0 in graph.devices()]):
            sst.setProgramOption("partitioner", "sst.self")

        # First, we instantiate all of the components with
        # their attributes.  Raise an exception if a particular
        # device has no SST component implementation.
        graphDevices = graph.devices()
        if deterministic:
            graphDevices = sorted(graphDevices, key=lambda d: d.name)
        for d0 in graphDevices:
            if d0.sstlib is None:
                raise RuntimeError(f"No SST library for device: {d0.name}")

            if not d0.is_subcomponent():
                c0 = sst.Component(d0.name, d0.sstlib)
                c0.addParams(self.__encode(d0.attr))
                components[d0] = c0
                n2c[d0.name] = c0
                for key in global_params:
                    c0.addGlobalParamSet(key)
                if d0._rank is not None:
                    c0.setRank(d0._rank, d0._thread)

                for (d1, n1, s1) in d0.get_subcomponents():
                    if d1.sstlib is None:
                        raise RuntimeError(f"No SST library: {d1.name}")
                    if s1 is None:
                        c1 = c0.setSubComponent(n1, d1.sstlib)
                    else:
                        c1 = c0.setSubComponent(n1, d1.sstlib, s1)
                    c1.addParams(self.__encode(d1.attr))
                    components[d1] = c1
                    n2c[d1.name] = c1
                    for key in global_params:
                        c1.addGlobalParamSet(key)

        # Second, link the component ports using graph links.
        graphLinks = graph.links()
        if deterministic:
            graphLinks = sorted(graphLinks)
        for (p0, p1, t) in graphLinks:
            dt = max(t, 1)
            c0 = components[p0.device]
            c1 = components[p1.device]
            s0 = p0.get_name()
            s1 = p1.get_name()
            link = sst.Link(f"{p0}__{dt}__{p1}")
            n0 = (c0, s0, f"{dt}ps")
            n1 = (c1, s1, f"{dt}ps")
            link.connect(n0, n1)

        for (p0, p1) in graph.ext_links():
            dt = 1
            c0 = components[p0.device]
            s0 = p0.get_name()
            c1 = p1.comp
            s1 = p1.portName
            link = sst.Link(f"{p0}__{dt}__{p1}")
            n0 = (c0, s0, self._TIMEBASE)
            n1 = (c1, s1, self._TIMEBASE)
            link.connect(n0, n1)

        # Return a map of component names to components.
        return n2c

    def write(self, graph: 'DeviceGraph', filename: str, nranks: int = 1,
              program_options: dict = None,
              partialExpand: bool = False) -> None:
        """
        Generate the JSON and write it to the specified filename.

        The program_options dictionary provides a way to pass SST
        prograph options, such as stopAtCycle.
        If partialExpand is set to True, then the graph will be flattened per
        rank and links followed across ranks but the entire graph will not
        necessarily be expanded all at once
        """
        # If this is serial, just dump the whold thing.
        if nranks == 1:
            self.__write_model(
                graph,
                filename,
                nranks,
                graph.devices(),
                graph.links(),
                program_options,
            )

        # Graph has already been expanded.  Find the partition
        # information and write out the models.
        elif not partialExpand:
            (base, ext) = os.path.splitext(filename)
            partition = self.__partition_graph(graph, nranks)

            for d0 in graph.devices():
                if d0._rank is None:
                    raise RuntimeError(f"No rank for component: {d0.name}")

            for rank in range(nranks):
                self.__write_model(
                    graph,
                    base + str(rank) + ext,
                    nranks,
                    partition[rank][0],
                    partition[rank][1],
                    program_options,
                )

        # Perform a partial expansion.
        else:
            (base, ext) = os.path.splitext(filename)

            for rank in range(nranks):
                rankGraph = graph.flatten(rank=rank).follow_links(rank)
                partition = self.__partition_graph(rankGraph, nranks)

                for d in rankGraph.devices():
                    if d._rank is None:
                        raise RuntimeError(f"No rank for component: {d.name}")

                self.__write_model(
                    rankGraph,
                    base + str(rank) + ext,
                    nranks,
                    partition[rank][0],
                    partition[rank][1],
                    program_options,
                )

                # Manually remove each graph to make sure we don't overflow
                del rankGraph
                del partition
                gc.collect()

    def __partition_graph(self, graph: 'DeviceGraph', nranks: int) -> list:
        """
        Partition the graph based on ranks.

        Return a list of pairs of the form (component-set, link-list),
        where each list entry corresponds to a particular processor rank.
        It is faster to partition the graph once rather than search it
        O(p) times.
        """
        partition = [(set(), list()) for p in range(nranks)]

        for (p0, p1, dt) in graph.links():
            d0 = p0.device
            d1 = p1.device

            if d0.is_subcomponent():
                d0 = d0._subOwner
            if d1.is_subcomponent():
                d1 = d1._subOwner

            r0 = d0._rank
            r1 = d1._rank

            partition[r0][0].add(d0)
            partition[r0][0].add(d1)
            partition[r0][1].append((p0, p1, dt))

            if r0 != r1:
                partition[r1][0].add(d0)
                partition[r1][0].add(d1)
                partition[r1][1].append((p0, p1, dt))

        return partition

    def __write_model(self, graph: 'DeviceGraph', filename: str, nranks: int,
                      rank_components: set, rank_links: list,
                      program_options: dict) -> None:
        """
        Generate the model for the SST program.

        If rank is None, then we are not running in parallel.
        Otherwise only grab the components and links associated with this rank.
        """
        model = dict()

        # Write the program options to the model.
        if program_options is None:
            model["program_options"] = dict()
        else:
            model["program_options"] = dict(program_options)

        # If running in parallel, then set up the SST SELF partitioner.
        if nranks > 1:
            model["program_options"]["partitioner"] = "sst.self"

        # Set up global parameters.
        global_params = self.__encode(graph.attr, True)
        model["global_params"] = dict()
        for (key, val) in global_params.items():
            model["global_params"][key] = dict({key: val})
        global_set = list(global_params.keys())

        # Define all the components.  We define the name, type,
        # parameters, and global parameters.  Raise an exception
        # if a particular device has no SST component implementation.
        components = list()
        for d0 in rank_components:
            if d0.sstlib is None:
                raise RuntimeError(f"No SST library for device: {d0.name}")

            component = {
                "name": d0.name,
                "type": d0.sstlib,
                "params": self.__encode(d0.attr, True),
                "params_global_sets": global_set,
            }
            if d0._rank is not None:
                component["partition"] = {
                    "rank": d0._rank,
                    "thread": d0._thread,
                }

            subcomponents = list()
            for (d1, n1, s1) in d0.get_subcomponents():
                if d1.sstlib is None:
                    raise RuntimeError(f"No SST library: {d1.name}")

                subcomponents.append(
                    {
                        "slot_name": n1,
                        "type": d1.sstlib,
                        "slot_number": s1,
                        "params": self.__encode(d1.attr, True),
                        "params_global_sets": global_set,
                    }
                )

            if len(subcomponents) > 0:
                component["subcomponents"] = subcomponents
            components.append(component)

        model["components"] = components

        # Now define the links between components.
        links = list()
        for (p0, p1, dt) in rank_links:
            dt = max(dt, 1)
            links.append(
                {
                    "name": f"{p0}__{dt}__{p1}",
                    "left": {
                        "component": p0.device.name,
                        "port": p0.get_name(),
                        "latency": f"{dt}ps",
                    },
                    "right": {
                        "component": p1.device.name,
                        "port": p1.get_name(),
                        "latency": f"{dt}ps",
                    },
                }
            )

        model["links"] = links

        with io.open(filename, "wb") as jfile:
            jfile.write(orjson.dumps(model, option=orjson.OPT_INDENT_2))
