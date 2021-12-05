
from nodes.models import Node
import requests
from rest_framework import exceptions

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