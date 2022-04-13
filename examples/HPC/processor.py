"""
Collection of PyDL Device wrappers around SST Components
"""
from PyDL import *
import os


@sstlib('vanadis.VanadisCPU')
class VanadisCPU(Device):
    """VanadisCPU"""

    def __init__(self, name: str, attr: dict = None):
        """Initialize"""
        parameters = {
            "clock": "1GHz",
            "executable": (f"{os.getenv('SST_ELEMENTS_HOME')}"
                           "/src/sst/elements/rdmaNic/tests/app/rdma/msg"),
            "app.argc": 4,
            "app.arg0": "IMB",
            "app.arg1": "PingPong",
            "app.arg2": "-iter",
            "app.arg3": "3",
            "app.env_count": 1,
            "app.env0": f"HOME={os.getenv('HOME')}",
            "app.env1": "VANADIS_THREAD_NUM=0",
            "verbose": 0,
            "physical_fp_registers": 168,
            "physical_int_registers": 180,
            "integer_arith_cycles": 2,
            "integer_arith_units": 2,
            "fp_arith_cycles": 8,
            "fp_arith_units": 2,
            "branch_unit_cycles": 2,
            "print_int_reg": 1,
            "pipeline_trace_file": "",
            "reorder_slots": 64,
            "decodes_per_cycle": 4,
            "issues_per_cycle": 4,
            "retires_per_cycle": 4,
            "pause_when_retire_address": 0
        }
        if attr is not None:
            parameters.update(attr)
        super().__init__(name, attr=parameters)


@sstlib('vanadis.VanadisMIPSDecoder')
class VanadisMIPSDecoder(Device):
    """VanadisMIPSDecoder"""

    def __init__(self, name: str, attr: dict = None):
        """Initialize"""
        parameters = {
            "uop_cache_entries": 1536,
            "predecode_cache_entries": 4
        }
        if attr is not None:
            parameters.update(attr)
        super().__init__(name, attr=parameters)


@sstlib('vanadis.VanadisMIPSOSHandler')
@port('os_link', Port.Single, 'os', Port.Required)
class VanadisMIPSOSHandler(Device):
    """VanadisMIPSOSHandler"""

    def __init__(self, name: str, attr: dict = None):
        """Initialize"""
        parameters = {
            "verbose": 0,
            "brk_zero_memory": "yes"
        }
        if attr is not None:
            parameters.update(attr)
        super().__init__(name, attr=parameters)


@sstlib('vanadis.VanadisBasicBranchUnit')
class VanadisBasicBranchUnit(Device):
    """VanadisBasicBranchUnit"""

    def __init__(self, name: str, attr: dict = None):
        """Initialize"""
        parameters = {
            "branch_entries": 32
        }
        if attr is not None:
            parameters.update(attr)
        super().__init__(name, attr=parameters)


@sstlib('vanadis.VanadisSequentialLoadStoreQueue')
class VanadisSequentialLoadStoreQueue(Device):
    """VanadisSequentialLoadStoreQueue"""

    def __init__(self, name: str, attr: dict = None):
        """Initialize"""
        parameters = {
            "verbose": 0,
            "address_mask": 0xFFFFFFFF,
            "load_store_entries": 32,
            "fault_non_written_loads_after": 0,
            "check_memory_loads": "no",
            "allow_speculated_operations": "no"
        }
        if attr is not None:
            parameters.update(attr)
        super().__init__(name, attr=parameters)


@sstlib('vanadis.VanadisNodeOS')
@port('core', Port.Multi, 'os', Port.Required, '#')
class VanadisNodeOS(Device):
    """VanadisNodeOS"""

    def __init__(self, name: str, attr: dict = None):
        """Initialize"""
        parameters = {
            "verbose": 0,
            "cores": 1,
            "heap_start": 512 * 1024 * 1024,
            "heap_end": (2 * 1024 * 1024 * 1024) - 4096,
            "page_size": 4096,
            "heap_verbose": 0
        }
        if attr is not None:
            parameters.update(attr)
        super().__init__(name, attr=parameters)


@sstlib('memHierarchy.standardInterface')
@port('port', Port.Single, 'simpleMem', Port.Required)
class memInterface(Device):
    """memInterface"""

    def __init__(self, name: str, attr: dict = None):
        """Initialize"""
        parameters = {
            "coreId": 0
        }
        if attr is not None:
            parameters.update(attr)
        super().__init__(name, attr=parameters)


@sstlib('memHierarchy.Cache')
@port('high_network', Port.Multi, 'simpleMem', Port.Required, '_#')
@port('low_network', Port.Multi, 'simpleMem', Port.Required, '_#')
class Cache(Device):
    """Cache"""

    def __init__(self, name: str, model: str, attr: dict = None):
        """Initialize with a model of which cache level this is (L1, L2)."""
        parameters = {
            "access_latency_cycles": 2,
            "replacement_policy": "lru",
            "coherence_protocol": "MESI",
            "associativity": 8,
            "cache_line_size": 64,
            "cache_size": "32KB",
            "cache_frequency": "1GHz"
        }
        if model == 'L1':
            parameters.update({
                "L1": 1
            })
        elif model == 'L2':
            parameters.update({
                "L1": 0
            })
        else:
            return None

        if attr is not None:
            parameters.update(attr)
        super().__init__(name, attr=parameters)


@sstlib('memHierarchy.Bus')
@port('high_network', Port.Multi, 'simpleMem', Port.Required, '_#')
@port('low_network', Port.Multi, 'simpleMem', Port.Required, '_#')
class Bus(Device):
    """Bus"""

    def __init__(self, name: str, attr: dict = None):
        """Initialize."""
        parameters = {
            "bus_frequency": "1GHz",
        }
        if attr is not None:
            parameters.update(attr)
        super().__init__(name, attr=parameters)


@sstlib('memHierarchy.MemLink')
@port('port', Port.Single, 'simpleMem', Port.Required)
class MemLink(Device):
    """MemLink"""

    def __init__(self, name: str, attr: dict = None):
        """Initialize."""
        parameters = dict()
        if attr is not None:
            parameters.update(attr)
        super().__init__(name, attr=parameters)


@assembly
@port('low_network', Port.Multi, 'simpleMem', Port.Required, '_#')
class Processor(Device):
    """Processor"""

    def __init__(self, name: str, node: int, core: int):
        """Initialize."""
        super().__init__(name)
        self.attr['node'] = node
        self.attr['core'] = core

    def expand(self):
        """Expand the server into its components."""
        graph = DeviceGraph()  # initialize a Device Graph
        # add myself to the graph, useful if the assembly has ports
        graph.add(self)

        cpu = VanadisCPU(f"{self.name}.VanadisCPU")

        decoder = VanadisMIPSDecoder(f"{self.name}.VanadisMIPSDecoder")
        osHandler = VanadisMIPSOSHandler(f"{self.name}.VanadisMIPSOSHandler")
        branch = VanadisBasicBranchUnit(f"{self.name}.VanadisBasicBranchUnit")
        decoder.add_subcomponent(osHandler, "os_handler")
        decoder.add_subcomponent(branch, "branch_unit")
        cpu.add_subcomponent(decoder, 'decoder0')

        icache = memInterface(f"{self.name}.ICache",
                              {'coreId': self.attr['core']})
        cpu.add_subcomponent(icache, 'mem_interface_inst')

        lsq = VanadisSequentialLoadStoreQueue(
            f"{self.name}.VanadisSequentialLoadStoreQueue")
        cpu.add_subcomponent(lsq, 'lsq')

        dcache = memInterface(f"{self.name}.DCache",
                              {'coreId': self.attr['core']})
        cpu.add_subcomponent(dcache, 'memory_interface')

        nodeOS = VanadisNodeOS(f"{self.name}.VanadisNodeOS")
        nodeOSmem = memInterface(f"{self.name}.NodeOSMemIF",
                                 {'coreId': self.attr['core']})
        nodeOS.add_subcomponent(nodeOSmem, 'mem_interface')

        nodeOSL1D = Cache(f"{self.name}.nodeOSL1D", 'L1')

        cpuL1D = Cache(f"{self.name}.cpuL1D", 'L1')
        cpu_to_L1D = MemLink(f"{self.name}.cpu_to_L1D")
        L1D_to_L2 = MemLink(f"{self.name}.L1D_to_L2")
        cpuL1D.add_subcomponent(cpu_to_L1D, 'cpulink')
        cpuL1D.add_subcomponent(L1D_to_L2, 'memlink')

        cpuL1I = Cache(f"{self.name}.cpuL1I", 'L1')
        cpu_to_L1I = MemLink(f"{self.name}.cpu_to_L1I")
        L1I_to_L2 = MemLink(f"{self.name}.L1I_to_L2")
        cpuL1I.add_subcomponent(cpu_to_L1I, 'cpulink')
        cpuL1I.add_subcomponent(L1I_to_L2, 'memlink')

        bus = Bus(f"{self.name}.Bus")

        # now that the subcomponents have been added, we can add things
        # to the DeviceGraph and start linking them together
        # Only devices that are NOT subcomponents get added to the graph
        # directly!
        graph.add(cpu)
        graph.add(nodeOS)
        graph.add(nodeOSL1D)
        graph.add(cpuL1D)
        graph.add(cpuL1I)
        graph.add(bus)

        graph.link(dcache.port('port'), cpu_to_L1D.port('port'), 1000)
        graph.link(icache.port('port'), cpu_to_L1I.port('port'), 1000)
        graph.link(nodeOSmem.port('port'), nodeOSL1D.high_network(0), 1000)
        graph.link(L1D_to_L2.port('port'), bus.high_network(0), 1000)
        graph.link(L1I_to_L2.port('port'), bus.high_network(1), 1000)
        graph.link(cpuL1D.low_network(0), bus.high_network(2), 1000)
        graph.link(osHandler.os_link, nodeOS.core(0), 5000)

        graph.link(bus.low_network(0), self.low_network(0), 1000)
        return graph
