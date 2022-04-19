"""
Collection of PyDL Device wrappers around SST Components
"""
from processor import *
from PyDL import *


@sstlib('memHierarchy.MemNIC')
@port('port', Port.Single, 'simpleNet', Port.Required)
class MemNIC(Device):
    """MemNIC"""

    def __init__(self, name: str, model: str, attr: dict = None) -> 'Device':
        """Initialize."""
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
@port('port', Port.Multi, 'simpleNet', Port.Optional, '#')
class Router(Device):
    """Router"""

    def __init__(self, name: str, model: str, id: int = 0, ports: int = 1,
                 attr: dict = None) -> 'Device':
        """Initialize with a model describing the number of ports."""
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
    """Single Router Topology"""

    def __init__(self, name: str, attr: dict = None) -> 'Device':
        """Initialize."""
        super().__init__(name, attr=attr)


@sstlib('memHierarchy.DirectoryController')
@port('direct_link', Port.Single, 'simpleMem', Port.Required)
class DirectoryController(Device):
    """DirectoryController"""

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
@port('direct_link', Port.Single, 'simpleMem', Port.Required)
class MemController(Device):
    """MemController"""

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
    """simpleMem"""

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
@port('port', Port.Multi, 'simpleNet', Port.Optional, '#')
class RDMA_NIC(Device):
    """RDMA_NIC"""

    def __init__(self, name: str, id: int = 0, nodes: int = 2,
                 cores: int = 1, attr: dict = None) -> 'Device':
        """Initialize."""
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
@port('rtr_port', Port.Single, 'simpleNet', Port.Required)
class LinkControl(Device):
    """LinkControl"""

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
@port('network', Port.Single, 'simpleNet', Port.Optional)
class Server(Device):
    """Server constructed of a processor and some memory."""

    def __init__(self, name: str, node: int = 0,
                 racks: int = 2, nodes: int = 2, cores: int = 1,
                 attr: dict = None) -> 'Device':
        """Store our name and use number of cores as the model type"""
        super().__init__(name, f"{cores}Core", attr)
        self.attr['node'] = node
        self.attr['racks'] = racks
        self.attr['nodes'] = nodes
        self.attr['cores'] = cores

    def expand(self) -> 'DeviceGraph':
        """Expand the server into its components."""
        graph = DeviceGraph()  # initialize a Device Graph
        # add myself to the graph, useful if the assembly has ports
        graph.add(self)

        NoC = Router(f"{self.name}.NoC", 'NoC', 0, self.attr['cores'] + 2)
        NoC_topo = SingleRouter(f"{self.name}.NoC_topo")
        NoC.add_subcomponent(NoC_topo, 'topology')
        graph.add(NoC)

        for core in range(self.attr['cores']):
            cpu = Processor(f"{self.name}.CPU{core}", core, self.attr['cores'])

            L2 = Cache(f"{self.name}.CPU{core}_L2", 'L2')
            L1_to_L2 = MemLink(f"{self.name}.CPU{core}_L1_to_L2")
            L2_to_mem = MemNIC(f"{self.name}.CPU{core}_L1_to_mem", 'Cache')
            L2.add_subcomponent(L1_to_L2, 'cpulink')
            L2.add_subcomponent(L2_to_mem, 'memlink')

            graph.add(cpu)
            graph.add(L2)

            graph.link(cpu.low_network(0), L1_to_L2.port('port'), 1000)
            graph.link(L2_to_mem.port('port'), NoC.port('port', core), 1000)

        dirctrl = DirectoryController(f"{self.name}.DirectoryController")
        dir_to_mem = MemLink(f"{self.name}.dir_to_mem")
        dirNIC = MemNIC(f"{self.name}.dirNIC", 'DirCtrl')
        dirctrl.add_subcomponent(dir_to_mem, 'memlink')
        dirctrl.add_subcomponent(dirNIC, 'cpulink')

        memctrl = MemController(f"{self.name}.MemController")
        mem_to_dir = MemLink(f"{self.name}.mem_to_dir")
        memory = simpleMem(f"{self.name}.simpleMem")
        memctrl.add_subcomponent(mem_to_dir, 'cpulink')
        memctrl.add_subcomponent(memory, 'backend')

        nic = RDMA_NIC(f"{self.name}.NIC", self.attr['node'],
                       self.attr['racks'] * self.attr['nodes'],
                       self.attr['cores'])
        mmioIf = memInterface(f"{self.name}.MMIO_IF")
        mmioNIC = MemNIC(f"{self.name}.MMIO_NIC", 'SHMEMNIC')
        netLink = LinkControl(f"{self.name}.netLink")
        mmioIf.add_subcomponent(mmioNIC, 'memlink')
        nic.add_subcomponent(mmioIf, 'mmio')
        nic.add_subcomponent(netLink, 'rtrLink')

        graph.add(dirctrl)
        graph.add(memctrl)
        graph.add(nic)

        graph.link(NoC.port('port', None), dirNIC.port('port'), 1000)
        graph.link(NoC.port('port', None), mmioNIC.port('port'), 10000)
        graph.link(dir_to_mem.port('port'), mem_to_dir.port('port'), 1000)
        graph.link(netLink.port('rtr_port'), self.network, 10000)

        return graph
