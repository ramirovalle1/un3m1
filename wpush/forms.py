from datetime import datetime

from django import forms

from webpush.models import Group, PushInformation, SubscriptionInfo
from wpush.models import SubscriptionInfomation, APP


class WebPushForm(forms.Form):
    group = forms.CharField(max_length=255, required=False)
    status_type = forms.ChoiceField(choices=[
                                      ('subscribe', 'subscribe'),
                                      ('unsubscribe', 'unsubscribe')
                                    ])

    def save_or_delete(self, subscription, user, status_type, group_name):
        # Ensure get_or_create matches exactly
        data = {"user": None, "group": None}

        if user.is_authenticated:
            data["user"] = user

        if group_name:
            group, created = Group.objects.get_or_create(name=group_name)
            data["group"] = group

        data["subscription"] = subscription

        push_info, created = PushInformation.objects.get_or_create(**data)

        # If unsubscribe is called, that means need to delete the browser
        # and notification info from server.
        if status_type == "unsubscribe":
            push_info.delete()
            subscription.delete()


class SubscriptionInfoForm(forms.ModelForm):

    class Meta:
        model = SubscriptionInfo
        fields = ('endpoint', 'auth', 'p256dh', 'browser')

    def get_or_save(self):
        eSubscriptionInfo = SubscriptionInfo.objects.filter(**self.cleaned_data)
        if eSubscriptionInfo.count() > 1:
            # first = eSubscriptionInfo.first()
            last = eSubscriptionInfo.last()
            eSubscriptionInfo.exclude(pk=last.pk).delete()
            subscription = last
        else:
            subscription, created = SubscriptionInfo.objects.get_or_create(**self.cleaned_data)
        return subscription
