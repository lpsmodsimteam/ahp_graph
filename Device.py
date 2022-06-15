"""
This module represents a Device.

There are decorators for annotating which library the device can be found
in along with port labels.

The most important feature is that a Device can be an assembly, meaning it is
constructed of other Devices. This combined with the DeviceGraph allows for
hierarchical representations of a graph.
"""

from __future__ import annotations
from typing import Optional, Union, Callable, Any
import collections


def library(name: str) -> Callable[[Device], Device]:
    """
    Python decorator to define the library associated with this Device.

    If library is not defined, the Device is an assembly and must define
    the expand function.
    For example, this represents the SST Element Library and Component used to
    simulate the Device ('element.component')
    """

    def wrapper(cls: Device) -> Device:
        cls.library = name
        return cls
    return wrapper


def port(name: str, ptype: str = None, limit: int = 1, required: bool = True,
         format: str = '.#') -> Callable[[Device], Device]:
    """
    Python decorator to define the ports for a particular device.

    A port has a name, a port type which is used to verify connections are
    between ports of the same type, whether the port is required to be
    connected or if it is an optional connection, and a limit on the number of
    connections. If you want unlimited connections, set this to None
    Can also have an optional format for how to format port numbers
    """

    def wrapper(cls: Device) -> Device:
        if not cls.portinfo:
            cls.portinfo = dict()
        cls.portinfo[name] = (limit, ptype, required, format)
        return cls
    return wrapper


class DevicePort:
    """
    A DevicePort represents a port on a Device.

    DevicePort contains a Device reference, a port name, and an
    optional port number.
    """

    def __init__(self, device: Device, name: str,
                 number: int = None) -> None:
        """Initialize the device, name, port number."""
        self.device: Device = device
        self.name: str = name
        self.number: Optional[int] = number
        self.link: Optional[DevicePort] = None

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
    Device is the base class for a node in the AHP graph.

    A Device may be represented by an model or may be an assembly
    of other Devices. If an assembly, then the Device must define
    an expand() method that returns a DeviceGraph that implements the Device.

    Devices may contain submodules which allow for parameterization of
    functionality similar to a lambda function (ex. SST subcomponents). This
    is done by creating a Device to represent the submodule and then adding
    it into another Device.

    Note that successive calls to port() will return the same DevicePort
    object so they can be used in sets and comparisons.
    """

    library: Optional[str] = None
    portInfoType = tuple[int, Optional[str], bool, str]
    portinfo: dict[str, portInfoType] = dict()

    def __init__(self, name: str, model: str = None,
                 attr: dict[str, Any] = None) -> None:
        """
        Initialize the Device.

        Initialize with the unique name, model, and optional
        dictionary of attributes which are used as model parameters.
        """
        self.name: str = name
        self.attr: dict[str, Any] = attr if attr is not None else dict()
        portType = dict[str, dict[int, DevicePort]]
        self.ports: portType = collections.defaultdict(dict)
        self.subs: set[tuple[Device, str, Optional[int]]] = set()
        self.subOwner: Optional[Device] = None
        self.partition: Optional[tuple[int, Optional[int]]] = None
        self.type: str = self.__class__.__name__
        self.model: Optional[str] = model
        if self.library is None and not hasattr(self, "expand"):
            raise RuntimeError(f"Assemblies must define expand(): {self.type}")

    def set_partition(self, rank: int, thread: int = None) -> None:
        """Assign a rank and optional thread to this device."""
        self.partition = (rank, thread)

    def add_submodule(self, device: Device, slotName: str,
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

    def __getattr__(self, port: str) -> Union[DevicePort,
                                              Callable[[Any], DevicePort]]:
        """
        Enable ports to be treated as variables.

        As a convenience, we allow ports to be named as an attribute on the
        class (e.g., Device.Input instead of Device.port("Input").
        If the port is not defined, then we thrown an exception.
        """
        info: Optional[Device.portInfoType] = self.portinfo.get(port)
        if info is None:
            raise RuntimeError(f"Unknown port in {self.name}: {port}")

        elif info[0] == 1:
            return self.port(port)
        else:
            return lambda x: self.port(port, x)

    def port(self, port: str, number: int = None) -> DevicePort:
        """
        Return a Port object representing the port on this Device.

        If a Single port, then make sure we do not have a port number.
        If the port has not already been defined, then add it.

        If a Bounded or Multi port, determine the port number.  If
        number is None, then create a new port at the end of the current
        list.  Make sure we do not create too many connections if Bounded.
        Finally, if the port has not already been defined, then create it.
        """
        info: Optional[Device.portInfoType] = self.portinfo.get(port)
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
        lines: list[str] = list()
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
