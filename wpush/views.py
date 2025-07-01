import json
from datetime import datetime

from django.http import HttpResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST, require_GET
from django.views.generic import TemplateView

from bd.models import Geolocation, GeolocationUser
from wpush.models import SubscriptionInfomation
from wpush.forms import WebPushForm, SubscriptionInfoForm
from django.core.cache import cache


@require_POST
@csrf_exempt
def save_info(request):
    # Parse the  json object from post data. return 400 if the json encoding is wrong
    try:
        post_data = json.loads(request.body.decode('utf-8'))
    except ValueError:
        return HttpResponse(status=400)

    # Process the subscription data to mach with the model
    subscription_data = process_subscription_data(post_data)
    subscription_info_form = SubscriptionInfoForm(subscription_data)
    # pass the data through WebPushForm for validation purpose
    web_push_form = WebPushForm(post_data)

    # Check if subscriptioninfo and the web push info bot are valid
    if subscription_info_form.is_valid() and web_push_form.is_valid():
        # Get the cleaned data in order to get status_type and group_name
        web_push_data = web_push_form.cleaned_data
        status_type = web_push_data.pop("status_type")
        group_name = web_push_data.pop("group")

        if request.user.is_authenticated or group_name:
            subscription = subscription_info_form.get_or_save()
            subscriptionInfomationEnCache = cache.get(f"subscription_infomation_id_{subscription.id}")
            if subscriptionInfomationEnCache:
                eSubscriptionInfomation = subscriptionInfomationEnCache
            else:
                eSubscriptionInfomation = SubscriptionInfomation.objects.filter(subscription=subscription)
                if eSubscriptionInfomation.values("id").exists():
                    eSubscriptionInfomation = eSubscriptionInfomation[0]
                else:
                    eSubscriptionInfomation = None

            if eSubscriptionInfomation is None:
                eSubscriptionInfomation = SubscriptionInfomation(subscription=subscription,
                                                                 app=1,
                                                                 screen_size=post_data['screen_size'],
                                                                 ops=post_data['os'])
                eSubscriptionInfomation.save(request)
                cache.set(f"subscription_infomation_id_{subscription.id}", eSubscriptionInfomation, 60 * 60 * 12)
            else:
                # NO COMENTAR PORQUE SE NECESITA GUARDAR EN LA BASE DE DATOS
                # eSubscriptionInfomation_ = SubscriptionInfomation.objects.filter(subscription=subscription)
                # if not eSubscriptionInfomation_.values("id").exists():
                #     eSubscriptionInfomation_ = eSubscriptionInfomation
                #     eSubscriptionInfomation_.save(request)
                # else:
                # eSubscriptionInfomation.subscription = subscription
                eSubscriptionInfomation.screen_size = post_data['screen_size']
                eSubscriptionInfomation.ops = post_data['os']
                eSubscriptionInfomation.save(request)
                if subscriptionInfomationEnCache:
                    cache.delete(f"subscription_infomation_id_{subscription.id}")
                cache.set(f"subscription_infomation_id_{subscription.id}", eSubscriptionInfomation, 60 * 60 * 12)

            if 'geolocation' in post_data and post_data['geolocation']:
                geolocationEnCache = cache.get(f"geolocation_{post_data['geolocation']['longitude']}_{post_data['geolocation']['latitude']}")
                if geolocationEnCache:
                    eGeolocation = geolocationEnCache
                else:
                    eGeolocation = Geolocation.objects.filter(longitude=post_data['geolocation']['longitude'], latitude=post_data['geolocation']['latitude'])
                    if not eGeolocation.values("id").exists():
                        eGeolocation = Geolocation(accuracy=post_data['geolocation']['accuracy'],
                                                   altitude=post_data['geolocation']['altitude'],
                                                   altitudeAccuracy=post_data['geolocation']['altitudeAccuracy'],
                                                   heading=post_data['geolocation']['heading'],
                                                   latitude=post_data['geolocation']['latitude'],
                                                   longitude=post_data['geolocation']['longitude'],
                                                   speed=post_data['geolocation']['speed'],
                                                   )
                        eGeolocation.save(request)
                    else:
                        eGeolocation = eGeolocation[0]
                    cache.set(f"geolocation_{eGeolocation.longitude}_{eGeolocation.latitude}", eGeolocation, 60 * 60 * 12)

                geolocationUserEnCache = cache.get(f"geolocation_id_{eGeolocation.id}_user_id{request.user.id}")
                if geolocationUserEnCache:
                    eGeolocationUser = geolocationUserEnCache
                else:
                    eGeolocationUser = GeolocationUser.objects.filter(user=request.user, geolocation=eGeolocation)
                    if not eGeolocationUser.values("id").exists():
                        eGeolocationUser = GeolocationUser(user=request.user,
                                                           geolocation=eGeolocation)
                        eGeolocationUser.save(request)
                    else:
                        eGeolocationUser = eGeolocationUser[0]
                    cache.get(f"geolocation_id_{eGeolocation.id}_user_id{request.user.id}", eGeolocationUser, 60 * 60 * 12)
                if not eGeolocationUser.id in eSubscriptionInfomation.geolocations().values("id").distinct():
                    eSubscriptionInfomation.geolocation.add(eGeolocationUser.id)
                    eSubscriptionInfomation.save(request)

            web_push_form.save_or_delete(
                subscription=subscription, user=request.user,
                status_type=status_type, group_name=group_name)

            # If subscribe is made, means object is created. So return 201
            if status_type == 'subscribe':
                return HttpResponse(status=201)
            # Unsubscribe is made, means object is deleted. So return 202
            elif "unsubscribe":
                return HttpResponse(status=202)

    return HttpResponse(status=400)


def process_subscription_data(post_data):
    """Process the subscription data according to out model"""
    subscription_data = post_data.pop("subscription", {})
    # As our database saves the auth and p256dh key in separate field,
    # we need to refactor it and insert the auth and p256dh keys in the same dictionary
    keys = subscription_data.pop("keys", {})
    subscription_data.update(keys)
    # Insert the browser name
    subscription_data["browser"] = post_data.pop("browser")
    return subscription_data


class ServiceWorkerView(TemplateView):
    """
    Service Worker need to be loaded from same domain.
    Therefore, use TemplateView in order to server the webpush_serviceworker.js
    """

    # template_name = 'webpush_serviceworker.js'
    template_name = 'serviceworker.js'
    content_type = 'application/javascript'
