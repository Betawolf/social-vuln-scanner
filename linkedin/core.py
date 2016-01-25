from urllib.parse import urlparse

network_name = 'LinkedIn'

def is_valid_result(caller,url):
  try:
    urlparts = urlparse(url)
    return (urlparts.scheme in ['http','https']) and (urlparts.netloc.find('linkedin.com') > -1) and get_net_id(caller, url) != None and (urlparts.path.find('/company/') == -1) and (urlparts.path.find('/dir/') == -1)
  except Exception as e:
    caller.logger.warn('Exception testing URL')
    caller.logger.warn(e)
    return False

def get_net_id(caller, url):
  try: 
    urlparts = urlparse(url)
    splitpath = urlparts.path.replace('pub/','')
    if len(splitpath) < 2:
      return None
    return splitpath
  except Exception as e:
    caller.logger.warn('Exception extracting ID from URL')
    caller.logger.warn(e)
    return None


