# coding: utf-8
#
# Copyright 2011, Novikov Valentin

__all__ = [ 'QTrafView' ]

import sqlite3
from os.path import join
from PyQt4 import QtCore, QtGui
from PyQt4.QtGui import QTableWidgetItem
from settings import DEFAULT_WORKDIR

dbfile = join(DEFAULT_WORKDIR, 'sqlite.db')

class tvDateEdit(QtGui.QDateEdit):
  """ QDateEdit + QCalendar """

  def __init__(self, parent):
    super(tvDateEdit, self).__init__(parent)

    self.setDateRange(QtCore.QDate(2008, 1, 1),
                      QtCore.QDate(2020, 1, 1))

    self.setDate(QtCore.QDate().currentDate())
    self.setDisplayFormat("dd.MM.yyyy")

    self.setCalendarPopup(True)
    self.setCalendarWidget(QtGui.QCalendarWidget(self))

  def __str__(self):
    return self.date().toString("dd.MM.yyyy")

class tvTimeEdit(QtGui.QTimeEdit):

  def __init__(self, parent=None):
    super(tvTimeEdit, self).__init__(parent)
    self.setTime(QtCore.QTime().currentTime())

  def __str__(self):
    return "{}".format(self.time().toString("h"))

  def __eq__(self, obj):
    return str(self) == str(obj)

class tvTable(QtGui.QTableWidget):
  labels = ('Дата', 'Время', 'Объем')

  def __init__(self, parent=None):
    super(tvTable, self).__init__(parent)
    self.parent = parent
    self.sqlconn = None
    self.curs = None
    self.myclear()

  def myclear(self):
    self.clear()
    self.setRowCount(1)
    self.setColumnCount(len(self.labels))
    self.setHorizontalHeaderLabels(self.labels)

  def refresh(self, dateSE, timeSE):
    if not self.sqlconn:
      self.sqlconn = sqlite3.connect(dbfile)
      self.curs = self.sqlconn.cursor()
    if not self.sqlconn or not self.curs:
      return

    ttype = "amounts_in" if str(self.parent.comboTrafType) == 0 else "amounts_out"
    q = "SELECT date,hour,amount FROM '{}' WHERE date > '{}'"
    q+= " AND date < '{}' AND hour > '{}' AND hour < '{}'"
    q = q.format(ttype, dateSE[0], dateSE[1], timeSE[0], timeSE[1])
    self.curs.execute(q)
    ## print("debug", q)

    irow = 0
    self.myclear()
    for row in self.curs:
      self.setRowCount(irow + 1)
      d = QTableWidgetItem(str(row[0]))
      h = QTableWidgetItem(str(row[1]))
      s = QTableWidgetItem(str(row[2])) ## TODO: gb, mb, etc..
      self.setItem(irow, 0, d)
      self.setItem(irow, 1, h)
      self.setItem(irow, 2, s)
      irow += 1

class tvComboTrafType(QtGui.QComboBox):
  items = ('Входящий', 'Исходящий')

  def __init__(self, parent=None):
    super(tvComboTrafType, self).__init__(parent)

    self.clear()
    [ self.addItem(i) for i in self.items ]

  def __str__(self):
    return str(self.currentIndex())

class tvComboTrafSize(QtGui.QComboBox):
  items = ('Gb', 'Mb', 'Kb', 'b')

  def __init__(self, parent=None):
    super(tvComboTrafSize, self).__init__(parent)

    self.clear()
    [ self.addItem(i) for i in self.items ]

class QTrafView(QtGui.QWidget):

  def __init__(self, parent=None):
    super(QTrafView, self).__init__(parent)
    vboxRoot = QtGui.QVBoxLayout(self)

    ## dates
    hboxDRange = QtGui.QHBoxLayout()
    hboxDRange.addWidget(QtGui.QLabel("Интервал дат", self))
    self.dateS = tvDateEdit(self)
    self.dateE = tvDateEdit(self)
    hboxDRange.addWidget(self.dateS)
    hboxDRange.addWidget(self.dateE)

    ## times
    hboxTRange = QtGui.QHBoxLayout()
    hboxTRange.addWidget(QtGui.QLabel("Интервал время", self))
    self.timeS = tvTimeEdit(self)
    self.timeE = tvTimeEdit(self)
    hboxTRange.addWidget(self.timeS)
    hboxTRange.addWidget(self.timeE)

    ## table
      # ::panel
    hboxTablePanel = QtGui.QHBoxLayout()
    hboxTablePanel.addWidget(QtGui.QLabel("Трафик", self))
    self.comboTrafType = tvComboTrafType(self)
    self.comboTrafSize = tvComboTrafSize(self)
    hboxTablePanel.addWidget(self.comboTrafType)
    hboxTablePanel.addWidget(self.comboTrafSize)
      #
    vboxTable = QtGui.QVBoxLayout()
    self.table = tvTable(self)
    vboxTable.addLayout(hboxTablePanel)
    vboxTable.addWidget(self.table)

    ##
    vboxRoot.addLayout(hboxDRange)
    vboxRoot.addLayout(hboxTRange)
    vboxRoot.addLayout(vboxTable)

    #
    self.setLayout(vboxRoot)
    self.setWindowTitle("Обзор трафика")

    ## SIGNALs
    self.timeS.timeChanged.connect(self.__timeCheck)
    self.timeE.timeChanged.connect(self.__timeCheck)
    self.dateS.dateChanged.connect(self.__timeCheck)
    self.dateE.dateChanged.connect(self.__timeCheck)

  __lockQuery = False
  def __timeCheck(self):
    self.__lockQuery = self.timeS == self.timeE
    if not self.__lockQuery:
      self.table.refresh(
          (str(self.dateS), str(self.dateE)),
          (str(self.timeS), str(self.timeE)))

