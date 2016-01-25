from urllib.request import urlopen
import os
import hashlib


class ImageStore:


  def __init__(self, savedir='images', logger=None):
      if not os.path.exists(savedir):
          os.makedirs(savedir)
      self.logger = logger
      logger.info("Images to be saved to '{}'".format(savedir))
      self.SDIR = savedir
      
  def save(self,url):
      """ Take a URL, generate a unique filename, save 
          the image to said file and return the filename."""
      ext = url.split('.')[-1]
      filename = self.SDIR+os.sep+hashlib.md5(url.encode('utf-8')).hexdigest()+'.'+ext
      if os.path.exists(filename):
          self.logger.debug('`{}` already exists'.format(filename))
          return filename
      try:
          self.logger.debug("Logging '{}' to file.".format(url))
          content = urlopen(url).read()
          f = open(filename,'wb') 
          f.write(content)
          f.close()
      except:
          return None
      return filename 
