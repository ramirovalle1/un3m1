import json
import random
import sys

from django.contrib import messages
from django.contrib.admin.models import LogEntry
from django.contrib.contenttypes.models import ContentType
from django.contrib.auth.decorators import login_required
from django.template.loader import get_template
from django.forms import model_to_dict
from decorators import last_access, secure_module
from django.template import Context
from django.db import transaction
from django.db.models import Max, ExpressionWrapper, F, fields
from django.http import HttpResponseRedirect, JsonResponse, HttpResponse
from django.shortcuts import render
from django.db.models.query_utils import Q
from datetime import datetime, timedelta
from sga.models import CoordinadorCarrera
from postulate.models import Partida, PersonaAplicarPartida, PersonaIdiomaPartida, PersonaFormacionAcademicoPartida, \
    PersonaExperienciaPartida, \
    PersonaPublicacionesPartida, PersonaCapacitacionesPartida, CalificacionPostulacion, PersonaApelacion, NotificacionGanador
from postulate.postular import validar_campos
from sagest.models import Departamento, DistributivoPersona
from settings import EMAIL_INSTITUCIONAL_AUTOMATICO, ACTUALIZAR_FOTO_ALUMNOS
from sga.commonviews import adduserdata, obtener_reporte
from postulate.forms import ConvocatoriaForm, PartidaForm, ConvocatoriaTerminosForm, AceptarDesistirForm
from sga.funciones import logobjeto, MiPaginador, generar_nombre
from sga.funcionesxhtml2pdf import conviert_html_to_pdf
from sga.tasks import send_html_mail
from sga.templatetags.sga_extras import encrypt

from xlwt import *
import xlwt

import xlsxwriter
import io


@login_required(redirect_field_name='ret', login_url='/loginpostulate')
@secure_module
@last_access
# @transaction.atomic()
def view(request):
    global ex
    data = {}
    perfilprincipal, persona, periodo = request.session['perfilprincipal'], request.session['persona'], request.session['periodo']
    data['hoy'] = hoy = datetime.now().date()
    data['currenttime'] = datetime.now()
    data['perfil'] = persona.mi_perfil()
    data['periodo'] = periodo
    data['url_'] = request.path
    mis_cordinaciones = persona.mis_coordinaciones().values_list('id', flat=True)
    mi_departamento = persona.mi_departamento()
    data['puede_ver_todos_bancos'] = puede_ver_todos_bancos = request.user.has_perm('postulate.puede_ver_todos_bancos')
    if request.method == 'POST':
        action = request.POST['action']

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
                    logobjeto(u'Anulo Revisión de Postulación: %s' % filtro, request, "add", None, filtro)
                    res_json = {"error": False}
            except Exception as ex:
                res_json = {'error': True, "message": "Error: {}".format(ex)}
            return JsonResponse(res_json, safe=False)

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
                    logobjeto(u'Finalizó Revisión de Desempate Postulación: %s' % filtro, request, "add",None,filtro)
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
                    logobjeto(u'Finalizo Anulación de Desempate Postulación: %s' % filtro, request, "del", None, filtro)
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
                    logobjeto(u'Anulo Revisión de Apelación: %s' % filtro, request, "add", None, filtro)
                    res_json = {"error": False}
            except Exception as ex:
                res_json = {'error': True, "message": "Error: {}".format(ex)}
            return JsonResponse(res_json, safe=False)

        # if action == 'desistir':
        #     with transaction.atomic():
        #         try:
        #             form = AceptarDesistirForm(request.POST, request.FILES)
        #             valid_ext = [".pdf"]
        #             if not form.is_valid():
        #                 raise NameError(f'{[{k:v[0]} for k, v in form.errors.items()]}')
        #             newfile = None
        #             if 'archivo' in request.FILES:
        #                 newfile = request.FILES['archivo']
        #                 ext = newfile._name[newfile._name.rfind("."):]
        #                 if not ext in valid_ext:
        #                     raise NameError("Solo archivos de tipo pdf")
        #                 if newfile.size > 30943040:
        #                     raise NameError('El archivo supera los 30Mb')
        #                 newfile._name = generar_nombre("evidencia", newfile._name)
        #             id = request.POST.get('id')
        #             personaaplicapartida = PersonaAplicarPartida.objects.get(status=True, id=int(id))
        #             desiste_ = loadpersondesiste(persona=personaaplicapartida.persona)
        #             perdesiste = None
        #             if 'desiste' in desiste_:
        #                 perdesiste = desiste_['desiste']
        #             else:
        #                 raise NameError(desiste_['mensaje'])
        #             if perdesiste:
        #                 desiste = perdesiste
        #                 desiste.fecha = form.cleaned_data['fecha']
        #                 desiste.observacion = form.cleaned_data['observacion']
        #                 if newfile: desiste.archivo = newfile
        #             else:
        #                 desiste = NotificacionGanador(
        #                     # persona = personaaplicapartida.persona,
        #                     personaaplicapartida = personaaplicapartida,
        #                     fecha = form.cleaned_data['fecha'],
        #                     observacion = form.cleaned_data['observacion'],
        #                     archivo=newfile
        #                 )
        #             desiste.save(request)
        #             logobjeto(f'Agrego registro de persona deiste: {desiste.__str__()}',request,'add',None,desiste)
        #             return HttpResponseRedirect(f'{request.path}')
        #         except Exception as ex:
        #             transaction.set_rollback(True)
        #             err_ = f"{ex.__str__()}({sys.exc_info()[-1].tb_lineno})"
        #             return JsonResponse({'result':True, 'mensaje':err_})


        return JsonResponse({"result": "bad", "mensaje": u"Solicitud Incorrecta."})
    else:
        adduserdata(request, data)
        if 'action' in request.GET:
            data['action'] = action = request.GET['action']

            if action == 'desempate':
                try:
                    data['id'] = id = int(encrypt(request.GET['id']))
                    data['postulante'] = postulante = PersonaAplicarPartida.objects.get(pk=id)
                    if not postulante.calificada:
                        return JsonResponse(
                            {"result": False, 'mensaje': 'Partida no esta calificada, no aplica a desempate'})
                    data['partida'] = partida = Partida.objects.get(pk=postulante.partida.pk)
                    data['resp_campos'] = validar_campos(request, persona, partida)
                    data['persona'] = postulante.persona
                    data['posidiomas'] = posidiomas = PersonaIdiomaPartida.objects.filter(status=True, personapartida=postulante).order_by('id')
                    data['posidiomascheck'] = True if not posidiomas.filter(aceptado=False).exists() else False
                    data['postitulacion'] = postitulacion = PersonaFormacionAcademicoPartida.objects.filter(status=True, personapartida=postulante).order_by('id')
                    data['postitulacioncheck'] = True if not postitulacion.filter(aceptado=False).exists() else False
                    data['posexperiencia'] = posexperiencia = PersonaExperienciaPartida.objects.filter(status=True, personapartida=postulante).order_by(
                        'id')
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

            if action == 'vercalificaciones':
                try:
                    data['id'] = id = int(encrypt(request.GET['id']))
                    data['postulante'] = postulante = PersonaAplicarPartida.objects.get(pk=id)
                    data['listado'] = listado = postulante.calificacionpostulacion_set.filter(status=True).order_by('-pk')
                    template = get_template("postulate/adm_revisionpostulacion/calificacionespostulante.html")
                    return JsonResponse({"result": True, 'data': template.render(data)})
                except Exception as ex:
                    return JsonResponse({"result": False, 'mensaje': str(ex)})

            if action == 'verdetallepostulante':
                try:
                    data['id'] = id = int(encrypt(request.GET['id']))
                    data['postulante'] = postulante = PersonaAplicarPartida.objects.get(pk=id)
                    data['partida'] = partida = Partida.objects.get(pk=postulante.partida.pk)
                    data['resp_campos'] = validar_campos(request, persona, partida)
                    data['reporte_1'] = obtener_reporte('hoja_vida_sagest')
                    data['persona'] = postulante.persona
                    data['posidiomas'] = PersonaIdiomaPartida.objects.filter(status=True,
                                                                             personapartida=postulante).order_by('id')
                    data['postitulacion'] = PersonaFormacionAcademicoPartida.objects.filter(status=True,
                                                                                            personapartida=postulante).order_by(
                        'id')
                    data['posexperiencia'] = PersonaExperienciaPartida.objects.filter(status=True,
                                                                                      personapartida=postulante).order_by(
                        'id')
                    data['poscapacitacion'] = PersonaCapacitacionesPartida.objects.filter(status=True,
                                                                                          personapartida=postulante).order_by(
                        'id')
                    data['pospublicacion'] = PersonaPublicacionesPartida.objects.filter(status=True,
                                                                                        personapartida=postulante).order_by(
                        'id')
                    template = get_template("postulate/adm_revisionpostulacion/verdetallepostulante.html")
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

            if action == 'auditoria':
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

            if action == 'excel_postulantes__all_banco_habilitados':
                try:
                    anioact = datetime.now().year
                    aniolimite = anioact - 2
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
                    listadodistributivo = DistributivoPersona.objects.values_list('persona_id', flat=True).filter(estadopuesto__id=1, status=True)
                    filtro = Q(status=True, convocatoria__ffin__year__range=[aniolimite, anioact] )

                    if not puede_ver_todos_bancos:
                        filtro &= (Q(carrera__coordinacion__id__in=mis_cordinaciones) |
                                   Q(convocatoria__departamento=mi_departamento))
                    partidas = Partida.objects.values_list('id', flat=True).filter(filtro).order_by('convocatoria__descripcion')

                    listado = PersonaAplicarPartida.objects.filter(status=True, estado= 1, partida_id__in=partidas,nota_final_meritos__gte=70).exclude(persona_id__in=listadodistributivo).order_by('-nota_final_meritos')[3:]

                    for det in listado:
                        if det.persona.mis_titulaciones().count() > 0:
                            row_count = row_num + det.persona.mis_titulaciones().count() - 1
                            titulos = det.persona.mis_titulaciones()
                            ws.write_merge(row_num, row_count, 0, 0, det.partida.convocatoria.descripcion, style2)
                            ws.write_merge(row_num, row_count, 1, 1, det.partida.convocatoria.tipocontrato.nombre if det.partida.convocatoria.tipocontrato else '', style2)
                            ws.write_merge(row_num, row_count, 2, 2, det.partida.titulo, style2)
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
                            ws.write_merge(row_num, row_count, 22, 22, det.get_estado_display(), style2)
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
                            ws.write_merge(row_num, row_count, 40, 40, det.get_estado_display(), style2)
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
                            ws.write(row_num, 2, det.partida.titulo, style2)
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
                            ws.write(row_num, 22, det.get_estado_display(), style2)
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
                            ws.write(row_num, 40, det.get_estado_display(), style2)
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

            # if action == 'desistir':
            #     try:
            #         hoy = datetime.now().date()
            #         dos_anos_atras = hoy - timedelta(days=365 * 2)
            #         id = request.GET.get('id')
            #         data['filtro'] = perapli = PersonaAplicarPartida.objects.get(status=True, id=int(encrypt(id)))
            #         desiste = loadpersondesiste(persona=perapli.persona)
            #         perdesiste = None
            #         if 'desiste' in desiste:
            #             perdesiste = desiste['desiste']
            #         else:
            #             raise NameError(desiste['mensaje'])
            #         form = AceptarDesistirForm()
            #         if perdesiste:
            #             form.initial = model_to_dict(perdesiste)
            #         data['form'] = form
            #         template = get_template('postulate/adm_postulate/modal/formmodelo.html')
            #         res_js = {"result": True,"data":template.render(data)}
            #     except Exception as ex:
            #         err_ = f"{ex.__str__()}({sys.exc_info()[-1].tb_lineno})"
            #         res_js = {"result": False,"mensaje":err_}
            #     return JsonResponse(res_js)

        else:
            try:
                data['title'] = u'Banco Habilitado'
                anioact = datetime.now().year
                aniolimite = anioact - 2
                listadodistributivo = DistributivoPersona.objects.values_list('persona_id',flat=True).filter(estadopuesto__id=1, status=True).distinct()

                filtro = Q(status=True, nota_final_meritos__gte=70, esganador=False,
                           partida__convocatoria__ffin__year__range=[aniolimite, anioact]
                           )

                if not puede_ver_todos_bancos:
                    filtro &= (Q(partida__carrera__coordinacion__id__in=mis_cordinaciones) |
                               Q(partida__convocatoria__departamento=mi_departamento))

                eListaPersonaAplicarPartida= PersonaAplicarPartida.objects.filter(filtro).exclude(persona_id__in=listadodistributivo)

                search, url_vars = request.GET.get('s', ''), ''

                if search:
                    data['s'] = search = request.GET['s'].strip()
                    ss = search.split(' ')
                    url_vars += "&s={}".format(search)
                    if len(ss) == 1:
                        eListaPersonaAplicarPartida = eListaPersonaAplicarPartida.filter(Q(persona__nombres__icontains=search) |
                                         Q(persona__apellido1__icontains=search) | Q(persona__apellido2__icontains=search) |
                                         Q(persona__cedula=search)| Q(partida__codpartida__icontains=search)| Q(partida__convocatoria__descripcion__icontains=search))
                    else:
                        eListaPersonaAplicarPartida = eListaPersonaAplicarPartida.filter(
                            (Q(persona__apellido1__icontains=ss[0]) & Q(persona__apellido2__icontains=ss[1]))
                             | Q(partida__codpartida__icontains=ss[0])
                             | Q(partida__codpartida__icontains=ss[1])
                             | Q(partida__convocatoria__descripcion__icontains=ss[0])
                             | Q(partida__convocatoria__descripcion__icontains=ss[1]))
                paging = MiPaginador(eListaPersonaAplicarPartida, 20)
                p = 1
                try:
                    paginasesion = 1
                    if 'paginador' in request.session:
                        paginasesion = int(request.session['paginador'])
                    if 'page' in request.GET:
                        p = int(request.GET['page'])
                    else:
                        p = paginasesion
                    try:
                        page = paging.page(p)
                    except:
                        p = 1
                    page = paging.page(p)
                except:
                    page = paging.page(p)
                request.session['paginador'] = p
                data['paging'] = paging
                data['rangospaging'] = paging.rangos_paginado(p)
                data['page'] = page
                data['url_vars'] = url_vars
                data['listado'] = page.object_list
                return render(request, "postulate/adm_bancohabilitado/view.html", data)
            except Exception as ex:
                pass

# def loadpersondesiste(**kwargs):
#     try:
#         fecha_actual = datetime.now()
#
#         # Calcular la fecha hace 2 años desde la fecha actual
#         fecha_hace_dos_anios = fecha_actual - timedelta(days=730)
#         request = kwargs.get('request', None)
#         _var = lambda x: request.session.get(x, None) if not x in kwargs else kwargs.get(x, None)
#         persona = _var('persona')
#         desiste = PersonaDesiste.objects.filter(
#             status=True, persona=persona,
#             fecha__gte=fecha_hace_dos_anios.date()
#         ).order_by('-fecha').first()
#         return {'desiste':desiste}
#     except Exception as ex:
#         err_ = f'{ex.__str__()}({sys.exc_info()[-1].tb_lineno})'
#         print(err_)
#         return {'result':False, 'mensaje':err_}