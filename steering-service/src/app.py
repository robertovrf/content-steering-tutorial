import os
import randomname
import threading

from flask import Flask
from flask import request
from flask import jsonify
from flask_cors import CORS, cross_origin

from urllib.parse import urlparse, parse_qs, urlencode, urlunparse

from monitor import monitor
from network import network
from selector import selector
from dash_parser import parser


# DEFINES
STEERING_ADDR = 'steering-service'
STEERING_PORT = 30500
BASE_URI      = f'https://{STEERING_ADDR}:{STEERING_PORT}'


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

            _, nos = selector.solver(**{
                'uid': uid,
                'adr': adr,
                'tar': tar,
                'thr': thr,
            })

            data = parser.build(
                tar = tar,
                nos = [nos],
                uri = BASE_URI,
                req = request
            )
            data['RELOAD-URI'] = f"{data['RELOAD-URI']}?_DASH_uid={uid}"

            print("\033[93mResponse data:", data, "\033[0m")

            return jsonify(data), 200


    def run(self):
        ssl_context = (
            'steering-service/certs/steering-service.pem', 
            'steering-service/certs/steering-service-key.pem'
        )
        self.app.run(
            host=STEERING_ADDR, 
            port=STEERING_PORT, 
            ssl_context=ssl_context,
            use_reloader=False,
            debug=True
        )
# END CLASS.

main = Main()

# MAIN
if __name__ == '__main__':
    monitor.start_collecting()
    main.run()
# EOF
