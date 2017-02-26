import os
import json

from TwitterAPI import TwitterAPI, TwitterRestPager
from datetime import datetime
from threading import Thread
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
    '''An object to fetch and maintain a cache of tweets in a local DB.'''
    cache = NUM_CACHE_TWEETS
    kill_flag = False

    def __init__(self, config_file='config.json', db='tweets_db',
                 log_enabled=False):
        self._config = config_file
        self._db = db
        self._tmp_db = 'tmp_' + db
        self._log_enabled = log_enabled

    def _load_config(self):
        '''JSON load the config file'''
        with open(self._config, 'r') as fd:
            return json.load(fd)

    # FIXME: doesn't work well with threading (maybe log to file?)
    def _log(self, msg):
        '''Log a message with timestamp'''
        if self._log_enabled:
            print '\033[91m%s\033[0m: \033[93m%s\033[0m' % (datetime.now(), msg)

    def get_last(self, count):
        ''' Get latest tweets from the local DB'''
        assert os.path.exists(self._db), "cache is not populated"
        with open(self._db, 'r') as fd:
            lines = fd.readlines()      # FIXME: out of range error-prone
            assert len(lines) >= count, "cache has only %s tweets" % len(lines)
            return map(json.loads, lines[:count])

    def _get_pager(self):
        '''Returns a paginating object over tweets'''
        config = self._load_config()

        api = TwitterAPI(config['consumer_key'],        # app-only auth
                         config['consumer_secret'],
                         auth_type='oAuth2')

        self.cache = config.get('cache', NUM_CACHE_TWEETS)
        query = config.get('query')
        assert query, 'expected a search query in config'

        params = {'q': query, 'count': TWEETS_PER_BATCH}
        self._log('Query: %r' % params)
        return TwitterRestPager(api, SEARCH_ENDPOINT, params)

    def _dump_to_db(self, batch):
        '''Dump a batch of tweets to DB'''
        with open(self._tmp_db, 'a') as fd:
            fd.writelines(batch)

    def _remove_tmp_db(self):
        if os.path.exists(self._tmp_db):
            os.remove(self._tmp_db)

    def _worker(self):
        self._remove_tmp_db()        # clear any unfinished runs

        while True:
            request = self._get_pager()
            # Make batch requests over specified intervals (so that we get
            # as many tweets we want without crossing our API request limits)
            paginating_iter = request.get_iterator(wait=WORKER_SLEEP_SECS)

            try:
                curr_batch = []
                for i, tweet_obj in enumerate(paginating_iter):
                    if i == self.cache:
                        self._dump_to_db(curr_batch)     # final dump
                        break

                    if self.kill_flag:      # check for kill status
                        self._log('Quitting worker...')
                        self._remove_tmp_db()
                        return

                    if (i + 1) % TWEETS_PER_BATCH == 0:
                        self._dump_to_db(curr_batch)     # dump once full
                        curr_batch = []

                    curr_batch.append(json.dumps(tweet_obj) + '\n')

                os.rename(self._tmp_db, self._db)     # atomic rename
                self._log('Fetched %d tweets' % self.cache)

                sleep(WORKER_SLEEP_SECS)    # final sleep to maintain interval
            except KeyboardInterrupt:
                break

    def run_worker(self):
        '''
        Launch a thread to keep the local DB updated with the latest N tweets
        matching the given query (both cache size and query are specified
        in the config)
        '''
        thread = Thread(target=self._worker)
        thread.start()

    def kill_worker(self):
        '''Set the kill flag to quit the worker'''
        self.kill_flag = True
