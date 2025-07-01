# coding=utf-8
from datetime import datetime

from django.db import transaction
from rest_framework.permissions import IsAuthenticated
from rest_framework.views import APIView
from rest_framework import status
from api.helpers.decorators import api_security
from api.helpers.response_herlper import Helper_Response
from api.serializers.alumno.miscitas import ProximaCitaSerializer
from api.serializers.alumno.ofertalaboral import OfertaLaboralSerializer,CarreraSerializer ,AplicanteOfertaSerializer, AplicanteOfertaObservacionSerializer
from matricula.models import PeriodoMatricula
from settings import EMAIL_DOMAIN
from sga.models import Noticia, Inscripcion, PerfilUsuario, Matricula, OfertaLaboral, AplicanteOfertaObservacion, AplicanteOferta, miinstitucion, CUENTAS_CORREOS, Empleador
from med.models import ProximaCita
from sga.tasks import send_html_mail
from sga.templatetags.sga_extras import encrypt
from sga.funciones import log


class OfertaLaboralAPIView(APIView):
    permission_classes = (IsAuthenticated,)
    api_key_module = 'ALUMNO_OFERTA_LABORAL'

    def post(self, request):
        TIEMPO_ENCACHE = 60 * 15
        try:
            if not 'action' in request.data:
                raise NameError(u'Parametro de acciòn no encontrado')

            action = request.data['action']
            if action == 'detalleOferta':
                try:
                    carreras = []
                    if not 'id' in request.data:
                        raise NameError(u'No se encontro parametro de materia asignada.')
                    id = encrypt(request.data['id'])
                    ofertalaboral = OfertaLaboral.objects.get(pk=int(id))
                    carreras = ofertalaboral.vercarreras()
                    carrera_serializer = CarreraSerializer(carreras, many = True)
                    ofertas_serializer = OfertaLaboralSerializer(ofertalaboral)

                    aData = {
                        'eCarrera': carrera_serializer.data if carreras.exists() else [],
                        'OfertaLaboral': ofertas_serializer.data

                    }
                    return Helper_Response(isSuccess=True, data=aData, status=status.HTTP_200_OK)
                except Exception as ex:
                    return Helper_Response(isSuccess=False, data={}, message=f'Ocurrio un error: {ex.__str__()}',
                                           status=status.HTTP_200_OK)

            elif action == 'confirmarAplicar':
                with transaction.atomic():
                    try:
                        if not 'id' in request.data:
                            raise NameError(u"Parametro no encontrado")
                        if not 'idins' in request.data:
                            raise NameError(u"Inscripción no encontrada")
                        idoferta = int(encrypt(request.data['id']))
                        idinscripcion = int(request.data['idins'])
                        eIncripcion = Inscripcion.objects.get(pk=idinscripcion)

                        solicitud = OfertaLaboral.objects.get(pk=idoferta)
                        if AplicanteOferta.objects.filter(oferta=solicitud, inscripcion=eIncripcion).exists():
                            raise NameError(u"Ya se encuentra registrado")

                        aplicante = AplicanteOferta(oferta=solicitud,
                                                    inscripcion=eIncripcion,
                                                    aprobada=False,
                                                    entrevistado=False)
                        aplicante.save(request)
                        log(u'Registro aplicante oferta en alumno oferta laboral: %s [%s]' % (aplicante, aplicante.id), request, "edit")
                        lista = ['empleo@unemi.edu.ec']
                        if eIncripcion.persona.emailinst:
                            lista.append(aplicante.inscripcion.persona.lista_emails_envio())
                        send_html_mail("Registrar Oferta", "emails/registraroferta.html", {'sistema': 'SGAEST', 'registro': aplicante, 't': miinstitucion(), 'dominio': EMAIL_DOMAIN}, lista, [], cuenta=CUENTAS_CORREOS[17][1])



                        aData = {
                        }
                        return Helper_Response(isSuccess=True, data=aData, status=status.HTTP_200_OK)
                    except Exception as ex:
                        transaction.set_rollback(True)
                        return Helper_Response(isSuccess=False, data={}, message=f'Ocurrio un error: {ex.__str__()}', status=status.HTTP_200_OK)

            elif action == 'deletefertalaboral':
                with transaction.atomic():
                    try:
                        if not 'id' in request.data:
                            raise NameError(u"Parametro no encontrado")
                        id = int(encrypt(request.data['id']))
                        oferta = AplicanteOferta.objects.get(pk=id)

                        log(u'Elimino oferta laboral en alumno oferta laboral: %s' % oferta, request, "del")
                        oferta.delete()

                        aData = {

                        }
                        return Helper_Response(isSuccess=True, data=aData, status=status.HTTP_200_OK)
                    except Exception as ex:
                        transaction.set_rollback(True)
                        return Helper_Response(isSuccess=False, data={}, message=f'Ocurrio un error: {ex.__str__()}', status=status.HTTP_200_OK)

            elif action == 'registarestado':
                with transaction.atomic():
                    try:
                        if not 'id' in request.data:
                            raise NameError(u"Parametro no encontrado")
                        id = int(encrypt(request.data['id']))
                        aplicante = AplicanteOferta.objects.get(pk=id)
                        aplicante.estado = True
                        aplicante.save(request)
                        log(u'Registro aplicante oferta en alumno oferta laboral: %s [%s]' % (aplicante, aplicante.id), request, "edit")
                        send_html_mail("Registrar Oferta", "emails/registraroferta.html", {'sistema': 'SGAEST', 'registro': aplicante, 't': miinstitucion(), 'dominio': EMAIL_DOMAIN}, aplicante.inscripcion.persona.lista_emails_envio(), [], cuenta=CUENTAS_CORREOS[17][1])
                        aData = {

                        }
                        return Helper_Response(isSuccess=True, data=aData, status=status.HTTP_200_OK)
                    except Exception as ex:
                        transaction.set_rollback(True)
                        return Helper_Response(isSuccess=False, data={}, message=f'Ocurrio un error: {ex.__str__()}', status=status.HTTP_200_OK)

            elif action == 'confirmarcita':
                with transaction.atomic():
                    try:
                        if not 'id' in request.data:
                            raise NameError(u"Parametro no encontrado")
                        id = int(encrypt(request.data['id']))
                        aplicante = AplicanteOferta.objects.get(id)
                        aplicante.citaconfirmada = True
                        aplicante.save(request)
                        empresaempleadora = aplicante.oferta.empresa
                        empleador = Empleador.objects.get(empresa=empresaempleadora)
                        log(u'Confirma aplica oferta en alumno oferta laboral: %s [%s] - empresa empleadora: %s - empleador: %s' % (aplicante, aplicante.id, empresaempleadora, empleador), request, "edit")
                        send_html_mail("Cita confirmada por candidato", "emails/citaconfirmada.html", {'sistema': 'SGAEST','registro': aplicante, 't': miinstitucion(), 'dominio': EMAIL_DOMAIN}, empleador.persona.lista_emails_envio(), [], cuenta=CUENTAS_CORREOS[4][1])

                        aData = {

                        }
                        return Helper_Response(isSuccess=True, data=aData, status=status.HTTP_200_OK)
                    except Exception as ex:
                        transaction.set_rollback(True)
                        return Helper_Response(isSuccess=False, data={}, message=f'Ocurrio un error: {ex.__str__()}', status=status.HTTP_200_OK)


            return Helper_Response(isSuccess=False, data={}, message=f'Acciòn no encontrada', status=status.HTTP_200_OK)
        except Exception as ex:
            return Helper_Response(isSuccess=False, data={}, message=f'Ocurrio un error: {ex.__str__()}',
                                   status=status.HTTP_200_OK)

    @api_security
    def get(self, request):
        try:
            aOfertas = []
            payload = request.auth.payload
            ePerfilUsuario = PerfilUsuario.objects.get(pk=encrypt(payload['perfilprincipal']['id']))
            if not ePerfilUsuario.es_estudiante():
                raise NameError(u'Solo los perfiles de estudiantes pueden ingresar al modulo.')
            if not 'id' in payload['matricula']:
                raise NameError(u'No se encuentra matriculado.')
            if 'id' in payload['matricula'] and payload['matricula']['id']:
                eMatricula = Matricula.objects.get(pk=encrypt(payload['matricula']['id']))
                if PeriodoMatricula.objects.values('id').filter(status=True, activo=True, periodo=eMatricula.nivel.periodo).exists():
                    ePeriodoMatricula = PeriodoMatricula.objects.get(status=True, activo=True, periodo=eMatricula.nivel.periodo)

            eMatricula = Matricula.objects.get(pk=encrypt(payload['matricula']['id']))
            eIncripcion = eMatricula.inscripcion
            idinscripcion = eIncripcion.id

            if eIncripcion.usado_graduados():
                ofertas = OfertaLaboral.objects.filter(cerrada=False, fin__gte=datetime.now().date())
            else:
                ofertas = OfertaLaboral.objects.filter(cerrada=False, graduado=False, fin__gte=datetime.now().date())

            for ofer in ofertas:
                aplicacion_data = None
                observaciones_data = None
                ofertas_data = OfertaLaboralSerializer(ofer).data
                if ofer.aplicanteoferta_set.filter(inscripcion=eIncripcion, oferta=ofer).exists():
                    eOfertaAplicacion = ofer.aplicanteoferta_set.filter(inscripcion=eIncripcion, oferta=ofer)[0]
                    aplicacion_data = AplicanteOfertaSerializer(eOfertaAplicacion).data
                if AplicanteOfertaObservacion.objects.filter(status=True, aplicanteoferta__inscripcion=eIncripcion,
                                                         aplicanteoferta__oferta=ofer).exists():
                    eObservaciones = AplicanteOfertaObservacion.objects.filter(status=True, aplicanteoferta__inscripcion=eIncripcion,
                                                         aplicanteoferta__oferta=self).order_by('id')
                    observaciones_data = AplicanteOfertaObservacionSerializer(eObservaciones).data
                ofertas_data.__setitem__('observaciones', observaciones_data)
                ofertas_data.__setitem__('esta_registrado', aplicacion_data)
                aOfertas.append(ofertas_data)

            data = {
                'eOfertas': aOfertas,
                'idinscrip': idinscripcion
            }
            return Helper_Response(isSuccess=True, data=data, status=status.HTTP_200_OK)
        except Exception as ex:
            return Helper_Response(isSuccess=False, data={}, message=f'Ocurrio un error: {ex.__str__()}', status=status.HTTP_200_OK)
