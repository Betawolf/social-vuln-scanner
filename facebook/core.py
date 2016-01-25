from urllib.parse import urlparse

from facebook.connect import FacebookConnection
import common.connect

facebook_url = 'https://graph.facebook.com/v2.0/'
network_name = 'Facebook'
domain = 'facebook.com'

def is_valid_result(caller, url):
  try:
    urlparts = urlparse(url)
    return (urlparts.scheme in ['https','http']) and (urlparts.netloc.find(domain) > -1) and ([urlparts.path.find(part) for part in ['/public/','/pages/','/events/']] == [-1,-1,-1])
  except Exception as e:
    caller.logger.warn('Exception testing URL')
    caller.logger.warn(e)
    return False

def get_net_id(caller, url):
  network_id = None
  params = {'id':url}
  connection = None
  if hasattr(caller, 'connection'):
    connection = caller.connection
  else:
    #guess at the default file
    try:
      connection = FacebookConnection(open('fb_cred.config', 'r').readlines()[0].split()[0],caller.logger)
    except:
      caller.logger.warn("Facebook id lookups require an API key file, create fb_cred.config")
      return None
  result = connection.get(facebook_url,params)
  if result and 'id' in result:
    network_id = result['id']
  return network_id
