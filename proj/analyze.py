from __future__ import absolute_import

"""
Analyze the tweet and try to figure out what the user means
Before analyzing you have to clean the data
"""

import os

import time

import tweepy  # switch to tweepy for posting to twitter

# import regex
import re
# import Twitter
from twitter import Twitter, OAuth, TwitterHTTPError

# get auth credentials from environment variables
CONSUMER_KEY = os.environ.get('TWITTER_API_KEY')
CONSUMER_SECRET = os.environ.get('TWITTER_API_SECRET')
ACCESS_TOKEN = os.environ.get('TWITTER_ACCESS_TOKEN')
ACCESS_SECRET = os.environ.get('TWITTER_ACCESS_SECRET')

# tweepy library credentials

tweepy_auth = tweepy.OAuthHandler(CONSUMER_KEY, CONSUMER_SECRET)
tweepy_auth.set_access_token(ACCESS_TOKEN, ACCESS_SECRET)

api = tweepy.API(tweepy_auth)

# twitter library credentials
oauth = OAuth(ACCESS_TOKEN, ACCESS_SECRET, CONSUMER_KEY, CONSUMER_SECRET)
t = Twitter(auth=oauth)

# import csv read_raw_tweets_from_cassandra
import csv

# import nltk
import nltk

from proj.celery import app

import pycassa

# ininialize Cassandra connection pool

pool = pycassa.ConnectionPool('tweets') # we can then use this connection pool to connect to Cassandra

domain_recongition_classifier = None
electricity_sentiment_classifier = None
water_sentiment_classifier = None
# issue_recognition_classifier = None

domain_feature_list = []
# issue_feature_list = []
electricity_feature_list = []
water_feature_list = []

def cleanTweet(tweet_text):
    # Convert to lower case
    tweet_text = tweet_text.lower()
    # Convert www.* or https?://* to URL
    tweet_text = re.sub('((www\.[^\s]+)|(https?://[^\s]+))','URL',tweet_text)
    # Convert @username to AT_USER
    tweet_text = re.sub('@[^\s]+','AT_USER',tweet_text)
    #Remove additional white spaces
    tweet_text = re.sub('[\s]+', ' ', tweet_text)
    #Replace #word with word
    tweet_text = re.sub(r'#([^\s]+)', r'\1', tweet_text)
    #trim
    tweet_text = tweet_text.strip('\'"')
    print 'tweet pre-processed:'
    print tweet_text
    return tweet_text

# look for 2 or more repetitions of character and replace with the character itself
def replaceTwoOrMore(word):
    pattern = re.compile(r"(.)\1{1,}", re.DOTALL)
    return pattern.sub(r"\1\1", word)

# split tweet into words
def getFeaturevector(tweet_text):
    feature_vector = []
    words = tweet_text.split()
    for word in words:
        word = replaceTwoOrMore(word=word)
        # strip out punctuation
        word = word.strip('\'"?,.')
        # check if the word stats with an alphabet
        # TODO: find out if this works for Swahili
        # val = re.search(r"^[a-zA-Z][a-zA-Z0-9]*$", word)
        # TODO: Add list of stop words that don't add meaning to the feature vector
        feature_vector.append(word.lower())
    return feature_vector

# use this to extract features of a domain
def domainExtractFeatures(feature_vector):
    tweet_words = set(feature_vector)  # remove duplicate vectors from tweet
    features = {}
    # print 'showing domain list:'
    # print domain_feature_list
    for word in domain_feature_list:
        domain = None
        # print 'searh for word below in domain list:'
        # print word[0]
        if word[0] in tweet_words:
            # print 'word found'
            domain = word[1]  # if keyword is mentioned in tweet words, add it to as a mentioned category
        else:
            # print 'word not found'
            domain = 'toanalyze' # if it wasn't mentioned then, we put it in the undefined category
        features['domain mention (%s)' % word[0]] = domain # find out if the set contains the words in the domain feature list
    return features

def electricityExtractFeatures(feature_vector):
    tweet_words = set(feature_vector)
    features = {}
    for word in electricity_feature_list:
        domain = None
        if word[0] in tweet_words:
            domain = "negative"  # True, in the sence that this could be a negative tweet
        else:
            domain = "toanalyze"  # when the algorithm thinks that the sentiment is not negative
        features['negativity meantioned (%s)' % word[0]] = domain
    return features

def waterExtractFeatures(feature_vector):
    tweet_words = set(feature_vector)
    features = {}
    for word in water_feature_list:
        domain = None
        if word[0] in tweet_words:
            domain = "negative"
        else:
            domain = "toanalyze"
        features['negativity mentioned (%s)' % word[0]] = domain
    return features

def getDomainRecognitionList():
    domain_keywords_csv = open('proj/domain_keywords.csv', "rb")
    reader = csv.reader(domain_keywords_csv)

    domain_list = [] # tuple containing a word and its domain

    # specific for electricity
    # TODO: Switch to a more generalized csv file, that will work for new domains
    for row in reader:
        if row[0] is not None:
            if row[0] != "":
                domain_list.append((row[0],'electricity'))
        if row[1] is not None:
            if row[1] != "":
                domain_list.append((row[1],'water'))
    print 'Domain list:'
    print domain_list
    return domain_list

def getElectricityRecognitionList():
    # TODO: Make recognition smarter by creating a better feature extractor. Should recognize tweets like 'no power outage' as not being negative
    domain_keywords_csv = open('proj/electricity_sentiment.csv', "rb")
    reader = csv.reader(domain_keywords_csv)
    domain_list = []  # tuple (tag,sentiment)
    for row in reader:
        domain_list.append((row[0],row[1]))
    return domain_list

def getWaterRecognitionList():
    domain_keywords_csv = open('proj/water_sentiment.csv', "rb")
    reader = csv.reader(domain_keywords_csv)
    domain_list = []  # tuple (tag, sentiment)
    for row in reader:
        domain_list.append((row[0],row[1]))
    return domain_list

def getDommainRecognitionTrainingSet():
    # TODO: Read data from domain_training_set.csv, pass it to you extractor & use that information and results to train your classifier
    domain_training_set_csv = open('proj/domain_training_set.csv',"rb")
    reader = csv.reader(domain_training_set_csv)
    training_set = []  # training set is a list of tuples (features, 'result')
    for row in reader:
        cleaned_tweet_text = cleanTweet(tweet_text=row[0])
        feature_vector = getFeaturevector(tweet_text=cleaned_tweet_text)
        training_set.append((domainExtractFeatures(feature_vector=feature_vector), row[1]))  # result of feature extraction, & expected result
    return training_set

def getElectricitySentimentTrainingSet():
    electricty_training_csv = open('proj/electricity_sentiment_training_set.csv')
    reader = csv.reader(electricty_training_csv)
    training_set = []
    for row in reader:
        cleaned_tweet_text = cleanTweet(tweet_text=row[0])
        feature_vector = getFeaturevector(tweet_text=cleaned_tweet_text)
        training_set.append((electricityExtractFeatures(feature_vector=feature_vector),row[1]))
    return training_set

def getWaterSentimentTrainingSet():
    water_training_csv = open('proj/water_sentiment_training_set.csv')
    reader = csv.reader(water_training_csv)
    training_set = []
    for row in reader:
        cleaned_tweet_text = cleanTweet(tweet_text=row[0])
        feature_vector = getFeaturevector(tweet_text=cleaned_tweet_text)
        training_set.append((waterExtractFeatures(feature_vector=feature_vector),row[1]))
    return training_set

#initialize lists and classifiers in memory
domain_feature_list = getDomainRecognitionList()
domain_recongition_classifier = nltk.NaiveBayesClassifier.train(getDommainRecognitionTrainingSet())
electricity_feature_list = getElectricityRecognitionList()
electricity_sentiment_classifier = nltk.NaiveBayesClassifier.train(getElectricitySentimentTrainingSet())
water_feature_list = getWaterRecognitionList()
water_sentiment_classifier = nltk.NaiveBayesClassifier.train(getWaterSentimentTrainingSet())

def getIssueRecognitionList():
    pass

def getIssueRecognitionTrainingSet():
    pass

@app.task
def analyzeTweet(tweet):
    print 'about to analyze tweet'
    cleaned_tweet_text = cleanTweet(tweet_text=tweet['text'])
    feature_vector = getFeaturevector(tweet_text=cleaned_tweet_text)
    print 'Showing domain features:'
    print domainExtractFeatures(feature_vector=feature_vector)
    print 'Showing classifier output:'
    classify_result = domain_recongition_classifier.classify(domainExtractFeatures(feature_vector=feature_vector))
    print classify_result
    if classify_result == "toanalyze":
        cf_analyzedtweets_toanalyze = pycassa.ColumnFamily(pool, 'analyzedtweets_toanalyze')
        cf_analyzedtweets_toanalyze.insert(tweet['id_str'], {'tweet_text': tweet['text'],'tweet_timestamp': int(tweet['timestamp_ms'][:-3]), 'user_screen_name': tweet['user']['screen_name'], 'tweet_category': classify_result})
        print "We didn't understand your tweet, your next visit will be better"
        # t.statuses.update(status="@nigelnindo we didn't understand your tweet, your next visit will be better.")
        api.update_status("@{0} we didn't understand your tweet, your next visit will be better. {1}".format(tweet['user']['screen_name'], time.time()))
    else:
        cf_analyzedtweets_tweetcategory = pycassa.ColumnFamily(pool, 'analyzedtweets_tweetcategory')
        cf_analyzedtweets_tweetcategory.insert(tweet['id_str'], {'tweet_text': tweet['text'],'tweet_timestamp': int(tweet['timestamp_ms'][:-3]), 'user_screen_name': tweet['user']['screen_name'], 'tweet_category': classify_result})
        sentimentAnalysis(tweet=tweet,tweet_class=classify_result,feature_vector=feature_vector)

def sentimentAnalysis(tweet,tweet_class,feature_vector):
    print 'starting sentiment analysis'
    if tweet_class == "electricity":
        electrictySentimentAnalysis(tweet=tweet,tweet_class=tweet_class,feature_vector=feature_vector)
    elif tweet_class == "water":
        waterSentimentAnalysis(tweet=tweet,tweet_class=tweet_class,feature_vector=feature_vector)
    else:
        print "This shouldn't happen"


def getWaterRecognitionList():
    pass

def saveSentimentToCassandra(tweet,tweet_sentiment):
    print 'saving sentiment to Cassandra'
    cf_sentimenttweets_tweetcategory = pycassa.ColumnFamily(pool, 'sentimenttweets_tweetcategory')
    cf_sentimenttweets_tweetcategory.insert(tweet['id_str'], {'tweet_text': tweet['text'], 'tweet_timestamp': int(tweet['timestamp_ms'][:-3]), 'user_screen_name': tweet['user']['screen_name'], 'tweet_sentiment': tweet_sentiment})

def saveSentimentToAnalyzeCassandra(tweet,tweet_sentiment):
    print 'saving sentiment to Cassandra'
    cf_sentimenttweets_toanalyze = pycassa.ColumnFamily(pool, 'sentimenttweets_toanalyze')
    cf_sentimenttweets_toanalyze.insert(tweet['id_str'], {'tweet_text': tweet['text'], 'tweet_timestamp': int(tweet['timestamp_ms'][:-3]), 'user_screen_name': tweet['user']['screen_name'], 'tweet_sentiment': tweet_sentiment})

def electrictySentimentAnalysis(tweet,tweet_class,feature_vector):
    classify_result = electricity_sentiment_classifier.classify(electricityExtractFeatures(feature_vector=feature_vector))
    print 'classification of electricity tweet:'
    print classify_result
    if classify_result == "toanalyze":
        saveSentimentToAnalyzeCassandra(tweet=tweet, tweet_sentiment=classify_result)
        print "We think you had an electricty issue, but we are not sure yet."
        # t.statuses.update(status="@nigelnindo we think you had an electricty issue, but we are not sure yet.")
        api.update_status("@{0} we think you had an electricty issue, but we are not sure yet. {1}".format(tweet['user']['screen_name'], time.time()))
    else:
        saveSentimentToCassandra(tweet=tweet, tweet_sentiment=classify_result)
        print "Your issue has been forwarded to Kenya Power."
        # t.statuses.update(status="@nigelnindo your issue has been forwarded to Kenya Power.")
        api.update_status("@{0} your issue has been forwarded to Kenya Power. {1}".format(tweet['user']['screen_name'], time.time()))

def waterSentimentAnalysis(tweet,tweet_class,feature_vector):
    classify_result = water_sentiment_classifier.classify(waterExtractFeatures(feature_vector=feature_vector))
    print 'classification of water tweet'
    print classify_result
    if classify_result == "toanalyze":
        saveSentimentToAnalyzeCassandra(tweet=tweet, tweet_sentiment=classify_result)
        print "We think you had a water issue, but we're not sure yet."
        # t.statuses.update(status="@nigelnindo we think you had a water issue, but we're not sure yet.")
        api.update_status("@{0} we think you had a water issue, but we're not sure yet. {1}".format(tweet['user']['screen_name'], time.time()))
    else:
        saveSentimentToCassandra(tweet=tweet, tweet_sentiment=classify_result)
        print "Your issue has been forwarded to Nairobi Water & Sewerage."
        # t.statuses.update(status="@nigelnindo your issue has been forwarded to Nairobi Water & Sewerage.")
        api.update_status("@{0} your issue has been forwarded to Nairobi Water & Sewerage. {1}".format(tweet['user']['screen_name'], time.time()))

# finds out whether this is a water or electricty issue
def issueCategorization():
    pass

# finds out what time the issue occured
def issueTimeCategorization():
    pass

    # finds out where this issue occured
def issuePlaceRecognition():
    pass

    # finds out where/who to direct the issue to
def organizationMatcher():
    pass
