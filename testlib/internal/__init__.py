import sys
import os
import logging

logging.getLogger("boto").setLevel(logging.INFO)
logging.getLogger("requests").setLevel(logging.WARN)

sys.path.append(os.path.abspath(os.path.dirname(__file__) + "../../../"))
