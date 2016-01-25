import common.analyser
import common.profilestore
import itertools
import math
import logging
import argparse
import editdistance
import pickle
import os


def areEquivalent(profileone,profiletwo,threshold=0.2):
    """Runs a number of comparison functions on the
    two profiles, and uses the results to adjust a prior
    Rules for comparison functions:
     
    1. They should accept two profiles
    2. They should return a value between 0 and 1 reflecting the confidence
       the function has that the two profiles are of the same person.
    3. Where the requirements for a comparison are not met, they should
        throw an exception. 

    :param Profile profileone: A profile object.
    :param Profile profiletwo: A profile object.  
    :return: Boolean result of comparison based on threshold, prior, and comparison functions on the two profiles."""

    coefficients = [9.959, -3.805, 5.480, 4.414, -2333, 35.29, 47.19, 51.87]

    exactNameWeight = sameNames(profileone,profiletwo)

    bestNameWeight = bestNameDiff(profileone,profiletwo)

    timeWeight = timeComparison(profileone,profiletwo)

    avatarWeight = avatarComparison(profileone,profiletwo)

    friendsWeight = friendsComparison(profileone,profiletwo)

    linkWeight = linkAnalysis(profileone,profiletwo)

    stylometricWeight = stylometricComparison(profileone, profiletwo)

    geographyWeight = geographicProfile(profileone,profiletwo)

    interactions = [exactNameWeight*bestNameWeight, 
              exactNameWeight*timeWeight, 
              exactNameWeight*avatarWeight,
              exactNameWeight*friendsWeight,
              exactNameWeight*linkWeight,
              exactNameWeight*stylometricWeight,
              bestNameWeight*timeWeight, 
              bestNameWeight*avatarWeight,
              bestNameWeight*friendsWeight,
              bestNameWeight*linkWeight,
              bestNameWeight*stylometricWeight,
              timeWeight*avatarWeight,
              timeWeight*friendsWeight,
              timeWeight*linkWeight,
              timeWeight*stylometricWeight,
              avatarWeight*friendsWeight,
              avatarWeight*linkWeight,
              avatarWeight*stylometricWeight,
              friendsWeight*linkWeight,
              friendsWeight*stylometricWeight,
              linkWeight*stylometricWeight]

    inter_coeffs = [-3.781, -9.477, -1.164, 3466, 97.84, 154.7, 7.408, -1.646, -832.7, -119.7, -188.4, -3.348, -115.3, 3.647, -20.36, 3207, 55.65, 47.97, -2479, 17210, 141.4]

    inter_terms = [interactions[i]*inter_coeffs[i] for i in range(0, len(inter_coeffs))]
    intercept = -6.819

    level = intercept+sum([exactNameWeight*coefficients[0], bestNameWeight*coefficients[1], timeWeight*coefficients[2], avatarWeight*coefficients[3], friendsWeight*coefficients[4], linkWeight*coefficients[5], stylometricWeight*coefficients[6], geographyWeight*coefficients[7]] + inter_terms)
    exp_l = math.exp(level)
    transformed_level = exp_l/(1+exp_l)
    return transformed_level > threshold


def sameNames(profileone, profiletwo):
  """ Comparison function.
  Counts the number of exactly-matching names this person has.
  As profile IDs can sometimes be added as names, skip those."""
  namecount = 0
  validone = 0
  validtwo = 0
  for n1 in profileone.names:
    if not n1.isnumeric():
      validone += 1
      for n2 in profiletwo.names:
        if not n2.isnumeric():
          validtwo += 1
          if n1 == n2:
            namecount += 1
  minlen = min([validone, validtwo])
  return namecount/minlen


def bestNameDiff(profileone, profiletwo):
    """ Applies Levenshtein distance between best names of two profiles."""
    n1 = profileone.bestname()
    n2 = profiletwo.bestname()
    if (not n1) or (not n2):
      return 0
    l1 = profileone.name_length
    l2 = profiletwo.name_length
    diff = editdistance.eval(n1,n2)
    return 1-(diff/(l1 if l1 > l2 else l2))

    
def timeComparison(profileone, profiletwo):
    """ We use a version of the method from Atig et al. 
        to compare time activity profiles. """
    highthresh = 0.2
    lowthresh = 0.08
    tactprofile1 = profileone.timeProfile()
    tactprofile2 = profiletwo.timeProfile()
    if not tactprofile1 or not tactprofile2:
        return 0
    likelihood = 0
    for period in tactprofile1:
        if tactprofile1[period] > highthresh and tactprofile2[period] > highthresh:
            #This is an activity peak.
            likelihood += 1/6
        elif tactprofile1[period] < lowthresh and tactprofile2[period] < lowthresh:
            #This is an inactivity period.
            likelihood += 1/6
    else:
        return likelihood

    
def avatarComparison(profileone, profiletwo):
    """ Use an image comparison approach to compare the
        profile images from the two profiles, confidence
        being the degree of similarity. Uses rms similarity
        between actual pixel value, so fairly confusable."""
    import operator
    from functools import reduce
    totaldiff=906 #adjusted based on observation
#    totaldiff=453
    h1 = profileone.getImageHistogram()
    h2 = profiletwo.getImageHistogram()
    if not h1 or not h2:
      return 0
    rms = math.sqrt(reduce(operator.add,  list(map(lambda a,b: (a-b)**2, h1, h2)))/len(h1) )
    if rms > totaldiff:
      logging.warn("Heuristic on avatar comparison error is wrong.")
      return 0
    return 1-(rms/totaldiff)


def stylometricComparison(profileone, profiletwo):
    """ Compare the bodies of text attached to each profile.
        Confidence is degree of linguistic similarity. Method is
        euclidean distance of function word proportions.  """
    sig1 = profileone.getWritingStyle()
    sig2 = profiletwo.getWritingStyle()
    if not sig1 or not sig2 or sum([sig1[w] for w in sig1]) == 0 or sum([sig2[w] for w in sig2]) == 0 :
      return 0
    rms = math.sqrt(sum([(sig1[word] - sig2[word]) ** 2 for word in sig1]))
    bl = math.sqrt(sum([(sig1[word] + sig2[word]) ** 2 for word in sig1]))
    return 1-(rms/bl)

    
def linkAnalysis(profileone, profiletwo):
    """ Compare the links made by the two profiles.
        Matches mean greater confidence of a connection."""
    from urllib.parse import urlparse

    try:
      ls1 = profileone.getLinks()
      ds1 = [urlparse(link).netloc for link in ls1]
      ls2 = profiletwo.getLinks()
      ds2 = [urlparse(link).netloc for link in ls2]
    except Exception as e:
      logging.warn(e)
      return 0
    
    score = 0
    if len(ls1) == 0 or len(ls2) == 0:
        return 0
    unit = 1/len(ls1)
    for link, domain in zip(ls1,ds1):
        if link in ls2:
            score += unit
        elif domain in ds2:
            score += unit/3
    return score


def geographicProfile(profileone, profiletwo):
    """ Compare the location fingerprint for the two
        profiles. Have to define overlap. """
    score = 0
    if len(profileone.location_set) < 2 or len(profiletwo.location_set) < 2:
        return 0
    unit=1/(len(profileone.location_set)*len(profiletwo.location_set))
    for l1, l2 in itertools.product(profileone.location_set, profiletwo.location_set):
        if l1.near(l2):
           score += unit
    return score


def friendsComparison(profileone,profiletwo):
    """ Decide whether a person's friends are the same.
        Computably, this is done via name comparison."""
    fs1 = list(set(profileone.interacted + profileone.followers + profileone.followed_by + profileone.grouped))
    fs2 = list(set(profiletwo.interacted + profiletwo.followers + profiletwo.followed_by + profiletwo.grouped))
    if len(fs1) < 2 or len(fs2) < 2:
      return 0
    friendcount = 0
    for f1, f2 in itertools.product(fs1,fs2):
        bdiff = bestNameDiff(f1,f2) 
        if bdiff > 0.8: 
            friendcount += 1
    friendmax = min([len(fs1), len(fs2)])
    if friendcount > friendmax:
      return 1
    return (friendcount/friendmax)


def resolve(profiles):
    """ Takes a big list of profiles, resolves those it can and
    then returns a list of matches consisting of the resolved profiles."""
    matches = []

    estimate = (len(profiles)*(len(profiles)+1))/2
    count = 0
    #For every pair of profiles.
    for pone, ptwo in itertools.combinations(profiles,2):
        count += 1
        logging.info("{} of {}: Comparing '{}' and '{}'".format(count,estimate,pone.uid,ptwo.uid))
        #Skip comparisons between same network profiles.
        if pone.network == ptwo.network:
          continue
        if (not pone.bestname()) or (not ptwo.bestname()):
          continue
        #Compare based on profile content.
        if areEquivalent(pone,ptwo):
          matches.append([pone,ptwo])
    return matches


def cross_resolve(employees, prefix):
  """ Resolve a list of profiles (employees) against a database.
  To reduce comparisons, blocks by the search terms, and assumes that
  the profiles match those terms. """
  pfdir = prefix+'expand-profiles/'
  ps = common.profilestore.ProfileStore(prefix+'expand-db.csv')
  grouped_profiles = []

  for record in ps.records:
    if os.path.exists(pfdir+record['uid']+'.pickle'):
      profile = pickle.load(open(pfdir+record['uid']+'.pickle','rb'))
      profile.rid = record['uid']
      sterm = record['search_term']
      if sterm in grouped_profiles:
        grouped_profiles[sterm].append(profile)
      else:
        grouped_profiles[sterm] = [profile]

  count = 0
  estimate = sum([len(grouped_profiles[t]) for t in grouped_profiles])*len(employees)
  matches = []
  for term in grouped_profiles:
    for employee in employees:
      if employee.bestname() == term:
        for candidate in grouped_profiles[term]:
          count += 1
          logging.info('Resolving {} of at most {}'.format(count, estimate))
          if employee.network == candidate.network:
            continue
          if areEquivalent(employee, candidate):
            matches.append([employee,candidate])

  return matches


def dictify(matches):
  d = {}
  for e, a in matches:
    if e in d:
      d[e].append(a)
    else:
      d[e] = [a]
  return d
