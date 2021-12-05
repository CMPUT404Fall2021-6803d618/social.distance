import random
import requests
from rest_framework import exceptions
from nodes.models import Node

def random_profile_color():
    return random.choice(["#39BAE6", "#FFB454", "#59C2FF", "#AAD94C", "#95E6CB", "#F07178", "#FF8F40", "#E6B673", "#D2A6FF", "#F29668", "#7FD962", "#73B8FF", "#F26D78", "#6C5980"]
)

def try_get(request_url):
    # try without the auth
    # can either be a local author being followed or foreign server does not require auth
    response = requests.get(request_url)
    
    if response.status_code != 200:
        nodes = [x for x in Node.objects.all() if x.host_url in request_url]
        if len(nodes) != 1:
            raise exceptions.NotFound("cannot find the node from foreign author url")

        node = nodes[0]
        response = requests.get(request_url, auth=node.get_basic_auth_tuple())
    return response

def try_delete(request_url):
    # try without the auth
    # can either be a local author being followed or foreign server does not require auth
    response = requests.get(request_url)
    
    if response.status_code != 200:
        nodes = [x for x in Node.objects.all() if x.host_url in request_url]
        if len(nodes) != 1:
            raise exceptions.NotFound("cannot find the node from foreign author url")

        node = nodes[0]
        response = requests.delete(request_url, auth=node.get_basic_auth_tuple())
    return response