import requests
import re

from dateutil import parser
from .models import GithubEvent

# using the regex to extract the username part
def extract_username_from_url(github_url):
    match = re.search(r'(https?:\/\/)?(www\.)?github\.com\/(?P<username>[\w-]+)\/?', github_url)
    # match object is None if no match is found
    return match.group("username") if match else ""

def github_event_to_post_adapter(github_events, github_url):
    objects = []
    for event in github_events:
        # we only support certain events
        if event["type"] not in GithubEvent.EventType:
            continue

        try:
            github_event = GithubEvent.objects.get(pk=event["id"])
        except:
            github_event = GithubEvent.objects.create(
                id = event["id"],
                type = event["type"],
                username = event["actor"]["login"],
                url = github_url,
                time = parser.parse(event["created_at"])
            )
            github_event.create_event_content(event)
            github_event.save()
    
        github_event_post = github_event.event_to_post()
        if github_event_post:
            objects.append(github_event_post)

    return objects

def get_github_activity(github_url):
    if github_url is None or "github.com/" not in github_url:
        return []
    
    # using the regex to extract the username part
    username = extract_username_from_url(github_url)
    if len(username) == 0:
        return []

    # Using the GitHub API to fetch the events
    # https://docs.github.com/en/rest/reference/activity#list-public-events-for-a-user
    # this will return the newest 30 activities by default
    response = requests.get(f"https://api.github.com/users/{username}/events")

    if response.status_code != 200:
        print(f"Cannot fetch github activity for user {username}")
        print(f"Request returned a status code of {response.status_code}")
        print(f"Request returned body: {response.text}")
        return None

    return github_event_to_post_adapter(response.json(), github_url)

    
