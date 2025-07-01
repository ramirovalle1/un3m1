from wpush.models import PushInformation, SubscriptionInfomation


def action_depurar_dispositivos_activos(user, app=None, data=None):
    pushes = PushInformation.objects.filter(user=user).order_by('-pk')
    if app is not None:
        subscriptions = SubscriptionInfomation.objects.filter(pk__in=pushes.values('subscription_id'), app=app)
        pushes = pushes.filter(subscription__in=subscriptions)
    for push in pushes:
        if not push.active_elapsed_time():
            push.delete()


