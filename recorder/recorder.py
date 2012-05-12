#!/usr/bin/env python2
# coding: utf-8

import sys
import signal

from collections import deque
from settings import settings
from storage import Storage
from camera import Camera

from logger import logging
logServer = logging.getLogger('server')

class Server(object):
    LIMIT_COUNT_CAMERAS = 8

    def __init__(self):
        self._cameras = {}

    def add_camera(self, obj):
        if obj.storage:
            storage = Storage(obj.uniqname, obj.storage)
        else:
            storage = None
        self._cameras[obj.uniqname] = [ Camera(obj), storage ]

    def start(self):
        _looped = True

        logServer.info('Starting server ...')
        if len(self._cameras) < 1:
            logServer.critical('No cameras')
            sys.exit(3)

        _cameras = deque([], self.LIMIT_COUNT_CAMERAS)
        for camera, storage in self._cameras.values():
            storage.open()
            _cameras.append([ camera, storage ])

        while _looped:
            try:
                for camera, storage in _cameras:
                    frame = camera.get_frame()
                    if frame:
                        storage.write(frame, camera._frame_stamp)
            except KeyboardInterrupt:
                logServer.warning('Aborted by user')
                break
        self.stop()

    def stop(self):
        logServer.warning('Shutdown server ...')

        for camera, storage in self._cameras.values():
            storage._lock_all = True
            camera._lock_all = True
            storage.close()

            while storage._storage[0] != None:
                pass

if __name__ == '__main__':
    import atexit
    import os

    pidfile = '/tmp/.recorder.pid'
    if os.path.isfile(pidfile):
        logServer.critical('pidfile is exists: %r', pidfile)
        raise OSError('pidfile is exists: %r' % pidfile)

    atexit.register(os.remove, pidfile)
    with open(pidfile, 'w') as fp:
        fp.write(str(os.getpid()))

    server = Server()
    [ server.add_camera(c) for c in settings['cameras'].values() ]
    server.start()
