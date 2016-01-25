from sys import path
path.append('..')

import common.connect

class LinkedInConnection(common.connect.JSONOauthConnection):

  waitseconds = 86400

  def build_request(self, url, params):
    params['format'] = 'json'
    return super().build_request(url, params)

  def handle_response(self,response_text):
    ret = super().handle_response(response_text)
    if ret and 'status' in ret:
      if ret['status'] == 404:
        return None
      if ret['status'] == 403:
        self.flag_wait()
    return ret
