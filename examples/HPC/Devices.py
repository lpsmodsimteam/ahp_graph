"""
Collection of PyDL Device wrappers around SST Components
"""
from PyDL import *


@sstlib('miranda.BaseCPU')
@port('cache_link', Port.Single, 'simpleMem', Port.Required)
@port('src', Port.Single, 'network', Port.Optional)
class BaseCPU(Device):
    """Miranda base CPU."""

    def __init__(self, name, attr):
        """Initialize."""
        super().__init__(name, attr=attr)


@sstlib('miranda.RandomGenerator')
class RandomGenerator(Device):
    """Random Generator for the miranda base CPU."""

    def __init__(self, name, attr):
        """Initialize with the maxAddress set."""
        super().__init__(name, attr=attr)


@sstlib('memHierarchy.Cache')
@port('high_network', Port.Multi, 'simpleMem', Port.Required, '_#')
@port('low_network', Port.Multi, 'simpleMem', Port.Required, '_#')
class Cache(Device):
    """Cache"""

    def __init__(self, name, model, attr):
        """Initialize with a model of which cache level this is (L1, L2)."""
        super().__init__(name, model, attr)


@sstlib('memHierarchy.Bus')
@port('high_network', Port.Multi, 'simpleMem', Port.Required, '_#')
@port('low_network', Port.Multi, 'simpleMem', Port.Required, '_#')
class Bus(Device):
    """Bus"""

    def __init__(self, name, attr):
        """Initialize."""
        super().__init__(name, attr=attr)


@sstlib('memHierarchy.MemController')
@port('direct_link', Port.Single, 'simpleMem', Port.Required)
class MemController(Device):
    """MemController"""

    def __init__(self, name, attr):
        """Initialize."""
        super().__init__(name, attr=attr)


@sstlib('memHierarchy.simpleMem')
class simpleMem(Device):
    """simpleMem"""

    def __init__(self, name, attr):
        """Initialize."""
        super().__init__(name, attr=attr)


@sstlib('merlin.hr_router')
@port('port', Port.Multi, 'network', Port.Optional, '#')
class Router(Device):
    """Router"""

    def __init__(self, name, model, attr):
        """Initialize with a model describing the number of ports."""
        super().__init__(name, model, attr)


@sstlib('merlin.mesh')
class MeshTopology(Device):
    """Mesh Topology"""

    def __init__(self, name, attr):
        """Initialize."""
        super().__init__(name, attr=attr)
