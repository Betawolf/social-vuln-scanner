import oauth2 as oauth
import urllib.parse  
import sys

if len(sys.argv) < 2:
  print('Need consumer_key and consumer_secret as arguments.')
  exit()
consumer_key           =  sys.argv[1]
consumer_secret        =  sys.argv[2]
consumer = oauth.Consumer(consumer_key, consumer_secret)
client = oauth.Client(consumer)

requestTokenUrl = 'https://api.linkedin.com/uas/oauth/requestToken'
resp, content = client.request(requestTokenUrl, "POST")
if resp['status'] != '200':
  raise Exception("Invalid response %s." % resp['status'])
request_token = urllib.parse.parse_qs(content.decode('utf-8'))

print("Request Token:")
print("    - oauth_token        = %s" % request_token['oauth_token'])
print("    - oauth_token_secret = %s" % request_token['oauth_token_secret'])
authorize_url = 'https://api.linkedin.com/uas/oauth/authorize'
print("Go to the following link in your browser:")
print("%s?oauth_token=%s" % (authorize_url, request_token['oauth_token'][0]))
accepted = 'n'
while accepted.lower() == 'n':
  accepted = input('Have you authorized me? (y/n) ')
oauth_verifier = input('What is the PIN? ')

access_token_url = 'https://api.linkedin.com/uas/oauth/accessToken'
token = oauth.Token(request_token['oauth_token'][0], request_token['oauth_token_secret'][0])
token.set_verifier(oauth_verifier)
client = oauth.Client(consumer, token)
resp, content = client.request(access_token_url, "POST")
access_token = urllib.parse.parse_qs(content.decode('utf-8'))
print(access_token)
print("Access Token:")
print("    - oauth_token        = %s" % access_token['oauth_token'])
print("    - oauth_token_secret = %s" % access_token['oauth_token_secret'])
print("You may now access protected resources using the access tokens above.")
