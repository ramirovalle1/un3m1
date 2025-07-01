import json
from datetime import datetime

from django.core.cache import cache
from django.db import transaction
from django.db.models import Q

from rest_framework.permissions import IsAuthenticated
from rest_framework.views import APIView
from rest_framework import status

from api.helpers.decorators import api_security
from api.helpers.response_herlper import Helper_Response
from api.serializers.alumno.feria import SolicitudFeriaSerializer, CronogramaFeriaSerializer, TutorSerializer, MatriculaSerializer, InscripcionSerializer
from sga.funciones import log, variable_valor
from sga.templatetags.sga_extras import encrypt
from feria.models import SolicitudFeria, ParticipanteFeria, CronogramaFeria, SolicitudFeriaHistorial
from sga.models import PerfilUsuario, Profesor, ProfesorMateria, Matricula, Inscripcion, CUENTAS_CORREOS
from sga.tasks import send_html_mail


class FeriasAPIView(APIView):
    permission_classes = (IsAuthenticated,)

    api_key_module = 'ALUMNO_FERIA'

    @api_security
    def post(self, request):
        urlepunemi = 'https://sagest.epunemi.gob.ec/'
        if 'multipart/form-data' in request.content_type:
            eRequest = request._request.POST
            eFiles = request._request.FILES
        else:
            eRequest = request.data

        action = eRequest['action']
        try:
            if not 'action' in eRequest:
                raise NameError(u'Parametro de acciòn no encontrado')

            if action == 'saveSolicitudFeria':
                with transaction.atomic():
                    try:
                        hoy = datetime.now()
                        payload = request.auth.payload
                        ePerfilUsuario = PerfilUsuario.objects.get(id=int(encrypt(payload['perfilprincipal']['id'])))

                        if not ePerfilUsuario.es_estudiante():
                            raise NameError(u'Solo los perfiles de estudiantes pueden ingresar al modulo.')

                        eIncripcion = ePerfilUsuario.inscripcion
                        # eSolicitudFeria = None
                        id = eRequest['id'] if eRequest['id'] != '' else None
                        if not 'eFilePropuesta' in eFiles:
                            raise NameError("Debe subir una presentacion propuesta")
                        newfile = eFiles['eFilePropuesta']
                        ext = newfile._name.split('.')[-1]
                        if not ext in ['pdf']:
                            raise NameError("El documento no es formato pdf.")
                        newfile._name = f"presen_propuesta_{hoy.year}{hoy.month}{hoy.day}{hoy.hour}{hoy.minute}{hoy.second}.{ext}"
                        if eRequest['id'] != '':
                            eSolicitudFeria = SolicitudFeria.objects.filter(pk=int(encrypt(id))).first()
                            if eSolicitudFeria is None:
                                raise NameError(u'No existe solicitud a  Modificar')
                            if eSolicitudFeria is None:
                                raise NameError(u'No existe solicitud a  Modificar')
                            eSolicitudFeria.cronograma_id = int(encrypt(eRequest['eCronogramaFeria']))
                            eSolicitudFeria.tutor_id = int(encrypt(eRequest['eTutor']))
                            eSolicitudFeria.titulo = eRequest['titulo']
                            eSolicitudFeria.resumen = eRequest['resumen']
                            eSolicitudFeria.objetivogeneral = eRequest['objetivogeneral']
                            eSolicitudFeria.objetivoespecifico = eRequest['objetivoespecifico']
                            eSolicitudFeria.materiales = eRequest['materiales']
                            eSolicitudFeria.resultados = eRequest['resultados']
                            if 'eFilePropuesta' in eFiles:
                                eSolicitudFeria.docpresentacionpropuesta = newfile
                            eSolicitudFeria.save(request)
                            if 'participantes' in eRequest:
                                participantes = json.loads(eRequest['participantes'])
                                for participante in participantes:
                                    eInscripcion = Inscripcion.objects.filter(pk=participante).first()
                                    eMatricula = eInscripcion.ultima_matricula()
                                    eParticipanteFeria = eSolicitudFeria.participanteferia_set.filter(inscripcion_id=eInscripcion.id).first()
                                    if eParticipanteFeria is None:
                                        eParticipanteFeria = ParticipanteFeria(solicitud=eSolicitudFeria, matricula=eMatricula, inscripcion_id=eInscripcion.id)
                                        eParticipanteFeria.save(request)
                                        log(u'Adiciono  participante feria: %s' % eParticipanteFeria, request, "add")
                                    else:
                                        rParticipante = eSolicitudFeria.participanteferia_set.filter(inscripcion_id=eInscripcion.id, status=False).first()
                                        if rParticipante is not None:
                                            rParticipante.status = True
                                            rParticipante.save(request)
                                            log(u'Adiciono  participante feria: %s' % rParticipante, request, "add")
                                eParticipantesDelete = eSolicitudFeria.participanteferia_set.exclude(inscripcion_id__in=participantes, status=True)
                                for eParticipanteFeria in eParticipantesDelete:
                                    eParticipanteFeria.status = False
                                    eParticipanteFeria.save(request)
                                    log(u'Elimino participante  %s  de solicitud feria: %s' % (eParticipanteFeria, eParticipanteFeria.solicitud), request, "del")
                                eSolicitudFeriaHistorial = SolicitudFeriaHistorial(solicitud=eSolicitudFeria, observacion='Edito solicitud feria: %s' % (eSolicitudFeria), estado=eSolicitudFeria.estado)
                                eSolicitudFeriaHistorial.save(request)
                                log(u'Edito solicitud feria: %s' % eSolicitudFeria, request, "edit")
                        else:
                            # eSolicitudesFerias = SolicitudFeria.objects.filter(cronograma_id=int(encrypt(eRequest['cronograma_id'])),
                            #                                                    estado__in=[1, 2],
                            #                                                    status=True).distinct()
                            # if eSolicitudesFerias.filter(usuario_creacion=payload['user_id']).values('id').exists():
                            #     raise NameError(u'Existe una solicitud en el cronograma seleccionado')
                            # eSolicitudesFerias = eSolicitudesFerias.filter(participanteferia__matricula__inscripcion__persona__usuario_id=payload['user_id'], status=True).distinct()
                            # if eSolicitudesFerias.values('id').exists():
                            #     raise NameError(u'Se encuentra participando en otra  solicitud en el cronograma seleccionado')
                            eSolicitudFeria = SolicitudFeria(
                                cronograma_id=int(encrypt(eRequest['eCronogramaFeria'])),
                                tutor_id=int(encrypt(eRequest['eTutor'])),
                                titulo=eRequest['titulo'],
                                resumen=eRequest['resumen'],
                                objetivogeneral=eRequest['objetivogeneral'],
                                objetivoespecifico=eRequest['objetivoespecifico'],
                                materiales=eRequest['materiales'],
                                resultados=eRequest['resultados'],
                                docpresentacionpropuesta = newfile,
                            )
                            eSolicitudFeria.save(request)
                            if 'participantes' in eRequest:
                                participantes = json.loads(eRequest['participantes'])

                                for participante in participantes:
                                    eIncripcion = Inscripcion.objects.get(pk=participante)
                                    eMaticula = eIncripcion.ultima_matricula()
                                    eParticipanteFeria = ParticipanteFeria(solicitud=eSolicitudFeria, matricula=eMaticula, inscripcion_id=eIncripcion.id)
                                    eParticipanteFeria.save(request)
                                    log(u'Adiciono  participante feria: %s' % eParticipanteFeria, request, "add")
                            eSolicitudFeriaHistorial = SolicitudFeriaHistorial(solicitud=eSolicitudFeria, observacion='Adiciono solicitud feria: %s'%(eSolicitudFeria), estado=eSolicitudFeria.estado)
                            eSolicitudFeriaHistorial.save(request)
                            log(u'Adiciono solicitud feria: %s' % eSolicitudFeria, request, "add")
                        # if eSolicitudFeria is not None:
                            tituloemail = "Notificación Tutor - Feria FACI"
                            aTutor = Profesor.objects.filter(status = True, id=int(encrypt(eRequest['eTutor']))).first()
                            aParticipante = eSolicitudFeria.participanteferia_set.filter(matricula__inscripcion__persona__usuario_id=eSolicitudFeria.usuario_creacion_id).first()
                            send_html_mail(tituloemail,
                                           "emails/feria_notificacion_tutor_solicitud.html",
                                           {'sistema': u'SGA',
                                            'saludo': 'Estimada' if aTutor.persona.sexo.id == 1 else 'Estimado',
                                            'solicitud': eSolicitudFeria,
                                            'participante': aParticipante,
                                            'tutor': aTutor
                                            },
                                           aTutor.persona.lista_emails_envio_2(),
                                           # ['isaltosm@unemi.edu.ec'],
                                           [],
                                           cuenta=CUENTAS_CORREOS[0][1]
                                           )
                        aData = {}
                        return Helper_Response(isSuccess=True, data=aData, status=status.HTTP_200_OK)
                    except Exception as ex:
                        transaction.set_rollback(True)
                        return Helper_Response(isSuccess=False, data={}, message=f'Ocurrio un error al guardar: {ex.__str__()}', status=status.HTTP_200_OK)

            if action == 'DeleteSolicitudFeria':
                with transaction.atomic():
                    try:
                        hoy = datetime.now()
                        payload = request.auth.payload
                        ePerfilUsuario = PerfilUsuario.objects.get(id=int(encrypt(payload['perfilprincipal']['id'])))
                        if not ePerfilUsuario.es_estudiante():
                            raise NameError(u'Solo los perfiles de estudiantes pueden ingresar al modulo.')
                        if not 'id' in eRequest:
                            raise NameError(u"No se encontro registro a eliminar")
                        eIncripcion = ePerfilUsuario.inscripcion
                        id = int(encrypt(eRequest['id']))
                        eSolicitudFeria = SolicitudFeria.objects.filter(pk=id).first()
                        if eSolicitudFeria is None:
                            raise NameError(u"No se encontro registro a eliminar")
                        eSolicitudFeria.status = False
                        eSolicitudFeria.save(request)
                        eParticipantes = eSolicitudFeria.participanteferia_set.all()
                        for eParticipante in eParticipantes:
                            eParticipante.status = False
                            eParticipante.save(request)
                            log(u'Elimino participante  %s  de solicitud feria: %s' % (eParticipante, eSolicitudFeria), request, "del")
                        log(u'Elimino solicitud feria: %s' % eSolicitudFeria, request, "del")
                        aData = {}
                        return Helper_Response(isSuccess=True, data=aData, status=status.HTTP_200_OK)
                    except Exception as ex:
                        transaction.set_rollback(True)
                        return Helper_Response(isSuccess=False, data={}, message=f'Ocurrio un error: {ex.__str__()}', status=status.HTTP_200_OK)

            if action == 'generaractacompromiso':
                try:
                    payload = request.auth.payload
                    if not 'id' in payload['matricula']:
                        raise NameError('Parametro matricula no encontrado')
                    eMatricula = Matricula.objects.get(pk=encrypt(payload['matricula']['id']))
                    valido , msg = eMatricula.generar_actacompromiso_matricula_pregrado(request=request)
                    if not valido:
                        raise NameError(msg)

                    aData = {
                        'ruta': msg
                    }
                    return Helper_Response(isSuccess=True, data=aData, status=status.HTTP_200_OK)
                except Exception as ex:
                    return Helper_Response(isSuccess=False, data={}, message=f'Ocurrio un error: {ex.__str__()}', status=status.HTTP_200_OK)

            if action == 'consultarcronogramamaxmin':
                try:
                    id = int(encrypt(eRequest['id']))
                    aCronograma = CronogramaFeria.objects.filter(status=True,id=id).first()
                    aData = {
                        'minParticipantes': aCronograma.minparticipantes if aCronograma else None,
                        'maxParticipantes': aCronograma.maxparticipantes if aCronograma else None
                    }
                    return Helper_Response(isSuccess=True, data=aData, status=status.HTTP_200_OK)
                except Exception as ex:
                    return Helper_Response(isSuccess=False, data={}, message=f'Ocurrio un error: {ex.__str__()}', status=status.HTTP_200_OK)

            return Helper_Response(isSuccess=False, data={}, message=f'Acción no encontrada', status=status.HTTP_200_OK)
        except Exception as ex:
            return Helper_Response(isSuccess=False, data={}, message=f'Ocurrio un error: {ex.__str__()}', status=status.HTTP_200_OK)


    @api_security
    def get(self, request):
        TIEMPO_ENCACHE = 60 * 60 * 60
        try:
            action = ''
            if 'action' in request.query_params:
                action = request.query_params['action']

            # if action == 'LoadFormSolicitudFeria':
            #     try:
            #         hoy = datetime.now()
            #         payload = request.auth.payload
            #         ePerfilUsuario = PerfilUsuario.objects.get(id=int(encrypt(payload['perfilprincipal']['id'])))
            #         if not ePerfilUsuario.es_estudiante():
            #             raise NameError(u'Solo los perfiles de estudiantes pueden ingresar al modulo.')
            #         if not 'id' in payload['matricula']:
            #             raise NameError(u'No se encuentra matriculado.')
            #         eMatricula = Matricula.objects.get(pk=int(encrypt(payload['matricula']['id'])))
            #         ePeriodo = eMatricula.nivel.periodo
            #         eIncripcion = ePerfilUsuario.inscripcion
            #         id = request.query_params.get('id')
            #         eSolicitudFeria = None
            #
            #         eCronogramasFerias = CronogramaFeria.objects.filter(carreras__id=eIncripcion.carrera_id,
            #                                                             fechainicioinscripcion__lte=hoy,
            #                                                             fechafininscripcion__gte=hoy, status=True)
            #
            #         idcarrs = list(eCronogramasFerias.values_list('carreras__id', flat=True))
            #         eMatriculas = None
            #         eMatriculas = Matricula.objects.filter(pk=eMatricula.id)
            #         if id:
            #             eSolicitudFeria = SolicitudFeria.objects.get(id=int(encrypt(id)))
            #             eCronogramasFerias = CronogramaFeria.objects.filter(carreras__id=eIncripcion.carrera_id, status=True)
            #             eMatriculas = eSolicitudFeria.get_participantes()
            #             idcarrs = list(CronogramaFeria.objects.filter(carreras__id=eIncripcion.carrera_id).values_list('carreras__id', flat=True))
            #
            #         ids_tutores = ProfesorMateria.objects.values_list('profesor_id', flat=True)\
            #             .filter(materia__nivel__periodo_id=ePeriodo.id,
            #                     #tipoprofesor_id=14,#Profesores tutores
            #                     materia__asignaturamalla__malla__carrera_id__in=idcarrs,
            #                     status=True).distinct('profesor_id')
            #         eTutores = Profesor.objects.filter(pk__in=ids_tutores, status=True)
            #         eTutores_serializer = TutorSerializer(eTutores, many=True)
            #         eCronogramasFerias__serializer = CronogramaFeriaSerializer(eCronogramasFerias, many=True)
            #         aData = {
            #             'eCronogramasFerias': eCronogramasFerias__serializer.data if eCronogramasFerias.values("id").exists() else [],
            #             'eTutores': eTutores_serializer.data if eTutores.values("id").exists() else [],
            #             'id': encrypt(eSolicitudFeria.id) if eSolicitudFeria is not None else '',
            #             'eParticipantes': MatriculaSerializer(eMatriculas, many=True).data if eMatriculas is not None else [],
            #             'eSolicitudFeria': SolicitudFeriaSerializer(eSolicitudFeria).data if eSolicitudFeria is not None else [],
            #             'id_matricula': payload['matricula']['id']
            #         }
            #         return Helper_Response(isSuccess=True, data=aData, status=status.HTTP_200_OK)
            #     except Exception as ex:
            #         #transaction.set_rollback(True)
            #         return Helper_Response(isSuccess=False, data={}, message=f'Ocurrio un error al diferir: {ex.__str__()}', status=status.HTTP_200_OK)
            #
            # elif action == 'SearchParticipantes':
            #         try:
            #             hoy = datetime.now()
            #             eRequest = request._request.GET
            #             payload = request.auth.payload
            #             ePerfilUsuario = PerfilUsuario.objects.get(id=int(encrypt(payload['perfilprincipal']['id'])))
            #             if not ePerfilUsuario.es_estudiante():
            #                 raise NameError(u'Solo los perfiles de estudiantes pueden ingresar al modulo.')
            #             if not 'id' in payload['matricula']:
            #                 raise NameError(u'No se encuentra matriculado.')
            #             eMatricula = Matricula.objects.get(pk=int(encrypt(payload['matricula']['id'])))
            #             ePeriodo = eMatricula.nivel.periodo
            #             eIncripcion = ePerfilUsuario.inscripcion
            #             search = eRequest['search']
            #             idms_excluir = json.loads(eRequest['participantes_excluir'])
            #             cronograma_id = int(encrypt(eRequest['cronograma_id']))
            #             eMatriculas = Matricula.objects.filter(#inscripcion__carrera_:id=eIncripcion.carrera_id,
            #                                                    #inscripcion__inscripcionnivel__nivel__orden__gte=4,
            #                                                    nivel__periodo_id=ePeriodo.id,
            #                                                    status=True)
            #             # if cronograma_id:
            #             #     eCronogramaFeria = CronogramaFeria.objects.get(pk=cronograma_id)
            #             #     idqms_excluir = ParticipanteFeria.objects.values_list('matricula_id', flat=True).filter(solicitud__cronograma_id=eCronogramaFeria.pk,
            #             #                                                                                             solicitud__estado__in=[1, 2], status=True)
            #             #     idms_excluir.extend(list(idqms_excluir))
            #             #     eMatriculas = eMatriculas.filter(inscripcion__carrera__in=eCronogramaFeria.carreras.all())
            #
            #             if search:
            #                 ss = search.split(' ')
            #                 if len(ss) == 1:
            #                     eMatriculas = eMatriculas.filter(Q(inscripcion__persona__usuario__username__icontains=search) |
            #                                                      Q(inscripcion__persona__cedula__icontains=search) |
            #                                                      Q(inscripcion__persona__pasaporte__icontains=search) |
            #                                                      Q(inscripcion__persona__nombres__icontains=search) |
            #                                                      Q(inscripcion__persona__apellido1__icontains=search) |
            #                                                      Q(inscripcion__persona__apellido2__icontains=search))
            #                 else:
            #                     eMatriculas = eMatriculas.filter(Q(inscripcion__persona__nombres__icontains=search) |
            #                                                      Q(inscripcion__persona__apellido1__icontains=ss[0]) &
            #                                                      Q(inscripcion__persona__apellido2__icontains=ss[1]))
            #             if len(idms_excluir) > 0:
            #                 eMatriculas = eMatriculas.exclude(pk__in=idms_excluir)
            #
            #             eMatriculas = eMatriculas[:5]
            #             eMatriculas_serializer = MatriculaSerializer(eMatriculas, many=True)
            #             aData = {
            #                 'eParticipantesSearh': eMatriculas_serializer.data if eMatriculas.values('id').exists() else []
            #             }
            #             return Helper_Response(isSuccess=True, data=aData, status=status.HTTP_200_OK)
            #         except Exception as ex:
            #             # transaction.set_rollback(True)
            #             return Helper_Response(isSuccess=False, data={}, message=f'Ocurrio un error al diferir: {ex.__str__()}', status=status.HTTP_200_OK)

            if action == 'LoadFormSolicitudFeria':
                try:
                    hoy = datetime.now()
                    payload = request.auth.payload
                    ePerfilUsuario = PerfilUsuario.objects.get(id=int(encrypt(payload['perfilprincipal']['id'])))
                    if not ePerfilUsuario.es_estudiante():
                        raise NameError(u'Solo los perfiles de estudiantes pueden ingresar al modulo.')
                    if not 'id' in payload['matricula']:
                        raise NameError(u'No se encuentra matriculado.')
                    eMatricula = Matricula.objects.get(pk=int(encrypt(payload['matricula']['id'])))
                    ePeriodo = eMatricula.nivel.periodo
                    eInscripcion = ePerfilUsuario.inscripcion
                    id = request.query_params.get('id')
                    eSolicitudFeria = None

                    eCronogramasFerias = CronogramaFeria.objects.filter(carreras__id=eInscripcion.carrera_id,
                                                                        fechainicioinscripcion__lte=hoy,
                                                                        fechafininscripcion__gte=hoy, status=True)

                    idcarrs = list(eCronogramasFerias.values_list('carreras__id', flat=True))
                    eMatriculas = None
                    eInscripciones = Inscripcion.objects.filter(pk=eInscripcion.id)
                    if id:
                        eSolicitudFeria = SolicitudFeria.objects.get(id=int(encrypt(id)))
                        eCronogramasFerias = CronogramaFeria.objects.filter(carreras__id=eInscripcion.carrera_id, status=True)
                        eInscripciones = eSolicitudFeria.get_participantes_inscripciones()
                        idcarrs = list(CronogramaFeria.objects.filter(carreras__id=eInscripcion.carrera_id).values_list('carreras__id', flat=True))

                    ids_tutores = ProfesorMateria.objects.values_list('profesor_id', flat=True)\
                        .filter(materia__nivel__periodo_id=ePeriodo.id,
                                #tipoprofesor_id=14,#Profesores tutores
                                materia__asignaturamalla__malla__carrera_id__in=idcarrs,
                                status=True).distinct('profesor_id')
                    eTutores = Profesor.objects.filter(pk__in=ids_tutores, status=True)
                    eTutores_serializer = TutorSerializer(eTutores, many=True)
                    eCronogramasFerias__serializer = CronogramaFeriaSerializer(eCronogramasFerias, many=True)
                    aData = {
                        'eCronogramasFerias': eCronogramasFerias__serializer.data if eCronogramasFerias.values("id").exists() else [],
                        'eTutores': eTutores_serializer.data if eTutores.values("id").exists() else [],
                        'id': encrypt(eSolicitudFeria.id) if eSolicitudFeria is not None else '',
                        'eParticipantes': InscripcionSerializer(eInscripciones, many=True).data if eInscripciones.values("id").exists() else [],
                        'eSolicitudFeria': SolicitudFeriaSerializer(eSolicitudFeria).data if eSolicitudFeria is not None else [],
                        'id_inscripcion': payload['inscripcion']['id']
                    }
                    return Helper_Response(isSuccess=True, data=aData, status=status.HTTP_200_OK)
                except Exception as ex:
                    #transaction.set_rollback(True)
                    return Helper_Response(isSuccess=False, data={}, message=f'Ocurrio un error al diferir: {ex.__str__()}', status=status.HTTP_200_OK)

            elif action == 'SearchParticipantes':
                    try:
                        hoy = datetime.now()
                        eRequest = request._request.GET
                        payload = request.auth.payload
                        ePerfilUsuario = PerfilUsuario.objects.get(id=int(encrypt(payload['perfilprincipal']['id'])))
                        if not ePerfilUsuario.es_estudiante():
                            raise NameError(u'Solo los perfiles de estudiantes pueden ingresar al modulo.')
                        if not 'id' in payload['matricula']:
                            raise NameError(u'No se encuentra matriculado.')
                        eMatricula = Matricula.objects.get(pk=int(encrypt(payload['matricula']['id'])))
                        ePeriodo = eMatricula.nivel.periodo
                        eIncripcion = ePerfilUsuario.inscripcion
                        search = eRequest['search']
                        idms_excluir = json.loads(eRequest['participantes_excluir'])
                        cronograma_id = int(encrypt(eRequest['cronograma_id']))
                        participantesExcluir = ParticipanteFeria.objects.values_list('inscripcion_id', flat=True).filter(solicitud__cronograma_id=cronograma_id, status=True).distinct()
                        eInscripciones = Inscripcion.objects.filter(status=True,
                                                                    activo=True,
                                                                    perfilusuario__visible=True,
                                                                    perfilusuario__status=True,
                                                                    coordinacion_id=4).distinct()

                        if search:
                            ss = search.split(' ')
                            if len(ss) == 1:
                                eInscripciones = eInscripciones.filter(Q(persona__usuario__username__icontains=search) |
                                                                 Q(persona__cedula__icontains=search) |
                                                                 Q(persona__pasaporte__icontains=search) |
                                                                 Q(persona__nombres__icontains=search) |
                                                                 Q(persona__apellido1__icontains=search) |
                                                                 Q(persona__apellido2__icontains=search))
                            else:
                                eInscripciones = eInscripciones.filter(Q(persona__nombres__icontains=search) |
                                                                 Q(persona__apellido1__icontains=ss[0]) &
                                                                 Q(persona__apellido2__icontains=ss[1]))
                        if len(idms_excluir) > 0:
                            eInscripciones = eInscripciones.exclude(pk__in=idms_excluir)

                        # if len(participantesExcluir) > 0:
                        #     eInscripciones = eInscripciones.exclude(pk__in=participantesExcluir)

                        eInscripciones = eInscripciones[:5]
                        eInscripcione_serializer = InscripcionSerializer(eInscripciones, many=True)
                        aData = {
                            'eParticipantesSearh': eInscripcione_serializer.data if eInscripciones.values('id').exists() else []
                        }
                        return Helper_Response(isSuccess=True, data=aData, status=status.HTTP_200_OK)
                    except Exception as ex:
                        # transaction.set_rollback(True)
                        return Helper_Response(isSuccess=False, data={}, message=f'Ocurrio un error al diferir: {ex.__str__()}', status=status.HTTP_200_OK)
            else:
                try:
                    hoy = datetime.now()
                    payload = request.auth.payload
                    ePerfilUsuario = PerfilUsuario.objects.get(id=int(encrypt(payload['perfilprincipal']['id'])))
                    eVariableChartBotEnCache = cache.get('HABILITAR_CHATBOT')
                    if eVariableChartBotEnCache is not None:
                        habilitar_chatbot = eVariableChartBotEnCache
                    else:
                        variable_name = 'HABILITAR_CHATBOT'
                        habilitar_chatbot = variable_valor(variable_name)
                        cache.set(variable_name, habilitar_chatbot, TIEMPO_ENCACHE)

                    if not ePerfilUsuario.es_estudiante():
                        raise NameError(u'Solo los perfiles de estudiantes pueden ingresar al modulo.')
                    if not 'id' in payload['matricula']:
                        raise NameError(u'No se encuentra matriculado.')

                    eInscripcion = ePerfilUsuario.inscripcion
                    ePersona = eInscripcion.persona
                    usuario_id = ePersona.usuario_id
                    qCronogramas = CronogramaFeria.objects.filter(carreras__id=eInscripcion.carrera.id, status=True)
                    eCronogramas = qCronogramas.filter(fechafininscripcion__gte=hoy)
                    nCronogramas = qCronogramas.filter(fechainicioinscripcion__lte=hoy,
                                                        fechafininscripcion__gte=hoy)
                    eSolicitudesFerias = SolicitudFeria.objects.filter(Q(usuario_creacion_id=usuario_id) |
                                                                       Q(participanteferia__matricula__inscripcion__persona__usuario_id=usuario_id), status=True).distinct()
                    eSolicitudesFerias_serializer = SolicitudFeriaSerializer(eSolicitudesFerias, context={'user_id': usuario_id}, many=True)
                    eCronograma_serializer = CronogramaFeriaSerializer(eCronogramas, many=True)
                    eData = {
                        'eSolicitudesFerias': eSolicitudesFerias_serializer.data if eSolicitudesFerias.values("id").exists() else [],
                        'eUserLog': usuario_id,
                        'eCronogramas': eCronograma_serializer.data if eCronogramas.values("id").exists() else [],
                        'enButtonNew': True if not eSolicitudesFerias.filter(cronograma__id__in=nCronogramas.values('id')).values("id").exists() and nCronogramas.count() > 0 else False, #habilitar el boton nuevo,
                        'habilitar_chatbot': habilitar_chatbot
                    }
                    return Helper_Response(isSuccess=True, data=eData, status=status.HTTP_200_OK)
                except Exception as ex:
                    return Helper_Response(isSuccess=False, data={}, message=f'Ocurrio un error: {ex.__str__()}', status=status.HTTP_200_OK)
        except Exception as ex:
            return Helper_Response(isSuccess=False, data={}, message=f'Ocurrio un error: {ex.__str__()}', status=status.HTTP_200_OK)

