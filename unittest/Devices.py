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


@assembly
@port('input')
@port('output')
class RecursiveAssemblyTestDevice(Device):
    """Unit Test for a recursive assembly."""

    def __init__(self, name: str = '') -> 'Device':
        """Test Device for recursive assembly."""
        super().__init__(f'{self.__class__.__name__}{name}')

    def expand(self) -> 'DeviceGraph':
        """Test for expanding a Device."""
        graph = DeviceGraph()
        a = RecursiveAssemblyTestDevice()
        graph.link(a.input, self.input)
        graph.link(a.output, self.output)
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


@library('ElementLibrary.Component')
@port('default')
class LibraryPortTestDevice(Device):
    """Unit test for Device with Library and Port."""

    def __init__(self, name: str = '') -> 'Device':
        """Test Device for Library."""
        super().__init__(f'{self.__class__.__name__}{name}')


@assembly
@port('input')
@port('output')
class AssemblyTestDevice(Device):
    """Unit Test for an assembly."""

    def __init__(self, name: str = '') -> 'Device':
        """Test Device for an assembly."""
        super().__init__(f'{self.__class__.__name__}{name}')

    def expand(self) -> 'DeviceGraph':
        """Test for expanding a Device."""
        graph = DeviceGraph()

        ltd = LibraryTestDevice()
        lptd = LibraryPortTestDevice()
        sub = LibraryPortTestDevice('sub')
        ltd.add_submodule(sub, 'slot')

        graph.link(sub.default, self.input)
        graph.link(lptd.default, self.output)

        return graph


@assembly
@port('input')
@port('output')
class TopAssemblyTestDevice(Device):
    """Unit Test for an assembly."""

    def __init__(self, name: str = '') -> 'Device':
        """Test Device for an assembly."""
        super().__init__(f'{self.__class__.__name__}{name}')

    def expand(self) -> 'DeviceGraph':
        """Test for expanding a Device."""
        graph = DeviceGraph()

        atd0 = AssemblyTestDevice(0)
        atd1 = AssemblyTestDevice(1)
        ltd = LibraryTestDevice()
        lptd = LibraryPortTestDevice()
        sub = LibraryPortTestDevice('sub')
        ltd.add_submodule(sub, 'slot')

        graph.link(self.input, atd0.input)
        graph.link(atd0.output, atd1.input)
        graph.link(atd1.output, sub.default)
        graph.link(lptd.default, self.output)

        return graph
