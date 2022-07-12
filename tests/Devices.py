"""Collection of ahp_graph Devices for testing."""

from ahp_graph.Device import *
from ahp_graph.DeviceGraph import *


class LibraryTestDevice(Device):
    """Unit test for Library."""

    library = 'ElementLibrary.Component'

    def __init__(self, name: str = '') -> None:
        """Test Device for Library."""
        super().__init__(f'{self.__class__.__name__}{name}')


class PortTestDevice(Device):
    """Unit test for Device Ports."""

    library = 'ElementLibrary.Component'
    portinfo = PortInfo()
    portinfo.add('default')
    portinfo.add('ptype', 'test')
    portinfo.add('no_limit', limit=None)
    portinfo.add('limit', limit=2)
    portinfo.add('optional', required=False)
    portinfo.add('format', limit=None, format='(#)')
    portinfo.add('exampleSinglePort', 'test', required=False)
    portinfo.add('exampleMultiPort', 'test', None, False)
    portinfo.add('port', 'port', None, False)

    def __init__(self, name: str = '') -> None:
        """Test Device for Device Ports."""
        super().__init__(f'{self.__class__.__name__}{name}')


class LibraryPortTestDevice(Device):
    """Unit test for Device with Library and Ports."""

    library = 'ElementLibrary.Component'
    portinfo = PortInfo()
    portinfo.add('input')
    portinfo.add('output')
    portinfo.add('optional', limit=None, required=False)

    def __init__(self, name: str = '') -> None:
        """Test Device for Library and Ports."""
        super().__init__(f'{self.__class__.__name__}{name}')


class RecursiveAssemblyTestDevice(Device):
    """Unit Test for a recursive assembly. Creates a ring of Devices."""

    portinfo = PortInfo()
    portinfo.add('input')
    portinfo.add('output')
    portinfo.add('optional', limit=None, required=False)

    def __init__(self, levels: int, name: str = '') -> None:
        """Test Device for recursive assembly."""
        super().__init__(f'{self.__class__.__name__}{levels}{name}', str(levels))

    def expand(self, graph: DeviceGraph) -> None:
        """Test for expanding a Device."""
        # If we have reached the specified number of levels, create 'leafs'
        # using LibraryPortTestDevice
        level = 0
        if self.model is not None:
            level = int(self.model)
        if level == 0:
            d0 = LibraryPortTestDevice('0')
            d1 = LibraryPortTestDevice('1')
            graph.link(d0.optional(0), self.optional(0))
            graph.link(d1.optional(0), self.optional(1))

        else:
            d0 = RecursiveAssemblyTestDevice(level-1, '0')
            d1 = RecursiveAssemblyTestDevice(level-1, '1')
            for i in range(2 ** level):
                graph.link(d0.optional(i), self.optional(i*2))
                graph.link(d1.optional(i), self.optional(i*2 + 1))

        graph.link(self.input, d0.input)
        graph.link(d0.output, d1.input)
        graph.link(d1.output, self.output)


class ModelTestDevice(Device):
    """Unit test for Device with model."""

    library = 'ElementLibrary.Component'

    def __init__(self, model: str, name: str = '') -> None:
        """Test Device with model."""
        super().__init__(f'{self.__class__.__name__}{name}', model)


class AttributeTestDevice(Device):
    """Unit test for Device with attributes."""

    library = 'ElementLibrary.Component'
    attr = {'a1': 1, 'a2': 'blue', 'a3': False}

    def __init__(self, attr: dict, name: str = '') -> None:
        """Test Device with attributes."""
        super().__init__(f'{self.__class__.__name__}{name}', attr=attr)
