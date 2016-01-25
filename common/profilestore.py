import os
import csv

try:
  import common.logger
except ImportError as ie:
  from sys import path
  path.append(os.path.abspath('.'))
  path.append(os.path.abspath('..'))
  import common.logger


class ProfileStore:
  
  fieldnames = ['uid','network','network_id','url','search_term']
  

  def __init__(self, filename, logger=None):
    self.records = []
    self.curuid = 0
    if not logger:
      logger = common.logger.getLogger('profile_store')
    self.logger = logger
    if os.path.exists(filename):
      reader = csv.DictReader(open(filename,'r'),self.fieldnames)
      for row in reader:
        self.records.append(row)
        self.curuid = int(row['uid'])
    self.outputwriter = csv.DictWriter(open(filename,'a'),self.fieldnames)
    self.logger.info("Initialised ProfileStore, curid={}".format(self.curuid))
     

  def add_record(self, record):
    """ Add a profile to the record. Checks is_new. 
    Returns the unique ID assigned to the record. """
    match = self.get_match(record)
    if not match:
      self.curuid += 1
      record['uid'] = self.curuid
      self.records.append(record)
      self.outputwriter.writerow(record)
    else:
      self.logger.info("Record `{}` is not new, ignoring.".format(record['network_id']))
      return match['uid']
    return self.curuid


  def get_match(self, record):
    """ Check an added record would be new. """
    for rec in self.records:
      if rec['network_id'] == record['network_id'] and rec['network'] == record['network']:
        return rec
    return None
