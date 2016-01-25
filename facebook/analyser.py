import argparse
import datetime
import time

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

class FacebookAnalyser(common.analyser.Analyser):
  
  network_name = 'Facebook'
  datestring = "%Y-%m-%dT%H:%M:%S+0000"

  def _analyse_main(self, result, profile):
    for n in ['name','first_name','last_name','id']:
      if n in result:
        profile.names.append(result[n])
    
    for d in ['about','bio']:
      if d in result:
        profile.self_descriptions.append(result[d])
    
    #various attempts at getting the age
    if 'birthday' in result:
      try:
        bday = result['birthday']
        diff = datetime.date.today() - datetime.date(int(bday[6:]),int(bday[:2]),int(bday[3:5]))
        profile.age = int(diff.days/365)
      except Exception as e:
        logging.warn("Unable to parse birthdate: {0}".format(e))
        pass
    if profile.age == 0 and 'age_range' in result:
      minages = result['age_range']['min']
      maxages = result['age_range']['max']
      minage = sum(minages)/len(minages)
      maxage = sum(maxages)/len(maxages)
      profile.age = (minage + maxage)/2
    
    if 'cover' in result and 'source' in result['cover']:
      profile.profile_images.append(self.imagestore.save(result['cover']['source']))
    
    if 'education' in result:
      for e in result['education']:
        profile.eduation.append(e['school'])
      
    if 'email' in result:
      profile.email_addresses.append(result['email'])
    
    if 'website' in result:
      profile.web_links.append(result['website'])
      
    if 'work' in result:
      for w in result['work']:
        profile.occupation = w['employer']
        if 'end_date' not in w:
          break
      
    if 'gender' in result:
      profile.gender = result['gender']
      
    if 'relationship_status' in result:
      profile.relationship_status = result['relationship_status'] 
      
    if 'religion' in result:
      profile.religion = result['religion']
      
    if 'is_verified' in result and result['is_verified']:
      profile.verified = True
      
    if 'location' in result:
      profile.current_location = common.analyser.Location(result['location'])
    elif 'hometown' in result:
      profile.current_location = common.analyser.Location(result['hometown'])
    if profile.current_location:
      profile.location_set.append(profile.current_location)
    return profile


  def _analyse_links(self, result, profile):
    if 'data' not in result or len(result['data']) < 1:
      return profile
    lnks = result['data']
    for l in lnks:
      
      opinion = None
      thetime = None
      if 'created_time' in l:
        thetime = time.strptime(l['created_time'],self.datestring)
        profile.activity_timestamps.append(thetime)
      
      if 'message' in l:
        profile.content.append(common.analyser.Content(common.analyser.Content.TEXT,l['message'],thetime,None,None,opinion))
      if 'picture' in l:
        profile.content.append(common.analyser.Content(common.analyser.Content.IMAGE,self.imagestore.save(l['picture']),thetime,None,None,opinion))
      if 'link' in l:
        profile.content.append(common.analyser.Content(common.analyser.Content.LINKS,l['link'],thetime,None,None,opinion))
    return profile


  def _analyse_comments(self, result, profile):
    if 'data' not in result or len(result['data']) < 1:
      return profile
    comments = result['data']
    #for each comment, if it was made by this user, store the content, else add the originating user as an interaction.
    for c in comments:
      if 'from' in c:
        u = c['from']
        if 'message' in c and u['id'] == profile.uid:
          thetime = time.strptime(c['created_time'],self.datestring)
          profile.activity_timestamps.append(thetime)
          opinion = c['like_count']
          profile.content.append(common.analyser.Content(common.analyser.Content.TEXT,c['message'],thetime,None,None,opinion))
          if 'attachment' in c:
            if 'media' in c['attachment'] and 'image' in c['attachment']['media']:
              profile.content.append(common.analyser.Content(common.analyser.Content.IMAGE,self.imagestore.save(c['attachment']['media']['src']),thetime,None,None,opinion))
            elif 'url' in c['attachment']:
              profile.content.append(common.analyser.Content(common.analyser.Content.LINKS, c['attachment']['url'],thetime,None,None,opinion))
        else:
          profile.interacted.append(self._analyse_main(u,common.analyser.Profile(u['id'],self.network_name,profile.uid)))
    return profile
    

  def analyse(self, response_obj, record):
    profile = common.analyser.Profile(record['network_id'], self.network_name, record['url'])
    for response_dict in response_obj:
      query_url = response_dict['query_url'] 
      result = response_dict['result']
      if not result:
        continue
      elif 'https://graph.facebook.com/' == query_url: 
        profile = self._analyse_main(result, profile)
      elif 'links' in query_url:
        profile = self._analyse_links(result, profile)
      elif 'comments' in query_url:
        profile = self._analyse_comments(result, profile)
      else:
        self.logger.warn("Don't know how to handle URL: {}".format(query_url))
    return profile


if __name__ == '__main__':
  parser = argparse.ArgumentParser(description='Analyse Facebook profiles.',fromfile_prefix_chars='@')
  parser.add_argument('database', help='A CSV ProfileStore to analyse downloaded profiles from')
  parser.add_argument('--verbose','-v', help='Give more output than usual.', action='count')
  parser.add_argument('--names','-n', help='Specify file to store name output in.', default='name_terms.txt')
  args = parser.parse_args()

  logger = None

  if args.verbose and args.verbose > 0:
    logger = common.logger.getLogger('facebookanalyser',level='info',output='facebook.log')
  else:
    logger = common.logger.getLogger('facebookanalyser',output='facebook.log')
  logger.info('Logger initialised')

  ps = common.profilestore.ProfileStore(args.database,logger=logger)
  logger.info('Using database \'{}\''.format(args.database))
  fbanalyser = FacebookAnalyser(ps, logger=logger, namesfile=args.names)
  prefix = args.database[:-7]
  fbanalyser.run(prefix+'-raw',prefix+'-profiles')



