"""
Server assembly.

Constructed from Processors and main memory using a NoC.
"""
from ahp_graph.Device import *
from ahp_graph.DeviceGraph import *
from processor import *


class MemNIC(Device):
    """MemNIC."""

    library = 'memHierarchy.MemNIC'
    portinfo = PortInfo()
    portinfo.add('port', 'simpleNet')
    attr = {
        "network_bw": "25GB/s"
    }

    def __init__(self, name: str, model: str, attr: dict = None) -> None:
        """Initialize with a model describing where this is on the NoC."""
        if model == 'Cache':
            parameters = {
                "group": 1,
                "destinations": "2,3"  # DirCtrl, SHMEMNIC
            }
        elif model == 'DirCtrl':
            parameters = {
                "group": 2,
                "sources": "1,3"  # Cache, SHMEMNIC
            }
        elif model == 'SHMEMNIC':
            parameters = {
                "group": 3,
                "sources": "1",  # Cache
                "destinations": "2"  # DirCtrl
            }
        else:
            return None

        if attr is not None:
            parameters.update(attr)
        super().__init__(name, attr=parameters)


class Router(Device):
    """Router."""

    library = 'merlin.hr_router'
    portinfo = PortInfo()
    portinfo.add('port', 'simpleNet', None, False, '#')

    def __init__(self, name: str, model: str, id: int = 0, ports: int = 1,
                 attr: dict = None) -> None:
        """Initialize with a model for a NoC or Interconnect."""
        parameters = {
            "id": id,
            "num_ports": ports
        }
        if model == 'NoC':
            parameters.update({
                "flit_size": "72B",
                "xbar_bw": "50GB/s",
                "link_bw": "25GB/s",
                "input_buf_size": "40KB",
                "output_buf_size": "40KB"
            })
        elif model == 'Interconnect':
            parameters.update({
                "link_bw": "16GB/s",
                "xbar_bw": "16GB/s",
                "link_lat": "10ns",
                "input_latency": "10ns",
                "output_latency": "10ns",
                "flit_size": "8B",
                "input_buf_size": "14KB",
                "output_buf_size": "14KB",
                "num_dims": 2
            })
        else:
            return None

        if attr is not None:
            parameters.update(attr)
        super().__init__(name, model, parameters)


class SingleRouter(Device):
    """Single Router Topology."""

    library = 'merlin.singlerouter'


class DirectoryController(Device):
    """DirectoryController."""

    library = 'memHierarchy.DirectoryController'
    portinfo = PortInfo()
    portinfo.add('direct_link', 'simpleMem', required=False)
    attr = {
        "coherence_protocol": "MESI",
        "entry_cache_size": 1024,
        "addr_range_start": 0x0,
        "addr_range_end": 0x7fffffff
    }


class MemController(Device):
    """MemController."""

    library = 'memHierarchy.MemController'
    portinfo = PortInfo()
    portinfo.add('direct_link', 'simpleMem', required=False)
    attr = {
        "clock": "1GHz",
        "backend.mem_size": "4GiB",
        "backing": "malloc",
        "addr_range_start": 0x0,
        "addr_range_end": 0x7fffffff
    }


class simpleMem(Device):
    """simpleMem."""

    library = 'memHierarchy.simpleMem'
    attr = {
        "mem_size": "2GiB",
        "access_time": "1 ns"
    }


class RDMA_NIC(Device):
    """RDMA_NIC."""

    library = 'rdmaNic.nic'
    portinfo = PortInfo()
    portinfo.add('port', 'simpleNet', None, False, '#')
    attr = {
        "clock": "8GHz",
        "maxPendingCmds": 128,
        "maxMemReqs": 256,
        "maxCmdQSize": 128,
        "cache_line_size": 64,
        'baseAddr': 0x80000000,
        'cmdQSize': 64
    }

    def __init__(self, name: str, id: int = 0, nodes: int = 2,
                 cores: int = 1, attr: dict = None) -> None:
        """
        Initialize using various simulation parameters.

        Need to know the number of processing elements (cores) per node.
        Also need the total number of nodes in the system.
        """
        super().__init__(name, attr=attr)
        self.attr['pesPerNode'] = cores
        self.attr['nicId'] = id
        self.attr['numNodes'] = nodes


class LinkControl(Device):
    """LinkControl."""

    library = 'merlin.linkcontrol'
    portinfo = PortInfo()
    portinfo.add('rtr_port', 'simpleNet')
    attr = {
        "link_bw": "16GB/s",
        "input_buf_size": "14KB",
        "output_buf_size": "14KB"
    }


class Server(Device):
    """Server constructed of a processor and some memory."""

    portinfo = PortInfo()
    portinfo.add('network', 'simpleNet')

    def __init__(self, name: str, node: int = 0,
                 racks: int = 2, nodes: int = 2, cores: int = 1,
                 attr: dict = None) -> None:
        """Store our name and use number of cores as the model type."""
        super().__init__(name, f"{cores}Core", attr)
        self.attr['node'] = node
        self.attr['racks'] = racks
        self.attr['nodes'] = nodes
        self.attr['cores'] = cores

    def expand(self, graph: DeviceGraph) -> None:
        """Expand the server into its components."""
        # Setup the NoC first so we can connect the Processors to it
        # Device names created by an assembly will automatically have the
        # assembly name prefixed to the name provided.
        NoC = Router("NoC", 'NoC', 0, self.attr['cores'] + 2)
        NoC_topo = SingleRouter("NoC_topo")
        NoC.add_submodule(NoC_topo, 'topology')

        # Generate the appropriate number of Processors and L2 Caches
        for core in range(self.attr['cores']):
            cpu = Processor(f"CPU{core}", core, self.attr['cores'])

            L2 = Cache(f"CPU{core}_L2", 'L2')
            L1_to_L2 = MemLink(f"CPU{core}_L1_to_L2")
            L2_to_mem = MemNIC(f"CPU{core}_L1_to_mem", 'Cache')
            L2.add_submodule(L1_to_L2, 'cpulink')
            L2.add_submodule(L2_to_mem, 'memlink')

            graph.link(cpu.low_network(0), L1_to_L2.port('port'), '1ns')
            graph.link(L2_to_mem.port('port'), NoC.port('port', core), '1ns')

        # Setup the main memory with controllers
        dirctrl = DirectoryController("DirectoryController")
        dir_to_mem = MemLink("dir_to_mem")
        dirNIC = MemNIC("dirNIC", 'DirCtrl')
        dirctrl.add_submodule(dir_to_mem, 'memlink')
        dirctrl.add_submodule(dirNIC, 'cpulink')

        memctrl = MemController("MemController")
        mem_to_dir = MemLink("mem_to_dir")
        memory = simpleMem("simpleMem")
        memctrl.add_submodule(mem_to_dir, 'cpulink')
        memctrl.add_submodule(memory, 'backend')

        # Initialize the RDMA_NIC and its interfaces
        nic = RDMA_NIC("NIC", self.attr['node'],
                       self.attr['racks'] * self.attr['nodes'],
                       self.attr['cores'])
        mmioIf = memInterface("MMIO_IF")
        mmioNIC = MemNIC("MMIO_NIC", 'SHMEMNIC')
        netLink = LinkControl("netLink")
        mmioIf.add_submodule(mmioNIC, 'memlink')
        nic.add_submodule(mmioIf, 'mmio')
        nic.add_submodule(netLink, 'rtrLink')

        graph.link(NoC.port('port', None), dirNIC.port('port'), '1ns')
        graph.link(NoC.port('port', None), mmioNIC.port('port'), '10ns')
        graph.link(dir_to_mem.port('port'), mem_to_dir.port('port'), '1ns')

        # Our external link is through the RDMA_NIC
        # Generally you don't want to put latency on the links to assembly
        # ports (ex: self.port) and allow whatever uses the assembly to
        # specify latency for the connection (it will get ignored anyway)
        graph.link(netLink.port('rtr_port'), self.network)
