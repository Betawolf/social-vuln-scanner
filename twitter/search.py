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
from twitter.connect import TwitterConnection

class TwitterSearch(common.search.APISearch):

  network_name = 'Twitter'
  twsearch_url =  'https://api.twitter.com/1.1/users/search.json'

  def search(self, search_term):
    result_list = []
    params = {'q':search_term}
    results = self.connection.get(self.twsearch_url, params)
    if results:
      for item in results:
        if not 'screen_name' in item:
          continue
        record = {}
        record['network'] = self.network_name
        record['network_id'] = item['screen_name']
        record['url'] = "http://twitter.com/{}".format(item['screen_name']) 
        record['search_term'] = search_term
        result_list.append(record)
    return result_list

if __name__ == '__main__':
  parser = argparse.ArgumentParser(description='Search Twitter for the input terms.',fromfile_prefix_chars='@')
  parser.add_argument('search_term', nargs='?', help='The phrase to search for.')
  parser.add_argument('--file','-f', help='A file containing search terms on each line.') 
  parser.add_argument('--key','-k', nargs=4, help='The consumer key, consumer secret, user token and user secret for Twitter API authentication, in that order.')
  parser.add_argument('--db', help='A CSV file to use as a running profile database.')
  parser.add_argument('--verbose','-v', help='Give more output than usual.', action='count')
  args = parser.parse_args()

  if not args.key or len(args.key) < 4:
    raise ValueError("Need credentials in order to query Twitter.")

  logger = None

  if args.verbose and args.verbose > 0:
    logger = common.logger.getLogger('twittersearch',level='info',output='twittersearch.log')
  else:
    logger = common.logger.getLogger('twittersearch',output='twittersearch.log')
  logger.info('Logger initialised')

  twconn = TwitterConnection(*args.key,logger=logger)
  if args.db:
    logger.info('Using database \'{}\''.format(args.db))
    ps = common.profilestore.ProfileStore(args.db.strip(),logger=logger)
    twsearch = TwitterSearch(twconn,profilestore=ps,logger=logger)
  else:
    twsearch = TwitterSearch(twconn,logger=logger)
  if args.file:
    results = twsearch.search_all(filename=args.file.strip())
    if not results:
      exit("No results")
    for term in results:
      print("\n\"{}\":".format(term))
      for item in results[term]:
        print("\t{}".format(item))
  elif args.search_term:
    results = twsearch.search(args.search_term)
    if not results:
      exit("No results")
    for item in results:
      print(item)
  else:
    raise ValueError("Need a search term to use in queries.")
