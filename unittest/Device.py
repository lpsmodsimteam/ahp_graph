"""Collection of Unit tests for AHPGraph Device."""

from AHPGraph import *
from AHPGraph.examples.pingpong import *


@sstlib('ElementLibrary.Component')
class LibraryTestDevice(Device):
    """Unit test for SST Library."""

    def __init__(self) -> 'Device':
        """Test Device for SST Library."""
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


class NoNameDeviceTestDevice(Device):
    """Unit test for Device with no name."""

    def __init__(self) -> 'Device':
        """Test Device with no name."""
        super().__init__()


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


def LibraryTest():
    """Test of Device with SST Library."""
    ltd = LibraryTestDevice()
    str = f"LibraryTest: {ltd.sstlib}"
    assert (ltd.sstlib == 'ElementLibrary.Component'), str
    print(f"Pass - {str}")


def PortTest():
    """Test of Device with various ports."""
    ptd = PortTestDevice()
    portinfo = ptd.get_portinfo()

    assert (ptd.default == ptd.port('default')), 'PortTest: __getattr__'

    try:
        ptd.portNotDefined
        raise AssertionError("PortTest: access port that isn't defined")
    except RuntimeError:
        pass

    print(f"Pass - PortTest")


def AssemblyNoExpandTest():
    """Test of assembly with no Expand function defined."""
    name = 'AssemblyNoExpandTest'
    try:
        @assembly
        class AssemblyNoExpandTestDevice(Device):
            """Assembly that doesn't define the expand function."""

            def __init__(self) -> 'Device':
                """Test Device for assembly with no expand function."""
                super().__init__(self.__class__.__name__)

        raise AssertionError(name)

    except RuntimeError:
        print(f"Pass - {name}")


if __name__ == "__main__":
    LibraryTest()
    PortTest()

    AssemblyNoExpandTest()

    print('All tests passed')
