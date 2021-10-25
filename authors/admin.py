from django.contrib import admin
from authors.models import Author, Follow, InboxObject

class AuthorAdmin(admin.ModelAdmin):
    pass

admin.site.register(Author, AuthorAdmin)
admin.site.register(Follow)
admin.site.register(InboxObject)