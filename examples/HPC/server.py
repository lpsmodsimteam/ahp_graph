"""
Server assembly.

Constructed from Processors and main memory using a NoC.
"""
from AHPGraph import *
from processor import *


@sstlib('memHierarchy.MemNIC')
@port('port', 'simpleNet')
class MemNIC(Device):
    """MemNIC."""

    def __init__(self, name: str, model: str, attr: dict = None) -> 'Device':
        """Initialize with a model describing where this is on the NoC."""
        parameters = {
            "network_bw": "25GB/s"
        }
        if model == 'Cache':
            parameters.update({
                "group": 1,
                "destinations": "2,3"  # DirCtrl, SHMEMNIC
            })
        elif model == 'DirCtrl':
            parameters.update({
                "group": 2,
                "sources": "1,3"  # Cache, SHMEMNIC
            })
        elif model == 'SHMEMNIC':
            parameters.update({
                "group": 3,
                "sources": "1",  # Cache
                "destinations": "2"  # DirCtrl
            })
        else:
            return None

        if attr is not None:
            parameters.update(attr)
        super().__init__(name, attr=parameters)


@sstlib('merlin.hr_router')
@port('port', 'simpleNet', None, False, '#')
class Router(Device):
    """Router."""

    def __init__(self, name: str, model: str, id: int = 0, ports: int = 1,
                 attr: dict = None) -> 'Device':
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


@sstlib('merlin.singlerouter')
class SingleRouter(Device):
    """Single Router Topology."""

    def __init__(self, name: str, attr: dict = None) -> 'Device':
        """Initialize."""
        super().__init__(name, attr=attr)


@sstlib('memHierarchy.DirectoryController')
@port('direct_link', 'simpleMem', required=False)
class DirectoryController(Device):
    """DirectoryController."""

    def __init__(self, name: str, attr: dict = None) -> 'Device':
        """Initialize."""
        parameters = {
            "coherence_protocol": "MESI",
            "entry_cache_size": 1024,
            "addr_range_start": 0x0,
            "addr_range_end": 0x7fffffff
        }
        if attr is not None:
            parameters.update(attr)
        super().__init__(name, attr=parameters)


@sstlib('memHierarchy.MemController')
@port('direct_link', 'simpleMem', required=False)
class MemController(Device):
    """MemController."""

    def __init__(self, name: str, attr: dict = None) -> 'Device':
        """Initialize."""
        parameters = {
            "clock": "1GHz",
            "backend.mem_size": "4GiB",
            "backing": "malloc",
            "addr_range_start": 0x0,
            "addr_range_end": 0x7fffffff
        }
        if attr is not None:
            parameters.update(attr)
        super().__init__(name, attr=parameters)


@sstlib('memHierarchy.simpleMem')
class simpleMem(Device):
    """simpleMem."""

    def __init__(self, name: str, attr: dict = None) -> 'Device':
        """Initialize."""
        parameters = {
            "mem_size": "2GiB",
            "access_time": "1 ns"
        }
        if attr is not None:
            parameters.update(attr)
        super().__init__(name, attr=parameters)


@sstlib('rdmaNic.nic')
@port('port', 'simpleNet', None, False, '#')
class RDMA_NIC(Device):
    """RDMA_NIC."""

    def __init__(self, name: str, id: int = 0, nodes: int = 2,
                 cores: int = 1, attr: dict = None) -> 'Device':
        """
        Initialize using various simulation parameters.

        Need to know the number of processing elements (cores) per node.
        Also need the total number of nodes in the system.
        """
        parameters = {
            "clock": "8GHz",
            "maxPendingCmds": 128,
            "maxMemReqs": 256,
            "maxCmdQSize": 128,
            "cache_line_size": 64,
            'baseAddr': 0x80000000,
            'cmdQSize': 64,
            'pesPerNode': cores,
            'nicId': id,
            'numNodes': nodes
        }
        if attr is not None:
            parameters.update(attr)
        super().__init__(name, attr=parameters)


@sstlib('merlin.linkcontrol')
@port('rtr_port', 'simpleNet')
class LinkControl(Device):
    """LinkControl."""

    def __init__(self, name: str, attr: dict = None) -> 'Device':
        """Initialize."""
        parameters = {
            "link_bw": "16GB/s",
            "input_buf_size": "14KB",
            "output_buf_size": "14KB"
        }
        if attr is not None:
            parameters.update(attr)
        super().__init__(name, attr=parameters)


@assembly
@port('network', 'simpleNet')
class Server(Device):
    """Server constructed of a processor and some memory."""

    def __init__(self, name: str, node: int = 0,
                 racks: int = 2, nodes: int = 2, cores: int = 1,
                 attr: dict = None) -> 'Device':
        """Store our name and use number of cores as the model type."""
        super().__init__(name, f"{cores}Core", attr)
        self.attr['node'] = node
        self.attr['racks'] = racks
        self.attr['nodes'] = nodes
        self.attr['cores'] = cores

    def expand(self) -> 'DeviceGraph':
        """Expand the server into its components."""
        graph = DeviceGraph()  # initialize a Device Graph

        # Setup the NoC first so we can connect the Processors to it
        # Device names created by an assembly will automatically have the
        # assembly name prefixed to the name provided.
        NoC = Router("NoC", 'NoC', 0, self.attr['cores'] + 2)
        NoC_topo = SingleRouter("NoC_topo")
        NoC.add_subcomponent(NoC_topo, 'topology')

        # Generate the appropriate number of Processors and L2 Caches
        for core in range(self.attr['cores']):
            cpu = Processor(f"CPU{core}", core, self.attr['cores'])

            L2 = Cache(f"CPU{core}_L2", 'L2')
            L1_to_L2 = MemLink(f"CPU{core}_L1_to_L2")
            L2_to_mem = MemNIC(f"CPU{core}_L1_to_mem", 'Cache')
            L2.add_subcomponent(L1_to_L2, 'cpulink')
            L2.add_subcomponent(L2_to_mem, 'memlink')

            graph.link(cpu.low_network(0), L1_to_L2.port('port'), '1ns')
            graph.link(L2_to_mem.port('port'), NoC.port('port', core), '1ns')

        # Setup the main memory with controllers
        dirctrl = DirectoryController("DirectoryController")
        dir_to_mem = MemLink("dir_to_mem")
        dirNIC = MemNIC("dirNIC", 'DirCtrl')
        dirctrl.add_subcomponent(dir_to_mem, 'memlink')
        dirctrl.add_subcomponent(dirNIC, 'cpulink')

        memctrl = MemController("MemController")
        mem_to_dir = MemLink("mem_to_dir")
        memory = simpleMem("simpleMem")
        memctrl.add_subcomponent(mem_to_dir, 'cpulink')
        memctrl.add_subcomponent(memory, 'backend')

        # Initialize the RDMA_NIC and its interfaces
        nic = RDMA_NIC("NIC", self.attr['node'],
                       self.attr['racks'] * self.attr['nodes'],
                       self.attr['cores'])
        mmioIf = memInterface("MMIO_IF")
        mmioNIC = MemNIC("MMIO_NIC", 'SHMEMNIC')
        netLink = LinkControl("netLink")
        mmioIf.add_subcomponent(mmioNIC, 'memlink')
        nic.add_subcomponent(mmioIf, 'mmio')
        nic.add_subcomponent(netLink, 'rtrLink')

        graph.link(NoC.port('port', None), dirNIC.port('port'), '1ns')
        graph.link(NoC.port('port', None), mmioNIC.port('port'), '10ns')
        graph.link(dir_to_mem.port('port'), mem_to_dir.port('port'), '1ns')

        # Our external link is through the RDMA_NIC
        # Generally you don't want to put latency on the links to assembly
        # ports (ex: self.port) and allow whatever uses the assembly to
        # specify latency for the connection (it will get ignored anyway)
        graph.link(netLink.port('rtr_port'), self.network)
        return graph
