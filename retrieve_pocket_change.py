#!/usr/bin/env python
# -*- coding: utf-8 -*-

import tweepy, time, sys, os, random, requests, urllib, datetime, unicodedata, operator
from dateutil import parser
import projectmanagement
from projectmanagement import *
from butils import debug_print

credlist = open("./credentials").read().splitlines()
CONSUMER_KEY = credlist[0]
CONSUMER_SECRET = credlist[1]
ACCESS_KEY = credlist[2]
ACCESS_SECRET = credlist[3]
DC_API_KEY = credlist[5]
auth = tweepy.OAuthHandler(CONSUMER_KEY, CONSUMER_SECRET)
auth.set_access_token(ACCESS_KEY, ACCESS_SECRET)
api = tweepy.API(auth)

linked_once = fetch_linked_projects(projectmanagement.LINKED_ONCE_FILENAME)
linked_twice = fetch_linked_projects(projectmanagement.LINKED_TWICE_FILENAME)
last_linked, last_status_id, last_linked_time = fetch_last_project(projectmanagement.LAST_LINKED_FILENAME)

# Set up criteria
primaryParams = {}
secondaryParams = {}
# start with cheap projects in high-poverty areas
primaryParams["costToComplete"] = 1 # start with $50 and under
primaryParams["highestPovertyLevel"] = "true" # yeah prioritize these
primaryParams["sortBy"] = 3 # This means sort by days-remaining, apparently
# next try the $50 and under ones that aren't from poverty schools
secondaryParams["costToComplete"] = 2
secondaryParams["sortBy"] = 3 

params_set_list = [primaryParams, secondaryParams]
    
tryRetrieval(api, params_set_list, linked_once, linked_twice, last_linked, last_linked_time, True, 30.0)