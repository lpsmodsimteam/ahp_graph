"""Collection of Unit tests for AHPGraph Device."""

from AHPGraph import *
from AHPGraph.unittest.test import *
from AHPGraph.unittest.Devices import *


def LibraryTest() -> bool:
    """Test of Device with Library."""
    t = test('LibraryTest')

    ltd = LibraryTestDevice().library
    t.test(ltd == 'ElementLibrary.Component', ltd)

    return t.finish()


def PortTest() -> bool:
    """Test of Device with various ports."""
    t = test('PortTest')

    ptd = PortTestDevice()
    portinfo = ptd.get_portinfo()

    t.test(portinfo['default']['type'] is None, 'default type')
    t.test(portinfo['default']['limit'] == 1, 'default limit')
    t.test(portinfo['default']['required'] is True, 'default required')
    t.test(portinfo['default']['format'] == '.#', 'default format')

    t.test(portinfo['type']['type'] == 'test', 'type')
    t.test(portinfo['no_limit']['limit'] is None, 'No limit')
    t.test(portinfo['limit']['limit'] == 2, 'limit')
    t.test(portinfo['optional']['required'] is False, 'optional')
    t.test(portinfo['format']['format'] == '(#)', 'format')

    t.test(ptd.default == ptd.port('default'), '__getattr__')
    t.test(ptd.default.device == ptd, 'device')
    t.test(ptd.default.name == 'default', 'name')
    t.test(ptd.default.number is None, 'No port number')
    notDefinedTest = None
    try:
        ptd.portNotDefined
        notDefinedTest = False
    except RuntimeError:
        notDefinedTest = True
    t.test(notDefinedTest, 'port not defined')

    noLimitTest = None
    try:
        for i in range(1000):
            ptd.no_limit(None)
        ptd.no_limit(3004823048)
        noLimitTest = True
    except RuntimeError:
        noLimitTest = False
    t.test(noLimitTest, 'no limit instantiation')

    limitTest = None
    try:
        ptd.limit(2)
        limitTest = False
    except RuntimeError:
        limitTest = True
    t.test(limitTest, 'limit instantiation')

    t.test(ptd.format(0).get_name() == 'format(0)', 'format incorrect')
    t.test(ptd.port('port').name == 'port', 'port named port')

    return t.finish()


def AssemblyTest() -> bool:
    """Test of Device that is an assembly."""
    t = test('AssemblyTest')

    try:
        ratd = RecursiveAssemblyTestDevice().assembly
        t.test(ratd, 'assembly')

        results = None

        @assembly
        class AssemblyNoExpandTestDevice(Device):
            """Assembly that doesn't define the expand function."""

            def __init__(self) -> 'Device':
                """Test Device for assembly with no expand function."""
                super().__init__(t.__class__.__name__)

        results = False
    except RuntimeError:
        results = True
    t.test(results, 'no expand method')

    return t.finish()


def ModelTest() -> bool:
    """Test of device with model."""
    t = test('ModelTest')

    mtd = ModelTestDevice('model0')
    ltd = LibraryTestDevice()
    t.test(mtd.model == 'model0', 'model')
    t.test(ltd.model is None, 'None model')

    return t.finish()


def AttributeTest() -> bool:
    """Test of Device with attributes."""
    t = test('AttributeTest')

    attr = {'a1': 1, 'a2': 'blue', 'a3': False}
    atd = AttributeTestDevice(attr)
    t.test(atd.attr == attr, 'attr')

    return t.finish()


def PartitionTest() -> bool:
    """Test of partitioning a device."""
    t = test('PartitionTest')

    ratd = RecursiveAssemblyTestDevice()
    ratd.set_partition(1)
    t.test(ratd.partition[0] == 1, 'rank')
    t.test(ratd.partition[1] is None, 'thread None')
    ratd.set_partition(2, 3)
    t.test(ratd.partition[0] == 2, 'rank')
    t.test(ratd.partition[1] == 3, 'thread')

    return t.finish()


def CategoryTest() -> bool:
    """Test of device category output."""
    t = test('CategoryTest')

    ltd = LibraryTestDevice()
    mtd = ModelTestDevice('model')
    t.test(ltd.get_category() == ltd.name, 'No model')
    t.test(mtd.get_category() == f'{mtd.name}_{mtd.model}', 'model')

    return t.finish()


def SubmoduleTest() -> bool:
    """Test for adding a submodule to a device."""
    t = test('SubmoduleTest')

    ltd0 = LibraryTestDevice()
    ltd1 = LibraryTestDevice()
    ltd0.add_submodule(ltd1, 'slotName')
    pop = ltd0.subs.pop()
    t.test(ltd1.subOwner == ltd0, 'subOwner')
    t.test(pop[0] == ltd1, 'subs')
    t.test(pop[1] == 'slotName', 'slotName')
    t.test(pop[2] is None, 'slotIndex')

    return t.finish()


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description='AHPGraph Device unittests')
    parser.add_argument('-v', '--verbose', action='store_true',
                        help='show detailed output')
    args = parser.parse_args()
    test.verbose = args.verbose

    results = [LibraryTest(),
               PortTest(),
               AssemblyTest(),
               ModelTest(),
               AttributeTest(),
               PartitionTest(),
               CategoryTest(),
               SubmoduleTest()]

    exit(1 if True in results else 0)
