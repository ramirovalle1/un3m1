import json
from datetime import datetime

from api.helpers.response_herlper import Helper_Response
from bd.models import Geolocation, GeolocationUser
from sga.models import PerfilUsuario
from sga.templatetags.sga_extras import encrypt
from wpush.models import SubscriptionInfomation
from wpush.forms import WebPushForm, SubscriptionInfoForm
from rest_framework.permissions import IsAuthenticated
from rest_framework.views import APIView
from rest_framework import status
from django.core.cache import cache

from wpush.views import process_subscription_data


class saveInfoNotificationAPIView(APIView):
    permission_classes = (IsAuthenticated,)

    def post(self, request):
        try:
            hoy = datetime.now()
            payload = request.auth.payload
            # ePerfilUsuario = PerfilUsuario.objects.get(pk=encrypt(payload['perfilprincipal']['id']))
            # if not ePerfilUsuario.es_estudiante():
            #     raise NameError(u'Solo los perfiles de estudiantes pueden ingresar al modulo.')
            # try:
            #     post_data = request.data
            # except ValueError:
            #     return Helper_Response(status=status.HTTP_400_BAD_REQUEST)
            #
            # subscription_data = process_subscription_data(post_data)
            # subscription_info_form = SubscriptionInfoForm(subscription_data)
            # web_push_form = WebPushForm(post_data)
            # if subscription_info_form.is_valid() and web_push_form.is_valid():
            #     web_push_data = web_push_form.cleaned_data
            #     status_type = web_push_data.pop("status_type")
            #     group_name = web_push_data.pop("group")
            #
            #     if request.user.is_authenticated or group_name:
            #         subscription = subscription_info_form.get_or_save()
            #         subscriptionInfomationEnCache = cache.get(f"subscription_infomation_id_{subscription.id}")
            #         if subscriptionInfomationEnCache:
            #             eSubscriptionInfomation = subscriptionInfomationEnCache
            #         else:
            #             eSubscriptionInfomation = SubscriptionInfomation.objects.filter(subscription=subscription)
            #             if eSubscriptionInfomation.values("id").exists():
            #                 eSubscriptionInfomation = eSubscriptionInfomation[0]
            #             else:
            #                 eSubscriptionInfomation = None
            #
            #         if eSubscriptionInfomation is None:
            #             eSubscriptionInfomation = SubscriptionInfomation(subscription=subscription,
            #                                                              app=2,
            #                                                              screen_size=post_data['screen_size'],
            #                                                              ops=post_data['os'])
            #             eSubscriptionInfomation.save(request)
            #             cache.set(f"subscription_infomation_id_{subscription.id}", eSubscriptionInfomation, 60 * 60 * 12)
            #         else:
            #             eSubscriptionInfomation.screen_size = post_data['screen_size']
            #             eSubscriptionInfomation.ops = post_data['os']
            #             eSubscriptionInfomation.save(request)
            #             if subscriptionInfomationEnCache:
            #                 cache.delete(f"subscription_infomation_id_{subscription.id}")
            #             cache.set(f"subscription_infomation_id_{subscription.id}", eSubscriptionInfomation, 60 * 60 * 12)
            #
            #         # if 'geolocation' in post_data and post_data['geolocation']:
            #         #     geolocationEnCache = cache.get(
            #         #         f"geolocation_{post_data['geolocation']['longitude']}_{post_data['geolocation']['latitude']}")
            #         #     if geolocationEnCache:
            #         #         eGeolocation = geolocationEnCache
            #         #     else:
            #         #         eGeolocation = Geolocation.objects.filter(longitude=post_data['geolocation']['longitude'],
            #         #                                                   latitude=post_data['geolocation']['latitude'])
            #         #         if not eGeolocation.values("id").exists():
            #         #             eGeolocation = Geolocation(accuracy=post_data['geolocation']['accuracy'],
            #         #                                        altitude=post_data['geolocation']['altitude'],
            #         #                                        altitudeAccuracy=post_data['geolocation'][
            #         #                                            'altitudeAccuracy'],
            #         #                                        heading=post_data['geolocation']['heading'],
            #         #                                        latitude=post_data['geolocation']['latitude'],
            #         #                                        longitude=post_data['geolocation']['longitude'],
            #         #                                        speed=post_data['geolocation']['speed'],
            #         #                                        )
            #         #             eGeolocation.save(request)
            #         #         else:
            #         #             eGeolocation = eGeolocation[0]
            #         #         cache.set(f"geolocation_{eGeolocation.longitude}_{eGeolocation.latitude}", eGeolocation, 60 * 60 * 12)
            #         #
            #         #     geolocationUserEnCache = cache.get(f"geolocation_id_{eGeolocation.id}_user_id{request.user.id}")
            #         #     if geolocationUserEnCache:
            #         #         eGeolocationUser = geolocationUserEnCache
            #         #     else:
            #         #         eGeolocationUser = GeolocationUser.objects.filter(user=request.user,
            #         #                                                           geolocation=eGeolocation)
            #         #         if not eGeolocationUser.values("id").exists():
            #         #             eGeolocationUser = GeolocationUser(user=request.user,
            #         #                                                geolocation=eGeolocation)
            #         #             eGeolocationUser.save(request)
            #         #         else:
            #         #             eGeolocationUser = eGeolocationUser[0]
            #         #         cache.get(f"geolocation_id_{eGeolocation.id}_user_id{request.user.id}", eGeolocationUser, 60 * 60 * 12)
            #         #     if not eGeolocationUser.id in eSubscriptionInfomation.geolocations().values("id").distinct():
            #         #         eSubscriptionInfomation.geolocation.add(eGeolocationUser.id)
            #         #         eSubscriptionInfomation.save(request)
            #
            #         # web_push_form.save_or_delete(
            #         #     subscription=subscription, user=request.user,
            #         #     status_type=status_type, group_name=group_name)
            #         #
            #         # if status_type == 'subscribe':
            #         #     return Helper_Response(isSuccess=True, status=status.HTTP_201_CREATED)
            #         # elif "unsubscribe":
            #         #     return Helper_Response(isSuccess=True, status=status.HTTP_200_OK)

            # return Helper_Response(isSuccess=True, status=status.HTTP_400_BAD_REQUEST)
            return Helper_Response(isSuccess=True, status=status.HTTP_201_CREATED)
        except Exception as ex:
            return Helper_Response(status=status.HTTP_400_BAD_REQUEST)

