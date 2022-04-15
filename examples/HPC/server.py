"""
Collection of PyDL Device wrappers around SST Components
"""
from PyDL.examples.HPC.processor import *
from PyDL import *


@sstlib('memHierarchy.MemNIC')
@port('port', Port.Single, 'simpleNet', Port.Required)
class MemNIC(Device):
    """MemNIC"""

    def __init__(self, name: str, attr: dict = None):
        """Initialize."""
        parameters = {
            "group": 1,
            "destinations": "2,3",  # DC, SHMEMNIC
            "network_bw": "25GB/s"
        }
        if attr is not None:
            parameters.update(attr)
        super().__init__(name, attr=parameters)


@sstlib('merlin.hr_router')
@port('port', Port.Multi, 'simpleNet', Port.Optional, '#')
class Router(Device):
    """Router"""

    def __init__(self, name: str, model: str, attr: dict = None):
        """Initialize with a model describing the number of ports."""
        parameters = {
            "id": 0
        }
        if model == 'NoC':
            parameters.update({
                "flit_size": "72B",
                "num_ports": 4,
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
                "flitSize": "8B",
                "input_buf_size": "14KB",
                "output_buf_size": "14KB"
            })
        else:
            return None

        if attr is not None:
            parameters.update(attr)
        super().__init__(name, attr=parameters)


@sstlib('merlin.singlerouter')
class SingleRouter(Device):
    """Single Router Topology"""

    def __init__(self, name: str, attr: dict = None):
        """Initialize."""
        super().__init__(name, attr=attr)


@sstlib('memHierarchy.DirectoryController')
@port('direct_link', Port.Single, 'simpleMem', Port.Required)
class DirectoryController(Device):
    """DirectoryController"""

    def __init__(self, name: str, attr: dict = None):
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
@port('direct_link', Port.Single, 'simpleMem', Port.Required)
class MemController(Device):
    """MemController"""

    def __init__(self, name: str, attr: dict = None):
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
    """simpleMem"""

    def __init__(self, name: str, attr: dict = None):
        """Initialize."""
        parameters = {
            "mem_size": "2GiB",
            "access_time": "1 ns"
        }
        if attr is not None:
            parameters.update(attr)
        super().__init__(name, attr=parameters)


@sstlib('rdmaNic.nic')
@port('port', Port.Multi, 'simpleNet', Port.Optional, '#')
class RDMA_NIC(Device):
    """RDMA_NIC"""

    def __init__(self, name: str, attr: dict = None):
        """Initialize with a model describing the number of ports."""
        parameters = {
            "clock": "8GHz",
            "maxPendingCmds": 128,
            "maxMemReqs": 256,
            "maxCmdQSize": 128,
            "cache_line_size": 64,
            'baseAddr': 0x80000000,
            'cmdQSize': 64,
            'pesPerNode': 1,
            # probably want to set these
            'nicId': 0,
            'numNodes': 2
        }
        if attr is not None:
            parameters.update(attr)
        super().__init__(name, attr=parameters)


@sstlib('merlin.linkcontrol')
@port('rtr_port', Port.Single, 'simpleNet', Port.Required)
class LinkControl(Device):
    """LinkControl"""

    def __init__(self, name: str, attr: dict = None):
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
@port('network', Port.Single, 'simpleNet', Port.Optional)
class Server(Device):
    """Server constructed of a processor and some memory."""

    def __init__(self, name: str, node: int, attr: dict = None):
        """Store our name"""
        super().__init__(name, attr=attr)
        self.attr['node'] = node

    def expand(self):
        """Expand the server into its components."""
        graph = DeviceGraph()  # initialize a Device Graph
        # add myself to the graph, useful if the assembly has ports
        graph.add(self)

        cpu = Processor(f"{self.name}.CPU", self.attr['node'], 0)

        L2 = Cache(f"{self.name}.L2", 'L2')
        L1_to_L2 = MemLink(f"{self.name}.L1_to_L2")
        L2_to_mem = MemNIC(f"{self.name}.L1_to_mem")
        L2.add_subcomponent(L1_to_L2, 'cpulink')
        L2.add_subcomponent(L2_to_mem, 'memlink')

        NoC = Router(f"{self.name}.NoC", 'NoC')
        NoC_topo = SingleRouter(f"{self.name}.NoC_topo")
        NoC.add_subcomponent(NoC_topo, 'topology')

        dirctrl = DirectoryController(f"{self.name}.DirectoryController")
        dir_to_mem = MemLink(f"{self.name}.dir_to_mem")
        dirNIC = MemNIC(f"{self.name}.dirNIC")
        dirctrl.add_subcomponent(dir_to_mem, 'memlink')
        dirctrl.add_subcomponent(dirNIC, 'cpulink')

        memctrl = MemController(f"{self.name}.MemController")
        mem_to_dir = MemLink(f"{self.name}.mem_to_dir")
        memory = simpleMem(f"{self.name}.simpleMem")
        memctrl.add_subcomponent(mem_to_dir, 'cpulink')
        memctrl.add_subcomponent(memory, 'backend')

        nic = RDMA_NIC(f"{self.name}.NIC")
        mmioIf = memInterface(f"{self.name}.MMIO_IF")
        mmioNIC = MemNIC(f"{self.name}.MMIO_NIC",
                         {"group": 3,
                          "sources": "1",  # L2
                          "destinations": "2"})  # DC
        netLink = LinkControl(f"{self.name}.netLink")
        mmioIf.add_subcomponent(mmioNIC, 'memlink')
        nic.add_subcomponent(mmioIf, 'mmio')
        nic.add_subcomponent(netLink, 'rtrLink')

        graph.add(cpu)
        graph.add(L2)
        graph.add(NoC)
        graph.add(dirctrl)
        graph.add(memctrl)
        graph.add(nic)

        graph.link(L2_to_mem.port('port'), NoC.port('port', 0), 1000)
        graph.link(NoC.port('port', 1), dirNIC.port('port'), 1000)
        graph.link(dir_to_mem.port('port'), mem_to_dir.port('port'), 1000)

        graph.link(cpu.low_network(0), L1_to_L2.port('port'), 1000)
        graph.link(NoC.port('port', 3), mmioNIC.port('port'), 10000)

        graph.link(netLink.port('rtr_port'), self.network, 10000)

        return graph
