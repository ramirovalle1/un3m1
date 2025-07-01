#!/usr/bin/env python
# -*- coding: latin-1 -*-
# from settings import DEBUG
import os
import json
import unicodedata
import requests
from datetime import datetime

from settings import DEBUG
from sga.funciones import convertirfecha
from soap.consumer.dinardap import clientSoap
from requests.auth import HTTPBasicAuth


class Titulos(object):
    _dataJson = {}
    _identificacion = ''
    _ePersona = None
    _response = None
    _dataResponse = []

    def __init__(self, identificacion):
        from settings import SITE_ROOT
        dataJson = {}
        with open(os.path.join(SITE_ROOT, 'soap', 'consumer', 'auth_dinardap.json')) as fileJson:
            dataJson = json.load(fileJson)
        self._dataJson = dataJson
        self._identificacion = identificacion

    def _get_variable(self, e):
        from settings import DEBUG
        value = None
        dataJson = self._dataJson
        if DEBUG:
            dev = None
            if 'dev' in dataJson:
                dev = dataJson['dev']
                for key in dev:
                    if e == key:
                        value = dev[key]
        else:
            for key in dataJson:
                if e == key:
                    value = dataJson[key]
        return value

    def consultar(self):
        from django.core.exceptions import ObjectDoesNotExist
        from django.db.models import Q
        from django.db import transaction
        from sga.models import Persona, Titulacion, PersonaTituloUniversidad
        from bd.models import HistorialPersonaConsultaTitulo
        ePersonas = Persona.objects.filter(Q(cedula=self._identificacion) | Q(pasaporte=self._identificacion))
        if not ePersonas.values("id").exists():
            return []
        self._ePersona = ePersonas.first()
        totalConsultaDia = HistorialPersonaConsultaTitulo.objects.values("id").filter(fecha=datetime.now().date()).count()
        if totalConsultaDia > 9900:
            return []
        isContinue = True
        if DEBUG is False:
            eHistorialPersonaConsultaTitulos = HistorialPersonaConsultaTitulo.objects.filter(persona=self._ePersona, servicio=HistorialPersonaConsultaTitulo.Servicios.SENESCYT).order_by('-fecha')
            if eHistorialPersonaConsultaTitulos.values("id").exists():
                eHistorialPersonaConsultaTitulo = eHistorialPersonaConsultaTitulos.first()
                diferencia = datetime.now().date() - eHistorialPersonaConsultaTitulo.fecha
                if diferencia.days <= 30:
                    isContinue = False
        if isContinue:
            url = f"{self._get_variable('SITE_URL_SCI')}/api/dinardap/senescyt"
            auth = HTTPBasicAuth(self._get_variable('AUTH_USERNAME'), self._get_variable('AUTH_PASSWORD'))
            headers = {"Content-Type": "application/json; charset=utf-8"}

            params = {
                "identificacion": self._identificacion,
            }
            response = requests.post(url, headers=headers, json=params, auth=auth)
            status = response.status_code
            if status == 200:
                response = response.json()
                if not response['isSuccess']:
                    raise NameError(f"{response['message']}")
                self._response = response
                with transaction.atomic():
                    try:
                        self._procesar()
                        data = response['data'].get('senescyt', [])
                        eHistorialPersonaConsultaTitulo = HistorialPersonaConsultaTitulo(persona=self._ePersona,
                                                                                         fecha=datetime.now().date(),
                                                                                         servicio=HistorialPersonaConsultaTitulo.Servicios.SENESCYT,
                                                                                         obtuvo=True if len(data) else False)
                        eHistorialPersonaConsultaTitulo.save()
                    except Exception as ex:
                        transaction.set_rollback(True)
        eTitulaciones = Titulacion.objects.filter(persona=self._ePersona).values_list('persona_id', 'titulo__nombre', 'institucion__nombre', 'registro')
        ePersonaTituloUniversidades = PersonaTituloUniversidad.objects.filter(persona=self._ePersona).values_list('persona_id', 'nombrecarrera', 'universidad__nombre', 'codigoregistro')
        return list(ePersonaTituloUniversidades) + list(eTitulaciones)

    def _procesar(self):
        response = self._response
        data = response['data'].get('senescyt', [])
        self._dataResponse = data
        for registro in data:
            self._titulacion(registro)

    def _niveltitulacion(self, nombre):
        from sga.models import NivelTitulacion
        if nombre is None:
            return None
        if nombre in ['TECNICO_SUPERIOR', 'Técnico Superior', 'Tercer Nivel Técnico Superior']:
            return NivelTitulacion.objects.get(pk=2)
        if nombre in ['TERCER_NIVEL', 'Tercer Nivel o Pregrado', 'Tercer Nivel', 'Pregrado']:
            return NivelTitulacion.objects.get(pk=3)
        if nombre in ['CUARTO_NIVEL', 'Cuarto Nivel o Posgrado', 'Cuarto Nivel', 'Posgrado']:
            return NivelTitulacion.objects.get(pk=4)
        eNivelTitulaciones = NivelTitulacion.objects.filter(nombre__icontains=nombre, nivel__in=[3, 4, 5])
        if not eNivelTitulaciones.values("id").exists():
            return None
        return eNivelTitulaciones.first()

    def _areatitulo(self, area, areaCodigo):
        from sga.models import AreaTituloSenescyt
        if not area is None:
            eAreaTituloSenescyts = AreaTituloSenescyt.objects.filter(nombre=area)
            if not eAreaTituloSenescyts.values("id").exists():
                eAreaTituloSenescyt = AreaTituloSenescyt(nombre=area,
                                                         codigo=areaCodigo)
                eAreaTituloSenescyt.save()
            else:
                eAreaTituloSenescyt = eAreaTituloSenescyts.first()
            return eAreaTituloSenescyt
        return None

    def _subareatitulo(self, subarea, subareaCodigo):
        from sga.models import SubareaTituloSenescyt
        if not subarea is None:
            eSubareaTituloSenescyts = SubareaTituloSenescyt.objects.filter(nombre=subarea)
            if not eSubareaTituloSenescyts.values("id").exists():
                eSubareaTituloSenescyt = SubareaTituloSenescyt(nombre=subarea,
                                                               codigo=subareaCodigo)
                eSubareaTituloSenescyt.save()
            else:
                eSubareaTituloSenescyt = eSubareaTituloSenescyts.first()
            return eSubareaTituloSenescyt
        return None

    def _ies(self, ies):
        from sga.models import InstitucionEducacionSuperior
        if not ies is None:
            eInstitucionEducacionSuperiores = InstitucionEducacionSuperior.objects.filter(nombre__contains=ies)
            if not eInstitucionEducacionSuperiores.values("id").exists():
                eInstitucionEducacionSuperior = InstitucionEducacionSuperior(nombre=ies)
                eInstitucionEducacionSuperior.save()
            else:
                eInstitucionEducacionSuperior = eInstitucionEducacionSuperiores.first()
            return eInstitucionEducacionSuperior
        return None

    def _titulo(self, nivel, nombreTitulo):
        from sga.models import Titulo
        eNivelTitulacion = self._niveltitulacion(nivel)
        eTitulo = None
        if not nombreTitulo is None:
            eTitulos = Titulo.objects.filter(nombre=nombreTitulo)
            if not eTitulos.values("id").exists():
                eTitulo = Titulo(nombre=nombreTitulo,
                                 nivel=eNivelTitulacion,
                                 senescyt=True)
                eTitulo.save(usuario_id=self._ePersona.usuario_id)
            else:
                eTitulo = eTitulos.first()
                if not eTitulo.senescyt:
                    eTitulo.nivel = eNivelTitulacion
                    eTitulo.senescyt = True
                    eTitulo.save(usuario_id=self._ePersona.usuario_id)
        return eTitulo

    def _titulacion(self, registro):
        from django.db.models import Q
        from sga.models import Titulacion, PersonaTituloUniversidad
        area = registro.get('area', None)
        areaCodigo = registro.get('areaCodigo', None)
        eAreaTituloSenescyt = self._areatitulo(area, areaCodigo)
        subarea = registro.get('subarea', None)
        subareaCodigo = registro.get('subareaCodigo', None)
        eSubareaTituloSenescyt = self._subareatitulo(subarea, subareaCodigo)
        ies = registro.get('ies', None)
        ies = self._ies(ies)
        nivel = registro.get('nivel', None)
        nombreTitulo = registro.get('nombreTitulo', None)
        fechaGrado = registro.get('fechaGrado', None)
        fechaRegistro = registro.get('fechaRegistro', None)
        numeroRegistro = registro.get('numeroRegistro', None)
        tiponivel = 0
        if nivel is None:
            tiponivel = 0
        if nivel in ['TECNICO_SUPERIOR', 'Técnico Superior', 'Tercer Nivel Técnico Superior']:
            tiponivel = 2
        if nivel in ['TERCER_NIVEL', 'Tercer Nivel o Pregrado', 'Tercer Nivel', 'Pregrado']:
            tiponivel = 4
        if nivel in ['CUARTO_NIVEL', 'Cuarto Nivel o Posgrado', 'Cuarto Nivel', 'Posgrado']:
            tiponivel = 5
        ePersonaTituloUniversidades = PersonaTituloUniversidad.objects.filter(Q(nombrecarrera=nombreTitulo) | Q(codigoregistro=numeroRegistro), persona=self._ePersona)
        if ePersonaTituloUniversidades.values("id").exists():
            for ePersonaTituloUniversidad in ePersonaTituloUniversidades:
                ePersonaTituloUniversidad.persona = self._ePersona
                ePersonaTituloUniversidad.nombrecarrera = nombreTitulo
                ePersonaTituloUniversidad.codigoregistro = numeroRegistro
                if fechaRegistro:
                    ePersonaTituloUniversidad.fecharegistro = convertirfecha(fechaRegistro)
                if fechaGrado:
                    ePersonaTituloUniversidad.fechaacta = convertirfecha(fechaGrado)
                ePersonaTituloUniversidad.universidad = ies
                ePersonaTituloUniversidad.tiponivel = tiponivel
                ePersonaTituloUniversidad.verificadosenescyt = True
                ePersonaTituloUniversidad.fechamigradosenescyt = datetime.now()
                ePersonaTituloUniversidad.save(usuario_id=self._ePersona.usuario_id)
        else:
            ePersonaTituloUniversidad = PersonaTituloUniversidad(persona=self._ePersona,
                                                                 nombrecarrera=nombreTitulo,
                                                                 codigoregistro=numeroRegistro,
                                                                 universidad=ies,
                                                                 tiponivel=tiponivel,
                                                                 verificadosenescyt=True,
                                                                 fechamigradosenescyt=datetime.now())
            if fechaRegistro:
                ePersonaTituloUniversidad.fecharegistro = convertirfecha(fechaRegistro)
            if fechaGrado:
                ePersonaTituloUniversidad.fechaacta = convertirfecha(fechaGrado)
            ePersonaTituloUniversidad.save(usuario_id=self._ePersona.usuario_id)
        eTitulo = self._titulo(nivel, nombreTitulo)
        eTitulaciones = Titulacion.objects.filter(Q(titulo=eTitulo) | Q(registro=numeroRegistro), persona=self._ePersona)
        if eTitulaciones.values("id").exists():
            for eTitulacion in eTitulaciones:
                eTitulacion.persona = self._ePersona
                eTitulacion.titulo = eTitulo
                eTitulacion.registro = numeroRegistro
                eTitulacion.educacionsuperior = True
                eTitulacion.institucion = ies
                eTitulacion.areasenescyt = eAreaTituloSenescyt
                eTitulacion.subareasenescyt = eSubareaTituloSenescyt
                eTitulacion.verificadosenescyt = True
                eTitulacion.fechamigradosenescyt = datetime.now()
                if fechaRegistro:
                    eTitulacion.fecharegistro = convertirfecha(fechaRegistro)
                eTitulacion.save(usuario_id=self._ePersona.usuario_id)
        else:
            eTitulacion = Titulacion(persona=self._ePersona,
                                     titulo=eTitulo,
                                     registro=numeroRegistro,
                                     educacionsuperior=True,
                                     institucion=ies,
                                     areasenescyt=eAreaTituloSenescyt,
                                     subareasenescyt=eSubareaTituloSenescyt,
                                     verificadosenescyt=True,
                                     fechamigradosenescyt=datetime.now())
            if fechaRegistro:
                eTitulacion.fecharegistro = convertirfecha(fechaRegistro)
            eTitulacion.save(usuario_id=self._ePersona.usuario_id)


