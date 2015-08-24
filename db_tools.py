"""Useful & neccessary utility functions for doing stuff with our database."""
import tweepy
import time
import mongoengine as mge
import pygraphviz as pgv
from math import log10
from datetime import datetime

mge.connect('twitter-poetry')

API_CUTOFF = 10

class User(mge.Document):
    """User doctype. Holds all the info we need for a user."""
    username = mge.StringField(unique=True)
    idnumber = mge.IntField()
    friends = mge.ListField()
    tweets = mge.ListField()
    num_tweets = mge.IntField()
    corpus = mge.DictField()
    join_date = mge.DateTimeField()
    last_twitter_id = mge.IntField()

class Poem(mge.Document):
    poem_id = mge.IntField(unique=True)
    lines = mge.ListField()
    seed_user = mge.ReferenceField(User)
    friends = mge.BooleanField()
    
def init_api():
    """Initializes the twitter api."""
    #REMEMBER TO REMOVE THESE BEFORE PUBLISHING!
    consumer_key = '9837qrKedgU22V9Xz9mHgw'
    consumer_secret = 'vsGk8T1J9UZwPsBkfgcMRWXSmw44a4mW9MmCPWXVzyc'
    access_token_key = '16007524-OyqJQMw2RHi8y1L8URIErrCKHfSYFZGdc5vImrZpf'
    access_token_secret = 'Y2iUhIeI6N194qe1y6r7lLGiJaPHLXwLqZS3OXU2yc'
    
    auth = tweepy.OAuthHandler(consumer_key, consumer_secret)
    auth.set_access_token(access_token_key, access_token_secret)
    return tweepy.API(auth)

API = init_api()

def check_rate():
    """Checks usage, and sleeps until we get a reset if we drop below a cutoff
    value of remaining api hits...just in case there's some kind of bug that
    sucks up hits."""
    stat = API.rate_limit_status()
    if stat["remaining_hits"] < API_CUTOFF:
        resettime = datetime.strptime(stat["reset_time"], 
                "%a %b %d %H:%M:%S +0000 %Y")
        remaining_time = (resettime - datetime.utcnow()).total_seconds() + 10
        if remaining_time > 0:
            print "API hits exhausted. Waking up in {0} \
            seconds".format(remaining_time)
            time.sleep(remaining_time)
            print "Waking up."
            #Just to be sure.
            check_rate()

def user_add_info(screenname):
    """Adds info to the database for a user. 'screenname' should be a
    string."""
    try:
        user_t = API.get_user(screenname)
    except tweepy.error.TweepError:
        print("Twitter error! Either there's no user by that name \
            or they're private.")
        return None
    user = User(username=screenname, 
                idnumber=user_t.id,
                num_tweets=user_t.statuses_count,
                join_date = user_t.created_at
                )
    return user.save()

def split_words(text, markov):
    """Breaks words into pairs and adds them to a database. "text" can be any
    unicode string. Markov should be either an empty dict, or a prepopulated
    markov dict."""
    wordslist = text.split()
    #Words are all unicode strings, so we have to give translate a dict.
    words = map(lambda t: t.translate({ord("$"): None, ord("."): None}), 
            wordslist)
    index = 0
    while index < (len(words) - 1):
        key = words[index]
        if key in markov:
            markov[key].append(words[index + 1])
        else:
            markov[key] = [words[index + 1]]
        index += 1
    return markov

def make_markov(user):
    """Makes a markov dict for a user with tweets."""
    mkv = {}
    for t in user.tweets:
        split_words(t, mkv)
    return mkv

def all_tweets(username):
    """Gets tweets for a given username. Goes until we get an empty response"""
    check_rate()
    print "Getting timeline for {0}".format(username)
    t = API.user_timeline(username, count=100)
    print "Page 1: got {0} tweets".format(len(t))
    n = 2
    while True:
        check_rate()
        results = API.user_timeline(username, count=100, page=n)
        print "Page {0}: got {1} tweets".format(n, len(results))
        if results:
            t.extend(results)
        else:
            print "Got no results; bailing."
            break
        n += 1
        time.sleep(0.5)
    return t
    
def add_tweets(user):
    """Adds tweets to a user document."""
    if user.tweets:
        print "User already has tweets, skipping"
        return user
    print "Adding tweets for {0}".format(user.username)
    try:
        timeline = all_tweets(user.username)
        if timeline:
            user.last_twitter_id = timeline[0].id
    except tweepy.error.TweepError:
        print "Twitter error!"
        return user
    
    for tweet in timeline:
        text = tweet.text
        user.tweets.append(text)

    __ = user.save()

def add_corpus(user):
    """Adds a markov dict to a user document."""
    if user.tweets and not user.corpus:
        for k, v in make_markov(user).iteritems():
            if u"\x00" not in k:
                user.corpus[k] = v
        print "Corpus length for {0}: {1}".format(user.username,
                len(user.corpus))
        __ = user.save()
    elif not user.tweets:
        print "No tweets for user {0}".format(user.username)

def generate_graph(filename="usergraph.png"):
    """Generates a graph of our social network."""
    graph = pgv.AGraph(strict = False)
    for user in User.objects:
        for friend in user.friends:
            graph.add_edge(user.username, friend)
        n = graph.get_node(user.username)
        n.attr['label'] = ""
        n.attr['shape'] = 'point'
        if user.username == u'juliemastrine':
            n.attr['color'] = 'red'
    graph.layout()
    graph.draw(filename)
