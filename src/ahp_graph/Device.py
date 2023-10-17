"""
This module represents a Device.

The most important feature is that a Device can be an assembly, meaning it is
constructed of other Devices. This combined with the DeviceGraph allows for
hierarchical representations of a graph.
"""

class SmallDeviceAttr(list):
    """
    Implement a low-memory attribute dictionary

    This class mocks up a dict API using a list for the underlying
    storage.  While is can save a significant amount of memory, it
    does so at the cost of O(n) inserts and lookups.

    The list stores keys at even indices and values at odd indices.
    """
    __slots__ = ()

    def __init__(self, vals=None):
        super().__init__()
        if vals is not None:
            self.update(vals)

    def __setitem__(self, key, val):
        for i in range(0, super().__len__(), 2):
            if super().__getitem__(i) == key:
                super().__setitem__(i+1, val)
                return val

        self.append(key)
        self.append(val)
        return val

    def __getitem__(self, key):
        for i in range(0, super().__len__(), 2):
            if super().__getitem__(i) == key:
                return super().__getitem__(i+1)
        raise KeyError(key)

    def __delitem__(self, key):
        raise NotImplemented

    def pop(self, *args):
        raise NotImplemented

    def popitem(self, *args):
        raise NotImplemented

    def remove(self, *args):
        raise NotImplemented

    def get(self, key, default=None):
        for i in range(0, super().__len__(), 2):
            if super().__getitem__(i) == key:
                return super().__getitem__(i+1)
        return default

    def __len__(self):
        return super().__len__() // 2

    def __contains__(self, key):
        return any(_ == key for _ in self.__reversed__())

    def __iter__(self):
        return iter(super().__getitem__(slice(0, None, 2)))

    def __reversed__(self):
        return iter(super().__getitem__(slice(super().__len__()-2, None, -2)))

    def keys(self):
        return super().__getitem__(slice(0, None, 2))

    def values(self):
        return super().__getitem__(slice(1, None, 2))

    def items(self):
        it = super().__iter__()
        return zip(it, it)

    def update(self, vals=None, **kwds):
        if vals is not None:
            if type(vals) is dict:
                vals = vals.items()
            for key, val in vals:
                self.append(key)
                self.append(val)
        for key, val in kwds.items():
            self.append(key)
            self.append(val)


class PortInfo(dict):
    """
    PortInfo is a dictionary describing what ports a Device can have.

    PortInfo contains information such as port type, limit on the number
    of connections, whether the port is required, and formatting data.
    PortInfo is a class variable which defines the available ports for
    all instances of a specific Device. DevicePort represents an actual
    instance of a port on a Device.
    """
    __slots__ = ()

    def add(self, name: str, ptype: str = None, limit: int = 1,
            required: bool = True, format: str = '.p#') -> None:
        """Add a port definition to the dictionary."""
        self[name] = (limit, ptype, required, format)


class DevicePort:
    """
    A DevicePort represents an instance of a port on a Device.

    DevicePort contains a Device reference, a port name, and an
    optional port number.  It can also reference the other DevicePort
    to which it is linked.  We use __slots__ to minimize the amount
    of memory used by each instance; it can save maybe 10% or so.
    """
    __slots__ = ('device', 'name', 'number', 'link')

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
    an expand() method that returns a DeviceGraph that implements
    the Device.

    Devices may contain submodules which allow for parameterization of
    functionality similar to a lambda function (ex. SST subcomponents).
    This is done by creating a Device to represent the submodule and
    then adding it into another Device.

    The variables library and portinfo are class variables that can be
    set on the definition of a new Device class. The variable attr is a
    dictionary of attributes.
    """
    __slots__ = (
        'name', 'attr', 'ports', 'subs', 'subOwner',
        'partition', 'type', 'model'
    )
    library = None
    portinfo = PortInfo()

    def __init__(self, name: str, model: str = None,
                 attr: dict = None) -> None:
        """
        Initialize the Device.

        Initialize with the unique name, model, and optional
        dictionary of attributes which are used as model parameters.
        """
        self.name = name
        self.attr = SmallDeviceAttr(attr)
        self.ports = {}
        self.subs = None
        self.subOwner = None
        self.partition = None
        self.type = self.__class__.__name__
        self.model = model
        if self.library is None and not hasattr(self, "expand"):
            raise RuntimeError(f"Assemblies must define expand: {self.type}")

    def dealloc(self):
        """
        Deallocate the device.  This clears ports and other references.
        """
        self.ports.clear()
        self.subs = None
        self.subOwner = None

    def set_partition(self, rank: int, thread: int = None) -> None:
        """
        Assign a rank and optional thread to this device.
        """
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
        if not self.subs:
            self.subs = []
        self.subs.append((device, slotName, slotIndex))

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

        if info[0] == 1:
            # Single Port, don't use port numbers
            if number is not None:
                print(f"WARNING! Single port ({port}) being provided a port"
                      f" number ({number})")

        else:
            #
            # Multi Port, use port numbers and check the provided limit
            #
            # As a hack, we store the port count in the same dict as we
            # store the port pairs.  We need to be careful to filter it
            # out when we access the ports.
            #
            if number is None:
                number = self.ports.get(port, 0)
            if info[0] is not None:
                if number >= info[0]:
                    raise RuntimeError(f"Too many connections ({number}):"
                                       f" {port} (limit {info[0]})")
            self.ports[port] = max(number+1, self.ports.get(port, 1))
            
        key = (port, number)
        if key not in self.ports:
            self.ports[key] = DevicePort(self, port, number)
        return self.ports[key]

    def get_category(self) -> str:
        """Return the category for this Device (type, model)."""
        if self.model is not None:
            return f"{self.type}_{self.model}"
        return self.type

    def label_ports(self) -> str:
        """Return the port labels for a graphviz record style node."""
        if len(self.ports) == 0:
            return ""

        port_names = set([ 
            p[0] for p in self.ports.keys() if isinstance(p, tuple)
        ])

        label = '{'
        for port in port_names:
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
            for key, val in sorted(self.attr.items()):
                lines.append(f"\t\t{key} = {val}")
        if self.subs:
            lines.append(f"\tSubmodules:")
            for sub in sorted(self.subs, key=lambda x: (x[1], x[2])):
                lines.append(f"\t\t{sub[1]}:{sub[2]} -> {sub[0].name}")

        return "\n".join(lines)