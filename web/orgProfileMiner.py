import os
import logging
import time
from urllib.parse import urlparse, urljoin
from urllib.request import urlopen
from sys import path
path.append('../')
import web.generic

from bs4 import BeautifulSoup

class WebOrg:

  crawldelay = 1
  network = 'web'

  def __init__(self, id):
    self.id = id
    self.alternates = []
    self.targets = []
    self.names = None

  @staticmethod
  def fromURL(url):
    wo = WebOrg(web.generic.Web.scrapeURL(url))
    wo.subset = None
    ss = urlparse(url).path
    if ss:
      wo.subset = ss
    return wo

  @staticmethod
  def isValidURL(url):
    return web.generic.Web.isValidURL(url)

  def getLinks(self,url,page,known,checkfunction):
    urls = []
    soup = BeautifulSoup(page)
    for anchor in soup.find_all('a'):
      link = anchor.get('href')
      
      #de-relativise links
      urlparts = urlparse(link)
      if urlparts.netloc == '':
        if len(urlparts.path) > 1 and urlparts.path.find('.') == -1:
          link = link + '/'
        link = urljoin(url,link)
      #check it's a usable, unknown link
      if checkfunction(link) and link not in known:
        urls.append(link)
    return list(set(urls))

  def internalPage(self,link):
    urlparts = urlparse(link)
    extension = os.path.splitext(urlparts.path)[1]
    if self.subset:
      return extension in web.generic.Web.webextensions and urlparts.netloc == self.id and self.subset in urlparts.path
    else:
      return extension in web.generic.Web.webextensions and urlparts.netloc == self.id 

  def externalPage(self,link):
    """ Returns true if the url is a page from one of the claimed domains. """
    urlparts = urlparse(link)
    extension = os.path.splitext(urlparts.path)[1]
    if extension not in web.generic.Web.webextensions:
      return False
    for cd in web.generic.Web.claimedomains:
      if urlparts.netloc.find(cd) != -1:
        return True
    return False
      
  def reversePageName(self,filename):
    url = self.id
    if filename != 'root.cache':
      url += filename.replace('^','/').rstrip('.cache')
    return url

  def getCache(self,storage_dir):
    dirstring = storage_dir+os.sep+self.id
    urls = []
    try:
      os.makedirs(dirstring)
      #placed here so that recaching means skip download (while entry condition below).
      urls = ['http://'+self.id+'/'] 
    except FileExistsError:
      logging.info("Directory '{0}' already exists, we must be re-caching.".format(dirstring))
      pass
    done = []
    while len(urls) > 0:
      url = urls.pop()
      done.append(url)
      try:
        request = urlopen(url,timeout=10)
        page = request.read()
        request.close()
        pagename = web.generic.Web.makePageName(urlparse(url).path)
        out = open(dirstring+os.sep+pagename,'w')
        out.write(page.decode('utf-8'))
        out.close()
        urls = urls + self.getLinks(url,page,urls+done,self.internalPage)
        time.sleep(WebOrg.crawldelay)
      except Exception as e:
        logging.warn(e)
        pass
    logging.info("Out of links. {0} pages freshly cached for {1}".format(len(done),self.id))
    self.cache = dirstring
    self.targets = None
    self.name = None
    return self.cache

  def getEmail(self):
    dirstring = 'webcache'+os.sep+self.id
    emails = []
    files = self.__cachedfiles()
    for f in files:
      filepath = dirstring + os.sep + f
      page = open(filepath,'r').read()
      text = web.generic.Web.visibleText(page)
      emails += web.generic.Web.regexGet(web.generic.Web.EMAIL_REGEX, text)
    return list(set(emails))

  def getPhone(self):
    dirstring = 'webcache'+os.sep+self.id
    numbers = []
    files = self.__cachedfiles()
    for f in files:
      filepath = dirstring + os.sep + f
      page = open(filepath,'r').read()
      text = web.generic.Web.visibleText(page)
      numbers += web.generic.Web.regexGet(web.generic.Web.PHONE_REGEX, text)
    return list(set(numbers))

  def getDocs(self):
    dirstring = 'webcache'+os.sep+self.id
    docs = []
    for f in self.__cachedfiles():
      filepath = dirstring + os.sep + f
      page = open(filepath,'r').read()
      soup = BeautifulSoup(page)
      for anchor in soup.find_all('a'):
        link = anchor.get('href')
        if link and '.pdf' in link:
          docs.append(link)
    return docs
      

  def __cachedfiles(self):
    return [f for f in os.listdir(self.cache)]

  def getAlternates(self):
    if self.alternates:
      return self.alternates
    files = self.__cachedfiles()
    urls = [self.reversePageName(f) for f in files]
    outurls = []
    for f, u in zip(files,urls):
      outurls = outurls + self.getLinks(u, open(self.cache+os.sep+f,'r').read(), outurls, self.externalPage)
    self.alternates = outurls
    return outurls


  def getTargets(self):
    if self.targets:
      return self.targets
    files = self.__cachedfiles()
    people  = []
    for f in files:
      fullpath = self.cache+os.sep+f
      page = open(fullpath,'r').read()
      text = web.generic.Web.visibleText(page)
      entities = web.generic.Web.getEntities(text)
      if 'PERSON' in entities:
        for person in entities['PERSON']:
          if person not in people:
              people.append(person)
    return people

  def getNames(self):
    if not self.names:
      rootfile = self.cache+os.sep+'root.cache'
      if os.path.exists(rootfile):
        logging.info("Rootfile: {}".format(rootfile))
        self.names = [BeautifulSoup(open(rootfile,'r')).html.head.title.string]
      else:
        self.names = [self.id]
    return self.names
