"""
Collection of PyDL Device wrappers around SST Components
"""
from PyDL import *


@sstlib('miranda.BaseCPU')
@port('cache_link', Port.Single, 'simpleMem')
@port('src', Port.Single, 'network')
class BaseCPU(Device):
    """Miranda base CPU."""

    def __init__(self, name, **kwargs):
        """Initialize."""
        super().__init__(name, kwargs)


@sstlib('miranda.RandomGenerator')
class RandomGenerator(Device):
    """Random Generator for the miranda base CPU."""

    def __init__(self, name, **kwargs):
        """Initialize with the maxAddress set."""
        super().__init__(name, kwargs)


@sstlib('memHierarchy.Cache')
@port('high_network', Port.Single, 'simpleMem')
@port('low_network', Port.Single, 'simpleMem')
class Cache(Device):
    """Cache"""

    def __init__(self, name, model, **kwargs):
        """Initialize."""
        super().__init__(name, model, kwargs)


@sstlib('memHierarchy.MemController')
@port('direct_link', Port.Single, 'simpleMem')
class MemController(Device):
    """MemController"""

    def __init__(self, name, **kwargs):
        """Initialize."""
        super().__init__(name, kwargs)


@sstlib('memHierarchy.simpleMem')
class simpleMem(Device):
    """simpleMem"""

    def __init__(self, name, **kwargs):
        """Initialize."""
        super().__init__(name, kwargs)


@sstlib('merlin.hr_router')
@port('network', Port.Multi, 'network')
class Router(Device):
    """Router"""

    def __init__(self, name, model, **kwargs):
        """Initialize."""
        super().__init__(name, model, kwargs)
