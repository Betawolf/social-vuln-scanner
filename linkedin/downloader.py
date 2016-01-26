import argparse

try:
  import common.logger
except ImportError as ie:
  from sys import path
  import os
  path.append(os.path.abspath('.'))
  path.append(os.path.abspath('..'))
  import common.logger


from linkedin.connect import LinkedInConnection
from common.connect import PooledConnection

import common.downloader
import common.profilestore
from urllib.parse import quote_plus


class LinkedInDownloader(common.downloader.Downloader):

  network_name = 'LinkedIn'
  apiroot = "https://api.linkedin.com/v1/people/url="

  def download(self, record):
    results = []
    n_id = record['url']
    #params for main grab
    params = {}
    namefields = ['id','first-name','last-name','maiden-name',
        'formatted-name','phonetic-first-name','phonetic-last-name','formatted-phonetic-name']
    occfields = ['headline','industry','positions']
    locfields = ['location:(name,country:(code))']
    activfields = ['current-share']
    degreefields = ['num-connections','num-connections-capped']
    descrifields = ['summary','specialties']
    visualfields = ['picture-url']
    selectors = namefields+occfields+locfields+activfields+degreefields+descrifields+visualfields
    results.append(self.get_bundled(self.apiroot+quote_plus(n_id)+':('+','.join(selectors)+')', params))
    return results 


if __name__ == '__main__':
  parser = argparse.ArgumentParser(description='Download LinkedIn profiles.',fromfile_prefix_chars='@')
  parser.add_argument('database', help='A CSV ProfileStore to download profiles from')
  parser.add_argument('--key','-k', help='The consumer key, consumer secret, user token and user secret for LinkedIn API authentication, in that order.')
  parser.add_argument('--verbose','-v', help='Give more output than usual.', action='count')
  args = parser.parse_args()

  if not args.key or len(args.key) < 4:
    raise ValueError("Need an API key in order to query LinkedIn.")

  logger = None

  if args.verbose and args.verbose > 0:
    logger = common.logger.getLogger('linkedindownloader',level='info',output='linkedin.log')
  else:
    logger = common.logger.getLogger('linkedindownloader',output='linkedin.log')
  logger.info('Logger initialised')

  linkedinconn = PooledConnection(args.key, LinkedInConnection, logger=logger)
  ps = common.profilestore.ProfileStore(args.database,logger=logger)
  logger.info('Using database \'{}\''.format(args.database))
  lidownloader = LinkedInDownloader(ps, linkedinconn,logger=logger)
  lidownloader.run()


