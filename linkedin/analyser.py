import argparse
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

class LinkedInAnalyser(common.analyser.Analyser):
  
  network_name = 'LinkedIn'

  def _analyse_main(self, result, profile):
    if 'id' in result and result['id'] == 'private':
      self.logger.warn("Profile cache not available. The profile is private.")
      return profile
    
    #Add names
    for nf in ['id','firstName','lastName','maidenName','formattedName',
        'phoneticFirstName','phoneticLastName','formattedPhoneticName']:
      if nf in result:
        profile.names.append(result[nf])

    #Add self-descriptions
    for df in ['summary','specialties']:
      if df in result:
        profile.self_descriptions.append(result[df])

    if 'positions' in result and 'values' in result['positions']:
      for pos in result['positions']['values']:
        if 'summary' in pos:
          profile.self_descriptions.append(pos['summary'])
        if 'title' in pos:
          profile.tags.append(pos['title'])
        if 'name' in pos['company']:
          profile.tags.append(pos['company']['name'])
        if 'industry' in pos['company']:
          profile.tags.append(pos['company']['industry'])
        if 'startDate' in pos and 'year' in pos['startDate']:
          day = pos['startDate']['day'] if 'day' in pos['startDate'] else 1
          month = pos['startDate']['month'] if 'month' in pos['startDate'] else 1
          profile.activity_timestamps.append(datetime.date(pos['startDate']['year'],month,day).timetuple())

    if 'location' in result:
      loc = common.analyser.Location(result['location']['name'])
      profile.current_location = loc
      profile.location_set.append(loc)

    if 'headline' in result:
      profile.occupation = result['headline']
      profile.tags.append(result['headline'])

    if 'industry' in result:
      profile.tags.append(result['industry'])

    if 'numConnections' in result:
      cons = result['numConnections']
      if 'numConnectionsCapped' in result and result['numConnectionsCapped'] != False:
        cons += 1
      profile.subscribers = cons
      profile.subscribed = cons

    if 'pictureUrl' in result:
      profile.profile_images.append(self.imagestore.save(result['pictureUrl']))

    if 'currentShare' in result:
      sh = result['currentShare']
      #convert timestamp format.
      timestamp = datetime.datetime.fromtimestamp(result['currentShare']['timestamp']/1000)
      profile.activity_timestamps.append(timestamp.timetuple())
      profile.last_seen = timestamp
      category = None
      if 'industry' in result:
        category = result['industry']
      if 'comment' in sh:
        content = common.analyser.Content(common.analyser.Content.TEXT, sh['comment'], timestamp, None, category, None)
        profile.content.append(content)
      if 'content' in sh and 'submittedImageUrl' in sh['content']:
        content  = common.analyser.Content(common.analyser.Content.IMAGE, self.imagestore.save(sh['content']['submittedImageUrl']), timestamp, None, category, None)
        profile.content.append(content)
      if 'content' in sh and 'submittedUrl' in sh['content']:
        content  = common.analyser.Content(common.analyser.Content.LINKS, sh['content']['submittedUrl'], timestamp, None, category, None)
        profile.content.append(content)
    return profile


  def analyse(self, response_obj, record):
    profile = common.analyser.Profile(record['network_id'], self.network_name, record['url'])
    for response_dict in response_obj:
      query_url = response_dict['query_url'] 
      result = response_dict['result']
      if not result:
        continue
      elif 'people/url' in query_url: 
        profile = self._analyse_main(result, profile)
      else:
        self.logger.warn("Don't know how to handle URL: {}".format(query_url))
    return profile


if __name__ == '__main__':
  parser = argparse.ArgumentParser(description='Analyse LinkedIn profiles.',fromfile_prefix_chars='@')
  parser.add_argument('database', help='A CSV ProfileStore to analyse downloaded profiles from')
  parser.add_argument('--verbose','-v', help='Give more output than usual.', action='count')
  parser.add_argument('--names','-n', help='Specify file to store name output in.', default='name_terms.txt')
  args = parser.parse_args()

  logger = None

  if args.verbose and args.verbose > 0:
    logger = common.logger.getLogger('linkedinanalyser',level='info',output='linkedin.log')
  else:
    logger = common.logger.getLogger('linkedinanalyser',output='linkedin.log')
  logger.info('Logger initialised')

  ps = common.profilestore.ProfileStore(args.database,logger=logger)
  logger.info('Using database \'{}\''.format(args.database))
  lianalyser = LinkedInAnalyser(ps, logger=logger, namesfile=args.names)
  lianalyser.run()



