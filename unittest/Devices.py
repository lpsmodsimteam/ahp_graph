"""Collection of AHPGraph Devices for testing."""

from AHPGraph import *


@library('ElementLibrary.Component')
class LibraryTestDevice(Device):
    """Unit test for Library."""

    def __init__(self, name: str = '') -> 'Device':
        """Test Device for Library."""
        super().__init__(f'{self.__class__.__name__}{name}')


@port('default')
@port('ptype', 'test')
@port('no_limit', limit=None)
@port('limit', limit=2)
@port('optional', required=False)
@port('format', limit=None, format='(#)')
@port('exampleSinglePort', 'test', required=False)
@port('exampleMultiPort', 'test', None, False)
@port('port', 'port', None, False)
class PortTestDevice(Device):
    """Unit test for Device Ports."""

    def __init__(self, name: str = '') -> 'Device':
        """Test Device for Device Ports."""
        super().__init__(f'{self.__class__.__name__}{name}')


@library('ElementLibrary.Component')
@port('input')
@port('output')
@port('optional', limit=None, required=False)
class LibraryPortTestDevice(Device):
    """Unit test for Device with Library and Ports."""

    def __init__(self, name: str = '') -> 'Device':
        """Test Device for Library and Ports."""
        super().__init__(f'{self.__class__.__name__}{name}')


@assembly
@port('input')
@port('output')
@port('optional', limit=None, required=False)
class RecursiveAssemblyTestDevice(Device):
    """Unit Test for a recursive assembly. Creates a ring of Devices."""

    def __init__(self, levels: int, name: str = '') -> 'Device':
        """Test Device for recursive assembly."""
        super().__init__(f'{self.__class__.__name__}{levels}{name}', levels)

    def expand(self) -> 'DeviceGraph':
        """Test for expanding a Device."""
        graph = DeviceGraph()

        # If we have reached the specified number of levels, create 'leafs'
        # using LibraryPortTestDevice
        if self.model == 0:
            d0 = LibraryPortTestDevice(0)
            d1 = LibraryPortTestDevice(1)
            graph.link(d0.optional(0), self.optional(0))
            graph.link(d1.optional(0), self.optional(1))

        else:
            d0 = RecursiveAssemblyTestDevice(self.model-1, 0)
            d1 = RecursiveAssemblyTestDevice(self.model-1, 1)
            for i in range(2 ** self.model):
                graph.link(d0.optional(i), self.optional(i*2))
                graph.link(d1.optional(i), self.optional(i*2 + 1))

        graph.link(self.input, d0.input)
        graph.link(d0.output, d1.input)
        graph.link(d1.output, self.output)

        return graph


class ModelTestDevice(Device):
    """Unit test for Device with model."""

    def __init__(self, model, name: str = '') -> 'Device':
        """Test Device with model."""
        super().__init__(f'{self.__class__.__name__}{name}', model)


class AttributeTestDevice(Device):
    """Unit test for Device with attributes."""

    def __init__(self, attr, name: str = '') -> 'Device':
        """Test Device with attributes."""
        super().__init__(f'{self.__class__.__name__}{name}', attr=attr)
