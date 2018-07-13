import pylxd
from prometheus_client import start_http_server, Gauge, write_to_textfile, CollectorRegistry
import time
import multiprocessing
from psutil import virtual_memory

def process_metrics(g_cpu,g_mem_usage,g_mem_usage_peak,g_swap_usage,g_swap_usage_peak,\
                    g_process_count,g_disk_usage,g_container_pid,g_network_usage,g_container_status,\
                    g_total_cpu,g_total_mem):
    time.sleep(1)
    client = pylxd.Client()
    containers = client.containers.all()
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
                container_name = container.name
                container_status = 1
                network = container.state().network
                g_disk_uage.labels(container_name, 'disk_usage').set(disk_usage)
                for interface, value in network.iteritems():
                    for operation, value in value['counters'].iteritems():
                        g_network_usage.labels(container_name, 'container_pid',interface,operation).set(value)


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

            total_cpu = multiprocessing.cpu_count()
            total_mem = virtual_memory().total

            g_total_cpu.labels('total_cpu').set(total_cpu)
            g_total_mem.labels('total_mem').set(total_mem)
            g_cpu.labels(container_name,'cpu_usage').set(cpu_usage)
            g_mem_usage.labels(container_name, 'mem_usage').set(mem_usage)
            g_mem_usage_peak.labels(container_name, 'mem_usage_peak').set(mem_usage_peak)
            g_swap_usage.labels(container_name, 'swap_usage').set(swap_usage)
            g_swap_usage_peak.labels(container_name, 'swap_usage_peak').set(swap_usage_peak)
            g_process_count.labels(container_name, 'process_count').set(process_count)
            g_container_pid.labels(container_name,'container_pid').set(container_pid)
            g_container_status.labels(container_name,'container_status').set(container_status)
        except:
            pass

if __name__ == '__main__':
    # Start up the server to expose the metrics.
    registry = CollectorRegistry()
    start_http_server(8000,registry=registry)

    g_cpu = Gauge('lxc_container_cpu_usage', 'Usage of lxc cpu', labelnames=['container_name','metrictype'], registry=registry)
    g_mem_usage = Gauge('lxc_container_mem_usage', 'Usage of lxc Memory', labelnames=['container_name','metrictype'], registry=registry)
    g_mem_usage_peak = Gauge('lxc_container_mem_usage_peak', 'Usage of lxc Memory Peak', labelnames=['container_name','metrictype'], registry=registry)
    g_swap_usage = Gauge('lxc_container_swap_usage', 'Usage of SWAP', labelnames=['container_name','metrictype'], registry=registry)
    g_swap_usage_peak = Gauge('lxc_container_swap_usage_peak', 'Usage of SWAP Peak', labelnames=['container_name','metrictype'], registry=registry)
    g_process_count = Gauge('lxc_container_process_count', 'Number of Process in Container', labelnames=['container_name','metrictype'], registry=registry)
    g_disk_uage = Gauge('lxc_container_disk_usage', 'Root Filesystem Space Usage', labelnames=['container_name','metrictype'], registry=registry)
    g_container_pid = Gauge('lxc_container_container_pid', 'PID of LXC Container', labelnames=['container_name','metrictype'], registry=registry)
    g_network_usage = Gauge('lxc_container_container_network_usage', 'Network Usage By Container', labelnames=['container_name','metrictype','interface','operation'], registry=registry)
    g_container_status = Gauge('lxc_container_container_status', 'Container status', labelnames=['container_name','metrictype'], registry=registry)
    g_total_cpu = Gauge('lxc_container_host_cpu_total', 'Usage of lxc cpu', labelnames=['metrictype'], registry=registry)
    g_total_mem = Gauge('lxc_container_host_mem_total', 'Usage of lxc cpu', labelnames=['metrictype'], registry=registry)

    while True:

        process_metrics(g_cpu,g_mem_usage,g_mem_usage_peak,g_swap_usage,g_swap_usage_peak,\
                        g_process_count,g_disk_uage,g_container_pid,g_network_usage,g_container_status,\
                        g_total_cpu,g_total_mem)
        write_to_textfile('collect.prom', registry)

