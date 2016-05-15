from sys import path
path.append('..')

import datetime
import common.connect

class LinkedInConnection(common.connect.JSONOauthConnection):

  waitseconds = 86400

  def build_request(self, url, params):
    params['format'] = 'json'
    return super().build_request(url, params)

  def handle_response(self,response_text, headers):
    ret = super().handle_response(response_text, headers)
    if ret and 'status' in ret:
      if ret['status'] == 404:
        return None
      if ret['status'] == 403 and ret['errorCode'] != 0:
        self.flag_wait()
    return ret

class LinkedInSearchConnection(common.connect.MediaConnection):

  delay = 5
  waitseconds = 60
  in_block = False

  def handle_error(self, error_obj):
    self.logger.warn(error_obj)
    if hasattr(error_obj, "code"):
      self.logger.info(error_obj.code)
      if error_obj.code == 999 and not self.waitseconds > 7680:
        if self.in_block:
          self.waitseconds += self.waitseconds 
          self.delay = self.delay + 5
        self.in_block = True
        self.logger.info('Hit 999 response. Waiting for {} seconds.'.format(self.waitseconds))
        self.flag_wait()

  def handle_response(self, response_text, headers):
    if self.delay > 5 and response_text != None:
      self.delay = self.delay - 15
    if self.in_block and response_text != None:
      self.in_block = False
      self.waitseconds = 60
    return response_text


  def flag_wait(self):
    """ Flag to the next request that a wait
    period is necessary (rate limiting). """
    self.waitfrom = datetime.datetime.now()
    self.get(self.lasturl, self.lastparams)
