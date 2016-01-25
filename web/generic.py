from socket import *
from urllib.parse import urlparse
import re
import logging
from bs4 import BeautifulSoup

class Web:

  PORT=1234
  HOST='localhost'
  claimedomains = ['facebook.com','twitter.com','gplus.com','linkedin.com']
  webextensions = ['','.html','.php','.aspx']
  knownpeoplemaps = {}
  PHONE_REGEX='0[0-9 ]{9,}'
  EMAIL_REGEX='[-0-9a-zA-Z.+_]+@[-0-9a-zA-Z.+_]+\.[a-zA-Z]{2,4}'

  @staticmethod
  def makePageName(path):
    if path in ['','/']:
      return 'root.cache'
    else:
      return path.replace('/','^')+'.cache'


  @staticmethod
  def scrapeURL(url):
    if Web.isValidURL(url):
      return urlparse(url).netloc
    else:
      raise Exception("Invalid or excluded URL, cannot create organisation miner.")

  @staticmethod
  def isValidURL(url):
    domain = urlparse(url).netloc
    if domain == '':
      return False
    for cdom in Web.claimedomains:
      if cdom in domain:
        return False 
    else:
      return True

  def regexGet(regex,text):
    return [st for st in re.findall(regex,text) if isinstance(st,str)]

  @staticmethod
  def visibleText(source):
    soup = BeautifulSoup(source)
    texts = soup.find_all(text=True)
    fulltext = ''
    for t in texts:
      ntext = ''
      if t.parent.name not in ['style', 'script', '[document]']:
        ntext = re.sub('<!--.*-->|\r|\n', ' ', str(t), flags=re.DOTALL)
        ntext = re.sub('\s{2,}|&nbsp;', ' ', ntext)
        if t.parent.name == 'td':
          ntext += ';'
      fulltext += ntext+'\n'
    return fulltext

  @staticmethod
  def getEntities(text):
    text = text.replace('\n\n',' ')
    tagged_text = ''
    for line in text.split('\n'):
      s = socket(AF_INET,SOCK_STREAM)
      s.connect((Web.HOST,Web.PORT))
      s.sendall((line+'\n').encode('utf-8'))
      try:
        tagged_text += s.recv(4096).decode('utf-8')
      except Exception as e:
        logging.warn("Error handling entity-tagger result.")
        logging.warn(e)
      s.close()
    return Web.slashTags_parse_entities(tagged_text)


  @staticmethod
  def allowableSubname(name, subname):
    if len(name) < len(subname):
      #too long to be a subname
      return False
    if name.find(subname) != -1:
      #simple substring
      return True
    elif subname.find(' ') or subname.find('.'):
      nameparts = name.replace('.',' ').split()
      subnameparts = subname.replace('.',' ').split()
      matches = []
      for snp in subnameparts: 
        match = False
        index = -1
        if snp in nameparts:
          match = True
          index = nameparts.index(snp)
        else:
          for np in nameparts:
            if np.find(snp) == 0:
              match = True
              index = nameparts.index(np)
              break
        if match:
          matches.append(index)
      unique = matches == list(set(matches))
      ordered = matches == sorted(matches)
      if unique and ordered and len(matches) == len(subnameparts):
        return True
    return False

  @staticmethod
  def resolvePeople(people):
    pstr = ';'.join(people)
    if pstr in Web.knownpeoplemaps:
      return Web.knownpeoplemaps[pstr]
    best = {}
    for person in people:
      matches = []
      for person2 in people:
        if person2 != person and Web.allowableSubname(person, person2):
          matches.append(person2)
      best[person] = matches
    toremove = []
    for person in best:
      if best[person] != []:
         toremove += best[person]
    toremove = list(set(toremove))
    for rm in toremove:
      del best[rm]
    Web.knownpeoplemaps[pstr] = best
    return best  

  @staticmethod
  def slashTags_parse_entities(tagged_text):
    """Thanks to dat hoang, https://github.com/dat.
    Return a list of token tuples (entity_type, token) parsed
    from slashTags-format tagged text.
    :param tagged_text: slashTag-format entity tagged text
    """
    import re
    from itertools import groupby
    from operator import itemgetter
    SLASHTAGS_EPATTERN = re.compile(r'(.+?)/([A-Z]+)?\s*')
    entities = (match.groups()[::-1] for match in SLASHTAGS_EPATTERN.finditer(tagged_text))
    entities = ((etype, " ".join(t[1] for t in tokens)) for (etype, tokens) in groupby(entities, key=itemgetter(0)) if etype != None)
    entities = dict((first, list(map(itemgetter(1), second))) for (first, second) in groupby(sorted(entities, key=itemgetter(0)), key=itemgetter(0)))
    if 'O' in entities:
      del entities['O']
    return entities
