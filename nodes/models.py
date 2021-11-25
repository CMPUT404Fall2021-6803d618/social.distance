import functools
import re
from django.db import models
from django.contrib.auth.models import User
from django.db.models.query_utils import Q
from typing import List

import requests
from requests.models import HTTPBasicAuth, Response
from requests import Request
from rest_framework import exceptions
from authors.models import Author, Follow, InboxObject
from authors.serializers import FollowSerializer

from posts.models import Like, Post
from posts.serializers import LikeSerializer, PostSerializer

import logging
logger = logging.getLogger(__name__)

global_session = requests.Session()
    
# Create your models here.
class Node(models.Model):
    # name of the node
    name = models.CharField(max_length=200, default="foreign_server")

    host_url = models.URLField(max_length=500)
    # username and password that they use, as a client, to be authenticated in our server
    user = models.OneToOneField(User, on_delete=models.CASCADE, null=True) # one2one with django user

    # username and password that WE use, as a client, to authenticate on this node/server
    username = models.CharField(max_length=200) 
    password = models.CharField(max_length=200) 

    def get_basic_auth(self):
        return HTTPBasicAuth(self.username, self.password)

    def get_basic_auth_tuple(self):
        return (self.username, self.password)

# https://stackoverflow.com/a/24025175
# catch all request error and just print them out instead
def silent_500(fn):
    @functools.wraps(fn)
    def wrapper(*args, **kwargs):
        try:
            return fn(*args, **kwargs)
        except requests.exceptions.RequestException as e:
            logger.error("node notifying error: ", e)
    return wrapper

class ConnectorService:
    @staticmethod
    def get_target_users_for_post(post: Post):
        """
        - public posts are sent to all followers
        - friend posts are sent to friends only
        - unlisted posts are not sent to anyone
        """
        if post.visibility == Post.Visibility.PUBLIC:
            return Author.objects.filter(followings__object=post.author)
        elif post.visibility == Post.Visibility.FRIENDS:
            # TODO test this
            return Author.objects.filter(Q(followings__object=post.author, followings__status=Follow.FollowStatus.ACCEPTED) & Q(followers__actor=post.author, followers__status=Follow.FollowStatus.ACCEPTED))
        elif post.visibility == Post.Visibility.PRIVATE:
            return []
        elif post.unlisted:
            return []

    @staticmethod
    def get_inbox_and_host_from_url(url):
        url_results = re.findall(r'(http[s]?:\/\/[^/]+.*)(author\/[^/]+\/)', url)
        if len(url_results) != 1:
            raise exceptions.APIException(f"cannot match the author endpoint from the url: {url}")
        host, author_path = url_results[0]
        # returns (host_url, inbox_url, author_url)
        return host + author_path + 'inbox/', host, host + author_path

    @silent_500
    def notify_like(self, like: Like, request: Request = None):
        inbox_url, host_url, author_url = self.get_inbox_and_host_from_url(like.object)

        if not self._same_host_and_save_to_inbox(request, host_url, inbox_item=like, inbox_author_url=author_url):
            self._find_node_and_post_to_inbox(inbox_url, host_url, LikeSerializer(like).data)

    @silent_500
    def notify_post(self, post: Post, request: Request = None, targets: List[Author] = None):
        # get all follwers and their endpoints
        target_users = targets or self.get_target_users_for_post(post)

        # post the post to each of the followers' inboxes
        for follower in target_users:
            inbox_url, host_url, _ = self.get_inbox_and_host_from_url(follower.url)
            if not self._same_host_and_save_to_inbox(request, host_url, inbox_item=post, inbox_author=follower):
                self._find_node_and_post_to_inbox(inbox_url, host_url, PostSerializer(post).data)

    @silent_500
    def notify_follow(self, follow: Follow, request=None):
        target_author = follow.object

        inbox_url, host_url, _ = self.get_inbox_and_host_from_url(target_author.url)
        if not self._same_host_and_save_to_inbox(request, host_url, inbox_item=follow, inbox_author=target_author):
            self._find_node_and_post_to_inbox(inbox_url, host_url, FollowSerializer(follow).data)

    @staticmethod
    def _same_host_and_save_to_inbox(request, host_url, inbox_author_url=None, inbox_item=None, inbox_author=None):
        """
        Check if the host_url is the same as the request's domain.
        If it is, save the inbox_item to the author's inbox and return True. Later step should skip further notifications.
        If it is not, do nothing and return False.

        If inbox_author_url is given, we grab that local author if needed. Use it as inbox_author instead.
        """
        domain = request.get_host() # points to the server root
        if domain in host_url:
            # find the local inbox author
            local_inbox_author = Author.objects.get(Q(url=inbox_author_url) | Q(url=inbox_author_url[:-1])) if inbox_author_url else None
            # wrap the item in an inboxObject, links with author
            item_as_inbox = InboxObject(content_object=inbox_item, author=inbox_author or local_inbox_author)
            item_as_inbox.save()
            return True
        else:
            return False

    @staticmethod
    @silent_500
    def _find_node_and_post_to_inbox(inbox_url, host_url, data):
        # find the node that matches the url
        node: Node = Node.objects.get(Q(host_url=host_url) | Q(host_url=host_url[:-1]))
        # post the data to the inbox on the node
        global_session.post(inbox_url, json=data, auth=node.get_basic_auth())


connector_service = ConnectorService()
