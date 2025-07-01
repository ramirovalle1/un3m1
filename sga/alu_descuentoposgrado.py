# -*- coding: latin-1 -*-
from datetime import datetime

from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.http import HttpResponseRedirect, JsonResponse
from django.shortcuts import render
from django.template import Context
from django.template.loader import get_template

from decorators import secure_module, last_access
from posgrado.forms import RequisitosMaestriaForm
from sga.commonviews import adduserdata
from sga.forms import IngresoDescuentoPosgradoForm, SubirEvidenciaDescuentoForm
from sga.funciones import log, generar_nombre, variable_valor
from sga.models import DescuentoPosgradoMatricula, ConfiguracionDescuentoPosgrado, \
    DetalleConfiguracionDescuentoPosgrado, EvidenciasDescuentoPosgradoMatricula, \
    RequisitosDetalleConfiguracionDescuentoPosgrado, DetalleEvidenciaDescuentoPosgradoMatricula, miinstitucion
from sga.tasks import conectar_cuenta, send_html_mail


@login_required(redirect_field_name='ret', login_url='/loginsga')
@secure_module
@last_access
@transaction.atomic()
def view(request):
    data = {}
    adduserdata(request, data)
    persona = request.session['persona']
    perfilprincipal = request.session['perfilprincipal']
    periodo = request.session['periodo']
    if not perfilprincipal.es_estudiante():
        return HttpResponseRedirect("/?info=Solo los perfiles de estudiantes pueden ingresar al modulo.")
    inscripcion = perfilprincipal.inscripcion
    if inscripcion.mi_coordinacion().id != 7:
        return HttpResponseRedirect("/?info=Módulo solo para estudiantes de posgrado.")
    malla = inscripcion.malla_inscripcion().malla
    matricula = inscripcion.matricula_periodo(periodo)
    carrera = inscripcion.carrera
    if periodo.tipo.id == 3 or periodo.tipo.id == 4:
        a=1
    else:
        return HttpResponseRedirect("/?info=Solo los perfiles de estudiantes de Maestrías pueden ingresar al modulo.")
    if request.method == 'POST':
        if 'action' in request.POST:
            action = request.POST['action']
            if action == 'add':
                try:
                    f = IngresoDescuentoPosgradoForm(request.POST, request.FILES)
                    if 'archivo' in request.FILES:
                        arch = request.FILES['archivo']
                        extension = arch._name.split('.')
                        tam = len(extension)
                        exte = extension[tam - 1]
                        if arch.size > 10485760:
                            return JsonResponse({"result": "bad", "mensaje": u"Error, el tamaño del archivo es mayor a 10 Mb."})
                        if not exte.lower() == 'pdf':
                            return JsonResponse({"result": "bad", "mensaje": u"Solo se permiten archivos .pdf"})

                    if f.is_valid():
                        detalle = DetalleConfiguracionDescuentoPosgrado.objects.get(descuentoposgrado=f.cleaned_data['descuentoposgrado'], periododetalleconfiguraciondescuentoposgrado__periodo=periodo, status=True, periododetalleconfiguraciondescuentoposgrado__status=True)

                        descuentoposgradomatricula = DescuentoPosgradoMatricula(matricula=matricula,
                                                                                detalleconfiguraciondescuentoposgrado=detalle)
                        descuentoposgradomatricula.save(request)
                        if 'archivo' in request.FILES:
                            newfile = request.FILES['archivo']
                            newfile._name = generar_nombre(str(inscripcion.persona_id), newfile._name)
                            descuentoposgradomatricula.archivo = newfile
                        descuentoposgradomatricula.save(request)
                        log(u'Adiciono Tema Titulación PosGrado: %s' % descuentoposgradomatricula, request, "add")
                        return JsonResponse({"result": "ok"})
                    else:
                        raise NameError('Error')
                except Exception as ex:
                    transaction.set_rollback(True)
                    return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos %s." % ex})

            elif action == 'delete':
                try:
                    solicitud = DescuentoPosgradoMatricula.objects.get(pk=int(request.POST['id']), status=True)
                    log(u'Eliminó la solicitud descuento estudiante posgrado: %s' % solicitud, request, "del")
                    solicitud.delete()
                    return JsonResponse({"result": "ok"})
                except Exception as ex:
                    transaction.set_rollback(True)
                    return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

            if action == 'adddoc':
                try:
                    f = SubirEvidenciaDescuentoForm(request.POST, request.FILES)
                    newfilep = None
                    if 'archivo' in request.FILES:
                        newfilep = request.FILES['archivo']
                        if newfilep:
                            if newfilep.size > 12582912:
                                return JsonResponse({"result": "bad", "mensaje": u"Error, archivo mayor a 12 Mb."})
                            elif newfilep.size <= 0:
                                return JsonResponse({"result": "bad", "mensaje": u"Error, el archivo Propuesta Práctica esta vacío."})
                            else:
                                newfilesd = newfilep._name
                                ext = newfilesd[newfilesd.rfind("."):]
                                if ext == '.pdf':
                                    newfilep._name = generar_nombre("evidencia_", newfilep._name)
                                else:
                                    return JsonResponse({"result": "bad","mensaje": u"Error, archivo de Evidencia solo en .pdf."})
                    if newfilep:
                        cabecera = DescuentoPosgradoMatricula.objects.get(pk=int(request.POST['id']))
                        if f.is_valid():
                            if newfilep:
                                propuesta = EvidenciasDescuentoPosgradoMatricula(descuentoposgradomatricula=cabecera,
                                                                                 evidencia=f.cleaned_data['evidencia'],
                                                                                 requisitosdetalleconfiguraciondescuentoposgrado=f.cleaned_data['requisitosdetalleconfiguraciondescuentoposgrado'],
                                                                                 archivo=newfilep)
                                propuesta.save(request)
                            log(u"Añade archivo evidencia descuento  posgrado: %s" % (propuesta), request, "add")
                            return JsonResponse({'result': 'ok'})
                        else:
                            return JsonResponse({'result': 'bad', 'mensaje': u'Error, al guardar los archivos'})
                    else:
                        return JsonResponse({'result': 'bad', 'mensaje': u'Ingrese almenos un archivo'})
                except Exception as ex:
                    transaction.set_rollback(True)
                    return JsonResponse({'result': 'bad', 'mensaje': u'Ocurrio un problema al guardar archivos'})

            elif action == 'deldoc':
                try:
                    revision = EvidenciasDescuentoPosgradoMatricula.objects.filter(pk=request.POST['id'])
                    revision.delete()
                    log(u"Elimina archivo de evidencia de descuento posgrado %s" % (revision), request, "delete")
                    return JsonResponse({'result': 'ok'})
                except Exception as ex:
                    transaction.set_rollback(True)
                    return JsonResponse({'result': 'bad'})

            if action == 'cargamasiva':
                try:
                    inscripcioncohorte = DescuentoPosgradoMatricula.objects.get(pk=request.POST['id'])
                    listadorequisitosmaestria = RequisitosDetalleConfiguracionDescuentoPosgrado.objects.filter(detalleconfiguraciondescuentoposgrado=inscripcioncohorte.detalleconfiguraciondescuentoposgrado,status=True)
                    for requi in listadorequisitosmaestria:
                        nombrefile = 'requisito' + str(requi.id)
                        if nombrefile in request.FILES:
                            if not EvidenciasDescuentoPosgradoMatricula.objects.filter(requisitosdetalleconfiguraciondescuentoposgrado=requi,descuentoposgradomatricula=inscripcioncohorte,status=True).exists():
                                requisitomaestria = EvidenciasDescuentoPosgradoMatricula(requisitosdetalleconfiguraciondescuentoposgrado=requi,
                                                                                         descuentoposgradomatricula=inscripcioncohorte)
                                requisitomaestria.save(request)
                                newfile = request.FILES[nombrefile]
                                newfile._name = generar_nombre("requisitodescuentoposgrado_" + str(requi.id) + "_", newfile._name)
                                requisitomaestria.archivo = newfile
                                requisitomaestria.save(request)
                                log(u'Adicionó requisito descuento de maestria solicitante: %s' % requisitomaestria.requisitosdetalleconfiguraciondescuentoposgrado,request, "add")
                                detalle = DetalleEvidenciaDescuentoPosgradoMatricula(evidencia=requisitomaestria,
                                                                                     estadorevision=1,
                                                                                     fecha=datetime.now().date(),
                                                                                     observacion='')
                                detalle.save(request)
                    send_html_mail("Ingreso Evidencias Descuento-UNEMI.", "emails/registroingresoevidencias.html",{'sistema': u'Descuento Posgrado - UNEMI', 'fecha': datetime.now().date(),'hora': datetime.now().time(), 't': miinstitucion()},inscripcioncohorte.matricula.inscripcion.persona.emailpersonal(), [],cuenta=variable_valor('CUENTAS_CORREOS')[16])
                    return JsonResponse({"result": "ok"})
                except Exception as ex:
                    transaction.set_rollback(True)
                    return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

            if action == 'cargararchivo':
                try:
                    if 'archivo' in request.FILES:
                        newfile = request.FILES['archivo']
                        if newfile.size > 10485760:
                            return JsonResponse(
                                {"result": "bad", "mensaje": u"Error, Tamaño de archivo Maximo permitido es de 10Mb"})
                        else:
                            newfiles = request.FILES['archivo']
                            newfilesd = newfiles._name
                            ext = newfilesd[newfilesd.rfind("."):]
                            if not ext.lower() == '.pdf':
                                return JsonResponse({"result": "bad", "mensaje": u"Error, solo archivos .pdf."})
                    f = RequisitosMaestriaForm(request.POST)
                    if f.is_valid():
                        inscripcioncohorte = DescuentoPosgradoMatricula.objects.get(pk=request.POST['id'])
                        requisitosmaestria = RequisitosDetalleConfiguracionDescuentoPosgrado.objects.get(pk=request.POST['idevidencia'])
                        if not EvidenciasDescuentoPosgradoMatricula.objects.filter(requisitosdetalleconfiguraciondescuentoposgrado=requisitosmaestria,descuentoposgradomatricula=inscripcioncohorte,status=True).exists():
                            requisitomaestria = EvidenciasDescuentoPosgradoMatricula(requisitosdetalleconfiguraciondescuentoposgrado=requisitosmaestria,
                                                                                     descuentoposgradomatricula=inscripcioncohorte)
                            requisitomaestria.save(request)
                            if 'archivo' in request.FILES:
                                newfile = request.FILES['archivo']
                                newfile._name = generar_nombre("requisitodescuentoposgrado_", newfile._name)
                                requisitomaestria.archivo = newfile
                                requisitomaestria.save(request)
                            log(u'Adicionó requisito de descuento maestria solicitante: %s' % requisitomaestria.requisitosdetalleconfiguraciondescuentoposgrado, request,"add")
                            detalle = DetalleEvidenciaDescuentoPosgradoMatricula(evidencia=requisitomaestria,
                                                                                 estadorevision=1,
                                                                                 fecha=datetime.now().date(),
                                                                                 observacion=f.cleaned_data['observacion'])
                            detalle.save(request)
                            return JsonResponse({"result": "ok"})
                        else:
                            if 'archivo' in request.FILES:
                                newfile = request.FILES['archivo']
                                if newfile.size > 10485760:
                                    return JsonResponse({"result": "bad","mensaje": u"Error, Tamaño de archivo Maximo permitido es de 10Mb"})
                                else:
                                    newfiles = request.FILES['archivo']
                                    newfilesd = newfiles._name
                                    ext = newfilesd[newfilesd.rfind("."):]
                                    if not ext.lower() == '.pdf':
                                        return JsonResponse({"result": "bad", "mensaje": u"Error, solo archivos .pdf."})
                            f = RequisitosMaestriaForm(request.POST)
                            requisito = EvidenciasDescuentoPosgradoMatricula.objects.get(requisitosdetalleconfiguraciondescuentoposgrado=requisitosmaestria,descuentoposgradomatricula=inscripcioncohorte,status=True)
                            if f.is_valid():
                                # requisito.observacion = f.cleaned_data['observacion']
                                # requisito.estadorevision = 1
                                # requisito.save(request)
                                if 'archivo' in request.FILES:
                                    newfile = request.FILES['archivo']
                                    newfile._name = generar_nombre("requisitopgrado_", newfile._name)
                                    requisito.archivo = newfile
                                    requisito.save(request)
                                detalle = DetalleEvidenciaDescuentoPosgradoMatricula(evidencia=requisito,
                                                                                     estadorevision=1,
                                                                                     # persona=inscripcioncohorte.inscripcionaspirante.persona,
                                                                                     fecha=datetime.now().date(),
                                                                                     observacion=f.cleaned_data['observacion'])
                                detalle.save(request)
                                log(u'Editó requisito de descuento maestria solicitante: %s' % requisito, request, "edit")
                                return JsonResponse({"result": "ok"})
                            else:
                                raise NameError('Error')
                    else:
                        raise NameError('Error')
                except Exception as ex:
                    transaction.set_rollback(True)
                    return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

            return JsonResponse({"result": "bad", "mensaje": u"Solicitud Incorrecta."})
    else:
        if 'action' in request.GET:
            action = request.GET['action']

            if action == 'add':
                try:
                    data['title'] = u'Selección Descuento PosGrado'
                    form = IngresoDescuentoPosgradoForm()
                    form.ingresar(periodo)
                    data['form'] = form
                    return render(request, "alu_descuentoposgrado/add.html", data)
                except Exception as ex:
                    pass

            if action == 'delete':
                try:
                    data['title'] = u'Eliminar solicitud de descueto posgrado'
                    data['solicitud'] = DescuentoPosgradoMatricula.objects.get(pk=request.GET['id'])
                    return render(request, 'alu_descuentoposgrado/delete.html', data)
                except Exception as ex:
                    pass

            if action == 'adddoc':
                try:
                    hoy = datetime.now().date()
                    data['title'] = u'Requisitos de Solicitud Descuento'
                    data['aspirante'] = persona
                    data['inscripcioncohorte'] = inscripcioncohorte = DescuentoPosgradoMatricula.objects.get(pk=int(request.GET['id']))
                    tienerequisitos = False
                    if inscripcioncohorte.evidenciasdescuentoposgradomatricula_set.filter(status=True).exists():
                        tienerequisitos = True
                    data['tienerequisitos'] = tienerequisitos
                    permisorequisito = False
                    if inscripcioncohorte.detalleconfiguraciondescuentoposgrado.configuraciondescuentoposgrado.fechafin >= hoy:
                        permisorequisito = True
                    data['permisorequisito'] = permisorequisito
                    # if InscripcionCohorte.objects.filter(grupo__isnull=True):
                    if DescuentoPosgradoMatricula.objects.filter(pk=int(request.GET['id'])):
                        data['requisitos'] = RequisitosDetalleConfiguracionDescuentoPosgrado.objects.filter(detalleconfiguraciondescuentoposgrado=inscripcioncohorte.detalleconfiguraciondescuentoposgrado, status=True).order_by("id").distinct()
                    return render(request, "alu_descuentoposgrado/adddoc.html", data)
                except Exception as ex:
                    pass

            elif action == 'deldoc':
                try:
                    data['title'] = u"Eliminar evidencia Descuento"
                    revision = EvidenciasDescuentoPosgradoMatricula.objects.get(pk=request.GET['id'])
                    data['mensaje'] = u"¿Está seguro que desea eliminar los archivos de la Evidencia del Descuento?"
                    data['revision'] = revision
                    return render(request, "alu_descuentoposgrado/deletedoc.html", data)
                except Exception as ex:
                    pass

            if action == 'cargararchivo':
                try:
                    data['title'] = u'Evidencias de requisitos de Solicitud Descuento'
                    data['id'] = request.GET['id']
                    data['idevidencia'] = request.GET['idevidencia']
                    requisito = RequisitosDetalleConfiguracionDescuentoPosgrado.objects.get(pk=int(request.GET['idevidencia']), status=True)
                    form = RequisitosMaestriaForm()
                    data['form'] = form
                    template = get_template("alu_descuentoposgrado/add_requisitomaestria.html")
                    json_content = template.render(data)
                    return JsonResponse({"result": "ok", 'data': json_content, "nombre": "SUBIR DOCUMENTO DE REQUISITO " + str(requisito.requisito)})
                except Exception as ex:
                    pass

            return HttpResponseRedirect(request.path)
        else:
            # propuesta
            data['title'] = u'Descuento Posgrado'
            data['idalu'] = inscripcion.id
            mensaje1 = ''
            puede = False
            puede2 = False
            data['requisitosdetalleconfiguraciondescuentoposgrados'] = None
            data['descuentoposgradomatricula'] = descuentoposgradomatricula = DescuentoPosgradoMatricula.objects.filter(status=True, matricula=matricula)
            if not inscripcion.inscripcionmalla_set.filter(status=True):
                return HttpResponseRedirect("/?info=Debe tener malla asociada para poder inscribirse.")
            mensaje1 = 'No existe configuración de su periodo para Descuento de Posgrado'
            hoy = datetime.now().date()
            if ConfiguracionDescuentoPosgrado.objects.filter(fechainicio__lte=hoy, fechafin__gte=hoy,detalleconfiguraciondescuentoposgrado__periododetalleconfiguraciondescuentoposgrado__periodo=periodo,  status=True).exists():
                data['configuracion'] = ConfiguracionDescuentoPosgrado.objects.filter(fechainicio__lte=hoy, fechafin__gte=hoy,detalleconfiguraciondescuentoposgrado__periododetalleconfiguraciondescuentoposgrado__periodo=periodo,  status=True)[0]
                puede = True
                mensaje1 = ''

            if puede:
                historial = descuentoposgradomatricula
                if historial:
                    data['requisitosdetalleconfiguraciondescuentoposgrados'] = RequisitosDetalleConfiguracionDescuentoPosgrado.objects.filter(detalleconfiguraciondescuentoposgrado=descuentoposgradomatricula[0].detalleconfiguraciondescuentoposgrado, status=True).distinct()
                    puede2 = False
                    estado = historial[0].estado
                    if estado == 1:
                        puede = False
                        mensaje1 = 'Su solicitud esta en revisión'
                    if estado == 2:
                        puede = False
                        mensaje1 = 'Su solicitud esta aprobada'
                    if estado == 3:
                        puede = True
                else:
                    puede = True
                    puede2 = True


            data['puede'] = puede
            data['puede2'] = puede2
            data['mensaje1'] = mensaje1
            # fin propuesta
            return render(request, "alu_descuentoposgrado/view.html", data)