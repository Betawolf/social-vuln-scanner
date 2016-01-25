import argparse
import common.profilestore
import common.logger
import common.connect

import gplus.search
import twitter.search
import linkedin.search
import facebook.search
import gplus.downloader
import twitter.downloader
import linkedin.downloader
import facebook.downloader
import gplus.analyser
import twitter.analyser
import linkedin.analyser
import facebook.analyser
import gplus.connect
import twitter.connect
import linkedin.connect
import facebook.connect






parser = argparse.ArgumentParser(description='Sample profiles linked from Google+.')
parser.add_argument('run_name', help='The name to use for the run and its output files.')
parser.add_argument('namesfile', help='The name file to use for the run.')
parser.add_argument('--gk', help='The keyfile containing one or more Google+ access keys.')
parser.add_argument('--fk', help='The keyfile containing one or more Facebook access keys.')
parser.add_argument('--tk', help='The keyfile containing one or more Twitter access key sets.')
parser.add_argument('--lk', help='The keyfile containing one or more LinkedIn access key sets.')

args = parser.parse_args()

logger = common.logger.getLogger('oneshot', output=args.run_name+'.log', level='info')

db_file = args.run_name+'-db.csv'
logger.info('Database is {}'.format(db_file))
profilestore = common.profilestore.ProfileStore(db_file, logger)


if args.gk:
  gpconn = common.connect.PooledConnection(args.gk, gplus.connect.GoogleConnection, logger)
if args.fk:
  fbconn = common.connect.PooledConnection(args.fk, facebook.connect.FacebookConnection, logger)
if args.tk:
  twconn = common.connect.PooledConnection(args.tk, twitter.connect.TwitterConnection, logger)
if args.lk:
  liconn = common.connect.PooledConnection(args.lk, linkedin.connect.LinkedInConnection, logger)


searchers = []
downers = []
analysers = []

if fbconn:
  searchers.append(facebook.search.FacebookSearch(fbconn, profilestore, logger))
  downers.append(facebook.downloader.FacebookDownloader(profilestore, fbconn, logger))
  analysers.append(facebook.analyser.FacebookAnalyser(profilestore, logger=logger))

if gpconn:
  searchers.append(gplus.search.GPlusSearch(gpconn, profilestore, logger))
  downers.append(gplus.downloader.GplusDownloader(profilestore, gpconn, logger))
  analysers.append(gplus.analyser.GplusAnalyser(profilestore, logger=logger))

if twconn:
  searchers.append(twitter.search.TwitterSearch(twconn, profilestore, logger))
  downers.append(twitter.downloader.TwitterDownloader(profilestore, twconn, logger))
  analysers.append(twitter.analyser.TwitterAnalyser(profilestore, logger=logger))

if liconn:
  searchers.append(linkedin.search.LinkedInSearch(profilestore, logger))
  downers.append(linkedin.downloader.LinkedInDownloader(profilestore, liconn, logger))
  analysers.append(linkedin.analyser.LinkedInAnalyser(profilestore, logger=logger))

raw_dir = args.run_name+'-raw'
prof_dir = args.run_name+'-profiles'

for s in searchers:
  s.search_all(args.namesfile)

for d in downers:
  d.run(dirpath=raw_dir)

for a in analysers:
  a.run(indirpath=raw_dir, outdirpath=prof_dir)
