import os
import json
import sys

from datetime import datetime
from TwitterAPI import TwitterAPI, TwitterRestPager

NUM_CACHE_TWEETS = 1000
SEARCH_ENDPOINT = 'search/tweets'
TWEETS_PER_BATCH = 100
WORKER_SLEEP_SECS = 2.5


class TweetFetcher(object):
    cache = NUM_CACHE_TWEETS

    def __init__(self, config_file='config.json', db='tweets_db'):
        self.config = config_file
        self.db = db
        self.tmp_db = 'tmp_' + db

    def log(self, msg):
        print '\033[91m%s\033[0m: \033[93m%s\033[0m' % (datetime.now(), msg)

    def get_pager(self):
        with open(self.config, 'r') as fd:
            config = json.load(fd)

        api = TwitterAPI(config['consumer_key'],
                         config['consumer_secret'],
                         auth_type='oAuth2')

        self.cache = config.get('cache', NUM_CACHE_TWEETS)
        query = config.get('query')
        assert query, 'expected a search query in config'

        params = {'q': query, 'count': TWEETS_PER_BATCH}
        self.log('Query: %r' % params)
        return TwitterRestPager(api, SEARCH_ENDPOINT, params)

    def dump_to_db(self, tweet_batch):
        with open(self.tmp_db, 'a') as fd:
            fd.writelines(tweet_batch)

    def run_worker(self):
        if os.path.exists(self.tmp_db):
            os.remove(self.tmp_db)

        while True:
            request = self.get_pager()
            paginating_iter = request.get_iterator(wait=WORKER_SLEEP_SECS)

            try:
                curr_batch = []
                for i, tweet_obj in enumerate(paginating_iter):
                    if i == self.cache:
                        self.dump_to_db(curr_batch)
                        break

                    if (i + 1) % TWEETS_PER_BATCH == 0:
                        self.dump_to_db(curr_batch)
                        curr_batch = []

                    curr_batch.append(json.dumps(tweet_obj) + '\n')

                os.rename(self.tmp_db, self.db)
                self.log('Fetched %d tweets' % self.cache)
            except KeyboardInterrupt:
                break
