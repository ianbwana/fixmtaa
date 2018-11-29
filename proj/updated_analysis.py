from __future__ import absolute_import

import csv
import time

import pycassa
import tweepy

import os

# get auth credentials from environment variables
CONSUMER_KEY = os.environ.get('TWITTER_API_KEY')
CONSUMER_SECRET = os.environ.get('TWITTER_API_SECRET')
ACCESS_TOKEN = os.environ.get('TWITTER_ACCESS_TOKEN')
ACCESS_SECRET = os.environ.get('TWITTER_ACCESS_SECRET')

# tweepy library credentials
tweepy_auth = tweepy.OAuthHandler(CONSUMER_KEY, CONSUMER_SECRET)
tweepy_auth.set_access_token(ACCESS_TOKEN, ACCESS_SECRET)

api = tweepy.API(tweepy_auth)

from proj.celery import app

pool = pycassa.ConnectionPool('tweets')

cf_domainless_tweets_by_timestamp = pycassa.ColumnFamily(pool, 'domainless_tweets_by_timestamp')
cf_domainless_tweets_by_tweet_id = pycassa.ColumnFamily(pool, 'domainless_tweets_by_tweet_id')

cf_negative_tweets_by_timestamp = pycassa.ColumnFamily(pool, 'negative_tweets_by_timestamp')
cf_negative_tweets_by_domain = pycassa.ColumnFamily(pool, 'negative_tweets_by_domain')
cf_negative_tweets_by_tweet_id = pycassa.ColumnFamily(pool, 'negative_tweets_by_tweet_id')

cf_positive_tweets_by_timestamp = pycassa.ColumnFamily(pool, 'positive_tweets_by_timestamp')
cf_positive_tweets_by_domain = pycassa.ColumnFamily(pool, 'positive_tweets_by_domain')
cf_positive_tweets_by_tweet_id = pycassa.ColumnFamily(pool, 'positive_tweets_by_tweet_id')

cf_unverified_tweets_by_timestamp = pycassa.ColumnFamily(pool, 'unverified_tweets_by_timestamp')
cf_unverified_tweets_by_domain = pycassa.ColumnFamily(pool, 'unverified_tweets_by_domain')
cf_unverified_tweets_by_tweet_id = pycassa.ColumnFamily(pool, 'unverified_tweets_by_tweet_id')

# from cassandra.cluster import Cluster
# cluster = Cluster()  # use default args for now
# session = cluster.connect('tweets')

domain_keywords_list = []
domain_indicator_keywords_list = []
negation_keywords_list = []
domain_negation_keywords_list = []


def generateDomainKeywords():
    """
    ->  Domain keywords are those words that strongly point to a certain
        domain.
    ->  These keywords, when followed by a domain negation keyword, leads to
        to a negative sentiment about the domain.
    """
    domain_keywords = open('proj/domain_keywords_updated.csv', "rb")
    reader = csv.reader(domain_keywords)
    for row in reader:
        domain_keywords_list.append((row[0], row[1]))


def generateDomainIndicatorKeywords():
    """
    ->  Domain indicator keywords are words that point to a certain domain.
    ->  When a domain indicator is followed by a domain negation keyword, there's
        a strong chance that it isn't a negative sentiment.
    """
    domain_indicators = open('proj/indicator_keywords.csv', "rb")
    reader = csv.reader(domain_indicators)
    for row in reader:
        domain_indicator_keywords_list.append((row[0], row[1]))


def generateNegationKeywords():
    """
    ->  These are general English words that lead to negation.
    ->  If the come immediately after a domain keyword, we can strongly believe
        that a negative sentiment is insinuated, even without there being a negative
        domain keyword.
    ->  These keywords can however also negate a domain negation keyword, where
        the double negation causes a positive sentiment.
    """
    negation_keywords = open('proj/general_negation_keywords.csv', "rb")
    reader = csv.reader(negation_keywords)
    for row in reader:
        negation_keywords_list.append(row[0])


def generateDomainNegationKeywords():
    """
    -> Has been explained if you read the above comments
    """
    domain_negation_keywords = open('proj/domain_negation_keywords.csv', "rb")
    reader = csv.reader(domain_negation_keywords)
    for row in reader:
        # word | domain | can_prefix | can_suffix | is_independent
        print row[0]
        domain_negation_keywords_list.append((row[0], row[1], row[2], row[3], row[4]))


generateDomainKeywords()
generateDomainIndicatorKeywords()
generateNegationKeywords()
generateDomainNegationKeywords()


def findDomainNegationKeywords(tweet_tokens, identified_domain):
    # create a new list containing only keywords from that domain
    specified_domain_negation_keywords = [text for text, domain, can_prefix, can_suffix, is_independent in domain_negation_keywords_list if domain == identified_domain]
    if not specified_domain_negation_keywords:
        # this means that this is an empty list
        # print "The domain doesn't have any negation keywords"
        return (tweet_tokens, False)
    token_index = 0
    for text, classifier, domain in tweet_tokens:
        # 'DI' may also be 'DNK'
        # since we have determined the domain, 'DI' keywords are not useful anymore
        if classifier == 'u' or classifier == 'DI':
            if text in specified_domain_negation_keywords:
                tweet_tokens[token_index] = (text, 'DNK', identified_domain)
        token_index = token_index + 1
    """
    -> From the list of all domain keywords, filter them and remain with the
        one that point with the selected domain.
    """
    # print tweet_tokens
    return (tweet_tokens, True)  # True: The identified_domain passed as input is valid


def findNegationKeywords(tweet_tokens):
    # TODO: Figure out if general negation should also be suited for each domain
    # token_texts = [text for text, classifier, domain in tweet_tokens]
    # negation_data = [value for value, domain, is_prefixed in negation_keywords_list]
    token_index = 0
    for text, classifier, domain in tweet_tokens:
        if classifier == 'u':
            if text in negation_keywords_list:
                # update tweet_tokens
                # negation_index = negation_data.index(text)
                tweet_tokens[token_index] = (text, 'NK', 'u')
        token_index = token_index + 1
    # print tweet_tokens
    return tweet_tokens


def findDomainIndicatorKeywords(tweet_tokens):
    # all_token_texts used to maintain original token index
    # no need to re-classify domain keywords
    domain_indicator_data = [value for value, domain in domain_indicator_keywords_list]
    token_index = 0
    # for simplicity's sake, we can't enumerate here
    for text, classifier, domain in tweet_tokens:
        if classifier == 'u':
            if text in domain_indicator_data:
                domain_indicator_index = domain_indicator_data.index(text)
                tweet_tokens[token_index] = (text, 'DI', domain_indicator_keywords_list[domain_indicator_index][1])
        token_index = token_index + 1
    # token_texts = [text for text, classifier, domain in tweet_tokens if classifier == 'u']
    # for index, token in enumerate(token_texts):
    # print tweet_tokens
    return tweet_tokens


def findDomainKeywords(tweet_tokens):
    # get lists without meta-data
    token_texts = [text for text, classifier, domain in tweet_tokens]
    domain_data = [value for value, domain in domain_keywords_list]
    for index, token in enumerate(token_texts):
        # print index
        if token in domain_data:
            # update tweet_tokens if domain keyword is present in tweet
            domain_index = domain_data.index(token)
            tweet_tokens[index] = (token, 'DK', domain_keywords_list[domain_index][1])
    # print tweet_tokens
    # findDomainIndicatorKeywords(tweet_tokens=tweet_tokens)
    return tweet_tokens

"""
print domain_keywords_list
print domain_indicator_keywords_list
print negation_keywords_list
print domain_negation_keywords_list
"""

# tweet domain retriever functions below


def getDomainByDomainKeywords(tweet_tokens):
    for text, classifier, domain in tweet_tokens:
        if classifier == 'DK':
            return domain
    return None


def getDomainByDomainIdentifiers(tweet_tokens):
    domain_counter = {}
    for text, classifier, domain in tweet_tokens:
        if classifier == 'DI':
            if domain not in domain_counter:
                domain_counter[domain] = 1
            else:
                domain_counter[domain] = domain_counter[domain] + 1
    # print domain_counter
    if not domain_counter:
        # empty dictionary means that no domains matched
        return None
    else:
        # TODO: Deal with max having two or more domains i.e {'electricity': 2, 'water': 2} !!!IMPORTANT!!!
        int_values = []
        for key, val in domain_counter.items():
            int_values.append(val)
        max_int_value = max(int_values)
        for key, val in domain_counter.items():
            if val == max_int_value:
                # print 'returning max DI'
                # print key
                return key
    return None  # don't see this happening



def getTweetDomain(tweet_tokens):
    """
    -> At this point, we expect the tweet to have 'DK' and/or 'DI' tokens present
    -> If the tweet does not have both ('DK' or 'DI'), then we cannot determine the domain
       of the tweet. We need to mark it as 'domainless' and store it somewhere for
       futher analysis. There could be something we missed out on.
    -> If we encounter a 'DK', we stop getting the tweet domain and use the domain
       keyword provided as our identified_domain.
    -> If there are no "DK's", we rely on the "DI's" available in the tweet.
    -> For a first implementation, we will use the domain where it's "DI's" show
       up the most as the identified_domain. This only works if there are no ties
       btwn different domains.
    -> In the future, this a great place to add a regression model that can give
       us the most probable (yes, probability) domain the tweet belongs to given
       its 'DI' tokens.
    -> All domain getter functions are defined outside this function so that we
       create a pluggable system, on that we can remove any of those functions without
       affecting the other functions. this means that they mutate state, they take in
       input and give out an output.
    -> This pluggability also allows us to add more domian getter function in the future
    """
    identified_domain = None
    identified_domain = getDomainByDomainKeywords(tweet_tokens=tweet_tokens)
    # if we find the domain by domain keywords, our search ends
    if identified_domain is not None:
        return identified_domain
    identified_domain = getDomainByDomainIdentifiers(tweet_tokens=tweet_tokens)
    return identified_domain  # will be None if the second domain getting step failed


def isValidIndex(list_to_check, index_to_check):
    if 0 <= index_to_check < len(list_to_check):
        return True
    else:
        return False


# TODO: If a domain identifier isn't changed to a 'DNK', it may be used as 'DK' when extracting the tweet sentiment

def getKeywordsAfterNK(tweet_tokens, domain_negators):
    token_index = 0
    # print tweet_tokens
    for text, classifier, domain in tweet_tokens:
        if classifier == 'NK':
            print 'found a negative keyword'
            # check if next token classifier is a keyword
            if isValidIndex(tweet_tokens, token_index + 1):
                if tweet_tokens[token_index + 1][1] == 'DK':
                    print 'next token classifier is a domain keyword'
                    # check if token classifier after keywords is a domain negator
                    if isValidIndex(tweet_tokens, token_index + 2):
                        if tweet_tokens[token_index + 2][1] == 'DNK':
                            print 'next token after domain keyword is a domain negation keyword'
                            # if it is a domain negator, check whether it can be suffixed after a keyword
                            dnk_index = [index for index, domain_list in enumerate(domain_negators) if domain_list[0] == tweet_tokens[token_index + 2][0]]
                            if domain_negators[dnk_index[0]][3] == 'yes':
                                print 'domain negation keyword can be suffixed after a domain keyword'
                                # means we have a NK-DK-DNK combination which is false
                                return (False, 'verified')
                            else:
                                print "domain negation keyword can't be suffixed after a domain keyword"
                                # although we have a NK-DK-DNK combination, the DNK can't be used as a suffix for DK's
                                return (True, 'verified')
                        else:
                            print 'print there was no domain negation keyword found, tweet is negative'
                            # next token found was not a domain negator, we have a negative tweet
                            return (True, 'verified')
                    else:
                        print 'There was no next token, tweet is negative'
                        # the was no token found after confirming an NK-DK combination
                        return (True, 'verified')
                else:
                    print "Next token is not a domain keyword, can't verify sentiment"
                    # next token classifier was not a keyword, can't very negative sentiment
                    pass
            else:
                print "No next token available, can't verify sentiment"
                # there is no next token, can't verify negative sentiment insinuated by NK
                pass
        token_index = token_index + 1
    # return False & unverified if we were not able to determine sentiment after this step
    print "negative keywords filtering didn't failed to find tweet sentiment"
    return (False, 'unverified')


def getDomainNegativeDescriptors(tweet_tokens, domain_negators):
    token_index = 0
    for text, classifier, domain in tweet_tokens:
        if classifier == 'DNK':
            print 'Found a domain negative keyword'
            dnk_index = [index for index, domain_list in enumerate(domain_negators) if domain_list[0] == text]
            # check if if the DNK cannot be prefixed or suffixed
            if domain_negators[dnk_index[0]][2] == 'no' and domain_negators[dnk_index[0]][3] == 'no':
                print 'DNK cannot be prefixed or suffixed, inherently independent'
                # check if a negative keyword comes before it
                if isValidIndex(tweet_tokens, token_index - 1):
                    if tweet_tokens[token_index - 1][1] == 'NK':
                        print "negator keyword found before independent DNK, tweet is positive"
                        # token found before DNK that was a negator
                        return (False, 'verified')
                    else:
                        print "negator keyword not found before independent DNK, tweet is negative"
                        # token found before DNK, but it wasn't a negator
                        return (True, 'verified')
                else:
                    # no tokens found before DNK, shows negative tweet
                    return (True, 'verified')
            # check if DNK is independent
            if domain_negators[dnk_index[0]][4] == 'yes':
                print 'DNK is independent'
                # check if a negative keyword comes before it
                if isValidIndex(tweet_tokens, token_index - 1):
                    if tweet_tokens[token_index - 1][1] == 'NK':
                        # token found before independent DNK was a negator
                        print "negator keyword found before independent DNK, tweet is positive"
                        return (False, 'verified')
                    else:
                        # token found before independent DNK was not a negator
                        print "negator keyword not found before independent DNK, tweet is negative"
                        return (True, 'verified')
                else:
                    # no tokens before DNK, negative tweet
                        return (True, 'verified')
            # check if the DNK can be prefixed before a keyword [we get here only if it can be prefixed or suffixed]
            if domain_negators[dnk_index[0]][2] == 'yes':
                print 'DNK can be prefixed by a keyword'
                # check if a keyword comes after it
                if isValidIndex(tweet_tokens, token_index + 1):
                    if tweet_tokens[token_index + 1][1] == 'DK':
                        # check if negation keyword comes before it
                        if isValidIndex(tweet_tokens, token_index - 1):
                            if tweet_tokens[token_index - 1][1] == 'NK':
                                # NK-DNK-DK combination, tweet is positive
                                return (False, 'verified')
                            else:
                                # no negation keyword before DNK-DK combination
                                return (True, 'verified')
                        else:
                            # no negation keyword comes before DNK-DK combination, tweet is negative
                            return (True, 'verified')
                else:
                    # no other token comes after this DNK, can't verify negativity of tweet
                    pass
            # check if DNK can be suffixed after a keyword
            if domain_negators[dnk_index[0]][3] == 'yes':
                print 'DNK can be suffixed by a keyword'
                # check if a keyword comes before it
                if isValidIndex(tweet_tokens, token_index -1):
                    if tweet_tokens[token_index - 1][1] == 'DK':
                        print 'a domain keyword comes before this DNK'
                        # check if a negation keyword comes before the domain keyword
                        if isValidIndex(tweet_tokens, token_index - 2):
                            if tweet_tokens[token_index - 2][1] == 'NK':
                                print 'a negator keyword comes before the domain keyword, tweet is positive'
                                # NK-DK-DNK combination found, tweet is positive
                                return (False, 'verified')
                            else:
                                print 'a negator keyword does not come before the domain keyword, tweet is negative'
                                # no NK before DK-DNK combination, tweet is negative
                                return (True, 'verified')
                        else:
                            print 'no word/token found before domain keyword, tweet is negative'
                            return (True, 'verified')
                else:
                    print "Can't verify negativity of DNK if no word comes before a suffixed DNK"
                    # no other token comes before DNK, unable to verify negativity of tweet
                    pass
        token_index = token_index + 1
    return (False, 'unverified')


def getTweetProblem(tweet_tokens, identified_domain):
    """
    -> The model is simple enough to use if else's for now. But if we determined
       that we have undeffited, we may have to switch to decision trees if using
       if-else statements becomes cumbersome and difficult to follow.
    """
    # TODO: Auto-correcting function for negative domain keywords list
    # print 'getting tweet problem'
    # print identified_domain
    # ->True [Negative sentiment found] ->False[Positive sentiment found/sentiment unconfirmed]
    negative_sentiment = (False, 'unverified')
    # get domain_negators for identified_domain
    # print domain_negation_keywords_list
    domain_negators = [domain_list for index, domain_list in enumerate(domain_negation_keywords_list) if domain_list[1] == identified_domain]
    # print 'filtered domain negators'
    # print domain_negators
    # print tweet_tokens
    negative_sentiment = getKeywordsAfterNK(tweet_tokens=tweet_tokens, domain_negators=domain_negators)
    if negative_sentiment[0] == False and negative_sentiment[1] == 'unverified':
        negative_sentiment = getDomainNegativeDescriptors(tweet_tokens=tweet_tokens, domain_negators=domain_negators)
    return negative_sentiment

def getTweetTokensAsString(tweet_tokens):
    token_string = ""
    for token in tweet_tokens:
        token_text = token[0]
        token_classifier = token[1]
        token_string = token_string +  token_text + " : " + token_classifier + ", "  # TODO: store both token text & classifier
    return token_string

def domainlessHandler(tweet, tweet_tokens):
    # TODO: save to cassandra & return appropriate error message to the user
    # store tweets by current timestamp & tweet_id
    # timestamp # || current_timestamp || tweet_id | tweet_text | tweet_tokens |
    # tweet_id # || tweet_id || current_timestamp | tweet_text | tweet_tokens |
    # print 'RESULT: domainless : {0}'.format(tweet['text']).encode('utf-8').strip()  # TODO: Fix non-unicode character display in terminal
    cf_domainless_tweets_by_timestamp.insert(time.time(), {'tweet_id': tweet['id_str'], 'tweet_text': tweet['text'].encode("utf-8"), 'tweet_tokens': getTweetTokensAsString(tweet_tokens).encode("utf-8")})
    cf_domainless_tweets_by_tweet_id.insert(tweet['id_str'], {'current_timestamp': time.time(), 'tweet_text': tweet['text'].encode("utf-8"), 'tweet_tokens': getTweetTokensAsString(tweet_tokens).encode("utf-8")})
    # TODO: send feedback to user using tweepy
    api.update_status("@{0} FixMtaa didn't understand your tweet, information you provided will help make it better.".format(tweet['user']['screen_name']), tweet['id_str'])

def negativeSentimentHandler(tweet, tweet_tokens, identified_domain):
    # store tweets by current timestamp, domain & tweet_id
    # timestamp # || current_timestamp | tweet_id | tweet_text | tweet_tokens | domain_text |
    # domain # || domain_text || current_timestamp | tweet_id | tweet_text | tweet_tokens |
    # tweet_id # || tweet_id || current_timestamp | tweet_id | tweet_text | tweet_tokens |
    cf_negative_tweets_by_timestamp.insert(time.time(), {'tweet_id': tweet['id_str'], 'tweet_text': tweet['text'].encode("utf-8"), 'tweet_tokens': getTweetTokensAsString(tweet_tokens).encode("utf-8"), 'domain_text': identified_domain})
    cf_negative_tweets_by_domain.insert(identified_domain, {'current_timestamp': time.time(), 'tweet_id': tweet['id_str'], 'tweet_text': tweet['text'].encode("utf-8"), 'tweet_tokens': getTweetTokensAsString(tweet_tokens).encode("utf-8")})
    cf_negative_tweets_by_tweet_id.insert(tweet['id_str'], {'current_timestamp': time.time(), 'tweet_id': tweet['id_str'], 'tweet_text': tweet['text'].encode("utf-8"), 'tweet_tokens': getTweetTokensAsString(tweet_tokens).encode("utf-8")})
    # TODO: send feedback to user using tweepy
    api.update_status("@{0} FixMtaa has forwarded your issue to the relevant authorities.".format(tweet['user']['screen_name']), tweet['id_str'])

def positiveSentimentHandler(tweet, tweet_tokens, identified_domain):
    # store tweets by current timestamp, domain & tweet_id
    # timestamp # || current_timestamp | tweet_id | tweet_text | tweet_tokens | domain_text |
    # domain # || domain_text || current_timestamp | tweet_id | tweet_text | tweet_tokens |
    # tweet_id # || tweet_id || current_timestamp | tweet_id | tweet_text | tweet_tokens |
    cf_positive_tweets_by_timestamp.insert(time.time(), {'tweet_id': tweet['id_str'], 'tweet_text': tweet['text'].encode("utf-8"), 'tweet_tokens': getTweetTokensAsString(tweet_tokens).encode("utf-8"), 'domain_text': identified_domain})
    cf_positive_tweets_by_domain.insert(identified_domain, {'current_timestamp': time.time(), 'tweet_id': tweet['id_str'], 'tweet_text': tweet['text'].encode("utf-8"), 'tweet_tokens': getTweetTokensAsString(tweet_tokens).encode("utf-8")})
    cf_positive_tweets_by_tweet_id.insert(tweet['id_str'], {'current_timestamp': time.time(), 'tweet_id': tweet['id_str'], 'tweet_text': tweet['text'].encode("utf-8"), 'tweet_tokens': getTweetTokensAsString(tweet_tokens).encode("utf-8")})
    # TODO: send feedback to user using tweepy
    api.update_status("@{0} FixMtaa understood your tweet, but couldn't detect a community problem.".format(tweet['user']['screen_name']), tweet['id_str'])


def unverifiedSentimentHandler(tweet, tweet_tokens, identified_domain):
    # store tweets by current timestamp, domain & tweet_id
    # timestamp # || current_timestamp | tweet_id | tweet_text | tweet_tokens | domain_text |
    # domain # || domain_text || current_timestamp | tweet_id | tweet_text | tweet_tokens |
    # tweet_id # || tweet_id || current_timestamp | tweet_id | tweet_text | tweet_tokens |
    cf_unverified_tweets_by_timestamp.insert(time.time(), {'tweet_id': tweet['id_str'], 'tweet_text': tweet['text'].encode("utf-8"), 'tweet_tokens': getTweetTokensAsString(tweet_tokens).encode("utf-8"), 'domain_text': identified_domain})
    cf_unverified_tweets_by_domain.insert(identified_domain, {'current_timestamp': time.time(), 'tweet_id': tweet['id_str'], 'tweet_text': tweet['text'].encode("utf-8"), 'tweet_tokens': getTweetTokensAsString(tweet_tokens).encode("utf-8")})
    cf_unverified_tweets_by_tweet_id.insert(tweet['id_str'], {'current_timestamp': time.time(), 'tweet_id': tweet['id_str'], 'tweet_text': tweet['text'].encode("utf-8"), 'tweet_tokens': getTweetTokensAsString(tweet_tokens).encode("utf-8")})
    # TODO: send feedback to user using tweepy
    api.update_status("@{0} FixMtaa understood you were asking about {1}, but couldn't detect your problem.".format(tweet['user']['screen_name']), tweet['id_str'])


def extractTweetDomainInformation(tweet_tokens):
    return findDomainIndicatorKeywords(findDomainKeywords(tweet_tokens=tweet_tokens))


def extractTweetInfomationAfterDomainIdentification(tweet_tokens, identified_domain):
    return findDomainNegationKeywords(findNegationKeywords(tweet_tokens=tweet_tokens), identified_domain=identified_domain)

# TODO: Route internet service disruption to the service provider mentioned in the tweet

@app.task
def analysisTweetReceiver(tweet, tweet_text, tweet_tokens):
    """
    ->  This is the method that recieves the unmodifed tweets, together with
        the tweets cleaned tokens.
    """
    # find 'DK' and 'DI' tokens in tweet
    tweet_tokens = extractTweetDomainInformation(tweet_tokens=tweet_tokens)
    identified_domain = getTweetDomain(tweet_tokens=tweet_tokens)
    if identified_domain is None:
        domainlessHandler(tweet=tweet, tweet_tokens=tweet_tokens)
        return
    # update tweet tokens after domain identification
    tweet_tokens = extractTweetInfomationAfterDomainIdentification(tweet_tokens=tweet_tokens, identified_domain=identified_domain)
    # method above return a tuple (tweet_tokens, boolean). Boolean shows if there are any negation keywords for this domain.
    # we can now use the updated tweet_tokens to identify the problem in the tweet
    # negative_sentiment is a tuple with a boolean for sentiment state and whether the boolean value has been verified by the algorithm
    # this covers the case where we don't have a negative sentiment that has been determined by the algorithm
    negative_sentiment = getTweetProblem(tweet_tokens=tweet_tokens[0], identified_domain=identified_domain)
    formated_result = 'RESULT: {0} : {1}'.format(tweet_text.encode("utf-8"), str(negative_sentiment))
    # print 'tweet:'
    # print tweet
    # print 'sentiment:'
    # print negative_sentiment
    print formated_result
    if negative_sentiment[0] == True:
        # we have positively identified a negative sentiment in the tweet_text
        negativeSentimentHandler(tweet=tweet, tweet_tokens=tweet_tokens[0], identified_domain=identified_domain)
        return
    if negative_sentiment[0] == False and negative_sentiment[1] == 'verified':
        # we we're able to extract domain information, but identified there's no problem in your tweet
        positiveSentimentHandler(tweet=tweet, tweet_tokens=tweet_tokens[0], identified_domain=identified_domain)
        return
    if negative_sentiment[0] == False and negative_sentiment[1] == 'unverified':
        # we we're able to extract the domain information, but could not figure out positive or negative sentiment
        unverifiedSentimentHandler(tweet=tweet, tweet_tokens=tweet_tokens[0], identified_domain=identified_domain)
        return
    print 'We are never supposed to see this on the terminal screen'


# TODO: Switch to DataStax python driver for cassandra
