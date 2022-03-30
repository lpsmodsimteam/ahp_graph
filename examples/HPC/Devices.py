"""
Collection of PyDL Device wrappers around SST Components
"""
from PyDL import *


@sstlib('miranda.BaseCPU')
@port('cache_link', Port.Single, 'simpleMem')
@port('src', Port.Single, 'TODO: fix this', Port.Optional)
class BaseCPU(Device):
    """Miranda base CPU."""

    def __init__(self, name, **kwargs):
        """Initialize."""
        super().__init__(name, attr=kwargs)


@sstlib('miranda.RandomGenerator')
class RandomGenerator(Device):
    """Random Generator for the miranda base CPU."""

    def __init__(self, name, **kwargs):
        """Initialize with the maxAddress set."""
        super().__init__(name, attr=kwargs)


@sstlib('memHierarchy.Cache')
@port('high_network', Port.Multi, 'simpleMem')
@port('low_network', Port.Single, 'simpleMem')
class Cache(Device):
    """Cache"""

    def __init__(self, name, model, **kwargs):
        """Initialize with a model of which cache level this is (L1, L2)."""
        super().__init__(name, model, attr=kwargs)


@sstlib('memHierarchy.MemController')
@port('direct_link', Port.Single, 'simpleMem')
class MemController(Device):
    """MemController"""

    def __init__(self, name, **kwargs):
        """Initialize."""
        super().__init__(name, attr=kwargs)


@sstlib('memHierarchy.simpleMem')
class simpleMem(Device):
    """simpleMem"""

    def __init__(self, name, **kwargs):
        """Initialize."""
        super().__init__(name, attr=kwargs)


@sstlib('merlin.hr_router')
@port('network', Port.Multi, 'network', Port.Optional)
class Router(Device):
    """Router"""

    def __init__(self, name, model, **kwargs):
        """Initialize with a model describing the number of ports."""
        super().__init__(name, model, attr=kwargs)
