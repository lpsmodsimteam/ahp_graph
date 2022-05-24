"""Collection of Unit tests for AHPGraph DeviceGraph."""

from AHPGraph import *
from AHPGraph.unittest.test import *
from AHPGraph.unittest.Devices import *


def AttributeTest() -> bool:
    """Test of DeviceGraph with attributes."""
    t = test('AttributeTest')

    attr = {'a1': 1, 'a2': 'blue', 'a3': False}
    graph = DeviceGraph(attr)
    t.test(graph.attr == attr, 'attr')

    return t.finish()


def AddDeviceTest() -> bool:
    """Test of adding Devices to a DeviceGraph."""
    t = test('AddDeviceTest')
    graph = DeviceGraph()

    ltd = LibraryTestDevice('ltd')
    sub1 = LibraryTestDevice('sub1')
    sub2 = LibraryTestDevice('sub2')
    sub11 = LibraryTestDevice('sub11')
    sub1.add_submodule(sub11, 'slot')
    ltd.add_submodule(sub1, 'slot', 1)
    ltd.add_submodule(sub2, 'slot', 2)
    graph.add(ltd)

    t.test(len(graph.devices) == 4, 'num devices')
    t.test(graph.devices[ltd.name] == ltd, 'get device')

    return t.finish()


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(
        description='AHPGraph DeviceGraph unittests')
    parser.add_argument('-v', '--verbose', action='store_true',
                        help='show detailed output')
    args = parser.parse_args()
    test.verbose = args.verbose

    results = [AttributeTest(),
               AddDeviceTest()]

    exit(1 if True in results else 0)
