from django.contrib import admin
from authors.models import Author, Follow, InboxObject

admin.site.register(Author)
admin.site.register(Follow)
admin.site.register(InboxObject)
