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

    def __init__(self, timebase: str = '1ps') -> 'BuildSST':
        """Create the SST builder object. The default time base is 1ps."""
        self._TIMEBASE = timebase

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

    def build(self, graph: 'DeviceGraph', nranks: int = 1,
              partialExpand: bool = False) -> dict:
        """
        Build the SST graph.

        Return a dictionary of component names to SST component objects.
        """
        # If this is serial, generate the entire graph
        if nranks == 1:
            return self.__build_model(
                graph.attr,
                False,
                graph.devices.values(),
                graph.links.values()
            )

        # Find the partition information and build the model for this rank
        else:
            # only import sst when we are going to build the graph
            import sst
            rank = sst.getMyMPIRank()
            sst.setProgramOption("partitioner", "sst.self")

            rankGraph = graph
            if partialExpand:
                rankGraph = graph.flatten(rank=rank).follow_links(rank)
            partition = self.__partition_graph(rankGraph, nranks)

            for d0 in graph.devices.values():
                if d0.rank is None:
                    raise RuntimeError(f"No rank for component: {d0.name}")

            return self.__build_model(
                rankGraph.attr,
                True,
                partition[rank][0],
                partition[rank][1]
            )

    def __build_model(self, attr: dict, self_partition: bool,
                      rank_components: set, rank_links: list) -> dict:
        """
        Generate the model for the SST program.

        If rank is None, then we are not running in parallel.
        Otherwise only grab the components and links associated with this rank.
        """
        # only import sst when we are going to build the graph inside of sst
        import sst
        n2c = dict()

        # Set up global parameters.
        global_params = self.__encode(attr)
        for (key, val) in global_params.items():
            sst.addGlobalParam(key, key, val)

        def recurseSubcomponents(dev: 'Device', comp: 'Component'):
            for (d1, n1, s1) in dev.subs:
                if d1.sstlib is None:
                    raise RuntimeError(f"No SST library: {d1.name}")
                if s1 is None:
                    c1 = comp.setSubComponent(n1, d1.sstlib)
                else:
                    c1 = comp.setSubComponent(n1, d1.sstlib, s1)
                c1.addParams(self.__encode(d1.attr))
                n2c[d1.name] = c1
                for key in global_params:
                    c1.addGlobalParamSet(key)
                if len(d1.subs) > 0:
                    recurseSubcomponents(d1, c1)

        # First, we instantiate all of the components with
        # their attributes.  Raise an exception if a particular
        # device has no SST component implementation.
        for d0 in rank_components:
            if d0.sstlib is None:
                raise RuntimeError(f"No SST library for device: {d0.name}")

            if d0.subOwner is None:
                c0 = sst.Component(d0.name, d0.sstlib)
                c0.addParams(self.__encode(d0.attr))
                # Set the component rank if we are self-partitioning
                if self_partition:
                    c0.setRank(d0.rank, d0.thread)
                n2c[d0.name] = c0
                for key in global_params:
                    c0.addGlobalParamSet(key)
                if d0.rank is not None:
                    c0.setRank(d0.rank, d0.thread)
                recurseSubcomponents(d0, c0)

        # Second, link the component ports using graph links.
        for (p0, p1, t) in rank_links:
            c0 = n2c[p0.device.name]
            c1 = n2c[p1.device.name]
            s0 = p0.get_name()
            s1 = p1.get_name()
            link = sst.Link(f"{p0}__{t}__{p1}")
            link.connect((c0, s0, t), (c1, s1, t))

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
                graph.attr,
                filename,
                nranks,
                graph.devices.values(),
                graph.links.values(),
                program_options,
            )

        # Graph has already been expanded.  Find the partition
        # information and write out the models.
        elif not partialExpand:
            (base, ext) = os.path.splitext(filename)
            partition = self.__partition_graph(graph, nranks)

            for d0 in graph.devices.values():
                if d0.rank is None:
                    raise RuntimeError(f"No rank for component: {d0.name}")

            for rank in range(nranks):
                self.__write_model(
                    graph.attr,
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

                for d in rankGraph.devices.values():
                    if d.rank is None:
                        raise RuntimeError(f"No rank for component: {d.name}")

                self.__write_model(
                    rankGraph.attr,
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

        for (p0, p1, dt) in graph.links.values():
            d0 = p0.device
            d1 = p1.device

            while d0.subOwner is not None:
                d0 = d0.subOwner
            while d1.subOwner is not None:
                d1 = d1.subOwner

            r0 = d0.rank
            r1 = d1.rank

            partition[r0][0].add(d0)
            partition[r0][0].add(d1)
            partition[r0][1].append((p0, p1, dt))

            if r0 != r1:
                partition[r1][0].add(d0)
                partition[r1][0].add(d1)
                partition[r1][1].append((p0, p1, dt))

        return partition

    def __write_model(self, attr: dict, filename: str, nranks: int,
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
        global_params = self.__encode(attr, True)
        model["global_params"] = dict()
        for (key, val) in global_params.items():
            model["global_params"][key] = dict({key: val})
        global_set = list(global_params.keys())

        def recurseSubcomponents(dev: 'Device') -> list:
            subcomponents = list()
            for (d1, n1, s1) in dev.subs:
                if d1.sstlib is None:
                    raise RuntimeError(f"No SST library: {d1.name}")

                item = {
                        "slot_name": n1,
                        "type": d1.sstlib,
                        "slot_number": s1,
                        "params": self.__encode(d1.attr, True),
                        "params_global_sets": global_set,
                    }
                if len(d1.subs) > 0:
                    item["subcomponents"] = recurseSubcomponents(d1)
                subcomponents.append(item)
            return subcomponents

        # Define all the components.  We define the name, type,
        # parameters, and global parameters.  Raise an exception
        # if a particular device has no SST component implementation.
        components = list()
        for d0 in rank_components:
            if d0.subOwner is None:
                if d0.sstlib is None:
                    raise RuntimeError(f"No SST library for device: {d0.name}")

                component = {
                    "name": d0.name,
                    "type": d0.sstlib,
                    "params": self.__encode(d0.attr, True),
                    "params_global_sets": global_set,
                }
                if d0.rank is not None:
                    component["partition"] = {
                        "rank": d0.rank,
                        "thread": d0.thread,
                    }

                subcomponents = recurseSubcomponents(d0)
                if len(subcomponents) > 0:
                    component["subcomponents"] = subcomponents
                components.append(component)

        model["components"] = components

        # Now define the links between components.
        links = list()
        for (p0, p1, t) in rank_links:
            links.append(
                {
                    "name": f"{p0}__{t}__{p1}",
                    "left": {
                        "component": p0.device.name,
                        "port": p0.get_name(),
                        "latency": t,
                    },
                    "right": {
                        "component": p1.device.name,
                        "port": p1.get_name(),
                        "latency": t,
                    },
                }
            )

        model["links"] = links

        with io.open(filename, "wb") as jfile:
            jfile.write(orjson.dumps(model, option=orjson.OPT_INDENT_2))
