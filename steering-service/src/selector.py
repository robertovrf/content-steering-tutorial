import randomname

from datetime import datetime, timedelta


class Selector:
    def __init__(self):
        self.nodes = []
        self.sessions = {}

    def solver(self, **kwargs):
        uid = kwargs.get('uid', 'anonymous')
        adr = kwargs.get('adr', '0.0.0.0')
        tar = kwargs.get('tar', 'cloud')
        thr = kwargs.get('thr', 0.0)

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

        print(f"Session: {session}")

        self.sessions[uid] = session

        return {
            "uid": uid,
            "tar": tar,
            "thr": thr
        }

        # if thr > 0:
        #     thr = min(thr/1000, )


selector = Selector()