import json
from django.contrib.auth.models import User, Group
from django.http import HttpResponse
from django.shortcuts import render

# Create your views here.
from oauth2_provider.decorators import protected_resource
from oauth2_provider.contrib.rest_framework import TokenHasReadWriteScope, TokenHasScope
from rest_framework import generics, permissions
from sga.models import Persona

from api.serializers.user import UserSerializer, GroupSerializer


class UserList(generics.ListCreateAPIView):
    permission_classes = [permissions.IsAuthenticated, TokenHasReadWriteScope]
    queryset = User.objects.all()
    serializer_class = UserSerializer


class UserDetails(generics.RetrieveAPIView):
    permission_classes = [permissions.IsAuthenticated, TokenHasReadWriteScope]
    queryset = User.objects.all()
    serializer_class = UserSerializer


class GroupList(generics.ListAPIView):
    permission_classes = [permissions.IsAuthenticated, TokenHasScope]
    required_scopes = ['groups']
    queryset = Group.objects.all()
    serializer_class = GroupSerializer


@protected_resource(scopes=['read'])
def profile(request):
    email = ''
    first_name = ''
    last_name = ''
    if Persona.objects.filter(usuario_id=request.resource_owner.id).exists():
        persona = Persona.objects.filter(usuario_id=request.resource_owner.id).first()
        email = persona.emailinst if persona.emailinst else persona.email if persona.email else ''
        # email = 'taylorluis93@gmail.com'
        first_name = persona.nombres
        last_name = (u"%s %s" % (persona.apellido1, persona.apellido2)).strip()
    return HttpResponse(json.dumps({
        "id": request.resource_owner.id,
        "username": request.resource_owner.username,
        "email": email,
        "first_name": first_name,
        "last_name": last_name
    }), content_type="application/json")
