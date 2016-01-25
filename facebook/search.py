import argparse
from urllib.parse import urlparse

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
import facebook.core
import common.search
import common.profilestore

class FacebookSearch(common.search.APISearch):

  network_name = 'Facebook'
  fbsearch_url =  'https://graph.facebook.com/search'

  def get_net_id(self, url):
    return facebook.core.get_net_id(self, url)

  def is_valid_result(self, url):
    return facebook.core.is_valid_result(self, url)

  def search(self, search_term):
    result_list = []
    params = {'q':search_term, 'type':'user', 'as_user':True}
    results = self.connection.get(self.fbsearch_url, params)
    if results and 'data' in results:
      for item in results['data']:
        record = {}
        record['network'] = self.network_name
        record['network_id'] = item['id']
        record['url'] =  'http://facebook.com/'+str(item['id'])
        record['search_term'] = search_term
        result_list.append(record)
    return result_list
        

if __name__ == '__main__':
  parser = argparse.ArgumentParser(description='Search for the input terms on Facebook (Google wrapper).',fromfile_prefix_chars='@')
  parser.add_argument('search_term', nargs='?', help='The phrase to search for.')
  parser.add_argument('--file','-f', help='A file containing search terms on each line.') 
  parser.add_argument('--key','-k', help='The access token for the app to query the Facebook API')
  parser.add_argument('--db', help='A CSV file to use as a running profile database.')
  parser.add_argument('--verbose','-v', help='Give more output than usual.', action='count')
  args = parser.parse_args()

  if not args.key:
    raise ValueError("Need an API key in order to query Facebook.")

  logger = None

  if args.verbose and args.verbose > 0:
    logger = common.logger.getLogger('linkedinsearch',level='info',output='facebook.log')
  else:
    logger = common.logger.getLogger('linkedinsearch',output='facebook.log')
  logger.info('Logger initialised')

  fbconn = PooledConnection(args.key, FacebookConnection, logger=logger)
  if args.db:
    logger.info('Using database \'{}\''.format(args.db))
    ps = common.profilestore.ProfileStore(args.db.strip(),logger=logger)
    fbsearch = FacebookSearch(connection=fbconn,profilestore=ps,logger=logger)
  else:
    fbsearch = FacebookSearch(connection=fbconn,logger=logger)
  if args.file:
    results = fbsearch.search_all(filename=args.file.strip())
    if not results:
      exit("No results")
    for term in results:
      print("\n\"{}\":".format(term))
      for item in results[term]:
        print("\t{}".format(item))
  elif args.search_term:
    results = fbsearch.search(args.search_term)
    if not results:
      exit("No results")
    for item in results:
      print(item)
  else:
    raise ValueError("Need a search term to use in queries.")
