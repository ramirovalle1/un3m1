# -*- coding: UTF-8 -*-
from datetime import datetime

from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.db.models import Q
from django.http import HttpResponseRedirect, JsonResponse
from django.shortcuts import render
from django.template import Context
from django.template.loader import get_template
from decorators import secure_module, last_access
from sagest.forms import ArchivoBecaDocenteForm
from sagest.models import BecaDocente, CategoriaRubroBeca, DetalleRubroBecaDocente
from sga.commonviews import adduserdata
from sga.funciones import MiPaginador, log, generar_nombre
from sga.funcionesxhtml2pdf import conviert_html_to_pdf
from sga.models import miinstitucion, CUENTAS_CORREOS
from sga.tasks import send_html_mail, conectar_cuenta


@login_required(redirect_field_name='ret', login_url='/loginsagest')
@secure_module
@last_access
@transaction.atomic()
def view(request):
    data = {}
    adduserdata(request, data)
    persona = request.session['persona']
    if request.method == 'POST':
        action = request.POST['action']

        if action == 'detallepdf':
            try:
                data['title'] = u'Proyecto Beca'
                data['becadocente'] = becadocente = BecaDocente.objects.filter(id=int(request.POST['id']))[0]
                data['detallebecadocentes'] = detallebecadocente = becadocente.detallebecadocente_set.filter(status=True).order_by('fechainicio')
                data['categoriarubrobecas'] = CategoriaRubroBeca.objects.filter(status=True, rubrobeca__detallerubrobecadocente__detallebecadocente__in=detallebecadocente).distinct()
                hoy = datetime.now().date()
                return conviert_html_to_pdf(
                    'adm_aprobacionbecasdocentes/proyectobeca_pdf.html',
                    {
                        'pagesize': 'A4',
                        'data': data,
                    }
                )
            except Exception as ex:
                pass

        if action == 'detalle_archivo':
            try:
                data['detallerubrobecadocente'] = detallerubrobecadocente = DetalleRubroBecaDocente.objects.get(pk=request.POST['id'], status=True)
                data['detallerubrobecadocentearchivo'] = detallerubrobecadocente.detallerubrobecadocentearchivo_set.filter(status=True)
                template = get_template("adm_aprobacionbecasdocentes/detalle_archivo.html")
                json_content = template.render(data)
                return JsonResponse({"result": "ok", 'html': json_content})
            except Exception as ex:
                return JsonResponse({"result": "bad", "mensaje": u"Error al obtener los datos."})

        if action == 'addaprobacion':
            try:
                becadocente = BecaDocente.objects.get(pk=request.POST['id'])
                becadocente.estadobeca=int(request.POST['esta'])
                becadocente.observacion=request.POST['obse']
                becadocente.save(request)
                lista = becadocente.becario.lista_emails()
                send_html_mail("Aprobación Beca Docente %s" % becadocente.proyecto ,"emails/aprobacion_beca_docente.html",{'sistema': request.session['nombresistema'], 'proyecto': becadocente.proyecto,'docente': becadocente.becario.nombre_completo_inverso(),'estado': becadocente.get_estadobeca_display(), 't': miinstitucion()}, lista, [], cuenta=CUENTAS_CORREOS[0][1])
                log(u'Aprobacion-Rechazo Beca-Docente: %s' % becadocente, request, "edit")
                return JsonResponse({"result": "ok"})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        if action == 'addarchivo':
            try:
                form = ArchivoBecaDocenteForm(request.POST, request.FILES)
                if form.is_valid():
                    becadocente = BecaDocente.objects.get(pk=request.POST['id'])
                    newfile = request.FILES['archivo']
                    newfile._name = generar_nombre("becadocenteresolucion_", newfile._name)
                    if becadocente.archivo:
                        log(u'Edito Archivo Resolucion Beca-Docente: %s' % becadocente, request, "edit")
                    else:
                        log(u'Adiciono Archivo Resolucion Beca-Docente: %s' % becadocente, request, "add")
                    becadocente.archivo = newfile
                    becadocente.save(request)
                    return JsonResponse({"result": "ok"})
                else:
                    raise NameError('Debe subir archivo pdf con los MG especificado')
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        if action == 'addarchivocontrato':
            try:
                form = ArchivoBecaDocenteForm(request.POST, request.FILES)
                if form.is_valid():
                    becadocente = BecaDocente.objects.get(pk=request.POST['id'])
                    newfile = request.FILES['archivo']
                    newfile._name = generar_nombre("becadocentecontrato_", newfile._name)
                    if becadocente.archivo:
                        log(u'Edito Archivo Contrato Beca-Docente: %s' % becadocente, request, "edit")
                    else:
                        log(u'Adiciono Archivo Contrato Beca-Docente: %s' % becadocente, request, "add")
                    becadocente.archivocontrato = newfile
                    becadocente.save(request)
                    return JsonResponse({"result": "ok"})
                else:
                    raise NameError('Debe subir archivo pdf con los MG especificado')
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        return JsonResponse({"result": "bad", "mensaje": u"Solicitud Incorrecta."})
    else:
        if 'action' in request.GET:
            action = request.GET['action']

            if action == 'rubros':
                try:
                    data['title'] = u'Detalle de Rubros-Becas'
                    data['becadocente'] = becadocente = BecaDocente.objects.get(pk=request.GET['id'])
                    data['detallebecadocentes'] = becadocente.detallebecadocente_set.filter(status=True).order_by('fechainicio')
                    return render(request, "adm_aprobacionbecasdocentes/rubros.html", data)
                except Exception as ex:
                    pass

            if action == 'detalle':
                try:
                    data = {}
                    data['becadocente'] = BecaDocente.objects.get(pk=int(request.GET['id']))
                    data['fecha'] = datetime.now().date()
                    data['aprobador'] = persona
                    template = get_template("adm_aprobacionbecasdocentes/detalle_aprobar.html")
                    json_content = template.render(data)
                    return JsonResponse({"result": "ok", 'data': json_content})
                except Exception as ex:
                    transaction.set_rollback(True)
                    return JsonResponse({"result": "bad", "mensaje": u"Error al obtener los datos."})

            if action == 'addarchivo':
                try:
                    data['title'] = u'Subir archivo Resolución OCAS'
                    form = ArchivoBecaDocenteForm()
                    data['idbecadocente'] = request.GET['id']
                    data['form'] = form
                    return render(request, "adm_aprobacionbecasdocentes/addarchivo.html", data)
                except Exception as ex:
                    pass

            if action == 'addarchivocontrato':
                try:
                    data['title'] = u'Subir archivo Contrato'
                    form = ArchivoBecaDocenteForm()
                    data['idbecadocente'] = request.GET['id']
                    data['form'] = form
                    return render(request, "adm_aprobacionbecasdocentes/addarchivocontrato.html", data)
                except Exception as ex:
                    pass

            return HttpResponseRedirect(request.path)

        else:
            data['title'] = u'Aprobación Proyectos Beca Docente'
            search = None
            ids = None
            if 's' in request.GET:
                search = request.GET['s']
            if search:
                becadocente = BecaDocente.objects.filter(Q(becario__nombre__icontains=search) | Q(becario__apellido1__icontains=search) | Q(becario__apellido2__icontains=search), status=True).order_by('id')
            elif 'id' in request.GET:
                ids = request.GET['id']
                becadocente = BecaDocente.objects.filter(id=ids,status=True).order_by('id')
            else:
                becadocente = BecaDocente.objects.filter(status=True).order_by('id')
            paging = MiPaginador(becadocente, 10)
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
            data['search'] = search if search else ""
            data['ids'] = ids if ids else ""
            data['listbecadocentes'] = page.object_list
            return render(request, "adm_aprobacionbecasdocentes/view.html", data)
