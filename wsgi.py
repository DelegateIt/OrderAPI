#!/usr/bin/env python2.7

import gator.config
from gator import app

# Fix broken SSL
import urllib3.contrib.pyopenssl
urllib3.contrib.pyopenssl.inject_into_urllib3()

if __name__ == '__main__':
    port = gator.config.store["api_host"]["bind_port"]
    app.run(host="0.0.0.0", port=port)
