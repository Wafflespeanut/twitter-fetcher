import os
import json

from TwitterAPI import TwitterAPI, TwitterRestPager
from datetime import datetime
from time import sleep

# Number of tweets to be cached in the local DB
NUM_CACHE_TWEETS = 1000
# Endpoint for all search queries
SEARCH_ENDPOINT = 'search/tweets'
# Twitter's maximum allowed pagination is 100 tweets per page
# https://dev.twitter.com/rest/reference/get/search/tweets
TWEETS_PER_BATCH = 100
# Twitter allows up to 450 requests per (15 min) window for apps
# (which corresponds to a request every 2 seconds)
WORKER_SLEEP_SECS = 2.1


class TweetFetcher(object):
    '''
    An object to fetch and maintain a cache of tweets in a local DB.

    Usage:
    >>> from fetch import TweetFetcher
    >>> f = TweetFetcher()      # defaults
    >>> f.run_worker()          # to start the infinite loop

    (or)
    >>> f.get_last(10)          # get the latest 10 tweets from cache
    '''
    cache = NUM_CACHE_TWEETS

    def __init__(self, config_file='config.json', db='tweets_db'):
        self.config = config_file
        self.db = db
        self.tmp_db = 'tmp_' + db

    def load_config(self):
        '''JSON load the config file'''
        with open(self.config, 'r') as fd:
            return json.load(fd)

    def log(self, msg):
        '''Log a message with timestamp'''
        print '\033[91m%s\033[0m: \033[93m%s\033[0m' % (datetime.now(), msg)

    def get_last(self, count):
        ''' Get latest tweets from the local DB'''
        with open(self.db, 'r') as fd:
            lines = fd.readlines()      # FIXME: out of range error-prone
            assert len(lines) >= count, "cache has only %s tweets" % len(lines)
            return map(json.loads, lines[:count])

    def get_pager(self):
        '''Returns a paginating object over tweets'''
        config = self.load_config()

        api = TwitterAPI(config['consumer_key'],
                         config['consumer_secret'],
                         auth_type='oAuth2')

        self.cache = config.get('cache', NUM_CACHE_TWEETS)
        query = config.get('query')
        assert query, 'expected a search query in config'

        params = {'q': query, 'count': TWEETS_PER_BATCH}
        self.log('Query: %r' % params)
        return TwitterRestPager(api, SEARCH_ENDPOINT, params)

    def dump_to_db(self, batch):
        '''Dump a batch of tweets to DB'''
        with open(self.tmp_db, 'a') as fd:
            fd.writelines(batch)

    def run_worker(self):
        '''
        Infinitely keep the local DB updated with the latest N tweets
        matching the given query (both cache size and query are specified
        in the config)
        '''
        if os.path.exists(self.tmp_db):     # clear any unfinished runs
            os.remove(self.tmp_db)

        while True:
            request = self.get_pager()
            # Make batch requests over specified intervals (so that we get
            # as many tweets we want without crossing our API request limits)
            paginating_iter = request.get_iterator(wait=WORKER_SLEEP_SECS)

            try:
                curr_batch = []
                for i, tweet_obj in enumerate(paginating_iter):
                    if i == self.cache:
                        self.dump_to_db(curr_batch)     # final dump
                        break

                    if (i + 1) % TWEETS_PER_BATCH == 0:
                        self.dump_to_db(curr_batch)     # dump once full
                        curr_batch = []

                    curr_batch.append(json.dumps(tweet_obj) + '\n')

                os.rename(self.tmp_db, self.db)     # atomic rename
                self.log('Fetched %d tweets' % self.cache)
                sleep(WORKER_SLEEP_SECS)    # final sleep to maintain interval
            except KeyboardInterrupt:
                break
