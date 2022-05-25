"""
This module represents a Device.

There are decorators for annotating which library the device can be found
in along with port labels.

The most important feature is that a Device can be an assembly, meaning is is
constructed of other Devices. This combined with the DeviceGraph allows for
hierarchical representations of a graph.
"""

import collections


def library(name: str) -> 'Device':
    """
    Python decorator to define library associated with this Device.

    For example, this represents the SST Element Library and Component used to
    simulate the device ('element.component')
    Note that a device may have a model library defined and also
    be an assembly (e.g., a multi-resolution model).
    """

    def wrapper(cls: 'Device') -> 'Device':
        cls.library = name
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


def port(name: str, ptype: str = None, limit: int = 1,
         required: bool = True, format: str = '.#') -> 'Device':
    """
    Python decorator to define the ports for a particular device.

    A port has a name, a port type which is used to verify connections are
    between ports of the same type, whether the port is required to be
    connected or if it is an optional connection, and a limit on the number of
    connections. If you want unlimited connections, set this to None
    Can also have an optional format for how to format port numbers
    """

    def wrapper(cls: 'Device') -> 'Device':
        if cls._portinfo is None:
            cls._portinfo = collections.defaultdict(dict)
        cls._portinfo[name] = {
            'limit': limit,
            'type': ptype,
            'required': required,
            'format': format
        }
        return cls
    return wrapper


class DevicePort:
    """
    A DevicePort represents a port on a Device.

    DevicePort contains a device reference, a port name, and an
    optional port number.
    """

    def __init__(self, device: 'Device', name: str,
                 number: int = None) -> 'DevicePort':
        """Initialize the device, name, port number."""
        self.device = device
        self.name = name
        self.number = number

    def get_name(self) -> str:
        """Return a string representation of the port name and number."""
        if self.number is None:
            return self.name
        else:
            sf = self.device.get_portinfo()[self.name]['format'].split('#')
            return f"{self.name}{sf[0]}{self.number}{sf[1]}"

    def __repr__(self) -> str:
        """Return a string representation of this DevicePort."""
        return f"{self.device.name}.{self.get_name()}"

    def __cmp__(self, other: 'DevicePort') -> tuple:
        """Generate tuples to use for comparison."""
        n0 = -1 if self.number is None else self.number
        n1 = -1 if other.number is None else other.number
        p0 = (self.device.name, self.name, n0)
        p1 = (other.device.name, other.name, n1)
        return (p0, p1)

    def __lt__(self, other: 'DevicePort') -> bool:
        """Compare this DevicePort to another."""
        (p0, p1) = self.__cmp__(other)
        return p0 < p1

    def __le__(self, other: 'DevicePort') -> bool:
        """Compare this DevicePort to another."""
        (p0, p1) = self.__cmp__(other)
        return p0 <= p1

    def __gt__(self, other: 'DevicePort') -> bool:
        """Compare this DevicePort to another."""
        (p0, p1) = self.__cmp__(other)
        return p0 > p1

    def __ge__(self, other: 'DevicePort') -> bool:
        """Compare this DevicePort to another."""
        (p0, p1) = self.__cmp__(other)
        return p0 >= p1

    def __eq__(self, other: 'DevicePort') -> bool:
        """Compare this DevicePort to another."""
        (p0, p1) = self.__cmp__(other)
        return p0 == p1

    def __hash__(self) -> int:
        """Need to define a hash function since we defined __eq__."""
        return hash((self.device.name, self.name,
                     -1 if self.number is None else self.number))


class Device:
    """
    Device is the base class for a node in the AHP graph.

    This object is immutable. Each device exports several ports.
    A device may be represented by an model, may be an assembly
    of other devices, or both. If an assembly, then the device must define
    an expand() method that returns a device graph that implements the device.

    Devices may contain submodules which allow for parameterization of
    functionality similar to a lambda function (ex. SST subcomponents). This
    is done by creating a Device to represent the submodule and then adding
    it into another device.

    Note that successive calls to port() will return the same DevicePort
    object so they can be used in sets and comparisons.

    Each device must have a unique name.
    """

    library = None
    assembly = False
    _portinfo = None

    def __init__(self, name: str, model: str = None,
                 attr: dict = None) -> 'Device':
        """
        Initialize the device.

        Initialize with the unique name, model, and optional
        dictionary of attributes which are used as model parameters.
        """
        self.name = name
        self.attr = attr if attr is not None else dict()
        self.ports = collections.defaultdict(dict)
        self.subs = set()
        self.subOwner = None
        self.partition = None
        self.type = self.__class__.__name__
        self.model = model

    def set_partition(self, rank: int, thread: int = None) -> None:
        """Assign a rank and optional thread to this device."""
        self.partition = (rank, thread)

    def add_submodule(self, device: 'Device', slotName: str,
                      slotIndex: int = None) -> None:
        """
        Add a submodule to this component.

        Both the submodule and this device must have libraries.
        Note that all submodules must be added to the device before
        the device is added to the graph.
        """
        if self.library is None or device.library is None:
            raise RuntimeError(f"Submodule and parent must have libraries")
        device.subOwner = self
        self.subs.add((device, slotName, slotIndex))

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
        elif info['limit'] == 1:
            return self.port(port)
        else:
            return lambda x: self.port(port, x)

    def port(self, port: str, number: int = None) -> 'DevicePort':
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

        elif info['limit'] == 1:
            # Single Port, don't use port numbers
            if number is not None:
                print(f"WARNING! Single port ({port}) being provided a port"
                      f" number ({number})")
            if port not in self.ports:
                self.ports[port] = DevicePort(self, port)
            return self.ports[port]

        else:
            # Multi Port, use port numbers and check the provided limit
            if number is None:
                number = len(self.ports[port])
            if info['limit'] is not None:
                if number >= info['limit']:
                    raise RuntimeError(f"Too many connections ({number}):"
                                       f" {port} (limit {info['limit']})")
            if number not in self.ports[port]:
                self.ports[port][number] = DevicePort(self, port, number)
            return self.ports[port][number]

    def get_portinfo(self) -> dict:
        """Return the portinfo for this Device Class."""
        if self._portinfo is None:
            return dict()
        return self._portinfo

    def get_category(self) -> str:
        """Return the category for this Device (type, model)."""
        if self.model is not None:
            return f"{self.type}_{self.model}"
        else:
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
        lines.append(f"\tassembly = {self.assembly}")
        if self.model:
            lines.append(f"\tmodel = {self.model}")
        if self.library:
            lines.append(f"\tlibrary = {self.library}")
        if self.partition:
            lines.append(f"\tpartition = {self.partition}")
        if self.subOwner is not None:
            lines.append(f"\tsubmoduleParent = {self.subOwner.name}")

        portinfo = self.get_portinfo()
        if portinfo:
            lines.append(f"\tPorts:")
            for port in sorted(portinfo):
                lines.append(f"\t\t{port} = {portinfo[port]}")
        if self.attr:
            lines.append(f"\tAttributes:")
            for key in sorted(self.attr):
                lines.append(f"\t\t{key} = {self.attr[key]}")
        if self.subs:
            lines.append(f"\tSubmodules:")
            for sub in sorted(self.subs, key=lambda x: (x[1], x[2])):
                lines.append(f"\t\t{sub[1]}:{sub[2]} -> {sub[0].name}")

        return "\n".join(lines)
