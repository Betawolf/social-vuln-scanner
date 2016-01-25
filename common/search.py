import argparse

try:
  import common.logger
except ImportError as ie:
  from sys import path
  import os
  path.append(os.path.abspath('.'))
  print(path)
  import common.logger

from common.connect import MediaConnection
from urllib.request import unquote

class Search:

  def search(self,  search_term):
    raise NotImplementedError('`search()` not implemented for {}'.format(self.__class__.__name__))

  def search_all(self, filename, results_filter=(lambda x: x is not None and len(x) > 0)):
    """ Return a dictionary mapping between input search terms and search
    results. """
    infile  = open(filename,'r')
    results = {}
    for line in infile:
      term = line.strip()
      term_results = self.search(term)
      if results_filter(term_results):
        results[term] = term_results
    return results


class APISearch(Search):

  def __init__(self, connection, profilestore=None, logger=None):
    self.connection = connection
    self.profilestore = profilestore
    if not logger:
      logger = common.logger.getLogger(self.__class__.__name__)
    self.logger = logger

 
  def search_all(self, filename, results_filter=(lambda x: x is not None and len(x) > 0)):
    """ Return a dictionary mapping between input search terms and search
    results. If a ProfileStore has been passed, output to that."""
    infile  = open(filename,'r')
    results = {}
    for line in infile:
      term = line.strip()
      term_results = self.search(term)
      if results_filter(term_results):
        results[term] = term_results
        if self.profilestore:
          for record in term_results:
            self.profilestore.add_record(record)
      else:
        self.logger.info('`{}` does not meet filter, skipping results'.format(term))
    return results

class ProxiedAPISearch(APISearch):
  
  def __init__(self,domain,profilestore=None,logger=None):
    if not logger:
      logger = common.logger.getLogger(self.__class__.__name__)
    self.logger = logger
    self.domain = domain
    self.proxy = GoogleSearch(logger=logger,restrict_to=[domain])
    self.profilestore = profilestore

  def is_valid_result(self,url):
    """ A dumb default for easy acceptance."""
    return domain in url

  def get_net_id(self,url):
    raise NotImplementedError('Do not know how to get ID from `{}`'.format(url))

  def search(self, search_term):
    links = self.proxy.search('insite:{} {}'.format(self.domain, search_term))
    result_list = []
    if not links or len(links) < 1:
      return None 
    for link in links:
      if self.is_valid_result(link):
        record = {}
        record['network'] = self.network_name
        record['network_id'] = self.get_net_id(link)
        record['url'] = link
        record['search_term'] = search_term
        result_list.append(record)
    return result_list


class GoogleSearch(Search):

  google_url = 'http://www.google.com/search'

  def __init__(self, logger=None, restrict_to=[]):
    if not logger:
      logger = common.logger.getLogger(self.__class__.__name__)
    self.logger = logger
    self.connection = MediaConnection(logger)
    self.restrict_to = restrict_to
    self.connection.delay=1
  
  def search(self, search_term):
    #Perform the search and get the text of the page.
    params = {'q' : search_term,
              'btnG' : 'Google Search'}
    text = self.connection.get(GoogleSearch.google_url, params)
    if not text:
      return None
    #Pull out the links of results
    start = text.find('<div id="res">')
    end = text.find('<div id="foot">')
    if text[start:end] == '':
      self.logger.warn("No results for `{}`".format(search_term))
      return None
    links = []
    text  = text[start:end]
    start = 0
    end   = 0
    while start>-1 and end>-1:
      start = text.find('<a href="/url?q=')
      text = text[start+len('<a href="/url?q='):]
      end = text.find('&amp;sa=U&amp;ei=')
      if start>-1 and end>-1: 
        link = unquote(text[0:end])
        text = text[end:len(text)]
        if link.find('http')==0:
            links.append(link)

    #If necessary, filter the links based on content.
    if len(self.restrict_to) > 0:
      filtered_links = []
      for link in links:
        for domain in self.restrict_to:
          if domain in link:
            filtered_links.append(link)
      links = list(set(filtered_links))
    return links

if __name__ == '__main__':
  parser = argparse.ArgumentParser(description='Simply searches Google for the input terms.')
  parser.add_argument('search_term', nargs='?', help='The phrase to search for.')
  parser.add_argument('--file','-f', help='A file containing search terms on each line.') 
  parser.add_argument('--restrict','-r', nargs='*',help='A list of terms to filter results by.')
  args = parser.parse_args()
  logger = common.logger.getLogger('simple_search','info')
  if args.restrict:
    gs = GoogleSearch(logger, restrict_to=args.restrict)
  else:
    gs = GoogleSearch(logger)
  if args.file:
    results = gs.search_all(args.file)
    if not results:
      print("No results.")
      exit()
    for term in results:
      print("\n\"{}\":".format(term))
      for item in results[term]:
        print("\t{}".format(item))
  elif args.search_term:
    results = gs.search(args.search_term)
    if not results:
      exit("No results.")
    for item in results:
      print(item)
  else:
    logger.error("No input search terms.")

