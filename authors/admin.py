from django.contrib import admin
from authors.models import Author, InboxObject, FriendRequest

admin.site.register(Author)
admin.site.register(InboxObject)
admin.site.register(FriendRequest)
