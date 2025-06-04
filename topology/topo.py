import os
import time
import json

from multiprocessing import Process

from containernet.cli import CLI
from containernet.net import Containernet
from containernet.term import makeTerm

from mininet.node import OVSKernelSwitch, OVSSwitch, Host, CPULimitedHost
from mininet.node import Controller
from mininet.topolib import TreeNet
from mininet.link import TCLink

import numpy as np
import networkx as nx
import matplotlib.pyplot as plt


from mobility import MobilitySwitch, NetworkGraph
from common import poisson_per_time, zipf

config_file = f'{os.getcwd()}/topology/config.json'
with open(config_file, 'r') as f:
    config = json.load(f)

total_videos = config.get('total_videos', 10)
total_time   = config.get('total_time', 10)
alpha        = config.get('alpha', 2.0)
arr_rate     = config.get('arr_rate', 10)
seed         = config.get('seed', 0)
station = []


# display = Display()
# display.start()

def topology():
    n_cdns = 3
    n_users = 1 # arr_rate*total_time

    net = Containernet()

    print("*** Creating nodes")
    cdns = [
        net.addDocker(
            'cdn%d' % (i+1),
            ip='10.0.1.%d' % (i+1),
            mac='00:00:00:00:01:%02d' % (i+1),
            dimage="cloud/apache",
            volumes=[
                f'/home/tutorial/Documents/content-steering-tutorial/dataset:/usr/local/apache2/htdocs/'
            ],
        ) for i in range(n_cdns)
    ]

    cdn_sws = [
        net.addSwitch(
            'cdn-sw%d' % (i+1), 
            cls=MobilitySwitch
        ) for i in range(n_cdns)
    ]

    stations = [
        net.addHost(
            name='sta%d' % (i+1),
            mac='00:00:00:00:00:%02d' % (i+1),
            ip='10.0.0.%d/16' % (i+1)
        ) for i in range(n_users)
    ]

    stations_sws = [
        net.addSwitch(
            'sta-sw%d' % (i+1), 
            cls=MobilitySwitch
        ) for i in range(n_users)
    ]

    print("*** Creating links")
    
    for i in range(n_cdns):
        net.addLink(cdns[i], cdn_sws[i], delay='40ms')

    for i in range(n_cdns):
        for j in range(n_users):
            net.addLink(cdn_sws[i], stations_sws[j], delay='10ms')

    for i in range(n_users):
        net.addLink(stations[i], stations_sws[i], delay='10ms')

    c0 = net.addController(
        name='c0',
        controller=Controller,
        protocol='tcp',
        port=6653
    )

    print("*** Starting network")
    net.build()
    net.addNAT(name='nat0', linkTo='cdn-sw', ip='10.0.0.100').configDefault()

    c0.start()
    for i in range(n_cdns): cdn_sws[i].start([c0])
    for i in range(n_users): stations_sws[i].start([c0])

    return net, n_cdns, n_users, cdns, cdn_sws, stations, stations_sws


def netcon(mod, nett, host):
    print(str(mod) + "-" + str(nett) + "  traces.............")
    os.system('./topology/5G/topo.sh')


def planner():
    print(" planner.............")
    os.system(f'python services/planner/online/main.py --seed={seed} > planner.out 2>&1 ')


def monitor(sws):
    print(" monitor.............")
    os.system(f'python topology/5G/node_monitor.py > monitor.out 2>&1 &')
    os.system(f'python topology/5G/network_monitor.py {len(sws)}')


def start_stations(sts):
    # available_stations = [(st.name, st) for st in sts]
    # busy_sts = []
    
    terms = []
    arrivals = poisson_per_time(total_time, arr_rate)
    videos_requests = zipf(total_videos, len(arrivals), alpha)

    print(f'Arrivals: {arrivals}')
    print(f'Videos requests: {videos_requests}')
    
    for arrival, video, st in zip(arrivals, videos_requests, sts):
        time.sleep(arrival)

        cmd = ' '.join([
            f'google-chrome', 
            f'http://cdn1/player/index.html?video=4',
            # f'http://cdn1/player/index.html?video={video}',
            # f'--headless=new',
            f'--incognito',
            f'--no-sandbox',
            f'--disable-dev-shm-usage',
            f'--no-user-gesture-required',
            f'--disable-gpu',
            f'--disable-cache',
            f'--aggressive-cache-discard',
            f'--disk-cache-size=0',
            f'--new-window'
        ])
        
        # makeTerm returns a list [terminal, process]
        term = makeTerm(st, cmd=cmd)
        print(term)
        terms.append(term)
        
        print(f'Arrival {st.name} at {arrival} seconds')

    print("All stations finished.")


if __name__ == '__main__':

    os.makedirs(f'{os.getcwd()}/logs/{seed}', exist_ok=True)

    nett, n_cdns, n_users, cdns, cdn_sws, sts, sts_sws = topology()

    graph = NetworkGraph()

    for i in range(n_cdns):
        graph.add_connection(cdns[i], cdn_sws[i])

    for i in range(n_users):
        graph.add_connection(sts[i], sts_sws[i])


    for i in range(n_cdns):
        for j in range(n_users):
            graph.add_connection(cdn_sws[i], sts_sws[j])

    for i in range(n_users):
        graph.add_connection(sts_sws[i], sts[i])

    print("*** Network graph created.")

    # graph.visualize()
    graph.print_connections()

    for i in range(n_cdns):
        cdns[i].cmd('apachectl -D FOREGROUND &')

    print("Starting stations .......")
    p = Process(target=start_stations, args=(sts,))
    p.start()

    print("*** Running CLI ........")
    CLI(nett)

    # p.join()

    
    print("*** Stopping network.")
    nett.stop()

# display.stop()
