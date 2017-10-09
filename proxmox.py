import logging
from collections import namedtuple

from requests import ConnectionError
from pipelines import WikiPipeline as Pipe
from proxmoxer import ProxmoxAPI
from settings import PROXMOX_HOST, PROXMOX_USER, PROXMOX_PASS

logger = logging.getLogger(__name__)

# nodes and VMs models
Node = namedtuple('Node', ['mem_used', 'mem_total', 'cpu',
                           'root_hdd_used', 'root_hdd_total',
                           'name', 'local_total', 'local_available'])

VM = namedtuple('VM', ['mem', 'hdd', 'cpu', 'name', 'uptime',
                       'state', 'vmid', 'node', 'description'])


class Proxmox(object):

    # proxmox connection
    _conn = None

    # json pipe
    _pipe = Pipe()

    def __init__(self):
        # trying to setup connection
        self.setup_conn()

    def setup_conn(self):
        if self._conn is None:
            try:
                self._conn = ProxmoxAPI(host=PROXMOX_HOST,
                                        user='{}@pam'.format(PROXMOX_USER),
                                        password=PROXMOX_PASS,
                                        verify_ssl=False)
                logger.debug('connected to the "{}"'.format(PROXMOX_HOST))

            except ConnectionError as e:
                logger.critical('"{}" while connecting to the proxmox'.format(e))

    def _get_vm(self, vm):
        """combine VM model structure"""

        if vm.get('name'):
            hdd = self._bytes_to_gb(
                vm.get('maxdisk', 0))
            mem = self._bytes_to_gb(
                vm.get('maxmem', 0))
            return VM(name=vm['name'],
                      hdd=hdd,
                      mem=mem,
                      uptime=self._sec_to_days(vm['uptime']),
                      cpu=vm.get('maxcpu', 0),
                      vmid=vm['vmid'],
                      description=vm['description'],
                      node=vm['node'],
                      state=vm['status'])

    def _get_node(self, node):
        """combine Node model structure"""

        # get values in GB
        mem_used = self._bytes_to_gb(
            node.get('mem', 0))
        mem_total = self._bytes_to_gb(
            node.get('maxmem', 0))
        root_hdd_used = self._bytes_to_gb(
            node.get('disk', 0))
        root_hdd_total = self._bytes_to_gb(
            node.get('maxdisk', 0))
        local_total = self._bytes_to_gb(
            node.get('local_total', 0))
        local_avail = self._bytes_to_gb(
            node.get('local_avail', 0))

        return Node(name=node['node'],
                    mem_used=mem_used,
                    mem_total=mem_total,
                    root_hdd_used=root_hdd_used,
                    root_hdd_total=root_hdd_total,
                    local_total=local_total,
                    local_available=local_avail,
                    cpu=node.get('maxcpu', 0))

    @staticmethod
    def _bytes_to_gb(bytes_val):
        try:
            # 1073741824 bytes in 1 GB
            return round(
                int(bytes_val) / 1073741824, 2
            )
        except TypeError:
            return 0

    @staticmethod
    def _sec_to_days(sec):
        return int(sec / 86400.0)

    def _get_resources(self):
        try:
            return self._conn.cluster.resources.get()
        except Exception as e:
            logger.error('"{}" while getting resources'.format(e))

    def _vm_config(self, node, vmid):
        if node and vmid:
            url = '{}/qemu/{}/config'.format(node, vmid)
            vm = self._conn.nodes(url).get()
            descr = vm.get('description')
            if descr and not isinstance(descr, unicode):
                descr = descr.decode('utf-8')
            return {
                'description': descr or u''
            }

    def _node_config(self, node):
        if node:
            url = '{}/storage/local/status'.format(node)
            data = self._conn.nodes(url).get()
            return {
                'local_total': data.get('total', 0),
                'local_avail': data.get('avail', 0),
            }

    def get_stats(self):
        """get stats (VMs and nodes resources)"""
        results = {}
        # check proxmox connection
        if self._conn is None:
            logger.error('no connection found; exiting..')
            return

        # get cluster resources
        resources = self._get_resources()
        if not resources:
            logger.error('no resources found')

        # extract nodes and VMs from list of resources
        for item in resources or []:
            if item.get('vmid'):  # VM found (let's assume that only VM has 'vmid' attribute)
                additional_data = self._vm_config(item['node'], item['vmid'])
                if additional_data:
                    item.update(additional_data)
                    vm = self._get_vm(item)
                    if vm:
                        logger.debug('found "{}" VM from "{}" node'.format(vm.name, vm.node))
                        results.setdefault(vm.node, {})
                        results[vm.node].setdefault('vms', [])
                        results[vm.node]['vms'].append(vm)

            elif item.get('type') == 'node':  # node found
                additional_data = self._node_config(item['node'])
                if additional_data:
                    item.update(additional_data)
                    node = self._get_node(item)
                    if node:
                        logger.debug('found node: "{}"'.format(node.name))
                        results.setdefault(node.name, {})
                        results[node.name]['node_resources'] = node

        return self._pipe.process_items(results)

