import argparse

try:
  import common.logger
except ImportError as ie:
  from sys import path
  import os
  path.append(os.path.abspath('.'))
  path.append(os.path.abspath('..'))
  import common.logger

import common.search
import common.profilestore
from gplus.connect import GoogleConnection


class GPlusSearch(common.search.APISearch):
  
  gplus_url = 'https://www.googleapis.com/plus/v1/people'
  network_name = 'Google+'

  def search(self, search_term, limit=True):
    params = {'query' : search_term}
    result_list = []
    while(True):
      result = self.connection.get(self.gplus_url, params)
      self.logger.info(result)
      if not result or 'items' not in result or len(result['items']) < 1:
        #Filter searches with no items.
        self.logger.info('No more results for {}'.format(search_term))
        if len(result_list) == 0:
          return None
        else:
          return result_list
      if limit and 'totalItems' in result and result['totalItems'] >= 300:
        #Filter searches we know will have too many items. 
        self.logger.info('Too many results for {} : {}'.format(search_term,result['totalItems']))
        return None
      for ri in result['items']:
        if 'id' in ri and 'url' in ri:
          record = {}
          record['network'] = self.network_name
          record['network_id'] = ri['id']
          record['url'] = ri['url']
          record['search_term'] = search_term
          result_list.append(record)
      if 'nextPageToken' in result:
        params['pageToken'] = result['nextPageToken']
      else:
        break
    return result_list
    

  def search_all(self, filename, limit=True):
    if limit:
      return super().search_all(filename, results_filter=(lambda x: x is not None and len(x) > 0 and len(x) < 300))
    else:
      return super().search_all(filename)


if __name__ == '__main__':
  parser = argparse.ArgumentParser(description='Search Google+ for the input terms.',fromfile_prefix_chars='@')
  parser.add_argument('search_term', nargs='?', help='The phrase to search for.')
  parser.add_argument('--file','-f', help='A file containing search terms on each line.') 
  parser.add_argument('--key','-k',help='The API keys file for Google+.')
  parser.add_argument('--db', help='A CSV file to use as a running profile database.')
  parser.add_argument('--verbose','-v', help='Give more output than usual.', action='count')
  args = parser.parse_args()

  if not args.key:
    raise ValueError("Need an API key in order to query Google+.")

  logger = None

  if args.verbose and args.verbose > 0:
    logger = common.logger.getLogger('gplussearch',level='info',output='gplus.log')
  else:
    logger = common.logger.getLogger('gplussearch',output='gplus.log')
  logger.info('Logger initialised')

  gplusconn = common.connect.PooledConnection(args.key, GoogleConnection, logger) 
  if args.db:
    logger.info('Using database \'{}\''.format(args.db))
    ps = common.profilestore.ProfileStore(args.db.strip(),logger=logger)
    gpsearch = GPlusSearch(gplusconn,profilestore=ps,logger=logger)
  else:
    gpsearch = GPlusSearch(gplusconn,logger=logger)
  if args.file:
    results = gpsearch.search_all(filename=args.file.strip())
    if not results:
      exit("No results")
    for term in results:
      print("\n\"{}\":".format(term))
      for item in results[term]:
        print("\t{}".format(item))
  elif args.search_term:
    results = gpsearch.search(args.search_term)
    if not results:
      exit("No results")
    for item in results:
      print(item)
  else:
    raise ValueError("Need a search term to use in queries.")
