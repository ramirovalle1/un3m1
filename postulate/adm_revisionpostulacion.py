import json
import random
import sys

from django.contrib import messages
from django.contrib.admin.models import LogEntry
from django.contrib.auth.decorators import login_required
from django.contrib.contenttypes.models import ContentType
from django.template.loader import get_template
from django.forms import model_to_dict

from bd.models import LogEntryLogin
from decorators import last_access, secure_module
from django.template import Context
from django.db import transaction
from django.http import HttpResponseRedirect, JsonResponse, HttpResponse
from django.shortcuts import render
from django.db.models.query_utils import Q
from datetime import datetime
from postulate.models import Convocatoria, Partida, ConvocatoriaTerminosCondiciones, PartidaAsignaturas, PersonaAplicarPartida, PersonaIdiomaPartida, PersonaFormacionAcademicoPartida, PersonaExperienciaPartida, PersonaCapacitacionesPartida, PersonaPublicacionesPartida, CalificacionPostulacion, PartidaTribunal, PersonaApelacion
from postulate.postular import validar_campos
from sagest.models import Departamento
from settings import EMAIL_INSTITUCIONAL_AUTOMATICO, ACTUALIZAR_FOTO_ALUMNOS
from sga.commonviews import adduserdata, obtener_reporte
from postulate.forms import ConvocatoriaForm, PartidaForm, ConvocatoriaTerminosForm, RechazarPostulacionForm
from sga.funciones import log, MiPaginador, logobjeto
from sga.funcionesxhtml2pdf import conviert_html_to_pdf
from sga.models import AreaConocimientoTitulacion, SubAreaConocimientoTitulacion, \
    SubAreaEspecificaConocimientoTitulacion, Carrera, Asignatura, Titulo, miinstitucion, CUENTAS_CORREOS, \
    LogEntryBackup, LogEntryBackupdos
from sga.tasks import send_html_mail
from sga.templatetags.sga_extras import encrypt

from xlwt import *
import xlwt


@login_required(redirect_field_name='ret', login_url='/loginpostulate')
@secure_module
@last_access
# @transaction.atomic()
def view(request):
    global ex
    data = {}
    perfilprincipal = request.session['perfilprincipal']
    persona = request.session['persona']
    periodo = request.session['periodo']
    data['hoy'] = hoy = datetime.now().date()
    data['currenttime'] = datetime.now()
    data['perfil'] = persona.mi_perfil()
    data['periodo'] = periodo
    data['url_'] = request.path

    if request.method == 'POST':
        action = request.POST['action']

        if action == 'obsgradoacademico':
            try:
                instance = PersonaAplicarPartida.objects.get(id=int(request.POST['id']))
                instance.obsgradoacademico = request.POST['value']
                instance.save(request)
                logobjeto(u'{} : Observación Grado Academico'.format(instance.__str__()), request, "add",None,instance)
                return JsonResponse({"result": "ok"})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al obtener los datos. {}".format(str(ex))})

        if action == 'obsexperienciadoc':
            try:
                instance = PersonaAplicarPartida.objects.get(id=int(request.POST['id']))
                instance.obsexperienciadoc = request.POST['value']
                instance.save(request)
                logobjeto(u'{} : Observación Grado Academico'.format(instance.__str__()), request, "add",None,instance)
                return JsonResponse({"result": "ok"})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al obtener los datos. {}".format(str(ex))})

        if action == 'obsexperienciapro':
            try:
                instance = PersonaAplicarPartida.objects.get(id=int(request.POST['id']))
                instance.obsexperienciaadmin = request.POST['value']
                instance.save(request)
                logobjeto(u'{} : Observación Grado Academico'.format(instance.__str__()), request, "add",None,instance)
                return JsonResponse({"result": "ok"})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al obtener los datos. {}".format(str(ex))})

        if action == 'obscapacitacion':
            try:
                instance = PersonaAplicarPartida.objects.get(id=int(request.POST['id']))
                instance.obscapacitacion = request.POST['value']
                instance.save(request)
                logobjeto(u'{} : Observación Grado Academico'.format(instance.__str__()), request, "add",None,instance)
                return JsonResponse({"result": "ok"})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al obtener los datos. {}".format(str(ex))})

        if action == 'obsgeneral':
            try:
                instance = PersonaAplicarPartida.objects.get(id=int(request.POST['id']))
                instance.obsgeneral = request.POST['value']
                instance.save(request)
                logobjeto(u'{} : Observación Grado Academico'.format(instance.__str__()), request, "add",None,instance)
                return JsonResponse({"result": "ok"})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al obtener los datos. {}".format(str(ex))})

        if action == 'finalizarrevision':
            try:
                with transaction.atomic():
                    filtro = PersonaAplicarPartida.objects.get(id=int(request.POST['id']))
                    calificacion = CalificacionPostulacion.objects.filter(status=True, postulacion=filtro).order_by('-id').first()
                    if calificacion:
                        calificacion.valida = False
                        calificacion.save(request)
                    filtro.estado = request.POST['estado']
                    filtro.calificada = True
                    filtro.pgradoacademico = filtro.total_puntos_gradoacademico()
                    filtro.pcapacitacion = filtro.total_puntos_capacitacion()
                    filtro.pexpdocente = filtro.total_puntos_experiencia_docente()
                    filtro.pexpadministrativa = filtro.total_puntos_experiencia_administrativo()
                    filtro.nota_final_meritos = filtro.total_puntos()
                    filtro.revisado_por = request.user
                    filtro.fecha_revision = datetime.now()
                    filtro.save(request)
                    calificacion = CalificacionPostulacion(postulacion=filtro)
                    calificacion.pgradoacademico = filtro.total_puntos_gradoacademico()
                    calificacion.obsgradoacademico = filtro.obsgradoacademico
                    calificacion.pcapacitacion = filtro.total_puntos_capacitacion()
                    calificacion.obscapacitacion = filtro.obscapacitacion
                    calificacion.pexpdocente = filtro.total_puntos_experiencia_docente()
                    calificacion.obsexperienciadoc = filtro.obsexperienciadoc
                    calificacion.pexpadministrativa = filtro.total_puntos_experiencia_administrativo()
                    calificacion.pexpadministrativa = filtro.pexpadministrativa
                    calificacion.nota_final = filtro.total_puntos()
                    calificacion.obsgeneral = filtro.obsgeneral
                    calificacion.revisado_por = request.user
                    calificacion.estado = request.POST['estado']
                    calificacion.fecha_revision = datetime.now()
                    calificacion.valida = True
                    calificacion.save(request)
                    logobjeto(u'Finalizo Revisión de Postulación: %s' % filtro, request, "add",None,filtro)
                    res_json = {"error": False}
            except Exception as ex:
                res_json = {'error': True, "message": "Error: {}".format(ex)}
            return JsonResponse(res_json, safe=False)

        if action == 'reversarcalificacion':
            try:
                with transaction.atomic():
                    filtro = PersonaAplicarPartida.objects.get(id=request.POST['id'])
                    filtro.aplico_desempate = False
                    filtro.calificada = False
                    filtro.estado = 0
                    filtro.pgradoacademico = 0
                    filtro.pcapacitacion = 0
                    filtro.pexpdocente = 0
                    filtro.pexpadministrativa = 0
                    filtro.nota_final_meritos = 0
                    filtro.save(request)
                    calificacion = CalificacionPostulacion.objects.filter(status=True, postulacion=filtro).order_by('-id').first()
                    calificacion.valida = False
                    calificacion.save(request)
                    logobjeto(u'Anulo Revisión de Postulación: %s' % filtro, request, "add",None,filtro)
                    res_json = {"error": False}
            except Exception as ex:
                res_json = {'error': True, "message": "Error: {}".format(ex)}
            return JsonResponse(res_json, safe=False)

        if action == 'reversarapelacion':
            try:
                with transaction.atomic():
                    filtro = PersonaAplicarPartida.objects.get(id=request.POST['id'])
                    apelacion = filtro.traer_apelacion()
                    apelacion.estado = 0
                    apelacion.save(request)
                    logobjeto(u'Anulo Revisión de Apelación: %s' % filtro, request, "add",None,filtro)
                    res_json = {"error": False}
            except Exception as ex:
                res_json = {'error': True, "message": "Error: {}".format(ex)}
            return JsonResponse(res_json, safe=False)

        if action == 'desempateadicional':
            try:
                instance = PersonaAplicarPartida.objects.get(id=int(request.POST['id']))
                instance.obdadicional = request.POST['value']
                instance.save(request)
                logobjeto(u'{} : Asunto Detalle Adicional'.format(instance.__str__()), request, "add",None,instance)
                return JsonResponse({"result": "ok"})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al obtener los datos. {}".format(str(ex))})

        if action == 'pdesempateadicional':
            try:
                instance = PersonaAplicarPartida.objects.get(id=int(request.POST['id']))
                instance.pdadicional = request.POST['value']
                instance.save(request)
                logobjeto(u'{} : Punto Adicional'.format(instance.__str__()), request, "add",None,instance)
                return JsonResponse({"result": "ok", "totaladicional": instance.total_puntos_desempate(), 'total_desempate': instance.total_desempate_calificacion()})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al obtener los datos. {}".format(str(ex))})

        if action == 'desempatecapacitacion':
            try:
                id, filtro, valor, total, icono_ = int(request.POST['id']), None, 0, 0, ''
                filtro = PersonaAplicarPartida.objects.get(id=id)
                estado='Aprobó'
                if filtro.valpdcapprof:
                    filtro.valpdcapprof = False
                    filtro.pdcapprof = 0
                    filtro.save(request)
                    icono_ = '<i  style="color: red">Rechazado</i>'
                    estado = 'Rechazó'
                else:
                    filtro.valpdcapprof = True
                    filtro.pdcapprof = 1
                    filtro.save(request)
                    icono_ = '<i style="color: green">Aceptado</i>'
                logobjeto(u'%s Desempate Puntos por Capacitacion Profesional: %s' % (estado,filtro), request, "edit",None,filtro)
                valor = filtro.pdcapprof
                total = filtro.total_puntos_desempate()
                total_desempate = filtro.total_desempate_calificacion()
                return JsonResponse({"result": "ok", "icono_": icono_, "valor": valor, "totaladicional": total, "total_desempate": total_desempate})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": "Error al actualizar."})

        if action == 'desempateidioma':
            try:
                id, filtro, valor, total, icono_ = int(request.POST['id']), None, 0, 0, ''
                filtro = PersonaAplicarPartida.objects.get(id=id)
                estado ='Aprobó'
                if filtro.valpdidioma:
                    filtro.valpdidioma = False
                    filtro.pdidioma = 0
                    filtro.save(request)
                    icono_ = '<i  style="color: red">Rechazado</i>'
                    estado = 'Rechazó'

                else:
                    filtro.valpdidioma = True
                    filtro.pdidioma = 2
                    filtro.save(request)
                    icono_ = '<i style="color: green">Aceptado</i>'
                logobjeto(u'%s Desempate Puntos por Idiomas: %s' % (estado,filtro), request, "edit",None,filtro)
                valor = filtro.pdidioma
                total = filtro.total_puntos_desempate()
                total_desempate = filtro.total_desempate_calificacion()
                return JsonResponse({"result": "ok", "icono_": icono_, "valor": valor, "totaladicional": total, "total_desempate": total_desempate})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": "Error al actualizar."})

        if action == 'desempatepublicacion1':
            try:
                id, filtro, valor, total, icono_ = int(request.POST['id']), None, 0, 0, ''
                filtro = PersonaAplicarPartida.objects.get(id=id)
                estado = 'Aprobó'
                if filtro.valpdepub1:
                    filtro.valpdepub1 = False
                    filtro.pdepub1 = 0
                    filtro.save(request)
                    icono_ = '<i  style="color: red">Rechazado</i>'
                    estado = 'Rechazó'

                else:
                    filtro.valpdepub1 = True
                    filtro.pdepub1 = 1
                    filtro.save(request)
                    icono_ = '<i style="color: green">Aceptado</i>'
                logobjeto(u'%s Desempate Puntos por Publicación 1: %s' % (estado,filtro), request, "edit",None,filtro)
                valor = filtro.pdepub1
                total = filtro.total_puntos_desempate()
                total_desempate = filtro.total_desempate_calificacion()
                return JsonResponse({"result": "ok", "icono_": icono_, "valor": valor, "totaladicional": total, "total_desempate": total_desempate})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": "Error al actualizar."})

        if action == 'desempatepublicacion2':
            try:
                id, filtro, valor, total, icono_ = int(request.POST['id']), None, 0, 0, ''
                filtro = PersonaAplicarPartida.objects.get(id=id)
                estado = 'Aprobó'
                if filtro.valpdepub2:
                    filtro.valpdepub2 = False
                    filtro.pdepub2 = 0
                    filtro.save(request)
                    icono_ = '<i  style="color: red">Rechazado</i>'
                    estado = 'Rechazó'
                else:
                    filtro.valpdepub2 = True
                    filtro.pdepub2 = 1
                    filtro.save(request)
                    icono_ = '<i style="color: green">Aceptado</i>'
                logobjeto(u'%s Desempate Puntos por Publicación 2: %s' % (estado,filtro), request, "edit",None,filtro)
                valor = filtro.pdepub2
                total = filtro.total_puntos_desempate()
                total_desempate = filtro.total_desempate_calificacion()
                return JsonResponse({"result": "ok", "icono_": icono_, "valor": valor, "totaladicional": total, "total_desempate": total_desempate})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": "Error al actualizar."})

        if action == 'desempatecongreso':
            try:
                id, filtro, valor, total, icono_ = int(request.POST['id']), None, 0, 0, ''
                filtro = PersonaAplicarPartida.objects.get(id=id)
                estado = 'Aprobó'
                if filtro.valpdecongreso:
                    filtro.valpdecongreso = False
                    filtro.pdecongreso = 0
                    filtro.save(request)
                    icono_ = '<i  style="color: red">Rechazado</i>'
                    estado = 'Rechazó'
                else:
                    filtro.valpdecongreso = True
                    filtro.pdecongreso = 1
                    filtro.save(request)
                    icono_ = '<i style="color: green">Aceptado</i>'
                logobjeto(u'%s Desempate Puntos por Congreso: %s' % (estado,filtro), request, "edit",None,filtro)
                valor = filtro.pdecongreso
                total = filtro.total_puntos_desempate()
                total_desempate = filtro.total_desempate_calificacion()
                return JsonResponse({"result": "ok", "icono_": icono_, "valor": valor, "totaladicional": total, "total_desempate": total_desempate})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": "Error al actualizar."})

        if action == 'desempateaccionafirmativa':
            try:
                id, filtro, valor, total, icono_ = int(request.POST['id']), None, 0, 0, ''
                filtro = PersonaAplicarPartida.objects.get(id=id)
                estado='Aprobó'
                if filtro.valpdaccionafirmativa:
                    filtro.valpdaccionafirmativa = False
                    filtro.pdaccionafirmativa = 0
                    filtro.save(request)
                    estado = 'Rechazó'
                    icono_ = '<i  style="color: red">Rechazado</i>'
                else:
                    filtro.valpdaccionafirmativa = True
                    filtro.pdaccionafirmativa = 1
                    filtro.save(request)
                    icono_ = '<i style="color: green">Aceptado</i>'
                logobjeto(u'%s Desempate Puntos por Acción Afirmativa: %s' % filtro, request, "edit",None,filtro)
                valor = filtro.pdaccionafirmativa
                total = filtro.total_puntos_desempate()
                total_desempate = filtro.total_desempate_calificacion()
                return JsonResponse({"result": "ok", "icono_": icono_, "valor": valor, "totaladicional": total, "total_desempate": total_desempate})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": "Error al actualizar."})

        if action == 'estcertificacionidiomas':
            try:
                activar, id, filtro, valor, icono_ = int(request.POST['activar']), int(request.POST['id']), None, 0, ''
                estado = 'Aprobó'
                if activar == 0:
                    if PersonaIdiomaPartida.objects.filter(id=id):
                        filtro = PersonaIdiomaPartida.objects.filter(id=id).first()
                        if filtro.aceptado:
                            filtro.aceptado = False
                            filtro.save(request)
                            icono_ = '<i  style="color: red">Rechazado</i>'
                            estado = 'Rechazó'
                        else:
                            filtro.aceptado = True
                            filtro.save(request)
                            icono_ = '<i style="color: green">Aceptado</i>'
                elif activar == 1:
                    if PersonaIdiomaPartida.objects.filter(id=id):
                        filtro = PersonaIdiomaPartida.objects.filter(id=id).first()
                        filtro.aceptado = True
                        filtro.save(request)
                        estado = 'Aprobó todas'

                elif activar == 2:
                    if PersonaIdiomaPartida.objects.filter(id=id):
                        filtro = PersonaIdiomaPartida.objects.filter(id=id).first()
                        filtro.aceptado = False
                        filtro.save(request)
                        estado = 'Rechazó todas'

                logobjeto(u'%s las Certificación Idiomas: %s' % (estado,filtro), request, "edit",None,filtro)
                return JsonResponse({"result": "ok", "icono_": icono_})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": "Error al actualizar."})

        if action == 'estformacionacademica':
            try:
                activar, id, filtro, valor, total, icono_ = int(request.POST['activar']), int(request.POST['id']), None, 0, 0, ''
                estado = 'Aprobó'
                if activar == 0:
                    if PersonaFormacionAcademicoPartida.objects.filter(id=id):
                        filtro = PersonaFormacionAcademicoPartida.objects.filter(id=id).first()
                        if filtro.aceptado:
                            filtro.aceptado = False
                            filtro.save(request)
                            icono_ = '<i  style="color: red">Rechazado</i>'
                            estado = 'Rechazó'
                        else:
                            filtro.aceptado = True
                            filtro.save(request)
                            icono_ = '<i style="color: green">Aceptado</i>'
                elif activar == 1:
                    if PersonaFormacionAcademicoPartida.objects.filter(id=id):
                        filtro = PersonaFormacionAcademicoPartida.objects.filter(id=id).first()
                        filtro.aceptado = True
                        filtro.save(request)
                        estado = 'Aprobó todas'
                elif activar == 2:
                    if PersonaFormacionAcademicoPartida.objects.filter(id=id):
                        filtro = PersonaFormacionAcademicoPartida.objects.filter(id=id).first()
                        filtro.aceptado = False
                        filtro.save(request)
                        estado = 'Rechazó todas'

                logobjeto(u'%s las Formación Academica: %s' % (estado,filtro), request, "edit",None,filtro.personapartida)
                if filtro:
                    postulacion = PersonaAplicarPartida.objects.get(pk=filtro.personapartida.id)
                    valor = postulacion.total_puntos_gradoacademico()
                    total = postulacion.total_puntos()
                return JsonResponse({"result": "ok", "icono_": icono_, "valor": valor, "total": total})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": "Error al actualizar."})

        if action == 'estcapacitacion':
            try:
                activar, id, filtro, valor, total, icono_ = int(request.POST['activar']), int(request.POST['id']), None, 0, 0, ''
                estado = 'Aprobó'
                if activar == 0:
                    if PersonaCapacitacionesPartida.objects.filter(id=id):
                        filtro = PersonaCapacitacionesPartida.objects.filter(id=id).first()
                        if filtro.aceptado:
                            filtro.aceptado = False
                            filtro.save(request)
                            icono_ = '<i  style="color: red">Rechazado</i>'
                            estado = 'Rechazó'
                        else:
                            filtro.aceptado = True
                            filtro.save(request)
                            icono_ = '<i style="color: green">Aceptado</i>'
                elif activar == 1:
                    if PersonaCapacitacionesPartida.objects.filter(id=id):
                        filtro = PersonaCapacitacionesPartida.objects.filter(id=id).first()
                        filtro.aceptado = True
                        filtro.save(request)
                        estado = 'Aprobó todas'

                elif activar == 2:
                    if PersonaCapacitacionesPartida.objects.filter(id=id):
                        filtro = PersonaCapacitacionesPartida.objects.filter(id=id).first()
                        filtro.aceptado = False
                        filtro.save(request)
                        estado = 'Rechazó todas'

                logobjeto(u'%s las Capacitaciones: %s' % (estado,filtro), request, "edit",None,filtro.personapartida)
                if filtro:
                    postulacion = PersonaAplicarPartida.objects.get(pk=filtro.personapartida.id)
                    valor = postulacion.total_puntos_capacitacion()
                    total = postulacion.total_puntos()
                return JsonResponse({"result": "ok", "icono_": icono_, "valor": valor, "total": total})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": "Error al actualizar."})

        if action == 'estexperiencia':
            try:
                activar, id, filtro, valoradm, valordoc, total, icono_ = int(request.POST['activar']), int(request.POST['id']), None, 0, 0, 0, ''
                estado = 'Aprobó'
                if activar == 0:
                    if PersonaExperienciaPartida.objects.filter(id=id):
                        filtro = PersonaExperienciaPartida.objects.filter(id=id).first()
                        if filtro.aceptado:
                            filtro.aceptado = False
                            filtro.save(request)
                            icono_ = '<i  style="color: red">Rechazado</i>'
                            estado = 'Rechazó'
                        else:
                            filtro.aceptado = True
                            filtro.save(request)
                            icono_ = '<i style="color: green">Aceptado</i>'
                elif activar == 1:
                    if PersonaExperienciaPartida.objects.filter(id=id):
                        filtro = PersonaExperienciaPartida.objects.filter(id=id).first()
                        filtro.aceptado = True
                        filtro.save(request)
                        estado = 'Aprobó todas'
                elif activar == 2:
                    if PersonaExperienciaPartida.objects.filter(id=id):
                        filtro = PersonaExperienciaPartida.objects.filter(id=id).first()
                        filtro.aceptado = False
                        filtro.save(request)
                        estado = 'Rechazó todas'

                logobjeto(u'%s todas las Experiencia: %s' % (estado,filtro), request, "edit",None,filtro.personapartida)
                if filtro:
                    postulacion = PersonaAplicarPartida.objects.get(pk=filtro.personapartida.id)
                    valoradm = postulacion.total_puntos_experiencia_administrativo()
                    valordoc = postulacion.total_puntos_experiencia_docente()
                    total = postulacion.total_puntos()
                return JsonResponse({"result": "ok", "icono_": icono_, "valoradm": valoradm, "valordoc": valordoc, "total": total})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": "Error al actualizar."})

        if action == 'estpublicacion':
            try:
                activar, id, filtro, valor, icono_ = int(request.POST['activar']), int(request.POST['id']), None, 0, ''
                estado = 'Aprobó'
                if activar == 0:
                    if PersonaPublicacionesPartida.objects.filter(id=id):
                        filtro = PersonaPublicacionesPartida.objects.filter(id=id).first()
                        if filtro.aceptado:
                            filtro.aceptado = False
                            filtro.save(request)
                            icono_ = '<i  style="color: red">Rechazado</i>'
                            estado = 'Rechazó'
                        else:
                            filtro.aceptado = True
                            filtro.save(request)
                            icono_ = '<i style="color: green">Aceptado</i>'
                elif activar == 1:
                    if PersonaPublicacionesPartida.objects.filter(id=id):
                        filtro = PersonaPublicacionesPartida.objects.filter(id=id).first()
                        filtro.aceptado = True
                        filtro.save(request)
                        estado = 'Aprobó todas'
                elif activar == 2:
                    if PersonaPublicacionesPartida.objects.filter(id=id):
                        filtro = PersonaPublicacionesPartida.objects.filter(id=id).first()
                        filtro.aceptado = False
                        filtro.save(request)
                        estado = 'Rechazó todas'

                logobjeto(u'%s las Publicaciones: %s' % (estado,filtro), request, "edit",None,filtro.personapartida)
                return JsonResponse({"result": "ok", "icono_": icono_})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": "Error al actualizar."})

        if action == 'finalizardesempate':
            try:
                with transaction.atomic():
                    filtro = PersonaAplicarPartida.objects.get(id=int(request.POST['id']))
                    filtro.aplico_desempate = True
                    filtro.pdmaestria = filtro.total_desempate_maestria()
                    filtro.pdphd = filtro.total_desempate_phd()
                    filtro.pdexpdocente = filtro.total_desempate_experiencia_docente()
                    filtro.pdcappeda = filtro.total_desempate_capacitacion()
                    filtro.desempate_revisado_por = request.user
                    filtro.desempate_fecha_revision = datetime.now()
                    filtro.nota_calificacion = filtro.total_puntos()
                    filtro.nota_desempate = filtro.total_puntos_desempate()
                    filtro.nota_final_meritos = filtro.total_desempate_calificacion()
                    filtro.save(request)
                    calificacion_ = filtro.calificacionpostulacion_set.filter(status=True, valida=True).order_by('-id').last()
                    if calificacion_:
                        calificacion_.aplico_desempate = True
                        calificacion_.pdmaestria = filtro.total_desempate_maestria()
                        calificacion_.pdphd = filtro.total_desempate_phd()
                        calificacion_.pdexpdocente = filtro.total_desempate_experiencia_docente()
                        calificacion_.pdcappeda = filtro.total_desempate_capacitacion()
                        calificacion_.valpdcapprof = filtro.valpdcapprof
                        calificacion_.pdcapprof = filtro.pdcapprof
                        calificacion_.valpdidioma = filtro.valpdidioma
                        calificacion_.pdidioma = filtro.pdidioma
                        calificacion_.valpdepub1 = filtro.valpdepub1
                        calificacion_.pdepub1 = filtro.pdepub1
                        calificacion_.valpdepub2 = filtro.valpdepub2
                        calificacion_.pdepub2 = filtro.pdepub2
                        calificacion_.valpdecongreso = filtro.valpdecongreso
                        calificacion_.pdecongreso = filtro.pdecongreso
                        calificacion_.valpdaccionafirmativa = filtro.valpdaccionafirmativa
                        calificacion_.pdaccionafirmativa = filtro.pdaccionafirmativa
                        calificacion_.obdadicional = filtro.obdadicional
                        calificacion_.pdadicional = filtro.pdadicional
                        calificacion_.desempate_revisado_por = request.user
                        calificacion_.desempate_fecha_revision = datetime.now()
                        calificacion_.nota_meritos = filtro.nota_final
                        calificacion_.nota_desempate = filtro.total_puntos_desempate()
                        calificacion_.nota_final = filtro.total_desempate_calificacion()
                        calificacion_.save(request)
                    logobjeto(u'Finalizo Revisión de Desempate Postulación: %s' % filtro, request, "add",None,filtro)
                    res_json = {"error": False}
            except Exception as ex:
                res_json = {'error': True, "message": "Error: {}".format(ex)}
            return JsonResponse(res_json, safe=False)

        if action == 'anulardesempate':
            try:
                with transaction.atomic():
                    filtro = PersonaAplicarPartida.objects.get(id=int(request.POST['id']))
                    filtro.aplico_desempate = False
                    filtro.save(request)
                    logobjeto(u'Finalizo Anulación de Desempate Postulación: %s' % filtro, request, "del",None,filtro)
                    res_json = {"error": False}
            except Exception as ex:
                res_json = {'error': True, "message": "Error: {}".format(ex)}
            return JsonResponse(res_json, safe=False)

        if action == 'calculapuntuados':
            try:
                with transaction.atomic():
                    filtro = Partida.objects.get(id=int(request.POST['id']))
                    filtro.personaaplicarpartida_set.filter(status=True, esmejorpuntuado=True).update(esmejorpuntuado=False)
                    mejores = filtro.personaaplicarpartida_set.values_list('id',flat=True).filter(status=True, estado__in=[1, 4, 5]).order_by(
                        '-nota_final_meritos')[:filtro.convocatoria.nummejorespuntuados]
                    actualizamejores=PersonaAplicarPartida.objects.filter(id__in=mejores)
                    actualizamejores.update(esmejorpuntuado=True)
                    logobjeto(u'Finalizo calculo de mejores puntuados: %s' % filtro, request, "del",None,filtro)
                    res_json = {"error": False}
            except Exception as ex:
                res_json = {'error': True, "message": "Error: {}".format(ex)}
            return JsonResponse(res_json, safe=False)

        if action == 'finalizarapelacion':
            try:
                with transaction.atomic():
                    filtro = PersonaApelacion.objects.get(id=int(request.POST['id']))
                    filtro.observacion_revisor = request.POST['observacion']
                    filtro.estado = request.POST['estado']
                    filtro.revisado_por = request.user
                    filtro.fecha_revision = datetime.now()
                    filtro.save(request)
                    logobjeto(u'Finalizo Revisión de Apelación Postulación: %s' % filtro, request, "add",None,filtro)
                    res_json = {"error": False, "idpostulacion": filtro.personapartida.id}
            except Exception as ex:
                res_json = {'error': True, "message": "Error: {}".format(ex)}
            return JsonResponse(res_json, safe=False)

        if action == 'mailterminacionrevision':
            try:
                with transaction.atomic():
                    convo = Convocatoria.objects.get(id=int(request.POST['id']))
                    fil = convo.partida_set.filter(status=True, vigente=True)
                    for filtro in fil:
                        cont=0
                        for post_ in filtro.participantes():
                            cont+=1
                            personaemail_=[]
                            if post_.persona.email:
                                personaemail_.append(post_.persona.email)
                            if cont<=1:
                                personaemail_.append('rviterib1@unemi.edu.ec')
                            if personaemail_.__len__()>0:
                                send_html_mail("Postulate: Terminación de Revisión", "emails/postulate_primeraetapa.html",
                                               {'sistema': u'SISTEMA POSTULATE UNEMI', 'persona': post_.persona, 'partida': filtro,
                                                't': miinstitucion()}, personaemail_, [], cuenta=CUENTAS_CORREOS[30][1])
                        logobjeto(u'Notificación Finalización de Revisión: %s' % filtro, request, "add",None,filtro)
                    res_json = {"error": False}
            except Exception as ex:
                res_json = {'error': True, "message": "Error: {}".format(ex)}
            return JsonResponse(res_json, safe=False)

        if action == 'm_mailterminacionrevision':
            try:
                with transaction.atomic():
                    convo = Convocatoria.objects.get(id=int(request.POST['id_convocatoria_mensaje']))
                    contenido_body = request.POST['mensajecontenido']
                    #apelacion = request.POST['postulanteapelacion']
                    option = None
                    if 'envio_opciones' in request.POST:
                        option = int(request.POST['envio_opciones'])
                    if not option:
                        raise NameError("Seleccione que tipo de correo va enviar: Fin de aplicación, Fn de apelación, Prueba técnica")
                    if option == 1:
                        fil = convo.partida_set.filter(status=True, vigente=True)
                        for filtro in fil:
                            cont=0
                            for post_ in filtro.participantes():
                                cont += 1
                                personaemail_ = []
                                if post_.persona.email:
                                    personaemail_.append(post_.persona.email)
                                if cont <= 1:
                                    personaemail_.append('rviterib1@unemi.edu.ec')
                                if personaemail_:
                                    send_html_mail("Postulate: Terminación de Revisión",
                                                   "emails/postulate_primeraetapa_new.html",
                                                   {'sistema': u'SISTEMA POSTULATE UNEMI', 'persona': post_.persona,
                                                    'partida': filtro, 'contenido': contenido_body,
                                                    't': miinstitucion()}, [personaemail_], [],
                                                   cuenta=CUENTAS_CORREOS[30][1])
                            logobjeto(u'Notificación Finalización de Revisión: %s' % filtro, request, "add", None, filtro)
                    elif option == 2:
                        fil = convo.partida_set.filter(status=True, convocatoria__apelacion=True)
                        for filtro in fil.filter(personaaplicarpartida__solapelacion=True).distinct()[:1]:
                            cont=0
                            for post_ in filtro.participantes_apelando():
                                cont += 1
                                personaemail_ = []
                                if post_.persona.email:
                                    personaemail_.append(post_.persona.email)
                                if cont <= 1:
                                    personaemail_.append('rviterib1@unemi.edu.ec')
                                if personaemail_:
                                    send_html_mail("Postulate: Terminación de Apelación",
                                                   "emails/postulate_segundoetapa.html",
                                                   {'sistema': u'SISTEMA POSTULATE UNEMI', 'persona': post_.persona,
                                                    'partida': filtro, 'contenido': contenido_body,
                                                    't': miinstitucion()}, [personaemail_], [],
                                                   cuenta=CUENTAS_CORREOS[30][1])
                            filtro.save(request)
                            logobjeto(u'Notificación Finalización de Apelación: %s' % filtro, request, "add", None,filtro)
                    elif option == 3:
                        fil = convo.partida_set.filter(status=True, vigente=True)
                        for filtro in fil[:1]:
                            cont=0
                            for post_ in filtro.participantes_mejores_puntuados():
                                cont += 1
                                personaemail_ = []
                                if post_.persona.email:
                                    personaemail_.append(post_.persona.email)
                                # if cont <= 1:
                                #     personaemail_.append('rviterib1@unemi.edu.ec')
                                if personaemail_:
                                    send_html_mail("Postulate: Prueba Técnica",
                                                   "emails/postulate_pt_new.html",
                                                   {'sistema': u'SISTEMA POSTULATE UNEMI', 'persona': post_.persona,
                                                    'partida': filtro, 'contenido': contenido_body,
                                                    't': miinstitucion()}, [personaemail_], [],
                                                   cuenta=CUENTAS_CORREOS[30][1])
                            logobjeto(u'Notificación Prueba Tecnica: %s' % filtro, request, "add", None, filtro)
                res_json = {"error": False}
            except Exception as ex:
                res_json = {'error': True, "message": "Error: {}".format(ex)}
            return JsonResponse(res_json, safe=False)

        if action == 'mailterminacionapelacion':
            try:
                with transaction.atomic():
                    convo = Convocatoria.objects.get(id=int(request.POST['id']))
                    fil = convo.partida_set.filter(status=True, convocatoria__apelacion=True)
                    for filtro in fil:
                        for post_ in filtro.participantes_apelando():
                            personaemail_ = post_.persona.email if post_.persona.email else None
                            if personaemail_:
                                send_html_mail("Postulate: Terminación de Apelación", "emails/postulate_segundoetapa.html",
                                               {'sistema': u'SISTEMA POSTULATE UNEMI', 'persona': post_.persona, 'partida': filtro,
                                                't': miinstitucion()}, [personaemail_], [], cuenta=CUENTAS_CORREOS[30][1])
                        filtro.save(request)
                        logobjeto(u'Notificación Finalización de Apelación: %s' % filtro, request, "add",None,filtro)
                    res_json = {"error": False}
            except Exception as ex:
                res_json = {'error': True, "message": "Error: {}".format(ex)}
            return JsonResponse(res_json, safe=False)

        if action == 'rechazarpostulacion':
            try:
                with transaction.atomic():
                    filtro = PersonaAplicarPartida.objects.get(id=int(encrypt(request.POST['id'])))
                    filtro.estado = 2
                    filtro.calificada = True
                    filtro.obsgradoacademico = request.POST['observacion']
                    filtro.revisado_por = request.user
                    filtro.fecha_revision = datetime.now()
                    filtro.save(request)
                    calificacion = CalificacionPostulacion(postulacion=filtro)
                    calificacion.obsgradoacademico = filtro.obsgradoacademico
                    calificacion.revisado_por = request.user
                    calificacion.estado = 2
                    calificacion.fecha_revision = datetime.now()
                    calificacion.valida = True
                    calificacion.save(request)
                    logobjeto(u'Rechazo postulación Postulación: %s' % filtro, request, "edit",None,filtro)
                    res_json = {"error": False}
            except Exception as ex:
                res_json = {'error': True, "message": "Error: {}".format(ex)}
            return JsonResponse(res_json, safe=False)


        return JsonResponse({"result": "bad", "mensaje": u"Solicitud Incorrecta."})
    else:
        adduserdata(request, data)
        if 'action' in request.GET:
            data['action'] = action = request.GET['action']

            if action == 'reloadpostulante':
                try:
                    data['postulante'] = postulante = PersonaAplicarPartida.objects.get(pk=request.GET['id'])
                    template_datos = get_template("postulate/adm_revisionpostulacion/reloaddatos.html")
                    template_btn = get_template("postulate/adm_revisionpostulacion/reloadbtn.html")
                    template_estado = get_template("postulate/adm_revisionpostulacion/reloadestado.html")
                    template_apelacion = get_template("postulate/adm_revisionpostulacion/reloadapelacion.html")
                    return JsonResponse({"result": True, 'data_estado': template_estado.render(data), 'data_datos': template_datos.render(data), 'data_btn': template_btn.render(data), 'data_apelacion': template_apelacion.render(data)})
                except Exception as ex:
                    pass

            if action == 'buscarpartidas':
                try:
                    convocatoria = Convocatoria.objects.get(pk=request.GET['convocatoria'])
                    qspartidas = Partida.objects.filter(convocatoria=convocatoria, status=True)
                    validarpartidas = True
                    departamentogestion = Departamento.objects.filter(status=True, permisodepartamento=2)
                    if departamentogestion.exists():
                        if departamentogestion.first().mis_integrantes().filter(id=persona.pk).exists():
                            validarpartidas = False
                    if request.user.is_superuser:
                        validarpartidas = False
                    if validarpartidas:
                        idsmispartidas = PartidaTribunal.objects.filter(status=True, persona=persona, tipo=1).values_list('partida_id', flat=True)
                        qspartidas = qspartidas.filter(id__in=idsmispartidas)
                    data['partidas'] = qspartidas.order_by('codpartida')
                    template = get_template("postulate/adm_revisionpostulacion/cbpartidas.html")
                    return JsonResponse({"result": True, 'data': template.render(data)})
                except Exception as ex:
                    pass

            if action == 'consultarconvocatoria':
                try:
                    instance = Convocatoria.objects.get(id=int(request.GET['id']))
                    partida = instance.partida_set.filter(status=True, vigente=True).first()
                    return JsonResponse({"result": "ok", "convocatoria": instance.descripcion, 'nombre_partida': str(partida.denominacionpuesto) })
                except Exception as ex:
                    transaction.set_rollback(True)
                    return JsonResponse({"result": "bad", "mensaje": u"Error al obtener los datos. {}".format(str(ex))})

            if action == 'buscarpostulantes':
                try:
                    data['partida'] = partida = Partida.objects.get(pk=request.GET['partida'])
                    data['postulantes'] = PersonaAplicarPartida.objects.filter(partida=partida, status=True).order_by('id')
                    data['mejorespuntuados'] = partida.participantes_mejores_puntuados().count
                    template = get_template("postulate/adm_revisionpostulacion/postulantes.html")
                    return JsonResponse({"result": True, 'data': template.render(data)})
                except Exception as ex:
                    pass

            if action == 'buscarpostulantesapelacion':
                try:
                    data['partida'] = partida = Partida.objects.get(pk=request.GET['partida'])
                    data['postulantes'] = PersonaAplicarPartida.objects.filter(partida=partida, status=True, solapelacion=True).order_by('-id')
                    template = get_template("postulate/adm_revisionpostulacion/postulantes.html")
                    return JsonResponse({"result": True, 'data': template.render(data)})
                except Exception as ex:
                    pass

            if action == 'buscarpostulantesaprobados':
                try:
                    data['partida'] = partida = Partida.objects.get(pk=request.GET['partida'])
                    data['postulantes'] = PersonaAplicarPartida.objects.filter(Q(estado=1) | Q(esmejorpuntuado=True), partida=partida, status=True).order_by('-nota_final_meritos')
                    template = get_template("postulate/adm_revisionpostulacion/postulantes.html")
                    return JsonResponse({"result": True, 'data': template.render(data)})
                except Exception as ex:
                    pass

            if action == 'verdetallepostulante':
                try:
                    data['id'] = id = int(encrypt(request.GET['id']))
                    data['postulante'] = postulante = PersonaAplicarPartida.objects.get(pk=id)
                    data['partida'] = partida = Partida.objects.get(pk=postulante.partida.pk)
                    data['resp_campos'] = validar_campos(request, persona, partida)
                    data['reporte_1'] = obtener_reporte('hoja_vida_sagest')
                    data['persona'] = postulante.persona
                    data['posidiomas'] = PersonaIdiomaPartida.objects.filter(status=True, personapartida=postulante).order_by('id')
                    data['postitulacion'] = PersonaFormacionAcademicoPartida.objects.filter(status=True, personapartida=postulante).order_by('id')
                    data['posexperiencia'] = PersonaExperienciaPartida.objects.filter(status=True, personapartida=postulante).order_by('id')
                    data['poscapacitacion'] = PersonaCapacitacionesPartida.objects.filter(status=True, personapartida=postulante).order_by('id')
                    data['pospublicacion'] = PersonaPublicacionesPartida.objects.filter(status=True, personapartida=postulante).order_by('id')
                    template = get_template("postulate/adm_revisionpostulacion/verdetallepostulante.html")
                    return JsonResponse({"result": True, 'data': template.render(data)})
                except Exception as ex:
                    pass

            elif action == 'auditoria':
                try:
                    baseDate = datetime.today()
                    year = request.GET['year'] if 'year' in request.GET and request.GET['year'] else baseDate.year
                    # month = request.GET['month'] if 'month' in request.GET and request.GET[
                    #     'month'] else baseDate.month
                    data['idi'] = request.GET['id']
                    data['filtro'] = filtro = PersonaAplicarPartida.objects.get(pk=int(encrypt(request.GET['id'])))
                    aplicacion = filtro._meta.app_label
                    modelo = filtro._meta.model_name
                    contenido = ContentType.objects.filter(app_label=aplicacion, model=modelo).first()

                    logs = LogEntry.objects.filter(object_id=filtro.id, content_type=contenido.id,
                                                   action_time__year=year).exclude(user__is_superuser=True)
                    # if int(month):
                    #     logs = logs.filter(action_time__month=month)

                    logslist = list(logs.values_list("action_time", "action_flag", "change_message", "user__username"))
                    aLogList = []
                    for xItem in logslist:
                        # print(xItem)
                        if xItem[1] == 1:
                            action_flag = '<label class="label label-success">AGREGAR</label>'
                        elif xItem[1] == 2:
                            action_flag = '<label class="label label-info">EDITAR</label>'
                        elif xItem[1] == 3:
                            action_flag = '<label class="label label-important">ELIMINAR</label>'
                        else:
                            action_flag = '<label class="label label-warning">OTRO</label>'
                        aLogList.append({"action_time": xItem[0],
                                         "action_flag": action_flag,
                                         "change_message": xItem[2],
                                         "username": xItem[3]})
                    my_time = datetime.min.time()
                    datalogs = aLogList
                    data['logs'] = sorted(datalogs, key=lambda x: x['action_time'], reverse=True)
                    numYear = 6
                    dateListYear = []
                    for x in range(0, numYear):
                        dateListYear.append((baseDate.year) - x)
                    data['list_years'] = dateListYear
                    data['year_now'] = int(year)
                    template = get_template("postulate/adm_revisionpostulacion/auditoria.html")
                    return JsonResponse({"result": True, 'data': template.render(data)})
                except Exception as ex:
                    return JsonResponse({"result": "bad", "mensaje": u"Error al consultar los datos."})

            if action == 'calificar':
                try:
                    data['id'] = id = int(encrypt(request.GET['id']))
                    data['postulante'] = postulante = PersonaAplicarPartida.objects.get(pk=id)
                    data['partida'] = partida = Partida.objects.get(pk=postulante.partida.pk)

                    data['resp_campos'] = validar_campos(request, persona, partida)
                    data['persona'] = postulante.persona
                    data['posidiomas'] = posidiomas = PersonaIdiomaPartida.objects.filter(status=True, personapartida=postulante).order_by('id')
                    data['posidiomascheck'] = True if not posidiomas.filter(aceptado=False).exists() else False
                    data['postitulacion'] = postitulacion = PersonaFormacionAcademicoPartida.objects.filter(status=True, personapartida=postulante).order_by('id')

                    estados = ((1, u'ACEPTADO'), (2, u'RECHAZADO'),) if postitulacion.values('id').filter(titulo__nivel__nivel=partida.nivel, aceptado=True).exists() else ((2, u'RECHAZADO'),)

                    data['estados'] = estados

                    data['postitulacioncheck'] = True if not postitulacion.filter(aceptado=False).exists() else False
                    data['posexperiencia'] = posexperiencia = PersonaExperienciaPartida.objects.filter(status=True, personapartida=postulante).order_by('id')
                    data['posexperienciacheck'] = True if not posexperiencia.filter(aceptado=False).exists() else False
                    data['poscapacitacion'] = poscapacitacion = PersonaCapacitacionesPartida.objects.filter(status=True, personapartida=postulante).order_by('id')
                    data['poscapacitacioncheck'] = True if not poscapacitacion.filter(aceptado=False).exists() else False
                    data['pospublicacion'] = pospublicacion = PersonaPublicacionesPartida.objects.filter(status=True, personapartida=postulante).order_by('id')
                    data['pospublicacioncheck'] = True if not pospublicacion.filter(aceptado=False).exists() else False


                    data['titulos_partida'] = titulos_partida = partida.titulos.all()
                    data['aplicatitulo'] = postitulacion.filter(titulo__in=list(titulos_partida.values_list('id', flat=True))).exists()

                    template = get_template("postulate/adm_revisionpostulacion/calificar.html")
                    return JsonResponse({"result": True, 'data': template.render(data)})
                except Exception as ex:
                    return JsonResponse({"result": False, 'mensaje': str(ex)})

            if action == 'calificarapelacion':
                try:
                    data['id'] = id = int(encrypt(request.GET['id']))
                    data['postulante'] = postulante = PersonaAplicarPartida.objects.get(pk=id)
                    data['partida'] = partida = Partida.objects.get(pk=postulante.partida.pk)
                    data['resp_campos'] = validar_campos(request, persona, partida)
                    data['persona'] = postulante.persona
                    data['posidiomas'] = posidiomas = PersonaIdiomaPartida.objects.filter(status=True, personapartida=postulante).order_by('id')
                    data['posidiomascheck'] = True if not posidiomas.filter(aceptado=False).exists() else False
                    data['postitulacion'] = postitulacion = PersonaFormacionAcademicoPartida.objects.filter(status=True, personapartida=postulante).order_by('id')
                    data['postitulacioncheck'] = True if not postitulacion.filter(aceptado=False).exists() else False
                    data['posexperiencia'] = posexperiencia = PersonaExperienciaPartida.objects.filter(status=True, personapartida=postulante).order_by('id')
                    data['posexperienciacheck'] = True if not posexperiencia.filter(aceptado=False).exists() else False
                    data['poscapacitacion'] = poscapacitacion = PersonaCapacitacionesPartida.objects.filter(status=True, personapartida=postulante).order_by('id')
                    data['poscapacitacioncheck'] = True if not poscapacitacion.filter(aceptado=False).exists() else False
                    data['pospublicacion'] = pospublicacion = PersonaPublicacionesPartida.objects.filter(status=True, personapartida=postulante).order_by('id')
                    data['pospublicacioncheck'] = True if not pospublicacion.filter(aceptado=False).exists() else False
                    data['estados'] = estados = ESTADOS_APLICACION = ((1, u'ACEPTADO'), (2, u'RECHAZADO'),)
                    template = get_template("postulate/adm_revisionpostulacion/calificarapelacion.html")
                    return JsonResponse({"result": True, 'data': template.render(data)})
                except Exception as ex:
                    pass

            if action == 'vercalificaciones':
                try:
                    data['id'] = id = int(encrypt(request.GET['id']))
                    data['postulante'] = postulante = PersonaAplicarPartida.objects.get(pk=id)
                    data['listado'] = listado = postulante.calificacionpostulacion_set.filter(status=True).order_by('-pk')
                    template = get_template("postulate/adm_revisionpostulacion/calificacionespostulante.html")
                    return JsonResponse({"result": True, 'data': template.render(data)})
                except Exception as ex:
                    return JsonResponse({"result": False, 'mensaje': str(ex)})

            if action == 'vercalificar':
                try:
                    data['id'] = id = int(encrypt(request.GET['id']))
                    data['postulante'] = postulante = PersonaAplicarPartida.objects.get(pk=id)
                    data['partida'] = partida = Partida.objects.get(pk=postulante.partida.pk)
                    data['resp_campos'] = validar_campos(request, persona, partida)
                    data['persona'] = postulante.persona
                    data['posidiomas'] = posidiomas = PersonaIdiomaPartida.objects.filter(status=True, personapartida=postulante).order_by('id')
                    data['postitulacion'] = postitulacion = PersonaFormacionAcademicoPartida.objects.filter(status=True, personapartida=postulante).order_by('id')
                    data['posexperiencia'] = posexperiencia = PersonaExperienciaPartida.objects.filter(status=True, personapartida=postulante).order_by('id')
                    data['poscapacitacion'] = poscapacitacion = PersonaCapacitacionesPartida.objects.filter(status=True, personapartida=postulante).order_by('id')
                    data['pospublicacion'] = pospublicacion = PersonaPublicacionesPartida.objects.filter(status=True, personapartida=postulante).order_by('id')
                    template = get_template("postulate/adm_revisionpostulacion/vercalificacion.html")
                    return JsonResponse({"result": True, 'data': template.render(data)})
                except Exception as ex:
                    pass

            if action == 'verapelacion':
                try:
                    data['id'] = id = encrypt(request.GET['id'])
                    data['filtro'] = filtro = PersonaApelacion.objects.get(pk=id)
                    template = get_template("postulate/adm_revisionpostulacion/verapelacion.html")
                    return JsonResponse({"result": True, 'data': template.render(data)})
                except Exception as ex:
                    pass

            if action == 'validarapelacion':
                try:
                    data['id'] = id = encrypt(request.GET['id'])
                    data['filtro'] = filtro = PersonaApelacion.objects.get(pk=id)
                    data['estados'] = ESTADO_APELACION = ((1, u'ACEPTADO'),(2, u'RECHAZADO'))
                    template = get_template("postulate/adm_revisionpostulacion/validarapelacion.html")
                    return JsonResponse({"result": True, 'data': template.render(data)})
                except Exception as ex:
                    pass

            if action == 'desempate':
                try:
                    data['id'] = id = int(encrypt(request.GET['id']))
                    data['postulante'] = postulante = PersonaAplicarPartida.objects.get(pk=id)
                    if not postulante.calificada:
                        return JsonResponse({"result": False, 'mensaje': 'Partida no esta calificada, no aplica a desempate'})
                    data['partida'] = partida = Partida.objects.get(pk=postulante.partida.pk)
                    data['resp_campos'] = validar_campos(request, persona, partida)
                    data['persona'] = postulante.persona
                    data['posidiomas'] = posidiomas = PersonaIdiomaPartida.objects.filter(status=True, personapartida=postulante).order_by('id')
                    data['posidiomascheck'] = True if not posidiomas.filter(aceptado=False).exists() else False
                    data['postitulacion'] = postitulacion = PersonaFormacionAcademicoPartida.objects.filter(status=True, personapartida=postulante).order_by('id')
                    data['postitulacioncheck'] = True if not postitulacion.filter(aceptado=False).exists() else False
                    data['posexperiencia'] = posexperiencia = PersonaExperienciaPartida.objects.filter(status=True, personapartida=postulante).order_by('id')
                    data['posexperienciacheck'] = True if not posexperiencia.filter(aceptado=False).exists() else False
                    data['poscapacitacion'] = poscapacitacion = PersonaCapacitacionesPartida.objects.filter(status=True, personapartida=postulante).order_by('id')
                    data['poscapacitacioncheck'] = True if not poscapacitacion.filter(aceptado=False).exists() else False
                    data['pospublicacion'] = pospublicacion = PersonaPublicacionesPartida.objects.filter(status=True, personapartida=postulante).order_by('id')
                    data['pospublicacioncheck'] = True if not pospublicacion.filter(aceptado=False).exists() else False
                    data['estados'] = estados = ESTADOS_APLICACION = ((1, u'ACEPTADO'), (2, u'RECHAZADO'),)
                    template = get_template("postulate/adm_revisionpostulacion/desempatar.html")
                    return JsonResponse({"result": True, 'data': template.render(data)})
                except Exception as ex:
                    pass

            if action == 'excel_postulantes__all':
                try:
                    response = HttpResponse(content_type='application/ms-excel')
                    response['Content-Disposition'] = 'attachment; filename="postulantes_all.xls"'
                    title = easyxf('font: name Calibri, color-index black, bold on , height 350; alignment: horiz centre')
                    title2 = easyxf('font: name Calibri, color-index black, bold on , height 250; alignment: horiz centre')
                    font_style = xlwt.XFStyle()
                    font_style.font.bold = True
                    fuentecabecera = easyxf('font: name Calibri, color-index black, bold on; pattern: pattern solid, fore_colour gray25; alignment: horiz centre; borders: left thin, right thin, top thin, bottom thin')
                    fuentenormal = easyxf('font: name Calibri, color-index black, height 150; borders: left thin, right thin, top thin, bottom thin')
                    style2 = easyxf('borders: left thin, right thin, top thin, bottom thin; alignment: horiz centre')
                    wb = xlwt.Workbook(encoding='utf-8')
                    ws = wb.add_sheet('postulantes')
                    ws.write_merge(0, 0, 0, 8, 'UNIVERSIDAD ESTATAL ESTATAL DE MILAGRO', title)
                    ws.write_merge(1, 1, 0, 8, 'LISTADO DE POSTULANTES', title2)
                    row_num = 2
                    columns = [
                        ('Convocatoria', 10000),
                        ('Categoria', 10000),
                        ('Partida', 30000),
                        ('Carrera', 30000),
                        ('Asignaturas', 30000),
                        ('Dedicación', 10000),
                        ('RMU', 10000),
                        ('Nivel', 10000),
                        ('Modalidad', 10000),
                        ('Jornada', 10000),
                        ('Campo Amplio', 30000),
                        ('Campo Especifico', 30000),
                        ('Campo Detallado', 30000),
                        ('Cod. Unico', 10000),
                        ('Apellidos', 10000),
                        ('Nombres', 10000),
                        ('Identificación', 10000),
                        ('Correo', 10000),
                        ('Telf.', 10000),
                        ('Telf. Conv.', 10000),
                        ('Estado Calificación', 10000),
                        ('¿Tiene Formación?', 10000),
                        ('¿Tiene Experiencia?', 10000),
                        ('¿Tiene Capacitación?', 10000),
                        ('¿Tiene Publicaciones?', 10000),
                        ('¿Tiene Certificación Idiomas?', 10000),
                        ('Nota Formación', 10000),
                        ('Obs. Formación', 20000),
                        ('Nota Exp. Docente', 10000),
                        ('Obs. Exp. Docente', 20000),
                        ('Nota Exp. Administrativo', 10000),
                        ('Obs. Exp. Administrativo', 20000),
                        ('Nota Capacitación', 10000),
                        ('Obs. Capacitación', 20000),
                        ('¿Aplico Desempate?', 10000),
                        ('Nota Desempate', 10000),
                        ('Nota Final', 10000),
                        ('Obs. Final', 20000),
                        ('Estado', 10000),
                        ('¿Calificada?', 10000),
                        ('¿Apelo?', 10000),
                        ('Estado Apelación', 10000),
                        ('Obs. Apelación', 20000),
                        ('Usuario Revisión Meritos', 10000),
                        ('Fecha Revisión Meritos', 10000),
                        ('Usuario Revisión Apelación', 10000),
                        ('Fecha Revisión Apelación', 10000),
                        ('Usuario Revisión Desempate', 10000),
                        ('Fecha Revisión Desempate', 10000),
                        ('Código partida', 10000),
                        ('Horas capacitación partida', 10000),
                        ('Meses experiencia partida', 10000),
                        ('Horas capacitación postulante primeras 40', 10000),
                        ('Suma Horas capacitación', 10000),
                        ('Meses experiencia postulante', 10000),
                        ('Nomenclatura partida', 10000),
                        ('Título postulación', 10000),
                        ('Título tercer nivel postulante', 10000),
                        ('Título cuarto nivel postulante', 10000),
                        ('Pais residencia', 10000),
                        ('Provincia residencia', 10000),
                        ('Canton residencia', 10000),
                        ('Dirección residencia', 10000),
                        ('Mejor puntuado', 10000),
                    ]
                    font_style = xlwt.XFStyle()
                    font_style.font.bold = True
                    for col_num in range(len(columns)):
                        ws.write(row_num, col_num, columns[col_num][0], fuentecabecera)
                        ws.col(col_num).width = columns[col_num][1]
                    row_num += 1
                    listado = PersonaAplicarPartida.objects.filter(status=True, partida__convocatoria__vigente=True).order_by('partida__convocatoria__descripcion')
                    for det in listado:
                        ws.write(row_num, 0, det.partida.convocatoria.descripcion, style2)
                        ws.write(row_num, 1, det.partida.convocatoria.tipocontrato.nombre if det.partida.convocatoria.tipocontrato else '', style2)
                        ws.write(row_num, 2, str(det.partida), style2)
                        ws.write(row_num, 3, det.partida.carrera.__str__() if det.partida.carrera else '', style2)
                        asignaturas_ = ''
                        for asig in det.partida.partidas_asignaturas():
                            asignaturas_ += '{}, '.format(asig.__str__())
                        ws.write(row_num, 4, asignaturas_, style2)
                        ws.write(row_num, 5, det.partida.get_dedicacion_display(), style2)
                        ws.write(row_num, 6, det.partida.rmu, style2)
                        ws.write(row_num, 7, det.partida.get_nivel_display(), style2)
                        ws.write(row_num, 8, det.partida.get_modalidad_display(), style2)
                        ws.write(row_num, 9, det.partida.get_jornada_display(), style2)
                        campo_amplio = ''
                        for ca in det.partida.campoamplio.all():
                            campo_amplio += '{}, '.format(ca.__str__())
                        ws.write(row_num, 10, campo_amplio, style2)
                        campo_especifico = ''
                        for ca in det.partida.campoespecifico.all():
                            campo_especifico += '{}, '.format(ca.__str__())
                        ws.write(row_num, 11, campo_especifico, style2)
                        campo_detallado = ''
                        for ca in det.partida.campodetallado.all():
                            campo_detallado += '{}, '.format(ca.__str__())
                        ws.write(row_num, 12, campo_detallado, style2)
                        ws.write(row_num, 13, det.pk, style2)
                        ws.write(row_num, 14, "{} {}".format(det.persona.apellido1, det.persona.apellido2), style2)
                        ws.write(row_num, 15, "{}".format(det.persona.nombres), style2)
                        ws.write(row_num, 16, u"%s"%det.persona.identificacion(), style2)
                        ws.write(row_num, 17, det.persona.email, style2)
                        ws.write(row_num, 18, det.persona.telefono, style2)
                        ws.write(row_num, 19, det.persona.telefono_conv, style2)
                        ws.write(row_num, 20, det.estado_primera_fase(), style2)
                        ws.write(row_num, 21, 'SI' if det.tiene_formacionacademica() else 'NO', style2)
                        ws.write(row_num, 22, 'SI' if det.tiene_experienciapartida() else 'NO', style2)
                        ws.write(row_num, 23, 'SI' if det.tiene_capacitaciones() else 'NO', style2)
                        ws.write(row_num, 24, 'SI' if det.tiene_publicaciones() else 'NO', style2)
                        ws.write(row_num, 25, 'SI' if det.tiene_idiomas() else 'NO', style2)
                        ws.write(row_num, 26, det.pgradoacademico, style2)
                        ws.write(row_num, 27, det.obsgradoacademico, style2)
                        ws.write(row_num, 28, det.pexpdocente, style2)
                        ws.write(row_num, 29, det.obsexperienciadoc, style2)
                        ws.write(row_num, 30, det.pexpadministrativa, style2)
                        ws.write(row_num, 31, det.obsexperienciaadmin, style2)
                        ws.write(row_num, 32, det.pcapacitacion, style2)
                        ws.write(row_num, 33, det.obscapacitacion, style2)
                        ws.write(row_num, 34, 'SI' if det.aplico_desempate else 'NO', style2)
                        ws.write(row_num, 35, det.nota_desempate, style2)
                        ws.write(row_num, 36, det.nota_final_meritos, style2)
                        ws.write(row_num, 37, det.obsgeneral, style2)
                        ws.write(row_num, 38, det.estado_primera_fase(), style2)
                        ws.write(row_num, 39, 'SI' if det.calificada else 'NO', style2)
                        ws.write(row_num, 40, 'SI' if det.solapelacion else 'NO', style2)
                        ws.write(row_num, 41, det.traer_apelacion().get_estado_display() if det.traer_apelacion() else '', style2)
                        obs_revisor, revisado_por, fecha_revision = '', '', ''
                        if det.traer_apelacion():
                            if det.traer_apelacion().estado != 0:
                                obs_revisor = det.traer_apelacion().observacion_revisor
                                revisado_por = det.traer_apelacion().revisado_por.username if det.traer_apelacion().revisado_por else ''
                                fecha_revision = str(det.traer_apelacion().fecha_revision)
                        ws.write(row_num, 42, obs_revisor, style2)
                        ws.write(row_num, 43, revisado_por, style2)
                        ws.write(row_num, 44, fecha_revision, style2)
                        nomenclatura_partida=""
                        contad=0
                        if det.partida.obtener_titulos():
                            for nomenclatura in det.partida.obtener_titulos():
                                contad+=1
                                nomenclatura_partida += u"%s: %s " % (contad,nomenclatura.combinacion.titulo)
                        nomenclatura_postulate = ""
                        contad = 0
                        if det.tiene_formacionacademica():
                            for titulo_postu in det.formacionacademica():
                                contad += 1
                                nomenclatura_postulate += u"%s: %s "  % (contad,titulo_postu.combinacion)
                        ws.write(row_num, 49, u"%s"%det.partida.codpartida, style2)
                        ws.write(row_num, 50, u"%s"%det.partida.minhourcapa, style2)
                        ws.write(row_num, 51, u"%s"%det.partida.minmesexp, style2)
                        ws.write(row_num, 52, det.primera_hora_capacitacion_cumple(), style2)
                        ws.write(row_num, 53, det.total_horas_capacitacion(), style2)
                        ws.write(row_num, 54, det.total_meses_experiencia(), style2)
                        ws.write(row_num, 55, nomenclatura_partida, style2)
                        ws.write(row_num, 56, nomenclatura_postulate, style2)
                        titulos_3_nivel=""
                        for titulacion  in det.persona.mis_titulacionesxgrupo(3):
                            titulos_3_nivel+="%s"%titulacion.titulo
                        titulos_4_nivel=""
                        for titulacion  in det.persona.mis_titulacionesxgrupo(4):
                            titulos_4_nivel+="%s"%titulacion.titulo
                        ws.write(row_num, 57, u"%s" %titulos_3_nivel, style2)
                        ws.write(row_num, 58, u"%s" %titulos_4_nivel, style2)
                        ws.write(row_num, 59, u"%s" % det.persona.pais if det.persona.pais else "", style2)
                        ws.write(row_num, 60, u"%s" %det.persona.provincia if det.persona.provincia else "", style2)
                        ws.write(row_num, 61, u"%s" %det.persona.canton if det.persona.canton else "", style2)
                        ws.write(row_num, 62, u"%s" %det.persona.direccion_corta(), style2)
                        ws.write(row_num, 63, u"%s" %det.esmejorpuntuado, style2)
                        row_num += 1
                    wb.save(response)
                    return response
                except Exception as ex:
                    messages.error(request, str(ex))

            if action == 'excel_postulantes__all_mejores_puntuados':
                try:
                    response = HttpResponse(content_type='application/ms-excel')
                    response['Content-Disposition'] = 'attachment; filename="postulantes_all_mejores_puntuados.xls"'
                    title = easyxf('font: name Calibri, color-index black, bold on , height 350; alignment: horiz centre')
                    title2 = easyxf('font: name Calibri, color-index black, bold on , height 250; alignment: horiz centre')
                    font_style = xlwt.XFStyle()
                    font_style.font.bold = True
                    fuentecabecera = easyxf('font: name Calibri, color-index black, bold on; pattern: pattern solid, fore_colour gray25; alignment: horiz centre; borders: left thin, right thin, top thin, bottom thin')
                    fuentenormal = easyxf('font: name Calibri, color-index black, height 150; borders: left thin, right thin, top thin, bottom thin')
                    style2 = easyxf('borders: left thin, right thin, top thin, bottom thin; alignment: horiz centre')
                    wb = xlwt.Workbook(encoding='utf-8')
                    ws = wb.add_sheet('postulantes')
                    ws.write_merge(0, 0, 0, 8, 'UNIVERSIDAD ESTATAL ESTATAL DE MILAGRO', title)
                    ws.write_merge(1, 1, 0, 8, 'LISTADO DE POSTULANTES MEJORES PUNTUADOS', title2)
                    row_num = 2
                    columns = [
                        ('Convocatoria', 10000),
                        ('Categoria', 10000),
                        ('Partida', 30000),
                        ('Carrera', 30000),
                        ('Asignaturas', 30000),
                        ('Dedicación', 10000),
                        ('RMU', 10000),
                        ('Nivel', 10000),
                        ('Modalidad', 10000),
                        ('Jornada', 10000),
                        ('Campo Amplio', 30000),
                        ('Campo Especifico', 30000),
                        ('Campo Detallado', 30000),
                        ('Cod. Unico', 10000),
                        ('Apellidos', 10000),
                        ('Nombres', 10000),
                        ('Titulo', 25000),
                        ('Archivo', 10000),
                        ('Identificación', 10000),
                        ('Correo', 10000),
                        ('Telf.', 10000),
                        ('Telf. Conv.', 10000),
                        ('Estado Calificación', 10000),
                        ('¿Tiene Formación?', 10000),
                        ('¿Tiene Experiencia?', 10000),
                        ('¿Tiene Capacitación?', 10000),
                        ('¿Tiene Publicaciones?', 10000),
                        ('¿Tiene Certificación Idiomas?', 10000),
                        ('Nota Formación', 10000),
                        ('Obs. Formación', 20000),
                        ('Nota Exp. Docente', 10000),
                        ('Obs. Exp. Docente', 20000),
                        ('Nota Exp. Administrativo', 10000),
                        ('Obs. Exp. Administrativo', 20000),
                        ('Nota Capacitación', 10000),
                        ('Obs. Capacitación', 20000),
                        ('¿Aplico Desempate?', 10000),
                        ('Nota Desempate', 10000),
                        ('Nota Final', 10000),
                        ('Obs. Final', 20000),
                        ('Estado', 10000),
                        ('¿Calificada?', 10000),
                        ('¿Apelo?', 10000),
                        ('Estado Apelación', 10000),
                        ('Obs. Apelación', 20000),
                        ('Usuario Revisión Meritos', 10000),
                        ('Fecha Revisión Meritos', 10000),
                        ('Usuario Revisión Apelación', 10000),
                        ('Fecha Revisión Apelación', 10000),
                        ('Usuario Revisión Desempate', 10000),
                        ('Fecha Revisión Desempate', 10000),
                    ]
                    font_style = xlwt.XFStyle()
                    font_style.font.bold = True
                    for col_num in range(len(columns)):
                        ws.write(row_num, col_num, columns[col_num][0], fuentecabecera)
                        ws.col(col_num).width = columns[col_num][1]
                    row_num += 1
                    for partidas in Partida.objects.filter(status=True, convocatoria__vigente=True).order_by('convocatoria__descripcion'):
                        listado = partidas.participantes_mejores_puntuados()
                        for det in listado:
                            if det.persona.mis_titulaciones().count() >0:
                                row_count = row_num+det.persona.mis_titulaciones().count()-1
                                titulos = det.persona.mis_titulaciones()
                                ws.write_merge(row_num,row_count, 0,0, det.partida.convocatoria.descripcion, style2)
                                ws.write_merge(row_num,row_count, 1,1, det.partida.convocatoria.tipocontrato.nombre if det.partida.convocatoria.tipocontrato else '', style2)
                                ws.write_merge(row_num,row_count, 2,2, str(det.partida), style2)
                                ws.write_merge(row_num,row_count, 3,3, det.partida.carrera.__str__() if det.partida.carrera else '', style2)
                                asignaturas_ = ''
                                for asig in det.partida.partidas_asignaturas():
                                    asignaturas_ += '{}, '.format(asig.__str__())
                                ws.write_merge(row_num,row_count, 4,4, asignaturas_, style2)
                                ws.write_merge(row_num,row_count, 5,5, det.partida.get_dedicacion_display(), style2)
                                ws.write_merge(row_num,row_count, 6,6, det.partida.rmu, style2)
                                ws.write_merge(row_num,row_count, 7,7, det.partida.get_nivel_display(), style2)
                                ws.write_merge(row_num,row_count, 8,8, det.partida.get_modalidad_display(), style2)
                                ws.write_merge(row_num,row_count, 9,9, det.partida.get_jornada_display(), style2)
                                campo_amplio = ''
                                for ca in det.partida.campoamplio.all():
                                    campo_amplio += '{}, '.format(ca.__str__())
                                ws.write_merge(row_num,row_count ,10,10, campo_amplio, style2)
                                campo_especifico = ''
                                for ca in det.partida.campoespecifico.all():
                                    campo_especifico += '{}, '.format(ca.__str__())
                                ws.write_merge(row_num,row_count, 11,11, campo_especifico, style2)
                                campo_detallado = ''
                                for ca in det.partida.campodetallado.all():
                                    campo_detallado += '{}, '.format(ca.__str__())
                                ws.write_merge(row_num,row_count, 12,12, campo_detallado, style2)
                                ws.write_merge(row_num,row_count, 13,13, det.pk, style2)
                                ws.write_merge(row_num,row_count, 14,14, "{} {}".format(det.persona.apellido1, det.persona.apellido2), style2)
                                ws.write_merge(row_num,row_count, 15,15, "{}".format(det.persona.nombres), style2)

                                ws.write_merge(row_num,row_count, 18,18, det.persona.cedula, style2)
                                ws.write_merge(row_num,row_count, 19,19, det.persona.email, style2)
                                ws.write_merge(row_num,row_count, 20,20, det.persona.telefono, style2)
                                ws.write_merge(row_num,row_count, 21,21, det.persona.telefono_conv, style2)
                                ws.write_merge(row_num,row_count, 22,22, det.estado_primera_fase(), style2)
                                ws.write_merge(row_num,row_count, 23,23, 'SI' if det.tiene_formacionacademica() else 'NO', style2)
                                ws.write_merge(row_num,row_count, 24,24, 'SI' if det.tiene_experienciapartida() else 'NO', style2)
                                ws.write_merge(row_num,row_count, 25,25, 'SI' if det.tiene_capacitaciones() else 'NO', style2)
                                ws.write_merge(row_num,row_count, 26,26, 'SI' if det.tiene_publicaciones() else 'NO', style2)
                                ws.write_merge(row_num,row_count, 27,27, 'SI' if det.tiene_idiomas() else 'NO', style2)
                                ws.write_merge(row_num,row_count, 28,28, det.pgradoacademico, style2)
                                ws.write_merge(row_num,row_count, 29,29, det.obsgradoacademico, style2)
                                ws.write_merge(row_num,row_count, 30,30, det.pexpdocente, style2)
                                ws.write_merge(row_num,row_count, 31,31, det.obsexperienciadoc, style2)
                                ws.write_merge(row_num,row_count, 32,32, det.pexpadministrativa, style2)
                                ws.write_merge(row_num,row_count, 33,33, det.obsexperienciaadmin, style2)
                                ws.write_merge(row_num,row_count, 34,34, det.pcapacitacion, style2)
                                ws.write_merge(row_num,row_count, 35,35, det.obscapacitacion, style2)
                                ws.write_merge(row_num,row_count, 36,36, 'SI' if det.aplico_desempate else 'NO', style2)
                                ws.write_merge(row_num,row_count, 37,37, det.nota_desempate, style2)
                                ws.write_merge(row_num,row_count, 38,38, det.nota_final_meritos, style2)
                                ws.write_merge(row_num,row_count, 39,39, det.obsgeneral, style2)
                                ws.write_merge(row_num,row_count, 40,40, det.estado_primera_fase(), style2)
                                ws.write_merge(row_num,row_count, 41,41, 'SI' if det.calificada else 'NO', style2)
                                ws.write_merge(row_num,row_count, 42,42, 'SI' if det.solapelacion else 'NO', style2)
                                ws.write_merge(row_num,row_count, 43,43, det.traer_apelacion().get_estado_display() if det.traer_apelacion() else '', style2)
                                obs_revisor, revisado_por, fecha_revision = '', '', ''
                                if det.traer_apelacion():
                                    if det.traer_apelacion().estado != 0:
                                        obs_revisor = det.traer_apelacion().observacion_revisor
                                        revisado_por = det.traer_apelacion().revisado_por.username if det.traer_apelacion().revisado_por else ''
                                        fecha_revision = str(det.traer_apelacion().fecha_revision)
                                ws.write_merge(row_num,row_count, 44,44, obs_revisor, style2)
                                ws.write_merge(row_num,row_count, 45,45, revisado_por, style2)
                                ws.write_merge(row_num,row_count, 46,46, fecha_revision, style2)
                                ws.write_merge(row_num,row_count, 47,47, det.revisado_por.username if det.revisado_por else '', style2)
                                ws.write_merge(row_num,row_count, 48,48, str(det.fecha_revision) if det.fecha_revision else '', style2)
                                ws.write_merge(row_num,row_count, 49,49, det.desempate_revisado_por.username if det.desempate_revisado_por else '', style2)
                                ws.write_merge(row_num,row_count, 50,50, str(det.desempate_fecha_revision) if det.desempate_fecha_revision else '', style2)
                                for dato in titulos:
                                    ws.write(row_num, 16, "{}".format(dato.titulo), style2)
                                    ws.write(row_num, 17, "https://sga.unemi.edu.ec/{}".format(dato.archivo.url) if dato.archivo else '', style2)
                                    row_num += 1
                            else:
                                ws.write(row_num, 0, det.partida.convocatoria.descripcion, style2)
                                ws.write(row_num, 1, det.partida.convocatoria.tipocontrato.nombre if det.partida.convocatoria.tipocontrato else '', style2)
                                ws.write(row_num, 2, str(det.partida), style2)
                                ws.write(row_num, 3, det.partida.carrera.__str__() if det.partida.carrera else '', style2)
                                asignaturas_ = ''
                                for asig in det.partida.partidas_asignaturas():
                                    asignaturas_ += '{}, '.format(asig.__str__())
                                ws.write(row_num, 4, asignaturas_, style2)
                                ws.write(row_num, 5, det.partida.get_dedicacion_display(), style2)
                                ws.write(row_num, 6, det.partida.rmu, style2)
                                ws.write(row_num, 7, det.partida.get_nivel_display(), style2)
                                ws.write(row_num, 8, det.partida.get_modalidad_display(), style2)
                                ws.write(row_num, 9, det.partida.get_jornada_display(), style2)
                                campo_amplio = ''
                                for ca in det.partida.campoamplio.all():
                                    campo_amplio += '{}, '.format(ca.__str__())
                                ws.write(row_num, 10, campo_amplio, style2)
                                campo_especifico = ''
                                for ca in det.partida.campoespecifico.all():
                                    campo_especifico += '{}, '.format(ca.__str__())
                                ws.write(row_num, 11, campo_especifico, style2)
                                campo_detallado = ''
                                for ca in det.partida.campodetallado.all():
                                    campo_detallado += '{}, '.format(ca.__str__())
                                ws.write(row_num, 12, campo_detallado, style2)
                                ws.write(row_num, 13, det.pk, style2)
                                ws.write(row_num, 14, "{} {}".format(det.persona.apellido1, det.persona.apellido2), style2)
                                ws.write(row_num, 15, "{}".format(det.persona.nombres), style2)
                                ws.write(row_num, 16, "", style2)
                                ws.write(row_num, 17, "", style2)
                                ws.write(row_num, 18, det.persona.cedula, style2)
                                ws.write(row_num, 19, det.persona.email, style2)
                                ws.write(row_num, 20, det.persona.telefono, style2)
                                ws.write(row_num, 21, det.persona.telefono_conv, style2)
                                ws.write(row_num, 22, det.estado_primera_fase(), style2)
                                ws.write(row_num, 23, 'SI' if det.tiene_formacionacademica() else 'NO', style2)
                                ws.write(row_num, 24, 'SI' if det.tiene_experienciapartida() else 'NO', style2)
                                ws.write(row_num, 25, 'SI' if det.tiene_capacitaciones() else 'NO', style2)
                                ws.write(row_num, 26, 'SI' if det.tiene_publicaciones() else 'NO', style2)
                                ws.write(row_num, 27, 'SI' if det.tiene_idiomas() else 'NO', style2)
                                ws.write(row_num, 28, det.pgradoacademico, style2)
                                ws.write(row_num, 29, det.obsgradoacademico, style2)
                                ws.write(row_num, 30, det.pexpdocente, style2)
                                ws.write(row_num, 31, det.obsexperienciadoc, style2)
                                ws.write(row_num, 32, det.pexpadministrativa, style2)
                                ws.write(row_num, 33, det.obsexperienciaadmin, style2)
                                ws.write(row_num, 34, det.pcapacitacion, style2)
                                ws.write(row_num, 35, det.obscapacitacion, style2)
                                ws.write(row_num, 36, 'SI' if det.aplico_desempate else 'NO', style2)
                                ws.write(row_num, 37, det.nota_desempate, style2)
                                ws.write(row_num, 38, det.nota_final_meritos, style2)
                                ws.write(row_num, 39, det.obsgeneral, style2)
                                ws.write(row_num, 40, det.estado_primera_fase(), style2)
                                ws.write(row_num, 41, 'SI' if det.calificada else 'NO', style2)
                                ws.write(row_num, 42, 'SI' if det.solapelacion else 'NO', style2)
                                ws.write(row_num, 43, det.traer_apelacion().get_estado_display() if det.traer_apelacion() else '', style2)
                                obs_revisor, revisado_por, fecha_revision = '', '', ''
                                if det.traer_apelacion():
                                    if det.traer_apelacion().estado != 0:
                                        obs_revisor = det.traer_apelacion().observacion_revisor
                                        revisado_por = det.traer_apelacion().revisado_por.username if det.traer_apelacion().revisado_por else ''
                                        fecha_revision = str(det.traer_apelacion().fecha_revision)
                                ws.write(row_num, 44, obs_revisor, style2)
                                ws.write(row_num, 45, revisado_por, style2)
                                ws.write(row_num, 46, fecha_revision, style2)
                                ws.write(row_num, 47, det.revisado_por.username if det.revisado_por else '', style2)
                                ws.write(row_num, 48, str(det.fecha_revision) if det.fecha_revision else '', style2)
                                ws.write(row_num, 49, det.desempate_revisado_por.username if det.desempate_revisado_por else '', style2)
                                ws.write(row_num, 50, str(det.desempate_fecha_revision) if det.desempate_fecha_revision else '', style2)
                                row_num += 1
                    wb.save(response)
                    return response
                except Exception as ex:
                    messages.error(request, str(ex))

            if action == 'excel_postulantes__all_banco_habilitados':
                try:
                    response = HttpResponse(content_type='application/ms-excel')
                    response['Content-Disposition'] = 'attachment; filename="postulantes_banco_habilitantes.xls"'
                    title = easyxf('font: name Calibri, color-index black, bold on , height 350; alignment: horiz centre')
                    title2 = easyxf('font: name Calibri, color-index black, bold on , height 250; alignment: horiz centre')
                    font_style = xlwt.XFStyle()
                    font_style.font.bold = True
                    fuentecabecera = easyxf('font: name Calibri, color-index black, bold on; pattern: pattern solid, fore_colour gray25; alignment: horiz centre; borders: left thin, right thin, top thin, bottom thin')
                    fuentenormal = easyxf('font: name Calibri, color-index black, height 150; borders: left thin, right thin, top thin, bottom thin')
                    style2 = easyxf('borders: left thin, right thin, top thin, bottom thin; alignment: horiz centre')
                    wb = xlwt.Workbook(encoding='utf-8')
                    ws = wb.add_sheet('postulantes')
                    ws.write_merge(0, 0, 0, 8, 'UNIVERSIDAD ESTATAL ESTATAL DE MILAGRO', title)
                    ws.write_merge(1, 1, 0, 8, 'LISTADO DE POSTULANTES BANCO HABILITANTES', title2)
                    row_num = 2
                    columns = [
                        ('Convocatoria', 10000),
                        ('Categoria', 10000),
                        ('Partida', 30000),
                        ('Carrera', 30000),
                        ('Asignaturas', 30000),
                        ('Dedicación', 10000),
                        ('RMU', 10000),
                        ('Nivel', 10000),
                        ('Modalidad', 10000),
                        ('Jornada', 10000),
                        ('Campo Amplio', 30000),
                        ('Campo Especifico', 30000),
                        ('Campo Detallado', 30000),
                        ('Cod. Unico', 10000),
                        ('Apellidos', 10000),
                        ('Nombres', 10000),
                        ('Titulo', 25000),
                        ('Archivo', 10000),
                        ('Identificación', 10000),
                        ('Correo', 10000),
                        ('Telf.', 10000),
                        ('Telf. Conv.', 10000),
                        ('Estado Calificación', 10000),
                        ('¿Tiene Formación?', 10000),
                        ('¿Tiene Experiencia?', 10000),
                        ('¿Tiene Capacitación?', 10000),
                        ('¿Tiene Publicaciones?', 10000),
                        ('¿Tiene Certificación Idiomas?', 10000),
                        ('Nota Formación', 10000),
                        ('Obs. Formación', 20000),
                        ('Nota Exp. Docente', 10000),
                        ('Obs. Exp. Docente', 20000),
                        ('Nota Exp. Administrativo', 10000),
                        ('Obs. Exp. Administrativo', 20000),
                        ('Nota Capacitación', 10000),
                        ('Obs. Capacitación', 20000),
                        ('¿Aplico Desempate?', 10000),
                        ('Nota Desempate', 10000),
                        ('Nota Final', 10000),
                        ('Obs. Final', 20000),
                        ('Estado', 10000),
                        ('¿Calificada?', 10000),
                        ('¿Apelo?', 10000),
                        ('Estado Apelación', 10000),
                        ('Obs. Apelación', 20000),
                        ('Usuario Revisión Meritos', 10000),
                        ('Fecha Revisión Meritos', 10000),
                        ('Usuario Revisión Apelación', 10000),
                        ('Fecha Revisión Apelación', 10000),
                        ('Usuario Revisión Desempate', 10000),
                        ('Fecha Revisión Desempate', 10000),
                    ]
                    font_style = xlwt.XFStyle()
                    font_style.font.bold = True
                    for col_num in range(len(columns)):
                        ws.write(row_num, col_num, columns[col_num][0], fuentecabecera)
                        ws.col(col_num).width = columns[col_num][1]
                    row_num += 1
                    for partidas in Partida.objects.filter(status=True, convocatoria__vigente=True).order_by('convocatoria__descripcion'):
                        listado = partidas.participantes_banco_aspirantes()
                        for det in listado:
                            if det.persona.mis_titulaciones().count() > 0:
                                row_count = row_num + det.persona.mis_titulaciones().count() - 1
                                titulos = det.persona.mis_titulaciones()
                                ws.write_merge(row_num, row_count, 0, 0, det.partida.convocatoria.descripcion, style2)
                                ws.write_merge(row_num, row_count, 1, 1, det.partida.convocatoria.tipocontrato.nombre if det.partida.convocatoria.tipocontrato else '', style2)
                                ws.write_merge(row_num, row_count, 2, 2, str(det.partida), style2)
                                ws.write_merge(row_num, row_count, 3, 3, det.partida.carrera.__str__() if det.partida.carrera else '', style2)
                                asignaturas_ = ''
                                for asig in det.partida.partidas_asignaturas():
                                    asignaturas_ += '{}, '.format(asig.__str__())
                                ws.write_merge(row_num, row_count, 4, 4, asignaturas_, style2)
                                ws.write_merge(row_num, row_count, 5, 5, det.partida.get_dedicacion_display(), style2)
                                ws.write_merge(row_num, row_count, 6, 6, det.partida.rmu, style2)
                                ws.write_merge(row_num, row_count, 7, 7, det.partida.get_nivel_display(), style2)
                                ws.write_merge(row_num, row_count, 8, 8, det.partida.get_modalidad_display(), style2)
                                ws.write_merge(row_num, row_count, 9, 9, det.partida.get_jornada_display(), style2)
                                campo_amplio = ''
                                for ca in det.partida.campoamplio.all():
                                    campo_amplio += '{}, '.format(ca.__str__())
                                ws.write_merge(row_num, row_count, 10, 10, campo_amplio, style2)
                                campo_especifico = ''
                                for ca in det.partida.campoespecifico.all():
                                    campo_especifico += '{}, '.format(ca.__str__())
                                ws.write_merge(row_num, row_count, 11, 11, campo_especifico, style2)
                                campo_detallado = ''
                                for ca in det.partida.campodetallado.all():
                                    campo_detallado += '{}, '.format(ca.__str__())
                                ws.write_merge(row_num, row_count, 12, 12, campo_detallado, style2)
                                ws.write_merge(row_num, row_count, 13, 13, det.pk, style2)
                                ws.write_merge(row_num, row_count, 14, 14, "{} {}".format(det.persona.apellido1, det.persona.apellido2), style2)
                                ws.write_merge(row_num, row_count, 15, 15, "{}".format(det.persona.nombres), style2)

                                ws.write_merge(row_num, row_count, 18, 18, det.persona.cedula, style2)
                                ws.write_merge(row_num, row_count, 19, 19, det.persona.email, style2)
                                ws.write_merge(row_num, row_count, 20, 20, det.persona.telefono, style2)
                                ws.write_merge(row_num, row_count, 21, 21, det.persona.telefono_conv, style2)
                                ws.write_merge(row_num, row_count, 22, 22, det.estado_primera_fase(), style2)
                                ws.write_merge(row_num, row_count, 23, 23, 'SI' if det.tiene_formacionacademica() else 'NO', style2)
                                ws.write_merge(row_num, row_count, 24, 24, 'SI' if det.tiene_experienciapartida() else 'NO', style2)
                                ws.write_merge(row_num, row_count, 25, 25, 'SI' if det.tiene_capacitaciones() else 'NO', style2)
                                ws.write_merge(row_num, row_count, 26, 26, 'SI' if det.tiene_publicaciones() else 'NO', style2)
                                ws.write_merge(row_num, row_count, 27, 27, 'SI' if det.tiene_idiomas() else 'NO', style2)
                                ws.write_merge(row_num, row_count, 28, 28, det.pgradoacademico, style2)
                                ws.write_merge(row_num, row_count, 29, 29, det.obsgradoacademico, style2)
                                ws.write_merge(row_num, row_count, 30, 30, det.pexpdocente, style2)
                                ws.write_merge(row_num, row_count, 31, 31, det.obsexperienciadoc, style2)
                                ws.write_merge(row_num, row_count, 32, 32, det.pexpadministrativa, style2)
                                ws.write_merge(row_num, row_count, 33, 33, det.obsexperienciaadmin, style2)
                                ws.write_merge(row_num, row_count, 34, 34, det.pcapacitacion, style2)
                                ws.write_merge(row_num, row_count, 35, 35, det.obscapacitacion, style2)
                                ws.write_merge(row_num, row_count, 36, 36, 'SI' if det.aplico_desempate else 'NO', style2)
                                ws.write_merge(row_num, row_count, 37, 37, det.nota_desempate, style2)
                                ws.write_merge(row_num, row_count, 38, 38, det.nota_final_meritos, style2)
                                ws.write_merge(row_num, row_count, 39, 39, det.obsgeneral, style2)
                                ws.write_merge(row_num, row_count, 40, 40, det.estado_primera_fase(), style2)
                                ws.write_merge(row_num, row_count, 41, 41, 'SI' if det.calificada else 'NO', style2)
                                ws.write_merge(row_num, row_count, 42, 42, 'SI' if det.solapelacion else 'NO', style2)
                                ws.write_merge(row_num, row_count, 43, 43, det.traer_apelacion().get_estado_display() if det.traer_apelacion() else '', style2)
                                obs_revisor, revisado_por, fecha_revision = '', '', ''
                                if det.traer_apelacion():
                                    if det.traer_apelacion().estado != 0:
                                        obs_revisor = det.traer_apelacion().observacion_revisor
                                        revisado_por = det.traer_apelacion().revisado_por.username if det.traer_apelacion().revisado_por else ''
                                        fecha_revision = str(det.traer_apelacion().fecha_revision)
                                ws.write_merge(row_num, row_count, 44, 44, obs_revisor, style2)
                                ws.write_merge(row_num, row_count, 45, 45, revisado_por, style2)
                                ws.write_merge(row_num, row_count, 46, 46, fecha_revision, style2)
                                ws.write_merge(row_num, row_count, 47, 47, det.revisado_por.username if det.revisado_por else '', style2)
                                ws.write_merge(row_num, row_count, 48, 48, str(det.fecha_revision) if det.fecha_revision else '', style2)
                                ws.write_merge(row_num, row_count, 49, 49, det.desempate_revisado_por.username if det.desempate_revisado_por else '', style2)
                                ws.write_merge(row_num, row_count, 50, 50, str(det.desempate_fecha_revision) if det.desempate_fecha_revision else '', style2)
                                for dato in titulos:
                                    ws.write(row_num, 16, "{}".format(dato.titulo), style2)
                                    ws.write(row_num, 17, "https://sga.unemi.edu.ec/{}".format(dato.archivo.url) if dato.archivo else '', style2)
                                    row_num += 1
                            else:
                                ws.write(row_num, 0, det.partida.convocatoria.descripcion, style2)
                                ws.write(row_num, 1, det.partida.convocatoria.tipocontrato.nombre if det.partida.convocatoria.tipocontrato else '', style2)
                                ws.write(row_num, 2, str(det.partida), style2)
                                ws.write(row_num, 3, det.partida.carrera.__str__() if det.partida.carrera else '', style2)
                                asignaturas_ = ''
                                for asig in det.partida.partidas_asignaturas():
                                    asignaturas_ += '{}, '.format(asig.__str__())
                                ws.write(row_num, 4, asignaturas_, style2)
                                ws.write(row_num, 5, det.partida.get_dedicacion_display(), style2)
                                ws.write(row_num, 6, det.partida.rmu, style2)
                                ws.write(row_num, 7, det.partida.get_nivel_display(), style2)
                                ws.write(row_num, 8, det.partida.get_modalidad_display(), style2)
                                ws.write(row_num, 9, det.partida.get_jornada_display(), style2)
                                campo_amplio = ''
                                for ca in det.partida.campoamplio.all():
                                    campo_amplio += '{}, '.format(ca.__str__())
                                ws.write(row_num, 10, campo_amplio, style2)
                                campo_especifico = ''
                                for ca in det.partida.campoespecifico.all():
                                    campo_especifico += '{}, '.format(ca.__str__())
                                ws.write(row_num, 11, campo_especifico, style2)
                                campo_detallado = ''
                                for ca in det.partida.campodetallado.all():
                                    campo_detallado += '{}, '.format(ca.__str__())
                                ws.write(row_num, 12, campo_detallado, style2)
                                ws.write(row_num, 13, det.pk, style2)
                                ws.write(row_num, 14, "{} {}".format(det.persona.apellido1, det.persona.apellido2), style2)
                                ws.write(row_num, 15, "{}".format(det.persona.nombres), style2)
                                ws.write(row_num, 16, "", style2)
                                ws.write(row_num, 17, "", style2)
                                ws.write(row_num, 18, det.persona.cedula, style2)
                                ws.write(row_num, 19, det.persona.email, style2)
                                ws.write(row_num, 20, det.persona.telefono, style2)
                                ws.write(row_num, 21, det.persona.telefono_conv, style2)
                                ws.write(row_num, 22, det.estado_primera_fase(), style2)
                                ws.write(row_num, 23, 'SI' if det.tiene_formacionacademica() else 'NO', style2)
                                ws.write(row_num, 24, 'SI' if det.tiene_experienciapartida() else 'NO', style2)
                                ws.write(row_num, 25, 'SI' if det.tiene_capacitaciones() else 'NO', style2)
                                ws.write(row_num, 26, 'SI' if det.tiene_publicaciones() else 'NO', style2)
                                ws.write(row_num, 27, 'SI' if det.tiene_idiomas() else 'NO', style2)
                                ws.write(row_num, 28, det.pgradoacademico, style2)
                                ws.write(row_num, 29, det.obsgradoacademico, style2)
                                ws.write(row_num, 30, det.pexpdocente, style2)
                                ws.write(row_num, 31, det.obsexperienciadoc, style2)
                                ws.write(row_num, 32, det.pexpadministrativa, style2)
                                ws.write(row_num, 33, det.obsexperienciaadmin, style2)
                                ws.write(row_num, 34, det.pcapacitacion, style2)
                                ws.write(row_num, 35, det.obscapacitacion, style2)
                                ws.write(row_num, 36, 'SI' if det.aplico_desempate else 'NO', style2)
                                ws.write(row_num, 37, det.nota_desempate, style2)
                                ws.write(row_num, 38, det.nota_final_meritos, style2)
                                ws.write(row_num, 39, det.obsgeneral, style2)
                                ws.write(row_num, 40, det.estado_primera_fase(), style2)
                                ws.write(row_num, 41, 'SI' if det.calificada else 'NO', style2)
                                ws.write(row_num, 42, 'SI' if det.solapelacion else 'NO', style2)
                                ws.write(row_num, 43, det.traer_apelacion().get_estado_display() if det.traer_apelacion() else '', style2)
                                obs_revisor, revisado_por, fecha_revision = '', '', ''
                                if det.traer_apelacion():
                                    if det.traer_apelacion().estado != 0:
                                        obs_revisor = det.traer_apelacion().observacion_revisor
                                        revisado_por = det.traer_apelacion().revisado_por.username if det.traer_apelacion().revisado_por else ''
                                        fecha_revision = str(det.traer_apelacion().fecha_revision)
                                ws.write(row_num, 44, obs_revisor, style2)
                                ws.write(row_num, 45, revisado_por, style2)
                                ws.write(row_num, 46, fecha_revision, style2)
                                ws.write(row_num, 47, det.revisado_por.username if det.revisado_por else '', style2)
                                ws.write(row_num, 48, str(det.fecha_revision) if det.fecha_revision else '', style2)
                                ws.write(row_num, 49, det.desempate_revisado_por.username if det.desempate_revisado_por else '', style2)
                                ws.write(row_num, 50, str(det.desempate_fecha_revision) if det.desempate_fecha_revision else '', style2)
                                row_num += 1
                    wb.save(response)
                    return response
                except Exception as ex:
                    msg_ex = 'Error on line {} - {}'.format(sys.exc_info()[-1].tb_lineno, str(ex))
                    return JsonResponse({"result": False, 'data': str(msg_ex)})

            if action == 'excel_postulantes__aptos':
                try:
                    response = HttpResponse(content_type='application/ms-excel')
                    response['Content-Disposition'] = 'attachment; filename="postulantes_all.xls"'
                    title = easyxf('font: name Calibri, color-index black, bold on , height 350; alignment: horiz centre')
                    title2 = easyxf('font: name Calibri, color-index black, bold on , height 250; alignment: horiz centre')
                    font_style = xlwt.XFStyle()
                    font_style.font.bold = True
                    fuentecabecera = easyxf('font: name Calibri, color-index black, bold on; pattern: pattern solid, fore_colour gray25; alignment: horiz centre; borders: left thin, right thin, top thin, bottom thin')
                    fuentenormal = easyxf('font: name Calibri, color-index black, height 150; borders: left thin, right thin, top thin, bottom thin')
                    style2 = easyxf('borders: left thin, right thin, top thin, bottom thin; alignment: horiz centre')
                    wb = xlwt.Workbook(encoding='utf-8')
                    ws = wb.add_sheet('postulantes')
                    ws.write_merge(0, 0, 0, 8, 'UNIVERSIDAD ESTATAL ESTATAL DE MILAGRO', title)
                    ws.write_merge(1, 1, 0, 8, 'LISTADO DE POSTULANTES', title2)
                    row_num = 2
                    columns = [
                        ('Convocatoria', 10000),
                        ('Codigo Partida', 10000),
                        ('Categoria', 10000),
                        ('Partida', 30000),
                        ('Carrera', 30000),
                        ('Asignaturas', 30000),
                        ('Dedicación', 10000),
                        ('RMU', 10000),
                        ('Nivel', 10000),
                        ('Modalidad', 10000),
                        ('Jornada', 10000),
                        ('Campo Amplio', 30000),
                        ('Campo Especifico', 30000),
                        ('Campo Detallado', 30000),
                        ('Cod. Unico', 10000),
                        ('Postulante', 10000),
                        # ('Nombres', 10000),
                        ('Identificación', 10000),
                        ('Correo', 10000),
                        ('Telf.', 10000),
                        ('Telf. Conv.', 10000),
                        ('Estado Calificación', 10000),
                        ('¿Tiene Formación?', 10000),
                        ('¿Tiene Experiencia?', 10000),
                        ('¿Tiene Capacitación?', 10000),
                        ('¿Tiene Publicaciones?', 10000),
                        ('¿Tiene Certificación Idiomas?', 10000),
                        ('Titulos Postulante', 10000),
                        ('Titulos Partida', 10000),
                        ('Fecha Nacimiento', 10000),
                    ]
                    font_style = xlwt.XFStyle()
                    font_style.font.bold = True
                    for col_num in range(len(columns)):
                        ws.write(row_num, col_num, columns[col_num][0], fuentecabecera)
                        ws.col(col_num).width = columns[col_num][1]
                    row_num += 1
                    listado = PersonaAplicarPartida.objects.filter(status=True , partida__convocatoria__vigente=True).order_by('partida__convocatoria__descripcion')
                    for det in listado:
                        titulos_partida = det.partida.titulos.all().values_list('id', flat=True)
                        titulos_partida_nombres = det.partida.titulos.all().values_list('nombre', flat=True)
                        if PersonaFormacionAcademicoPartida.objects.filter(status=True, personapartida=det, titulo__in=list(titulos_partida)):
                            ws.write(row_num, 0, det.partida.convocatoria.descripcion, style2)
                            ws.write(row_num, 1, det.partida.codpartida, style2)
                            ws.write(row_num, 2, det.partida.convocatoria.tipocontrato.nombre if det.partida.convocatoria.tipocontrato else '', style2)
                            ws.write(row_num, 3, str(det.partida), style2)
                            ws.write(row_num, 4, det.partida.carrera.__str__() if det.partida.carrera else '', style2)
                            asignaturas_ = ''
                            for asig in det.partida.partidas_asignaturas():
                                asignaturas_ += '{}, '.format(asig.__str__())
                            ws.write(row_num, 5, asignaturas_, style2)
                            ws.write(row_num, 6, det.partida.get_dedicacion_display(), style2)
                            ws.write(row_num, 7, det.partida.rmu, style2)
                            ws.write(row_num, 8, det.partida.get_nivel_display(), style2)
                            ws.write(row_num, 9, det.partida.get_modalidad_display(), style2)
                            ws.write(row_num, 10, det.partida.get_jornada_display(), style2)
                            campo_amplio = ''
                            for ca in det.partida.campoamplio.all():
                                campo_amplio += '{}, '.format(ca.__str__())
                            ws.write(row_num, 11, campo_amplio, style2)
                            campo_especifico = ''
                            for ca in det.partida.campoespecifico.all():
                                campo_especifico += '{}, '.format(ca.__str__())
                            ws.write(row_num, 12, campo_especifico, style2)
                            campo_detallado = ''
                            for ca in det.partida.campodetallado.all():
                                campo_detallado += '{}, '.format(ca.__str__())
                            ws.write(row_num, 13, campo_detallado, style2)
                            ws.write(row_num, 14, det.pk, style2)
                            ws.write(row_num, 15, "{} {} {}".format(det.persona.apellido1, det.persona.apellido2, det.persona.nombres), style2)
                            ws.write(row_num, 16, det.persona.identificacion(), style2)
                            ws.write(row_num, 17, det.persona.email, style2)
                            ws.write(row_num, 18, det.persona.telefono, style2)
                            ws.write(row_num, 19, det.persona.telefono_conv, style2)
                            ws.write(row_num, 20, det.estado_primera_fase(), style2)
                            ws.write(row_num, 21, 'SI' if det.tiene_formacionacademica() else 'NO', style2)
                            ws.write(row_num, 22, 'SI' if det.tiene_experienciapartida() else 'NO', style2)
                            ws.write(row_num, 23, 'SI' if det.tiene_capacitaciones() else 'NO', style2)
                            ws.write(row_num, 24, 'SI' if det.tiene_publicaciones() else 'NO', style2)
                            ws.write(row_num, 25, 'SI' if det.tiene_idiomas() else 'NO', style2)
                            titulospersona = PersonaFormacionAcademicoPartida.objects.filter(status=True, personapartida=det).values_list('titulo__nombre',flat=True)
                            tit_persona = ''
                            for ca in titulospersona:
                                tit_persona += '{}, '.format(ca)
                            tit_partida = ''
                            for ca in titulos_partida_nombres:
                                tit_partida += '{}, '.format(ca)
                            ws.write(row_num, 26, tit_persona, style2)
                            ws.write(row_num, 27, tit_partida, style2)
                            ws.write(row_num, 28, str(det.persona.nacimiento), style2)
                            row_num += 1
                    wb.save(response)
                    return response
                except Exception as ex:
                    messages.error(request, str(ex))

            if action == 'excel_postulantes__no__aptos':
                try:
                    response = HttpResponse(content_type='application/ms-excel')
                    response['Content-Disposition'] = 'attachment; filename="postulantes_all.xls"'
                    title = easyxf('font: name Calibri, color-index black, bold on , height 350; alignment: horiz centre')
                    title2 = easyxf('font: name Calibri, color-index black, bold on , height 250; alignment: horiz centre')
                    font_style = xlwt.XFStyle()
                    font_style.font.bold = True
                    fuentecabecera = easyxf('font: name Calibri, color-index black, bold on; pattern: pattern solid, fore_colour gray25; alignment: horiz centre; borders: left thin, right thin, top thin, bottom thin')
                    fuentenormal = easyxf('font: name Calibri, color-index black, height 150; borders: left thin, right thin, top thin, bottom thin')
                    style2 = easyxf('borders: left thin, right thin, top thin, bottom thin; alignment: horiz centre')
                    wb = xlwt.Workbook(encoding='utf-8')
                    ws = wb.add_sheet('postulantes')
                    ws.write_merge(0, 0, 0, 8, 'UNIVERSIDAD ESTATAL ESTATAL DE MILAGRO', title)
                    ws.write_merge(1, 1, 0, 8, 'LISTADO DE POSTULANTES', title2)
                    row_num = 2
                    columns = [
                        ('Convocatoria', 10000),
                        ('Codigo Partida', 10000),
                        ('Categoria', 10000),
                        ('Partida', 30000),
                        ('Carrera', 30000),
                        ('Asignaturas', 30000),
                        ('Dedicación', 10000),
                        ('RMU', 10000),
                        ('Nivel', 10000),
                        ('Modalidad', 10000),
                        ('Jornada', 10000),
                        ('Campo Amplio', 30000),
                        ('Campo Especifico', 30000),
                        ('Campo Detallado', 30000),
                        ('Cod. Unico', 10000),
                        ('Postulante', 10000),
                        # ('Nombres', 10000),
                        ('Identificación', 10000),
                        ('Correo', 10000),
                        ('Telf.', 10000),
                        ('Telf. Conv.', 10000),
                        ('Estado Calificación', 10000),
                        ('¿Tiene Formación?', 10000),
                        ('¿Tiene Experiencia?', 10000),
                        ('¿Tiene Capacitación?', 10000),
                        ('¿Tiene Publicaciones?', 10000),
                        ('¿Tiene Certificación Idiomas?', 10000),
                        ('Titulos Postulante', 10000),
                        ('Titulos Partida', 10000),
                        ('Fecha Nacimiento', 10000),
                    ]
                    font_style = xlwt.XFStyle()
                    font_style.font.bold = True
                    for col_num in range(len(columns)):
                        ws.write(row_num, col_num, columns[col_num][0], fuentecabecera)
                        ws.col(col_num).width = columns[col_num][1]
                    row_num += 1
                    listado = PersonaAplicarPartida.objects.filter(status=True , partida__convocatoria__vigente=True).order_by('partida__convocatoria__descripcion')
                    for det in listado:
                        titulos_partida = det.partida.titulos.all().values_list('id', flat=True)
                        titulos_partida_nombres = det.partida.titulos.all().values_list('nombre', flat=True)
                        if not PersonaFormacionAcademicoPartida.objects.filter(status=True, personapartida=det, titulo__in=list(titulos_partida)):
                            ws.write(row_num, 0, det.partida.convocatoria.descripcion, style2)
                            ws.write(row_num, 1, det.partida.codpartida, style2)
                            ws.write(row_num, 2, det.partida.convocatoria.tipocontrato.nombre if det.partida.convocatoria.tipocontrato else '', style2)
                            ws.write(row_num, 3, str(det.partida), style2)
                            ws.write(row_num, 4, det.partida.carrera.__str__() if det.partida.carrera else '', style2)
                            asignaturas_ = ''
                            for asig in det.partida.partidas_asignaturas():
                                asignaturas_ += '{}, '.format(asig.__str__())
                            ws.write(row_num, 5, asignaturas_, style2)
                            ws.write(row_num, 6, det.partida.get_dedicacion_display(), style2)
                            ws.write(row_num, 7, det.partida.rmu, style2)
                            ws.write(row_num, 8, det.partida.get_nivel_display(), style2)
                            ws.write(row_num, 9, det.partida.get_modalidad_display(), style2)
                            ws.write(row_num, 10, det.partida.get_jornada_display(), style2)
                            campo_amplio = ''
                            for ca in det.partida.campoamplio.all():
                                campo_amplio += '{}, '.format(ca.__str__())
                            ws.write(row_num, 11, campo_amplio, style2)
                            campo_especifico = ''
                            for ca in det.partida.campoespecifico.all():
                                campo_especifico += '{}, '.format(ca.__str__())
                            ws.write(row_num, 12, campo_especifico, style2)
                            campo_detallado = ''
                            for ca in det.partida.campodetallado.all():
                                campo_detallado += '{}, '.format(ca.__str__())
                            ws.write(row_num, 13, campo_detallado, style2)
                            ws.write(row_num, 14, det.pk, style2)
                            ws.write(row_num, 15, "{} {} {}".format(det.persona.apellido1, det.persona.apellido2, det.persona.nombres), style2)
                            ws.write(row_num, 16, det.persona.identificacion(), style2)
                            ws.write(row_num, 17, det.persona.email, style2)
                            ws.write(row_num, 18, det.persona.telefono, style2)
                            ws.write(row_num, 19, det.persona.telefono_conv, style2)
                            ws.write(row_num, 20, det.estado_primera_fase(), style2)
                            ws.write(row_num, 21, 'SI' if det.tiene_formacionacademica() else 'NO', style2)
                            ws.write(row_num, 22, 'SI' if det.tiene_experienciapartida() else 'NO', style2)
                            ws.write(row_num, 23, 'SI' if det.tiene_capacitaciones() else 'NO', style2)
                            ws.write(row_num, 24, 'SI' if det.tiene_publicaciones() else 'NO', style2)
                            ws.write(row_num, 25, 'SI' if det.tiene_idiomas() else 'NO', style2)
                            titulospersona = PersonaFormacionAcademicoPartida.objects.filter(status=True, personapartida=det).values_list('titulo__nombre',flat=True)
                            tit_persona = ''
                            for ca in titulospersona:
                                tit_persona += '{}, '.format(ca)
                            tit_partida = ''
                            for ca in titulos_partida_nombres:
                                tit_partida += '{}, '.format(ca)
                            ws.write(row_num, 26, tit_persona, style2)
                            ws.write(row_num, 27, tit_partida, style2)
                            ws.write(row_num, 28, str(det.persona.nacimiento), style2)
                            row_num += 1
                    wb.save(response)
                    return response
                except Exception as ex:
                    messages.error(request, str(ex))

            if action == 'excel_postulantes__apelaciones':
                try:
                    response = HttpResponse(content_type='application/ms-excel')
                    response['Content-Disposition'] = 'attachment; filename="postulantes_all.xls"'
                    title = easyxf('font: name Calibri, color-index black, bold on , height 350; alignment: horiz centre')
                    title2 = easyxf('font: name Calibri, color-index black, bold on , height 250; alignment: horiz centre')
                    font_style = xlwt.XFStyle()
                    font_style.font.bold = True
                    fuentecabecera = easyxf('font: name Calibri, color-index black, bold on; pattern: pattern solid, fore_colour gray25; alignment: horiz centre; borders: left thin, right thin, top thin, bottom thin')
                    fuentenormal = easyxf('font: name Calibri, color-index black, height 150; borders: left thin, right thin, top thin, bottom thin')
                    style2 = easyxf('borders: left thin, right thin, top thin, bottom thin; alignment: horiz centre')
                    wb = xlwt.Workbook(encoding='utf-8')
                    ws = wb.add_sheet('postulantes')
                    ws.write_merge(0, 0, 0, 8, 'UNIVERSIDAD ESTATAL ESTATAL DE MILAGRO', title)
                    ws.write_merge(1, 1, 0, 8, 'LISTADO DE POSTULANTES', title2)
                    row_num = 2
                    columns = [
                        ('Convocatoria', 10000),
                        ('Categoria', 10000),
                        ('Partida', 30000),
                        ('Carrera', 30000),
                        ('Asignaturas', 30000),
                        ('Dedicación', 10000),
                        ('RMU', 10000),
                        ('Nivel', 10000),
                        ('Modalidad', 10000),
                        ('Jornada', 10000),
                        ('Campo Amplio', 30000),
                        ('Campo Especifico', 30000),
                        ('Campo Detallado', 30000),
                        ('Cod. Unico', 10000),
                        ('Apellidos', 10000),
                        ('Nombres', 10000),
                        ('Identificación', 10000),
                        ('Correo', 10000),
                        ('Telf.', 10000),
                        ('Telf. Conv.', 10000),
                        ('Estado Calificación', 10000),
                        ('¿Tiene Formación?', 10000),
                        ('¿Tiene Experiencia?', 10000),
                        ('¿Tiene Capacitación?', 10000),
                        ('¿Tiene Publicaciones?', 10000),
                        ('¿Tiene Certificación Idiomas?', 10000),
                        ('Nota Formación', 10000),
                        ('Obs. Formación', 20000),
                        ('Nota Exp. Docente', 10000),
                        ('Obs. Exp. Docente', 20000),
                        ('Nota Exp. Administrativo', 10000),
                        ('Obs. Exp. Administrativo', 20000),
                        ('Nota Capacitación', 10000),
                        ('Obs. Capacitación', 20000),
                        ('¿Aplico Desempate?', 10000),
                        ('Nota Desempate', 10000),
                        ('Nota Final', 10000),
                        ('Obs. Final', 20000),
                        ('Estado', 10000),
                        ('¿Calificada?', 10000),
                        ('¿Apelo?', 10000),
                        ('Estado Apelación', 10000),
                        ('Obs. Apelación', 20000),
                        ('Usuario Revisión Meritos', 10000),
                        ('Fecha Revisión Meritos', 10000),
                        ('Usuario Revisión Apelación', 10000),
                        ('Fecha Revisión Apelación', 10000),
                        ('Usuario Revisión Desempate', 10000),
                        ('Fecha Revisión Desempate', 10000),
                        ('Titulos Personas', 10000),
                        ('Titulos Requeridos', 10000),
                    ]
                    font_style = xlwt.XFStyle()
                    font_style.font.bold = True
                    for col_num in range(len(columns)):
                        ws.write(row_num, col_num, columns[col_num][0], fuentecabecera)
                        ws.col(col_num).width = columns[col_num][1]
                    row_num += 1
                    listado = PersonaAplicarPartida.objects.filter(status=True, partida__convocatoria__vigente=True, solapelacion=True).order_by('partida__convocatoria__descripcion')
                    for det in listado:
                        ws.write(row_num, 0, det.partida.convocatoria.descripcion, style2)
                        ws.write(row_num, 1, det.partida.convocatoria.tipocontrato.nombre if det.partida.convocatoria.tipocontrato else '', style2)
                        ws.write(row_num, 2, str(det.partida), style2)
                        ws.write(row_num, 3, det.partida.carrera.__str__() if det.partida.carrera else '', style2)
                        asignaturas_ = ''
                        for asig in det.partida.partidas_asignaturas():
                            asignaturas_ += '{}, '.format(asig.__str__())
                        ws.write(row_num, 4, asignaturas_, style2)
                        ws.write(row_num, 5, det.partida.get_dedicacion_display(), style2)
                        ws.write(row_num, 6, det.partida.rmu, style2)
                        ws.write(row_num, 7, det.partida.get_nivel_display(), style2)
                        ws.write(row_num, 8, det.partida.get_modalidad_display(), style2)
                        ws.write(row_num, 9, det.partida.get_jornada_display(), style2)
                        campo_amplio = ''
                        for ca in det.partida.campoamplio.all():
                            campo_amplio += '{}, '.format(ca.__str__())
                        ws.write(row_num, 10, campo_amplio, style2)
                        campo_especifico = ''
                        for ca in det.partida.campoespecifico.all():
                            campo_especifico += '{}, '.format(ca.__str__())
                        ws.write(row_num, 11, campo_especifico, style2)
                        campo_detallado = ''
                        for ca in det.partida.campodetallado.all():
                            campo_detallado += '{}, '.format(ca.__str__())
                        ws.write(row_num, 12, campo_detallado, style2)
                        ws.write(row_num, 13, det.pk, style2)
                        ws.write(row_num, 14, "{} {}".format(det.persona.apellido1, det.persona.apellido2), style2)
                        ws.write(row_num, 15, "{}".format(det.persona.nombres), style2)
                        ws.write(row_num, 16, det.persona.cedula, style2)
                        ws.write(row_num, 17, det.persona.email, style2)
                        ws.write(row_num, 18, det.persona.telefono, style2)
                        ws.write(row_num, 19, det.persona.telefono_conv, style2)
                        ws.write(row_num, 20, det.estado_primera_fase(), style2)
                        ws.write(row_num, 21, 'SI' if det.tiene_formacionacademica() else 'NO', style2)
                        ws.write(row_num, 22, 'SI' if det.tiene_experienciapartida() else 'NO', style2)
                        ws.write(row_num, 23, 'SI' if det.tiene_capacitaciones() else 'NO', style2)
                        ws.write(row_num, 24, 'SI' if det.tiene_publicaciones() else 'NO', style2)
                        ws.write(row_num, 25, 'SI' if det.tiene_idiomas() else 'NO', style2)
                        ws.write(row_num, 26, det.pgradoacademico, style2)
                        ws.write(row_num, 27, det.obsgradoacademico, style2)
                        ws.write(row_num, 28, det.pexpdocente, style2)
                        ws.write(row_num, 29, det.obsexperienciadoc, style2)
                        ws.write(row_num, 30, det.pexpadministrativa, style2)
                        ws.write(row_num, 31, det.obsexperienciaadmin, style2)
                        ws.write(row_num, 32, det.pcapacitacion, style2)
                        ws.write(row_num, 33, det.obscapacitacion, style2)
                        ws.write(row_num, 34, 'SI' if det.aplico_desempate else 'NO', style2)
                        ws.write(row_num, 35, det.nota_desempate, style2)
                        ws.write(row_num, 36, det.nota_final_meritos, style2)
                        ws.write(row_num, 37, det.obsgeneral, style2)
                        ws.write(row_num, 38, det.estado_primera_fase(), style2)
                        ws.write(row_num, 39, 'SI' if det.calificada else 'NO', style2)
                        ws.write(row_num, 40, 'SI' if det.solapelacion else 'NO', style2)
                        ws.write(row_num, 41, det.traer_apelacion().get_estado_display() if det.traer_apelacion() else '', style2)
                        obs_revisor, revisado_por, fecha_revision = '', '', ''
                        if det.traer_apelacion():
                            if det.traer_apelacion().estado != 0:
                                obs_revisor = det.traer_apelacion().observacion_revisor
                                revisado_por = det.traer_apelacion().revisado_por.username if det.traer_apelacion().revisado_por else ''
                                fecha_revision = str(det.traer_apelacion().fecha_revision)
                        ws.write(row_num, 42, obs_revisor, style2)
                        ws.write(row_num, 43, revisado_por, style2)
                        ws.write(row_num, 44, fecha_revision, style2)
                        titulos_partida = det.partida.titulos.all().values_list('id', flat=True)
                        titulos_partida_nombres = det.partida.titulos.all().values_list('nombre', flat=True)
                        titulospersona = PersonaFormacionAcademicoPartida.objects.filter(status=True, personapartida=det).values_list('titulo__nombre',flat=True)
                        tit_persona = ''
                        for ca in titulospersona:
                            tit_persona += '{}, '.format(ca)
                        tit_partida = ''
                        for ca in titulos_partida_nombres:
                            tit_partida += '{}, '.format(ca)
                        ws.write(row_num, 45, tit_persona, style2)
                        ws.write(row_num, 46, tit_partida, style2)
                        row_num += 1
                    wb.save(response)
                    return response
                except Exception as ex:
                    messages.error(request, str(ex))

            if action == 'excel_partida':
                try:
                    partida = Partida.objects.get(pk=request.GET['id'])
                    response = HttpResponse(content_type='application/ms-excel')
                    response['Content-Disposition'] = 'attachment; filename="postulantes_part_{}.xls"'.format(str(partida.denominacionpuesto).upper().replace(' ','_'))
                    title = easyxf('font: name Calibri, color-index black, bold on , height 350; alignment: horiz centre')
                    title2 = easyxf('font: name Calibri, color-index black, bold on , height 250; alignment: horiz centre')
                    font_style = xlwt.XFStyle()
                    font_style.font.bold = True
                    fuentecabecera = easyxf('font: name Calibri, color-index black, bold on; pattern: pattern solid, fore_colour gray25; alignment: horiz centre; borders: left thin, right thin, top thin, bottom thin')
                    fuentenormal = easyxf('font: name Calibri, color-index black, height 150; borders: left thin, right thin, top thin, bottom thin')
                    style2 = easyxf('borders: left thin, right thin, top thin, bottom thin; alignment: horiz centre')
                    wb = xlwt.Workbook(encoding='utf-8')
                    ws = wb.add_sheet('postulantes')
                    ws.write_merge(0, 0, 0, 8, 'UNIVERSIDAD ESTATAL ESTATAL DE MILAGRO', title)
                    ws.write_merge(1, 1, 0, 8, 'LISTADO DE POSTULANTES {}'.format(str(partida.denominacionpuesto)), title2)
                    row_num = 2
                    columns = [
                        ('Cod. Unico', 10000),
                        ('Apellidos', 10000),
                        ('Nombres', 10000),
                        ('Identificación', 10000),
                        ('Correo', 10000),
                        ('Telf.', 10000),
                        ('Telf. Conv.', 10000),
                        ('Estado', 10000),
                        ('¿Tiene Formación?', 10000),
                        ('¿Tiene Experiencia?', 10000),
                        ('¿Tiene Capacitación?', 10000),
                        ('¿Tiene Publicaciones?', 10000),
                        ('¿Tiene Certificación Idiomas?', 10000),
                        ('Nota Formación', 10000),
                        ('Obs. Formación', 20000),
                        ('Nota Exp. Docente', 10000),
                        ('Obs. Exp. Docente', 20000),
                        ('Nota Exp. Administrativo', 10000),
                        ('Obs. Exp. Administrativo', 20000),
                        ('Nota Capacitación', 10000),
                        ('Obs. Capacitación', 20000),
                        ('¿Aplico Desempate?', 10000),
                        ('Nota Desempate', 10000),
                        ('Nota Final', 10000),
                        ('Obs. Final', 20000),
                        # ('Estado', 10000),
                        ('¿Calificada?', 10000),
                        ('¿Apelo?', 10000),
                        ('Estado Apelación', 10000),
                        ('Obs. Apelación', 20000),
                        ('Usuario Revisión Meritos', 10000),
                        ('Fecha Revisión Meritos', 10000),
                        ('Usuario Revisión Apelación', 10000),
                        ('Fecha Revisión Apelación', 10000),
                        ('Usuario Revisión Desempate', 10000),
                        ('Fecha Revisión Desempate', 10000),
                    ]
                    font_style = xlwt.XFStyle()
                    font_style.font.bold = True
                    for col_num in range(len(columns)):
                        ws.write(row_num, col_num, columns[col_num][0], fuentecabecera)
                        ws.col(col_num).width = columns[col_num][1]
                    row_num += 1
                    listado = PersonaAplicarPartida.objects.filter(status=True, partida=partida).order_by('-nota_final_meritos')
                    for det in listado:
                        ws.write(row_num, 0, det.pk, style2)
                        ws.write(row_num, 1, "{} {}".format(det.persona.apellido1, det.persona.apellido2), style2)
                        ws.write(row_num, 2, "{}".format(det.persona.nombres), style2)
                        ws.write(row_num, 3, det.persona.cedula, style2)
                        ws.write(row_num, 4, det.persona.email, style2)
                        ws.write(row_num, 5, det.persona.telefono, style2)
                        ws.write(row_num, 6, det.persona.telefono_conv, style2)
                        ws.write(row_num, 7, det.estado_primera_fase(), style2)
                        ws.write(row_num, 8, 'SI' if det.tiene_formacionacademica() else 'NO', style2)
                        ws.write(row_num, 9, 'SI' if det.tiene_experienciapartida() else 'NO', style2)
                        ws.write(row_num, 10, 'SI' if det.tiene_capacitaciones() else 'NO', style2)
                        ws.write(row_num, 11, 'SI' if det.tiene_publicaciones() else 'NO', style2)
                        ws.write(row_num, 12, 'SI' if det.tiene_idiomas() else 'NO', style2)
                        ws.write(row_num, 13, det.pgradoacademico, style2)
                        ws.write(row_num, 14, det.obsgradoacademico, style2)
                        ws.write(row_num, 15, det.pexpdocente, style2)
                        ws.write(row_num, 16, det.obsexperienciadoc, style2)
                        ws.write(row_num, 17, det.pexpadministrativa, style2)
                        ws.write(row_num, 18, det.obsexperienciaadmin, style2)
                        ws.write(row_num, 19, det.pcapacitacion, style2)
                        ws.write(row_num, 20, det.obscapacitacion, style2)
                        ws.write(row_num, 21, 'SI' if det.aplico_desempate else 'NO', style2)
                        ws.write(row_num, 22, det.nota_desempate, style2)
                        ws.write(row_num, 23, det.nota_final_meritos, style2)
                        ws.write(row_num, 24, det.obsgeneral, style2)
                        # ws.write(row_num, 25, det.get_estado_display(), style2)
                        ws.write(row_num, 25, 'SI' if det.calificada else 'NO', style2)
                        ws.write(row_num, 26, 'SI' if det.solapelacion else 'NO', style2)
                        ws.write(row_num, 27, det.traer_apelacion().get_estado_display() if det.traer_apelacion() else '', style2)
                        obs_revisor, revisado_por, fecha_revision = '', '', ''
                        if det.traer_apelacion():
                            if det.traer_apelacion().estado != 0:
                                obs_revisor = det.traer_apelacion().observacion_revisor
                                revisado_por = det.traer_apelacion().revisado_por if det.traer_apelacion().revisado_por else ''
                                fecha_revision = str(det.traer_apelacion().fecha_revision)
                        ws.write(row_num, 28, obs_revisor, style2)
                        ws.write(row_num, 29, revisado_por, style2)
                        ws.write(row_num, 30, fecha_revision, style2)
                        ws.write(row_num, 31, det.revisado_por.username if det.revisado_por else '', style2)
                        ws.write(row_num, 32, str(det.fecha_revision) if det.fecha_revision else '', style2)
                        ws.write(row_num, 33, det.desempate_revisado_por if det.desempate_revisado_por else '', style2)
                        ws.write(row_num, 34, str(det.desempate_fecha_revision) if det.desempate_fecha_revision else '', style2)
                        row_num += 1
                    wb.save(response)
                    return response
                except Exception as ex:
                    messages.success(request, str(ex))

            if action == 'rechazarpostulacion':
                try:
                    data['id'] = id = int(encrypt(request.GET['id']))
                    form=RechazarPostulacionForm()
                    data['form']=form
                    data['postulante'] = postulante = PersonaAplicarPartida.objects.get(pk=id)
                    template = get_template("postulate/adm_revisionpostulacion/rechazarpostulacion.html")
                    return JsonResponse({"result": True, 'data': template.render(data)})
                except Exception as ex:
                    pass
        else:
            try:
                data['title'] = u'Revisión Postulaciones'
                qsconvocatorias = Convocatoria.objects.filter(status=True, vigente=True).order_by('descripcion')
                validarpartidas = True
                departamentogestion = Departamento.objects.filter(status=True, permisodepartamento=2)
                if departamentogestion.exists():
                    if departamentogestion.first().mis_integrantes().filter(id=persona.pk).exists():
                        validarpartidas = False
                if request.user.is_superuser:
                    validarpartidas = False
                if validarpartidas:
                    idsconvocatorias = PartidaTribunal.objects.filter(status=True, persona=persona, tipo=1).values_list('partida__convocatoria__id', flat=True)
                    qsconvocatorias = qsconvocatorias.filter(id__in=idsconvocatorias)
                data['convocatorias'] = qsconvocatorias.order_by('-id')
                return render(request, "postulate/adm_revisionpostulacion/view.html", data)
            except Exception as ex:
                pass