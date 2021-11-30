from django.db import models
from authors.models import Author
from authors.serializers import AuthorSerializer
from posts.models import Post

from datetime import datetime

class GithubEvent(models.Model):
    class EventType(models.TextChoices):
        PUSH_EVENT = 'PushEvent'

    id = models.CharField(primary_key=True, editable=False, max_length=40)
    type = models.CharField(max_length=30, choices=EventType.choices)
    username = models.CharField(max_length=40)
    url = models.URLField()
    event_content = models.TextField(editable=False, default="")
    event_title = models.CharField(max_length=50)
    time = models.DateTimeField()

    # TODO: make everything in markdown (i.e. clickable)
    def create_event_content(self, github_event):
        if github_event["type"] == GithubEvent.EventType.PUSH_EVENT:
            commits = github_event["payload"]["commits"]
            repo = "github.com/" + github_event["repo"]["name"]
            content = f"{self.username} made {len(commits)} commits to {repo} \n"
            for commit in commits:
                content += commit["sha"] + ": " + commit["message"]
            self.event_content = content
            self.save()
    
    # here we are creating a Post JSON to return to the front end
    # the actual Post object is NOT created
    def event_to_post(self):
        data = {
            "title": "GitHub " + self.type,
            "source": self.url,
            "origin": self.url,
            "content_type": "text/markdown",
            "content": self.event_content,
            "published": self.time,
            "visibility": "PUBLIC",
            "unlisted": False
        }
        
        fake_post = Post(**data, author=Author.objects.get(github_url=self.url))

        return fake_post



