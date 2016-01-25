import argparse

try:
  import common.logger
except ImportError as ie:
  from sys import path
  import os
  path.append(os.path.abspath('.'))
  path.append(os.path.abspath('..'))
  import common.logger


from twitter.connect import TwitterConnection

import common.downloader
import common.profilestore
from urllib.parse import quote_plus


class TwitterDownloader(common.downloader.Downloader):

  network_name = 'Twitter'
  showroot = 'https://api.twitter.com/1.1/users/show.json'
  friendsroot = 'https://api.twitter.com/1.1/friends/list.json'
  followroot = 'https://api.twitter.com/1.1/followers/list.json'
  contrbroot = 'https://api.twitter.com/1.1/users/contributors.json'
  statusroot = 'https://api.twitter.com/1.1/statuses/user_timeline.json'

  def __init__(self, ps, connection, logger, include_connections=True):
    self.include_connections = include_connections
    super().__init__(ps, connection, logger)

  def download(self, record):
    results = []
    n_id = record['network_id']
    params = {}
    params['screen_name'] = n_id
    results.append(self.get_bundled(self.showroot, {'screen_name': n_id}))
    params['count'] = 200
    results.append(self.get_bundled(self.statusroot, params))
    if self.include_connections:
      params['include_user_entities'] = True
      results.append(self.get_bundled(self.friendsroot, params))
      results.append(self.get_bundled(self.followroot, params))
      if results[0] and 'contributors_enabled' in results[0] and results[0]['contributors_enabled'] == True:
        results.append(self.get_bundled(self.contrbroot, params))
    return results 

if __name__ == '__main__':
  parser = argparse.ArgumentParser(description='Download Twitter profiles.')
  parser.add_argument('database', help='A CSV ProfileStore to download profiles from')
  parser.add_argument('--key','-k',help='The credentials file with consumer key, consumer secret, user token and user secret for Twitter API authentication, in that order per line.')
  parser.add_argument('--verbose','-v', help='Give more output than usual.', action='count')
  args = parser.parse_args()

  if not args.key or len(args.key) < 4:
    raise ValueError("Need an API key in order to query Twitter.")

  logger = None

  if args.verbose and args.verbose > 0:
    logger = common.logger.getLogger('twitterdownloader',level='info',output='twitter.log')
  else:
    logger = common.logger.getLogger('twitterdownloader',output='twitter.log')
  logger.info('Logger initialised')

  twitterconnpool = common.connect.PooledConnection(args.key,TwitterConnection,logger)
  ps = common.profilestore.ProfileStore(args.database,logger=logger)
  logger.info('Using database \'{}\''.format(args.database))
  twdownloader = TwitterDownloader(ps, twitterconnpool,logger=logger)
  twdownloader.run()


