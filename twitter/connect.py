import time
import datetime
from sys import path
path.append('..')

import common.connect

class TwitterConnection(common.connect.JSONOauthConnection):

  waitseconds = 900
  
  def handle_response(self, response_text, head):
      ret = super().handle_response(response_text, head)
      if not ret:
        return None
      if 'status' in ret and ret['status'] == 404:
        self.logger.warn("404 status in returned JSON")
        ret = None
      elif 'errors' in ret:
        self.logger.warn("Errors in returned JSON")
        try:
          for e in ret['errors']:
            self.logger.warn("Error code {}: '{}'".format(e['code'],e['message']))
            if e['code'] == 88:
              if head and 'x-rate-limit-reset' in head:
                waituntil = datetime.datetime.fromtimestamp(float(head['x-rate-limit-reset']))
                diff = waituntil - datetime.datetime.now() 
                daysecs = diff.days * 3600 * 24
                self.waitseconds = daysecs + diff.seconds
              else:
                self.waitseconds = 900
              self.flag_wait()
            else:
              ret = None
        except KeyError as ke:
          self.logger.warn("KeyError in Twitter JSON")
          self.logger.warn(ke)
      return ret
