from django.db import models
from datetime import timedelta, datetime
from settings import TIEMPO_CIERRE_SESION
from webpush.models import SubscriptionInfo, PushInformation

from bd.models import Geolocation, GeolocationUser
from sga.funciones import ModeloBase

APP = (
    (1, u"SGA"),
    (2, u"SIE"),
)


class SubscriptionInfomation(ModeloBase):
    subscription = models.ForeignKey(SubscriptionInfo, related_name='+', on_delete=models.CASCADE)
    geolocation = models.ManyToManyField(GeolocationUser, related_name='+')
    app = models.IntegerField(choices=APP, default=1, verbose_name=u'app')
    ops = models.CharField(default='', max_length=50, blank=True, null=True, db_index=True, verbose_name=u"Sistema Operativo")
    screen_size = models.CharField(default='', max_length=50, blank=True, null=True, db_index=True, verbose_name=u"Tamaño de Pantalla")

    class Meta:
        ordering = ['-subscription']

    def get_display_app(self):
        return dict(APP)[self.app]

    def geolocations(self):
        return self.geolocation.all()


class PushInformation(PushInformation):
    objects = models.Manager()

    class Meta:
        proxy = True
        ordering = ['-subscription']

    def __init__(self, *args, **kwargs):
        super(PushInformation, self).__init__(*args, **kwargs)

    def information(self):
        try:
            eSubscriptionInfomation = SubscriptionInfomation.objects.filter(subscription=self.subscription)
            if eSubscriptionInfomation.values("id").exists():
                return eSubscriptionInfomation[0]
            return None
        except Exception as ex:
            return None

    def has_last_connection(self):
        try:
            if self.information():
                return self.information().fecha_modificacion is not None
            else:
                return False
        except Exception as ex:
            return False

    def last_connection(self):
        try:
            if self.has_last_connection():
                return self.information().fecha_modificacion
            return None
        except Exception as ex:
            return False

    def active_elapsed_time(self):
        try:
            if self.has_last_connection():
                return (self.information().fecha_modificacion + timedelta(seconds=TIEMPO_CIERRE_SESION)) > datetime.now()
        except Exception as ex:
            return  False

    def dispositivo_ios(self):
        return self.information().subscription.browser.lower() in 'ios' if self.information() else None

    def dispositivo_android(self):
        return self.information().subscription.browser.lower() in 'android' if self.information() else None

    def dispositivo_window(self):
        return self.subscription.browser.lower() in 'win' if self.information() else None

    def dispositivo_linux(self):
        return self.information().subscription.browser.lower() in 'lin' if self.information() else None

    def dispositivo_mac(self):
        return self.information().subscription.browser.lower() in 'mac' if self.information() else None

    def geolocation(self):
        try:
            from geopy.geocoders import Nominatim
            if self.information().geolocations().values("id").exists():
                eGeolocationUser = self.information().geolocations().order_by('-fecha_creacion')[0]
                geolocator = Nominatim(user_agent='unemi')
                location = geolocator.reverse(f"{eGeolocationUser.geolocation.latitude}, {eGeolocationUser.geolocation.longitude}")
                return f"{location.address}" if location else None
            return None
        except Exception as ex:
            return False
