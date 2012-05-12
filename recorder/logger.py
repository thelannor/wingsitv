# coding: utf-8

import os
import logging

from datetime import datetime
from settings import settings

DEBUG = os.environ.get('DEBUG', False)

frmt = '%(asctime)s: %(levelname)-8s:%(name)s: %(message)s'

if DEBUG:
    frmt = '%(levelname)-8s: %(asctime)s: [%(module)s.%(funcName)s:%(lineno)d]:%(name)s: %(message)s'

logdirname = os.path.expanduser(settings['logger']['path'])
logfilename = datetime.now().strftime(
                        os.path.join(logdirname, '%Y.%m.%d/%Y.%m.%d_%H%M%S.log')
                        )
d = os.path.dirname(logfilename)
if not os.path.isdir(d):
    os.makedirs(d)

logging.basicConfig(
    level=logging.DEBUG,
    format=frmt,
    datefmt='%H:%M:%S,%f',
    filename=logfilename,
    filemode='w'
)

console = logging.StreamHandler()
console.setLevel(logging.INFO)
formatter = logging.Formatter(frmt)
console.setFormatter(formatter)
logging.getLogger('').addHandler(console)

