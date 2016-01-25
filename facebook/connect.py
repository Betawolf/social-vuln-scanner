import argparse

try:
  import common.connect
except ImportError as ie:
  from sys import path
  import os
  path.append(os.path.abspath('.'))
  path.append(os.path.abspath('..'))
  import common.connect 


class FacebookConnection(common.connect.JSONConnection):

  delay = 2

  def __init__(self,app_token,user_token,logger):
    self.app_token = app_token
    self.user_token = user_token
    super().__init__(logger)

  def build_request(self,url,params):
    if 'as_user' in params:
      params['access_token'] = self.user_token
      del params['as_user']
    else: 
      params['access_token'] = self.app_token
    return super().build_request(url,params)

if __name__ == '__main__':
  parser = argparse.ArgumentParser(description='Generate long access token')
  parser.add_argument('short_token', help='A short user access token from the Facebook API.')
  parser.add_argument('app_file', help='A file containing the app_id and app_secret, in order, separated by spaces.')
  args = parser.parse_args()
  
  app_id, app_secret = open(args.app_file,'r').readlines()[0].split()
  params = {}
  params['grant_type'] = 'fb_exchange_token'
  params['client_id'] = app_id
  params['client_secret'] = app_secret
  params['fb_exchange_token'] = args.short_token 
  conn = common.connect.MediaConnection(logger=common.logger.getLogger('fbconnect',level='debug', output='facebook.log'))
  result = conn.get('http://graph.facebook.com/oauth/access_token',params)
  print(result)
  
