import re
import os
import json
import pandas as pd

from flask import Flask, request, make_response
from slack_sdk import WebClient
from slack_bolt import App, Say
from slack_bolt.adapter.flask import SlackRequestHandler
from dotenv import load_dotenv

from utils import *

load_dotenv()

app = Flask(__name__)

token = os.environ.get("CLIENT_TOKEN")
client = WebClient(token=token)

bolt_app = App(token=token, signing_secret=os.environ.get("SIGNING_SECRET"))

handler = SlackRequestHandler(bolt_app)

@app.route("/slack/events", methods=["POST"])
def handle_events():
    return handler.handle(request)

LATEST_ASSIGNMENTS = []
LATEST_WEIGHTS = {}

@bolt_app.command('/codepals-generate')
def codepals_generate(ack, respond, command):
    ack()
    if ('text' in command) and (command['text'] == os.environ.get('CODEPALS_PASSWORD')):
        respond('generating...', response_type='in_channel')
        roster = read_roster(path=PREPEND+ROSTER_PATH)
        weights = read_weights(path=PREPEND+JSON_PATH)
        weights = sync_weights(roster, weights)
        verify_weights(weights)
        assignments, weights = assign(roster, weights)
        msg = '*ASSIGNMENT*:\n'
        
        for pairing in assignments:
            for email in pairing:
                msg += get_name_by_email(email) + ' - '
            msg = msg[:-2] + '\n'
        
        respond(msg, response_type='in_channel')
        
        global LATEST_ASSIGNMENTS
        global LATEST_WEIGHTS
        LATEST_ASSIGNMENTS = assignments
        LATEST_WEIGHTS = weights
    else:
        respond('failed', response_type='in_channel')

FREQUENCIES = {'0', '1' ,'2'}

@bolt_app.command('/codepals-frequency')
def update_frequency(ack, respond, command):
    ack()
    if 'text' in command and command['text'] in FREQUENCIES:
        email, val = get_email(command["user_id"]), int(command['text'])
        if val < 0:
            respond('failed. please select a nonnegative integer (e.g. `/codepals-frequency 1`)', response_type='in_channel')
            return
        update_roster(email, val, path=PREPEND+ROSTER_PATH)
        respond(f'successfully updated {email} with {val} frequency', response_type='in_channel')
    else:
        respond('failed. please select a nonnegative integer (e.g. `/codepals-frequency 1`)', response_type='in_channel')

@bolt_app.command('/codepals-assign')
def codepals_assign(ack, respond, command):
    ack()
    if 'text' in command and command['text'].split(' ')[0] == os.environ.get('CODEPALS_PASSWORD'):
        global LATEST_ASSIGNMENTS
        global LATEST_WEIGHTS
        if not LATEST_ASSIGNMENTS and not LATEST_WEIGHTS:
            respond('please generate codepals assignments first with /codepals-generate {PASSWORD}', response_type='in_channel')
            return
        elif not LATEST_ASSIGNMENTS:
            respond('failed', response_type='in_channel')
            return
        elif not LATEST_WEIGHTS:
            respond('failed', response_type='in_channel')
            return

        splits = command['text'].split(' ')
        respond('sending...', response_type='in_channel')
        if len(splits) > 1 and splits[1] != '':
            create_dms(LATEST_ASSIGNMENTS, respond, msg=' '.join(splits[1:]))
        else:
            create_dms(LATEST_ASSIGNMENTS, respond)

        write_weights(LATEST_WEIGHTS, path=PREPEND+JSON_PATH)
        LATEST_ASSIGNMENTS = []
        LATEST_WEIGHTS = {}
        respond('codepals assignments sent!', response_type='in_channel')
    else:
        respond('failed', response_type='in_channel')

LATEST_TEST_ASSIGNMENTS = []
LATEST_TEST_WEIGHTS = {}

@bolt_app.command('/test-codepals-generate')
def test_codepals_generate(ack, respond, command):
    ack()
    if 'text' in command and command['text'] == 'test':
        respond('generating...', response_type='in_channel')
        roster = read_roster(path=PREPEND+'test.csv')
        weights = read_weights(path=PREPEND+'test.json')
        weights = sync_weights(roster, weights)
        verify_weights(weights)
        assignments, weights = assign(roster, weights)
        msg = '*ASSIGNMENT*:\n'
        
        for pairing in assignments:
            for email in pairing:
                msg += get_name_by_email(email) + ' - '
            msg = msg[:-2] + '\n'

        respond(msg, response_type='in_channel')

        global LATEST_TEST_ASSIGNMENTS
        global LATEST_TEST_WEIGHTS
        LATEST_TEST_ASSIGNMENTS = assignments
        LATEST_TEST_WEIGHTS = weights
    else:
        respond('failed', response_type='in_channel')

@bolt_app.command('/test-codepals-frequency')
def test_update_frequency(ack, respond, command):
    ack()
    if 'text' in command and command['text'] in FREQUENCIES:
        email, val = get_email(command["user_id"]), int(command['text'])
        if val < 0:
            respond('failed. please select a nonnegative integer (e.g. `/codepals-frequency 1`)', response_type='in_channel')
            return
        update_roster(email, val, path=PREPEND+'test.csv')
        respond(f'successfully updated {email} with {val} frequency', response_type='in_channel')
    else:
        respond('failed. please select a nonnegative integer (e.g. `/codepals-frequency 1`)', response_type='in_channel')

@bolt_app.command('/test-codepals-assign')
def test_codepals_assign(ack, respond, command):
    ack()
    if 'text' in command and command['text'].split(' ')[0] == 'test':
        global LATEST_TEST_ASSIGNMENTS
        global LATEST_TEST_WEIGHTS
        if not LATEST_TEST_ASSIGNMENTS and not LATEST_TEST_WEIGHTS:
            respond('please generate codepals assignments first with /codepals-generate {PASSWORD}', response_type='in_channel')
            return
        elif not LATEST_TEST_ASSIGNMENTS:
            respond('failed', response_type='in_channel')
            return
        elif not LATEST_TEST_WEIGHTS:
            respond('failed', response_type='in_channel')
            return

        splits = command['text'].split(' ')
        respond('sending...', response_type='in_channel')
        if len(splits) > 1 and splits[1] != '':
            create_dms(LATEST_TEST_ASSIGNMENTS, respond, msg=' '.join(splits[1:]))
        else:
            create_dms(LATEST_TEST_ASSIGNMENTS, respond)

        write_weights(LATEST_TEST_WEIGHTS, path=PREPEND+'test.json')
        LATEST_TEST_ASSIGNMENTS = []
        LATEST_TEST_WEIGHTS = {}
        respond('codepals assignments sent!', response_type='in_channel')
    else:
        respond('failed', response_type='in_channel')

def get_name_by_email(email):
    try:
        user = bolt_app.client.users_lookupByEmail(email=email)['user']
        return user['profile']['display_name'] or user['profile']['real_name']
    except:
        print("couldn't find: ", user)

def get_user_by_email(email):
    try:
        user = bolt_app.client.users_lookupByEmail(email=email)['user']
        return user['id']
    except:
        print("couldn't find:", email)

def get_display_name(user):
    try:
        profile = bolt_app.client.users_profile_get(user=user)['profile']
        return profile['display_name'] or profile['real_name']
    except:
        print("couldn't find:", user)
        
def get_email(user):
    try:
        profile = bolt_app.client.users_profile_get(user=user)['profile']
        return profile['email']
    except:
        print("couldn't find:", user)

DEFAULT_CODEPALS_MSG = "say hi to your new codepals! :)"

def create_dms(assignments, respond, msg=DEFAULT_CODEPALS_MSG):
    for pairings in assignments:
        users = [get_user_by_email(person) for person in pairings]
        group_dm = client.conversations_open(
            users=users
        )
        if not group_dm['ok']:
            respond(f'group {pairings} failed', response_type='in_channel')
        else:
            client.chat_postMessage(
                channel=group_dm['channel']['id'],
                text=msg
            )

PREPEND = sys.path[0] + '/'
if __name__ == '__main__':
    app.run(threaded=True, port=5000)
    PREPEND = ''