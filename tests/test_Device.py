"""Collection of Unit tests for ahp_graph Device."""

from ahp_graph.Device import *
from Devices import *


def test_library() -> None:
    """Test of Device with Library."""
    ltd = LibraryTestDevice().library
    assert ltd == 'ElementLibrary.Component', ltd


def test_port() -> None:
    """Test of Device with various ports."""
    ptd = PortTestDevice()

    assert ptd.portinfo['default'][0] == 1, 'default limit'
    assert ptd.portinfo['default'][1] is None, 'default type'
    assert ptd.portinfo['default'][2] is True, 'default required'
    assert ptd.portinfo['default'][3] == '.p#', 'default format'

    assert ptd.portinfo['no_limit'][0] is None, 'No limit'
    assert ptd.portinfo['limit'][0] == 2, 'limit'
    assert ptd.portinfo['ptype'][1] == 'test', 'type'
    assert ptd.portinfo['optional'][2] is False, 'optional'
    assert ptd.portinfo['format'][3] == '(#)', 'format'

    assert ptd.default == ptd.port('default'), '__getattr__'
    assert ptd.default.device == ptd, 'device'  # type: ignore[union-attr]
    assert ptd.default.name == 'default', 'name'  # type: ignore[union-attr]
    assert ptd.default.number is None, 'No port number'  # type: ignore[union-attr]
    notDefinedTest = None
    try:
        ptd.portNotDefined
        notDefinedTest = False
    except RuntimeError:
        notDefinedTest = True
    assert notDefinedTest, 'port not defined'

    noLimitTest = None
    try:
        for i in range(1000):
            ptd.no_limit(None)  # type: ignore[operator]
        ptd.no_limit(3004823048)  # type: ignore[operator]
        noLimitTest = True
    except RuntimeError:
        noLimitTest = False
    assert noLimitTest, 'no limit instantiation'

    limitTest = None
    try:
        ptd.limit(2)  # type: ignore[operator]
        limitTest = False
    except RuntimeError:
        limitTest = True
    assert limitTest, 'limit instantiation'

    assert ptd.format(0).get_name() == 'format(0)', 'format incorrect'  # type: ignore[operator]
    assert ptd.port('port').name == 'port', 'port named port'


def test_assembly() -> None:
    """Test of Device that is an assembly."""
    ratd = RecursiveAssemblyTestDevice(0).library is None
    assert ratd, 'assembly'

    results = None
    try:
        class AssemblyNoExpandTestDevice(Device):
            """Assembly that doesn't define the expand function."""

            def __init__(self) -> None:
                """Test Device for assembly with no expand function."""
                super().__init__('AssemblyNoExpandTestDevice')

        anetd = AssemblyNoExpandTestDevice()
        results = False
    except RuntimeError:
        results = True
    assert results, 'no expand method'


def test_model() -> None:
    """Test of device with model."""
    mtd = ModelTestDevice('model0')
    ltd = LibraryTestDevice()
    assert mtd.model == 'model0', 'model'
    assert ltd.model is None, 'None model'


def test_attribute() -> None:
    """Test of Device with attributes."""
    attr1 = {'a1': 1, 'a2': 'blue', 'a3': False}
    atd1 = AttributeTestDevice({})
    assert atd1.attr == attr1, 'class attr'
    attr2 = {'a1': 1, 'a2': 'blue', 'a3': False, 'b': 'test'}
    atd2 = AttributeTestDevice({'b': 'test'})
    assert atd2.attr == attr2, 'instance attr'
    assert atd1.attr == attr1, 'class attr unchanged'


def test_partition() -> None:
    """Test of partitioning a device."""
    ratd = RecursiveAssemblyTestDevice(0)
    ratd.set_partition(1)
    assert ratd.partition[0] == 1, 'rank'  # type: ignore[index]
    assert ratd.partition[1] is None, 'thread None'  # type: ignore[index]
    ratd.set_partition(2, 3)
    assert ratd.partition[0] == 2, 'rank'  # type: ignore[index]
    assert ratd.partition[1] == 3, 'thread'  # type: ignore[index]


def test_category() -> None:
    """Test of device category output."""
    ltd = LibraryTestDevice()
    mtd = ModelTestDevice('model')
    assert ltd.get_category() == ltd.name, 'No model'
    assert mtd.get_category() == f'{mtd.name}_{mtd.model}', 'model'


def test_submodule() -> None:
    """Test for adding a submodule to a device."""
    ltd0 = LibraryTestDevice()
    ltd1 = LibraryTestDevice()
    ltd0.add_submodule(ltd1, 'slotName')
    pop = ltd0.subs.pop()
    assert ltd1.subOwner == ltd0, 'subOwner'
    assert pop[0] == ltd1, 'subs'
    assert pop[1] == 'slotName', 'slotName'
    assert pop[2] is None, 'slotIndex'
