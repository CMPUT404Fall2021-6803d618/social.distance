"""social_distance URL Configuration

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/3.2/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.urls import path, include
from rest_framework_simplejwt.views import TokenRefreshView

from drf_spectacular.views import SpectacularAPIView, SpectacularSwaggerView
from authors.views import proxy

from posts.views import get_all_posts

from .views import register, login, token_refresh

urlpatterns = [
    path('admin/', admin.site.urls),
    path('api-auth/', include('rest_framework.urls')),

    # auth
    path('register/', register),  # includes author info
    path('login/', login),  # includes author info
    path('token-refresh/', token_refresh, name='token_refresh'),

    # authors app
    path('authors/', include('authors.urls_authors')),
    path('author/', include('authors.urls_author')),
    path('proxy/<path:object_url>/', proxy, name='social-proxy'),

    path('posts/', get_all_posts, name='all-posts'),

    # other stuff
    path('nodes/', include('nodes.urls')),

    # root
    path('schema/', SpectacularAPIView.as_view(), name='open-schema'),
    path('', SpectacularSwaggerView.as_view(
        url_name='open-schema'), name='api-root'),
]
