# -*- coding: UTF-8 -*-
import sys
from django.db import models
from sga.funciones import ModeloBase


def mobile_list_classes():
    listclass = []
    current_module = sys.modules[__name__]
    for key in dir(current_module):
        if isinstance(getattr(current_module, key), type):
            try:
                a = eval(key + '.objects')
                listclass.append(key)
            except:
                pass
    return listclass



MOBILE_DEVICES = (
    (1, u"Android"),
    (2, u"iOS"),
    (3, u"BlackBerry")
)



class UserAuthMobile(ModeloBase):
    from django.contrib.auth.models import User
    user = models.ForeignKey(User, verbose_name=u'Usuario',on_delete=models.CASCADE)
    authstr = models.CharField(max_length=32, default='', verbose_name=u'Atenticacion')
    device = models.IntegerField(choices=MOBILE_DEVICES, default=1, verbose_name=u'Tipo de dispositivo')
    when = models.DateTimeField(verbose_name=u'Cuando')
    lastaccess = models.DateTimeField(verbose_name=u'Ultimo acceso')
    padre = models.BooleanField(default=False, verbose_name=u'Padre')

    def __str__(self):
        return "%s %s" % (self.user.username, MOBILE_DEVICES[self.device - 1][1])

    class Meta:
        verbose_name = u"User auth mobile"
        verbose_name_plural = u"Users auth mobile"
        unique_together = ('authstr',)


class VersionHorarios(ModeloBase):
    version = models.IntegerField(default=1, verbose_name=u'Version del horario')


class AreaAutorizada(ModeloBase):
    nombre = models.CharField(max_length=100, default='', verbose_name=u'Nombre')
    p1_x = models.FloatField(default=0, verbose_name="Punto 1 x")
    p1_y = models.FloatField(default=0, verbose_name="Punto 1 y")
    p2_x = models.FloatField(default=0, verbose_name="Punto 2 x")
    p2_y = models.FloatField(default=0, verbose_name="Punto 2 y")

    def __str__(self):
        return "%s" % self.nombre

    class Meta:
        verbose_name = u"Area autorizada"
        verbose_name_plural = u"Areas autorizadas"
        unique_together = ('nombre',)

    def save(self, *args, **kwargs):
        self.nombre = self.nombre.upper().strip()
        super(AreaAutorizada, self).save(*args, **kwargs)


def versionhorarios():
    if VersionHorarios.objects.exists():
        return VersionHorarios.objects.all()[0]
    else:
        version = VersionHorarios()
        version.save()
        return version
