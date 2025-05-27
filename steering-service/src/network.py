import os
import re
import subprocess
import threading


units = {
    'B': 1,
    'kB': 1e3,
    'MB': 1e6,
    'GB': 1e9,
    'TB': 1e12,
    'KiB': 1024,
    'MiB': 1024**2,
    'GiB': 1024**3,
    'TiB': 1024**4
}


class NetworkControl:

    def __init__(self):
        self.lock = threading.Lock()

        self.interface   = 'eth0'
        self.latency     = 0  
        self.bandwidth   = 0
        self.packet_loss = 0


    def get_current_conditions(self):
        with self.lock:
            return {
                'latency': 100,     # in milliseconds
                'bandwidth': 1000,  # in kbps
                'packet_loss': 0.01 # as a fraction
            }


    def update_conditions(self, latency=None, bandwidth=None, packet_loss=None):
        with self.lock:
            if latency is not None:
                self.latency = latency
            if bandwidth is not None:
                self.bandwidth = bandwidth
            if packet_loss is not None:
                self.packet_loss = packet_loss
            
            self.apply_tc_rules()


    def apply_tc_rules(self):
        try:
            subprocess.run([
                "tc", "qdisc", "del", 
                "dev", self.interface, 
                "root"
            ], check=True)

            subprocess.run([
                "tc", "qdisc", "add",
                "dev", self.interface,
                "root", "netem",
                f"delay {self.latency}ms",
                f"loss {self.packet_loss * 100}%"
            ], check=True)

        except subprocess.CalledProcessError as e:
            print(f"Error applying tc rules: {e}")


    def parse_mem(self, val):
        match = re.match(
            r'([\d\.]+)\s*([A-Za-z]+)', 
            val.strip()
        )

        if match:
            num, unit = match.groups()
            return float(num) * units.get(unit, 1)

        return 0.0

    def parse_docker_stats(self):
        result = subprocess.run(
            [
                "docker", "stats", "--no-stream", "--format",
                f"{{.Container}}\t"
                f"{{.Name}}\t"
                f"{{.CPUPerc}}\t"
                f"{{.MemUsage}}\t"
                f"{{.MemPerc}}\t"
                f"{{.NetIO}}\t"
                f"{{.BlockIO}}\t"
                f"{{.PIDs}}"
            ],
            capture_output=True,
            text=True
        )
        lines = result.stdout.strip().split('\n')

        stats = {}
        for line in lines:
            fields = line.split('\t')
            if len(fields) == 8:
                container_id, name, cpu, mem_usage, mem_perc, net_io, block_io, pids = fields

                mem_used, mem_limit = self.parse_mem_pair(mem_usage)
                net_in, net_out     = self.parse_io_pair(net_io)
                block_in, block_out = self.parse_io_pair(block_io)
                
                stats[name] = {
                    "container_id": container_id,
                    "cpu":       self.parse_percentage(cpu),
                    "mem_usage": mem_used,
                    "mem_limit": mem_limit,
                    "mem_perc":  self.parse_percentage(mem_perc),
                    "net_in":    net_in,
                    "net_out":   net_out,
                    "block_in":  block_in,
                    "block_out": block_out,
                    "pids":      int(pids)
                }
        return stats

    def parse_percentage(self, val):
        try:
            return float(val.strip().replace('%', ''))
        except Exception:
            return 0.0

    def parse_mem_pair(self, val):
        parts = val.split('/')
        
        if len(parts) == 2:
            return (
                self.parse_mem(parts[0]), 
                self.parse_mem(parts[1])
            )
        
        return (
            self.parse_mem(val), 
            0.0
        )

    def parse_io_pair(self, val):
        parts = val.split('/')
        
        if len(parts) == 2:
            return (
                self.parse_mem(parts[0]), 
                self.parse_mem(parts[1])
            )
        
        return (
            self.parse_mem(val), 
            0.0
        )

network = NetworkControl()


if __name__ == "__main__":
    import pprint
    pprint.pprint(network.parse_docker_stats())
    pprint.pprint(network.parse_docker_stats_2())