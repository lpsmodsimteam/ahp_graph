"""Collection of Unit tests for ahp_graph DeviceGraph."""

from ahp_graph.Device import *
from ahp_graph.DeviceGraph import *
from Devices import *


def test_attribute() -> None:
    """Test of DeviceGraph with attributes."""
    attr = {'a1': 1, 'a2': 'blue', 'a3': False}
    graph = DeviceGraph(attr)
    assert graph.attr == attr, 'attr'


def test_addDevice() -> None:
    """Test of adding Devices to a DeviceGraph."""
    graph = DeviceGraph()

    ltd = LibraryTestDevice('ltd')
    sub1 = LibraryTestDevice('sub1')
    sub2 = LibraryTestDevice('sub2')
    sub11 = LibraryTestDevice('sub11')
    sub1.add_submodule(sub11, 'slot')
    ltd.add_submodule(sub1, 'slot', 1)
    ltd.add_submodule(sub2, 'slot', 2)
    graph.add(ltd)

    assert len(graph.devices) == 4, 'num devices'
    assert ltd in graph.devices, 'get device'
    assert sub1 in graph.devices, 'get device'
    assert sub2 in graph.devices, 'get device'
    assert sub11 in graph.devices, 'get device'

    ltd = LibraryTestDevice()
    graph.add(ltd)
    graph.add(ltd)
    assert len(graph.devices) == 5, 'duplicate add'

    sameName = None
    try:
        graph.add(LibraryTestDevice())
        sameName = False
    except RuntimeError:
        sameName = True
    assert sameName, 'same name'


def test_countDevices() -> None:
    """Test of counting Devices in a DeviceGraph."""
    graph = DeviceGraph()

    devs = dict()
    for i in range(10):
        for j in range(3):
            devs[f'mtd{i}.{j}'] = ModelTestDevice(f'model{i}',
                                                  f'mtd{i}.{j}')
            graph.add(devs[f'mtd{i}.{j}'])

    assert len(graph.devices) == 30, 'num devices'
    assert devs['mtd0.0'] in graph.devices, 'get device'
    c = graph.count_devices()
    assert len(c) == 10, 'device count length'
    assert c[devs['mtd0.0'].get_category()] == 3, 'device count length'


def test_checkPartition() -> None:
    """Test of checking partition info in a DeviceGraph."""
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
    assert partitionIncluded, 'correct partitioning'

    graph.add(LibraryTestDevice())
    partitionIncluded = None
    try:
        graph.check_partition()
        partitionIncluded = False
    except RuntimeError:
        partitionIncluded = True
    assert partitionIncluded, 'missing partitioning'


def test_link() -> None:
    """Test of linking Devices in a DeviceGraph."""
    graph = DeviceGraph()

    ptd0 = PortTestDevice('0')
    ptd1 = PortTestDevice('1')
    ltd = LibraryTestDevice()
    lptd = LibraryPortTestDevice()
    ltd.add_submodule(lptd, 'slot')

    graph.link(lptd.input, ptd0.optional)
    assert len(graph.devices) == 3, 'linking add submodule parent'
    assert ltd in graph.devices, 'submodule parent included'
    assert graph.links[frozenset({lptd.input, ptd0.optional})] == '0s', 'default latency'
    linkAgain = None
    try:
        graph.link(ptd0.optional, lptd.input)
        linkAgain = False
    except RuntimeError:
        linkAgain = True
    assert linkAgain, 'link again with ports reversed'
    callablePort = None
    try:
        graph.link(ptd0.limit, ptd1.no_limit)
        callablePort = False
    except RuntimeError:
        callablePort = True
    assert callablePort, 'forgot to include port num on multi port'
    typeMismatch = None
    try:
        graph.link(ptd0.default, ptd1.ptype)
        typeMismatch = False
    except RuntimeError:
        typeMismatch = True
    assert typeMismatch, 'port type mismatch'
    changeSinglePortLink = None
    try:
        graph.link(ptd0.optional, ptd1.optional)
        changeSinglePortLink = False
    except RuntimeError:
        changeSinglePortLink = True
    assert changeSinglePortLink, 'linking from a single port again'
    graph.link(ptd0.limit(0), ptd1.limit(0), '123ns')
    assert graph.links[frozenset({ptd0.limit(0), ptd1.limit(0)})] == '123ns', 'latency'


def test_verifyLinks() -> None:
    """Test of verifying links in a DeviceGraph."""
    graph = DeviceGraph()

    ptd0 = PortTestDevice('0')
    ptd1 = PortTestDevice('1')
    ltd = LibraryTestDevice()
    lptd = LibraryPortTestDevice()
    ltd.add_submodule(lptd, 'slot')

    graph.link(lptd.input, ptd0.optional)
    graph.link(lptd.output, ptd1.optional)
    graph.link(ptd0.default, ptd1.default)
    graph.link(ptd0.ptype, ptd1.ptype)
    graph.link(ptd0.no_limit(0), ptd1.no_limit(0))
    graph.link(ptd0.limit(0), ptd1.limit(0))
    verified = None
    try:
        graph.verify_links()
        verified = False
    except RuntimeError:
        verified = True
    assert verified, 'not all required ports connected'

    graph.link(ptd0.format(0), ptd1.format(0))
    verified = None
    try:
        graph.verify_links()
        verified = True
    except RuntimeError:
        verified = False
    assert verified, 'verified all required ports have at least 1 connection'


def test_followLinks() -> None:
    """Test of following links by rank in a DeviceGraph."""
    graph = DeviceGraph()
    levels = 2

    ratd0 = RecursiveAssemblyTestDevice(levels, '0')
    ratd1 = RecursiveAssemblyTestDevice(levels, '1')
    lptd0 = LibraryPortTestDevice('0')
    lptd1 = LibraryPortTestDevice('1')

    # complete the rings
    graph.link(ratd0.input, ratd0.output)
    graph.link(ratd1.input, ratd1.output)

    graph.link(lptd0.input, lptd1.output)
    graph.link(lptd1.input, lptd0.output)
    for i in range(2 ** (levels+1)):
        graph.link(lptd0.optional(None), ratd0.optional(None))
        graph.link(lptd1.optional(None), ratd1.optional(None))

    ratd0.set_partition(0)
    ratd1.set_partition(1)
    lptd0.set_partition(2)
    lptd1.set_partition(2)

    graph.follow_links(0)
    for dev in graph.devices:
        if dev.library is None:
            assert dev.name == f'RecursiveAssemblyTestDevice{levels}1', 'only one assembly left'
        else:
            assert dev.library is not None, 'library set'


def test_flatten() -> None:
    """Test of flattening a DeviceGraph."""
    levels = 6

    def createGraph() -> tuple:
        """Create a graph for testing."""
        graph = DeviceGraph()

        ratd0 = RecursiveAssemblyTestDevice(levels, '0')
        ratd1 = RecursiveAssemblyTestDevice(levels, '1')
        lptd0 = LibraryPortTestDevice('0')
        lptd1 = LibraryPortTestDevice('1')

        # complete the rings
        graph.link(ratd0.input, ratd0.output)
        graph.link(ratd1.input, ratd1.output)

        graph.link(lptd0.input, lptd1.output)
        graph.link(lptd1.input, lptd0.output)
        for i in range(2 ** (levels+1)):
            graph.link(lptd0.optional(None), ratd0.optional(None))
            graph.link(lptd1.optional(None), ratd1.optional(None))

        ratd0.set_partition(0)
        ratd1.set_partition(1)
        lptd0.set_partition(2)
        lptd1.set_partition(2)
        return graph, ratd0

    flat, _ = createGraph()
    flat.flatten()
    assert not any([d.library is None for d in flat.devices]), 'no assemblies left'

    twoLevels, _ = createGraph()
    twoLevels.flatten(2)
    assert [d.library is None for d in twoLevels.devices].count(True) == 8, 'correct number of assemblies left'

    byName, _ = createGraph()
    byName.flatten(name=f'RecursiveAssemblyTestDevice{levels}0')
    rank0, _ = createGraph()
    rank0.flatten(rank=0)
    assert byName.names == rank0.names, 'name and rank devices'

    byNameLinks = set()
    rankLinks = set()
    for link in byName.links:
        for port in link:
            byNameLinks.add(str(port))
    for link in rank0.links:
        for port in link:
            rankLinks.add(str(port))
    assert byNameLinks == rankLinks, 'name and rank links'

    expand, ratd0 = createGraph()
    expand.flatten(expand={ratd0})
    assemblies = [d.library is None for d in expand.devices]
    assert assemblies.count(True) == 3, 'correct number of assemblies left'
