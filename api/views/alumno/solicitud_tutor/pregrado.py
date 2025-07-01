# coding=utf-8
import json
import os
import sys
from datetime import datetime, timedelta, date
from decimal import Decimal

from django.core.exceptions import ObjectDoesNotExist
from django.db import connection, transaction, connections
from django.template.defaultfilters import floatformat
from django.db.models import Q, Sum
from rest_framework.permissions import IsAuthenticated
from rest_framework.views import APIView
from rest_framework import status
from settings import DEBUG
from api.forms.solicitud_tutor import SolicitudTutorMateriaForm
from api.helpers.decorators import api_security
from api.helpers.response_herlper import Helper_Response
from api.views.alumno.matricula.functions import validate_entry_to_student_api
from core.cache import get_cache_ePerfilUsuario
from sga.funciones import generar_nombre, log
from sga.models import PerfilUsuario, Matricula, SolicitudTutorSoporteMatricula, SolicitudTutorSoporteMateria, Persona, \
    MateriaAsignada, Notificacion, Materia, ProfesorDistributivoHoras
from sga.templatetags.sga_extras import encrypt
from django.core.cache import cache
from api.serializers.alumno.solicitud_tutor import SolicitudTutorSoporteMateriaSerializer


class PregradoAPIView(APIView):
    permission_classes = (IsAuthenticated,)
    api_key_module = 'ALUMNO_SOLICITUD_TUTOR'

    @api_security
    def post(self, request):
        if 'multipart/form-data' in request.content_type:
            eRequest = request._request.POST
            eFiles = request._request.FILES
        else:
            eRequest = request.data
        try:
            payload = request.auth.payload
            ePerfilUsuario = get_cache_ePerfilUsuario(int(encrypt(payload['perfilprincipal']['id'])))
            eMatricula = Matricula.objects.get(pk=encrypt(payload['matricula']['id']))
            action = eRequest.get('action', None)
            if not action:
                raise NameError(u'Acción no permitida')

            if action == 'loadMaterias':
                try:
                    ePeriodo = eMatricula.nivel.periodo
                    filtro = Q(matricula=eMatricula, matricula__status=True, materia__status=True, retiramateria=False, materia__nivel__periodo=ePeriodo)
                    if not DEBUG:
                        filtro = filtro & Q(matricula__cerrada=False, materia__cerrado=False)
                    eMateriaAsignadas = MateriaAsignada.objects.filter(filtro)
                    eMaterias = Materia.objects.filter(pk__in=eMateriaAsignadas.values_list('materia__id', flat=True), profesormateria__tipoprofesor_id__in=[16, 8]).exclude(asignaturamalla__malla_id__in=[353, 22])
                    results = [{"id": x.id, "name": x.nombre_mostrar_alias()} for x in eMaterias]
                    return Helper_Response(isSuccess=True, data={'results': results}, message=f'Se cargaron correctamente los datos', status=status.HTTP_200_OK)
                except Exception as ex:
                    return Helper_Response(isSuccess=False, data={}, message=f'Error al cargar los datos: {ex.__str__()}', status=status.HTTP_200_OK)

            elif action == 'loadProfesor':
                try:
                    id = eRequest.get('id', 0)
                    try:
                        eMateria = Materia.objects.get(pk=id)
                    except ObjectDoesNotExist:
                        raise NameError(u"Materia no encontrada")
                    ePeriodo = eMatricula.nivel.periodo
                    eProfesorDistributivoHoras = ProfesorDistributivoHoras.objects.filter(status=True, periodo=ePeriodo, detalledistributivo__criteriodocenciaperiodo__criterio_id=136, profesor__persona__real=True).distinct()
                    eProfesorMaterias = eMateria.profesormateria_set.filter(status=True, activo=True, profesor_id__in=eProfesorDistributivoHoras.values_list('profesor_id', flat=True).distinct())
                    results = [{"id": x.profesor.id, "name": x.profesor.persona.nombre_completo_inverso()} for x in eProfesorMaterias]
                    return Helper_Response(isSuccess=True, data={'results': results}, message=f'Se cargaron correctamente los datos', status=status.HTTP_200_OK)
                except Exception as ex:
                    return Helper_Response(isSuccess=False, data={}, message=f'Error al cargar los datos: {ex.__str__()}', status=status.HTTP_200_OK)

            elif action == 'saveSolicitudTutorSoporteMateria':
                with transaction.atomic():
                    try:
                        isNew = False
                        f = SolicitudTutorMateriaForm(eRequest, eFiles)
                        f.initQuerySet(eRequest)
                        if not f.is_valid():
                            errors = []
                            for k, v in f.errors.items():
                                errors.append({'field': k, 'message': v[0]})
                            f.addErrors(errors)
                            form = f.toArray()
                            transaction.set_rollback(True)
                            return Helper_Response(isSuccess=False, data={'form': form}, message=f'Debe ingresar la información en todos los campos requeridos', status=status.HTTP_200_OK)
                        try:
                            eMateriaAsignada = MateriaAsignada.objects.get(materia=f.cleaned_data['materia'], matricula=eMatricula, retiramateria=False)
                        except ObjectDoesNotExist:
                            raise NameError(u"No se encontro materia asignada")
                        id = eRequest.get('id', 0)
                        try:
                            eSolicitudTutorSoporteMateria = SolicitudTutorSoporteMateria.objects.get(materiaasignada__matricula=eMatricula, pk=id)
                        except ObjectDoesNotExist:
                            eSolicitudTutorSoporteMateria = SolicitudTutorSoporteMateria(profesor=f.cleaned_data['profesor'],
                                                                                         materiaasignada=eMateriaAsignada)
                            isNew = True
                        eSolicitudTutorSoporteMateria.tipo = f.cleaned_data['tipo']
                        eSolicitudTutorSoporteMateria.descripcion = f.cleaned_data['descripcion']
                        archivo = f.files.get('archivo', None)
                        if archivo:
                            archivo.name = generar_nombre("solicitud_", archivo.name)
                            eSolicitudTutorSoporteMateria.archivo = archivo
                        eSolicitudTutorSoporteMateria.save(request)
                        if isNew is True:
                            log(u'Adicionó solicitud a tutor de su materia: %s' % eSolicitudTutorSoporteMateria.materiaasignada, request, "add")
                        else:
                            log(u'Edito solicitud a tutor de su materia: %s' % eSolicitudTutorSoporteMateria.materiaasignada, request, "add")
                        # Notificacion para el docente
                        eNotificacion = Notificacion(titulo='Consulta de acompañamiento del alumno %s' % eSolicitudTutorSoporteMateria.materiaasignada.matricula.inscripcion.persona.nombre_completo_minus(),
                                                     cuerpo='Tiene una consulta de la asignatura %s' % eSolicitudTutorSoporteMateria.materiaasignada.materia.asignatura,
                                                     destinatario=eSolicitudTutorSoporteMateria.profesor.persona,
                                                     url="/pro_tutoria?action=verobservacionesmimateria&id={}".format(eSolicitudTutorSoporteMateria.pk),
                                                     content_type=None,
                                                     object_id=eSolicitudTutorSoporteMateria.pk,
                                                     prioridad=2,
                                                     fecha_hora_visible=datetime.now() + timedelta(days=1),
                                                     app_label='sga')
                        eNotificacion.save(request)
                        return Helper_Response(isSuccess=True, data={}, message=f'Se guardo correctamente los datos', status=status.HTTP_200_OK)
                    except Exception as ex:
                        transaction.set_rollback(True)
                        return Helper_Response(isSuccess=False, data={}, message=f'Error al guardar los datos: {ex.__str__()}', status=status.HTTP_200_OK)

            elif action == 'deleteSolicitudTutorSoporteMateria':
                with transaction.atomic():
                    try:
                        id = eRequest.get('id', 0)
                        try:
                            eSolicitudTutorSoporteMateria = SolicitudTutorSoporteMateria.objects.get(materiaasignada__matricula=eMatricula, pk=id)
                        except ObjectDoesNotExist:
                            raise NameError(u"Datos no encontrados")
                        deleteSolicitudTutorSoporteMateria = eSolicitudTutorSoporteMateria
                        eSolicitudTutorSoporteMateria.delete()
                        log(u'Eliminó solicitud de tutoria académica: %s' % deleteSolicitudTutorSoporteMateria, request, "del")
                        return Helper_Response(isSuccess=True, data={}, message=f'Se elimino correctamente solicitud', status=status.HTTP_200_OK)
                    except Exception as ex:
                        transaction.set_rollback(True)
                        return Helper_Response(isSuccess=False, data={}, message=f'Error al guardar los datos: {ex.__str__()}', status=status.HTTP_200_OK)

            return Helper_Response(isSuccess=False, data={}, message=f'Acción no encontrada', status=status.HTTP_200_OK)

        except Exception as ex:
            return Helper_Response(isSuccess=False, data={}, message=f'Ocurrio un error: {ex.__str__()}', status=status.HTTP_200_OK)

    @api_security
    def get(self, request):
        TIEMPO_ENCACHE = 60 * 15
        try:
            eRequest = request.query_params
            aData = {}
            hoy = datetime.now().date()
            payload = request.auth.payload
            ePerfilUsuario = PerfilUsuario.objects.get(pk=encrypt(payload['perfilprincipal']['id']))
            if not ePerfilUsuario.es_estudiante():
                raise NameError(u'Solo los perfiles de estudiantes pueden ingresar al modulo.')
            if not 'id' in payload['matricula']:
                raise NameError(u'No se encuentra matriculado.')
            if payload['matricula']['id'] is None:
                raise NameError(u'No se encuentra matriculado.')
            if cache.has_key(f"matricula_id_{payload['matricula']['id']}"):
                eMatricula = cache.get(f"matricula_id_{payload['matricula']['id']}")
            else:
                eMatricula = Matricula.objects.get(pk=encrypt(payload['matricula']['id']))
                cache.set(f"matricula_id_{payload['matricula']['id']}", eMatricula, TIEMPO_ENCACHE)
            valid, msg_error = validate_entry_to_student_api(ePerfilUsuario, 'pregrado')
            if not valid:
                raise NameError(msg_error)
            search = eRequest.get('search', None)
            filtro = Q(materiaasignada__matricula=eMatricula) & Q(status=True)
            if search:
                filtro_s = Q(materiaasignada__materia__asignatura__nombre__icontains=search) | Q(materiaasignada__materia__paralelomateria__nombre__icontains=search)
                filtro = filtro & filtro_s
            eSolicitudes = SolicitudTutorSoporteMateria.objects.filter(filtro).order_by('-id')
            eSolicitudes = SolicitudTutorSoporteMateriaSerializer(eSolicitudes, many=True).data if eSolicitudes.values("id").exists() else []
            return Helper_Response(isSuccess=True, data={'eSolicitudes': eSolicitudes}, status=status.HTTP_200_OK)
        except Exception as ex:
            return Helper_Response(isSuccess=False, data={'eSolicitudes': []}, message=f'{ex.__str__()}', status=status.HTTP_200_OK)
