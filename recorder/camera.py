# coding: utf-8

import time
import Image
import ImageDraw
import StringIO

from datetime import datetime
from urllib import urlopen

from logger import logging
logCamera = logging.getLogger('server.camera')

class Camera(object):

    def __init__(self, camera_obj):
        self.obj = camera_obj

        # Флаг, блокирует все операции
        self._lock_all = False

        # Флаг, блокирует операцию получения кадров с камеры
        self._lock_get = False

        # Время когда был получен кадр
        self._frame_stamp = None

        # Количество полученных кадров
        self._count_frames = 0

    def __repr__(self):
        return (
            '<{0.__class__.__name__} {0.obj.uniqname!r}:'
            ' frames={0._count_frames!r}'
            '>'.format(self)
        )

    def get_frame(self):
        """Получает кадр с камеры
        """

        if self._lock_all or self._lock_get:
            return None

        try:
            frame = StringIO.StringIO(urlopen(self.obj.url).read())
            self._frame_stamp = datetime.now()
        except IOError as err:
            logCamera.error('%r: %r', self.obj.uniqname, err)
            return None
        else:
            self._count_frames += 1
            if self.obj.stamp and len(self.obj.stamp) > 1:
                return self.paintTimeStamp(frame, self._frame_stamp, self.obj.stamp)
            return frame

    def paintTimeStamp(self, frame, stamp, stampfrmt, position=[5,5]):
        """Размещает время и возвращает новый кадр, или None
            @frame     = кадр
            @stamp     = объект времени [datetime]
            @stampfrmt = формат времени
            @position  = позиция времени (x,y)
        """

        if self._lock_all:
            return None

        try:
            pil = Image.open(frame)
            draw = ImageDraw.Draw(pil)
            draw.text(tuple(position), stamp.strftime(stampfrmt))
            del draw
        except Exception as err:
            logCamera.error('%r: %r', self.obj.uniqname, err)
            return None
        else:
            newframe = StringIO.StringIO()
            pil.save(newframe, 'JPEG')
            _frame = StringIO.StringIO(newframe.getvalue())
            newframe.close()
            return _frame

