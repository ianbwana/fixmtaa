from __future__ import absolute_import

import pycassa

pool = pycassa.ConnectionPool('tweets')

cf_rawtweets_tweetid = pycassa.ColumnFamily(pool, 'rawtweets_tweetid')

# get all raw tweets
def getRawTweets():
    return cf_rawtweets_tweetid.get_range()

# get raw tweets that need to be analyzed
def getRawTweetsToAnalyze():
    pass

def getCategorizedTweets():
    pass

def getCategorizedTweetsToAnalyze():
    pass

def getSentimentTweets():
    pass

def getSentimentTweetsToAnalyze():
    pass
