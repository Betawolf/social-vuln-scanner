import argparse
import time
import datetime

try:
  import common.logger
except ImportError as ie:
  from sys import path
  import os
  path.append(os.path.abspath('.'))
  path.append(os.path.abspath('..'))
  import common.logger

import common.profilestore
import common.analyser

class GplusAnalyser(common.analyser.Analyser):
  
  network_name = 'Google+'
  datestring = '%Y-%m-%dT%H:%M:%S'

  def _analyse_main(self, result, profile):
        #names
    for f in ['nickname','displayName']:
      if f in result:
        profile.names.append(result[f])
    if 'name' in result:
      n = result['name']
      for k in ['formatted','familyName','givenName','middleName']:
        if k in n:
          profile.names.append(n[k])
      #tags
      for k in ['honorificSuffix','honorificPrefix']:
        if k in n:
          profile.tags.append(n[k])

    #links
    if 'urls' in result:
      profile.web_links = [u['value'] for u in result['urls'] if u['type'] != 'otherProfile']
      profile.profile_links = [u['value'] for u in result['urls'] if u['type'] == 'otherProfile']

    if 'domain' in result:
      profile.web_links.append(result['domain'])

    #email
    if 'emails' in result:
      profile.email_addresses = [e['value'] for e in result['emails']]

    #description
    for f in ['aboutMe','tagline','braggingRights']:
      if f in result:
        profile.self_descriptions.append(result[f])

    #age
    if 'birthday' in result:
      bday = result['birthday']
      try:
        diff = datetime.date.today() - datetime.date(int(bday[:4]),int(bday[5:7]),int(bday[8:]))
        profile.age = int(diff.days/365)
      except Exception as e:
        self.logger.warn("Unable to parse date: {0}".format(e))
        pass
    if profile.age == 0 and 'ageRange' in result:
      profile.age = int((result['ageRange']['min'] + result['ageRange']['max'])/2)

    #tags
    for f in ['tagline',  'braggingRights', 'skills']:
      if f in result:
        profile.tags.append(result[f])

    #education
    if 'organizations' in result:
      for o in result['organizations']:
        if o['type'] == 'school':
          profile.education.append(o['name'])

    #some more bio
    if 'occupation' in result:
      profile.occupation = result['occupation']
    if 'gender' in result:
      profile.gender = result['gender']
    if 'relationshipStatus' in result:
      profile.relationship_status = result['relationshipStatus']
    if 'verified' in result:
      profile.verified = result['verified']

    #images
    if 'image' in result:
      profile.profile_images.append(self.imagestore.save(result['image']['url']))
    if 'cover' in result and 'coverPhoto' in result['cover']:
      profile.banners.append(self.imagestore.save(result['cover']['coverPhoto']['url']))

    #degree
    if 'circledByCount' in result:
      profile.subscribers = result['circledByCount']
    if 'plusOneCount' in result:
      profile.reputation = result['plusOneCount']
    return profile

  def _analyse_activities(self, result, profile):
    activities = result['items']
    #for every returned activity item
    for a in activities:
      if 'actor' in a:
        #If the activity actor isn't the person, they're an interaction.
        if profile.uid != a['actor']['id']:
          profile.interacted.append(
            self._analyse_main(a['actor'], 
                               common.analyser.Profile(a['actor']['id'], self.network_name, profile.uid)))
      if 'object' in a:
        ao = a['object']
        if 'actor' in ao and 'id' in ao['actor'] and profile.uid != ao['actor']['id']:
          profile.interacted.append(
            self._analyse_main(ao['actor'], 
                               common.analyser.Profile(ao['actor']['id'], self.network_name, profile.uid)))
        thetime = time.strptime(a['published'][:19],self.datestring)
        profile.activity_timestamps.append(thetime)
        #location seems to be doubly encoded
        loc = None
        if 'geocode' in a:
          loc = common.analyser.Location(a['geocode'])
        elif 'location' in a and 'position' in a['location'] and 'latitude' in a['location']['position']:
          pos = a['location']['position']
          loc = common.analyser.Location([pos['longitude'],pos['latitude']],True)

        if loc != None:
          #if we get a location we can tie to a time...
          profile.location_history.append({thetime:loc})
          profile.location_set.append(loc)

        #two options for opinion measures
        opinion = {}
        if 'resharers' in ao:
          opinion['reshares'] = ao['resharers']
        if 'plusoners' in ao:
          opinion['plusones'] = ao['plusoners']

        #add content item
        text = None
        if 'originalContent' in ao:
          text = ao['originalContent']
        elif 'annotation' in ao:
          text = ao['annotation']
      
        if text != None:
          profile.content.append(common.analyser.Content(common.analyser.Content.TEXT,text,thetime,loc,None,opinion))

        #handle attachments for non-text content
        if 'attachments' in ao:
          for att in ao['attachments']:
            if 'objectType' in att:
              if att['objectType'] == 'article' and 'url' in att:
                  profile.content.append(common.analyser.Content(common.analyser.Content.LINKS, att['url'], thetime, loc, None, opinion))
              elif att['objectType'] == 'photo' and 'fullImage' in att and 'url' in att['fullImage']:
                  profile.content.append(common.analyser.Content(common.analyser.Content.IMAGE, self.imagestore.save(att['fullImage']['url']), thetime, loc, None, opinion))
              elif att['objectType'] == 'album' and 'thumbnails' in att:
                for thumb in att['thumbnails']:
                  if 'image' in thumb and 'url' in thumb['image']: 
                    profile.content.append(common.analyser.Content(common.analyser.Content.IMAGE, self.imagestore.save(thumb['image']['url']), thetime, loc, None, opinion))
              elif att['objectType'] == 'video' and 'embed' in att and 'url' in att['embed']:
                  profile.content.append(common.analyser.Content(common.analyser.Content.VIDEO, att['embed']['url'], thetime, loc, None, opinion))
    return profile


  def _analyse_comments(self, result, profile):
    comments = result['items']
    for c in comments:
      if profile.uid != c['actor']['id']:
        profile.interacted.append(
          self._analyse_main(c['actor'], 
                             common.analyser.Profile(c['actor']['id'], self.network_name, profile.uid)))
      else:
        thetime = time.strptime(c['published'][:19],self.datestring)
        profile.activity_timestamps.append(thetime)

        if 'object' in c:
          text = None
          if 'originalContent' in c['object']:
            text = c['object']['originalContent']
          elif 'content' in c['object']:
            text = c['object']['content']

          if text != None:
            profile.content.append(common.analyser.Content(common.analyser.Content.TEXT,text,thetime,None,None,{'plusones':c['plusoners']['totalItems']}))
    return profile

  def _analyse_people(self, result, profile):
    if 'items' in result:
      rlist = result['items']
      for r in rlist:
        profile.interacted.append(self._analyse_main(r, common.analyser.Profile(r['id'],self.network_name, profile.uid)))
    else:
        profile.interacted.append(self._analyse_main(result, common.analyser.Profile(result['id'],self.network_name, profile.uid)))
    return profile

  def analyse(self, response_obj, record):
    profile = common.analyser.Profile(record['network_id'], self.network_name, record['url'])
    for response_dict in response_obj:
      query_url = response_dict['query_url'] 
      result = response_dict['result']
      if not result:
        continue
      elif 'people' in query_url and 'activities' not in query_url:
        profile = self._analyse_main(result, profile)
      elif 'activities' in query_url and 'public' in query_url:
        profile = self._analyse_activities(result, profile)
      elif 'activities' in query_url and ('plusoners' in query_url or 'resharers' in query_url):
        profile = self._analyse_people(result, profile)
      elif 'activities' in query_url and 'comments' in query_url:
        profile = self._analyse_comments(result, profile)
      else:
        self.logger.warn("Don't know how to handle URL: {}".format(query_url))
    return profile
      
        
if __name__ == '__main__':
  parser = argparse.ArgumentParser(description='Analyse Google+ profiles.',fromfile_prefix_chars='@')
  parser.add_argument('database', help='A CSV ProfileStore to analyse downloaded profiles from')
  parser.add_argument('--verbose','-v', help='Give more output than usual.', action='count')
  parser.add_argument('--names','-n', help='Specify file to store name output in.', default='name_terms.txt')
  args = parser.parse_args()

  logger = None

  if args.verbose and args.verbose > 0:
    logger = common.logger.getLogger('gplusanalyser',level='info',output='gplus.log')
  else:
    logger = common.logger.getLogger('gplusanalyser',output='gplus.log')
  logger.info('Logger initialised')

  ps = common.profilestore.ProfileStore(args.database,logger=logger)
  logger.info('Using database \'{}\''.format(args.database))
  runname = args.database.split('.')[0]
  gpanalyser = GplusAnalyser(ps, logger=logger, namesfile=args.names)
  gpanalyser.run(indirpath=runname+'-raw',outdirpath=runname+'-profiles')



