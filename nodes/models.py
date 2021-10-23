import functools
import re
from django.db import models
from django.contrib.auth.models import User
from django.db.models.query_utils import Q

import requests
from requests.models import HTTPBasicAuth, Response
from requests import Request
from rest_framework import exceptions

from posts.models import Like
from posts.serializers import LikeSerializer

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
    @functools.warps(fn)
    def wrapper(*args, **kwargs):
        try:
            return fn(*args, **kwargs)
        except requests.exceptions.RequestException as e:
            print("node connector error: ", e)
    return wrapper

class ConnectorService:
    @staticmethod
    def get_inbox_and_host_from_url(url):
        inbox_url = re.findall(r'(http[s]?:\/\/[^/]+\/)(author\/[^/]+\/)', url)
        if len(inbox_url) != 1:
            raise exceptions.APIException(f"cannot match the author endpoint from the url: {url}")
        host, author_path = inbox_url[0]
        return host + author_path + 'inbox/', host

    def notify_like(self, like: Like):
        inbox_url, host_url = self.get_inbox_and_host_from_url(like.object)
        node: Node = Node.objects.get(Q(host_url=host_url) | Q(host_url=host_url[:-1]))
        res = global_session.post(inbox_url, json=LikeSerializer(like).data, auth=node.get_basic_auth())
        return res.content
        
connector_service = ConnectorService()