from django.contrib.auth import authenticate
from rest_framework.decorators import api_view
from rest_framework.response import Response
from rest_framework.reverse import reverse
from rest_framework import status
from drf_spectacular.utils import extend_schema
from rest_framework_simplejwt.authentication import JWTAuthentication
from rest_framework_simplejwt.serializers import TokenRefreshSerializer

from django.contrib.auth.backends import AllowAllUsersModelBackend

from social_distance.models import DynamicSettings

from .serializers import CommonAuthenticateSerializer, RegisterSerializer


@api_view(['GET'])
def api_root(request, format=None):
    return Response({
        'authors': reverse('author-list', request=request, format=format),
        'author': reverse('author-root', request=request, format=format),
    })


# TODO: login, logout, register. bind User and Author
@extend_schema(
    request=RegisterSerializer,
    responses=CommonAuthenticateSerializer
)
@api_view(['POST'])
def register(request):
    """
    ## Description:  
    Registering a new account  
    ## Responses:  
    **200**: if the account is successfully registered <br>  
    **400**: if the payload failed the serializer check
    """
    # deserialize request data
    serializer = RegisterSerializer(
        data=request.data, context={'request': request})
    if serializer.is_valid():
        # create user and author
        user = serializer.save()
        try:
            # if needs approval mode is turned on, set user to inactive on register
            # will need manual approval later by setting u.is_active = True
            dyn_settings = DynamicSettings.load()
            if dyn_settings.register_needs_approval:
                user.is_active = False
                user.save()
        except DynamicSettings.DoesNotExist:
            pass
        return Response(CommonAuthenticateSerializer(user).data)
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

@extend_schema(
    request=TokenRefreshSerializer,
    responses=CommonAuthenticateSerializer
)
@api_view(['POST'])
def token_refresh(request):
    """
    ## Description:  
    grab the refresh token, try authenticate and get user  
    ## Responses:  
    **200**: for successful POST request, returns useful user data, and access_token <br>
    **400**: if the payload does not contain the refresh token
    """
    if not request.data.get('refresh'):
        return Response(status=status.HTTP_400_BAD_REQUEST)

    auth = JWTAuthentication()
    validated_token = auth.get_validated_token(request.data['refresh'])
    user            = auth.get_user(validated_token)
    return Response(CommonAuthenticateSerializer(user).data)

@extend_schema(
    request=CommonAuthenticateSerializer,
    responses=CommonAuthenticateSerializer
)
@api_view(['POST'])
def login(request):
    """
    ## Description:  
    login with username and password  
    ## Responses:  
    **200**: for successful POST request, returns user data <br>
    **400**: if the payload failed the serializer check <br>
    **401**: if the user cannot be authenticated <br>
    **403**: if the user is not currently active
    """
    serializer = CommonAuthenticateSerializer(data=request.data)
    if serializer.is_valid():
        data = serializer.validated_data
        username = data.get('username')
        password = data.get('password')

        # auth backend with custom rule so that we can verify inactive users
        # but still forbid them from logging in.
        auth_backend = AllowAllUsersModelBackend()
        user = auth_backend.authenticate(request=request, username=username, password=password)
        if not user:
            return Response(status=status.HTTP_401_UNAUTHORIZED)
        if not user.is_active:
            return Response("please wait for the admin to approve and activate your account", status=status.HTTP_403_FORBIDDEN)
        return Response(CommonAuthenticateSerializer(user).data)
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
