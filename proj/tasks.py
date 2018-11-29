from __future__ import absolute_import

from datetime import timedelta, datetime
import time

from celery import Task

from proj.celery import app
from celery.decorators import periodic_task

from proj.analyze import analyzeTweet

import pycassa

# callback classes help to reduce callback hell
# we define on success an failure callbacks where the method is created, and not where it is invoked
# slice out last 3 characters digits from twitter timestamps
# python timestamps work to the second, & not to the millisecond


"""
A Cassandra table created with compact storage can only have one column that is not part of the primary key.
"""

@app.task
def save_raw_tweet_to_cassandra(tweet):
    pool = pycassa.ConnectionPool('tweets')
    cf_rawtweets_tweetid = pycassa.ColumnFamily(pool, 'rawtweets_tweetid')
    cf_rawtweets_tweettimestamp = pycassa.ColumnFamily(pool, 'rawtweets_tweettimestamp')
    cf_rawtweets_tweetid.insert(tweet['id_str'], {'tweet_text': tweet['text'], 'tweet_timestamp': int(tweet['timestamp_ms'][:-3]), 'user_id': tweet['user']['id_str'], 'user_name': tweet['user']['name'], 'user_screen_name': tweet['user']['screen_name'], 'user_created_at': tweet['user']['created_at']})
    # cf_rawtweets_tweettimestamp.insert(int(tweet['timestamp_ms'][:-3]), {'tweet_text': tweet['text'], 'tweet_timestamp': int(tweet['id_str']), 'user_id': tweet['user']['id_str'], 'user_name': tweet['user']['name'], 'user_screen_name': tweet['user']['screen_name'], 'user_created_at': tweet['user']['created_at']})
    print 'raw tweet stored in cassandra'
    analyzeTweet.apply_async((tweet,))


@periodic_task(run_every=timedelta(seconds= 30))
def read_raw_tweets_from_cassandra():
    pass
