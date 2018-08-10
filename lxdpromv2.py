import pylxd
import subprocess
from prometheus_client import start_http_server, Metric, REGISTRY
import time
import argparse
parser = argparse.ArgumentParser()
parser.add_argument('--port',help='Enter the port number to listen')
arguments = parser.parse_args()

#import multiprocessing
#from psutil import virtual_memory

SYMBOLS = {
    'customary'     : ('B', 'K', 'M', 'G', 'T', 'P', 'E', 'Z', 'Y'),
    'customary_ext' : ('byte', 'kilo', 'mega', 'giga', 'tera', 'peta', 'exa',
                       'zetta', 'iotta'),
    'iec'           : ('Bi', 'Ki', 'Mi', 'Gi', 'Ti', 'Pi', 'Ei', 'Zi', 'Yi'),
    'iec_ext'       : ('byte', 'kibi', 'mebi', 'gibi', 'tebi', 'pebi', 'exbi',
                       'zebi', 'yobi'),
}

def human2bytes(s):
    """
    Attempts to guess the string format based on default symbols
    set and return the corresponding bytes as an integer.
    When unable to recognize the format ValueError is raised.

      >>> human2bytes('0 B')
      0
      >>> human2bytes('1 K')
      1024
      >>> human2bytes('1 M')
      1048576
      >>> human2bytes('1 Gi')
      1073741824
      >>> human2bytes('1 tera')
      1099511627776

      >>> human2bytes('0.5kilo')
      512
      >>> human2bytes('0.1  byte')
      0
      >>> human2bytes('1 k')  # k is an alias for K
      1024
      >>> human2bytes('12 foo')
      Traceback (most recent call last):
          ...
      ValueError: can't interpret '12 foo'
    """
    init = s
    num = ""
    while s and s[0:1].isdigit() or s[0:1] == '.':
        num += s[0]
        s = s[1:]
    num = float(num)
    letter = s.strip()
    for name, sset in SYMBOLS.items():
        if letter in sset:
            break
    else:
        if letter == 'k':
            # treat 'k' as an alias for 'K' as per: http://goo.gl/kTQMs
            sset = SYMBOLS['customary']
            letter = letter.upper()
        else:
            raise ValueError("can't interpret %r" % init)
    prefix = {sset[0]:1}
    for i, s in enumerate(sset[1:]):
        prefix[s] = 1 << (i+1)*10
    return int(num * prefix[letter])

def get_zfs_details():
    zfs_connect = subprocess.Popen('zfs list -t all | head -n 2 | grep -v NAME',shell=True,stdout=subprocess.PIPE)

    zfs_connect.wait()

    zfs_details_str = zfs_connect.stdout.read()
    zfs_details_array = zfs_details_str.split()

    zfs_used = human2bytes(zfs_details_array[1])
    zfs_available = human2bytes(zfs_details_array[2])

    details = list()
    details.append(zfs_used)
    details.append(zfs_available)
    return  details

class lxdcollector(object):
    def __init__(self,client):
        self.client = client

    def collect(self):

        containers = self.client.containers.all()

        metric_cpu = Metric('lxd_container_cpu_usage', 'LXD Container CPU Usage', 'gauge')
        metric_mem = Metric('lxd_container_mem_usage', 'LXD Container Memory Usage', 'gauge')
        metric_mem_usage_peak = Metric('lxd_container_mem_usage_peak', 'LXD Container Memory Usage Peak', 'gauge')
        metric_swap_usage = Metric('lxd_container_swap_usage', 'LXD Container Swap Usage', 'gauge')
        metric_swap_usage_peak = Metric('lxd_container_swap_usage_peak', 'LXD Container Swap Usage Peak', 'gauge')
        metric_process_count = Metric('lxd_container_process_count', 'LXD Container Process Count', 'gauge')
        metric_disk_usage = Metric('lxd_container_disk_usage', 'LXD Container Disk Usage', 'gauge')
        metric_container_pid = Metric('lxd_container_pid', 'LXD Container PID', 'gauge')
        metric_container_running_status = Metric('lxd_container_running_status', 'LXD container Running Status', 'gauge')
        metric_network_usage = Metric('lxd_container_network_usage', 'LXD Container Network Usage', 'gauge')
        metric_network_address = Metric('lxd_container_interface_ip', 'LXD Container IP addresses', 'gauge')

        zfs_used_space , zfs_free_space = get_zfs_details()

        metric_zfs_used_space = Metric('lxd_zfs_used_space', 'LXD Host Zfs Used Space', 'gauge')
        metric_zfs_free_space = Metric('lxd_zfs_free_space', 'LXD Host Zfs Free Space', 'gauge')
        metric_zfs_free_space.add_sample('lxd_zfs_free_space', value=zfs_free_space,labels={})
        metric_zfs_used_space.add_sample('lxd_zfs_used_space',value=zfs_used_space,labels={})

#        total_cpu = multiprocessing.cpu_count()
#        total_mem = virtual_memory().total
#
#        metric_total_cpu = Metric('lxd_host_cpu_count','LXD Host total cpu count','gauge')
#        metric_total_mem = Metric('lxd_host_total_mem','LXD Host total memory','gauge')
#        metric_total_cpu.add_sample('lxd_host_cpu_count',value=total_cpu,labels={})
#        metric_total_mem.add_sample('lxd_host_total_mem',value=total_mem,labels={})
#        yield metric_total_mem
#        yield metric_total_cpu
        yield  metric_zfs_used_space
        yield metric_zfs_free_space

        for container in containers:
            try:
                if container.state().status == 'Running':

                    cpu_usage = container.state().cpu['usage']
                    mem_usage = container.state().memory['usage']
                    mem_usage_peak = container.state().memory['usage_peak']
                    swap_usage = container.state().memory['swap_usage']
                    swap_usage_peak = container.state().memory['swap_usage']
                    process_count = container.state().processes
                    disk_usage = container.state().disk['root']['usage']
                    container_pid = container.state().pid
                    container_status = 1

                    container_name = container.name

                    network = container.state().network
                    for interface, value in network.iteritems():
                        for operation, value in value['counters'].iteritems():
                            metric_network_usage.add_sample('lxd_container_network_usage',
                                                                       value=value,
                                                                       labels={'container_name': container_name,'interface': interface,
                                                                               'operation': operation})
                    yield metric_network_usage

                    for interface, value in network.iteritems():
                        for value in value['addresses']:
                            metric_network_address.add_sample('lxd_container_interface_ip',
                                                                       value=1,
                                                                       labels={'container_name': container_name,'interface': interface,
                                                                               'address': value['address']})
                    yield metric_network_address
                else:
                    cpu_usage = 0
                    mem_usage = 0
                    mem_usage_peak = 0
                    swap_usage = 0
                    swap_usage_peak = 0
                    process_count = 0
                    disk_usage = 0
                    container_pid = -1
                    container_name = container.name
                    container_status = 0



            except Exception:
                pass
            finally:
                metric_cpu.add_sample('lxd_container_cpu_usage', value=cpu_usage,
                                      labels={'container_name': container_name})
                metric_mem.add_sample('lxd_container_mem_usage', value=mem_usage,
                                      labels={'container_name': container_name})

                metric_mem_usage_peak.add_sample('lxd_container_mem_usage_peak', value=mem_usage_peak,
                                                 labels={'container_name': container_name})

                metric_swap_usage.add_sample('lxd_container_swap_usage', value=swap_usage,
                                             labels={'container_name': container_name})

                metric_swap_usage_peak.add_sample('lxd_container_swap_usage_peak', value=swap_usage_peak,
                                                  labels={'container_name': container_name})

                metric_process_count.add_sample('lxd_container_process_count', value=process_count,
                                                labels={'container_name': container_name})

                metric_disk_usage.add_sample('lxd_container_disk_usage', value=disk_usage,
                                             labels={'container_name': container_name})

                metric_container_pid.add_sample('lxd_container_pid', value=container_pid,
                                                labels={'container_name': container_name})

                metric_container_running_status.add_sample('lxd_container_running_status', value=container_status,
                                                           labels={'container_name': container_name})

                yield metric_cpu
                yield metric_mem
                yield metric_mem_usage_peak
                yield metric_swap_usage
                yield metric_swap_usage_peak
                yield metric_process_count
                yield metric_disk_usage
                yield metric_container_pid
                yield metric_container_running_status

if __name__ == '__main__':
  client = pylxd.Client()
  if arguments.port :
      start_http_server(int(arguments.port))
  else:
      start_http_server(18000)
  collector = lxdcollector(client)
  REGISTRY.register(collector)

  while True:
      time.sleep(1)
