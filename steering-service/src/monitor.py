import time
import docker
import threading


# CLASS
class ContainerMonitor:
    def __init__(self):
        self.client = docker.from_env()
        self.con_status = {}
        self.interval = 2


    def start_collecting(self):
        self.collect_stats()

        # Schedule the next collection
        threading.Timer(self.interval, self.start_collecting).start()


    def collect_stats(self):
        try:
            cons = self.client.containers.list(all=True)

            for con in cons:
                self._process_container(con)        

        except Exception as e:
            self._log_error("Failed to list Docker containers", e)        


    def _process_container(self, con) -> None:
        name = con.name
        
        if con.status != 'running':
            if con.name in self.con_status:
                del self.con_status[con.name]
                return

        # Get container statistics
        stats = con.stats(stream=False)

        # Extract network information
        ip_address = self._extract_container_ip(con)
        
        # Get previous stats for rate calculations
        prev_stats = self._get_previous_stats(name)

        # Calculate current metrics
        con_metrics = self._calculate_metrics(stats, prev_stats, ip_address)
        
        # Store metrics with rolling window
        self._store_metrics(name, con_metrics)


    def _extract_container_ip(self, container) -> str:
        try:
            networks = container.attrs['NetworkSettings']['Networks']

            if 'video-streaming_default' in networks:
                return networks['video-streaming_default'].get('IPAddress', 'N/A')
            elif networks:
                return next(
                    iter(networks.values())
                ).get('IPAddress', 'N/A')
            return 'N/A'
        except (KeyError, TypeError):
            return 'N/A'


    def _get_previous_stats(self, name: str) -> dict:
        container_history = self.con_status.get(
            name, 
            []
        )
        
        if container_history:
            return container_history[-1]
        return {}
    

    def _calculate_metrics(self, stats: dict, prev_stats: dict, ip_address: str) -> dict:
        try:
            # Safely calculate CPU usage percentage
            cpu_usage = self._calculate_cpu_usage(stats)
            
            # Safely calculate memory usage percentage  
            memory_usage = self._calculate_memory_usage(stats)
            
            # Get network metrics (handle missing eth0 interface)
            network_metrics = self._get_network_metrics(stats, prev_stats)
            
            return {
                'cpu_usage_percent':     cpu_usage,
                'memory_usage_percent':  memory_usage,
                'network_rx_bytes':      network_metrics['rx_bytes'],
                'network_tx_bytes':      network_metrics['tx_bytes'],
                'network_rx_rate_bytes': network_metrics['rx_rate'],
                'network_tx_rate_bytes': network_metrics['tx_rate'],
                'ip_address':            ip_address,
                'timestamp':             time.time(),  # Add timestamp for better tracking
            }
        
        except Exception as e:
            self._log_error(f"Failed to calculate container metrics", e)
            return self._get_default_metrics(ip_address)
    

    def _get_default_metrics(self, ip_address: str) -> dict:
        return {
            'cpu_usage_percent':     0.0,
            'memory_usage_percent':  0.0,
            'network_rx_bytes':      0,
            'network_tx_bytes':      0,
            'network_rx_rate_bytes': 0,
            'network_tx_rate_bytes': 0,
            'ip_address':            ip_address,
            'timestamp':             time.time(),
        }


    def _store_metrics(self, name: str, metrics: dict) -> None:
        if name not in self.con_status:
            self.con_status[name] = []
        
        self.con_status[name].append(metrics)
        
        # Maintain rolling window of last 10 metrics
        max_history = getattr(self, 'max_metrics_history', 10)

        # Ensure we don't exceed the maximum history size
        self.con_status[name] = self.con_status[name][-max_history:]


    def _calculate_cpu_usage(self, stats: dict) -> float:
        try:
            cpu_stats     = stats['cpu_stats']
            cpu_usage     = cpu_stats['cpu_usage']['total_usage']
            sys_cpu_usage = cpu_stats['system_cpu_usage']
            
            if sys_cpu_usage == 0:
                return 0.0
                
            # Get number of CPU cores for more accurate calculation
            cpu_count     = cpu_stats.get('online_cpus', 1)
            usage_percent = (cpu_usage / sys_cpu_usage) * cpu_count * 100
            
            return min(usage_percent, 100.0)
        
        except (
            KeyError,
            ZeroDivisionError,
            TypeError
        ):
            return 0.0


    def _calculate_memory_usage(self, stats: dict) -> float:
        try:
            memory_stats = stats['memory_stats']
            usage = memory_stats['usage']
            limit = memory_stats['limit']
            
            if limit == 0:
                return 0.0
                
            return (usage / limit) * 100
        except (
            KeyError, 
            ZeroDivisionError, 
            TypeError
        ):
            return 0.0


    def _get_network_metrics(self, stats: dict, prev_stats: dict) -> dict:
        default_metrics = {
            'rx_bytes': 0,
            'tx_bytes': 0, 
            'rx_rate': 0,
            'tx_rate': 0
        }
        
        try:
            networks = stats.get('networks', {})
            
            # Try eth0 first, then any available interface
            inf_data = networks.get('eth0')
            if not inf_data and networks:
                inf_data = next(iter(networks.values()))
                
            if not inf_data:
                return default_metrics
                
            cur_rx = inf_data.get('rx_bytes', 0)
            cur_tx = inf_data.get('tx_bytes', 0)
            
            # Calculate rates
            prev_rx = prev_stats.get('network_rx_bytes', 0)
            prev_tx = prev_stats.get('network_tx_bytes', 0)
            
            return {
                'rx_bytes': cur_rx,
                'tx_bytes': cur_tx,
                'rx_rate': max(0, cur_rx - prev_rx),  # Ensure non-negative
                'tx_rate': max(0, cur_tx - prev_tx),
            }
        except (KeyError, TypeError):
            return default_metrics


    def getNodes(self, metric='tx_bytes'):
        return [(name, stat[-1]['ip_address']) for name, stat in self.con_status.items()]
    
    def get_nodes(self, metric='tx_bytes'):
        return [
            (name, stat[-1]['ip_address']) for name, stat in self.con_status.items()
        ]
    

    def get_cpu_usage(self, name: str) -> float:
        if name in self.con_status and self.con_status[name]:
            return self.con_status[name][-1]['cpu_usage_percent']
        return 0.0


    def get_memory_usage(self, name: str) -> float:
        if name in self.con_status and self.con_status[name]:
            return self.con_status[name][-1]['memory_usage_percent']
        return 0.0
    

    def _log_error(self, msg: str, exc: Exception) -> None:
        import logging

        logger = logging.getLogger(__name__)
        logger.error(f"{msg}: {exc}", exc_info=True)
        
        if not logger.handlers:
            print(f"ERROR - {msg}: {exc}")

    def print_stats(self):
        for name, stats_list in self.con_status.items():
            print(f"Stats for {name}:")
            if stats_list:
                stats = stats_list[-1]
                print(f"  CPU Usage: {stats['cpu_usage']}")
                print(f"  Memory Usage: {stats['mem_usage']}")
                print(f"  Network Input: {stats['rx_bytes']}")
                print(f"  Network Output: {stats['tx_bytes']}")
                print(f"  Rate Network Input: {stats['rate_rx_bytes']}")
                print(f"  Rate Network Output: {stats['rate_tx_bytes']}")
                print(f"  Metrics size: {len(stats_list)}")
                print(f"  IP address: {stats['ip_address']}")

# END CLASS.

monitor = ContainerMonitor()

# MAIN
if __name__ == '__main__':
    main = ContainerMonitor()
    main.start_collecting()
# EOF