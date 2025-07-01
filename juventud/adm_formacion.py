# -*- coding: latin-1 -*-
from django.template.loader import get_template
from xlwt import *
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.http import HttpResponseRedirect, JsonResponse, HttpResponse
from django.shortcuts import render
from django.db.models import Q
from datetime import datetime
from decorators import secure_module, last_access
from juventud.forms import PostulacionPersonaForm
from juventud.models import Programaformacion, Personaformacion, PersonaPrograma
from sga.commonviews import adduserdata
from sga.funciones import MiPaginador
from sga.models import miinstitucion, CUENTAS_CORREOS
from sga.tasks import send_html_mail
from sga.templatetags.sga_extras import encrypt

@login_required(redirect_field_name='ret', login_url='/loginsga')
@secure_module
@last_access
@transaction.atomic()
def view(request):
    global ex
    data = {}
    data['fecha_actual'] = fecha_actual = datetime.now()
    adduserdata(request, data)
    persona = request.session['persona']
    if request.method == 'POST':
        if 'action' in request.POST:
            action = request.POST['action']

            if action == 'addpersona':
                try:
                    return JsonResponse({'result': 'ok'})
                except Exception as ex:
                    transaction.set_rollback(True)
                    return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos. %s" % ex})

            elif action == 'editpostulacion':
                try:
                    form = PostulacionPersonaForm(request.POST)
                    if form.is_valid():
                        postulante = PersonaPrograma.objects.get(pk=int(encrypt(request.POST['id'])))
                        postulante.estado = form.cleaned_data['estado']
                        postulante.observacion = form.cleaned_data['observacion']
                        postulante.aprobador = persona
                        postulante.fecharegistroestado = fecha_actual
                        if form.cleaned_data['envioemail']:
                            postulante.emailenviado = form.cleaned_data['envioemail']
                        postulante.save(request)

                        if form.cleaned_data['envioemail']:
                            send_html_mail("Escuela de Liderazgo", "emails/notificacion_juventud_ap.html",
                                           {'sistema': u'SISTEMA', 't': miinstitucion(), 'tiposistema_': 2, 'estado': int(postulante.estado)}, [postulante.personaformacion.email], [], cuenta=CUENTAS_CORREOS[4][1])

                        return JsonResponse({'result': False, 'mensaje': 'Edicion Exitosa'})
                except Exception as ex:
                    transaction.set_rollback(True)
                    return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        return JsonResponse({"result": "bad", "mensaje": u"Solicitud Incorrecta."})

    else:

        if 'action' in request.GET:
            data['action'] = action = request.GET['action']

            if action == 'listadoparticipantes':
                try:
                    data['title'] = u'Listado de participantes'
                    search, filtro, url_vars = request.GET.get('s', ''), Q(status=True), ''
                    codigoprograma = request.GET['idpro']
                    data['programa'] = programa = Programaformacion.objects.get(pk=codigoprograma,status=True)
                    if 's' in request.GET:
                        search = request.GET['s'].strip()
                        url_vars += f'&s={search}'
                        ss = search.split(' ')
                        if len(ss) == 1:
                            listadoparticipantes = programa.personaprograma_set.filter(
                                Q(personaformacion__nombres__icontains=search) |
                                Q(personaformacion__apellido1__icontains=search) |
                                Q(personaformacion__apellido2__icontains=search) |
                                Q(personaformacion__cedula__icontains=search),status=True).order_by('personaformacion__apellido1', 'personaformacion__apellido2')
                        else:
                            listadoparticipantes = programa.personaprograma_set.filter(
                                Q(personaformacion__apellido1__icontains=ss[0]) &
                                Q(personaformacion__apellido2__icontains=ss[1]),status=True).order_by('personaformacion__apellido1', 'personaformacion__apellido2')
                    else:
                        listadoparticipantes = programa.personaprograma_set.filter(status=True).order_by('personaformacion__apellido1', 'personaformacion__apellido2')
                    numerofilas = 25
                    paging = MiPaginador(listadoparticipantes, numerofilas)
                    p = 1
                    url_vars += '&action={}'.format(action)
                    url_vars += '&idpro={}'.format(codigoprograma)
                    try:
                        paginasesion = 1
                        if 'paginador' in request.session:
                            paginasesion = int(request.session['paginador'])
                        if 'page' in request.GET:
                            p = int(request.GET['page'])
                            if p == 1:
                                numerofilasguiente = numerofilas
                            else:
                                numerofilasguiente = numerofilas * (p - 1)
                        else:
                            p = paginasesion
                            if p == 1:
                                numerofilasguiente = numerofilas
                            else:
                                numerofilasguiente = numerofilas * (p - 1)
                        try:
                            page = paging.page(p)
                        except:
                            p = 1
                        page = paging.page(p)
                    except:
                        page = paging.page(p)
                    request.session['paginador'] = p
                    data['paging'] = paging
                    data['numerofilasguiente'] = numerofilasguiente
                    data['numeropagina'] = p
                    data['rangospaging'] = paging.rangos_paginado(p)
                    data['page'] = page
                    data['search'] = search if search else ""
                    data["url_vars"] = url_vars
                    data['listadoparticipantes'] = page.object_list
                    return render(request, "admisionjuventud/participantes.html", data)
                except Exception as ex:
                    pass

            elif action == 'xlsparticipantes':
                try:
                    __author__ = 'Unemi'
                    wb = Workbook(encoding='utf-8')
                    ws = wb.add_sheet('reporte 1')
                    fuentenormal = easyxf('font: name Verdana, color-index black, height 150; borders: left thin, right thin, top thin, bottom thin')
                    encabezado = 0
                    codigoprograma = request.GET['idpro']
                    programa = Programaformacion.objects.get(pk=codigoprograma, status=True)
                    listadoparticipantes = programa.personaprograma_set.filter(status=True).order_by('personaformacion__apellido1', 'personaformacion__apellido2')
                    response = HttpResponse(content_type="application/ms-excel")
                    response['Content-Disposition'] = 'attachment; filename =LISTADO_PARTICIPANTES.xls'
                    row_num = 0
                    columns = [
                        (u"#N", 1500),
                        (u"CEDULA", 4000),
                        (u"APELLIDOS Y NOMBRES", 15000),
                        (u"EMAIL", 10000),
                        (u"TELEFONO", 4000),
                        (u"GENERO", 4000),
                        (u"EDAD", 2000),
                        (u"PAIS", 10000),
                        (u"PROVINCIA", 10000),
                        (u"CANTON", 10000),
                        (u"DIRECCION", 10000),
                        (u"LUGAR NACIMIENTO", 10000),
                        (u"ESTADO", 3000),
                        (u"EMAIL ENVIADO", 3000),
                        (u"OBSERVACIÓN", 8000),
                        (u"PROYECTO", 15000),
                        (u"POBLACION", 15000),
                        (u"META", 15000),
                        (u"RESULTADO", 15000)
                    ]
                    for col_num in range(len(columns)):
                        ws.write(row_num, col_num, columns[col_num][0], fuentenormal)
                        ws.col(col_num).width = columns[col_num][1]

                    for participante in listadoparticipantes:
                        row_num += 1
                        edad = 0
                        email = 'NO'
                        if participante.emailenviado:
                            email = 'SI'
                        if participante.personaformacion.fechanacimiento:
                            edad = fecha_actual.year - participante.personaformacion.fechanacimiento.year - ((fecha_actual.month, fecha_actual.day) < (participante.personaformacion.fechanacimiento.month, participante.personaformacion.fechanacimiento.day))
                        ws.write(row_num, 0, row_num, fuentenormal)
                        ws.write(row_num, 1, str(participante.personaformacion.cedula), fuentenormal)
                        ws.write(row_num, 2, str(participante.personaformacion), fuentenormal)
                        ws.write(row_num, 3, str(participante.personaformacion.email), fuentenormal)
                        ws.write(row_num, 4, str(participante.personaformacion.telefono), fuentenormal)
                        ws.write(row_num, 5, str(participante.personaformacion.sexo), fuentenormal)
                        ws.write(row_num, 6, edad, fuentenormal)
                        ws.write(row_num, 7, participante.personaformacion.pais.nombre, fuentenormal)
                        ws.write(row_num, 8, participante.personaformacion.provincia.nombre, fuentenormal)
                        ws.write(row_num, 9, participante.personaformacion.canton.nombre, fuentenormal)
                        ws.write(row_num, 10, participante.personaformacion.direccion, fuentenormal)
                        ws.write(row_num, 11, participante.personaformacion.lugarnacimiento, fuentenormal)
                        ws.write(row_num, 12, participante.get_estado_display(), fuentenormal)
                        ws.write(row_num, 13, email, fuentenormal)
                        ws.write(row_num, 14, participante.observacion, fuentenormal)
                        ws.write(row_num, 15, participante.nombreproyecto, fuentenormal)
                        ws.write(row_num, 16, participante.poblacion, fuentenormal)
                        ws.write(row_num, 17, participante.meta, fuentenormal)
                        ws.write(row_num, 18, participante.resultado, fuentenormal)
                    wb.save(response)
                    return response
                except Exception as es:
                    pass

            elif action == 'editpostulacion':
                try:
                    data['portulacion'] = portulacion = PersonaPrograma.objects.get(pk=request.GET['id'])
                    data['title'] = u'Aprobar o rechazar'
                    form = PostulacionPersonaForm(initial={'estado': portulacion.estado,
                                                           'observacion': portulacion.observacion})
                    data['form'] = form
                    template = get_template("admisionjuventud/editpostulacion.html")
                    return JsonResponse({"result": True, 'data': template.render(data)})
                except Exception as ex:
                    pass

            return HttpResponseRedirect(request.path)
        else:
            try:
                data['title'] = u'Administración de formación política'
                data['listadoprograma'] = Programaformacion.objects.filter(status=True)
                return render(request, "admisionjuventud/admview.html", data)
            except Exception as ex:
                pass