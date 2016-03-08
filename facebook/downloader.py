import argparse

try:
  import common.logger
except ImportError as ie:
  from sys import path
  import os
  path.append(os.path.abspath('.'))
  path.append(os.path.abspath('..'))
  import common.logger


from facebook.connect import FacebookConnection
from common.connect import PooledConnection

import common.downloader
import common.profilestore


class FacebookDownloader(common.downloader.Downloader):

  network_name = 'Facebook'
  apiroot = 'https://graph.facebook.com/'

  def download(self, record):
    results = []
    n_id = record['network_id']
    if n_id == None or n_id == '':
      return results
    #params for main grab
    params = {}
    selectors = ['id','about','bio','cover','hometown','is_verified','link','location','name','website']
    params['fields'] = ', '.join(selectors)
    params['id'] = n_id
    results.append(self.get_bundled(self.apiroot, params))
    params = {'fields':'from'}
    comments = self.get_bundled(self.apiroot+n_id+'/comments', params)

    links = self.get_bundled(self.apiroot+n_id+'/links', {})
    results.append(links)
    
    if links and 'data' in links:
      for l in links['data']:
        if not 'id' in l:
          continue
        params = {'summary': True}
        results.append(self.get_bundled(self.apiroot+l['id']+'/comments',params))
        params = {'fields':'from'}
        results.append(self.get_bundled(self.apiroot+l['id']+'/comments',params))
    return results 


if __name__ == '__main__':
  parser = argparse.ArgumentParser(description='Download Facebook profiles.',fromfile_prefix_chars='@')
  parser.add_argument('database', help='A CSV ProfileStore to download profiles from')
  parser.add_argument('--key','-k',help='The API access token for Facebook.')
  parser.add_argument('--verbose','-v', help='Give more output than usual.', action='count')
  args = parser.parse_args()

  if not args.key:
    raise ValueError("Need an API key in order to query Facebook.")

  logger = None

  if args.verbose and args.verbose > 0:
    logger = common.logger.getLogger('facebookdownloader',level='info',output='facebook.log')
  else:
    logger = common.logger.getLogger('facebookdownloader',output='facebook.log')
  logger.info('Logger initialised')

  facebookconn = PooledConnection(args.key, FacebookConnection, logger=logger)
  ps = common.profilestore.ProfileStore(args.database,logger=logger)
  logger.info('Using database \'{}\''.format(args.database))
  fbdownloader = FacebookDownloader(ps, facebookconn,logger=logger)
  fbdownloader.run()


