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
    ltd = LibraryTestDevice().sstlib
    str = f"LibraryTest: {ltd}"
    assert (ltd == 'ElementLibrary.Component'), str
    print(f"Pass - {str}")


# TODO
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


def AssemblyTest():
    """Test of Device that is an assembly."""
    rat = RecursiveAssemblyTestDevice().assembly
    assert rat, 'AssemblyTest'
    print('Pass - AssemblyTest')


def NoNameTest():
    """Test of device with no name provided."""
    class NoNameTestDevice(Device):
        """Unit test for Device with no name."""

        def __init__(self) -> 'Device':
            """Test Device with no name."""
            super().__init__()

    try:
        nntd = NoNameTestDevice()
        raise AssertionError('NoNameTest')
    except TypeError:
        print('Pass - NoNameTest')


def ModelTest():
    """Test of device with model."""
    mt = ModelTestDevice('model0')
    ltd = LibraryTestDevice()
    assert (mt.model == 'model0'), 'model'
    assert (ltd.model is None), 'None model'
    print('Pass - ModelTest')


def AttributeTest():
    """Test of Device with attributes."""
    attr = {'a1': 1, 'a2': 'blue', 'a3': False}
    at = AttributeTestDevice(attr)
    assert (at.attr == attr), 'attr'
    print('Pass - AttributeTest')


def SubcomponentTest():
    """Test for adding subcomponent to a component."""
    ltd0 = LibraryTestDevice()
    ltd1 = LibraryTestDevice()
    ltd0.add_subcomponent(ltd1, 'slotName')
    pop = ltd0.subs.pop()
    assert (ltd1.subOwner == ltd0), 'subOwner'
    assert (pop[0] == ltd1), 'subs'
    assert (pop[1] == 'slotName'), 'slotName'
    assert (pop[2] is None), 'slotIndex'
    print('Pass - SubcomponentTest')


if __name__ == "__main__":
    LibraryTest()
    PortTest()
    AssemblyNoExpandTest()
    AssemblyTest()
    NoNameTest()
    ModelTest()
    AttributeTest()

    SubcomponentTest()

    print('All tests passed')
