
import os
import json

try:
  import common.logger
except ImportError as ie:
  from sys import path
  path.append(os.path.abspath('.'))
  path.append(os.path.abspath('..'))
  import common.logger


class Downloader():
  
  network_name = 'None'

  def __init__(self, profilestore, connection, logger=None):
    self.profilestore = profilestore
    self.connection = connection
    if not logger:
      logger = common.logger.getLogger(self.__class__.__name__)
    self.logger = logger
    self.cache = []

  def get_bundled(self, url, params):
    result = self.connection.get(url, params)
    bundle = {'query_url': url,
              'query_params': params,
              'result' : result}
    self.cache.append(bundle)
    return result
    
  def flush(self,dirpath,record):
    fh = open(dirpath+os.sep+str(record['uid'])+'.json','w')
    json.dump(self.cache,fh)
    fh.close()
    self.cache = []

  def download(self, record):
    raise NotImplementedError('`download()` not implemented for {}'.format(self.__class__.__name__))

  def run(self, dirpath='raw'):
    try:
      os.mkdir(dirpath) 
    except FileExistsError:
      pass
    for record in self.profilestore.records:
      if record['network'] == self.network_name:
        self.download(record)
        self.flush(dirpath,record)
