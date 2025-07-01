# coding=utf-8
from datetime import datetime
from django.core.cache import cache
from django.db import transaction
from django.db.models import Q
from rest_framework.permissions import IsAuthenticated
from rest_framework.views import APIView
from rest_framework import status
from api.helpers.decorators import api_security
from api.helpers.response_herlper import Helper_Response
from api.serializers.alumno.actividadescomplementarias import PaeActividadesPeriodoAreasSerializer, PaeInscripcionActividadesSerializer, ComplementariaInscripcionSerializer, ComplementariaInscripcionSerializer_2
from api.serializers.alumno.miscitas import ProximaCitaSerializer
from sga.funciones import log, generar_nombre, convertir_fecha_invertida
from sga.models import Noticia, Inscripcion, PerfilUsuario, Matricula, PaeInscripcionActividades, PaeActividadesPeriodoAreas, InscripcionActividadesSolicitud
from med.models import ProximaCita
from sga.templatetags.sga_extras import encrypt


class ActividadesComplementariasAPIView(APIView):
    permission_classes = (IsAuthenticated,)
    api_key_module = 'ALUMNO_ACTV_COMPLEMENTARIAS'

    @api_security
    def post(self, request):
        if 'multipart/form-data' in request.content_type:
            eRequest = request._request.POST
            eFiles = request._request.FILES
        else:
            eRequest = request.data

        TIEMPO_ENCACHE = 60 * 15
        try:
            if not 'action' in eRequest:
                raise NameError(u'Parametro de acciòn no encontrado')

            action = eRequest['action']

            if action == 'solicitudeliminacion':
                with transaction.atomic():
                    try:
                        if not 'observacion' in eRequest:
                            raise NameError(u"Favor complete el campo de observación")

                        if not 'idEliminar' in eRequest:
                            raise NameError(u"No se encuentra el código de la inscripción.")

                        observacion = eRequest['observacion']
                        id = int(encrypt(eRequest['idEliminar']))
                        inscripcion = PaeInscripcionActividades.objects.get(status=True, pk=id)
                        if not InscripcionActividadesSolicitud.objects.filter(status=True, matricula=inscripcion.matricula, actividades=inscripcion.actividades).exists():
                            solicitud = InscripcionActividadesSolicitud(matricula=inscripcion.matricula,
                                                                        actividades=inscripcion.actividades,
                                                                        observacion=str(observacion))
                            solicitud.save(request)
                            log(u'Envio solicitud actividad complementaria: %s' % solicitud, request, "add")
                        else:
                            raise NameError(u"Ya envió solicitud.")


                        aData = {
                        }
                        return Helper_Response(isSuccess=True, data=aData, status=status.HTTP_200_OK)
                    except Exception as ex:
                        transaction.set_rollback(True)
                        return Helper_Response(isSuccess=False, data={}, message=f'Ocurrio un error: {ex.__str__()}', status=status.HTTP_200_OK)

            if action == 'archivoinscripcion':
                with transaction.atomic():
                    try:
                        if not 'fileDocumento' in eFiles:
                            raise NameError(u"Favor subir el archivo de la copia de cédula o pasaporte")
                        if not 'id' in eRequest:
                            raise NameError(u"No se encuentra el código de la inscripción.")
                        id = int(encrypt(eRequest['id']))
                        nfileDocumento = None
                        if 'fileDocumento' in eFiles:
                            nfileDocumento = eFiles['fileDocumento']
                            extensionDocumento = nfileDocumento._name.split('.')
                            tamDocumento = len(extensionDocumento)
                            exteDocumento = extensionDocumento[tamDocumento - 1]
                            if nfileDocumento.size > 1500000:
                                raise NameError(u"Error al cargar, el archivo es mayor a 15 Mb.")
                            if not exteDocumento.lower() == 'pdf':
                                raise NameError(u"Error al cargar, solo se permiten archivos .pdf")
                        nfileDocumento._name = generar_nombre("dp_documento", nfileDocumento._name)
                        participante = PaeInscripcionActividades.objects.get(pk=id)
                        participante.archivo=nfileDocumento
                        participante.save(request)
                        log(u'elimino actividad complementaria: %s' % participante, request, "del")
                        aData = {
                        }
                        return Helper_Response(isSuccess=True, data=aData, status=status.HTTP_200_OK)
                    except Exception as ex:
                        transaction.set_rollback(True)
                        return Helper_Response(isSuccess=False, data={}, message=f'Ocurrio un error: {ex.__str__()}', status=status.HTTP_200_OK)

            if action == 'addinscripcion':
                with transaction.atomic():
                    try:
                        payload = request.auth.payload
                        if not 'id' in request.data:
                            raise NameError(u"Parametro no encontrado")
                        idactividad = int(encrypt(request.data['id']))
                        eMatricula = None
                        if 'id' in payload['matricula']:
                            matriculaEnCache = cache.get(f"matricula_id_{payload['matricula']['id']}")
                            if matriculaEnCache:
                                eMatricula = matriculaEnCache
                            else:
                                eMatricula = Matricula.objects.get(pk=encrypt(payload['matricula']['id']))
                                cache.set(f"matricula_id_{payload['matricula']['id']}", eMatricula, TIEMPO_ENCACHE)

                        actividad = PaeActividadesPeriodoAreas.objects.get(pk=idactividad, status=True)
                        if not actividad.paeinscripcionactividades_set.values("id").filter(matricula=eMatricula, status=True).exists():
                            totalinscritos = actividad.paeinscripcionactividades_set.values("id").filter(status=True).count()
                            if totalinscritos >= actividad.cupo:
                                raise NameError(u'Lo sentimos, no hay cupo disponible.')
                            inscripcionactividad = PaeInscripcionActividades(matricula=eMatricula, actividades_id=idactividad)
                            inscripcionactividad.save(request)
                            log(u'Adiciono actividad complementaria: %s' % inscripcionactividad, request, "add")
                        else:
                            raise NameError(u'Lo sentimos, ya esta inscrito en esta actividad.')


                        aData = {
                        }
                        return Helper_Response(isSuccess=True, data=aData, status=status.HTTP_200_OK)
                    except Exception as ex:
                        transaction.set_rollback(True)
                        return Helper_Response(isSuccess=False, data={}, message=f'Ocurrio un error: {ex.__str__()}', status=status.HTTP_200_OK)

            return Helper_Response(isSuccess=False, data={}, message=f'Acciòn no encontrada', status=status.HTTP_200_OK)
        except Exception as ex:
            return Helper_Response(isSuccess=False, data={}, message=f'Ocurrio un error: {ex.__str__()}', status=status.HTTP_200_OK)

    @api_security
    def get(self, request):
        TIEMPO_ENCACHE = 60 * 15
        try:
            payload = request.auth.payload
            ePerfilUsuario = PerfilUsuario.objects.get(pk=encrypt(payload['perfilprincipal']['id']))
            if not ePerfilUsuario.es_estudiante():
                raise NameError(u'Solo los perfiles de estudiantes pueden ingresar al modulo.')
            if not 'id' in payload['matricula']:
                raise NameError(u'No se encuentra matriculado.')
            if payload['matricula']['id'] is None:
                raise NameError(u'No se encuentra matriculado.')

            eMatricula = None
            if 'id' in payload['matricula']:
                matriculaEnCache = cache.get(f"matricula_id_{payload['matricula']['id']}")
                if matriculaEnCache:
                    eMatricula = matriculaEnCache
                else:
                    eMatricula = Matricula.objects.get(pk=encrypt(payload['matricula']['id']))
                    cache.set(f"matricula_id_{payload['matricula']['id']}", eMatricula, TIEMPO_ENCACHE)

            eIncripcion = eMatricula.inscripcion
            inscripcion_serializer = ComplementariaInscripcionSerializer_2(eIncripcion)
            ePeriodo = eMatricula.nivel.periodo
            maximo_actextracurricular = ePeriodo.maximo_actextracurricular
            Seriaactividadesinscritas = PaeInscripcionActividades.objects.select_related().filter(matricula__inscripcion=eIncripcion, status=True, matricula__status=True).order_by('matricula__nivel__periodo__id')
            inscripciones = Seriaactividadesinscritas.filter(matricula=eMatricula, status=True)
            totalinscrito = inscripciones.count()
            totalinscritosalu = inscripciones.filter(actividades__general=False,matricula=eMatricula, status=True)
            Seriatotalinscritosalu= totalinscritosalu.count()

            PaeInscripcionActividades_serializer = PaeInscripcionActividadesSerializer(Seriaactividadesinscritas, many=True)

            hoy = datetime.now().date()
            mi_nivel = eMatricula.nivelmalla
            jornada = None
            if eMatricula:
                jornada = eMatricula.nivel
            actividades = PaeActividadesPeriodoAreas.objects.select_related().filter(((Q(
                nivelminimo__id__lte=mi_nivel.id) & Q(nivelmaximo__id__gte=mi_nivel.id)) | (Q(
                nivelminimo__isnull=True) & Q(nivelmaximo__isnull=True))) & Q(fechafin__gte=hoy) & Q(
                coordinacion=eIncripcion.coordinacion), Q(periodoarea__periodo=ePeriodo) & Q(status=True) & (Q(
                nivel__isnull=True) | Q(nivel=jornada)) & (Q(carrera__isnull=True) | Q(
                carrera=eIncripcion.carrera))).order_by('periodoarea__areas__nombre', 'coordinacion', 'nombre')
            if totalinscrito:
                actividades = actividades.exclude(pk__in=inscripciones.values('actividades_id'))

            Actividades_serializer = PaeActividadesPeriodoAreasSerializer(actividades, many=True)

            totalinscritosalu = inscripciones.filter(actividades__general=False, matricula=eMatricula, status=True)
            totalinscritosalu_count = totalinscritosalu.count()
            ePeriodo = eMatricula.nivel.periodo
            maximo_actextracurricular = ePeriodo.maximo_actextracurricular

            data = {
                'eInscripcion': inscripcion_serializer.data,
                'eActividadesComple': Actividades_serializer.data if actividades.exists() else [],
                'ePreInscripciones': PaeInscripcionActividades_serializer.data if Seriaactividadesinscritas.exists() else [],
                'totalinscritosalu': totalinscritosalu_count,
                'maximo_actextracurricular': maximo_actextracurricular

            }
            return Helper_Response(isSuccess=True, data=data, status=status.HTTP_200_OK)
        except Exception as ex:
            return Helper_Response(isSuccess=False, data={}, message=f'Ocurrio un error: {ex.__str__()}', status=status.HTTP_200_OK)
