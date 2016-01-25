import random
import argparse

datafile = './names/valid_surnames.txt'
maxlen = 128034

def sample(infile, outfile, inlen, outlen):
  linelist = random.sample(range(0,inlen), outlen)
  line_no = 0
  oh = open(outfile,'w')
  for line in open(infile, 'r'):
    if line_no in linelist:
      oh.write(line)
    line_no += 1

if __name__ == '__main__':
  parser = argparse.ArgumentParser(description='Produce a random sample of uncommon surnames')
  parser.add_argument('n', type=int, help='The number of uncommon surnames to sample. Cannot be more than {} (and should not usually be close to that number).'.format(maxlen))
  parser.add_argument('output_file', help='The output file to write to.')
  parser.add_argument('--infile','-i', help='A different file to sample from')
  args = parser.parse_args()
  
  if args.n > maxlen:
    raise ValueError('Requested sample is larger than population.')

  if args.infile:
    sample(args.infile, args.output_file, maxlen, args.n)
  else:
    sample(datafile, args.output_file, maxlen, args.n)
