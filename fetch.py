import os
import json
import sys

from datetime import datetime
from TwitterAPI import TwitterAPI, TwitterRestPager

NUM_CACHE_TWEETS = 1000
SEARCH_ENDPOINT = 'search/tweets'
WORKER_SLEEP_SECS = 2.5


class TweetFetcher(object):
    cache = NUM_CACHE_TWEETS

    def __init__(self, config_file='config.json', db='tweets_db'):
        self.config = config_file
        self.db = db

    def log(self, msg):
        print '\033[91m%s\033[0m: \033[93m%s\033[0m' % (datetime.now(), msg)

    def get_pager(self):
        with open(self.config, 'r') as fd:
            config = json.load(fd)

        api = TwitterAPI(config['consumer_key'],
                         config['consumer_secret'],
                         auth_type='oAuth2')

        self.cache = config.get('cache', NUM_CACHE_TWEETS)
        params = config.get('search', {})
        assert params.get('q'), 'expected a search query in config'
        params['count'] = 100

        self.log('Query: %r' % params['q'])
        return TwitterRestPager(api, SEARCH_ENDPOINT, params)

    def run_worker(self):
        db = 'tmp_' + self.db
        if os.path.exists(db):
            os.remove(db)

        while True:
            request = self.get_pager()
            paginating_iter = request.get_iterator(wait=WORKER_SLEEP_SECS)

            try:
                for i, tweet_obj in enumerate(paginating_iter):
                    if i == self.cache:
                        break

                    with open(db, 'a') as fd:
                        fd.writelines([json.dumps(tweet_obj) + '\n'])

                os.rename(db, self.db)
                self.log('Fetched %d tweets' % self.cache)
            except KeyboardInterrupt:
                break
