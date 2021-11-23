from django.urls import path

from .views import *

urlpatterns = [
    path('', NodesList.as_view(), name="nodes-list"),
    path('<str:node_id>/', NodeDetail.as_view(), name="node-detail"),
]
