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
known_completed = fetch_known_completed_project_set(projectmanagement.KNOWN_COMPLETED_FILENAME)

projects = last_three_linked_projects(linked_once, linked_twice)

def find_completed_project(projects, known_completed):
    for project in projects:
        project_id = project[0]
        project_dict = fetch_project(project_id)
        if project_is_completed(project_dict):
            debug_print("This one is completed! {}".format(project_dict[u"title"]))
            if not project_id in known_completed:
                return project
            else:
                debug_print("Already in known completed.")
        else:
            debug_print("Not completed at {}%: {}".format(project_dict[u"percentFunded"], project_dict[u"title"]))
    return None

project_tuple = find_completed_project(projects, known_completed)
    
if project_tuple:

    tweet_id = project_tuple[projectmanagement.TUPLE_TWEET_ID_INDEX]
    known_completed.add(project_tuple[projectmanagement.TUPLE_PROJECT_ID_INDEX])
    # Set up criteria
    primaryParams = {}
    secondaryParams = {}
    tertiaryParams = {}
    quaternaryParams = {}
    quinternaryParams = {}
    # start with cheap projects in high-poverty areas
    primaryParams["costToComplete"] = 1 # start with $50 and under
    primaryParams["highestPovertyLevel"] = "true" # yeah prioritize these
    primaryParams["sortBy"] = 3 # This means sort by days-remaining, apparently
    # next try the $60 and under ones
    secondaryParams["costToComplete"] = 2
    secondaryParams["highestPovertyLevel"] = "true"
    secondaryParams["sortBy"] = 3 
    # what about high-poverty projects under $100 that are matched?
    tertiaryParams["costToComplete"] = 2
    tertiaryParams["highestPovertyLevel"] = "true"
    tertiaryParams["sortBy"] = 3
    tertiaryParams["internalThreshold"] = MATCHED_THRESHOLD
    tertiaryParams["matchingId"] = -1
    # if we can't find any highest-poverty, fall back to all projects but still $50 and under
    quaternaryParams["costToComplete"] = 1
    quaternaryParams["sortBy"] = 3
    # okay now all matched sub-$100 projects
    quinternaryParams["costToComplete"] = 2
    quinternaryParams["sortBy"] = 3
    quinternaryParams["internalThreshold"] = MATCHED_THRESHOLD
    quinternaryParams["matchingId"] = -1
    
    params_set_list = [primaryParams, secondaryParams, tertiaryParams, quaternaryParams, quinternaryParams]
    tryConnection(api, params_set_list, linked_once, linked_twice, last_linked, last_linked_time, tweet_id)
    write_known_completed_projects(known_completed, projectmanagement.KNOWN_COMPLETED_FILENAME)