import argparse
import re
from urllib.parse import urlparse

try:
  import common.logger
except ImportError as ie:
  from sys import path
  import os
  path.append(os.path.abspath('.'))
  path.append(os.path.abspath('..'))
  import common.logger

import common.search 
import common.connect
import common.profilestore
import linkedin.core
import linkedin.connect

class LinkedInSearch(common.search.APISearch):

  network_name = 'LinkedIn'
  search_url   = "https://www.linkedin.com/pub/dir/"

        

  def __init__(self, profilestore=None, logger=None):
    self.connection = linkedin.connect.LinkedInSearchConnection(logger)
    self.profilestore = profilestore
    self.logger = logger

  def _parse_search(self, text):
#    print(text)
    links = []
    if text:
      for line in text.splitlines():
        if 'linkedin.com/in/' in line:
          if 'canonical' in line:
#            print('Match: {}'.format(line))
            link = re.sub('.*href="([^"]*linkedin.com\/in\/[^"]*)".*','\\1',line)
#            print('Link: {}'.format(link))
            links.append(link)
          elif 'Public' in line:
            links += list(set(re.findall('https://www.linkedin.com\/in\/[a-z0-9\-]+',line)))
    return list(set(links))

  def search(self, search_term):
    params = {}
    params['searchType'] = 'fps'
    params['first'] = search_term
    if search_term.count(' ') == 1:
      fname, lname = search_term.split(' ')
      params['first'] = fname
      params['last'] = lname
    text = self.connection.get(LinkedInSearch.search_url, params)
    links = self._parse_search(text)
    result_list = []
    for link in links:
      if self.is_valid_result(link):
        record = {}
        record['network'] = self.network_name
        record['network_id'] = self.get_net_id(link)
        record['url'] = link
        record['search_term'] = search_term
        result_list.append(record)
    return result_list
        

  def is_valid_result(self,url):
    return linkedin.core.is_valid_result(self, url)
    
  def get_net_id(self, url):
    return linkedin.core.get_net_id(self,url) 
     

if __name__ == '__main__':
  parser = argparse.ArgumentParser(description='Search for the input terms on LinkedIn (Google wrapper).',fromfile_prefix_chars='@')
  parser.add_argument('search_term', nargs='?', help='The phrase to search for.')
  parser.add_argument('--file','-f', help='A file containing search terms on each line.') 
  parser.add_argument('--db', help='A CSV file to use as a running profile database.')
  parser.add_argument('--verbose','-v', help='Give more output than usual.', action='count')
  args = parser.parse_args()

  logger = None

  if args.verbose and args.verbose > 0:
    logger = common.logger.getLogger('linkedinsearch',level='info',output='linkedin.log')
  else:
    logger = common.logger.getLogger('linkedinsearch',output='linkedin.log')
  logger.info('Logger initialised')

  if args.db:
    logger.info('Using database \'{}\''.format(args.db))
    ps = common.profilestore.ProfileStore(args.db.strip(),logger=logger)
    lisearch = LinkedInSearch(profilestore=ps,logger=logger)
  else:
    lisearch = LinkedInSearch(logger=logger)
  if args.file:
    results = lisearch.search_all(filename=args.file.strip())
    if not results:
      exit("No results")
    for term in results:
      print("\n\"{}\":".format(term))
      for item in results[term]:
        print("\t{}".format(item))
  elif args.search_term:
    results = lisearch.search(args.search_term)
    if not results:
      exit("No results")
    for item in results:
      print(item)
  else:
    raise ValueError("Need a search term to use in queries.")
