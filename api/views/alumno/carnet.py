# coding=utf-8
import json
import os
import sys
from datetime import datetime, timedelta, date
from decimal import Decimal
from django.db import connection, transaction, connections
from django.template.defaultfilters import floatformat
from django.db.models import Q
from fitz import fitz
from rest_framework.parsers import MultiPartParser, FormParser
from rest_framework.permissions import IsAuthenticated
from rest_framework.views import APIView
from rest_framework import status
from api.helpers.decorators import api_security
from api.helpers.response_herlper import Helper_Response
from api.serializers.alumno.carnet import CarnetSerializer, ConfiguracionCarnetSerializer, MatriculaSerializer
from certi.funciones import crear_carnet_estudiantil
from certi.models import Carnet
from matricula.models import PeriodoMatricula
from mobile.views import make_thumb_picture, make_thumb_fotopersona
from settings import DEBUG, GENERAR_TUMBAIL, SITE_STORAGE
from sga.funciones import log, generar_nombre
from sga.models import PerfilUsuario, Periodo, Matricula, Persona, FotoPersona
from sga.templatetags.sga_extras import encrypt
from django.core.cache import cache


class CarnetAPIView(APIView):
    permission_classes = (IsAuthenticated,)
    parser_class = (MultiPartParser, FormParser,)
    api_key_module = 'ALUMNO_CARNET'

    @api_security
    def post(self, request, format=None, *args, **kwargs):
        if 'multipart/form-data' in request.content_type:
            eRequest = request._request.POST
            eFiles = request._request.FILES
        else:
            eRequest = request.data

        TIEMPO_ENCACHE = 60 * 15
        try:
            hoy = datetime.now()
            payload = request.auth.payload
            if cache.has_key(f"perfilprincipal_id_{payload['perfilprincipal']['id']}"):
                ePerfilUsuario = cache.get(f"perfilprincipal_id_{payload['perfilprincipal']['id']}")
            else:
                ePerfilUsuario = PerfilUsuario.objects.db_manager("sga_select").get(
                    pk=encrypt(payload['perfilprincipal']['id']))
                cache.set(f"perfilprincipal_id_{payload['perfilprincipal']['id']}", ePerfilUsuario,
                          TIEMPO_ENCACHE)
            ePeriodo = None
            if 'id' in payload['periodo']:
                periodoEnCache = cache.get(f"periodo_id_{payload['periodo']['id']}")
                if periodoEnCache:
                    ePeriodo = periodoEnCache
                else:
                    ePeriodo = Periodo.objects.db_manager("sga_select").get(pk=encrypt(payload['periodo']['id']))
                    cache.set(f"periodo_id_{payload['periodo']['id']}", ePeriodo, TIEMPO_ENCACHE)
            eInscripcion = ePerfilUsuario.inscripcion
            ePersona = eInscripcion.persona

            if not 'action' in eRequest:
                raise NameError(u'Acción no permitida')
            action = eRequest.get('action')
            if not action:
                raise NameError(u'Acción no permitida')

            elif action == 'deleteCarnet':
                with transaction.atomic():
                    try:
                        if not ePeriodo:
                            raise NameError(u"Periodo no encontrado")
                        if not eInscripcion:
                            raise NameError(u"Inscripción no encontrada")
                        if not 'id' in eRequest:
                            raise NameError(u"No se encontro parametro de matricula")
                        if not Matricula.objects.values("id").filter(pk=encrypt(eRequest.get("id")), status=True):
                            raise NameError(u"Matrícula no valida")
                        eMatricula = Matricula.objects.get(pk=encrypt(eRequest.get("id")), status=True)
                        eInscripcion = eMatricula.inscripcion
                        ePersona = eInscripcion.persona
                        if not PeriodoMatricula.objects.values_list('id').filter(status=True, periodo=ePeriodo).exists():
                            raise NameError(f"Estimad{'a' if ePersona.es_mujer() else 'o'}, el periodo académico {ePeriodo.nombre} no permite carné estudiantil")
                        ePeriodoMatricula = PeriodoMatricula.objects.filter(status=True, periodo=ePeriodo)
                        if len(ePeriodoMatricula) > 1:
                            raise NameError(f"Estimad{'a' if ePersona.es_mujer() else 'o'}, el periodo académico {ePeriodo.nombre} no permite carné estudiantil")
                        ePeriodoMatricula = ePeriodoMatricula[0]
                        if not ePeriodoMatricula.valida_uso_carnet:
                            raise NameError(f"Estimad{'a' if ePersona.es_mujer() else 'o'}, el periodo académico {ePeriodo.nombre} no permite carné estudiantil")
                        eConfiguracionCarnet = ePeriodoMatricula.configuracion_carnet
                        eCarnets = Carnet.objects.filter(config=eConfiguracionCarnet, persona=ePersona, matricula=eMatricula)
                        if not eCarnets.values('id').exists():
                            raise NameError(u"No existe carné estudiantil a eliminar")
                        delete = eCarnet = eCarnets.first()
                        eCarnet.delete()
                        log(u'Elimino carné estudiantil: %s' % delete, request, "del")
                        return Helper_Response(isSuccess=True, data={}, status=status.HTTP_200_OK)
                    except Exception as ex:
                        transaction.set_rollback(True)
                        return Helper_Response(isSuccess=False, data={},
                                               message=f'Ocurrio un error al eliminar: {ex.__str__()}',
                                               status=status.HTTP_200_OK)

            elif action == 'saveFotoPerfil':
                with transaction.atomic():
                    try:
                        ePersona = Persona.objects.get(pk=ePersona.id)
                        if not 'fileFoto' in eFiles:
                            raise NameError(u"Favor subir el archivo de la copia de cédula o pasaporte")

                        nfileFoto = eFiles['fileFoto']
                        extensionFoto = nfileFoto._name.split('.')
                        tamFoto = len(extensionFoto)
                        exteFoto = extensionFoto[tamFoto - 1]
                        if nfileFoto.size > 1500000:
                            raise NameError(u"Error al cargar la foto de perfil, el tamaño del archivo es mayor a 15 Mb.")
                        if not exteFoto.lower() in ['jpg']:
                            raise NameError(u"Error al cargar la foto de perfil, solo se permiten archivos .jpg")
                        nfileFoto._name = generar_nombre("foto_", nfileFoto._name)
                        eFotoPersona = ePersona.foto()
                        if eFotoPersona:
                            eFotoPersona.foto = nfileFoto
                        else:
                            eFotoPersona = FotoPersona(persona=ePersona, foto=nfileFoto)
                        eFotoPersona.save(request)
                        make_thumb_picture(ePersona)
                        if GENERAR_TUMBAIL:
                            make_thumb_fotopersona(ePersona)
                        log(u'Adicionó foto de persona: %s' % eFotoPersona, request, "add")
                        eMatricula = Matricula.objects.filter(nivel__periodo=ePeriodo, inscripcion=eInscripcion)
                        if not eMatricula.values("id").exists():
                            raise NameError(f"Estimad{'a' if ePersona.es_mujer() else 'o'}, solo los perfiles de estudiantes matriculados.")
                        eMatricula = eMatricula.first()
                        ePeriodoMatricula = PeriodoMatricula.objects.filter(status=True, periodo=ePeriodo)
                        ePeriodoMatricula = ePeriodoMatricula[0]
                        eConfiguracionCarnet = ePeriodoMatricula.configuracion_carnet
                        eCarnets = Carnet.objects.filter(config=eConfiguracionCarnet, persona=ePersona, matricula=eMatricula)
                        # if not eCarnets.values('id').exists():
                        #     raise NameError(u"No existe carné estudiantil a eliminar")
                        if eCarnets.values('id').exists():
                            delete = eCarnets.first()
                            eCarnets.delete()
                            log(u'Elimino carné estudiantil: %s' % delete, request, "del")
                        # result, msg = crear_carnet_estudiantil(eMatricula, eConfiguracionCarnet, request, matricula_id=eMatricula.id)
                        # if not result:
                        #     raise NameError(msg)
                        return Helper_Response(isSuccess=True, data={}, status=status.HTTP_200_OK)
                    except Exception as ex:
                        transaction.set_rollback(True)
                        return Helper_Response(isSuccess=False, data={}, message=f'Ocurrio un error al guardar: {ex.__str__()}', status=status.HTTP_200_OK)

            return Helper_Response(isSuccess=False, data={}, message=f'Acción no encontrada', status=status.HTTP_200_OK)
        except Exception as ex:
            return Helper_Response(isSuccess=False, data={}, message=f'Ocurrio un error: {ex.__str__()}',
                                   status=status.HTTP_200_OK)

    @api_security
    def get(self, request):
        TIEMPO_ENCACHE = 60 * 15
        try:
            aData = {}
            hoy = datetime.now().date()
            payload = request.auth.payload
            if cache.has_key(f"perfilprincipal_id_{payload['perfilprincipal']['id']}"):
                ePerfilUsuario = cache.get(f"perfilprincipal_id_{payload['perfilprincipal']['id']}")
            else:
                ePerfilUsuario = PerfilUsuario.objects.db_manager("sga_select").get(pk=encrypt(payload['perfilprincipal']['id']))
                cache.set(f"perfilprincipal_id_{payload['perfilprincipal']['id']}", ePerfilUsuario, TIEMPO_ENCACHE)
            eInscripcion = ePerfilUsuario.inscripcion
            ePersona = eInscripcion.persona
            ePeriodo = None
            if 'id' in payload['periodo']:
                periodoEnCache = cache.get(f"periodo_id_{payload['periodo']['id']}")
                if periodoEnCache:
                    ePeriodo = periodoEnCache
                else:
                    if payload['periodo']['id'] is None:
                        return Helper_Response(isSuccess=False, redirect="/", module_access=False,
                                               message=f"Estimad{'a' if ePersona.es_mujer() else 'o'} {ePersona.__str__()}, para utilizar este módulo debe estar matriculad{'a' if ePersona.es_mujer() else 'o'}",
                                               status=status.HTTP_200_OK)
                    else:
                        if not Periodo.objects.values("id").filter(pk=encrypt(payload['periodo']['id']), status=True).exists():
                            return Helper_Response(isSuccess=False, data={}, message=f"Estimad{'a' if ePersona.es_mujer() else 'o'} {ePersona.__str__()}, para utilizar este módulo debe estar matriculad{'a' if ePersona.es_mujer() else 'o'}", status=status.HTTP_200_OK, module_access=False)
                        ePeriodo = Periodo.objects.get(pk=encrypt(payload['periodo']['id']), status=True)
                    cache.set(f"periodo_id_{payload['periodo']['id']}", ePeriodo, TIEMPO_ENCACHE)
            if not ePeriodo:
                return Helper_Response(isSuccess=False, redirect="/", module_access=False,
                                       message=f"Estimad{'a' if ePersona.es_mujer() else 'o'} {ePersona.__str__()}, para utilizar este módulo debe estar matriculad{'a' if ePersona.es_mujer() else 'o'}",
                                       status=status.HTTP_200_OK)
            if not PeriodoMatricula.objects.values_list('id').filter(status=True, periodo=ePeriodo).exists():
                return Helper_Response(isSuccess=False, redirect="/", module_access=False,
                                       message=f"Estimad{'a' if ePersona.es_mujer() else 'o'}, el periodo académico {ePeriodo.nombre} no permite carné estudiantil",
                                       status=status.HTTP_200_OK)
            ePeriodoMatricula = PeriodoMatricula.objects.filter(status=True, periodo=ePeriodo)
            if len(ePeriodoMatricula) > 1:
                return Helper_Response(isSuccess=False, redirect="/", module_access=False,
                                       message=f"Estimad{'a' if ePersona.es_mujer() else 'o'}, el periodo académico {ePeriodo.nombre} no permite carné estudiantil",
                                       status=status.HTTP_200_OK)
            ePeriodoMatricula = ePeriodoMatricula[0]
            if not ePeriodoMatricula.valida_uso_carnet:
                return Helper_Response(isSuccess=False, redirect="/", module_access=False,
                                       message=f"Estimad{'a' if ePersona.es_mujer() else 'o'}, el periodo académico {ePeriodo.nombre} no permite carné estudiantil",
                                       status=status.HTTP_200_OK)
            eConfiguracionCarnet = ePeriodoMatricula.configuracion_carnet
            if not Matricula.objects.values("id").filter(nivel__periodo=ePeriodo, inscripcion=eInscripcion).exists():
                return Helper_Response(isSuccess=False, redirect="/", module_access=False,
                                       message=f"Estimad{'a' if ePersona.es_mujer() else 'o'}, solo los perfiles de estudiantes matriculados pueden acceder al módulo.",
                                       status=status.HTTP_200_OK)
            eMatricula = Matricula.objects.filter(nivel__periodo=ePeriodo, inscripcion=eInscripcion)[0]
            eCarnet = Carnet.objects.filter(config=eConfiguracionCarnet, persona=ePersona, matricula=eMatricula)
            if ePersona.tiene_foto():
                with transaction.atomic():
                    try:
                        if not eCarnet.values("id").exists():
                            result, msg = crear_carnet_estudiantil(eMatricula, eConfiguracionCarnet, request, matricula_id=eMatricula.id)
                            if not result:
                                raise NameError(msg)
                            eCarnet = Carnet.objects.filter(config=eConfiguracionCarnet, persona=ePersona, matricula=eMatricula)
                        else:
                            cantidad_generacion = 0
                            while documento_esta_vacio(eCarnet.first().pdf):
                                if cantidad_generacion > 5:
                                    raise NameError('Falló generación de carné estudiantil')
                                eCarnet.delete()
                                result, msg = crear_carnet_estudiantil(eMatricula, eConfiguracionCarnet, request, matricula_id=eMatricula.id)
                                if not result:
                                    raise NameError(msg)
                                eCarnet = Carnet.objects.filter(config=eConfiguracionCarnet, persona=ePersona, matricula=eMatricula)
                                cantidad_generacion += 1
                    except Exception as exep:
                        transaction.set_rollback(True)
                        return Helper_Response(isSuccess=False, redirect="/", module_access=False,
                                               message=f'{exep.__str__()}',
                                               status=status.HTTP_200_OK)
            aData["eConfiguracionCarnet"] = ConfiguracionCarnetSerializer(eConfiguracionCarnet).data
            aData["eMatricula"] = MatriculaSerializer(eMatricula).data
            aData["eCarnet"] = CarnetSerializer(eCarnet[0]).data if eCarnet.values('id').exists() else {}
            return Helper_Response(isSuccess=True, data=aData, status=status.HTTP_200_OK)
        except Exception as ex:
            return Helper_Response(isSuccess=False, data={}, message=f'{ex.__str__()}', status=status.HTTP_200_OK)


def documento_esta_vacio(pdfname):
    if(os.path.exists("".join([SITE_STORAGE, pdfname]))):
        with fitz.open("".join([SITE_STORAGE, pdfname])) as document:
            words = ''
            for page_number, page in enumerate(document):
                words += page.get_text()
            return len(words) < 4
    else:
        return True