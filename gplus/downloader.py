import argparse

try:
  import common.logger
except ImportError as ie:
  from sys import path
  import os
  path.append(os.path.abspath('.'))
  path.append(os.path.abspath('..'))
  import common.logger


from gplus.connect import GoogleConnection
from common.connect import PooledConnection

import common.downloader
import common.profilestore

class GplusDownloader(common.downloader.Downloader):

  network_name = 'Google+'
  people_api = 'https://www.googleapis.com/plus/v1/people/'
  activity_api = 'https://www.googleapis.com/plus/v1/activities/'

  def download(self, record):
    results = []
    n_id = record['network_id']
    results.append(self.get_bundled(self.people_api+n_id, {}))
    results.append(self.get_bundled(self.people_api+n_id+'/activities/public', {}))
    if results[1] and 'items' in results[1]:
      for activity in results[1]['items']:
        if 'id' in activity:
          a_id = activity['id']
          if 'object' in activity:
            params = {'maxResults':100}
            ao = activity['object']
            if 'replies' in ao and ao['replies']['totalItems'] > 0:
              results.append(self.get_bundled(self.activity_api+a_id+'/comments', params))
            if 'plusoners' in ao and ao['plusoners']['totalItems'] > 0:
              results.append(self.get_bundled(self.activity_api+a_id+'/plusoners', params))
            if 'resharers' in ao and ao['resharers']['totalItems'] > 0:
              results.append(self.get_bundled(self.activity_api+a_id+'/resharers', params))
    return results
          
    

if __name__ == '__main__':
  parser = argparse.ArgumentParser(description='Download G+ profiles.',fromfile_prefix_chars='@')
  parser.add_argument('database', help='A CSV ProfileStore to download profiles from')
  parser.add_argument('--key','-k',help='The API keys file for Google+.')
  parser.add_argument('--verbose','-v', help='Give more output than usual.', action='count')
  args = parser.parse_args()

  if not args.key:
    raise ValueError("Need an API key in order to query Google+.")

  logger = None

  if args.verbose and args.verbose > 0:
    logger = common.logger.getLogger('gplusdownloader',level='info',output='gplus.log')
  else:
    logger = common.logger.getLogger('gplusdownloader',output='gplus.log')
  logger.info('Logger initialised')

  gplusconn = PooledConnection(args.key, GoogleConnection, logger=logger)
  ps = common.profilestore.ProfileStore(args.database,logger=logger)
  runname = args.database.split('.')[0]
  logger.info('Using database \'{}\''.format(args.database))
  gpdownloader = GplusDownloader(ps, gplusconn,logger=logger)
  gpdownloader.run(dirpath=runname+'-raw')
