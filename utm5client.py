#! /usr/bin/env python3
#
#   Copyright (c) 2010-2011, Andrew Grigorev <andrew@ei-grad.ru>
#   All rights reserved.
#
#   Redistribution and use in source and binary forms, with or without
#   modification, are permitted provided that the following conditions are
#   met:
#
#       Redistributions of source code must retain the above copyright notice,
#       this list of conditions and the following disclaimer.  Redistributions
#       in binary form must reproduce the above copyright notice, this list of
#       conditions and the following disclaimer in the documentation and/or
#       other materials provided with the distribution.  Neither the name of
#       the <ORGANIZATION> nor the names of its contributors may be used to
#       endorse or promote products derived from this software without
#       specific prior written permission.
#
#   THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS
#   IS" AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO,
#   THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR
#   PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT HOLDER OR
#   CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL,
#   EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED TO,
#   PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS OF USE, DATA, OR
#   PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF
#   LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING
#   NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE OF THIS
#   SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.
#


__all__ = [ 'UTM5Client' ]

import re, sys, os, atexit, getpass
from urllib.request import urlopen
from urllib.parse import urlencode
from datetime import datetime, timedelta
from getpass import getpass

import logging
logging.basicConfig(level=logging.INFO, format="%(levelname)s - %(funcName)s: %(message)s")

from storage import SqliteStorage

select_contract = lambda contracts: list(contracts)[0]

class UTM5Client(object):

  traffic_re = re.compile(r'<TR><TD BGCOLOR=#B0B0B0>\d+<TD ALIGN=LEFT>&nbsp;(?P<date>\d\d\.\d\d\.\d\d)( (?P<time>\d\d:\d\d:\d\d)|)&nbsp;<TD ALIGN=LEFT>&nbsp;(?P<login>\w+)&nbsp;<TD ALIGN=CENTER>&nbsp;(?P<direction>[<>])&nbsp;<TD ALIGN=LEFT>&nbsp;(?P<traffic_type>[\w ]+)'
      '&nbsp;<TD ALIGN=CENTER>&nbsp;(?P<amount>\d+)&nbsp;')
  contracts_re = re.compile(r'''<A HREF="\?FORMNAME=IP_CONTRACT_INFO&SID=(?P<sid>\w+)&CONTR_ID=(?P<id>\d+)&NLS=WR" TITLE="Посмотреть данные по договору" target="_self" method="post">(?P<name>\w+)</A>
&nbsp;<TD ALIGN=CENTER>&nbsp;(?P<client>[\w ]+)&nbsp;<TD ALIGN=RIGHT>&nbsp;\d+.\d\d&nbsp;<TD ALIGN=RIGHT>&nbsp;\d+.\d\d&nbsp;''', re.MULTILINE)

  def __init__(self, opt):
    self.url = opt.url.strip('/')
    self.hours = opt.hours

    if opt.backend == 'sqlite3':
      self.db = SqliteStorage(opt)

  def auth(self, login, passwd):
    """
      Authenticates and retrieves a list of available contracts.
    """
    logging.info('Authenticating as {0}...'.format(login))
    res = urlopen(self.url+'/!w3_p_main.showform',
      data=urlencode({'SID': '',
                    'NLS': 'WR',
                    'USERNAME': login,
                    'PASSWORD': passwd,
                    'FORMNAME': 'IP_CONTRACTS',
                    'BUTTON': 'Вход'.encode('cp1251')
                    })).read().decode('cp1251')

    self.contracts = {c.group('id'): c.groupdict() for c in self.contracts_re.finditer(res)}

    if not self.contracts:
      logging.error('Authentication failed! No contracts!')
      raise Exception('Authentication failed! No contracts!')

    self.set_contract(list(self.contracts)[0])

  def set_contract(self, cid):
    self.sid = self.contracts[str(cid)]['sid']
    self.cid = cid

  def request_day_from_utm5(self, date, traffic_type="LLTRAF_INET"):
    """
      Get info from UTM5 client area by HTTP.

      @param month: month in form "MM.YYYY"
      @param day: day of month
      @param traffic_type: type of traffic
            LLTRAF_INET - internet (default)
            LLTRAF_MM - multimedia
            LLTRAF_LOC - local
    """

    logging.info('Requesting %d.%d.%d from UTM5' % date.timetuple()[:3])

    month = '%.2d.%d' % (date.month, date.year)
    day = date.day

    res = urlopen(self.url+'/!w3_p_main.showform',
      data=urlencode({
                'CONTRACTID': self.cid,
                "DIR": "",
                "SRV": traffic_type,
                "MONTH": month,
                "DAY": day,
                "UNITS_VIEW": "1",
                "SID": self.sid,
                "NLS": "WR",
                "FORMNAME": "LL_TRAFFIC2",
                "BUTTON": 'Показать'.encode('cp1251')
               })).read().decode('cp1251')

    data = []

    for e in self.traffic_re.finditer(res):
      direction = "in" if e.group('direction') == "<" else "out"
      date = e.group('date')
      time = int((e.group('time') or '00:00:00')[:2])
      amount = e.group('amount')
      data.append((direction, date, time, amount))

    return data

  def get_month_traffic(self, year=datetime.today().year, month=datetime.today().month, traffic_type="LLTRAF_INET"):

    date = datetime(year, month, 1)

    if date > datetime.today():
      raise Exception(date.strftime("Нельзя узнать свою статистику за %B %Y"))

    daytime_amounts = [0, 0]
    full_amounts = [0, 0]

    while date.month == month:

      if not self.db.date_is_fixed(self.cid, date):
        data = self.request_day_from_utm5(date)
        self.db.update_data(self.cid, data)
        if date != datetime.today():
          self.db.fix_date(self.cid, date)

      date_daytime_amounts = self.db.get_amounts(self.cid, date, self.hours)
      daytime_amounts[0] += date_daytime_amounts[0]
      daytime_amounts[1] += date_daytime_amounts[1]

      date_full_amounts = self.db.get_amounts(self.cid, date, list(range(24)))
      full_amounts[0] += date_full_amounts[0]
      full_amounts[1] += date_full_amounts[1]

      if date == datetime.today():
        break
      else:
        date += timedelta(days=1)

    return sum(daytime_amounts), sum(full_amounts)


if __name__ == '__main__':
  from optparse import OptionParser
  parser = OptionParser(usage='Usage: %prog [options]', version='0.1.1')
  parser.add_option('-u', '--url', dest='url',
      help='адрес системы UTM5',
      default='https://mnx.net.ru/utm5')
  parser.add_option('-d', '--debug', action='store_true', dest='debug',
      help='вывод отладочных сообщений',
      default=False)
  parser.add_option('-v', '--verbose', action='store_true', dest='verbose',
      help='подробный вывод сообщений',
      default=False)
  parser.add_option('-w', '--workdir', dest='workdir',
      help='рабочая директория программы',
      default=os.path.expanduser(os.path.join('~', '.utm5client')))
  parser.add_option('-l', '--login', dest='login', metavar='LOGIN',
      help='логин от личного кабинета',
      default=None)
  parser.add_option('-p', '--passw', dest='passwd', metavar='PASSWORD',
      help='пароль от личного кабинета',
      default=None)
  parser.add_option('-n', '--night', dest='night', metavar='N-M',
      help='ночное время (по умолчанию: %default)',
      default='01-10')
  parser.add_option('-r', '--refresh', dest='delay', metavar='DELAY',
      help='интервал обновления информации',
      default=300)
  parser.add_option('-b', '--backend', dest='backend', metavar='',
      help='бэкэнд хранения данных, sqlite или plaintext',
      default='sqlite3')
  opt, args = parser.parse_args()

  if opt.login is None:
    opt.login = input('Login:')

  if opt.passwd is None:
    opt.passwd = getpass('Password:')

  begin, end = [ int(i) for i in opt.night.split('-') ]

  if begin < end:
    opt.hours = list(range(begin, end))
  else:
    opt.hours = list(range(0, end) + range(begin, 24))

  if not os.path.exists(opt.workdir):
    os.mkdir(opt.workdir)

  client = UTM5Client(opt)
  client.auth(opt.login, opt.passwd)
  daytime, full = client.get_month_traffic()

  def hum(size):
    SUFFIXES = ['KB', 'MB', 'GB']

    suf = 'B'

    for suffix in SUFFIXES:
      if size < 1024:
        break
      else:
        size /= 1024
        suf = suffix

    return '%.2f%s' % (size, suf)

  sys.stdout.write("Daytime: %s\nFull: %s\n" % (hum(daytime), hum(full)))

# vim: set ts=2 sw=2:
