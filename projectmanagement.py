#!/usr/bin/env python
# -*- coding: utf-8 -*-

import tweepy, time, sys, os, random, requests, urllib, datetime, unicodedata, operator
from emoji import emojize
from dateutil import parser
from BeautifulSoup import BeautifulStoneSoup
from butils import debug_print

TIME_THRESHOLD = 45
POST_FREQUENCY_HOURS = 6
COST_THRESHOLD = 60.0
MATCHED_THRESHOLD = 100.0
MATCHED_MAX_THRESHOLD = 201.00
BASE_URL = 'http://api.donorschoose.org/common/json_feed.html?'

LINKED_ONCE_FILENAME = "linked_once"
LINKED_TWICE_FILENAME = "linked_twice"
LAST_LINKED_FILENAME = "last_linked"
KNOWN_COMPLETED_FILENAME = "known_completed"

TUPLE_PROJECT_ID_INDEX = 0
TUPLE_TWEET_ID_INDEX = 1
TUPLE_DATE_INDEX = 2

DICT_TWEET_ID_INDEX = 0
DICT_DATE_INDEX = 1
        
def within_expiration_threshold(date_string):
    threshold = datetime.datetime.now() + datetime.timedelta(days=TIME_THRESHOLD)
    exp_date = parser.parse(date_string)
    return exp_date <= threshold
    
def within_cost_threshold(cost, threshold):
    return float(cost) < threshold and float(cost) > 1.00
    
def already_posted_within_hours(last_linked_time, hours_limit):
    return last_linked_time > datetime.datetime.now() - datetime.timedelta(hours=6)
    
def already_linked_today(project_id, linked_once, linked_twice):
    if project_id in linked_once:
        last_linked = linked_once[project_id][DICT_DATE_INDEX]
        return last_linked < datetime.datetime.now() - datetime.timedelta(days=1)
    else:
        return False

def already_linked_once(project_id, linked_once):
    return project_id in linked_once
    
def already_linked_twice(project_id, linked_twice):
    return project_id in linked_twice
    
def save_posted_project(project_id, status_id, linked_once, linked_twice):  
    appendedDate = datetime.datetime.now()#.strftime("%Y-%m-%d %H:%M:%S")
    if (already_linked_once(project_id, linked_once)):
        linked_twice[project_id] = (status_id, appendedDate)
        del linked_once[project_id]
    else:
        linked_once[project_id] = (status_id, appendedDate)
    return (linked_once, linked_twice)
        
def fetch_last_project(filename):
    project_id = ""
    last_status_id = 0
    last_date = datetime.datetime.now()
    with open(filename, "r") as lastfile:
        splitline = lastfile.read().split('|')
        if len(splitline) >= 3:
            project_id = splitline[TUPLE_PROJECT_ID_INDEX]
            last_status_id = splitline[TUPLE_TWEET_ID_INDEX]
            last_date = parser.parse(splitline[TUPLE_DATE_INDEX])
    return (project_id, last_status_id, last_date)
    
def write_last_project(project_id, status_id, filename):
    with open(filename, "w") as outfile:
        outfile.write("|".join([project_id, status_id, datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")]))

def fetch_linked_projects(filename):
    lines = open(filename).read().splitlines()
    result = {}
    for line in lines:
        splitline = line.split('|')
        result[splitline[TUPLE_PROJECT_ID_INDEX]] = (splitline[TUPLE_TWEET_ID_INDEX], parser.parse(splitline[TUPLE_DATE_INDEX]))
    return result
    
def last_three_linked_projects(linked_once, linked_twice):
    linked_once_flat_list = []
    linked_twice_flat_list = []
    
    for item in linked_once.items():
        linked_once_flat_list.append((item[0], item[1][DICT_TWEET_ID_INDEX], item[1][DICT_DATE_INDEX]))
    linked_once = sorted(linked_once_flat_list, key=operator.itemgetter(TUPLE_DATE_INDEX), reverse=True)[0:3]

    for item in linked_twice.items():
        linked_twice_flat_list.append((item[0], item[1][DICT_TWEET_ID_INDEX], item[1][DICT_DATE_INDEX]))
    linked_twice = sorted(linked_twice_flat_list, key=operator.itemgetter(TUPLE_DATE_INDEX), reverse=True)[0:3]

    linked_merged = linked_once + linked_twice
    linked_merged = sorted(linked_merged, key=operator.itemgetter(TUPLE_DATE_INDEX), reverse=True)[0:3]
    
    return linked_merged

def write_linked_projects(linked_dict, filename):
    lines = []
    linked_flat_list = []
    with open(filename, "w") as outfile:
        linked_items = linked_dict.items()
        for item in linked_items:
            linked_flat_list.append((item[0], item[1][DICT_TWEET_ID_INDEX], item[1][DICT_DATE_INDEX]))
        for item_tuple in sorted(linked_flat_list, key=operator.itemgetter(TUPLE_DATE_INDEX)):
            lines.append("|".join([item_tuple[TUPLE_PROJECT_ID_INDEX], item_tuple[TUPLE_TWEET_ID_INDEX], item_tuple[TUPLE_DATE_INDEX].strftime("%Y-%m-%d %H:%M:%S")]))
        outfile.write('\n'.join(lines))
        
def fetch_known_completed_project_set(filename):
    lines = open(filename).read().splitlines()
    return set(lines)
        
def write_known_completed_projects(project_set, filename):
    with open(filename, "w") as outfile:
        outfile.write("\n".join(project_set))

def within_hard_limit(item, hard_limit):
    # enforces a hard upper bound--used in pocket change script
    if float(item["costToComplete"]) < hard_limit:
        return True
    else:
        return False

def qualifies_for_linking(item):
    # a randomizer to decide whether to link things over $60
    if float(item["costToComplete"]) < 61.0 or random.randint(0,12) == 0:
        return True
    else:
        return False
        
def project_is_completed(project_dictionary):
    if u"percentFunded" in project_dictionary:
        return project_dictionary[u"percentFunded"] == u"100"
    else:
        raise ValueError('No percentFunded in project')

def fetch_project(project_id):
    params = {"id": project_id}
    resp = requests.get(BASE_URL+urllib.urlencode(params))
    if resp.status_code != 200:
        raise ApiError('ERROR {}'.format(resp.status_code))
    proposals = resp.json()["proposals"]
    if len(proposals):
        return proposals[0]
    else:
        return None

def fetch_projects(params, cost_threshold = COST_THRESHOLD, linked_once = {}, linked_twice = {}, last_linked = ""):
    item = None
    found_id = None
    debug_print("trying with cost threshold {}".format(cost_threshold))
    if "internalThreshold" in params:
        del params["internalThreshold"]
    resp = requests.get(BASE_URL+urllib.urlencode(params))
    if resp.status_code != 200:
        raise ApiError('ERROR {}'.format(resp.status_code))
    for item in resp.json()["proposals"]:
        if not already_linked_twice(item["id"], linked_twice) and \
          not already_linked_today(item["id"], linked_once, linked_twice) and \
          item["id"] != last_linked and \
          within_expiration_threshold(item["expirationDate"]) and \
          within_cost_threshold(item["costToComplete"], cost_threshold) :
            found_id = item["id"]
            break
    return (found_id, item)

template_list = ["{1}'s {2} project is {3}% funded! It only needs ${4}! {5}",
                "The {2} project for {1}'s class at {0} is only ${4} from completion! {5}",
                "Feel like helping out {1}'s class at {0}? {5} It's only ${4} from completion!"
                "{5} - Check it out, the {2} project only needs ${4} to hit 100%! Are you the one to put it over the top?",
                "{5} - Oh cool, only ${4} and {1}'s {2} project will hit 100%! Want to be their champ today?",
                "Have you seen {1}'s project, {2}, for {0}? {5} They're just ${4} from hitting the mark...",
                "Have you seen the {2} project? {5} They're just ${4} from hitting the mark...",
                "If you've got a little extra in your pocket, maybe throw it at the {2} project? {5} {1} only needs ${4}!",
                "All right. The {2} project is already {3}% funded. Let's do this. {5}",
                "All right. {1}'s {2} project is already {3}% funded. Let's do this. {5}",
                "Today's easy win: the {2} project for {0} is just ${4} from funding! {5}",
                "Hey champs, have you seen this one? {5} Just ${4} to go!",
                "Hey, THAT'S an easy win. {5} {1}'s {2} project only needs ${4} to fund!",
                "If you support {0}, you can show it by funding the {2} project! {5} They only need ${4}!",
                "You can help out {1}'s class right now by tossing the {2} project just ${4}. They're {3}% funded already! {5}",
                "The {2} project in {7}, {8} is already {3}% funded! {5} Think you can donate the other ${4}?",
                "Your chance to be a champ: {5} {1}'s {2} project is just ${4} from funding!",
                "{1}'s project at {0} in {7}, {8} is {3}% funded! It only needs ${4}! {5}",
                "{1}'s class project at {0} in {7}, {8} is only ${4} from completion! {5}",
                "Feel like helping out {1}'s class in {7}, {8} at {0}? {5} It's only ${4} from completion!"
                "{5} - Check it out, this project in {7}, {8} only needs ${4} to hit 100%! Are you the one to put it over the top?",
                "{5} - Oh cool, only ${4} and {1}'s project will hit 100%! Want to be their champ today?",
                "Have you seen {1}'s project for {0} in {7}, {8}? {5} They're just ${4} from hitting the mark...",
                "Got a little extra this month? Maybe throw it at the {2} project in {7}, {8}? {5}",
                "The {2} project in {7}, {8} is already {3}% funded. Let's do this. {5}",
                "{1}'s {2} project is already {3}% funded. Let's do this! {5}",
                "Today's easy win: the {2} project is just ${4} from funding! {5}",
                "Hey champs, have you seen this one in {7}, {8}? {5} Just ${4} to go!",
                "{1}'s {2} project only needs ${4}! {5}",
                "Be a champ for {7}, {8} by funding the {2} project!!",
                "You can help out @DonorsChoose right now by tossing the {2} project in {7}, {8} just ${4}! {5}",
                "The {2} project is already {3}% funded! {5} Think you can donate the other ${4}?",
                "Your chance to be a champ: {5} The {2} project is just ${4} from funding!"]
                
shorter_template_list = ["{1}'s project is {3}% funded! It only needs ${4}! {5}",
                "{1}'s class project at {0} is only ${4} from completion! {5}",
                "Feel like helping out {1}'s class at {0}? {5} It's only ${4} from completion!"
                "{5} - Check it out, this project only needs ${4} to hit 100%! Are you the one to put it over the top?",
                "{5} - Oh cool, only ${4} and {1}'s project will hit 100%! Want to be their champ today?",
                "Have you seen {1}'s project for {0}? {5} They're just ${4} from hitting the mark...",
                "Got a little extra this month? Maybe throw it at the {2} project? {5}",
                "The {2} project is already {3}% funded. Let's do this. {5}",
                "{1}'s {2} project is already {3}% funded. Let's do this! {5}",
                "Today's easy win: the {2} project is just ${4} from funding! {5}",
                "Hey champs, have you seen this one? {5} Just ${4} to go!",
                "{1}'s {2} project only needs ${4} to fund! {5}",
                "Be a champ by funding the {2} project! {5} {1} only needs ${4}!",
                "You can help out @DonorsChoose right now by tossing the {2} project just ${4}! {5}",
                "The {2} project is already {3}% funded! {5} Think you can donate the other ${4}?",
                "Your chance to be a champ: {5} The {2} project is just ${4} from funding!",
                "Hey champs, have you seen this one in {7}, {8}? {5} Just ${4} to go!",
                "{1}'s {2} project only needs ${4}! {5}"]
                
matched_template_list = ["All right, champs, can we do this together? {5} The {2} project needs ${4} and your donation will be matched!",
                "Donations are being matched for {1}'s {2} project today: {5} Looks like an easy win!",
                "The {2} project in {7}, {8} is having donations matched {5} and it's {3}% funded already!",
                "Shouldn't take much to finish funding {1}'s {2} project--it needs ${4}, but all donations will be matched! {5}",
                "{5} Donations to the {2} project are being matched, and they're {3}% funded already! Just ${4} to go!",
                "You can help out {1}'s class right now and get your donation matched! {5} They're already {3}% funded!",
                "All right, champs, can we do this together? {5} This project needs ${4} and your donation will be matched!",
                "Donations are being matched for {1}'s project in {7}, {8} today: {5}",
                "{1}'s project in {7}, {8} is having donations matched {5} and it's {3}% funded already!",
                "Shouldn't take much to finish funding {1}'s project in {7}, {8}--it needs ${4}, but all donations will be matched! {5}",
                "{5} Donations to {1}'s project are being matched, and they're {3}% funded already! Just ${4} to go!",
                "You can help out {1}'s class in {7}, {8} right now and get your donation matched! {5} They're already {3}% funded!"]
                
shorter_matched_template_list = ["All right, champs, can we do this together? {5} This project needs ${4} and your donation will be matched!",
                "Donations are being matched for {1}'s project today: {5} Let's give away someone else's money too!",
                "{1}'s project is having donations matched {5} and it's {3}% funded already!",
                "Shouldn't take much to finish funding {1}'s project--it needs ${4}, but all donations will be matched! {5}",
                "{5} Donations to {1}'s project are being matched, and they're {3}% funded already!",
                "You can help out {1}'s class right now and get your donation matched! {5} They're already {3}% funded!"]

connection_template_list = [":leftwards_black_arrow: FUNDED! That was quick. {5} Want to knock out another one today? {1}'s project only needs ${4}!",
                "Aaaand FUNDED! EMOJI PARTY! :party_popper: Okay, on to the next. Check out {1}'s project: {5}",
                "BOOM! DONE! :banknote_with_dollar_sign: If you missed your shot, this next project only needs ${4}: {5}",
                ":leftwards_black_arrow: NICE! That one's done. What about {1}'s project in {7}, {8}? {5}",
                ":party_popper: FUNDED! :party_popper: Now, have you seen what {1} is doing? {5}",
                "BAM. That's another one in the books. Think we can put together {4} for {1}'s class? {5}",
                "GOOOOOOOOOALLLL! :confetti_ball: Bet we can do the same for {1}'s class! {5}",
                "Put a bow on it because that project is DONE! :ribbon: What about this one? {5} Only ${4} left!",
                ":confetti_ball: Donations DONE! Wonder if we can finish up {5} next? It'll only take ${4}!",
                "Hope you were quick enough, because that project is DONE! :party_popper: You can still get in on {5} though!"]
                
def HTMLEntitiesToUnicode(text):
    """Converts HTML entities to unicode.  For example '&amp;' becomes '&'."""
    text = unicode(BeautifulStoneSoup(text, convertEntities=BeautifulStoneSoup.ALL_ENTITIES))
    return text
            
def templatize(item, template_list=template_list, shorter_template_list=shorter_template_list, matched_template_list=matched_template_list, shorter_matched_template_list=shorter_matched_template_list):
    if len(item) == 0:
        return

    chosen_template_list = template_list
    chosen_shorter_template_list = shorter_template_list
    
    # determine if project is matched before picking template list. maybe.
    if "matchingFund" in item and len(item["matchingFund"]) > 0 and random.randrange(2):
        chosen_template_list = matched_template_list
        chosen_shorter_template_list = shorter_matched_template_list
    
    debug_print("first item in the template list is {}".format(chosen_template_list[0]))
    debug_print("first item in the shorter template list is {}".format(chosen_shorter_template_list[0]))
    
    param_array = [HTMLEntitiesToUnicode(item["schoolName"]),
        HTMLEntitiesToUnicode(item["teacherName"]),
        HTMLEntitiesToUnicode(item["title"]),
        item["percentFunded"],
        item["costToComplete"],
        "{}",
        (100.0 - float(item["percentFunded"])),
        item["city"],
        item["state"]]

    retries = 0
    result = random.choice(chosen_template_list).format(*param_array)
    debug_print("choosing from list with length {}...".format(len(chosen_template_list)))
    while len(result) > 114 and retries < 5:
        result = random.choice(chosen_template_list).format(*param_array)            
        retries += 1
        
    # potentially keep trying with shorter list
    while len(result) > 114 and retries < 10:
        debug_print("tweets were too long, choosing from list with length {}...".format(len(chosen_shorter_template_list)))
        result = random.choice(chosen_shorter_template_list).format(*param_array)
        retries += 1
    
    if len(result) > 114:
        # last resort
        result = "{1}'s project in {7}, {8} only needs ${4}: {5}".format(*param_array)
                    
    # we're under target tweet length, add the URL
    result = result.format(item["proposalURL"])
        
#     I think the proposalURL is better?
#     result += item["fundURL"]
    return result
    
def connectize(item, template_list=connection_template_list):
    if len(item) == 0:
        return
    
    param_array = [HTMLEntitiesToUnicode(item["schoolName"]),
        HTMLEntitiesToUnicode(item["teacherName"]),
        HTMLEntitiesToUnicode(item["title"]),
        item["percentFunded"],
        item["costToComplete"],
        "{}",
        (100.0 - float(item["percentFunded"])),
        item["city"],
        item["state"]]
        
    debug_print("choosing from list with length {}...".format(len(template_list)))
    
    retries = 0
    result = random.choice(template_list).format(*param_array)
    while len(result) > 114 and retries < 10:
        result = random.choice(template_list).format(*param_array)
        retries += 1
            
    if len(result) > 114:
        # last resort
        result = "FUNDED! Next up, this project in {7}, {8} only needs ${4}: {5}".format(*param_array)
        
    # we're under target tweet length, add the URL
    result = result.format(item["proposalURL"])
        
    return result


def tryConnection(api, params_set_list, linked_once, linked_twice, last_linked, last_linked_time, reply_status_id):
    
    found_id = None
    found_tweet = None
    item = None
    
    # try each possible set of search parameters          
    for params in params_set_list:
        cost_threshold = COST_THRESHOLD
        if "internalThreshold" in params:
            cost_threshold = params["internalThreshold"]
        found_id, item = fetch_projects(params, cost_threshold, linked_once, linked_twice, last_linked)
        if item is not None and found_id is not None:
            found_tweet = connectize(item)
            debug_print(found_tweet)
            break
    
    debug_print("found a candidate for connection: {}".format(found_id))
    # tweet only if this isn't the same one we just linked
    if found_id is not None:
        debug_print("TWEETING THAT")
        status = api.update_status(status=emojize(found_tweet), in_reply_to_status_id=reply_status_id)
        status_id = status.id_str
        linked_once, linked_twice = save_posted_project(found_id, status_id, linked_once, linked_twice)
        write_last_project(found_id, status_id, LAST_LINKED_FILENAME)
        # TODO someday discard projects older than a year
        write_linked_projects(linked_once, LINKED_ONCE_FILENAME)
        write_linked_projects(linked_twice, LINKED_TWICE_FILENAME)

def tryRetrieval(api, params_set_list, linked_once, linked_twice, last_linked, last_linked_time, ignore_frequency = False, hard_limit=200.0):

    found_id = None
    found_tweet = None
    item = None
    
    # Only post every six hours at most. Possible to ignore this for special (cheap) cases
    if (not ignore_frequency) and already_posted_within_hours(last_linked_time, POST_FREQUENCY_HOURS):
        debug_print("last post too recent. returning")
        return
    
    # try each possible set of search parameters
    for params in params_set_list:
    #     print("trying params {}".format(params))
        cost_threshold = COST_THRESHOLD
        if "internalThreshold" in params:
            cost_threshold = params["internalThreshold"]
        found_id, item = fetch_projects(params, cost_threshold, linked_once, linked_twice, last_linked)
        if item is not None and found_id is not None:
            found_tweet = templatize(item)
            debug_print(found_tweet)
            break
    
    debug_print("found a candidate to tweet about: {}".format(found_id))
    # tweet ONLY IF this falls within the probability/money boundary
    if found_id is not None and within_hard_limit(item, hard_limit) and qualifies_for_linking(item):
        debug_print("TWEETING THAT")
        status = api.update_status(status=emojize(found_tweet))
        status_id = status.id_str
        linked_once, linked_twice = save_posted_project(found_id, status_id, linked_once, linked_twice)
        write_last_project(found_id, status_id, LAST_LINKED_FILENAME)            
        # TODO someday discard projects older than a year
        write_linked_projects(linked_once, LINKED_ONCE_FILENAME)
        write_linked_projects(linked_twice, LINKED_TWICE_FILENAME)
    else:
        debug_print("NOT tweeting that.")