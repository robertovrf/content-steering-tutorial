import randomname

from datetime import datetime, timedelta


from ai_server_selector import ai_selector
from network import network
from monitor import monitor

class Selector:
    def __init__(self):
        self.nodes    = []
        self.sessions = {}


    def solver(self, **kwargs):
        uid = kwargs.get('uid', 'anonymous')    # Unique identifier for the session
        adr = kwargs.get('adr', '0.0.0.0')      # Address of the client
        tar = kwargs.get('tar', 'cloud')        # Target pathway for the session
        thr = kwargs.get('thr', 0.0)            # Throughput for the session
        nos = kwargs.get('nos', [])               # List of nodes

        if uid not in self.sessions:
            session = {
                "start": datetime.now(),
                "end": datetime.now() + timedelta(seconds=30),
                "adr": adr,
                "tar": tar,
                "name": uid
            }
        else:
            session = self.sessions[uid]
            session["end"] = datetime.now() + timedelta(seconds=30)

        print(f"Session: {session}")

        nos = ai_selector.predict_best_server(
            network.get_current_conditions(),
            monitor.get_nodes('ip_address'),
        )

        self.sessions[uid] = session

        return {
            "uid": uid,
            "tar": tar,
            "thr": thr
        }, nos


selector = Selector()