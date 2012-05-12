# coding: utf-8

__all__ = [ 'table_sizes', 'to_bytes', 'get_free_size' ]

import re
import os

# Таблица размеров
table_sizes = dict([ [t,2**(10*i)] for i,t in enumerate('bkmgtpezy') ])

def to_bytes(s):
    result = re.match(r'(?P<amount>[0-9]+)(?P<t>[bkmgt]{1})$', s.lower())
    if not result:
        return 0

    amount, t = result.groups()
    return int(amount) * table_sizes[t]

def get_free_size(mount):
    """Возвращает количество свободных байт в указанной точке монтирования
        @mount - точка монтирования файловой системы
    """

    result = os.popen('df --total "%s"' % mount).read()
    index = result.find('total')

    if index < 0:
        return None

    (_, total, use, free, _) = result[index:].split()
    return int(free) * 1024 # to bytes
    # return to_bytes(free)
