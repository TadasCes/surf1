import os

from googleapiclient.discovery import build
import json
import requests
from dotenv import load_dotenv
import logging
import os
from slack_sdk import WebClient
from slack_sdk.errors import SlackApiError
import certifi
import ssl
import slack
import aiohttp
import schedule
import time

# CONFIG
load_dotenv()
API_KEY = os.getenv("API_KEY")
SLACK_WEBHOOK = os.getenv("SLACK_WEBHOOK")
SLACK_BOT_TOKEN = os.getenv("SLACK_BOT_TOKEN")

ssl_context = ssl.create_default_context()
ssl_context.check_hostname = False
ssl_context.verify_mode = ssl.CERT_NONE
client = slack.WebClient(token=SLACK_BOT_TOKEN,
                         ssl=ssl_context)
logger = logging.getLogger(__name__)

scopes = ["https://www.googleapis.com/auth/youtube.force-ssl"]
api_service_name = "youtube"
api_version = "v3"

monitored_keyword = ""
channel_id = None
# ===


def main():
    try:
        get_channel_id()

        if (monitored_keyword == ""):
            get_search_keyword()

        schedule.every().minute.do(get_search_keyword)
        schedule.every(10).minutes.do(get_youtube_results)

        while True:
            schedule.run_pending()
    except Exception as e:
        print(f"Error: {e}")


# get results from youtube API and sends message to slack channel
def get_youtube_results():
    try:
        youtube = build(api_service_name, api_version, developerKey=API_KEY)
        request = youtube.search().list(
            part="snippet",
            maxResults=5,
            q=monitored_keyword
        )
        response = request.execute()
        result = json.dumps(response, indent=4)
        send_slack_message(result)

    except Exception as e:
        print(f"Error: {e}")


def send_slack_message(message):
    try:
        slack_url = "https://hooks.slack.com/services/" + SLACK_WEBHOOK
        requests.post(url=slack_url, data=json.dumps(
            {"text": message}), headers={'Content-Type': 'application/json'})
    except Exception as e:
        print(f"Error: {e}")


# Scans slack channel for users messages, retrieves last one, if contains predefined value, sets text as a keyword
def get_search_keyword():
    global monitored_keyword
    conversation_history = []
    current_keyword = monitored_keyword
    try:
        result = client.conversations_history(channel=channel_id)
        conversation_history = result["messages"]
        sorted_by_time = sorted(conversation_history,
                                key=lambda d: d['ts'], reverse=False)
        for message in sorted_by_time:
            if "user" in message:
                if ".look:" in message['text']:
                    monitored_keyword = message['text'].split(':')[1].strip()

        if (current_keyword != monitored_keyword):
            send_slack_message("now monitoring: " + monitored_keyword)

    except SlackApiError as e:
        logger.error("Error creating conversation: {}".format(e))


# Retrieves monitoring channel id
def get_channel_id():
    channel_name = "keyword-monitoring"
    global channel_id
    try:
        for result in client.conversations_list():
            if channel_id is not None:
                break
            for channel in result["channels"]:
                if channel["name"] == channel_name:
                    channel_id = channel["id"]
                    break

    except SlackApiError as e:
        print(f"Error: {e}")


if __name__ == "__main__":
    main()
