"""
Vanadis Processor assembly.

Constructed from Vanadis components along with various L1 Caches.
Processor connects via a memHierarchy Bus.
"""
from ahp_graph.Device import *
from ahp_graph.DeviceGraph import *
import os


class VanadisCPU(Device):
    """VanadisCPU."""

    library = 'vanadis.dbg_VanadisCPU'
    portinfo = PortInfo()
    portinfo.add('os_link', 'os')
    attr = {
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


class VanadisMIPSDecoder(Device):
    """VanadisMIPSDecoder."""

    library = 'vanadis.VanadisMIPSDecoder'
    attr = {
        "uop_cache_entries": 1536,
        "predecode_cache_entries": 4
    }


class VanadisMIPSOSHandler(Device):
    """VanadisMIPSOSHandler."""

    library = 'vanadis.VanadisMIPSOSHandler'
    attr = {
        "verbose": 0,
        "brk_zero_memory": "yes"
    }


class VanadisBasicBranchUnit(Device):
    """VanadisBasicBranchUnit."""

    library = 'vanadis.VanadisBasicBranchUnit'
    attr = {
        "branch_entries": 32
    }


class VanadisSequentialLoadStoreQueue(Device):
    """VanadisSequentialLoadStoreQueue."""

    library = 'vanadis.VanadisSequentialLoadStoreQueue'
    attr = {
        "verbose": 0,
        "address_mask": 0xFFFFFFFF,
        "load_store_entries": 32,
        "fault_non_written_loads_after": 0,
        "check_memory_loads": "no",
        "allow_speculated_operations": "no"
    }


class VanadisNodeOS(Device):
    """VanadisNodeOS."""

    library = 'vanadis.VanadisNodeOS'
    portinfo = PortInfo()
    portinfo.add('core', 'os', limit=None, format='#')
    attr = {
        "verbose": 0,
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

    def __init__(self, name: str, cores: int = 1,
                 attr: dict = None) -> None:
        """Initialize with the number of cores per server."""
        super().__init__(name, attr=attr)
        self.attr['cores'] = cores


class memInterface(Device):
    """memInterface."""

    library = 'memHierarchy.standardInterface'
    portinfo = PortInfo()
    portinfo.add('port', 'simpleMem', required=False)

    def __init__(self, name: str, coreId: int = 0,
                 attr: dict = None) -> None:
        """Initialize."""
        super().__init__(name, attr=attr)
        self.attr['coreId'] = coreId


class Cache(Device):
    """Cache."""

    library = 'memHierarchy.Cache'
    portinfo = PortInfo()
    portinfo.add('high_network', 'simpleMem', None, False, '_#')
    portinfo.add('low_network', 'simpleMem', None, False, '_#')
    attr = {
        "replacement_policy": "lru",
        "coherence_protocol": "MESI",
        "cache_line_size": 64,
        "cache_frequency": "1GHz"
    }

    def __init__(self, name: str, model: str, attr: dict = None) -> None:
        """Initialize with a model of which cache level this is (L1, L2)."""
        if model == 'L1':
            parameters = {
                "L1": 1,
                "access_latency_cycles": 2,
                "associativity": 8,
                "cache_size": "32KB",
            }
        elif model == 'L2':
            parameters = {
                "L1": 0,
                "access_latency_cycles": 14,
                "associativity": 16,
                "cache_size": "1MB"
            }
        else:
            return None

        if attr is not None:
            parameters.update(attr)
        super().__init__(name, model, parameters)


class Bus(Device):
    """Bus."""

    library = 'memHierarchy.Bus'
    portinfo = PortInfo()
    portinfo.add('high_network', 'simpleMem', None, False, '_#')
    portinfo.add('low_network', 'simpleMem', None, False, '_#')
    attr = {
        "bus_frequency": "1GHz",
    }


class MemLink(Device):
    """MemLink."""

    library = 'memHierarchy.MemLink'
    portinfo = PortInfo()
    portinfo.add('port', 'simpleMem')


class Processor(Device):
    """Processor assembly made of various Vanadis components and Caches."""

    portinfo = PortInfo()
    portinfo.add('low_network', 'simpleMem', None, False, '_#')

    def __init__(self, name: str, core: int = 0, cores: int = 1,
                 attr: dict = None) -> None:
        """Initialize with the core ID and number of cores in a server."""
        super().__init__(name, attr=attr)
        self.attr['core'] = core
        self.attr['cores'] = cores

    def expand(self, graph: DeviceGraph) -> None:
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
