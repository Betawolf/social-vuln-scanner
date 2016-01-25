import logging

levels = {'info' : logging.INFO,
          'debug': logging.DEBUG,
          'warn' : logging.WARN,
          'warning' : logging.WARN,
          'error' : logging.ERROR}

def getLogger(name='default',level='warn',output=None):
  logger = logging.getLogger(name)
  logger.setLevel(levels[level])
  if output:
    fh = logging.FileHandler(output)
    logger.addHandler(fh) 
  return logger
