from django.urls import path

from .views import ForeignAuthorList

urlpatterns = [
    path('<int:node_id>/', ForeignAuthorList.as_view(), name="foreign-author-list"),
]
