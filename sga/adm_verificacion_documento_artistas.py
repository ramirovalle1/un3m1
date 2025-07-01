# -*- coding: latin-1 -*-
import random

from django.db.models import Q
from django.template.loader import get_template
from xlwt import *
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.http import HttpResponse, JsonResponse
from django.shortcuts import render
from decorators import secure_module, last_access
from sagest.forms import DiscapacidadForm2, ArtistaValidacionForm, BecaValidacionForm, DeportistaValidacionForm, \
    DiscapacidadValidacionForm, EtniaValidacionForm, MigranteValidacionForm
from sga.commonviews import adduserdata, obtener_reporte
from sga.funciones import generar_nombre, fechaformatostr, MiPaginador
from sga.models import Inscripcion, ArtistaPersona, BecaPersona, DeportistaPersona, PerfilInscripcion, MigrantePersona, \
    Carrera, CampoArtistico
from sga.funciones import log

@login_required(redirect_field_name='ret', login_url='/loginsga')
@secure_module
@last_access
@transaction.atomic()
def view(request):
    global ex
    data = {}
    adduserdata(request, data)
    data['periodo'] = periodo = request.session['periodo']
    if 'action' in request.POST:
        action = request.POST['action']
        if action == 'discapacidad':
            try:
                if 'archivo' in request.FILES:
                    newfile = request.FILES['archivo']
                    if newfile.size > 2194304:
                        return JsonResponse({"result": "bad", "mensaje": u"Error, Tamaño de archivo Maximo permitido es de 2Mb"})
                f = DiscapacidadForm2(request.POST)
                if f.is_valid():
                    newfile = None
                    perfil = Inscripcion.objects.get(pk=int(request.POST['id'])).persona.mi_perfil()
                    perfil.tienediscapacidad = f.cleaned_data['tienediscapacidad']
                    perfil.tipodiscapacidad = f.cleaned_data['tipodiscapacidad']
                    perfil.porcientodiscapacidad = f.cleaned_data['porcientodiscapacidad'] if f.cleaned_data[
                        'porcientodiscapacidad'] else 0
                    perfil.carnetdiscapacidad = f.cleaned_data['carnetdiscapacidad']
                    perfil.verificadiscapacidad = f.cleaned_data['verificadiscapacidad']
                    if not f.cleaned_data['tienediscapacidad']:
                        perfil.archivo = None
                    if 'archivo' in request.FILES:
                        newfile = request.FILES['archivo']
                        newfile._name = generar_nombre("archivosdiscapacidad_", newfile._name)
                        perfil.archivo = newfile
                    perfil.save(request)
                    log(u'Modifico tipo de discapacidad: %s' % perfil, request, "edit")
                    return JsonResponse({'result': 'ok'})
                else:
                     raise NameError('Error')
            except Exception as ex:
                return JsonResponse({'result': 'bad', 'mensaje': u'Error al guardar los datos'})

        elif action == 'validarartista':
            try:
                form = ArtistaValidacionForm(request.POST)
                if form.is_valid():
                    artista = ArtistaPersona.objects.get(pk=int(request.POST['ida']))
                    artista.estadoarchivo = form.cleaned_data['estadoartista']
                    artista.observacion = form.cleaned_data['observacionartista'].strip().upper()
                    artista.verificado = True if int(form.cleaned_data['estadoartista']) == 2 else False
                    artista.save(request)
                    log(u'Actualizó registro de artista: %s' % artista, request, "edit")
                    return JsonResponse({"result": "ok"})
                else:
                    raise NameError('Error')
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})
    else:
        if 'action' in request.GET:
            action = request.GET['action']
            if action == 'discapacidad':
                try:
                    data['title'] = u'Discapacidad'
                    inscripcion = Inscripcion.objects.get(pk=int(request.GET['id']))
                    perfil = inscripcion.persona.mi_perfil()
                    form = DiscapacidadForm2(initial={'tienediscapacidad': perfil.tienediscapacidad,
                                                      'tipodiscapacidad': perfil.tipodiscapacidad,
                                                      'porcientodiscapacidad': perfil.porcientodiscapacidad,
                                                      'carnetdiscapacidad': perfil.carnetdiscapacidad,
                                                      'verificadiscapacidad': perfil.verificadiscapacidad})
                    data['form'] = form
                    data['inscripcion'] = inscripcion
                    return render(request, "adm_discapacitados/discapacidad.html", data)
                except:
                    pass
            if action == 'descargar':
                try:
                    __author__ = 'UNEMI'
                    style0 = easyxf('font: name Times New Roman, color-index blue, bold off', num_format_str='#,##0.00')
                    style_nb = easyxf('font: name Times New Roman, color-index blue, bold on',
                                      num_format_str='#,##0.00')
                    style_sb = easyxf('font: name Times New Roman, color-index blue, bold on')
                    title = easyxf(
                        'font: name Times New Roman, color-index blue, bold on , height 350; alignment: horiz centre')
                    style1 = easyxf(num_format_str='D-MMM-YY')
                    font_style = XFStyle()
                    font_style.font.bold = True
                    font_style2 = XFStyle()
                    font_style2.font.bold = False
                    wb = Workbook(encoding='utf-8')
                    ws = wb.add_sheet('exp_xls_post_part')
                    response = HttpResponse(content_type="application/ms-excel")
                    response[
                        'Content-Disposition'] = 'attachment; filename=estudiantes_discapacidad_' + random.randint(1,
                                                                                                                   10000).__str__() + '.xls'
                    columns = [
                        (u"CEDULA", 3000),
                        (u"ESTUDIANTE", 12000),
                        (u"CORREO PERSONAL", 8000),
                        (u"CORREO INSTITUCIONAL", 8000),
                        (u"TELEFONOS", 6000),
                        (u"CARRERA", 12000),
                        (u"FACULTAD", 12000),
                        (u"SECCION", 6000),
                        (u"NIVEL", 6000),
                        (u"DISCAPACIDAD", 6000),
                        (u"PORCENTAJE", 6000),
                        (u"CARNET", 6000),
                        (u"BECA", 6000),
                        (u"VERIFICADO POR LA UBE", 6000),
                        (u"SEXO", 6000)
                    ]
                    row_num = 0
                    for col_num in range(len(columns)):
                        ws.write(row_num, col_num, columns[col_num][0], font_style)
                        ws.col(col_num).width = columns[col_num][1]
                    inscripcion = Inscripcion.objects.filter(matricula__status=True, matricula__nivel__periodo=periodo,
                                                             persona__perfilinscripcion__tienediscapacidad=True).order_by(
                        "persona")
                    row_num = 1
                    for r in inscripcion:
                        i = 0
                        campo1 = r.persona.cedula
                        campo2 = r.persona.__str__()
                        campo3 = r.persona.email
                        campo4 = r.persona.emailinst
                        campo5 = "%s - %s" % (r.persona.telefono, r.persona.telefono_conv)
                        campo15 = r.coordinacion.__str__()
                        campo6 = r.carrera.__str__()
                        campo7 = r.sesion.nombre
                        campo8 = r.matricula_set.filter(nivel__periodo=periodo)[0].nivelmalla.nombre
                        campo9 = ""
                        if r.persona.mi_perfil():
                            if r.persona.mi_perfil().tipodiscapacidad:
                                campo9 = r.persona.mi_perfil().tipodiscapacidad.nombre
                        campo10 = ("%s" % r.persona.mi_perfil().porcientodiscapacidad) + "%"
                        campo11 = r.persona.mi_perfil().carnetdiscapacidad
                        campo12 = "BECADO" if r.tiene_registro_becario() else "NO BECADO"
                        campo13 = "SI" if r.persona.mi_perfil().verificadiscapacidad else "NO"
                        campo14 = r.persona.sexo.nombre if r.persona.sexo else ''
                        ws.write(row_num, 0, campo1, font_style2)
                        ws.write(row_num, 1, campo2, font_style2)
                        ws.write(row_num, 2, campo3, font_style2)
                        ws.write(row_num, 3, campo4, font_style2)
                        ws.write(row_num, 4, campo5, font_style2)
                        ws.write(row_num, 5, campo6, font_style2)
                        ws.write(row_num, 6, campo15, font_style2)
                        ws.write(row_num, 7, campo7, font_style2)
                        ws.write(row_num, 8, campo8, font_style2)
                        ws.write(row_num, 9, campo9, font_style2)
                        ws.write(row_num, 10, campo10, font_style2)
                        ws.write(row_num, 11, campo11, font_style2)
                        ws.write(row_num, 12, campo12, font_style2)
                        ws.write(row_num, 13, campo13, font_style2)
                        ws.write(row_num, 14, campo14, font_style2)
                        row_num += 1
                    wb.save(response)
                    return response
                except Exception as ex:
                    pass

            elif action == 'datos':
                try:
                    artista = ArtistaPersona.objects.get(pk=int(request.GET['id']))
                    data['artista'] = artista
                    form = ArtistaValidacionForm(initial={'estadoartista':artista.estadoarchivo, 'observacionartista':artista.observacion})
                    form.editar()
                    form.fields['estadoartista'].choices= (
                                ('', u'--Seleccione--'),
                                (2, u'VALIDADO'),
                                (3, u'RECHAZADO'),
                                (5, u'REVISIÓN'),
                                (6, u'RECHAZADO IO')
                    )
                    data['form'] = form
                    template = get_template("adm_verificacion_documento/artistas/datos.html")
                    return JsonResponse({"result": True, 'datos': template.render(data)})
                except Exception as ex:
                    return JsonResponse({'result': False, 'mensaje': u'Error al obtener los datos'})

        else:
            data['title'] = u'Verificación de Documentos'
            search = None
            ids = None
            inscripciones = Inscripcion.objects.filter(matricula__status=True,
                                                  matricula__nivel__periodo=periodo,
                                                  persona__artistapersona__isnull=False,
                                                  persona__artistapersona__status=True,
                                                  persona__artistapersona__vigente=1)

            artistas = ArtistaPersona.objects.filter(
                                pk__in=inscripciones.values_list('persona__artistapersona__id', flat=True).distinct(),
                                persona__inscripcion__matricula__nivel__periodo=periodo
                        )

            carreras = Carrera.objects.filter(id__in=inscripciones.values_list('carrera_id', flat=True).distinct())
            camposartisticos = CampoArtistico.objects.filter(
                id__in=artistas.values_list('campoartistico__id', flat=True).distinct())

            if 's' in request.GET:
                search = request.GET['s']
                artistas = artistas.filter(Q(persona__nombres__icontains=search) |
                                           Q(persona__cedula__icontains=search)|
                                           Q(persona__apellido1__icontains=search)|
                                           Q(persona__apellido2__icontains=search)|
                                           Q(grupopertenece__icontains=search)
                                           )

            verificacion = 0
            if 'veri' in request.GET:
                verificacion = int(request.GET['veri'])
                if verificacion > 0:
                    artistas = artistas.filter(verificado=int(request.GET['veri']) == 1)

            carreraselect = 0
            if 'c' in request.GET:
                carreraselect = int(request.GET['c'])
                if carreraselect > 0:
                    artistas = artistas.filter(persona__inscripcion__carrera_id=carreraselect)



            modalidadselect = 0
            if 'm' in request.GET:
                modalidadselect = int(request.GET['m'])
                if modalidadselect > 0:
                    artistas = artistas.filter(persona__inscripcion__modalidad_id=modalidadselect)

            campoartisticoselect = 0
            if 'campa' in request.GET:
                campoartisticoselect = int(request.GET['campa'])
                if campoartisticoselect > 0:
                    artistas = artistas.filter(campoartistico__id=campoartisticoselect)


            artistas = artistas.order_by("persona")
            paging = MiPaginador(artistas, 25)

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
            data['page'] = page
            data['rangospaging'] = paging.rangos_paginado(p)
            data['artistas'] = page.object_list
            data['carreras'] = carreras
            data['carreraselect'] = carreraselect
            data['camposartisticos'] = camposartisticos
            data['campoartisticoselect'] = campoartisticoselect
            data['modalidadselect'] = modalidadselect
            data['verificacion'] = verificacion

            data['search'] = search if search else ""
            data['ids'] = ids if ids else ""
            data['form'] = ArtistaValidacionForm()
            data['reporte_1'] = obtener_reporte('hoja_vida_sagest')
            data['reporte_2'] = obtener_reporte('discapacitados')
            return render(request, "adm_verificacion_documento/artistas/view.html", data)