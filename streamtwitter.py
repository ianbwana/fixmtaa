from __future__ import absolute_import

import sys

import pprint

"""
Here is where we connect to twitter
Twitter credentials are set up in environment variables, for extra security and convenience
"""

"""
Store, Analze, Report, Reply
"""

import os
import json

from twitter import OAuth, TwitterHTTPError, TwitterStream

from urllib2 import URLError # catch network errors

# from proj.tasks import save_raw_tweet_to_cassandra
from proj.receive_tweets import tweetReceiver

# get auth credentials from environment variables
CONSUMER_KEY = os.environ.get('TWITTER_API_KEY')
CONSUMER_SECRET = os.environ.get('TWITTER_API_SECRET')
ACCESS_TOKEN = os.environ.get('TWITTER_ACCESS_TOKEN')
ACCESS_SECRET = os.environ.get('TWITTER_ACCESS_SECRET')

# give credentials to auth library
oauth = OAuth(ACCESS_TOKEN, ACCESS_SECRET, CONSUMER_KEY, CONSUMER_SECRET)

pp = pprint.PrettyPrinter(indent=4)  # pretty printer for twitter data

twitter_stream = TwitterStream(auth=oauth, block=False)

# twitter_stream creates an iterator that we can use to read tweets from the stream

try:
    iterator = twitter_stream.statuses.filter(track="fixmtaa")
except URLError:
    print 'please check your network connection'
    sys.exit(0)

print 'Streaming tweets...'

# read all tweets in the iterator
for tweet in iterator:
    if tweet is not None:
        pp.pprint(tweet)
        # save_raw_tweet_to_cassandra.apply_async((tweet,))
        tweetReceiver.apply_async((tweet,))
        print 'raw tweet sent to be saved in cassandra'
