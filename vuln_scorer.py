import os
import argparse
import pickle
import editdistance
import datetime

import resolver

import common.logger
import common.connect

import gplus.core
import facebook.core
import twitter.core
import linkedin.core

import gplus.connect
import facebook.connect
import twitter.connect
import linkedin.connect

import gplus.search
import facebook.search
import twitter.search
import linkedin.search

import gplus.downloader
import facebook.downloader
import twitter.downloader
import linkedin.downloader

import gplus.analyser
import facebook.analyser
import twitter.analyser
import linkedin.analyser

import web.orgProfileMiner

#Handle arguments
#- /run_name/ will be used to store the downloaded information, 
#- /url/ is the main web URL of the organisation targeted
#See README for information on keys.
parser = argparse.ArgumentParser(description='Sample profiles linked from Google+.')
parser.add_argument('run_name', help='The name to use for the run and its output files.')
parser.add_argument('url', help='The url of the company website')
parser.add_argument('--gk', help='The keyfile containing one or more Google+ access keys.')
parser.add_argument('--fk', help='The keyfile containing one or more Facebook access keys.')
parser.add_argument('--tk', help='The keyfile containing one or more Twitter access key sets.')
parser.add_argument('--lk', help='The keyfile containing one or more LinkedIn access key sets.')

args = parser.parse_args()

#Initialise logger
logger = common.logger.getLogger('sampling-tool', output=args.run_name+'.log', level='info')
logger.info('Logger initialised.')

#Initialise centralised store
#This is where affiliate profiles will be stored.
resdirname = 'results'
prefix = resdirname+os.sep+args.run_name+os.sep
if not os.path.isdir(prefix):
  os.makedirs(prefix)

db_file = prefix+'db.csv'
logger.info('Database is {}'.format(db_file))
profilestore = common.profilestore.ProfileStore(db_file, logger)
rawdir = prefix+'raw'
profdir = prefix+'profiles'

#Mine website
webdir = prefix+'web'
logger.info('Web store is {}'.format(webdir))
webminer = web.orgProfileMiner.WebOrg.fromURL(args.url)
webminer.getCache(webdir)
logger.info('Website cached.')

#Get social media links referring to the org.
alternates = webminer.getAlternates()
logger.info('Social profiles are {}. Filling seed database.'.format(alternates))

#Prepare seed storage
#This is where the organisation's own profiles will be gathered.
seedpsfile = prefix+'seed-db.csv'
seedrawdir = prefix+'seed-raw'
seedprofdir= prefix+'seed-profiles'
seedps = common.profilestore.ProfileStore(seedpsfile, logger=logger)

#Prime connection handlers.
gpconn = None
fbconn = None
twconn = None
liconn = None

downloaders = []
analysers = []

if args.gk:
  gpconn = common.connect.PooledConnection(args.gk, gplus.connect.GoogleConnection, logger)
  gpdown = gplus.downloader.GplusDownloader(seedps, gpconn, logger)
  gpanal = gplus.analyser.GplusAnalyser(seedps, logger=logger)
  downloaders.append(gpdown)
  analysers.append(gpanal)
if args.fk:
  fbconn = common.connect.PooledConnection(args.fk, facebook.connect.FacebookConnection, logger)
  fbdown = facebook.downloader.FacebookDownloader(seedps, fbconn, logger=logger) 
  fbanal = facebook.analyser.FacebookAnalyser(seedps, logger=logger)
  downloaders.append(fbdown)
  analysers.append(fbanal)
if args.tk:
  twconn = common.connect.PooledConnection(args.tk, twitter.connect.TwitterConnection, logger)
  twdown = twitter.downloader.TwitterDownloader(seedps, twconn, logger=logger, include_connections=True) 
  twanal = twitter.analyser.TwitterAnalyser(seedps, logger=logger)
  downloaders.append(twdown)
  analysers.append(twanal)
if args.lk:
  liconn = common.connect.PooledConnection(args.lk, linkedin.connect.LinkedInConnection, logger)
  lidown = linkedin.downloader.LinkedInDownloader(seedps, liconn, logger=logger) 
  lianal = linkedin.analyser.LinkedInAnalyser(seedps, logger=logger)
  downloaders.append(lidown)
  analysers.append(twanal)

#Create seed records
for url in alternates:
  record = {}
  record['url'] = url
  record['search_term'] = None
  if gpconn and gplus.core.is_valid_result(gpdown, url):
    record['network'] = 'Google+' 
    record['network_id'] = gplus.core.get_net_id(gpdown, url)
    seedps.add_record(record)    
  if twconn and twitter.core.is_valid_result(twdown, url):
    record['network'] = 'Twitter'
    record['network_id'] = twitter.core.get_net_id(twdown, url)
    seedps.add_record(record)    
  if fbconn and facebook.core.is_valid_result(fbdown, url):
    record['network'] = 'Facebook'
    record['network_id'] = facebook.core.get_net_id(fbdown, url)
    seedps.add_record(record)    
  if liconn and linkedin.core.is_valid_result(lidown, url):
    record['network'] = 'LinkedIn'
    record['network_id'] = linkedin.core.get_net_id(lidown, url)
    seedps.add_record(record)    

#Download seed profiles
logger.info('Beginning seed download phase')
for d in downloaders:
 d.run(dirpath=seedrawdir)

logger.info('Beginning seed analysis phase')
for a in analysers:
  a.run(indirpath=seedrawdir, outdirpath=seedprofdir)

#Transfer affiliated profiles to central store.
for f in os.listdir(seedprofdir):
  p = pickle.load(open(seedprofdir+os.sep+f,'rb'))
  idlist = [u.uid for u in p.interacted + p.followers + p.followed_by + p.grouped]
  idlist = list(set(idlist))
  for uid in idlist:
      record = {}
      record['network'] = p.network
      record['network_id'] = uid
      record['url'] = str(uid)
      record['search_term'] = p.uid
      profilestore.add_record(record)

#Download affiliate profiles
#(change of profilestore from prior, but re-use connections).
logger.info('Beginning affiliate download phase')
for d in downloaders:
  d.profilestore = profilestore
  d.run(dirpath=rawdir)

logger.info('Beginning affiliate analysis phase')
for a in analysers:
  a.profilestore = profilestore
  a.run(indirpath=rawdir, outdirpath=profdir)

logger.info('End of affiliate information gathering')

def string_sim(n1, n2):
    """ Applies Levenshtein distance between strings."""
    if (not n1) or (not n2):
      return 0
    l1 = len(n1)
    l2 = len(n2)
    diff = editdistance.eval(n1,n2)
    return 1-(diff/(l1 if l1 > l2 else l2))


def is_employee(profile, employer_profiles, employee_names, employer_names):
  """ Uses a decision-tree derived algorithm to decide if a profile is an 
  employee of the organisation represented. """
  onsite = False
  for name in profile.names:
    for ename in employee_names:
      nsim = nameDiff(name, ename)
      if nsim > 0.8:
        onsite = True
  hasfirmname = False
  for desc in profile.self_descriptions + [profile.occupation]:
    if not desc:
      continue
    for name in employer_names:
      if name in desc:
        hasfirmname = True
  employer_followed_by = [f.uid for employer_profile in employer_profiles for f in employer_profile.followed_by]
  employer_followers = [f.uid for employer_profile in employer_profiles for f in employer_profile.followers]
  count_followed_by = len([1 for f in profile.followed_by if f.uid in employer_followed_by])
  count_followers = len([1 for f in profile.followers if f.uid in employer_followers])

  if onsite:
    print("Onsite")
    if hasfirmname:
      return True
    else:
      if count_followed_by <= 2:
        if count_followers <= 1 or count_followed_by > 1:
          return True
  return False


logger.info('Identifying Employees')

#Extract the possible names of the company.
employer_names = webminer.getNames()

#Extract the names from the web page content.
#NOTE: REQUIRES the stanford NER package to be running as a server.
employee_names = webminer.getTargets()

employer_profiles = []
employee_profiles = []

#Load all the employer profiles
for record in seedps.records:
  fname = seedprofdir+str(record['uid'])+'.pickle'
  if os.path.exists(fname):
    profile = pickle.load(open(fname,'rb'))
    employer_profiles.append(profile)

#Identify employees
for record in profilestore.records:
  fname = profdir+str(record['uid'])+'.pickle'
  if os.path.exists(fname):
    profile = pickle.load(open(fname,'rb'))
    if is_employee(profile, employer_profiles, employee_names, employer_names):
      employee_profiles.append(profile)

logger.info('Identified {} employees.'.format(len(employee_profiles)))

#Extract the names of the employees, to use as search terms for expansion.
namesfile = prefix+'names.txt'
confirmed_names = []
for profile in employee_profiles:
  bname = profile.bestname()
  if not bname.isnumeric():
    confirmed_names.append(bname)

confirmed_names = list(set(confirmed_names))

wf = open(namesfile,'w')

for name in confirmed_names:
  wf.write('{}\n'.format(n))
wf.close()

logger.info('Wrote {} names to {}'.format(len(confirmed_names), namesfile))

#Set up to download search results.
logger('Initialising expansion DB.')
exp_db = prefix+'expand-db.csv'
exprawdir = prefix+'expand-raw'
expprofdir = prefix+'expand-profiles'
expstore = common.profilestore.ProfileStore(exp_df, logger)

searchers = []

if fbconn:
  searchers.append(facebook.search.FacebookSearch(fbconn, expstore, logger))
if gpconn:
  searchers.append(gplus.search.GPlusSearch(gpconn, expstore, logger))
if twconn:
  searchers.append(twitter.search.TwitterSearch(twconn, expstore, logger))
if liconn:
  searchers.append(linkedin.search.LinkedInSearch(expstore, logger))

#Download search results
logger.info('Beginning expansion search phase')
for s in searchers:
  s.search_all(namesfile)

logger.info('Beginning expansion download phase')
for d in downloaders:
  d.profilestore = expstore
  d.run(dirpath=exprawdir)

logger.info('Beginning expansion analysis phase')
for a in analysers:
  a.profilestore = expstore
  a.run(indirpath=exprawdir, outdirpath=expprofdir)

#Match the employees to any of the expansion results.
logger.info('Resolving identities')
matches = resolver.cross_resolve(employee_profiles, prefix)
matches = resolver.dictify(matches)

def structtodatetime(struct):
  """ Transforms a struct_time to a datetime object.
  This is done so timedeltas can be constructed. 
  
  :param struct_time struct: A time struct
  :return: A datetime object converted from the input. """
  return datetime.datetime(struct.tm_year, struct.tm_mon, struct.tm_mday, struct.tm_hour, struct.tm_min, struct.tm_sec)

#vulnerability item counting phase
counts = {}
for k in ['name', 'occupation', 'email', 'text', 'photo', 'hobbies', 'friends', 'phone', 'activity','docs']:
  counts[k] = 0

logger.info('Calculating per-employee vulnerabilities.')

for employee in employees:
  #array this person's identities
  person = [employee] 
  if employee in matches:
    person = person + matches[employee]

  #a local scoring grid based on the global one
  local_matches = {}
  for k in counts:
    local_matches[k] = False

  #for each profile update the grid
  for profile in person:
    if not local_matches['name'] and any([not n.isnumeric() for n in employee.names]):
      local_matches['name'] = True
    if not local_matches['occupation'] and employee.occupation:
      local_matches['occupation'] = True
    if not local_matches['email'] and len(employee.email_addresses) > 0:
      local_matches['email'] = True
    if not local_matches['phone'] and len(employee.phone_numbers) > 0:
      local_matches['phone'] = True
    if not local_matches['text'] and any([ci.ctype == 3 for ci in employee.content]):
      local_matches['text'] = True
    if not local_matches['activity']:
      updatetimes = [content.time for content in employee.content if content.time != None]
      samedaycount = 0
      for t1,t2 in itertools.combinations(updatetimes,2):
          delta = structtodatetime(t1) - structtodatetime(t2)
          daydiff = abs(delta.days)
          if daydiff == 0:
              samedaycount += 1
      if samedaycount > 1 and samedaycount/len(updatetimes) > 0.05:
        local_matches['activity'] = True
    if not local_matches['photo'] and len(employee.employee_images) > 0:
      local_matches['photo'] = True
    if not local_matches['hobbies'] and employee.habits or employee.tags:
      local_matches['hobbies'] = True
    if not local_matches['friends'] and len(employee.followers) or len(employee.followed_by):
      local_matches['friends'] = True

    for k in local_matches:
      if local_matches[k]:
        counts[k] += 1

#output results
logger.info('Finished per-employee counting.')

print("--Employees Only--")
for k,v in counts.items():
  print("{}:{}".format(k,v))

logger.info('Accessing web-mined data')
counts['email'] += len(webminer.getEmail())
counts['phone'] += len(webminer.getPhone())
counts['docs'] += (len(webminer.getDocs()))
logger.info('Finished counting.')

print("\n--Total--")

for k,v in counts.items():
  print("{}:{}".format(k,v))

bootstrap = counts['name']+counts['email']+counts['phone']+counts['activity']+counts['docs']
accentuator = counts['text']+counts['photo']+counts['hobbies']+counts['friends']
print("Boostrap: {}\nAccentuator: {}".format(bootstrap,accentuator))
 
