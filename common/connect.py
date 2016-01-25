from urllib.parse import urlencode
from urllib.request import urlopen, Request
import json
import oauth2 as oauth
import datetime
import time

try:
  import common.logger
except ImportError as ie:
  from sys import path
  import os
  path.append(os.path.abspath('.'))
  path.append(os.path.abspath('..'))
  import common.logger


class MediaConnection:

  waitfrom = None
  waitseconds = 0
  timeout = 5
  delay = 0

  def __init__(self,logger=None):
    if not logger:
      logger = common.logger.getLogger(self.__class__.__name__)
    self.logger = logger

  def build_request(self,url,params):
    """ Apply any special preprocessing to the input
    to create an object that can be accessed by urlopen(). """
#    headers = {'User-agent' : 'Mozilla/11.0'}
    headers = {'User-agent' : 'Mozilla/5.0 (X11; Linux i586; rv:31.0) Gecko/20100101 Firefox/31.0'}
    requrl  = url + '?' + urlencode(params)
    req     = Request(requrl,None,headers)
    self.logger.info('Built request `{}`'.format(requrl))
    return req


  def handle_error(self, error_obj):
    self.logger.warn(error_obj)
    if hasattr(error_obj, "code"):
      try:
        self.logger.warn(error_obj.read())
      except:
        pass


  def handle_response(self,response_text):
    """ Handle the result of the request.
    This could mean parsing the response for error codes
    or doing some necessary post-processing.
    
    :param dict response_text: The text of the requested resource, or None."""
    return response_text
  

  def flag_wait(self):
    """ Flag to the next request that a wait
    period is necessary (rate limiting). """
    self.waitfrom = datetime.datetime.now()


  def wait(self):
    """ Wait for a defined period. Usually will wait
    for self.delay seconds (inter-request rate limiting), 
    but will handle waiting periods when flag_wait has 
    been called. """
    if not self.waitfrom:
      time.sleep(self.delay)
    else:
      iterc = 0
      while True:
        iterc += 1
        now = datetime.datetime.now()
        diff = now - self.waitfrom
        #timedelta shifts whole days into a different attribute, so we have to get them out again
        daysecs = diff.days * 3600 * 24
        if diff.seconds + daysecs >= self.waitseconds:
          self.waitfrom = None
          break
        else:
          decile = self.waitseconds/10
          self.logger.info("{}) Have slept {} seconds of {}".format(iterc, diff.seconds, self.waitseconds))
          time.sleep(decile)


  def get(self, url, params):
    """ Query a resource using the given parameters. 
    
    :param str url: The url to query.
    :param dict params: A dictionary of parameters to query for. 
    :return dict jsonobj: The result of self.handle_response(). Could be None. """
    req = self.build_request(url,params)
    self.lasturl = url
    self.lastparams = params
    request,ret = None,None
    self.wait()
    try:
      request = urlopen(req,timeout=MediaConnection.timeout)
      content = request.read()
      ret = content.decode('utf-8')
    except Exception as e:
      self.logger.warn("Exception while requesting `{}`".format(req))
      self.handle_error(e) 
    return self.handle_response(ret)      


class JSONConnection(MediaConnection):
  
  def handle_response(self,response_text):
    ret = None
    try:
      ret = json.loads(response_text)
    except Exception as e:
      self.logger.warn("Exception parsing JSON")
      self.logger.debug(json)
      self.logger.warn(e)
    return ret
    

class OauthConnection(MediaConnection):
  
  def __init__( self,  
                consumer_key,
                consumer_secret,
                user_token,
                user_secret,
                logger):
    logger.info("OAuth:\nConsumer Key:{}\nConsumer Secret:{}\nUser Token:{}\nUser Secret:{}".format(consumer_key,consumer_secret,user_token,user_secret))
    consumer = oauth.Consumer(consumer_key,consumer_secret)
    client = oauth.Client(consumer)
    access_token = oauth.Token(key=user_token,
                               secret=user_secret)
    client = oauth.Client(consumer,access_token,timeout=MediaConnection.timeout)
    self.client = client
    super().__init__(logger)

  def build_request(self,url,params):
    """ Apply any special preprocessing to the input
    to create an object that can be accessed by client.request(). """
    requrl  = url + '?' + urlencode(params)
    self.logger.info('Built request `{}`'.format(requrl))
    return requrl

  def get(self, url, params):
    """ Query a resource using the given parameters. 
    
    :param str url: The url to query.
    :param dict params: A dictionary of parameters to query for. 
    :return dict jsonobj: The result of self.handle_response(). Could be None. """
    req = self.build_request(url,params)
    self.lasturl = url
    self.lastparams = params
    ret = None
    self.wait()
    try:
      resp, content = self.client.request(req, "GET")
      ret = content.decode('utf-8')
      self.logger.info("Response code {}.".format(resp))
    except Exception as e:
      self.logger.warn("Exception while oauth-requesting `{}`".format(url))
      self.handle_error(e) 
    return self.handle_response(ret)      


class JSONOauthConnection(OauthConnection):
  
  def handle_response(self,response_text):
    return JSONConnection.handle_response(self,response_text)


class PooledConnection:

  def __init__(self, credential_file, connection_class, logger):
    self.pool = []
    for line in open(credential_file,'r'):
      if ' ' in line:
        self.pool.append(connection_class(*line.strip().split(' '),logger=logger))
      else:
        self.pool.append(connection_class(line.strip(),logger))
    if len(self.pool) == 0:
      raise ValueError('Credentials file {} did not produce any connections')

  def get_connection(self):
    now  = datetime.datetime.now()
    connection = None
    for con in self.pool:
      if not con.waitfrom:
        connection = con
        break
      else:
        diff = now - con.waitfrom
        if diff.seconds >= con.waitseconds:
          con.waitfrom = None
          connection = con
          break
    if not connection:
      connection = self.pool[0]
    return connection

  def get(self, url, params):
    connection = self.get_connection()
    result = connection.get(url, params)
    if connection.waitfrom:
      connection = self.get_connection()
      result = connection.get(url, params)
    self.lasturl = connection.lasturl
    self.lastparams = connection.lastparams
    return result
    
