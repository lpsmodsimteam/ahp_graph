"""Collection of AHPGraph Devices for testing."""

from AHPGraph import *


@library('ElementLibrary.Component')
class LibraryTestDevice(Device):
    """Unit test for Library."""

    def __init__(self) -> 'Device':
        """Test Device for Library."""
        super().__init__(self.__class__.__name__)


@port('default')
@port('type', 'test')
@port('no_limit', limit=None)
@port('limit', limit=2)
@port('optional', required=False)
@port('format', limit=None, format='(#)')
@port('exampleSinglePort', 'test', required=False)
@port('exampleMultiPort', 'test', None, False)
@port('port', 'port', None, False)
class PortTestDevice(Device):
    """Unit test for Device Ports."""

    def __init__(self) -> 'Device':
        """Test Device for Device Ports."""
        super().__init__(self.__class__.__name__)


@assembly
@port('input', 'input')
@port('output', 'output')
class RecursiveAssemblyTestDevice(Device):
    """Unit Test of a recursive assembly."""

    def __init__(self) -> 'Device':
        """Test Device for recursive assembly."""
        super().__init__(self.__class__.__name__)

    def expand(self) -> 'DeviceGraph':
        """Test for expanding a Device."""
        graph = DeviceGraph()
        a = AssemblyTest()
        graph.link(a.input, self.input)
        graph.link(a.output, self.output)
        return graph


class ModelTestDevice(Device):
    """Unit test for Device with model."""

    def __init__(self, model) -> 'Device':
        """Test Device with model."""
        super().__init__(self.__class__.__name__, model)


class AttributeTestDevice(Device):
    """Unit test for Device with attributes."""

    def __init__(self, attr) -> 'Device':
        """Test Device with attributes."""
        super().__init__(self.__class__.__name__, attr=attr)
