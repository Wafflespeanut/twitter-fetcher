## twitter-fetcher

A simple wrapper over the [Twitter API](https://github.com/geduldig/TwitterAPI) to cache and serve tweets corresponding to a specified query.

### Setup:

 - [Create a new app](https://apps.twitter.com/app/new) in Twitter with read-only permission.
 - Create a new `config.json` file (matching the `config.json.sample` file).
 - Update the config with the search query along with the consumer key and consumer secret from your app.

### Usage:

``` python
from fetch import TweetFetcher

f = TweetFetcher()      # defaults
```

In order to keep the local database updated (with a background worker), run

``` python
f.run_worker()      # non-blocking
```

To stop the worker thread, run

``` python
f.kill_worker()
```

To get 10 latest tweets from the local DB, run

``` python
tweets = f.get_last(10)
print map(lambda tweet: tweet['text'], tweets)
```

### Design:

The goal of this wrapper is to serve the latest tweets (corresponding to the specified search query in the config) regardless of the API rate limitation imposed by Twitter. So, it makes use of a background worker which sends API requests every two seconds and keeps the local database in sync with the latest tweets matching that query. This allows us to independently fetch any number of latest tweets (limited by the cache size) any time.

The config is read only by the worker, and it reads it every time before populating the database. This means that whenever the config gets changed, it will be reflected in the database during the next iteration.
