
import logging

from . import BaseDocument
from .. import notify 
from .. trace import tracer as FTRACE 

log_name = "r.l.b.apryse"

class Apryse(BaseDocument):

    def __init__(self, options={}, log=log_name):
        super().__init__(options=options)

        self.logger_ = logging.getLogger(log)

        if "apryse-token" not in self.options_ or self.options_["apryse-token"] == "":
            self.logger().fatal("Missing Apryse API key")
            raise Exception("Missing Apryse API key")

    @FTRACE
    def loadDocument(self, filename=""):
        super().loadDocument(filename)

        call_data = notify.OpenDocument(document=None, filename=filename, page_count=10)

        self.logger().info("Posting OpenDocument notification")

        self.notificationCenter().raise_event("OpenDocument", call_data)

        self.devlog().info("Posted OpenDocument notification")
