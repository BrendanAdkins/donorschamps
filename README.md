# This is a Twitter bot for crawling DonorsChoose

It's not a very sophisticated bot but it tries to behave well. During daylight hours for most of the United States, it searches for projects created by teachers who need funding and only need a small amount of money to reach their goal. It has a preference for schools with high poverty levels among their students and for projects that are having their donations matched somehow. It picks a template from a list and inserts the relevant data, then tweets that (or will retry if the resulting tweet is too long). It won't link to any project twice in a row, or more than twice, period. If one of the projects it linked completes its funding run, it will tweet in celebration, then search for a new one.

# This is how you would install this robot

Drop its files into a directory and set up a crontab to run it sometimes. You'd also need Twitter keys for an app and an account, which you can obtain at https://apps.twitter.com/ and drop into the `credentials` file. (The DonorsChoose API does not currently require a key.)

# This is what its crontab looks like

```
14,28,42,56  0,16,17,18,19,20,21,22,23 * * * python /home/donorschamps/retrieve_pocket_change.py
16,30,44,58  0,16,17,18,19,20,21,22,23 * * * python /home/donorschamps/retrieve_normal.py
6,24,38,52  0,16,17,18,19,20,21,22,23 * * * python /home/donorschamps/followup.py
```

(This is set for a server on UTC.)

# These are its dependencies

[Tweepy](https://pypi.python.org/pypi/tweepy)
[Emoji](https://pypi.python.org/pypi/emoji/)
[Beautiful Soup](https://pypi.python.org/pypi/beautifulsoup4/)

# I know I need to get around to writing an actual setup file. I'm new at this

There's some refactoring to do yet too.

# This is its license

Donors Champs is released under the terms of the [MIT license](http://choosealicense.com/licenses/mit/).

