from django.db import models
from django.contrib.auth.models import User

import requests
from requests.models import HTTPBasicAuth, Response
from requests import Request

global_session = requests.Session()

class ConnectionMixin:
    session = global_session
    host_url = None
    username = None
    password = None

    def get_basic_auth(self):
        return HTTPBasicAuth(self.username, self.password) 
    
    
# Create your models here.
class Node(ConnectionMixin, models.Model):
    host_url = models.URLField()
    # username and password that they use, as a client, to be authenticated in our server
    user = models.OneToOneField(User, on_delete=models.CASCADE, null=True) # one2one with django user

    # username and password that WE use, as a client, to authenticate on this node/server
    username = models.CharField(max_length=200) 
    password = models.CharField(max_length=200) 


class ConnectorService:
    def _do_all(self, path, payload=None, method='GET'):
        responses = []
        for node in Node.objects.all():
            try:
                call = getattr(global_session, method.lower())
                res: Response = call(node.host_url + path, json=payload, auth=node.get_basic_auth())
                responses.append(res.text) 
            except:
                responses.append(res.status_code) 
        return responses
        
    def get_all(self, path: str, payload: dict = None):
        return self._do_all(path, payload)

    def post_all(self, path, payload):
        return self._do_all(path, payload, method='POST')

connector_service = ConnectorService()