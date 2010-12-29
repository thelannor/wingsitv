#! /usr/bin/env python3
# coding: utf-8

__all__ = [ 'UTM5Client' ]

import re, sys, os, atexit, getpass
from urllib.request import urlopen
from urllib.parse import urlencode
from datetime import date
from getpass import getpass
import datetime

import logging
logging.basicConfig(level=logging.INFO, format="%(levelname)s - %(funcName)s: %(message)s")

from storage import storage

select_contract = lambda contracts: list(contracts)[0]

class UTM5Client(object):

  traffic_re = re.compile(r'<TR><TD BGCOLOR=#B0B0B0>\d+<TD ALIGN=LEFT>&nbsp;(?P<date>\d\d\.\d\d\.\d\d)( (?P<time>\d\d:\d\d:\d\d)|)&nbsp;<TD ALIGN=LEFT>&nbsp;(?P<login>\w+)&nbsp;<TD ALIGN=CENTER>&nbsp;(?P<direction>[<>])&nbsp;<TD ALIGN=LEFT>&nbsp;(?P<traffic_type>[\w ]+)'
      '&nbsp;<TD ALIGN=CENTER>&nbsp;(?P<amount>\d+)&nbsp;')
  contracts_re = re.compile(r'''<A HREF="\?FORMNAME=IP_CONTRACT_INFO&SID=(?P<sid>\w+)&CONTR_ID=(?P<id>\d+)&NLS=WR" TITLE="Посмотреть данные по договору" target="_self" method="post">(?P<name>\w+)</A>
&nbsp;<TD ALIGN=CENTER>&nbsp;(?P<client>[\w ]+)&nbsp;<TD ALIGN=RIGHT>&nbsp;\d+.\d\d&nbsp;<TD ALIGN=RIGHT>&nbsp;\d+.\d\d&nbsp;''', re.MULTILINE)

  def __init__(self, utm5_url, opt):
    self.url = opt.url.strip('/')

    if opt.begin < opt.end:
      self.night = list(range(opt.begin, opt.end))
    else:
      self.night = list(range(0, end) + range(begin, 24))

    self.db = storage(opt)

  def auth(self, login, passwd):
    """
      Authenticates and retrieves a list of available contracts.
    """
    logging.info('Authenticating as {0}...'.format(user))
    res = urlopen(self.utm5_url+'/!w3_p_main.showform',
      data=urlencode({'SID': '',
                    'NLS': 'WR',
                    'USERNAME': login,
                    'PASSWORD': passwd,
                    'FORMNAME': 'IP_CONTRACTS',
                    'BUTTON': 'Вход'.encode('cp1251')
                    })).read().decode('cp1251')

    self.contracts = {c.group('id'): c.groupdict() for c in self.contracts_re.finditer(res)}

    if not contracts:
      logging.error('Authentication failed! No contracts!')
      raise Exception('Authentication failed! No contracts!')

    self.set_contract(list(self.contracts)[0]['sid'])

  def set_contract(self, contrid):
    self.sid = self.contracts[str(contrid)]['sid']
    self.contractid = contrid

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

    logging.info('Requesting {0} from UTM5'.format(date.isoformat()))

    month = '%.2d.%d' % (date.month, date.year)
    day = date.day

    res = urlopen(self.utm5_url+'/!w3_p_main.showform',
      data=urlencode({
                'CONTRACTID': self.contractid,
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
      amount = e.group('amount')
      time = e.group('time') or '00:00:00'
      date = e.group('date')
      data.append((date, time, direction, amount))

    return data

  def get_month_traffic(self, year, month=date.today().month, traffic_type="LLTRAF_INET"):

    date = datetime.date(year, month, 1)

    if date > date.today():
      raise Exception(date.strftime("Нельзя узнать свою статистику за %B %Y"))

    amounts = [0]*4

    while date.month == month:

      if not self.db.date_is_fixed(contrid, date):
        data = self.request_day_from_utm5(date)
        self.db.update_data(self.contrid, data)
        if date != datetime.today():
          self.db.fixdate(date)

      day_amounts = self.db.get_amounts(self.contrid, date)
      for i in range(4):
        amounts[i] += day_amounts[i]

      if date == datetime.today():
        break
      else:
        date += timedelta(days=1)

    return amounts


def timer_func(_config, client):
  client.verb('Calculate traffic ...\n')
  traf_full = client.get_month_traffic()

  (traf_fullin, traf_fullout) = (str(traf_full[0]), str(traf_full[1]))
  out = "All: Input  = {0} bytes\nAll: Output = {1} bytes\n"
  out = out.format(traf_fullin, traf_fullout)

  client.verb(out)
  conky = os.path.join(_config['usrhome'], 'utm5.conky')
  open(conky, 'w').write("%s / %s\n" %(str(traf_fullin), str(traf_fullout)))

  return out


def utm5client_main():
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
  parser.add_option('-n', '--night', dest='hours', metavar='N-M',
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
    opt.login = input('login:')

  if opt.passwd is None:
    opt.passwd = getpass('password:')

  client = UTM5Client(opt)

  if not os.path.exists(opt.workdir):
    os.mkdir(opt.workdir)

  client.auth(login, passwd)

if __name__ == '__main__':
  utm5client_main()
  sys.exit(0)

# vim: set ts=2 sw=2:
