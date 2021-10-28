from django.contrib import admin
from authors.models import Author, Follow, InboxObject

class AuthorAdmin(admin.ModelAdmin):
    
    # actions available on chosen Author objects
    actions = ['activate_user_if_exists', 'deactivate_user_if_exists']

    @admin.action(description='activate user if not already')
    def activate_user_if_exists(self, request, queryset):
        for author in queryset:
            if author.user:
                author.user.is_active = True
                author.user.save()


    @admin.action(description='deactivate user if not already')
    def deactivate_user_if_exists(self, request, queryset):
        for author in queryset:
            if author.user:
                author.user.is_active = False
                author.user.save()

admin.site.register(Author, AuthorAdmin)
admin.site.register(Follow)
admin.site.register(InboxObject)
