from sys import path
path.append('..')

import common.connect

class GoogleConnection(common.connect.JSONConnection):
  
  delay = 0.2
  waitseconds = 86400

  def __init__(self, server_key, logger=None):
    self.server_key = server_key
    super().__init__(logger)
    
  def build_request(self,url,params):
    params['key'] = self.server_key
    return super().build_request(url,params)

  def handle_error(self, error_obj):
    super().handle_error(error_obj)
    if hasattr(error_obj, 'code') and error_obj.code and error_obj.code == 403:
      self.flag_wait() 
