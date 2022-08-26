#!/usr/bin/env python3

"""
This module represents a Device.

There are decorators for annotating which library the device can be found
in along with port labels.

The most important feature is that a Device can be an assembly, meaning it is
constructed of other Devices. This combined with the DeviceGraph allows for
hierarchical representations of a graph.
"""

import collections


class PortInfo(dict):
    """
    PortInfo is a dictionary describing what ports a Device can have.

    PortInfo contains information such as port type, limit on the number of
    connections, whether the port is required, and formatting info.
    PortInfo is a class variable which defines the available ports for all
    instances of a specific Device. DevicePort represents an actual instance of
    a port on a Device.
    """

    def add(self, name: str, ptype: str = None, limit: int = 1,
            required: bool = True, format: str = '.p#') -> None:
        """Add a port definition to the dictionary."""
        self[name] = (limit, ptype, required, format)


class DevicePort:
    """
    A DevicePort represents an instance of a port on a Device.

    DevicePort contains a Device reference, a port name, and an
    optional port number.
    It can also reference the other DevicePort that it is linked to.
    """

    def __init__(self, device: 'Device', name: str,
                 number: int = None) -> None:
        """Initialize the device, name, port number."""
        self.device = device
        self.name = name
        self.number = number
        self.link = None

    def get_name(self) -> str:
        """Return a string representation of the port name and number."""
        if self.number is None:
            return self.name
        else:
            sf = self.device.portinfo[self.name][3].split('#')
            return f"{self.name}{sf[0]}{self.number}{sf[1]}"

    def __repr__(self) -> str:
        """Return a string representation of this DevicePort."""
        return f"{self.device.name}.{self.get_name()}"


class Device:
    """
    Device is the base class for a node in a DeviceGraph.

    A Device may be represented by an model or may be an assembly
    of other Devices. If an assembly, then the Device must define
    an expand() method that returns a DeviceGraph that implements the Device.

    Devices may contain submodules which allow for parameterization of
    functionality similar to a lambda function (ex. SST subcomponents). This
    is done by creating a Device to represent the submodule and then adding
    it into another Device.

    The variables library and portinfo are class variables that can be set on
    the definition of a new Device class. The variable attr is a dictionary of
    attributes that can be used as both a class variable and an instance
    variable. Attributes that are common among all instances of a Device can
    be set in the definition of that Device and instance attributes can be
    added to the class attributes on specific instances of the Device.
    """

    library = None
    portinfo = PortInfo()
    attr = dict()

    def __init__(self, name: str, model: str = None,
                 attr: dict = None) -> None:
        """
        Initialize the Device.

        Initialize with the unique name, model, and optional
        dictionary of attributes which are used as model parameters.
        """
        self.name = name
        if self.attr:
            if attr is not None:
                self.attr = {**self.attr, **attr}
        elif attr is not None:
            self.attr = attr
        self.ports = collections.defaultdict(dict)
        self.subs = set()
        self.subOwner = None
        self.partition = None
        self.type = self.__class__.__name__
        self.model = model
        if self.library is None and not hasattr(self, "expand"):
            raise RuntimeError(f"Assemblies must define expand(): {self.type}")

    def set_partition(self, rank: int, thread: int = None) -> None:
        """Assign a rank and optional thread to this device."""
        self.partition = (rank, thread)

    def add_submodule(self, device: 'Device', slotName: str,
                      slotIndex: int = None) -> None:
        """
        Add a submodule to this Device.

        Both the submodule and this Device must have libraries.
        Note that all submodules must be added to the Device before
        the Device is added to a DeviceGraph.
        """
        if self.library is None or device.library is None:
            raise RuntimeError(f"Submodule and parent must have libraries:"
                               f" {device.name}, {self.name}")
        device.subOwner = self
        self.subs.add((device, slotName, slotIndex))

    def __getattr__(self, port: str) -> 'DevicePort':
        """
        Enable ports to be treated as variables.

        As a convenience, we allow ports to be named as an attribute on the
        class (e.g., Device.Input instead of Device.port("Input").
        If the port is not defined, then we thrown an exception.
        """
        info = self.portinfo.get(port)
        if info is None:
            raise RuntimeError(f"Unknown port in {self.name}: {port}")

        elif info[0] == 1:
            return self.port(port)
        else:
            return lambda x: self.port(port, x)

    def port(self, port: str, number: int = None) -> 'DevicePort':
        """
        Return a DevicePort object representing the port on this Device.

        If a Single port, then make sure we do not have a port number.
        If the port has not already been defined, then add it.

        If a limited or multi port, determine the port number.  If
        number is None, then create a new port at the end of the current
        list.  Make sure we do not create too many connections if limited.
        Finally, if the port has not already been defined, then create it.
        """
        info = self.portinfo.get(port)
        if info is None:
            raise RuntimeError(f"Unknown port in {self.name}: {port}")

        elif info[0] == 1:
            # Single Port, don't use port numbers
            if number is not None:
                print(f"WARNING! Single port ({port}) being provided a port"
                      f" number ({number})")
            if port not in self.ports:
                self.ports[port][-1] = DevicePort(self, port)
            return self.ports[port][-1]

        else:
            # Multi Port, use port numbers and check the provided limit
            if number is None:
                number = len(self.ports[port])
            if info[0] is not None:
                if number >= info[0]:
                    raise RuntimeError(f"Too many connections ({number}):"
                                       f" {port} (limit {info[0]})")
            if number not in self.ports[port]:
                self.ports[port][number] = DevicePort(self, port, number)
            return self.ports[port][number]

    def get_category(self) -> str:
        """Return the category for this Device (type, model)."""
        if self.model is not None:
            return f"{self.type}_{self.model}"
        return self.type

    def label_ports(self) -> str:
        """Return the port labels for a graphviz record style node."""
        if len(self.ports) == 0:
            return ''
        label = '{'
        for port in self.ports:
            label += f"<{port}> {port}|"
        return label[:-1] + '}'

    def __repr__(self) -> str:
        """Return a description of the Device."""
        lines = list()
        lines.append(f"Device = {self.type}")
        lines.append(f"\tname = {self.name}")
        if self.model:
            lines.append(f"\tmodel = {self.model}")
        if self.library:
            lines.append(f"\tlibrary = {self.library}")
        else:
            lines.append(f"\tassembly = True")
        if self.partition:
            lines.append(f"\tpartition = {self.partition}")
        if self.subOwner is not None:
            lines.append(f"\tsubmoduleParent = {self.subOwner.name}")

        if self.portinfo:
            lines.append(f"\tPorts:")
            for port in sorted(self.portinfo):
                lines.append(f"\t\t{port} = {self.portinfo[port]}")
        if self.attr:
            lines.append(f"\tAttributes:")
            for key in sorted(self.attr):
                lines.append(f"\t\t{key} = {self.attr[key]}")
        if self.subs:
            lines.append(f"\tSubmodules:")
            for sub in sorted(self.subs, key=lambda x: (x[1], x[2])):
                lines.append(f"\t\t{sub[1]}:{sub[2]} -> {sub[0].name}")

        return "\n".join(lines)
