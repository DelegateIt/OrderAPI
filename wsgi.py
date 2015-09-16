#!/usr/bin/env python3

import argparse
from gator import socketio 

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description="Starts the api server")
    parser.add_argument("--port", "-bp", dest="port", type=int, default=80, help="The port to bind to")
    parser.add_argument("--host", "-bh", dest="host", default="0.0.0.0", help="The hostname to bind to")

    args = parser.parse_args()
    socketio.run(host=args.host, port=args.port)
