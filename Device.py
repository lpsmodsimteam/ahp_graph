"""
This module represents a Device which can be thought of as an SST component.

There are decorators for annotating which SST library the device can be found
in along with port labels.

The most important feature is that a Device can be an assembly, meaning is is
constructed of other Devices. This combined with the DeviceGraph allows for
hierarchical representations of a graph.
"""

import collections
import types

# The Port namespace defines constants used to describe ports.
Port = types.SimpleNamespace(
    # Port cardinality: single, multi, or bounded(N).
    Single=-1,
    Multi=0,
    Bounded=lambda x: x,
    # Whether the port is optional or required.
    Optional=False,
    Required=True
)


def sstlib(name: str) -> 'Device':
    """
    Python decorator to define the SST component associated with this Device.

    Note that a node may have an SST attribute and also
    be an assembly (e.g., a multi-resolution model of a component).
    """

    def wrapper(cls: 'Device') -> 'Device':
        cls.sstlib = name
        return cls

    return wrapper


def assembly(cls: 'Device') -> 'Device':
    """
    Python decorator to indicate that a device is an assembly.

    Verify that there is an expand method.
    """
    if not hasattr(cls, "expand"):
        raise RuntimeError(f"Assemblies must define expand(): {cls.__name__}")
    cls.assembly = True
    return cls


def port(name: str, card, ptype: str = None,
         need: bool = Port.Optional, format: str = '.#') -> 'Device':
    """
    Python decorator to define the ports for a particular device.

    A port is defined by a name, cardinality (single, multiple, or bounded),
    a port type (a string or None), and whether it is required.
    Can also have an optional format for how to handle Multi connections
    """

    def wrapper(cls: 'Device') -> 'Device':
        if not hasattr(cls, "_portinfo"):
            cls._portinfo = dict()
        cls._portinfo[name] = (card, ptype, need, format)
        return cls

    return wrapper


class DevicePort:
    """
    A DevicePort represents a port on a Device.

    DevicePort contains a device reference, a port name, and an
    optional port number.
    Optional format parameter for how to format a port number.
    This allows for ports to mimic the format of certain SST elements
    """

    def __init__(self, device: 'Device', name: str,
                 number: int = None, format: str = '.#') -> 'DevicePort':
        """
        Initialize the device, name, port number, and format.

        The DevicePort has the typical format of name.portNum
        If this doesn't work, you can specify the format to include a '#'
        to indicate where the portNum is placed after name.
        For example: format = '(#)' will result in name(portNum)
                     format = '_#'  will result in name_portNum
        """
        self.device = device
        self.name = name
        self.number = number
        self.format = format

    def is_single(self) -> bool:
        """Return whether this is a single port or not."""
        return self.number is None

    def get_name(self) -> str:
        """Return a string representation of the port name and number."""
        if self.number is None:
            return self.name
        else:
            sf = self.format.split('#')
            return f"{self.name}{sf[0]}{self.number}{sf[1]}"

    def __repr__(self) -> str:
        """Return a string representation of this DevicePort."""
        return f"{self.device.name}.{self.get_name()}"

    def __lt__(self, other: 'DevicePort') -> bool:
        """Compare this DevicePort to another."""
        n0 = -1 if self.number is None else self.number
        n1 = -1 if other.number is None else other.number
        p0 = (self.device.name, self.name, n0)
        p1 = (other.device.name, other.name, n1)
        return p0 < p1


class ExternalPort:
    """An ExternalPort object contains an sst.Component and a port name."""

    def __init__(self, comp, portName: str) -> 'ExternalPort':
        """Initialize the component and portName."""
        self.comp = comp
        self.portName = portName

    def __repr__(self) -> str:
        """Return a string representation of this ExternalPort."""
        return f"{self.comp.getFullName()}.{self.portName}"

    def comp_name(self) -> str:
        """Return the component name."""
        return self.comp.getFullName()

    def port_name(self) -> str:
        """Return the port name."""
        return self.portName


class Device:
    """
    Device is the base class for a node in the AHP graph.

    This object is immutable. Each device exports several ports.
    A device may be represented by an SST component, may be an assembly
    of other devices, or both. If an assembly, then the device must define
    an expand() method that returns a device graph that implements the device.

    Note that successive calls to port() will return the same DevicePort
    object so they can be used in sets and comparisons.

    Each device must have a unique name and model.
    """

    sstlib = None
    assembly = False

    def __init__(self, name: str, model=None, attr=None) -> 'Device':
        """
        Initialize the device.

        Initialize with the unique name, model, and optional
        dictionary of attributes.
        """
        self.name = name
        self.attr = dict(attr) if attr is not None else dict()
        self._ports = collections.defaultdict(dict)
        self._nport = collections.defaultdict(int)
        self._sub = list()
        self._issub = False
        self._subOwner = None

        self._rank = None
        self._thread = None
        self.attr["type"] = self.__class__.__name__

        if model is not None:
            self.attr["model"] = model

    def set_partition(self, rank: int, thread: int = 0) -> None:
        """Assign a rank and optional thread to this device."""
        self._rank = rank
        self._thread = thread

    def add_subcomponent(self, device: 'Device', name: str,
                         slotIndex: int = None) -> None:
        """
        Add a subcomponent to this component.

        Both the subcomponent and this component must be SST classes.
        Note that all subcomponents must be added to the device before
        the device is added to the graph.
        """
        if self.sstlib is None:
            raise RuntimeError(f"Parent of sub-component must be an SST class")
        if device.sstlib is None:
            raise RuntimeError(f"A sub-component must be an SST class")
        device._issub = True
        device._subOwner = self
        self._sub.append((device, name, slotIndex))

    def is_subcomponent(self) -> bool:
        """Return whether this component is a subcomponent."""
        return self._issub

    def get_subcomponents(self) -> list:
        """Return the list of (device,slot) sub-component pairs."""
        return self._sub

    def __getattr__(self, port: str) -> 'DevicePort':
        """
        Enable ports to be treated as variables.

        As a convenience, we allow ports to be named as an attribute on the
        class (e.g., Device.Input instead of Device.port("Input").
        If the port is not defined, then we thrown an exception.
        """
        info = self._portinfo.get(port)

        if info is None:
            raise RuntimeError(f"Unknown port in {self.name}: {port}")
        elif info[0] == Port.Single:
            return self.port(port)
        else:
            return lambda x: self.port(port, x)

    def port(self, port, number: int = None) -> 'DevicePort':
        """
        Return a Port object representing the port on this device.

        If a Single port, then make sure we do not have a port number.
        If the port has not already been defined, then add it.

        If a Bounded or Multi port, determine the port number.  If
        number is None, then create a new port at the end of the current
        list.  Make sure we do not create too many connections if Bounded.
        Finally, if the port has not already been defined, then create it.
        """
        info = self._portinfo.get(port)

        if info is None:
            raise RuntimeError(f"Unknown port in {self.name}: {port}")

        elif info[0] == Port.Single:
            if number is not None:
                raise RuntimeError(f"Port supports one connection: {port}")
            if port not in self._ports:
                self._ports[port] = DevicePort(self, port, format=info[3])
            return self._ports[port]

        else:
            if number is None:
                number = self._nport[port]
                self._nport[port] += 1
            else:
                self._nport[port] = number + 1
            if info[0] != Port.Multi and number >= info[0]:
                raise RuntimeError(f"Too many connections: {port}")
            if number not in self._ports[port]:
                self._ports[port][number] = DevicePort(self, port,
                                                       number, format=info[3])
            return self._ports[port][number]

    def reset_port_count(self) -> None:
        """Reset the port count for multiports."""
        for port in self._nport:
            self._nport[port] = 0

    def get_category(self) -> str:
        """Return the category for this Device (type, model)."""
        if 'model' in self.attr:
            return f"{self.attr['type']}_{self.attr['model']}"
        else:
            return f"{self.attr['type']}"

    def label_ports(self) -> str:
        """Return the port labels for a graphviz record style node."""
        if len(self._ports) == 0:
            return ''
        label = '{'
        for port in self._ports:
            label += f"<{port}> {port}|"
        return label[:-1] + '}'

    def __repr__(self) -> str:
        """Return a description of the Device."""
        lines = list()
        lines.append(f"Device={self.__class__.__name__}")
        lines.append(f"    name={self.name}")
        lines.append(f"    is-assembly={self.assembly}")

        if self.sstlib is not None:
            lines.append(f"    sstlib={self.sstlib}")

        for key in sorted(self.attr):
            lines.append(f"    {key}={self.attr[key]}")
        return "\n".join(lines)
