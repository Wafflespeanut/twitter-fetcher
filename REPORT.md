## Twitter fetcher - Experience report

**Date:** Feb 26, 2017 (Sun)

### Goal

The idea is to create a Twitter API client which fetches tweets corresponding to a hashtag along with additional filters (in my case, it was the tag `#custserve` and the tweets should be retweeted at least once!). Moreover, the client should be simple in design, easy to use and written for future development.

### Implementation

My language of choice was Python (having spent 3 years with that). Writing an API client by ourselves from scratch may sound good, but it's probably a bad idea, because a numerous factors come into picture - like endpoints for REST requests, for example. Or, maybe even the needs could change in the future. Switching the dependencies on the other hand won't cost you that much. There are [tons of libraries](https://dev.twitter.com/resources/twitter-libraries) available for interacting with the API. [`TwitterAPI`](https://github.com/geduldig/TwitterAPI) library seemed simple enough.

Now, the obvious way would be to have a wrapper that uses this library to fetch the tweet info. Twitter API has two limitations though. Firstly, it doesn't allow us to make unauthenticated requests, and so we need to create an app, get its consumer key and secret, and make the requests. And second, it limits the rate of requests for search queries to 180 per (15 minutes) window for user-based requests and 450 for app-based. We only need the latter, since a search query most often doesn't need a user context.

This limits our app to raising a single request (atmost) over an interval of 2 seconds, which means we can't raise an API request whenever we need one. So, we need a cache store to hold the tweets.

### Independent worker

At any moment, we only need to fetch "N" latest tweets. So, we could have a reasonable number for our cache size (say, 1k or 10k tweets), and launch a background thread to keep the cache in sync. This "worker" thread (isolated from the main thread) runs in an infinite loop, making API requests every 2 seconds (utilizing our app's rate limit entirely), writing batches of tweet JSONs to a file. The `TwitterAPI` library inherently supports pagination, and so we'll get a continuous flood of tweets (until we reach our cache limit).

The time taken for populating the cache is rather fast. Twitter API supports getting up to 100 tweets per request, which means we can get 2000 tweets in a minute (*which is fast!*). With this setup, we don't have to rely on the API every time for a fetch. Whenever we need some, we just get it from the cache. Moreover, the worker reads the config file every time before it fills up the cache. So, any changes made to the config will reflect back on the cache during the next iteration.

### Further improvements

 - The cache is much like a database of tweets. Its size will affect the performance of fetching. We could either go for an actual database, or (if it's an overkill), we could simply pad the lines and implement a simple cursor to "seek" through the file and get the necessary data.

 - Would there be any need to wrap a web framework around this (which I hope not), then it could be linked to a simple server which responds to AJAX calls from the client for the latest tweets.
