"""Collection of Unit tests for AHPGraph Device."""

from AHPGraph import *
from AHPGraph.unittest.test import *
from AHPGraph.unittest.Devices import *


class LibraryTest(test):
    """Test of Device with Library."""

    def __init__(self, verbose: bool = False) -> None:
        """Run the test."""
        super().__init__(self.__class__.__name__, verbose)

        ltd = LibraryTestDevice().library
        self.test(ltd == 'ElementLibrary.Component', ltd)

        self.finish()


class PortTest(test):
    """Test of Device with various ports."""

    def __init__(self, verbose: bool = False) -> None:
        """Run the test."""
        super().__init__(self.__class__.__name__, verbose)

        ptd = PortTestDevice()
        portinfo = ptd.get_portinfo()

        self.test(portinfo['default']['type'] is None, 'default type')
        self.test(portinfo['default']['limit'] == 1, 'default limit')
        self.test(portinfo['default']['required'] is True, 'default required')
        self.test(portinfo['default']['format'] == '.#', 'default format')

        self.test(portinfo['type']['type'] == 'test', 'type')
        self.test(portinfo['no_limit']['limit'] is None, 'No limit')
        self.test(portinfo['limit']['limit'] == 2, 'limit')
        self.test(portinfo['optional']['required'] is False, 'optional')
        self.test(portinfo['format']['format'] == '(#)', 'format')

        self.test(ptd.default == ptd.port('default'), '__getattr__')
        self.test(ptd.default.device == ptd, 'device')
        self.test(ptd.default.name == 'default', 'name')
        self.test(ptd.default.number is None, 'No port number')
        notDefinedTest = None
        try:
            ptd.portNotDefined
            notDefinedTest = False
        except RuntimeError:
            notDefinedTest = True
        self.test(notDefinedTest, 'port not defined')

        noLimitTest = None
        try:
            for i in range(1000):
                ptd.no_limit(None)
            ptd.no_limit(3004823048)
            noLimitTest = True
        except RuntimeError:
            noLimitTest = False
        self.test(noLimitTest, 'no limit instantiation')

        limitTest = None
        try:
            ptd.limit(2)
            limitTest = False
        except RuntimeError:
            limitTest = True
        self.test(limitTest, 'limit instantiation')

        self.test(ptd.format(0).get_name() == 'format(0)', 'format incorrect')
        self.test(ptd.port('port').name == 'port', 'port named port')

        self.finish()


class AssemblyTest(test):
    """Test of Device that is an assembly."""

    def __init__(self, verbose: bool = False) -> None:
        """Run the test."""
        super().__init__(self.__class__.__name__, verbose)

        try:
            ratd = RecursiveAssemblyTestDevice().assembly
            self.test(ratd, 'assembly')

            results = None

            @assembly
            class AssemblyNoExpandTestDevice(Device):
                """Assembly that doesn't define the expand function."""

                def __init__(self) -> 'Device':
                    """Test Device for assembly with no expand function."""
                    super().__init__(self.__class__.__name__)

            results = False
        except RuntimeError:
            results = True
        self.test(results, 'no expand method')

        self.finish()


class ModelTest(test):
    """Test of device with model."""

    def __init__(self, verbose: bool = False) -> None:
        """Run the test."""
        super().__init__(self.__class__.__name__, verbose)

        mtd = ModelTestDevice('model0')
        ltd = LibraryTestDevice()
        self.test(mtd.model == 'model0', 'model')
        self.test(ltd.model is None, 'None model')

        self.finish()


class AttributeTest(test):
    """Test of Device with attributes."""

    def __init__(self, verbose: bool = False) -> None:
        """Run the test."""
        super().__init__(self.__class__.__name__, verbose)

        attr = {'a1': 1, 'a2': 'blue', 'a3': False}
        atd = AttributeTestDevice(attr)
        self.test(atd.attr == attr, 'attr')

        self.finish()


class PartitionTest(test):
    """Test of partitioning a device."""

    def __init__(self, verbose: bool = False) -> None:
        """Run the test."""
        super().__init__(self.__class__.__name__, verbose)

        ratd = RecursiveAssemblyTestDevice()
        ratd.set_partition(1)
        self.test(ratd.partition[0] == 1, 'rank')
        self.test(ratd.partition[1] is None, 'thread None')
        ratd.set_partition(2, 3)
        self.test(ratd.partition[0] == 2, 'rank')
        self.test(ratd.partition[1] == 3, 'thread')

        self.finish()


class CategoryTest(test):
    """Test of device category output."""

    def __init__(self, verbose: bool = False) -> None:
        """Run the test."""
        super().__init__(self.__class__.__name__, verbose)

        ltd = LibraryTestDevice()
        mtd = ModelTestDevice('model')
        self.test(ltd.get_category() == ltd.name, 'No model')
        self.test(mtd.get_category() == f'{mtd.name}_{mtd.model}', 'model')

        self.finish()


class SubmoduleTest(test):
    """Test for adding a submodule to a device."""

    def __init__(self, verbose: bool = False) -> None:
        """Run the test."""
        super().__init__(self.__class__.__name__, verbose)

        ltd0 = LibraryTestDevice()
        ltd1 = LibraryTestDevice()
        ltd0.add_submodule(ltd1, 'slotName')
        pop = ltd0.subs.pop()
        self.test(ltd1.subOwner == ltd0, 'subOwner')
        self.test(pop[0] == ltd1, 'subs')
        self.test(pop[1] == 'slotName', 'slotName')
        self.test(pop[2] is None, 'slotIndex')

        self.finish()


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description='AHPGraph Device unittests')
    parser.add_argument('-v', '--verbose', action='store_true',
                        help='show detailed output')
    args = parser.parse_args()

    LibraryTest(args.verbose)
    PortTest(args.verbose)
    AssemblyTest(args.verbose)
    ModelTest(args.verbose)
    AttributeTest(args.verbose)
    PartitionTest(args.verbose)
    CategoryTest(args.verbose)
    SubmoduleTest(args.verbose)
