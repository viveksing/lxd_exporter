# Instructions for lxdprom.py sample script
Sample LXD Exporter for prometheus.io (Note: Do not run in Production!)

Works on Ubuntu 16.04 for lxd installed from feature branch
~~~
# apt install -t xenial-backports lxd lxd-client
# apt install python-minimal python-pip
~~~

Install Python Dependencies
~~~
pip install prometheus_client
pip install pylxd
pip install psutil
~~~

Clone Repository and run exporter
~~~
# git clone https://github.com/viveksing/lxd_exporter.git
# cd lxd_exporter
# python lxdprom.py
~~~

Listens on port 8000

Also Included LXD Grafana Dashboard in grafana-lxd.json 

# Instructions for lxdpromv2.py (Change Port Accordingly)
~~~
/usr/bin/python /usr/local/bin/lxd_exporter.py --port 18765
~~~

