import os
import subprocess
import threading


class NetworkControl:

    def __init__(self):
        self.lock = threading.Lock()

        self.interface = 'eth0'
        self.latency = 0  
        self.bandwidth = 0
        self.packet_loss = 0


    def get_current_conditions(self):
        with self.lock:
            # Simulate network conditions
            return {
                'latency': 100,  # in milliseconds
                'bandwidth': 1000,  # in kbps
                'packet_loss': 0.01  # as a fraction
            }
        
    def update_conditions(self, latency=None, bandwidth=None, packet_loss=None):
        with self.lock:
            # Update network conditions
            if latency is not None:
                self.latency = latency
            if bandwidth is not None:
                self.bandwidth = bandwidth
            if packet_loss is not None:
                self.packet_loss = packet_loss
            
            self.apply_tc_rules()


    def apply_tc_rules(self):
        # This function would apply the network conditions using tc commands
        # For example:
        try:
            subprocess.run(["tc", "qdisc", "del", "dev", "eth0", "root"], check=True)

            subprocess.run([
                "tc", "qdisc", "add", "dev", self.interface, "root", "netem",
                f"delay {self.latency}ms",
                f"loss {self.packet_loss * 100}%"
            ], check=True)
            
        except subprocess.CalledProcessError as e:
            print(f"Error applying tc rules: {e}")


network = NetworkControl()