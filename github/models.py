from django.db import models
from authors.models import Author
from authors.serializers import AuthorSerializer
from posts.models import Post

from datetime import datetime

class GithubEvent(models.Model):
    class EventType(models.TextChoices):
        # One or more commits are pushed to a repository branch or tag
        PUSH_EVENT = 'PushEvent'
        # A Git branch or tag is created
        CREATE_EVENT = 'CreateEvent'
        # A git branch or tag is deleted
        DELETE_EVENT = 'DeleteEvent'
        # When user stars a repository
        WATCH_EVENT = 'WatchEvent'
        # A user forks a repository
        FORK_EVENT = "ForkEvent"

    id = models.CharField(primary_key=True, editable=False, max_length=40)
    type = models.CharField(max_length=30, choices=EventType.choices)
    username = models.CharField(max_length=40)
    url = models.URLField()
    event_content = models.TextField(editable=False, default="")
    event_title = models.CharField(max_length=50)
    time = models.DateTimeField()

    def __str__(self):
        return f"{self.username} | {self.type} | {str(self.id)}"

    def create_event_content(self, github_event):
        try:
            repo_name = github_event["repo"]["name"]
            repo_url = "https://github.com/" + repo_name
            repo_md = f"[{repo_name}]({repo_url})"
            user_md = f"[{self.username}]({self.url})"
            if github_event["type"] == GithubEvent.EventType.PUSH_EVENT:
                commits = github_event["payload"]["commits"]
                content = f"{user_md} made {len(commits)} commit(s) to repo {repo_md}: \n"
                for commit in commits:
                    sha = commit["sha"]
                    message = commit["message"]
                    sha_url = commit["url"].replace("repos/", "").replace("api", "www")
                    content += f"[{sha}]({sha_url}): {message}"
            elif github_event["type"] == GithubEvent.EventType.CREATE_EVENT \
                or github_event["type"] == GithubEvent.EventType.DELETE_EVENT:
                ref = github_event["payload"]["ref"]
                ref_type = github_event["payload"]["ref_type"]

                # either "created" or "deleted"
                event_type = github_event["type"][0:6].lower() + "d"
                if ref:
                    content = f"{user_md} {event_type} the {ref} {ref_type} in repo {repo_md}"
                elif ref_type == "repository":
                    content = f"{user_md} {event_type} the repository {repo_md}"
            elif github_event["type"] == GithubEvent.EventType.WATCH_EVENT:
                content = f"{user_md} starred repo {repo_md}"
            elif github_event["type"] == GithubEvent.EventType.FORK_EVENT:
                content = f"{user_md} forked repo {repo_md}"

            if 'content' in locals():
                self.event_content = content
                self.save()
        except:
            pass

    
    # here we are creating a fake Post object to return to the front end
    # but this fake Post is NOT stored into the database
    def event_to_post(self):
        data = {
            "title": "GitHub " + self.type,
            "source": self.url,
            "origin": self.url,
            "content_type": "text/markdown",
            "content": self.event_content,
            "published": self.time,
            "visibility": "PUBLIC",
            "unlisted": False,
            "is_github": True
        }
        
        fake_post = Post(**data, author=Author.objects.get(github_url=self.url))

        return fake_post



