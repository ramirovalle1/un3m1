# -*- coding: UTF-8 -*-
from django.contrib.auth.models import User
from sga.funciones import ModeloBase
from django.db import models
from hashlib import md5


class UserAuth(ModeloBase):
    usuario = models.ForeignKey(User, null=True, blank=True, on_delete=models.CASCADE)
    username = models.CharField(default='', max_length=100, verbose_name=u'Usuario', db_index=True)
    password = models.CharField(default='', max_length=1000, verbose_name=u"Contraseña")
    first_name = models.CharField(default='', max_length=250, verbose_name=u"Nombres")
    last_name = models.CharField(default='', max_length=250, verbose_name=u"Apellidos")
    email = models.CharField(default='', max_length=200, verbose_name=u"Correo Institucional")

    def __str__(self):
        return u'%s - %s %s' % (self.username, self.first_name, self.last_name)

    class Meta:
        verbose_name = u"Moodle Usuario"
        verbose_name_plural = u"Moodle Usuarios"
        ordering = ['username']

    def set_data(self):
        from sga.models import Persona
        if self.usuario and Persona.objects.db_manager("sga_select").filter(usuario=self.usuario).exists():
            person = Persona.objects.values("nombres", "apellido1", "apellido2", "emailinst", "email").filter(usuario=self.usuario).first()
            self.username = self.usuario.username
            self.first_name = (u"%s %s" % (person.get("apellido1"), person.get("apellido2"))).strip()
            self.last_name = person.get("nombres")
            self.email = person.get("emailinst") if person.get("emailinst") else person.get("email")

    def check_data(self):
        from sga.models import Persona
        isUpdate = False
        person = Persona.objects.db_manager("sga_select").values("nombres", "apellido1", "apellido2", "emailinst").filter(usuario=self.usuario).first()
        first_name = person.get("nombres")
        last_name = (u"%s %s" % (person.get("apellido1"), person.get("apellido2"))).strip()
        email = person.get("emailinst")
        if not self.username == self.usuario.username:
            isUpdate = True
            self.username = self.usuario.username
        if not self.first_name == first_name:
            isUpdate = True
            self.first_name = first_name
        if not self.last_name == last_name:
            isUpdate = True
            self.last_name = last_name
        if not self.email == email:
            isUpdate = True
            self.email = email
        return isUpdate

    def set_password(self, pwd):
        self.password = md5(pwd.encode("utf-8")).hexdigest()

    def check_password(self, pwd):
        return self.password == md5(pwd.encode("utf-8")).hexdigest()

    def save(self, *args, **kwargs):
        super(UserAuth, self).save(*args, **kwargs)