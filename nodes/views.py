
import base64
from social_distance.pagination import PageSizePagination
import requests
from itertools import chain

from django.http.response import FileResponse, HttpResponse
from django.shortcuts import get_object_or_404, render
from django.contrib.contenttypes.models import ContentType
from rest_framework.decorators import api_view, authentication_classes, permission_classes
from drf_spectacular.types import OpenApiTypes

from rest_framework.views import APIView
from rest_framework.generics import ListAPIView, ListCreateAPIView, RetrieveUpdateDestroyAPIView, RetrieveAPIView
from rest_framework.response import Response
from rest_framework import serializers, status, permissions, exceptions
from drf_spectacular.utils import OpenApiExample, extend_schema

from authors.models import Author, InboxObject
from authors.serializers import AuthorSerializer

from .models import Node, connector_service
import uuid
import copy

# serialzier and pagination, too short to put in another file for now.
class NodesPagination(PageSizePagination):
    key = 'nodes'
    type = 'nodes'

class NodeSerializer(serializers.ModelSerializer):
    class Meta:
        model = Node
        fields = ['name', 'host_url', 'id']


# views
class NodesList(ListAPIView):
    serializer_class = NodeSerializer
    pagination_class = NodesPagination
    def get_queryset(self):
        return Node.objects.all()


class NodeDetail(RetrieveAPIView):
    serializer_class = NodeSerializer
    def retrieve(self, request, node_id: str):
        return Response(NodeSerializer(get_object_or_404(Node, pk=node_id)).data)
