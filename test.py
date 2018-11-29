from proj.receive_tweets import tweetReceiver

import json

tweetReceiver.apply_async(("@KenyaPower_Care Power out in Ruaka ac no. 14242770247. Please address.",))

# make your tests more broad and automatic.

# run throught the series of electricity tweets and see how your function behaves according to that data

with open('at_kenya_power_tweets.json') as data_file:
    data = json.load(data_file)
    for tweet in data:
    	print tweet
        # print 'sending tweet to queue'
        # print tweet['tweet']
        tweetReceiver.apply_async((tweet,))
