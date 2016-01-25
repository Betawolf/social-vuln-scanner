import urllib.error
import socket
import http.client
from urllib.request import urlopen
from urllib.parse import urlparse
from sys import path
from bs4 import BeautifulSoup
import os
import logging
path.append('../')
import personalProfile
import resolver
import imagestore
import search
import profileMiner
import web.generic
import web.orgProfileMiner
import config

class WebProfiler(profileMiner.ProfileMiner):

  @staticmethod
  def fromPerson(person):
    approved = None
    for profile in person.profiles:
      res = search.search(profile.bestname(),['twitter.com','facebook.com','plus.google.com','linkedin.com'],True)
      for r in res:
        wp = WebProfiler.fromURL(r)
        if wp:
            resultprofile = wp.getProfile()
            if resultprofile and resolver.areEquivalent(resultprofile,profile):
              approved = resultprofile
              break
    return approved

  @staticmethod
  def fromURL(url):
    if WebProfiler.isValidURL(url):
      try:
        logging.info(url)
        request = urlopen(url,timeout=config.timeout)
        page = request.read()
        request.close()
        soup = BeautifulSoup(page)
        text = '\n'.join([t.get_text() for t in soup.find_all('title')]+[b.get_text() for b in soup.find_all('body') ])
        entities = web.generic.Web.getEntities(text)
      except urllib.error.HTTPError as e:
        logging.warn(e)
        return None
      except urllib.error.URLError as e:
        logging.warn(e)
        return None
      except ConnectionResetError as e:
        logging.warn(e)
        return None
      except UnicodeEncodeError as e:
        logging.warn(e)
        return None
      except http.client.IncompleteRead as e:
        logging.warn(e)
        return None
      except socket.timeout as e:
        logging.warn(e)
        return None
      except RuntimeWarning as e:
        logging.warn(e)
        return None
      except Exception as e:
        logging.warn(e)
        return None
      if 'PERSON' in entities:
        loc = web.generic.Web.scrapeURL(url)
        dirstring =config.output_dir+os.sep+'cache'+os.sep+loc
        try:
          os.mkdir(dirstring)
        except FileExistsError:
          logging.info("Directory '{0}' already exists, we must be re-caching.".format(dirstring))
          pass
        path = dirstring+os.sep+web.generic.Web.makePageName(urlparse(url).path)
        try:
          out = open(path,'w')
          out.write(page.decode('utf-8'))
        except UnicodeDecodeError as e:
          logging.warn("Encoding error: Could not write cache of file.")
          logging.warn(e)
        except OSError as e:
          logging.warn("Encoding error: Could not write cache of file.")
          logging.warn(e)
        wp = WebProfiler(entities['PERSON'][0],[path])
        return wp
      else:
        return None
    else:
      logging.warn("Invalid URL. {}".format(url))
      return None

  @staticmethod
  def isImage(url):
    ext = url.split('.')[-1]
    return ext in ['jpg','jpeg','exif','tiff','rif','gif','bmp','png']
    
  @staticmethod
  def isValidURL(url):
    return web.generic.Web.isValidURL(url)

  @staticmethod
  def reversePath(path):
    cindex = path.find('cache/')
    if cindex == -1 or path[-6:] != '.cache':
      raise Exception("I expect a full cached filepath 'cache/<domain>/<path>.cache'. {0} does not match".format(path))
    path = path[cindex+6:-6]
    return path.replace('^','/')

  @staticmethod
  def slicesOf(searchterm, string):
    slices = []
    nl = len(searchterm)
    searchfrom = 0
    while True:
      index = string.find(searchterm, searchfrom)
      if index == -1:
        break
      searchfrom = index+nl
      slices.append((index,searchfrom))
    return slices

  @staticmethod
  def getLocal(names,strings,text):
    localstrings = []
    allowed = len(text)/15
    name_indices = []
    for n in names:
      name_indices += WebProfiler.slicesOf(n,text)
    name_indices = list(set(name_indices))
    for string in strings:
      string_indices = WebProfiler.slicesOf(string, text)
      for lower, upper in string_indices:
        for nlower, nupper in name_indices:
          if string not in localstrings and (abs(nlower - upper) < allowed or abs(lower - nupper) < allowed):
            localstrings.append(string)
    return localstrings 

  def getCache(self):
    wp = WebProfiler.fromURL(self.url)
    self.cache = wp.cache
    return self.cache

  def mineCache(self):
    names = []
    name = None
    #Unpack the names we packed into the ID
    #in the organisation miner.
    pindex = self.id.find('(')
    if pindex == -1:
      name = self.id
    else:
      name = self.id[:pindex]
      names = self.id[pindex+1:-1].split(',')
    names.append(name)
    domain = ''
    people = []
    locations = []
    organisations = []
    fullbody = []
    urls = []
    email = []
    numbers = []
    for filepath in self.cache:
      try:
        page = open(filepath,'r').read()
      except OSError as e:
        logging.warn(e)
        continue
      domain = urlparse('http://'+WebProfiler.reversePath(filepath)).netloc
      fullbody.append(page)
      soup = BeautifulSoup(page)
#      text = '\n'.join([t.get_text() for t in soup.find_all('title')]+)
      text = web.generic.Web.visibleText(page)

      #Any URLS enclosing a name of this person can be assumed relevant.
      for anchor in soup.find_all('a'):
        for n in names:
          if anchor.text.find(n) != -1:
            url = anchor.get('href')
            if url and url.find('mailto:') == 0:
              email.append(url[7:])
            elif url and url.find(domain) == -1 and WebProfiler.isValidURL(url):
              urls.append(url)

      #For non-enclosed information, we need to know if the whole page is 
      #about this person or not, which we determine from titles.
      localise = True
      for n in names:
        for t in soup.find_all('title')+soup.find_all('head'):
          if n in t.get_text():
            localise = False     

      #Handle entities, and some regexable info.
      page_numbers = web.generic.Web.regexGet(web.generic.Web.PHONE_REGEX, text)
      page_email = web.generic.Web.regexGet(web.generic.Web.EMAIL_REGEX, text)
      entities = web.generic.Web.getEntities(text)
      if 'PERSON' in entities:
        #page-level context should be enough for 'related people'
        people += entities['PERSON']
      if localise:
        numbers += WebProfiler.getLocal(names,page_numbers,text)
        email += WebProfiler.getLocal(names,page_email,page)
        if 'ORGANISATION' in entities:
          organisations += WebProfiler.getLocal(names,entities['ORGANISATION'],text)
        if 'LOCATION' in entities:
          locations += [personalProfile.Location(l) for l in WebProfiler.getLocal(names,entities['LOCATION'],text) if l]
      else:
        numbers += page_numbers
        email += page_email
        if 'ORGANISATION' in entities:
          organisations += entities['ORGANISATION']
        if 'LOCATION' in entities:
          locations += [personalProfile.Location(l) for l in entities['LOCATION'] if l]

    profile = personalProfile.Profile(str(hash(self.id+';'.join(self.cache))),web.orgProfileMiner.WebOrg.network,name+';'.join(self.cache))
    profile.names = names
    profile.education = [o for o in organisations if o.lower().find('school') != -1 or o.lower().find('university') != -1]
    profile.location_set = list(set(locations))
    profile.email_addresses = list(set(email))
    profile.phone_numbers = list(set(numbers))
    people = list(set(people))
    for n in names:
      if n in people:
        people.remove(n)
    for bname, subs in web.generic.Web.resolvePeople(people).items():
        wp = WebProfiler(bname+'('+','.join(subs) + ')',[])
        if wp:
            profile.grouped.append(wp.getProfile())
    urls = list(set(urls))
    email = list(set(urls))
    for u in urls:
      if WebProfiler.isValidURL(u):
        if WebProfiler.isImage(u):
            profile.profile_images.append(imagestore.save(u))
        else:
            profile.web_links.append(u)
      else:
        profile.profile_links.append(u)
    self.profile = profile
    return self.profile


  def extend(self):
    profile = self.profile
    res = search.search(profile.bestname(),['twitter.com','facebook.com','plus.google.com','linkedin.com'],True)
    for r in res:
      wp = WebProfiler.fromURL(r)
      if wp:
        resultprofile =  wp.getProfile()
        if resolver.areEquivalent(resultprofile,profile):
            #merge the mined fields.
            profile.names = list(set(profile.names+resultprofile.names))
            profile.education = list(set(profile.education+resultprofile.education))
            profile.location_set = list(set(profile.location_set+resultprofile.location_set))
            profile.email_addresses = list(set(profile.email_addresses+resultprofile.email_addresses))
            profile.phone_numbers = list(set(profile.phone_numbers+resultprofile.phone_numbers))
            profile.grouped = list(set(profile.grouped+resultprofile.grouped))
            profile.web_links = list(set(profile.web_links+resultprofile.web_links+[r]))
            profile.profile_links = list(set(profile.profile_links+resultprofile.profile_links))
        self.profile = profile
    return self.profile
