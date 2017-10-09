from __future__ import print_function
import logging

from logger import setup_logger
from proxmox import Proxmox
from confluence import ConfluenceClient


setup_logger()
logging.getLogger("proxmoxer.core").setLevel(logging.ERROR)
logger = logging.getLogger(__name__)


if __name__ == '__main__':
    proxmox = Proxmox()
    client = ConfluenceClient()
    results = proxmox.get_stats()
    client.put_results(results)
    client.close()
