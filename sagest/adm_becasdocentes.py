# -*- coding: UTF-8 -*-
import json
from datetime import datetime

from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.db.models import Q
from django.http import HttpResponseRedirect, JsonResponse
from django.shortcuts import render
from django.template import Context
from django.template.loader import get_template
from decorators import secure_module, last_access
from sagest.forms import DetalleBecaDocenteLiquidacionForm, DetalleBecaDocentePresupuestoForm
from sagest.models import BecaDocente, CategoriaRubroBeca, DetalleRubroBecaDocente, DetalleBecaDocente
from sga.commonviews import adduserdata
from sga.forms import ArchivoSolicitudSecretariaForm
from sga.funciones import MiPaginador, generar_nombre, log
from sga.funcionesxhtml2pdf import conviert_html_to_pdf
from sga.models import CUENTAS_CORREOS
from sga.tasks import send_html_mail, conectar_cuenta


@login_required(redirect_field_name='ret', login_url='/loginsagest')
@secure_module
@last_access
@transaction.atomic()
def view(request):
    data = {}
    adduserdata(request, data)
    if request.method == 'POST':
        action = request.POST['action']

        if action == 'detallepdf':
            try:
                data['title'] = u'Proyecto Beca'
                data['becadocente'] = becadocente = BecaDocente.objects.filter(id=int(request.POST['id']))[0]
                data['detallebecadocentes'] = detallebecadocente = becadocente.detallebecadocente_set.filter(status=True).distinct().order_by('fechainicio')
                data['categoriarubrobecas'] = CategoriaRubroBeca.objects.filter(status=True, rubrobeca__detallerubrobecadocente__detallebecadocente__in=detallebecadocente).distinct()
                hoy = datetime.now().date()
                return conviert_html_to_pdf(
                    'adm_becasdocentes/proyectobeca_pdf.html',
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
                template = get_template("adm_becasdocentes/detalle_archivo.html")
                json_content = template.render(data)
                return JsonResponse({"result": "ok", 'html': json_content})
            except Exception as ex:
                return JsonResponse({"result": "bad", "mensaje": u"Error al obtener los datos."})

        if action == 'liquidacion':
            try:
                form = DetalleBecaDocenteLiquidacionForm(request.POST, request.FILES)
                d = request.FILES['archivoliquidacion']
                if d.size > 10485760:
                    return JsonResponse({"result": "bad", "mensaje": u"Error, archivo mayor a 10 Mb."})
                extencion = d._name.split('.')
                exte = extencion[1]
                if not exte == 'pdf':
                    return JsonResponse({"result": "bad", "mensaje": u"Solo archivos .pdf"})
                if form.is_valid():
                    datos = json.loads(request.POST['lista_items1'])
                    detallebecadocente = DetalleBecaDocente.objects.get(pk=request.POST['id'])
                    newfile = request.FILES['archivoliquidacion']
                    newfile._name = generar_nombre("detallebecadocenteliquidacion_", newfile._name)
                    detallebecadocente.archivoliquidacion = newfile
                    detallebecadocente.observacionliquidacion = form.cleaned_data['observacionliquidacion']
                    detallebecadocente.estadodetallebeca = 2
                    detallebecadocente.save(request)
                    for elemento in datos:
                        detallerubrobecadocente = DetalleRubroBecaDocente.objects.filter(detallebecadocente=detallebecadocente, rubrobeca_id=int(elemento['id']))[0]
                        detallerubrobecadocente.valorpagado = elemento['valors']
                        detallerubrobecadocente.save(request)
                    mail = 'presupuesto@unemi.edu.ec'
                    docente = detallebecadocente.becadocente.becario.nombre_completo_inverso()
                    proyecto = detallebecadocente.becadocente.proyecto
                    detalle = str(detallebecadocente.fechainicio) + " - " + str(detallebecadocente.fechafin)
                    send_html_mail("Liquidación Detalle Beca Docente", "emails/liquidacionbecadocente.html", {'sistema': request.session['nombresistema'], 'docente': docente, 'proyecto': proyecto, 'detalle': detalle}, mail, [], cuenta=CUENTAS_CORREOS[0][1])
                    log(u'Subir archivo detalle beca docente liquidacion: %s' % detallebecadocente, request, "edit")
                    return JsonResponse({"result": "ok"})
                else:
                    raise NameError('Error')
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error, archivo mayor a 10 Mb."})

        if action == 'presupuesto':
            try:
                form = DetalleBecaDocentePresupuestoForm(request.POST, request.FILES)
                d = request.FILES['archivopresupuesto']
                if d.size > 10485760:
                    return JsonResponse({"result": "bad", "mensaje": u"Error, archivo mayor a 10 Mb."})
                extencion = d._name.split('.')
                exte = extencion[1]
                if not exte == 'pdf':
                    return JsonResponse({"result": "bad", "mensaje": u"Solo archivos .pdf"})
                if form.is_valid():
                    detallebecadocente = DetalleBecaDocente.objects.get(pk=request.POST['id'])
                    newfile = request.FILES['archivopresupuesto']
                    newfile._name = generar_nombre("detallebecadocentepresupuesto_", newfile._name)
                    detallebecadocente.archivopresupuesto = newfile
                    detallebecadocente.observacionpresupuesto = form.cleaned_data['observacionpresupuesto']
                    detallebecadocente.estadodetallebeca = 3
                    detallebecadocente.save(request)
                    log(u'Subir archivo detalle beca docente presupuesto: %s' % detallebecadocente, request, "edit")
                    return JsonResponse({"result": "ok"})
                else:
                    raise NameError('Error')
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error, archivo mayor a 10 Mb."})

        return JsonResponse({"result": "bad", "mensaje": u"Solicitud Incorrecta."})
    else:
        if 'action' in request.GET:
            action = request.GET['action']

            if action == 'rubros':
                try:
                    data['title'] = u'Detalle de Rubros-Becas'
                    data['becadocente'] = becadocente = BecaDocente.objects.get(pk=request.GET['id'])
                    data['detallebecadocentes'] = becadocente.detallebecadocente_set.filter(status=True).order_by('fechainicio')
                    return render(request, "adm_becasdocentes/rubros.html", data)
                except Exception as ex:
                    pass

            if action == 'liquidacion':
                try:
                    data['title'] = u'Revisión-Liquidación'
                    data['detallebecadocente'] = detallebecadocente = DetalleBecaDocente.objects.get(pk=request.GET['id'])
                    data['becadocente'] = detallebecadocente.becadocente
                    data['contratoscamposseleccion'] = detallebecadocente.detallerubrobecadocente_set.filter(status=True)
                    data['form'] = DetalleBecaDocenteLiquidacionForm()
                    return render(request, "adm_becasdocentes/liquidacion.html", data)
                except Exception as ex:
                    pass

            if action == 'presupuesto':
                try:
                    data['title'] = u'Presupuesto'
                    data['detallebecadocente'] = detallebecadocente = DetalleBecaDocente.objects.get(pk=request.GET['id'])
                    data['becadocente'] = detallebecadocente.becadocente
                    data['form'] = DetalleBecaDocentePresupuestoForm()
                    return render(request, "adm_becasdocentes/presupuesto.html", data)
                except Exception as ex:
                    pass

            return HttpResponseRedirect(request.path)

        else:
            data['title'] = u'Proyectos Beca Docente - Financiero'
            search = None
            ids = None
            if 's' in request.GET:
                search = request.GET['s']
            if search:
                becadocente = BecaDocente.objects.filter(Q(becario__nombre__icontains=search) | Q(becario__apellido1__icontains=search) | Q(becario__apellido2__icontains=search), status=True, estadobeca=2).order_by('id')
            elif 'id' in request.GET:
                ids = request.GET['id']
                becadocente = BecaDocente.objects.filter(id=ids,status=True, estadobeca=2).order_by('id')
            else:
                becadocente = BecaDocente.objects.filter(status=True, estadobeca=2).order_by('id')
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
            return render(request, "adm_becasdocentes/view.html", data)
