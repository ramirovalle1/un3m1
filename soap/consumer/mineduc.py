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
        from sga.models import Persona, Titulacion
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
            eHistorialPersonaConsultaTitulos = HistorialPersonaConsultaTitulo.objects.filter(persona=self._ePersona, servicio=HistorialPersonaConsultaTitulo.Servicios.MINEDUC).order_by('-fecha')
            if eHistorialPersonaConsultaTitulos.values("id").exists():
                eHistorialPersonaConsultaTitulo = eHistorialPersonaConsultaTitulos.first()
                diferencia = datetime.now().date() - eHistorialPersonaConsultaTitulo.fecha
                if diferencia.days <= 30:
                    isContinue = False
        if isContinue:
            url = f"{self._get_variable('SITE_URL_SCI')}/api/dinardap/mineduc"
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
                        data = response['data'].get('mineduc', [])
                        eHistorialPersonaConsultaTitulo = HistorialPersonaConsultaTitulo(persona=self._ePersona,
                                                                                         fecha=datetime.now().date(),
                                                                                         servicio=HistorialPersonaConsultaTitulo.Servicios.MINEDUC,
                                                                                         obtuvo=True if len(data) else False)
                        eHistorialPersonaConsultaTitulo.save()
                    except Exception as ex:
                        transaction.set_rollback(True)
        eTitulaciones = Titulacion.objects.filter(persona=self._ePersona).values_list('persona_id', 'titulo__nombre', 'institucion__nombre', 'registro')
        return list(eTitulaciones)

    def _procesar(self):
        response = self._response
        data = response['data'].get('mineduc', [])
        self._dataResponse = data
        for registro in data:
            self._titulacion(registro)

    def _titulo(self, eNivelTitulacion, nombreTitulo):
        from sga.models import Titulo, NivelTitulacion
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
                # if not eTitulo.senescyt:
                eTitulo.nivel = eNivelTitulacion
                eTitulo.senescyt = True
                eTitulo.save(usuario_id=self._ePersona.usuario_id)
        return eTitulo

    def _colegio(self, nombre):
        from sga.models import Colegio
        eColegio = None
        if not nombre is None:
            eColegios = Colegio.objects.filter(nombre=nombre)
            if not eColegios.values("id").exists():
                eColegio = Colegio(nombre=nombre,
                                   tipo=6)
                eColegio.save(usuario_id=self._ePersona.usuario_id)
            else:
                eColegio = eColegios.first()
        return eColegio

    def _titulacion(self, registro):
        from django.db.models import Q
        from sga.models import Titulacion, NivelTitulacion, DetalleTitulacionBachiller
        institucion = registro.get('institucion', None)
        titulo = registro.get('titulo', None)
        especialidad = registro.get('especialidad', None)
        eNivelTitulacion = NivelTitulacion.objects.get(pk=1)
        eTitulo = None
        if titulo:
            if especialidad:
                titulo_aux = f"{titulo} ESPECIALIZACION {especialidad}".upper()
                eTitulo = self._titulo(eNivelTitulacion, titulo_aux)
                if eTitulo is None:
                    titulo_aux = f"{titulo} ESPECIALIZACIÓN {especialidad}".upper()
                    eTitulo = self._titulo(eNivelTitulacion, titulo_aux)
            else:
                titulo = titulo.upper()
                eTitulo = self._titulo(eNivelTitulacion, titulo)
        numeroRefrendacion = registro.get('numeroRefrendacion', None)
        codigoRefrendacion = registro.get('codigoRefrendacion', None)
        fechaGrado = registro.get('fechaGrado', None)
        eColegio = self._colegio(institucion)
        eTitulaciones = Titulacion.objects.filter(Q(titulo__nivel=eNivelTitulacion) | Q(titulo=eTitulo) | Q(registro=codigoRefrendacion), persona=self._ePersona)
        if eTitulaciones.values("id").exists():
            for eTitulacion in eTitulaciones:
                eTitulacion.persona = self._ePersona
                eTitulacion.titulo = eTitulo
                eTitulacion.colegio = eColegio
                eTitulacion.save(usuario_id=self._ePersona.usuario_id)
                eDetalleTitulacionBachiller = DetalleTitulacionBachiller.objects.filter(titulacion=eTitulacion).first()
                if eDetalleTitulacionBachiller is None:
                    eDetalleTitulacionBachiller = DetalleTitulacionBachiller(titulacion=eTitulacion,
                                                                             calificacion=0,
                                                                             anioinicioperiodograduacion=None,
                                                                             codigorefrendacion=codigoRefrendacion,
                                                                             numerorefrendacion=numeroRefrendacion)
                else:
                    eDetalleTitulacionBachiller.codigorefrendacion=codigoRefrendacion
                    eDetalleTitulacionBachiller.numerorefrendacion=numeroRefrendacion
                if fechaGrado:
                    fechaGrado = datetime.strptime(fechaGrado, '%b %d, %Y %H:%M:%S %p')
                    eDetalleTitulacionBachiller.fechagrado = fechaGrado
                    eDetalleTitulacionBachiller.aniofinperiodograduacion = fechaGrado.year
                eDetalleTitulacionBachiller.save(usuario_id=self._ePersona.usuario_id)
        else:
            eTitulacion = Titulacion(persona=self._ePersona,
                                     titulo=eTitulo,
                                     colegio=eColegio
                                     )
            eTitulacion.save(usuario_id=self._ePersona.usuario_id)
            eDetalleTitulacionBachiller = DetalleTitulacionBachiller.objects.filter(titulacion=eTitulacion).first()
            if eDetalleTitulacionBachiller is None:
                eDetalleTitulacionBachiller = DetalleTitulacionBachiller(titulacion=eTitulacion,
                                                                         calificacion=0,
                                                                         anioinicioperiodograduacion=None,
                                                                         codigorefrendacion=codigoRefrendacion,
                                                                         numerorefrendacion=numeroRefrendacion)
                eDetalleTitulacionBachiller.save(usuario_id=self._ePersona.usuario_id)
            else:
                eDetalleTitulacionBachiller.codigorefrendacion = codigoRefrendacion
                eDetalleTitulacionBachiller.numerorefrendacion = numeroRefrendacion
            if fechaGrado:
                fechaGrado = datetime.strptime(fechaGrado, '%b %d, %Y %H:%M:%S %p')
                eDetalleTitulacionBachiller.fechagrado = fechaGrado
                eDetalleTitulacionBachiller.aniofinperiodograduacion = fechaGrado.year
            eDetalleTitulacionBachiller.save(usuario_id=self._ePersona.usuario_id)


