import pickle
import os
import argparse

try:
  import common.logger
except ImportError as ie:
  from sys import path
  path.append(os.path.abspath('.'))
  path.append(os.path.abspath('..'))
  import common.logger

import twitter.core
import twitter.connect
import twitter.downloader
import twitter.analyser
import common.profilestore
import common.connect


if __name__ == '__main__':
  parser = argparse.ArgumentParser(description='Download Twitter profiles connected to the listed seed profiles.')
  parser.add_argument('infile', help='A file containing a list of twitter profile URLs')
  parser.add_argument('--key','-k',help='The credentials file with consumer key, consumer secret, user token and user secret for Twitter API authentication, in that order per line.')
  args = parser.parse_args()


  logger = common.logger.getLogger('twitterfriends',output='friend-gen.log',level='info')

  #Build a seed database from the input file
  psfile = args.infile+'-seed.db'
  ps = common.profilestore.ProfileStore(psfile,logger=logger)
  
  for line in open(args.infile,'r'):
    record = {}
    record['network'] = 'Twitter'
    record['network_id'] = twitter.core.get_net_id(None,line.strip())
    record['url'] = line.strip()
    record['search_term'] = None
    ps.add_record(record)

  #Download the seed profiles
  if not args.key or len(args.key) < 4:
    raise ValueError("Need an API key in order to query Twitter.")

  twitterconnpool = common.connect.PooledConnection(args.key,twitter.connect.TwitterConnection,logger)
  seeddown = twitter.downloader.TwitterDownloader(ps, twitterconnpool, logger=logger) 

  srawdir = args.infile+'seed-raw'
  sprofdir = args.infile+'seed-profiles'
  seeddown.run(dirpath=srawdir)

  #Convert seed profiles into Profile objects.
  seedanalyser = twitter.analyser.TwitterAnalyser(ps, logger=logger)
  seedanalyser.run(indirpath=srawdir,outdirpath=sprofdir)

  #Build a profilestore of friends
  rpsfile = args.infile+'-results.db' 
  rps = common.profilestore.ProfileStore(rpsfile,logger=logger)
  for f in os.listdir(sprofdir):
    p = pickle.load(open(sprofdir+os.sep+f,'rb'))
    idlist = [ u.uid for u in p.interacted + p.followers + p.followed_by + p.grouped]
    for uid in idlist:
      record = {}
      record['network'] = 'Twitter'
      record['network_id'] = uid
      record['url'] = 'http://twitter.com/'+str(uid)
      record['search_term'] = p.uid
      rps.add_record(record)

  #Download results
  rawdir = args.infile+'results-raw'
  profdir = args.infile+'results-profiles'
  
  resultsdown = twitter.downloader.TwitterDownloader(rps, twitterconnpool, logger=logger, include_connections=True) 
  resultsdown.run(dirpath=rawdir)

  #Farm results into profile form
  analyser = twitter.analyser.TwitterAnalyser(rps, logger=logger)
  analyser.run(indirpath=rawdir, outdirpath=profdir)
