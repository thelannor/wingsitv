# coding: utf-8

__all__ = [ 'Storage', 'to_bytes', 'get_free_size' ]

import os
import tarfile

from datetime import datetime
from getfreespace import get_free_size

from logger import logging
logStorage = logging.getLogger('server.storage')

class Storage(object):

    def __init__(self, uniqname, storage_obj):
        self.obj = storage_obj
        self.uniqname = uniqname
        self.homepath = os.path.expanduser(
                                os.path.join(self.obj.path, uniqname))

        # Список текущего открытого хранилища
        # [объект, имя-хранилища, время-открытия]
        self._storage = [ None, None, None ]

        # Флаг, блокирует все операции, используется перед закрытием хранилища
        self._lock_all = False

        # Флаг, блокирует операцию отправки кадра в хранилище
        # Автоматически сбрасывается при успешном открытии хранилища
        self._lock_write = True

        # Флаг, блокирует операцию закрытия хранилища
        self._lock_close = False

        # Флаг, блокирует все операции если недостаточно места на носителе
        self._lock_not_space = False

        # Количество отправленных кадров в хранилище
        # Сбрасывается при каждом открытии хранилища
        self._storage_count_frames = 0

        # Шаблон имени файла кадра сохраняемого в хранилище
        self._storage_frame_filename = '%Y.%m/%d/%H%M/%S.%f.jpg'

    def __repr__(self):
        return (
            '<{0.__class__.__name__} {0.uniqname!r}:'
            ' homepath={0.homepath!r}, storage={0.obj!r}'
            '>'.format(self)
        )

    def open(self):
        """Открывает нового хранилище"""

        if self._lock_all:
            return False

        self._storage_count_frames = 0
        opened_stamp = datetime.now()

        # Формируем имя файла хранилища
        filename = opened_stamp.strftime(os.path.join(
                        self.homepath, '%Y.%m', '%d', '%H%M%S.%f.tar'))

        dirname = os.path.dirname(filename)
        if not os.path.isdir(dirname):
            logStorage.warning('Creating directory: %r', dirname)
            os.makedirs(dirname)

        logStorage.info('%r: Opening storage: %r', self.uniqname, filename)
        self._storage = [ tarfile.open(filename, 'w|'), filename, opened_stamp ]

        self._lock_write = False
        self._lock_close = False

        self.check_freespace()
        return True

    def close(self):
        """Закрывает хранилище"""

        if self._lock_close:
            # Закрытие хранилища запрещено
            return False

        if not self._lock_all:
            # Закрытие запрещено (не заблокированы все операции)
            return False

        if self._storage[0]:
            logStorage.info('%r: Closing storage: %r', self.uniqname, self._storage[1])
            self._storage[0].close()

        self._storage = [ None, None, None ]
        return True

    def write(self, frame, stamp=None):
        """Отправляет кадр в хранилище
            @frame = кадр
            @stamp = время получения кадра [datetime] (опционально)
        """

        if self._lock_all or self._lock_not_space:
            # Все операции - заблокированы
            return False

        if self._lock_write:
            # Операция отправки кадра - заблокирована
            return False

        if not isinstance(stamp, datetime):
            stamp = datetime.now()

        try:
            outfile = tarfile.TarInfo(stamp.strftime(self._storage_frame_filename))
            outfile.size = len(frame.getvalue())

            self._storage[0].addfile(outfile, frame)
            self._storage_count_frames += 1

        except Exception as err:
            logStorage.error('%r: %r', self.uniqname, err)

        if (self._storage_count_frames % 100) == 0:
            self.check_freespace()
            self.check_storage_size()

    def check_storage_size(self):
        """Проверяет размер хранилища, если больше допустимого,
           то открывает новое хранилище
        """

        if not self._storage[1]:
            return False

        current_filesize = os.path.getsize(self._storage[1])

        if (self._storage_count_frames % 500) == 0:
            logStorage.info('%r: Storage size = %d bytes (%.02f Mb)',
                        self.uniqname, current_filesize, current_filesize/1048576)

        if current_filesize >= self.obj.maxsize:
            self._lock_all = True

            while self.close() != True:
                # Ожидаем закрытия хранилища
                pass

            self._lock_all = False
            self.open()

            return True
        return False

    def check_freespace(self):
        """Проверяет свободное место на носителе где размещено хранилище
           Если свободного места меньше допустимого, то блокирует все операции
        """

        # TODO: Сделать возобновление работы программы, если место освободилось

        path = os.path.dirname(self._storage[1])
        freespace = get_free_size(path)

        self._lock_not_space = (freespace <= self.obj.minfreespace)
        if self._lock_not_space:
            freespace_mb = '%.02f Mb' % (freespace / 1048576)
            logStorage.critical('%r: not enough space on the media: %r (free %d bytes, %s)',
                                self.uniqname, path, freespace, freespace_mb)
            self._lock_all = True
            self.close()

