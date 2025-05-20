from flask import Flask
from flask import request
from flask import jsonify
from flask_cors import CORS, cross_origin
import randomname

from dash_parser import DashParser
from monitor import monitor
from network import network
from selector import selector
from ai_server_selector import AIServerSelector
from urllib.parse import urlparse, parse_qs, urlencode, urlunparse

# DEFINES
STEERING_ADDR = 'steering-service'
STEERING_PORT = 30500
BASE_URI      = f'https://{STEERING_ADDR}:{STEERING_PORT}'


# Create instances of the parsers and the container monitor
dash_parser  = DashParser()

# selector = AIServerSelector()


class Main:
    def __init__(self):
        """
        """
        self.app = Flask(__name__)
        CORS(self.app)

        @self.app.route('/<name>', methods=['GET'])
        @cross_origin()
        def do_remote_steering(name):
            uid = request.args.get('_DASH_uid', default=randomname.get_name(), type=str)
            tar = request.args.get('_DASH_pathway', default='', type=str)
            thr = request.args.get('_DASH_throughput', default=0.0, type=float)
            adr = request.remote_addr

            print("\033[92mRequest received:", request.url, "\033[0m")

            nodes = monitor.getNodes('ip_address')
            net = None # network.get_current_conditions()

            session = selector.solver(**{
                'uid': uid,
                'adr': adr,
                'tar': tar,
                'thr': thr,
                'net': net,

            })

            data = dash_parser.build(
                target  = tar,
                nodes   = nodes,
                uri     = BASE_URI,
                request = request
            )

            # Add session uid to the RELOAD-URI if present
            data['RELOAD-URI'] = f"{data['RELOAD-URI']}?_DASH_uid={uid}"

            return jsonify(data), 200


    def run(self):
        ssl_context = ('steering-service/certs/steering-service.pem', 'steering-service/certs/steering-service-key.pem')
        self.app.run(host=STEERING_ADDR, port=STEERING_PORT, debug=True, ssl_context=ssl_context)

# END CLASS.


# MAIN
if __name__ == '__main__':

    monitor.start_collecting()

    main = Main()
    main.run()
# EOF
