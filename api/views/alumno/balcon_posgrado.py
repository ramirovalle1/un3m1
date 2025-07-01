from datetime import datetime

from django.db import transaction
from rest_framework import status
from rest_framework.parsers import MultiPartParser, FormParser
from rest_framework.views import APIView

from api.helpers.response_herlper import Helper_Response
from api.serializers.alumno.balcon_posgrado_ser import TipoSolicitudSerializer, SolicitudBalconSerializer
from posgrado.models import TipoSolicitudBalcon, SolicitudBalcon, AdjuntoSolicitudBalcon
from sga.models import PerfilUsuario, MateriaAsignada, Periodo, ProfesorMateria
from sga.templatetags.sga_extras import encrypt


class BalconPosgradoAPIView(APIView):
    api_key_module = 'ALU_BALCON_SOLICITUD_POSGRADO'
    parser_classes = (MultiPartParser, FormParser)

    def post(self, request):

        from api.forms.solicitudbalconposgrado import SolicitudBalconPosgradoForm, AdjuntoSolicitudBalconForm
        eRequest = request.data
        eFiles = request.FILES
        try:
            action = eRequest.get('action', None)
            if not action:
                raise NameError(u'Acción no permitida')

            if action == 'saveSolicitudBalcon':
                with transaction.atomic():
                    try:
                        id_materia = eRequest.get('id_materia', None)
                        if not id_materia:
                            raise NameError(u'No se encuentra la materia asignada')
                        eMateriaAsignada = MateriaAsignada.objects.get(pk=int(encrypt(id_materia)))
                        formSol = SolicitudBalconPosgradoForm(eRequest)
                        formSol.initQuerySet(eRequest)
                        if not formSol.is_valid():
                            errors = []
                            for k, v in formSol.errors.items():
                                errors.append({'field': k, 'message': v[0]})
                            formSol.addErrors(errors)
                            form_e = formSol.toArray()
                            transaction.set_rollback(True)
                            return Helper_Response(isSuccess=False, data={'form': form_e},
                                                   message=f'Debe ingresar la información en todos los campos requeridos',
                                                   status=status.HTTP_200_OK)
                        eSolicitud = SolicitudBalcon(
                            tipo_solicitud=formSol.cleaned_data['tipo_solicitud'],
                            titulo=formSol.cleaned_data['titulo'],
                            detalle=formSol.cleaned_data['detalle'],
                            fecha_solicitud=datetime.now().date(),
                            estado=SolicitudBalcon.EstadoSolicitud.NUEVO,
                            materia_asignada=eMateriaAsignada,
                            tipo_proceso=SolicitudBalcon.TipoProceso.SOLICITUD,
                        )
                        eSolicitud.save(request)
                        if eFiles:
                            formAdj = AdjuntoSolicitudBalconForm(eRequest, eFiles)
                            formAdj.initQuerySet(eSolicitud.id)
                            if not formAdj.is_valid():
                                errors = []
                                for k, v in formAdj.errors.items():
                                    errors.append({'field': k, 'message': v[0]})
                                formAdj.addErrors(errors)
                                form_e = formAdj.toArray()
                                transaction.set_rollback(True)
                                return Helper_Response(isSuccess=False, data={'form': form_e},
                                                       message=f'Debe ingresar la información en todos los campos requeridos',
                                                       status=status.HTTP_200_OK)

                            eArchivos = formAdj.files.getlist('archivo')

                            from sga.funciones import verifica_docs_duplicados
                            v_duplicado = verifica_docs_duplicados(eArchivos)
                            if v_duplicado['e_duplicado']:
                                a_duplicados = ", ".join(v_duplicado['n_duplicados'])
                                raise NameError(f'archivos duplicados: {a_duplicados}. Reemplace uno de los archivos duplicados.')

                            for file in eArchivos:
                                extenFile = file.name.split('.')[-1]
                                if extenFile not in ['pdf', 'jpg', 'jpeg', 'png']:
                                    raise NameError(f'El formato del archivo {file.name} no es permitido, solo se permiten archivos PDF, JPG, JPEG y PNG')
                                if file.size > 5242880:
                                    raise NameError(f'El tamaño del archivo {file.name} no debe ser mayor a 5MB')
                                from sga.funciones import generar_nombre
                                file_nombre = file._name.split('.')[-2]
                                file._name = generar_nombre(f'adjunto_{eSolicitud.id}_', file._name)
                                eAdjunto = AdjuntoSolicitudBalcon(
                                    solicitud=eSolicitud,
                                    nombre=file_nombre,
                                    archivo=file,
                                    tipo=AdjuntoSolicitudBalcon.TipoAdjunto.SOLICITUD
                                )
                                eAdjunto.save(request)
                        from posgrado.adm_balcon_posgrado import notificar_proceso_solicitud
                        notificar_proceso_solicitud(eSolicitud.id, request)

                        return Helper_Response(isSuccess=True, data={}, message='Solicitud enviada correctamente',
                                               status=status.HTTP_200_OK)

                    except Exception as ex:
                        transaction.set_rollback(True)
                        return Helper_Response(isSuccess=False, data={}, message=f'Ocurrio un error: {ex.__str__()}',
                                               status=status.HTTP_200_OK)

            if action == 'saveCalificacionAtencion':
                with transaction.atomic():
                    try:
                        id_solicitud = eRequest.get('id_solicitud', None)
                        if not id_solicitud:
                            raise NameError(u'No se encuentra la solicitud')
                        calificacion = eRequest.get('calificacion', None)
                        if not calificacion:
                            raise NameError(u'No se encuentra la calificación')
                        if calificacion not in ['1', '2', '3', '4', '5'] or int(calificacion) < 1 or int(calificacion) > 5:
                            raise NameError(u'La calificación debe ser un número valido entre 1 y 5, marquelo en las estrellas de calificación')

                        eSolicitud = SolicitudBalcon.objects.get(pk=int(encrypt(id_solicitud)))
                        if eSolicitud.estado != 3 or eSolicitud.estado == 0:
                            raise NameError(u'La solicitud aún no ha sido atendida')
                        if eSolicitud.is_finalizada_calificacion():
                            raise NameError(u'La solicitud ya ha sido finalizada')
                        eSolicitud.calificacion = int(calificacion)
                        eSolicitud.calificacion_comentario = eRequest.get('comentario', '')
                        eSolicitud.calificacion_fecha = datetime.now().date()
                        eSolicitud.save(request)
                        return Helper_Response(isSuccess=True, data={}, message='Calificación enviada correctamente',
                                               status=status.HTTP_200_OK)
                    except Exception as ex:
                        transaction.set_rollback(True)
                        return Helper_Response(isSuccess=False, data={}, message=f'Ocurrio un error: {ex.__str__()}',
                                               status=status.HTTP_200_OK)


        except Exception as ex:
            return Helper_Response(isSuccess=False, data={}, message=f'Ocurrio un error: {ex.__str__()}',
                                   status=status.HTTP_200_OK)

    def get(self, request):
        try:
            payload = request.auth.payload
            ePerfilUsuario = PerfilUsuario.objects.get(pk=encrypt(payload['perfilprincipal']['id']))
            if not ePerfilUsuario.es_estudiante():
                raise NameError(u'Solo los perfiles de estudiantes pueden ingresar al modulo.')
            eInscripcion = ePerfilUsuario.inscripcion
            ePersona = ePerfilUsuario.persona
            eMaestria = Periodo.objects.get(pk=int(encrypt(payload['periodo']['id'])))
            if not eMaestria.es_posgrado():
                raise NameError(u'El periodo seleccionado no es de posgrado')
            eMateriaAsignadaCurso = MateriaAsignada.objects.filter(
                matricula_id=int(encrypt(payload['matricula']['id'])), estado_id=3).first()
            if not eMateriaAsignadaCurso:
                eMateriaAsignadaCurso= MateriaAsignada.objects.filter(matricula_id=int(encrypt(payload['matricula']['id']))).order_by('-fechaasignacion').first()
            eCoordinador = ProfesorMateria.objects.filter(tipoprofesor_id=8,
                                                          materia_id=eMateriaAsignadaCurso.materia.id).first()

            data = {}
            data['eMaestria'] = {'id': encrypt(eMaestria.id), 'display': eMaestria.nombre}
            data['eMateriaAsignadaCurso'] = {'id': encrypt(eMateriaAsignadaCurso.id),
                                             'display': eMateriaAsignadaCurso.materia.nombre_mostrar_sin_profesor()}
            data['eCoordinador'] = {'id': encrypt(eCoordinador.profesor.id), 'display': eCoordinador.profesor.__str__()}

            eTiposSolicitudes = TipoSolicitudBalcon.objects.filter(status=True)
            eTiposSolicitudes_ser = TipoSolicitudSerializer(eTiposSolicitudes, many=True)
            data['eTiposSolicitudes'] = eTiposSolicitudes_ser.data if eTiposSolicitudes_ser else []

            eSolicitudes = SolicitudBalcon.objects.filter(status=True, materia_asignada=eMateriaAsignadaCurso)
            eSolicitudes_ser = SolicitudBalconSerializer(eSolicitudes, many=True)
            data['eSolicitudes'] = eSolicitudes_ser.data if eSolicitudes_ser else []

            return Helper_Response(isSuccess=True, data=data, status=status.HTTP_200_OK)
        except Exception as ex:
            return Helper_Response(isSuccess=False, data={}, message=f'Ocurrio un error: {ex.__str__()}',
                                   status=status.HTTP_200_OK)
