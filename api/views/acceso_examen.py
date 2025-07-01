import json
import sys
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
from api.helpers.response_herlper import Helper_Response
from api.serializers.alumno.balconservicio import ProcesoSerializer, CategoriaSerializer, InformacionSerializer, SolicitudSerializer, HistorialSolicitudSerializer, EncuestaProcesoSerializer
from balcon.models import Proceso, Categoria, Informacion, ProcesoServicio, Solicitud, Agente, RequisitosSolicitud, HistorialSolicitud, RespuestaEncuestaSatisfaccion
from inno.models import MateriaAsignadaPlanificacionSedeVirtualExamen, TurnoPlanificacionSedeVirtualExamen, \
    AulaPlanificacionSedeVirtualExamen, FechaPlanificacionSedeVirtualExamen
from inno.serializers.AsistenciaExamen import MateriaAsignadaPlanificacionSedeVirtualExamenSerializer, \
    Persona2Serializer as PersonaSerializer, AulaPlanificacionSedeVirtualExamenSerializer, \
    TurnoPlanificacionSedeVirtualExamenSerializer, FechaPlanificacionSedeVirtualExamenSerializer, SedeVirtualSerializer, \
    LaboratorioVirtualSerializer
from settings import DEBUG
from sga.funciones import remover_caracteres_especiales_unicode, generar_nombre, log, notificacion
from sga.models import PerfilUsuario, Periodo, SedeVirtual


# from sga.templatetags.sga_extras import encrypt


class AccesoExamenAPIView(APIView):
    # permission_classes = (IsAuthenticated,)
    # api_key_module = 'ALUMNO_BALCON_SERVICIOS'

    # @api_security
    def get(self, request):
        action = request.query_params.get('action', None)
        if action is None:
            return JsonResponse({"result": False, "message": u"Acción no encontrada"})

        if action == 'validateCode':
            with transaction.atomic():
                try:
                    code = request.query_params.get('qr', None)
                    id = request.query_params.get('id', None)
                    if code is None:
                        raise NameError(u"Código no encontrado, contactarse con el administrador del sistema.")
                    if id is None:
                        raise NameError(u"Turno no encontrado, contactarse con el administrador del sistema.")
                    try:
                        eMateriaAsignadaPlanificacionSedeVirtualExamen = MateriaAsignadaPlanificacionSedeVirtualExamen.objects.get(codigo_qr=code)
                    except ObjectDoesNotExist:
                        raise NameError(u"Código inválido, acérquese a la mesa técnica.")
                    if not DEBUG:
                        if eMateriaAsignadaPlanificacionSedeVirtualExamen.asistencia:
                            fecha_asistencia = eMateriaAsignadaPlanificacionSedeVirtualExamen.fecha_asistencia
                            ePersona = PersonaSerializer(eMateriaAsignadaPlanificacionSedeVirtualExamen.materiaasignada.matricula.inscripcion.persona).data
                            return JsonResponse({"result": True, "acceso": False, "aData": ePersona, "message": f"Código QR fue utilizado el {fecha_asistencia.strftime('%Y-%m-%d %H:%M:%S')}."})
                    try:
                        eAulaPlanificacionSedeVirtualExamen = AulaPlanificacionSedeVirtualExamen.objects.get(pk=id)
                    except ObjectDoesNotExist:
                        ePersona = PersonaSerializer(eMateriaAsignadaPlanificacionSedeVirtualExamen.materiaasignada.matricula.inscripcion.persona).data
                        return JsonResponse({"result": True, "acceso": False, "aData": ePersona, "message": f"No se encontro turno valido, contactarse con el administrador del sistema."})
                    eTurnoPlanificacionSedeVirtualExamen = eAulaPlanificacionSedeVirtualExamen.turnoplanificacion
                    if eMateriaAsignadaPlanificacionSedeVirtualExamen.aulaplanificacion.turnoplanificacion.fechaplanificacion.sede_id != eTurnoPlanificacionSedeVirtualExamen.fechaplanificacion.sede_id:
                        ePersona = PersonaSerializer(eMateriaAsignadaPlanificacionSedeVirtualExamen.materiaasignada.matricula.inscripcion.persona).data
                        return JsonResponse({"result": True, "acceso": False, "aData": ePersona, "message": f"Su sede no corresponde a la ubicación actual, acérquese a la mesa técnica."})
                    if eMateriaAsignadaPlanificacionSedeVirtualExamen.aulaplanificacion.turnoplanificacion_id != eTurnoPlanificacionSedeVirtualExamen.pk:
                        ePersona = PersonaSerializer(eMateriaAsignadaPlanificacionSedeVirtualExamen.materiaasignada.matricula.inscripcion.persona).data
                        return JsonResponse({"result": True, "acceso": False, "aData": ePersona, "message": f"Aún no le corresponde ingresar, espere su fecha y hora que corresponde"})

                    epassword = eMateriaAsignadaPlanificacionSedeVirtualExamen.create_update_password()
                    MateriaAsignadaPlanificacionSedeVirtualExamen.objects.filter(pk=eMateriaAsignadaPlanificacionSedeVirtualExamen.id).update(asistencia=True, fecha_asistencia=datetime.now(), password=epassword)
                    # eMateriaAsignadaPlanificacionSedeVirtualExamen.asistencia = True
                    # eMateriaAsignadaPlanificacionSedeVirtualExamen.fecha_asistencia = datetime.now()
                    # eMateriaAsignadaPlanificacionSedeVirtualExamen.save(request)
                    ePersona = PersonaSerializer(eMateriaAsignadaPlanificacionSedeVirtualExamen.materiaasignada.matricula.inscripcion.persona).data
                    return JsonResponse({"result": True, "acceso": True, "aData": ePersona, "message": f"Acceso permitido"})
                except Exception as ex:
                    transaction.set_rollback(True)
                    print('Error on line {}'.format(sys.exc_info()[-1].tb_lineno))
                    return JsonResponse({"result": False, "aData": {}, "message": ex.__str__()})

        elif action == 'listPlaces':
            with transaction.atomic():
                try:
                    # ENVIAR ID DEL PERIODO 177
                    idp = request.query_params.get('idp', None)
                    if idp is None:
                        raise NameError(u"Parametro de periodo no encontrado, contactarse con el administrador del sistema.")
                    try:
                        ePeriodo = Periodo.objects.get(pk=idp)
                    except ObjectDoesNotExist:
                        raise NameError(u"Periodo no encontrado.")
                    eAulaPlanificacionSedeVirtualExamen = AulaPlanificacionSedeVirtualExamen.objects.filter(turnoplanificacion__fechaplanificacion__periodo=ePeriodo, status=True)
                    eSedes = SedeVirtual.objects.filter(status=True, pk__in=eAulaPlanificacionSedeVirtualExamen.values_list('turnoplanificacion__fechaplanificacion__sede_id', flat=True))
                    context = {
                        'exclude_fields': [
                            'id', 'display', 'imagen', 'referencias', 'usuario_creacion_id', 'usuario_modificacion_id', 'status',
                            'fecha_creacion', 'fecha_modificacion', 'activa', 'principal', 'foto', 'latitud', 'longitud'
                        ]
                    }
                    eSedes = SedeVirtualSerializer(eSedes, many=True, context=context).data if eSedes.values("id").exists() else []
                    return JsonResponse({"result": True, "aData": eSedes, "message": f""})
                except Exception as ex:
                    transaction.set_rollback(True)
                    print('Error on line {}'.format(sys.exc_info()[-1].tb_lineno))
                    return JsonResponse({"result": False, "aData": {}, "message": ex.__str__()})

        elif action == 'listDates':
            with transaction.atomic():
                try:
                    # ENVIAR ID DE SEDE
                    ids = request.query_params.get('ids', None)
                    if ids is None:
                        raise NameError(u"Parametro de sede no encontrado, contactarse con el administrador del sistema.")
                    try:
                        eSedeVirtual = SedeVirtual.objects.get(pk=ids)
                    except ObjectDoesNotExist:
                        raise NameError(u"Sede virtual no encontrado.")
                    idp = request.query_params.get('idp', None)
                    if idp is None:
                        raise NameError(u"Parametro de periodo no encontrado, contactarse con el administrador del sistema.")
                    try:
                        ePeriodo = Periodo.objects.get(pk=idp)
                    except ObjectDoesNotExist:
                        raise NameError(u"Periodo no encontrado.")
                    eFechaPlanificacionSedeVirtualExamenes = eSedeVirtual.get_fechaplanificacion(periodo=ePeriodo)
                    context = {
                        'exclude_fields': [
                            'id', 'display', 'usuario_creacion_id', 'usuario_modificacion_id', 'status',
                            'fecha_creacion', 'fecha_modificacion', 'periodo', 'supervisor', 'sede'
                        ]
                    }
                    eFechaPlanificacionSedeVirtualExamenes = FechaPlanificacionSedeVirtualExamenSerializer(eFechaPlanificacionSedeVirtualExamenes, context=context, many=True).data if len(eFechaPlanificacionSedeVirtualExamenes) else []
                    return JsonResponse({"result": True, "aData": eFechaPlanificacionSedeVirtualExamenes, "message": f""})
                except Exception as ex:
                    transaction.set_rollback(True)
                    print('Error on line {}'.format(sys.exc_info()[-1].tb_lineno))
                    return JsonResponse({"result": False, "aData": {}, "message": ex.__str__()})

        elif action == 'listHours':
            with transaction.atomic():
                try:
                    # ENVIAR ID DE FECHA
                    idf = request.query_params.get('idf', None)
                    if idf is None:
                        raise NameError(u"Parametro de fecha no encontrado, contactarse con el administrador del sistema.")
                    try:
                        eFechaPlanificacionSedeVirtualExamen = FechaPlanificacionSedeVirtualExamen.objects.get(pk=idf)
                    except ObjectDoesNotExist:
                        raise NameError(u"Fecha no encontrado.")
                    eTurnoPlanificacionSedeVirtualExamenes = eFechaPlanificacionSedeVirtualExamen.get_horasplanificadas()
                    context = {
                        'exclude_fields': [
                            'id', 'display', 'usuario_creacion_id', 'usuario_modificacion_id', 'status',
                            'fecha_creacion', 'fecha_modificacion', 'fechaplanificacion'
                        ]
                    }
                    eTurnoPlanificacionSedeVirtualExamenes = TurnoPlanificacionSedeVirtualExamenSerializer(eTurnoPlanificacionSedeVirtualExamenes, context=context, many=True).data if len(eTurnoPlanificacionSedeVirtualExamenes) else []
                    return JsonResponse({"result": True, "aData": eTurnoPlanificacionSedeVirtualExamenes, "message": f""})
                except Exception as ex:
                    transaction.set_rollback(True)
                    print('Error on line {}'.format(sys.exc_info()[-1].tb_lineno))
                    return JsonResponse({"result": False, "aData": {}, "message": ex.__str__()})

        elif action == 'listBlocks':
            with transaction.atomic():
                try:
                    # ENVIAR ID DE FECHA
                    idh = request.query_params.get('idh', None)
                    if idh is None:
                        raise NameError(u"Parametro de turno no encontrado, contactarse con el administrador del sistema.")
                    try:
                        eTurnoPlanificacionSedeVirtualExamen = TurnoPlanificacionSedeVirtualExamen.objects.get(pk=idh)
                    except ObjectDoesNotExist:
                        raise NameError(u"Fecha no encontrado.")
                    context = {
                        'exclude_fields': [
                            'id', 'display', 'usuario_creacion_id', 'usuario_modificacion_id', 'status',
                            'fecha_creacion', 'fecha_modificacion', 'fechaplanificacion', 'turnoplanificacion',
                            'sedevirtual', 'responsable', 'supervisor', 'password',
                            'fecha_registrohabilitacion', 'token', 'aula'
                        ]
                    }
                    eAulaPlanificacionSedeVirtualExamenes = []
                    for eAulaPlanificacionSedeVirtualExamen in AulaPlanificacionSedeVirtualExamen.objects.filter(turnoplanificacion=eTurnoPlanificacionSedeVirtualExamen, status=True):
                        eAulaPlanificacionSedeVirtualExamenSerializer = AulaPlanificacionSedeVirtualExamenSerializer(eAulaPlanificacionSedeVirtualExamen, context=context).data
                        eLaboratorioVirtual = eAulaPlanificacionSedeVirtualExamen.aula
                        # eLaboratorioVirtual = LaboratorioVirtualSerializer(eAulaPlanificacionSedeVirtualExamen.aula, context={'exclude_fields': [
                        #     'id', 'display', 'usuario_creacion_id', 'usuario_modificacion_id', 'status',
                        #     'fecha_creacion', 'fecha_modificacion', 'sedevirtual', 'tipo', 'capacidad',
                        #     'bloque', 'activo'
                        # ]}).data
                        eAulaPlanificacionSedeVirtualExamenSerializer.__setitem__('nombre', eLaboratorioVirtual.nombre)
                        eAulaPlanificacionSedeVirtualExamenes.append(eAulaPlanificacionSedeVirtualExamenSerializer)
                    return JsonResponse({"result": True, "aData": eAulaPlanificacionSedeVirtualExamenes, "message": f""})
                except Exception as ex:
                    transaction.set_rollback(True)
                    print('Error on line {}'.format(sys.exc_info()[-1].tb_lineno))
                    return JsonResponse({"result": False, "aData": {}, "message": ex.__str__()})
