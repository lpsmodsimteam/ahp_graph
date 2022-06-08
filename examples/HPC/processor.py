"""
Vanadis Processor assembly.

Constructed from Vanadis components along with various L1 Caches.
Processor connects via a memHierarchy Bus.
"""
from AHPGraph import *
import os


@library('vanadis.dbg_VanadisCPU')
@port('os_link', 'os')
class VanadisCPU(Device):
    """VanadisCPU."""

    def __init__(self, name: str, attr: dict = None) -> 'Device':
        """Initialize using the msg executable."""
        parameters = {
            "clock": "1GHz",
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


@library('vanadis.VanadisMIPSDecoder')
class VanadisMIPSDecoder(Device):
    """VanadisMIPSDecoder."""

    def __init__(self, name: str, attr: dict = None) -> 'Device':
        """Initialize."""
        parameters = {
            "uop_cache_entries": 1536,
            "predecode_cache_entries": 4
        }
        if attr is not None:
            parameters.update(attr)
        super().__init__(name, attr=parameters)


@library('vanadis.VanadisMIPSOSHandler')
class VanadisMIPSOSHandler(Device):
    """VanadisMIPSOSHandler."""

    def __init__(self, name: str, attr: dict = None) -> 'Device':
        """Initialize."""
        parameters = {
            "verbose": 0,
            "brk_zero_memory": "yes"
        }
        if attr is not None:
            parameters.update(attr)
        super().__init__(name, attr=parameters)


@library('vanadis.VanadisBasicBranchUnit')
class VanadisBasicBranchUnit(Device):
    """VanadisBasicBranchUnit."""

    def __init__(self, name: str, attr: dict = None) -> 'Device':
        """Initialize."""
        parameters = {
            "branch_entries": 32
        }
        if attr is not None:
            parameters.update(attr)
        super().__init__(name, attr=parameters)


@library('vanadis.VanadisSequentialLoadStoreQueue')
class VanadisSequentialLoadStoreQueue(Device):
    """VanadisSequentialLoadStoreQueue."""

    def __init__(self, name: str, attr: dict = None) -> 'Device':
        """Initialize."""
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


@library('vanadis.VanadisNodeOS')
@port('core', 'os', limit=None, format='#')
class VanadisNodeOS(Device):
    """VanadisNodeOS."""

    def __init__(self, name: str, cores: int = 1,
                 attr: dict = None) -> 'Device':
        """Initialize with the number of cores per server."""
        parameters = {
            "verbose": 0,
            "cores": cores,
            "heap_start": 512 * 1024 * 1024,
            "heap_end": (2 * 1024 * 1024 * 1024) - 4096,
            "page_size": 4096,
            "heap_verbose": 0,
            "executable": (f"{os.getenv('SST_ELEMENTS_HOME')}"
                           "/src/sst/elements/rdmaNic/tests/app/rdma/msg"),
            "app.argc": 4,
            "app.arg0": "IMB",
            "app.arg1": "PingPong",
            "app.arg2": "-iter",
            "app.arg3": "3",
            "app.env_count": 1,
            "app.env0": f"HOME={os.getenv('HOME')}",
            "app.env1": "VANADIS_THREAD_NUM=0"
        }
        if attr is not None:
            parameters.update(attr)
        super().__init__(name, attr=parameters)


@library('memHierarchy.standardInterface')
@port('port', 'simpleMem', required=False)
class memInterface(Device):
    """memInterface."""

    def __init__(self, name: str, coreId: int = 0,
                 attr: dict = None) -> 'Device':
        """Initialize."""
        parameters = {
            "coreId": coreId
        }
        if attr is not None:
            parameters.update(attr)
        super().__init__(name, attr=parameters)


@library('memHierarchy.Cache')
@port('high_network', 'simpleMem', None, False, '_#')
@port('low_network', 'simpleMem', None, False, '_#')
class Cache(Device):
    """Cache."""

    def __init__(self, name: str, model: str, attr: dict = None) -> 'Device':
        """Initialize with a model of which cache level this is (L1, L2)."""
        parameters = {
            "replacement_policy": "lru",
            "coherence_protocol": "MESI",
            "cache_line_size": 64,
            "cache_frequency": "1GHz"
        }
        if model == 'L1':
            parameters.update({
                "L1": 1,
                "access_latency_cycles": 2,
                "associativity": 8,
                "cache_size": "32KB",
            })
        elif model == 'L2':
            parameters.update({
                "L1": 0,
                "access_latency_cycles": 14,
                "associativity": 16,
                "cache_size": "1MB"
            })
        else:
            return None

        if attr is not None:
            parameters.update(attr)
        super().__init__(name, model, parameters)


@library('memHierarchy.Bus')
@port('high_network', 'simpleMem', None, False, '_#')
@port('low_network', 'simpleMem', None, False, '_#')
class Bus(Device):
    """Bus."""

    def __init__(self, name: str, attr: dict = None) -> 'Device':
        """Initialize."""
        parameters = {
            "bus_frequency": "1GHz",
        }
        if attr is not None:
            parameters.update(attr)
        super().__init__(name, attr=parameters)


@library('memHierarchy.MemLink')
@port('port', 'simpleMem')
class MemLink(Device):
    """MemLink."""

    def __init__(self, name: str, attr: dict = None) -> 'Device':
        """Initialize."""
        super().__init__(name, attr=attr)


@port('low_network', 'simpleMem', None, False, '_#')
class Processor(Device):
    """Processor assembly made of various Vanadis components and Caches."""

    def __init__(self, name: str, core: int = 0, cores: int = 1,
                 attr: dict = None) -> 'Device':
        """Initialize with the core ID and number of cores in a server."""
        super().__init__(name, attr=attr)
        self.attr['core'] = core
        self.attr['cores'] = cores

    def expand(self, graph: 'DeviceGraph') -> None:
        """Expand the server into its components."""
        # Reminder to add subcomponents to the main component BEFORE adding
        # the main component to the DeviceGraph. You can also link directly
        # to the subcomponents after they are connected to a parent component
        # Device names created by an assembly will automatically have the
        # assembly name prefixed to the name provided.
        cpu = VanadisCPU("VanadisCPU")

        decoder = VanadisMIPSDecoder("VanadisMIPSDecoder")
        osHandler = VanadisMIPSOSHandler("VanadisMIPSOSHandler")
        branch = VanadisBasicBranchUnit("VanadisBasicBranchUnit")
        decoder.add_submodule(osHandler, "os_handler")
        decoder.add_submodule(branch, "branch_unit")
        cpu.add_submodule(decoder, 'decoder0')

        icache = memInterface("ICache", self.attr['core'])
        cpu.add_submodule(icache, 'mem_interface_inst')

        lsq = VanadisSequentialLoadStoreQueue(
            "VanadisSequentialLoadStoreQueue")
        cpu.add_submodule(lsq, 'lsq')

        dcache = memInterface("DCache", self.attr['core'])
        lsq.add_submodule(dcache, 'memory_interface')

        nodeOS = VanadisNodeOS("VanadisNodeOS", self.attr['cores'])
        nodeOSmem = memInterface("NodeOSMemIF", self.attr['core'])
        nodeOS.add_submodule(nodeOSmem, 'mem_interface')

        nodeOSL1D = Cache("nodeOSL1D", 'L1')

        cpuL1D = Cache("cpuL1D", 'L1')
        cpu_to_L1D = MemLink("cpu_to_L1D")
        L1D_to_L2 = MemLink("L1D_to_L2")
        cpuL1D.add_submodule(cpu_to_L1D, 'cpulink')
        cpuL1D.add_submodule(L1D_to_L2, 'memlink')

        cpuL1I = Cache("cpuL1I", 'L1')
        cpu_to_L1I = MemLink("cpu_to_L1I")
        L1I_to_L2 = MemLink("L1I_to_L2")
        cpuL1I.add_submodule(cpu_to_L1I, 'cpulink')
        cpuL1I.add_submodule(L1I_to_L2, 'memlink')

        bus = Bus("Bus")

        # Linking automatically adds the devices as needed
        graph.link(dcache.port('port'), cpu_to_L1D.port('port'), '1ns')
        graph.link(icache.port('port'), cpu_to_L1I.port('port'), '1ns')
        graph.link(nodeOSmem.port('port'), nodeOSL1D.high_network(0), '1ns')
        graph.link(L1D_to_L2.port('port'), bus.high_network(0), '1ns')
        graph.link(L1I_to_L2.port('port'), bus.high_network(1), '1ns')
        graph.link(nodeOSL1D.low_network(0), bus.high_network(2), '1ns')
        graph.link(cpu.os_link, nodeOS.core(0), '5ns')

        # Our external connection goes through the memHierarchy Bus
        # Generally you don't want to put latency on the links to assembly
        # ports (ex: self.port) and allow whatever uses the assembly to
        # specify latency for the connection (it will get ignored anyway)
        graph.link(bus.low_network(0), self.low_network(0))
