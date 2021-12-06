from django.urls import path

from authors.views import ForeignAuthorList

from .views import *

urlpatterns = [
    path('', NodesList.as_view(), name="nodes-list"),
    path('<str:node_id>/', NodeDetail.as_view(), name="node-detail"),
    path('<str:node_id>/authors/', ForeignAuthorList.as_view(), name="foreign-author-list"),
]
