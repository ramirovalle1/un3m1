import json
import sys
import random
from datetime import datetime
from django.core.cache import cache
from django.core.exceptions import ObjectDoesNotExist
from django.db import transaction
from django.db.models import Q
from django.http import JsonResponse
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.views import APIView
from api.helpers.decorators import api_security
from api.helpers.functions_helper import get_variable
from api.helpers.response_herlper import Helper_Response
from api.serializers.alumno.balconservicio import ProcesoSerializer, CategoriaSerializer, InformacionSerializer, SolicitudSerializer, HistorialSolicitudSerializer, EncuestaProcesoSerializer
from inno.models import MateriaAsignadaPlanificacionSedeVirtualExamen, TurnoPlanificacionSedeVirtualExamen, \
    AulaPlanificacionSedeVirtualExamen, FechaPlanificacionSedeVirtualExamen
from inno.serializers.AsistenciaExamen import MateriaAsignadaPlanificacionSedeVirtualExamenSerializer, \
    Persona2Serializer as PersonaSerializer, AulaPlanificacionSedeVirtualExamenSerializer, \
    TurnoPlanificacionSedeVirtualExamenSerializer, FechaPlanificacionSedeVirtualExamenSerializer, SedeVirtualSerializer, \
    LaboratorioVirtualSerializer
from matricula.models import PeriodoMatricula
from settings import DEBUG
from sga.funciones import remover_caracteres_especiales_unicode, generar_nombre, log, notificacion, variable_valor
from sga.models import PerfilUsuario, Periodo, SedeVirtual, Modalidad, Carrera, Sesion


# from sga.templatetags.sga_extras import encrypt


class CronogramaMatriulaAPIView(APIView):
    # permission_classes = (IsAuthenticated,)
    # api_key_module = 'ALUMNO_BALCON_SERVICIOS'

    # @api_security
    def get(self, request):
        ahora = datetime.now()
        fecha_fin = datetime(ahora.year, ahora.month, ahora.day, 23, 59, 59)
        tiempo_cache = fecha_fin - ahora
        TIEMPO_ENCACHE = int(tiempo_cache.total_seconds())
        try:
            id_periodo_login_matricula = variable_valor('ID_BLOQUEO_LOGIN_MATRICULA')
            if id_periodo_login_matricula is None:
                id_periodo_login_matricula = 0
            if cache.has_key(f"cronograma_matricula_periodo_id_{id_periodo_login_matricula}"):
                _aModalidades = cache.get(f"cronograma_matricula_periodo_id_{id_periodo_login_matricula}")
            else:
                _aModalidades = []
                _ePeriodoMatriculas = PeriodoMatricula.objects.filter(status=True, valida_login=True, periodo_id=id_periodo_login_matricula)
                if (_ePeriodoMatricula := _ePeriodoMatriculas.filter(activo=True, valida_cronograma=True).first()) is not None:
                    if _ePeriodoMatricula.valida_cronograma and _ePeriodoMatricula.valida_login and _ePeriodoMatricula.tiene_cronograma_coordinaciones():
                        _ePeriodo = _ePeriodoMatricula.periodo
                        for eModalidad in Modalidad.objects.filter(pk__in=[1, 2, 3]).order_by('id'):
                            _imagen = None
                            if eModalidad.id == 1:  # PRESENCIAL
                                _imagen = f"{get_variable('SITE_URL_SGA')}/static/logos/presencial.png"
                            elif eModalidad.id == 2:  # SEMIPRESENCIAL
                                _imagen = f"{get_variable('SITE_URL_SGA')}/static/logos/semipresencial.png"
                            elif eModalidad.id == 3:  # EN LINEA
                                _imagen = f"{get_variable('SITE_URL_SGA')}/static/logos/en_linea.png"
                            _eModalidad = {'name': eModalidad.nombre, 'id': random.randint(1, 10000), 'imagen': _imagen}
                            _aCoordinaciones = []
                            _aCarreras = []
                            _aSecciones = []
                            for cronogramacoordinacion in _ePeriodoMatricula.cronograma_coordinaciones().filter(activo=True, cronogramacarrera__carrera__modalidad=eModalidad.id).distinct():
                                eCoordinacion = cronogramacoordinacion.coordinacion
                                _aCoordinacion = {}
                                eCarreras = Carrera.objects.filter(pk__in=cronogramacoordinacion.cronogramacarreras().filter(activo=True, carrera__modalidad=eModalidad.id).values_list('carrera__id', flat=True)).distinct()
                                _aCarreras = []
                                for eCarrera in eCarreras:
                                    _aCarrera = {'name': eCarrera.nombrevisualizar if eCarrera.nombrevisualizar else eCarrera.nombre,
                                                 'id': random.randint(1, 10000)}
                                    _aSecciones = []
                                    eSecciones = Sesion.objects.filter(pk__in=cronogramacoordinacion.cronogramacarreras().filter(activo=True, carrera=eCarrera).values_list('sesion__id', flat=True)).distinct()
                                    for eSeccion in eSecciones:
                                        _imagen = None
                                        if eSeccion.id in [1, 9]:  # Matutina
                                            _imagen = f"{get_variable('SITE_URL_SGA')}/static/logos/jornada_matutina.svg"
                                        elif eSeccion.id in [4]:  # VESPERTINA
                                            _imagen = f"{get_variable('SITE_URL_SGA')}/static/logos/jornada_vespertino.svg"
                                        elif eSeccion.id in [5, 10]:  # NOCTURNA
                                            _imagen = f"{get_variable('SITE_URL_SGA')}/static/logos/jornada_nocturna.svg"
                                        elif eSeccion.id in [13, 16]:  # EN LINEA
                                            _imagen = f"{get_variable('SITE_URL_SGA')}/static/logos/jornada_en_linea.svg"
                                        elif eSeccion.id in [7, 8, 11, 12]:  # FIN DE SEMANA
                                            _imagen = f"{get_variable('SITE_URL_SGA')}/static/logos/jornada_fin_semana.svg"
                                        else:  # SIN DEFINIR
                                            _imagen = f"{get_variable('SITE_URL_SGA')}/static/logos/jornada_fin_semana.svg"
                                        _aSeccion = {'name': eSeccion.alias if eSeccion.alias else eSeccion.nombre,
                                                     'id': random.randint(1, 10000),
                                                     'imagen': _imagen}
                                        cronogramacarrera = cronogramacoordinacion.cronogramacarreras().filter(activo=True, carrera=eCarrera, sesion=eSeccion).distinct().first()
                                        if cronogramacarrera:
                                            fhInicioCarrera = datetime.combine(cronogramacarrera.fechainicio, cronogramacarrera.horainicio)
                                            fhFinCarrera = datetime.combine(cronogramacarrera.fechafin, cronogramacarrera.horafin)
                                            _aSeccion['fecha_inicio'] = fhInicioCarrera.strftime('%Y %B, %d')
                                            _aSeccion['hora_inicio'] = fhInicioCarrera.strftime('%H:%M:%S')
                                            _aSeccion['fecha_fin'] = fhFinCarrera.strftime('%Y %B, %d')
                                            _aSeccion['hora_fin'] = fhFinCarrera.strftime('%H:%M:%S')
                                            _aNiveles = []
                                            for eNivel in cronogramacarrera.niveles():
                                                _aNiveles.append({'id': random.randint(1, 10000),
                                                                  'name': eNivel.nombre,
                                                                  'alias': eNivel.nombre.replace("NIVEL", "").lower().strip()})
                                            # _aSeccion['niveles'] = ', '.join(map(str, list(cronogramacarrera.niveles().values_list('nombre', flat=True))))
                                            _aSeccion['aNiveles'] = _aNiveles
                                        _aSecciones.append(_aSeccion)
                                    _aCarrera['aSecciones'] = _aSecciones
                                    _aCarreras.append(_aCarrera)
                                fhInicioCoordinacion = datetime.combine(cronogramacoordinacion.fechainicio, cronogramacoordinacion.horainicio)
                                fhFinCoordinacion = datetime.combine(cronogramacoordinacion.fechafin, cronogramacoordinacion.horafin)
                                if eCoordinacion.id in (2, 3):
                                    if not any(coordinacion['alias'] == 'FACSECYD' for coordinacion in _aCoordinaciones):
                                        _aCoordinacion = {'id': random.randint(2, 3),
                                                          'name': 'FACULTAD CIENCIAS SOCIALES, EDUCACIÓN COMERCIAL Y DERECHO',
                                                          'alias': 'FACSECYD',
                                                          'inicio': fhInicioCoordinacion.strftime('%Y-%m-%d %H:%M:%S'),
                                                          'fin': fhFinCoordinacion.strftime('%Y-%m-%d %H:%M:%S'),
                                                          'aCarreras': _aCarreras
                                                          }
                                        _aCoordinaciones.append(_aCoordinacion)
                                    else:
                                        # Encuentra el diccionario con el alias 'FACSECYD'
                                        coordinacion_index = None
                                        for i, coordinacion in enumerate(_aCoordinaciones):
                                            if coordinacion['alias'] == 'FACSECYD':
                                                coordinacion_index = i
                                                break
                                        # Verifica si se encontró la coordinación con el alias 'FACSECYD'
                                        if coordinacion_index is not None:
                                            # Actualiza el valor de 'aCarreras' en la coordinación encontrada
                                            _aCarreras_aux = _aCoordinaciones[coordinacion_index]['aCarreras']
                                            if _aCarreras_aux:
                                                for _aux in _aCarreras_aux:
                                                    _aCarreras.append(_aux)
                                                _aCoordinaciones[coordinacion_index]['aCarreras'] = _aCarreras

                                else:
                                    if not any(int(coordinacion['id']) == eCoordinacion.id for coordinacion in _aCoordinaciones):
                                        _aCoordinacion = {'id': eCoordinacion.id,
                                                          'name': eCoordinacion.nombre,
                                                          'alias': eCoordinacion.alias,
                                                          'inicio': fhInicioCoordinacion.strftime('%Y-%m-%d %H:%M:%S'),
                                                          'fin': fhFinCoordinacion.strftime('%Y-%m-%d %H:%M:%S'),
                                                          'aCarreras': _aCarreras
                                                          }
                                        _aCoordinaciones.append(_aCoordinacion)
                            _eModalidad['aCoordinaciones'] = _aCoordinaciones
                            _aModalidades.append(_eModalidad)
                cache.set(f"cronograma_matricula_periodo_id_{id_periodo_login_matricula}", _aModalidades, TIEMPO_ENCACHE)
            aData = {'aModalidades': _aModalidades}
            return Helper_Response(isSuccess=True, data={'aCronograma': aData}, status=status.HTTP_200_OK)
        except Exception as ex:
            textoerror = '{} Linea:{}'.format(ex, sys.exc_info()[-1].tb_lineno)
            print(textoerror)
            return Helper_Response(isSuccess=False, data={}, message=f'{ex.__str__()}', status=status.HTTP_200_OK)

