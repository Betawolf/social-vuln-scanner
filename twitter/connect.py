import time
from sys import path
path.append('..')

import common.connect

class TwitterConnection(common.connect.JSONOauthConnection):

  waitseconds = 900
  
  def handle_response(self, response_text):
      ret = super().handle_response(response_text)
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
              self.flag_wait()
            else:
              ret = None
        except KeyError as ke:
          self.logger.warn("KeyError in Twitter JSON")
          self.logger.warn(ke)
      return ret
