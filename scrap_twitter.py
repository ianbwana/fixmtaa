from __future__ import absolute_import

import os
import io, json

import tweepy # comparing tweepy and twitter python api

from twitter import Twitter, OAuth, TwitterHTTPError

# get auth credentials from environment variables
CONSUMER_KEY = os.environ.get('TWITTER_API_KEY')
CONSUMER_SECRET = os.environ.get('TWITTER_API_SECRET')
ACCESS_TOKEN = os.environ.get('TWITTER_ACCESS_TOKEN')
ACCESS_SECRET = os.environ.get('TWITTER_ACCESS_SECRET')

# set tweepy credentials from environment variables
tweepy_auth = tweepy.OAuthHandler(CONSUMER_KEY, CONSUMER_SECRET)
tweepy_auth.set_access_token(ACCESS_TOKEN, ACCESS_SECRET)

# initialize tweepy API
api = tweepy.API(tweepy_auth)

# twitter library credentials
oauth = OAuth(ACCESS_TOKEN, ACCESS_SECRET, CONSUMER_KEY, CONSUMER_SECRET)
t = Twitter(auth=oauth)

current_page = 1  # start script with the first page
list_of_tweets = [] # start with an empty list of tweets

def getTweetsTweepy():
    """
    statuses = api.search(q='@KenyaPower_Care', rrp=100, page=current_page)
    if statuses:
        for status in statuses:
            print 'status recieved'
            list_of_tweets.append(status)
    else:
        print 'no statuses found'
    current_page += 1
    """
    """
    for x in range(1,10):
        statuses = api.search(q='@KenyaPower_Care', rrp=100)
        if statuses:
            for status in statuses:
                print 'status recievd'
                list_of_tweets.append(status.text)
        else:
            print 'no statuses found'
    """
    statuses = tweepy.Cursor(api.search, q='@ZukuOfficial').items(1000)
    if statuses:
        for status in statuses:
            print 'status recieved'
            list_of_tweets.append(status.text)
    else:
        print 'no statuses found'


# give method the list of scrapped tweets
def storeTweets(tweets):
    with io.open('at_zuku_official_tweets.json', 'w', encoding='utf-8') as f:
        f.write(unicode(json.dumps(tweets, ensure_ascii=False)))

# we dont want to lose the list of tweets we have already scrapped in case the stream unexpectedly closes
# so we wrap the entire function in a catch all exception
try:
    getTweetsTweepy();
    storeTweets(tweets=list_of_tweets)
except Exception as e:
    storeTweetsTweepy(tweets=list_of_tweets)
    print e
