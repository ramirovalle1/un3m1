import json
from datetime import datetime
from django.db.models import Q
from django.core.exceptions import ObjectDoesNotExist
from django.db import transaction, connections
from rest_framework import status, serializers
from rest_framework.permissions import IsAuthenticated
from rest_framework.views import APIView

from api.forms.tutoria_academica import SolicitudTutoriaIndividualForm
from api.helpers.decorators import api_security
from api.helpers.response_herlper import Helper_Response
from api.serializers.alumno.tutoria_academica import SolicitudTutoriaIndividualSerializer
from inno.models import SolicitudTutoriaIndividual, HorarioTutoriaAcademica, SolicitudTutoriaIndividualTema
from core.cache import get_cache_ePerfilUsuario
from django.core.cache import cache

from settings import DEBUG
from sga.funciones import generar_nombre, log, elimina_tildes, convertir_fecha_invertida, variable_valor
from sga.models import PerfilUsuario, Matricula, MateriaAsignada, Materia, ProfesorDistributivoHoras, \
    DetalleDistributivo, Profesor, DetalleSilaboSemanalTema, Clase, Turno, miinstitucion
from sga.tasks import send_html_mail
from sga.templatetags.sga_extras import encrypt


class TutoriaAcademicaAPIView(APIView):
    permission_classes = (IsAuthenticated,)
    api_key_module = 'ALUMNO_TUTORIA_ACADEMICA'

    def post(self, request):
        if 'multipart/form-data' in request.content_type:
            eRequest = request._request.POST
            eFiles = request._request.FILES
        else:
            eRequest = request.data
        try:
            hoy = datetime.now().date()
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
                    if ePeriodo.tipo_id in [3, 4]:
                        filtro = filtro & Q(materia__inicio__lte=hoy, materia__fin__gte=hoy)
                    if not DEBUG:
                        filtro = filtro & Q(matricula__cerrada=False, materia__cerrado=False)
                    eMateriaAsignadas = MateriaAsignada.objects.filter(filtro).exclude(materia__profesormateria__tipoprofesor_id__in=[16]).distinct()
                    eMaterias = Materia.objects.filter(pk__in=eMateriaAsignadas.values_list('materia__id', flat=True)).exclude(asignaturamalla__malla_id__in=[353, 22])
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
                    eProfesorMaterias = eMateria.profesormateria_set.filter(status=True, activo=True).exclude(tipoprofesor_id__in=[16]).distinct('profesor_id')
                    results = []
                    for eProfesorMateria in eProfesorMaterias:
                        if DetalleDistributivo.objects.values("id").filter(distributivo__profesor=eProfesorMateria.profesor, distributivo__periodo=ePeriodo, criteriodocenciaperiodo__criterio__procesotutoriaacademica=True).exists():
                            results.append({"id": eProfesorMateria.profesor.id, "name": eProfesorMateria.profesor.persona.nombre_completo_inverso()})
                    # if isGrupo:
                    #     for eMateriaAsignada in MateriaAsignada.objects.filter(status=True, materia=eMateria).distinct().order_by('matricula__inscripcion__persona'):
                    #         aEstudiantes.append([{'id': eMateriaAsignada.matricula.id, 'name': u'%s - %s' % (eMateriaAsignada.matricula.inscripcion.persona.documento(), eMateriaAsignada.matricula.inscripcion.persona.nombre_completo())}])
                    return Helper_Response(isSuccess=True, data={'results': results}, message=f'Se cargaron correctamente los datos', status=status.HTTP_200_OK)
                except Exception as ex:
                    return Helper_Response(isSuccess=False, data={}, message=f'Error al cargar los datos: {ex.__str__()}', status=status.HTTP_200_OK)

            elif action == 'loadEstudiante':
                try:
                    id = eRequest.get('id', 0)
                    try:
                        eMateria = Materia.objects.get(pk=id)
                    except ObjectDoesNotExist:
                        raise NameError(u"Materia no encontrada")
                    ePeriodo = eMatricula.nivel.periodo
                    results = []
                    for eMateriaAsignada in MateriaAsignada.objects.filter(status=True, materia=eMateria, retiramateria=False).exclude(matricula=eMatricula).distinct().order_by('matricula__inscripcion__persona'):
                        results.append({'id': eMateriaAsignada.id, 'document': u'%s' % eMateriaAsignada.matricula.inscripcion.persona.documento(), 'name': u'%s' % (eMateriaAsignada.matricula.inscripcion.persona.nombre_completo())})
                    return Helper_Response(isSuccess=True, data={'results': results}, message=f'Se cargaron correctamente los datos', status=status.HTTP_200_OK)
                except Exception as ex:
                    return Helper_Response(isSuccess=False, data={}, message=f'Error al cargar los datos: {ex.__str__()}', status=status.HTTP_200_OK)

            elif action == 'loadHorario':
                try:
                    idm = eRequest.get('idm', 0)
                    idp = eRequest.get('idp', 0)
                    try:
                        eMateria = Materia.objects.get(pk=idm)
                    except ObjectDoesNotExist:
                        raise NameError(u"Materia no encontrada")
                    try:
                        eProfesor = Profesor.objects.get(pk=idp)
                    except ObjectDoesNotExist:
                        raise NameError(u"Profesor no encontrado")
                    ePeriodo = eMatricula.nivel.periodo
                    eHorarios = HorarioTutoriaAcademica.objects.filter(status=True, profesor=eProfesor, periodo=ePeriodo).distinct().order_by('dia')
                    results = []
                    for eHorario in eHorarios:
                        results.append({"id": eHorario.id, "name": u'%s - %s' % (eHorario.get_dia_display() if not eHorario.dia == 0 else 'DOMINGO', eHorario.turno)})
                    return Helper_Response(isSuccess=True, data={'results': results}, message=f'Se cargaron correctamente los datos', status=status.HTTP_200_OK)
                except Exception as ex:
                    return Helper_Response(isSuccess=False, data={}, message=f'Error al cargar los datos: {ex.__str__()}', status=status.HTTP_200_OK)

            elif action == 'loadTema':
                try:
                    idm = eRequest.get('idm', 0)
                    idp = eRequest.get('idp', 0)
                    try:
                        eMateria = Materia.objects.get(pk=idm)
                    except ObjectDoesNotExist:
                        raise NameError(u"Materia no encontrada")
                    try:
                        eProfesor = Profesor.objects.get(pk=idp)
                    except ObjectDoesNotExist:
                        raise NameError(u"Profesor no encontrado")
                    eTemas = DetalleSilaboSemanalTema.objects.filter(status=True, silabosemanal__silabo__materia=eMateria, silabosemanal__silabo__status=True, silabosemanal__fechainiciosemana__lte=datetime.now().date()).distinct().order_by('silabosemanal__semana')
                    results = []
                    for eTema in eTemas:
                        results.append({"id": eTema.id, "name": u'Sem: %s - %s (%s / %s)' % (eTema.silabosemanal.numsemana, eTema.temaunidadresultadoprogramaanalitico.descripcion, eTema.silabosemanal.fechainiciosemana, eTema.silabosemanal.fechafinciosemana,)})
                    return Helper_Response(isSuccess=True, data={'results': results}, message=f'Se cargaron correctamente los datos', status=status.HTTP_200_OK)
                except Exception as ex:
                    return Helper_Response(isSuccess=False, data={}, message=f'Error al cargar los datos: {ex.__str__()}', status=status.HTTP_200_OK)

            elif action == 'saveSolicitudTutoriaIndividual':
                with transaction.atomic():
                    try:
                        if not eMatricula:
                            raise NameError(u"No se encuentra matrículado")
                        ePeriodo = eMatricula.nivel.periodo
                        isNew = False
                        f = SolicitudTutoriaIndividualForm(eRequest, eFiles)
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
                        eHorarioTutoriaAcademica = f.cleaned_data['horario']
                        id = eRequest.get('id', 0)
                        eMateriaAsignadas = MateriaAsignada.objects.filter(matricula=eMatricula, materia__nivel__periodo=ePeriodo, materia__inicio__lte=hoy, materia__fin__gte=hoy, retiramateria=False).distinct()
                        eClases = Clase.objects.filter(activo=True, materia__materiaasignada__matricula=eMatricula, materia__materiaasignada__retiramateria=False, dia=eHorarioTutoriaAcademica.dia)

                        if ePeriodo.tipo_id in [3, 4]:
                            eClases = eClases.filter(materia__materiaasignada__materia_id__in=eMateriaAsignadas.values_list('materia_id', flat=True))
                            if eClases.values("id").exists():
                                eTurnos = Turno.objects.filter(Q(id__in=eClases.values_list('turno__id', flat=True))).distinct().order_by('comienza')
                        else:
                            if eClases.values("id").exists():
                                eTurnos = Turno.objects.filter(Q(id__in=eClases.values_list('turno__id', flat=True))).distinct().order_by('comienza')
                                for eTurno in eTurnos:
                                    if eHorarioTutoriaAcademica.turno.comienza <= eTurno.termina and eHorarioTutoriaAcademica.turno.termina >= eTurno.comienza:
                                        raise NameError(u"Usted no puede seleccionar este horario, ud tiene clases.")

                        if hoy.isoweekday() == eHorarioTutoriaAcademica.dia:
                            raise NameError(u"No puede solicitar una tutoria en un horario del mismo día, por favor intentelo con otro horario o al siguiente día.")

                        try:
                            eSolicitudTutoriaIndividual = SolicitudTutoriaIndividual.objects.get(pk=id)
                        except ObjectDoesNotExist:
                            eSolicitudTutoriaIndividual = SolicitudTutoriaIndividual(profesor=f.cleaned_data['profesor'],
                                                                                     materiaasignada=eMateriaAsignada)
                            isNew = True

                        eSolicitudTutoriaIndividualTemas = SolicitudTutoriaIndividualTema.objects.filter(status=True, solicitud__status=True, solicitud__profesor=f.cleaned_data['profesor'], solicitud__materiaasignada=eMateriaAsignada, solicitud__estado__in=[1, 2], solicitud__topico=1, tema=f.cleaned_data['tema'])
                        eSolicitudTutoriaIndividuales = SolicitudTutoriaIndividual.objects.filter(status=True, profesor_id=f.cleaned_data['profesor'], materiaasignada=eMateriaAsignada, topico=2, estado__in=[1, 2])
                        topico = int(f.cleaned_data['topico'])
                        if topico == 1:
                            if isNew:
                                if eSolicitudTutoriaIndividualTemas.values("id").exists():
                                    raise NameError(u"Usted no puede solicitar tutoría con el mismo tema.")
                            else:
                                if eSolicitudTutoriaIndividualTemas.values("id").exclude(solicitud_id=eSolicitudTutoriaIndividual.id).exists():
                                    raise NameError(u"Usted no puede solicitar tutoría con el mismo tema.")
                        elif topico == 2:
                            if isNew:
                                if eSolicitudTutoriaIndividuales.values("id").exists():
                                    raise NameError(u"Usted no puede solicitar tutoría hasta que se haya ejecutado la actual.")
                            else:
                                if eSolicitudTutoriaIndividuales.values("id").exclude(id=eSolicitudTutoriaIndividual.id).exists():
                                    raise NameError(u"Usted no puede solicitar tutoría hasta que se haya ejecutado la actual.")
                        eSolicitudTutoriaIndividual.materiaasignada = eMateriaAsignada
                        eSolicitudTutoriaIndividual.profesor = f.cleaned_data['profesor']
                        eSolicitudTutoriaIndividual.horario = eHorarioTutoriaAcademica
                        eSolicitudTutoriaIndividual.estado = 1
                        eSolicitudTutoriaIndividual.topico = topico
                        eSolicitudTutoriaIndividual.fechasolicitud = datetime.now()
                        eSolicitudTutoriaIndividual.tipo = 1
                        eSolicitudTutoriaIndividual.observacion_estudiante = f.cleaned_data['observacion_estudiante']
                        eSolicitudTutoriaIndividual.tipotutoria = 1
                        eSolicitudTutoriaIndividual.save(request)
                        if isNew:
                            log(u'Adiciono solicitud de tutoria academica: %s' % eSolicitudTutoriaIndividual, request, "add")
                            if topico == 1:
                                if not SolicitudTutoriaIndividualTema.objects.values("id").filter(solicitud=eSolicitudTutoriaIndividual, tema=f.cleaned_data['tema']).exists():
                                    eSolicitudTutoriaIndividualTema = SolicitudTutoriaIndividualTema(solicitud=eSolicitudTutoriaIndividual,
                                                                                                     tema=f.cleaned_data['tema'])
                                    eSolicitudTutoriaIndividualTema.save(request)
                            try:
                                send_html_mail("Solicitud de tutoría",
                                               "emails/solicitudtutoriaestudiante.html",
                                               {'sistema': u'SGA - UNEMI',
                                                'fecha': datetime.now().date(),
                                                'hora': datetime.now().time(),
                                                'solicitud': eSolicitudTutoriaIndividual,
                                                't': miinstitucion()
                                                },
                                               eSolicitudTutoriaIndividual.profesor.persona.lista_emails_interno(),
                                               [],
                                               cuenta=variable_valor('CUENTAS_CORREOS')[0]
                                               )
                            except:
                                pass
                        else:
                            log(u'Editó solicitud de tutoria academica: %s' % eSolicitudTutoriaIndividual, request, "edit")
                            if topico == 1:
                                if not SolicitudTutoriaIndividualTema.objects.values("id").filter(solicitud=eSolicitudTutoriaIndividual, tema=f.cleaned_data['tema']).exists():
                                    if SolicitudTutoriaIndividualTema.objects.values("id").filter(solicitud=eSolicitudTutoriaIndividual).exists():
                                        eSolicitudTutoriaIndividualTema = SolicitudTutoriaIndividualTema.objects.get(solicitud=eSolicitudTutoriaIndividual)
                                        eSolicitudTutoriaIndividualTema.tema = f.cleaned_data['tema']
                                        eSolicitudTutoriaIndividualTema.save(request)
                                    else:
                                        eSolicitudTutoriaIndividualTema = SolicitudTutoriaIndividualTema(solicitud=eSolicitudTutoriaIndividual,
                                                                                                         tema=f.cleaned_data['tema'])
                                        eSolicitudTutoriaIndividualTema.save(request)
                            elif topico == 2:
                                if SolicitudTutoriaIndividualTema.objects.filter(solicitud=eSolicitudTutoriaIndividual).exists():
                                    SolicitudTutoriaIndividualTema.objects.filter(solicitud=eSolicitudTutoriaIndividual).update(status=False)

                        return Helper_Response(isSuccess=True, data={}, message=f'Se guardo correctamente los datos', status=status.HTTP_200_OK)
                    except Exception as ex:
                        transaction.set_rollback(True)
                        return Helper_Response(isSuccess=False, data={}, message=f'Error al guardar los datos: {ex.__str__()}', status=status.HTTP_200_OK)

            elif action == 'deleteSolicitudTutoriaIndividual':
                with transaction.atomic():
                    try:
                        id = eRequest.get('id', 0)
                        try:
                            eSolicitudTutoriaIndividual = SolicitudTutoriaIndividual.objects.get(materiaasignada__matricula=eMatricula, pk=id)
                        except ObjectDoesNotExist:
                            raise NameError(u"Datos no encontrados")
                        if eSolicitudTutoriaIndividual.estado == 1:
                            eSolicitudTutoriaIndividual.status = False
                            eSolicitudTutoriaIndividual.save(request)
                            log(u'Eliminó solicitud de tutoria academica: %s' % eSolicitudTutoriaIndividual, request, "del")
                        return Helper_Response(isSuccess=True, data={}, message=f'Se elimino correctamente solicitud', status=status.HTTP_200_OK)
                    except Exception as ex:
                        transaction.set_rollback(True)
                        return Helper_Response(isSuccess=False, data={}, message=f'Error al guardar los datos: {ex.__str__()}', status=status.HTTP_200_OK)

            elif action == 'saveEncuesta':
                with transaction.atomic():
                    try:
                        id = eRequest.get('id', 0)
                        rating = int(eRequest.get('rating', '0'))
                        if rating == 0:
                            raise NameError(u"Valor de respuesta incorrecto")
                        try:
                            eSolicitudTutoriaIndividual = SolicitudTutoriaIndividual.objects.get(materiaasignada__matricula=eMatricula, pk=id)
                        except ObjectDoesNotExist:
                            raise NameError(u"Datos no encontrados")
                        eSolicitudTutoriaIndividual.resultadoencuesta = rating
                        eSolicitudTutoriaIndividual.save(request)
                        log(u'Realiza encuesta se satisfación tutoria: %s' % eSolicitudTutoriaIndividual, request, "edit")
                        return Helper_Response(isSuccess=True, data={}, message=f'Se guardo correctamente los datos', status=status.HTTP_200_OK)
                    except Exception as ex:
                        transaction.set_rollback(True)
                        return Helper_Response(isSuccess=False, data={}, message=f'Error al guardar los datos: {ex.__str__()}', status=status.HTTP_200_OK)

            elif action == 'saveClaseTutoria':
                with transaction.atomic():
                    try:
                        id = eRequest.get('id', 0)
                        try:
                            eSolicitudTutoriaIndividual = SolicitudTutoriaIndividual.objects.get(id=id)
                        except ObjectDoesNotExist:
                            raise NameError(u"No se encontro registro")
                        if not eSolicitudTutoriaIndividual.asistencia:
                            eSolicitudTutoriaIndividual.asistencia = True
                            eSolicitudTutoriaIndividual.estado = 3
                            eSolicitudTutoriaIndividual.save(request)
                            log(u'Registro de asistencia tutorían académica: %s' % eSolicitudTutoriaIndividual, request, "edit")
                        return Helper_Response(isSuccess=True, data={}, message=f'Se guardo correctamente la asistencia', status=status.HTTP_200_OK)
                    except Exception as ex:
                        transaction.set_rollback(True)
                        return Helper_Response(isSuccess=False, data={}, message=f'Error al guardar los datos: {ex.__str__()}', status=status.HTTP_200_OK)

            elif action == 'saveSolicitudTutoriaGrupal':
                with transaction.atomic():
                    try:
                        if not eMatricula:
                            raise NameError(u"No se encuentra matrículado")
                        ePeriodo = eMatricula.nivel.periodo
                        f = SolicitudTutoriaIndividualForm(eRequest, eFiles)
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
                        eHorarioTutoriaAcademica = f.cleaned_data['horario']
                        if hoy.isoweekday() == eHorarioTutoriaAcademica.dia:
                            raise NameError(u"No puede solicitar una tutoria en un horario del mismo día, por favor intentelo con otro horario o al siguiente día.")
                        topico = int(f.cleaned_data['topico'])
                        estudiantes = f.data.get('estudiantes', None)
                        if estudiantes is None:
                            raise NameError(u"No se encontro estudiante")
                        for id in json.loads(estudiantes):
                            try:
                                eMateriaAsignada_aux = MateriaAsignada.objects.get(materia=f.cleaned_data['materia'], retiramateria=False, pk=id)
                            except ObjectDoesNotExist:
                                raise NameError(u"No se encontro materia asignada")
                            eMatricula_aux = eMateriaAsignada_aux.matricula
                            eMateriaAsignadas_aux = MateriaAsignada.objects.filter(matricula=eMatricula_aux, materia__nivel__periodo=ePeriodo, materia__inicio__lte=hoy, materia__fin__gte=hoy, retiramateria=False).distinct()
                            eClases_aux = Clase.objects.filter(activo=True, materia__materiaasignada__matricula=eMatricula_aux, materia__materiaasignada__retiramateria=False, dia=eHorarioTutoriaAcademica.dia)
                            if eMatricula_aux.nivel.periodo.tipo_id in [3, 4]:
                                eClases_aux = eClases_aux.filter(materia__materiaasignada__materia_id__in=eMateriaAsignadas_aux.values_list('materia_id', flat=True))
                                if eClases_aux.values("id").exists():
                                    eTurnos_aux = Turno.objects.filter(Q(id__in=eClases_aux.values_list('turno__id', flat=True))).distinct().order_by('comienza')
                            else:
                                if eClases_aux.values("id").exists():
                                    eTurnos_aux = Turno.objects.filter(Q(id__in=eClases_aux.values_list('turno__id', flat=True))).distinct().order_by('comienza')
                                    for eTurno in eTurnos_aux:
                                        if eHorarioTutoriaAcademica.turno.comienza <= eTurno.termina and eHorarioTutoriaAcademica.turno.termina >= eTurno.comienza:
                                            raise NameError(u"Usted no puede seleccionar este horario, ud tiene clases.")

                            eSolicitudTutoriaIndividualTemas_aux = SolicitudTutoriaIndividualTema.objects.filter(status=True, solicitud__status=True, solicitud__profesor=f.cleaned_data['profesor'], solicitud__materiaasignada=eMateriaAsignada_aux, solicitud__estado__in=[1, 2], solicitud__topico=1, tema=f.cleaned_data['tema'])
                            eSolicitudTutoriaIndividuales_aux = SolicitudTutoriaIndividual.objects.filter(status=True, profesor_id=f.cleaned_data['profesor'], materiaasignada=eMateriaAsignada_aux, topico=2, estado__in=[1, 2])

                            if topico == 1:
                                if eSolicitudTutoriaIndividualTemas_aux.values("id").exists():
                                    raise NameError(u"%s no puede solicitar tutoría con el mismo tema." % eMatricula_aux.inscripcion.persona)
                            elif topico == 2:
                                if eSolicitudTutoriaIndividuales_aux.values("id").exists():
                                    raise NameError(u"%s tiene una solicitud de tutoría programada." % eMatricula_aux.inscripcion.persona)

                            eSolicitudTutoriaIndividual_aux = SolicitudTutoriaIndividual(profesor=f.cleaned_data['profesor'],
                                                                                         materiaasignada=eMateriaAsignada_aux)
                            eSolicitudTutoriaIndividual_aux.materiaasignada = eMateriaAsignada_aux
                            eSolicitudTutoriaIndividual_aux.profesor = f.cleaned_data['profesor']
                            eSolicitudTutoriaIndividual_aux.horario = eHorarioTutoriaAcademica
                            eSolicitudTutoriaIndividual_aux.estado = 1
                            eSolicitudTutoriaIndividual_aux.topico = topico
                            eSolicitudTutoriaIndividual_aux.fechasolicitud = datetime.now()
                            eSolicitudTutoriaIndividual_aux.tipo = 2
                            eSolicitudTutoriaIndividual_aux.observacion_estudiante = f.cleaned_data['observacion_estudiante']
                            eSolicitudTutoriaIndividual_aux.tipotutoria = 1
                            eSolicitudTutoriaIndividual_aux.save(request)
                            if topico == 1:
                                if not SolicitudTutoriaIndividualTema.objects.values("id").filter(solicitud=eSolicitudTutoriaIndividual_aux, tema=f.cleaned_data['tema']).exists():
                                    eSolicitudTutoriaIndividualTema_aux = SolicitudTutoriaIndividualTema(solicitud=eSolicitudTutoriaIndividual_aux,
                                                                                                         tema=f.cleaned_data['tema'])
                                    eSolicitudTutoriaIndividualTema_aux.save(request)

                        eMateriaAsignadas = MateriaAsignada.objects.filter(matricula=eMatricula, materia__nivel__periodo=ePeriodo, materia__inicio__lte=hoy, materia__fin__gte=hoy, retiramateria=False).distinct()
                        eClases = Clase.objects.filter(activo=True, materia__materiaasignada__matricula=eMatricula, materia__materiaasignada__retiramateria=False, dia=eHorarioTutoriaAcademica.dia)

                        if ePeriodo.tipo_id in [3, 4]:
                            eClases = eClases.filter(materia__materiaasignada__materia_id__in=eMateriaAsignadas.values_list('materia_id', flat=True))
                            if eClases.values("id").exists():
                                eTurnos = Turno.objects.filter(Q(id__in=eClases.values_list('turno__id', flat=True))).distinct().order_by('comienza')
                        else:
                            if eClases.values("id").exists():
                                eTurnos = Turno.objects.filter(Q(id__in=eClases.values_list('turno__id', flat=True))).distinct().order_by('comienza')
                                for eTurno in eTurnos:
                                    if eHorarioTutoriaAcademica.turno.comienza <= eTurno.termina and eHorarioTutoriaAcademica.turno.termina >= eTurno.comienza:
                                        raise NameError(u"Usted no puede seleccionar este horario, ud tiene clases.")

                        eSolicitudTutoriaIndividualTemas = SolicitudTutoriaIndividualTema.objects.filter(status=True, solicitud__status=True, solicitud__profesor=f.cleaned_data['profesor'], solicitud__materiaasignada=eMateriaAsignada, solicitud__estado__in=[1, 2], solicitud__topico=1, tema=f.cleaned_data['tema'])
                        eSolicitudTutoriaIndividuales = SolicitudTutoriaIndividual.objects.filter(status=True, profesor_id=f.cleaned_data['profesor'], materiaasignada=eMateriaAsignada, topico=2, estado__in=[1, 2])
                        topico = int(f.cleaned_data['topico'])
                        if topico == 1:
                            if eSolicitudTutoriaIndividualTemas.values("id").exists():
                                raise NameError(u"Usted no puede solicitar tutoría con el mismo tema.")
                        elif topico == 2:
                            if eSolicitudTutoriaIndividuales.values("id").exists():
                                raise NameError(u"Usted no puede solicitar tutoría hasta que se haya ejecutado la actual.")
                        eSolicitudTutoriaIndividual = SolicitudTutoriaIndividual(profesor=f.cleaned_data['profesor'],
                                                                                 materiaasignada=eMateriaAsignada)
                        eSolicitudTutoriaIndividual.materiaasignada = eMateriaAsignada
                        eSolicitudTutoriaIndividual.profesor = f.cleaned_data['profesor']
                        eSolicitudTutoriaIndividual.horario = eHorarioTutoriaAcademica
                        eSolicitudTutoriaIndividual.estado = 1
                        eSolicitudTutoriaIndividual.topico = topico
                        eSolicitudTutoriaIndividual.fechasolicitud = datetime.now()
                        eSolicitudTutoriaIndividual.tipo = 1
                        eSolicitudTutoriaIndividual.observacion_estudiante = f.cleaned_data['observacion_estudiante']
                        eSolicitudTutoriaIndividual.tipotutoria = 1
                        eSolicitudTutoriaIndividual.save(request)
                        log(u'Adiciono solicitud de tutoria academica: %s' % eSolicitudTutoriaIndividual, request, "add")
                        if topico == 1:
                            if not SolicitudTutoriaIndividualTema.objects.values("id").filter(solicitud=eSolicitudTutoriaIndividual, tema=f.cleaned_data['tema']).exists():
                                eSolicitudTutoriaIndividualTema = SolicitudTutoriaIndividualTema(solicitud=eSolicitudTutoriaIndividual,
                                                                                                 tema=f.cleaned_data['tema'])
                                eSolicitudTutoriaIndividualTema.save(request)
                        try:
                            send_html_mail("Solicitud de tutoría",
                                           "emails/solicitudtutoriaestudiante.html",
                                           {'sistema': u'SGA - UNEMI',
                                            'fecha': datetime.now().date(),
                                            'hora': datetime.now().time(),
                                            'solicitud': eSolicitudTutoriaIndividual,
                                            't': miinstitucion()
                                            },
                                           eSolicitudTutoriaIndividual.profesor.persona.lista_emails_interno(),
                                           [],
                                           cuenta=variable_valor('CUENTAS_CORREOS')[0]
                                           )
                        except:
                            pass

                        return Helper_Response(isSuccess=True, data={}, message=f'Se guardo correctamente los datos', status=status.HTTP_200_OK)
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

            eRequest = request.query_params
            if 'action' in eRequest:
                action = request.query_params['action']

                if action == 'loadSolicitudes':
                    try:
                        filtro = Q(materiaasignada__matricula=eMatricula, status=True)
                        search = eRequest.get('search', None)
                        if search:
                            filtro = filtro & Q(Q(materiaasignada__materia__asignatura__nombre__icontains=search) | Q(materiaasignada__materia__paralelomateria__nombre__icontains=search))
                        eSolicitudTutoriaIndividuales = SolicitudTutoriaIndividual.objects.filter(filtro)
                        eSolicitudes = SolicitudTutoriaIndividualSerializer(eSolicitudTutoriaIndividuales, many=True).data if eSolicitudTutoriaIndividuales.values("id").exists() else []
                        return Helper_Response(isSuccess=True, data={'eSolicitudes': eSolicitudes}, message=f'', status=status.HTTP_200_OK)
                    except Exception as ex:
                        return Helper_Response(isSuccess=False, data={'eSolicitudes': []}, message=f'Ocurrio un error: {ex.__str__()}', status=status.HTTP_200_OK)

            return Helper_Response(isSuccess=False, data={}, message=f'Acción no encontrada', status=status.HTTP_200_OK)
        except Exception as ex:
            return Helper_Response(isSuccess=False, data={}, message=f'Ocurrio un error: {ex.__str__()}', status=status.HTTP_200_OK)