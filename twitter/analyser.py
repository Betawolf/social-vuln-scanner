import argparse
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

class TwitterAnalyser(common.analyser.Analyser):
  
  network_name = 'Twitter'
  datestring = "%a %b %d %H:%M:%S +0000 %Y"

  def _analyse_show(self, result, profile):
    if 'entities' in result and 'url' in result['entities'] and 'urls' in result['entities']['url']:
      profile.web_links = [u['expanded_url'] for u in result['entities']['url']['urls']]
    if 'name' in result:
      profile.names.append(result['name'])
      profile.names.append(result['screen_name'])
      profile.names.append(result['id_str'])
    if 'description' in result:
      profile.self_descriptions.append(result['description'])
    if 'verified' in result:
      profile.verified = result['verified']
    if 'profile_image_url' in result:
      profile.profile_images.append(self.imagestore.save(result['profile_image_url']))
    if 'profile_background_url' in result:
      profile.banners.append(self.imagestore.save(result['profile_background_image_url']))

    if 'created_at' in result:
      create_str = result['created_at']
      profile.membership_date = time.strptime(create_str,self.datestring)

    if 'location' in result:
      cloc = common.analyser.Location(result['location'])
      profile.current_location = cloc
      profile.location_set.append(cloc)

    if 'time_zone' in result:
      profile.location_set.append(common.analyser.Location(result['time_zone']))

    if 'followers_count' in result:
      profile.subscribers = result['followers_count']
    if 'friends_count' in result:
      profile.subscribed = result['friends_count']
    if 'statuses_count' in result:
      profile.contributions = result['statuses_count']
    if 'favorites_count' in result:
      profile.visibility = result['favorites_count']
    return profile

  def _analyse_statuses(self, result, profile):
    for status in result:
      print(status)
      category = None
      if 'entities' in status :
        se = status['entities']
        #add interactions
        if 'user_mentions' in se:
          for um in se['user_mentions']:
            profile.interacted.append(self._analyse_show(um,common.analyser.Profile(um['id'], self.network_name, profile.uid)))
        #handle category info
        if 'hashtags' in se:
          category = [ht['text'] for ht in se['hashtags']]  

      #handle time
      if 'created_at' in status:
        statustime = time.strptime(status['created_at'],self.datestring)
        profile.activity_timestamps.append(statustime)

      #handle location
      location = None
      if 'coordinates' in status and status['coordinates'] and 'coordinates' in status['coordinates']:
        self.logger.info("Creating {}.".format(status['coordinates']['coordinates']))
        location = common.analyser.Location(status['coordinates']['coordinates'],True)
      elif 'place' in status and status['place']:
        location = common.analyser.Location(status['place'])
      if location:
        profile.location_history.append({statustime:location})
        profile.location_set.append(location)

      #handle opinions
      opinions = {}
      if 'retweet_count' in status:
        opinions['retweet'] = status['retweet_count']
      if 'favorite_count' in status:
        opinions['favourite'] = status['favorite_count']

      #create content item for text
      if 'text' in status:
        profile.content.append(common.analyser.Content(common.analyser.Content.TEXT,status['text'],statustime,location,category,opinions))
      # if applicable, create content item for media
      if 'media' in status:
        mtype = common.analyser.Content.IMAGE if status['media']['type'] == 'photo' else common.analyser.Content.VIDEO
        profile.content.append(common.analyser.Content(mtype,imagestore.save(status['media']['media_url']),statustime,location,category,opinions))
      # if applicable, create content item for links
      if 'entities' in status and 'urls' in status['entities']:
        for u in status['entities']['urls']:
          profile.content.append(common.analyser.Content(common.analyser.Content.LINKS,u['expanded_url'],statustime, location, category, opinions))
    return profile

  def _analyse_people(self, result, profile):
    users = []
    if 'users' in result:
        for r in result['users']:
          users.append(self._analyse_show(r, common.analyser.Profile(r['screen_name'],self.network_name, profile.uid)))
    else:
      self.logger.warn('No users in result supplied to _analyse_people')
    return users


  def analyse(self, response_obj, record):
    profile = common.analyser.Profile(record['network_id'], self.network_name, record['url'])
    for response_dict in response_obj:
      query_url = response_dict['query_url'] 
      result = response_dict['result']
      if not result:
        continue
      elif 'show' in query_url: 
        profile = self._analyse_show(result, profile)        
      elif 'statuses/user_timeline' in query_url:
        profile = self._analyse_statuses(result, profile)        
      elif 'followers/list' in query_url:
        profile.followed_by = self._analyse_people(result, profile)
      elif 'friends/list' in query_url:
        profile.followers = self._analyse_people(result, profile)
      elif 'contributors' in query_url:
        profile.interacted = self._analyse_people(result, profile)
      else:
        self.logger.warn("Don't know how to handle URL: {}".format(query_url))
    return profile


if __name__ == '__main__':
  parser = argparse.ArgumentParser(description='Analyse Twitter profiles.',fromfile_prefix_chars='@')
  parser.add_argument('database', help='A CSV ProfileStore to analyse downloaded profiles from')
  parser.add_argument('--verbose','-v', help='Give more output than usual.', action='count')
  parser.add_argument('--names','-n', help='Specify file to store name output in.', default='name_terms.txt')
  args = parser.parse_args()

  logger = None

  if args.verbose and args.verbose > 0:
    logger = common.logger.getLogger('twitteranalyser',level='info',output='twitter.log')
  else:
    logger = common.logger.getLogger('twitteranalyser',output='twitter.log')
  logger.info('Logger initialised')

  ps = common.profilestore.ProfileStore(args.database,logger=logger)
  logger.info('Using database \'{}\''.format(args.database))
  twanalyser = TwitterAnalyser(ps, logger=logger, namesfile=args.names)
  twanalyser.run()


        
