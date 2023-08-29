import logging

import EventNotifier

from .. import notify 
from .. import trace 

log_name = "r.l.b.base"

class BaseDocument:

    def __init__(self, options={}, log=log_name):
        self.options_ = options

        self.logger_ = logging.getLogger(log)
        self.devel_logger_ = logging.getLogger("d.devel")

        self.nc_ = EventNotifier.Notifier(["OpenDocument", "BeginPage", "EndPage", "ProcessElement"])

    def notificationCenter(self) -> EventNotifier.Notifier :
        return self.nc_


    def register(self, event:str, callback):
        self.notificationCenter().subscribe( event, callback )


    def logger(self):
        return self.logger_

    def devlog(self):
        return self.devel_logger_


    def loadDocument(self, filename=""):
        self.read_file_name_ = filename

    def processDocument(self):
        pass

    def saveDocument(self):
        pass
