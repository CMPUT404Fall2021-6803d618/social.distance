import functools
import re
from django.db import models
from django.contrib.auth.models import User
from django.db.models.query_utils import Q

import requests
from requests.models import HTTPBasicAuth, Response
from requests import Request
from rest_framework import exceptions
from authors.models import Author, Follow
from authors.serializers import FollowSerializer

from posts.models import Like, Post
from posts.serializers import LikeSerializer, PostSerializer

global_session = requests.Session()
    
# Create your models here.
class Node(models.Model):
    host_url = models.URLField()
    # username and password that they use, as a client, to be authenticated in our server
    user = models.OneToOneField(User, on_delete=models.CASCADE, null=True) # one2one with django user

    # username and password that WE use, as a client, to authenticate on this node/server
    username = models.CharField(max_length=200) 
    password = models.CharField(max_length=200) 

    def get_basic_auth(self):
        return HTTPBasicAuth(self.username, self.password)

# https://stackoverflow.com/a/24025175
# catch all request error and just print them out instead
def silent_500(fn):
    @functools.wraps(fn)
    def wrapper(*args, **kwargs):
        try:
            return fn(*args, **kwargs)
        except requests.exceptions.RequestException as e:
            print("node connector error: ", e)
    return wrapper

class ConnectorService:
    @staticmethod
    def get_inbox_and_host_from_url(url):
        url_results = re.findall(r'(http[s]?:\/\/[^/]+\/)(author\/[^/]+\/)', url)
        if len(url_results) != 1:
            raise exceptions.APIException(f"cannot match the author endpoint from the url: {url}")
        host, author_path = url_results[0]
        return host + author_path + 'inbox/', host

    @silent_500
    def notify_like(self, like: Like):
        inbox_url, host_url = self.get_inbox_and_host_from_url(like.object)
        node: Node = Node.objects.get(Q(host_url=host_url) | Q(host_url=host_url[:-1]))
        res = global_session.post(inbox_url, json=LikeSerializer(like).data, auth=node.get_basic_auth())
        return res.content

    @silent_500
    def notify_post(self, post: Post):
        # get all follwers and their endpoints
        followers = Author.objects.filter(followings__object=post.author)

        results = []
        # post the post to each of the followers' inboxes
        for follower in followers:
            inbox_url, host_url = self.get_inbox_and_host_from_url(follower.url)
            node: Node = Node.objects.get(Q(host_url=host_url) | Q(host_url=host_url[:-1]))
            res = global_session.post(inbox_url, json=PostSerializer(post).data, auth=node.get_basic_auth())
            results.append(res.content)
        return results

    @silent_500
    def notify_follow(self, follow: Follow):
        target_author = follow.object

        inbox_url, host_url = self.get_inbox_and_host_from_url(target_author.url)
        node: Node = Node.objects.get(Q(host_url=host_url) | Q(host_url=host_url[:-1]))
        res = global_session.post(inbox_url, json=FollowSerializer(follow).data, auth=node.get_basic_auth())
        return res.content
        
connector_service = ConnectorService()