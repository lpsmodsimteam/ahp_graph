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
    t.test(graph.devices[sub1.name] == sub1, 'get device')
    t.test(graph.devices[sub2.name] == sub2, 'get device')
    t.test(graph.devices[sub11.name] == sub11, 'get device')

    sameName = None
    try:
        graph.add(LibraryTestDevice())
        graph.add(LibraryTestDevice())
        sameName = False
    except RuntimeError:
        sameName = True
    t.test(sameName, 'same name')

    return t.finish()


def CountDevicesTest() -> bool:
    """Test of counting Devices in a DeviceGraph."""
    t = test('CountDevicesTest')
    graph = DeviceGraph()

    devs = dict()
    for i in range(10):
        for j in range(3):
            devs[f'mtd{i}.{j}'] = ModelTestDevice(f'model{i}',
                                                  f'mtd{i}.{j}')
            graph.add(devs[f'mtd{i}.{j}'])

    t.test(len(graph.devices) == 30, 'num devices')
    t.test(graph.devices[devs['mtd0.0'].name] == devs['mtd0.0'], 'get device')
    c = graph.count_devices()
    t.test(len(c) == 10, 'device count length')
    t.test(c[devs['mtd0.0'].get_category()] == 3, 'device count length')

    return t.finish()


def CheckPartitionTest() -> bool:
    """Test of checking partition info in a DeviceGraph."""
    t = test('CheckPartitionTest')
    graph = DeviceGraph()

    devs = dict()
    for i in range(10):
        for j in range(3):
            devs[f'mtd{i}.{j}'] = ModelTestDevice(f'model{i}',
                                                  f'mtd{i}.{j}')
            devs[f'mtd{i}.{j}'].set_partition(i, j)
            graph.add(devs[f'mtd{i}.{j}'])

    partitionIncluded = None
    try:
        graph.check_partition()
        partitionIncluded = True
    except RuntimeError:
        partitionIncluded = False
    t.test(partitionIncluded, 'correct partitioning')

    graph.add(LibraryTestDevice())
    partitionIncluded = None
    try:
        graph.check_partition()
        partitionIncluded = False
    except RuntimeError:
        partitionIncluded = True
    t.test(partitionIncluded, 'missing partitioning')

    return t.finish()


def LinkTest() -> bool:
    """Test of linking Devices in a DeviceGraph."""
    t = test('LinkTest')
    graph = DeviceGraph()

    ptd0 = PortTestDevice(0)
    ptd1 = PortTestDevice(1)
    ltd = LibraryTestDevice()
    lptd = LibraryPortTestDevice()
    ltd.add_submodule(lptd, 'slot')

    graph.link(lptd.default, ptd0.optional)
    t.test(len(graph.devices) == 3, 'linking add submodule parent')
    t.test(graph.devices[ltd.name] == ltd, 'submodule parent included')
    t.test(graph.links.popitem()[1][2] == '1ps', 'default latency')
    # start with a fresh graph since the link was popped off the dictionary
    graph = DeviceGraph()
    graph.link(lptd.default, ptd0.optional)
    linkAgain = None
    try:
        graph.link(ptd0.optional, lptd.default)
        linkAgain = False
    except RuntimeError:
        linkAgain = True
    t.test(linkAgain, 'link again with ports reversed')
    changeSinglePortLink = None
    try:
        graph.link(ptd0.optional, ptd1.optional)
        changeSinglePortLink = False
    except RuntimeError:
        changeSinglePortLink = True
    t.test(changeSinglePortLink, 'linking from a single port again')

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
               AddDeviceTest(),
               CountDevicesTest(),
               CheckPartitionTest(),
               LinkTest()]

    exit(1 if True in results else 0)
