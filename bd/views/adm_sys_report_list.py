from django.contrib.auth.decorators import login_required
from django.http import HttpResponseRedirect, JsonResponse
from django.shortcuts import render
from decorators import secure_module
from bd.forms import GestionPermisosForm, ReportesForm
from sga.commonviews import adduserdata
from django.db import connection, transaction
from django.template.loader import get_template
from sga.funciones import generar_nombre, log, puede_realizar_accion, puede_realizar_accion_is_superuser, logquery, convertir_fecha, resetear_clave, MiPaginador
from django.db.models.query_utils import Q
from bd.models import GestionPermisos
from django.forms import model_to_dict
from sga.templatetags.sga_extras import encrypt
from django.contrib.auth.models import Group, User, Permission
from sga.models import Modulo, Reporte, ParametroReporte, SubReporte, CategoriaReporte


@login_required(redirect_field_name='ret', login_url='/loginsga')
#@secure_module
@transaction.atomic()
def view(request):
    data = {}
    adduserdata(request, data)
    persona = request.session['persona']
    if request.method == 'POST':
        action = data['action'] = request.POST['action']
        if action == 'add':
            try:
                form = ReportesForm(request.POST, request.FILES)

                #Verificar si el formulario recibido es válido
                if form.is_valid():

                    #Inicialización de variables
                    interface = True if 'interface' in request.POST else False
                    activosga = True if 'activosga' in request.POST else False
                    formatopdf = True if 'formatopdf' in request.POST else False
                    formatoxls = True if 'formatoxls' in request.POST else False
                    formatocsv = True if 'formatocsv' in request.POST else False
                    formatoword = True if 'formatoword' in request.POST else False
                    certificado = True if 'certificado' in request.POST else False
                    activosagest = True if 'activosagest' in request.POST else False
                    activoposgrado = True if 'activoposgrado' in request.POST else False
                    enviarporcorreo = True if 'enviarporcorreo' in request.POST else False
                    ejecutarcomoproceso = True if 'ejecutarcomoproceso' in request.POST else False

                    #Generar nombre al archivo reporte
                    file = None
                    valid_ext = [".jrxml"]
                    if 'archivo' in request.FILES:
                        file = request.FILES['archivo']
                        if file:
                            if file.size > 20480000:
                                return JsonResponse({"result": "bad", "mensaje": u"Error, archivo es mayor a 20 Mb."})
                            else:
                                newfilesd = file._name
                                ext = newfilesd[newfilesd.rfind("."):]
                                if not ext in valid_ext:
                                    return JsonResponse(
                                        {"result": "bad", "mensaje": f"Error, Solo archivos con extensión .jrxml"})

                    #Añadir nuevo reporte
                    if not Reporte.objects.filter(nombre=form.cleaned_data['nombre'], status=True).exists():
                        anadirreporte = Reporte(nombre=form.cleaned_data['nombre'],
                                                descripcion=form.cleaned_data['descripcion'],
                                                detalle=form.cleaned_data['detalle'],
                                                archivo=file,
                                                categoria=form.cleaned_data['categoria'],
                                                interface=interface,
                                                formatoxls=formatoxls,
                                                formatocsv=formatocsv,
                                                formatoword=formatoword,
                                                formatopdf=formatopdf,
                                                certificado=certificado,
                                                vista=form.cleaned_data['vista'],
                                                html=form.cleaned_data['html'],
                                                sga=activosga,
                                                sagest=activosagest,
                                                posgrado=activoposgrado,
                                                version=form.cleaned_data['versionreporte'],
                                                es_background=ejecutarcomoproceso,
                                                enviar_email=enviarporcorreo)
                        anadirreporte.save(request)
                        anadirreporte.grupos.clear()
                        for grupo in form.cleaned_data['grupos']:
                            anadirreporte.grupos.add(int(grupo.id))
                        log(u'%s Adiciono nuevo reporte: %s' % (persona, anadirreporte), request, "add")

                        # Verificar si añadió parámetros para el reporte
                        contador = 0
                        for parametroreporte in request.POST.getlist('nombreparametro[]'):
                            statusparametros = True if request.POST.getlist('statusseleccionado[]')[contador] == '1' else False
                            # nombresparametros = request.POST.getlist('nombreparametro[]')[contador]
                            descripcionparametros = request.POST.getlist('descripcionparametro[]')[contador]
                            tipoparametro = request.POST.getlist('tipoparametro[]')[contador]
                            claserelacionada = request.POST.getlist('claserelacionada[]')[contador]
                            filtroclaserelacionada = request.POST.getlist('filtroclaserelacionada[]')[contador]
                            registrarparametro = ParametroReporte(reporte_id=anadirreporte.id,
                                                                  nombre=parametroreporte,
                                                                  descripcion=descripcionparametros,
                                                                  tipo=tipoparametro,
                                                                  extra=claserelacionada,
                                                                  filtro=filtroclaserelacionada,
                                                                  status=statusparametros)
                            registrarparametro.save(request)
                            log(u'%s Adiciono nuevo parametro: %s' % (persona, registrarparametro), request, "add")
                            contador += 1

                        #Verificar si el nuevo reporte tendrá subreportes
                        if 'archivosubreporte' in request.FILES:
                            contador = 0
                            for parametroreporte in request.FILES.getlist('archivosubreporte'):
                                statussubreporte = True if request.POST.getlist('statusadicionarreporte[]')[contador] == '1' else False
                                # archivosubreporte = request.FILES.getlist('archivosubreporte')[contador]
                                file = None
                                valid_ext = [".jrxml"]
                                file = parametroreporte
                                if file:
                                    if file.size > 20480000:
                                        return JsonResponse(
                                            {"result": "bad", "mensaje": u"Error, archivo es mayor a 20 Mb."})
                                    else:
                                        newfilesd = file._name
                                        ext = newfilesd[newfilesd.rfind("."):]
                                        if not ext in valid_ext:
                                            return JsonResponse(
                                                {"result": "bad",
                                                 "mensaje": f"Error, Solo archivos con extensión .jrxml"})
                                registrarsubreporte = SubReporte(reporte_id=anadirreporte.id,
                                                                 subreport=file,
                                                                 status=statussubreporte)
                                registrarsubreporte.save(request)
                                log(u'Adiciono nuevo subreporte: %s' % (registrarsubreporte), request, "add")
                    else:
                        return JsonResponse({'error': True, "message": "Reporte existente"})
                else:
                    print([{k: v[0]} for k, v in form.errors.items()])
                    return JsonResponse({'error': "bad", "mensaje": u"Por favor, complete correctamente el formulario" + "\n" + list(form.errors.items())[0][1][0]})

                return JsonResponse({"result": 'ok'}, safe=False)
            except Exception as ex:
                transaction.rollback()
                pass

        elif action == 'edit':
            try:
                form = ReportesForm(request.POST, request.FILES)

                # Verificar si el formulario recibido es válido
                if form.is_valid():

                    # Inicialización de variables
                    interface = True if 'interface' in request.POST else False
                    activosga = True if 'activosga' in request.POST else False
                    formatopdf = True if 'formatopdf' in request.POST else False
                    formatoxls = True if 'formatoxls' in request.POST else False
                    formatocsv = True if 'formatocsv' in request.POST else False
                    formatoword = True if 'formatoword' in request.POST else False
                    certificado = True if 'certificado' in request.POST else False
                    activosagest = True if 'activosagest' in request.POST else False
                    activoposgrado = True if 'activoposgrado' in request.POST else False
                    enviarporcorreo = True if 'enviarporcorreo' in request.POST else False
                    ejecutarcomoproceso = True if 'ejecutarcomoproceso' in request.POST else False

                    # Generar nombre al archivo reporte
                    file = request.POST['archivoreporte']
                    valid_ext = [".jrxml"]
                    if file == '1':
                        file = request.FILES['archivo']
                        if file:
                            if file.size > 20480000:
                                return JsonResponse({"result": "bad", "mensaje": u"Error, archivo es mayor a 20 Mb."})
                            else:
                                newfilesd = file._name
                                ext = newfilesd[newfilesd.rfind("."):]
                                if not ext in valid_ext:
                                    return JsonResponse(
                                        {"result": "bad", "mensaje": f"Error, Solo archivos con extensión .jrxml"})

                    #Consulta para verificar nombre único del reporte
                    editreporte = Reporte.objects.get(id=int(request.POST['id_reporte']))
                    verificarnombre = Reporte.objects.filter(nombre=form.cleaned_data['nombre'], status=True)

                    #Verificar si el nombre del reporte no es igual al nombre ingresado
                    if not editreporte.nombre == form.cleaned_data['nombre']:
                        # Verificar si existe un reporte con el nombre ingresado
                        if verificarnombre:
                            return JsonResponse({'error': True, "message": "Reporte con nombre ingresado existente"})

                    # Editar reporte
                    editreporte.nombre = form.cleaned_data['nombre']
                    editreporte.descripcion = form.cleaned_data['descripcion']
                    editreporte.detalle = form.cleaned_data['detalle']
                    editreporte.archivo = file
                    editreporte.categoria = form.cleaned_data['categoria']
                    editreporte.interface = interface
                    editreporte.formatoxls = formatoxls
                    editreporte.formatocsv = formatocsv
                    editreporte.formatoword = formatoword
                    editreporte.formatopdf = formatopdf
                    editreporte.certificado = certificado
                    editreporte.vista = form.cleaned_data['vista']
                    editreporte.html = form.cleaned_data['html']
                    editreporte.sga = activosga
                    editreporte.sagest = activosagest
                    editreporte.posgrado = activoposgrado
                    editreporte.version = form.cleaned_data['versionreporte']
                    editreporte.es_background = ejecutarcomoproceso
                    editreporte.enviar_email = enviarporcorreo
                    editreporte.save(request)
                    editreporte.grupos.clear()
                    for grupo in form.cleaned_data['grupos']:
                        editreporte.grupos.add(int(grupo.id))
                    log(u'%s Editó reporte: %s' % (persona, editreporte), request, "act")

                    # Verificar si añadió parámetros para el reporte
                    contador = 0

                    #Consulta para comparar parámetros guardados del reporte con los parámetros recibidos
                    eliminarparametroreporte = ParametroReporte.objects.filter(reporte_id=editreporte.id)

                    #Extraer lista id de los parámetros
                    extraerparametros = list(request.POST.getlist('idstatusseleccionado[]'))
                    longitudlista = extraerparametros.__len__()

                    #Si se añade un nuevo parámetro tendrá por defecto id 'nuevoparametro'
                    #Condición para verificar si se añadió un nuevo parámetro y lo extrae de la lista
                    if 'nuevoparametro' in extraerparametros:
                        #Remueve id 'nuevoparametro' para convertir lista a int
                        for removerparametro in list(extraerparametros):
                            if removerparametro == 'nuevoparametro':
                                extraerparametros.remove('nuevoparametro')

                    #Lista id de los parámetros que ya estaban vinculados al reporte actual
                    parametrosextraidos_entero = list(map(int,extraerparametros))

                    #Verifica si un parámetro del reporte ha sido removido
                    for parametroreport in eliminarparametroreporte:
                        #Si el id del parámetro no se encuentra en la lista significa que ha sido removido
                        if not parametroreport.id in parametrosextraidos_entero:
                            eliminarparametro = ParametroReporte.objects.get(id=int(parametroreport.id))
                            log(u'%s Elimina parametro: %s' % (persona, eliminarparametro), request, "del")
                            eliminarparametro.delete()
                            # eliminarparametro.save(request)

                    #Si la dimensión de la lista id de parámetros es 0 significa que no hay parámetros para editar o ingresar
                    if longitudlista > 0:
                        for idparametroreporte in request.POST.getlist('idstatusseleccionado[]'):
                            #Inicializo variables con los datos recibidos
                            statusparametro = True if request.POST.getlist('statusseleccionado[]')[contador] == '1' else False
                            nombreparametro = request.POST.getlist('nombreparametro[]')[contador]
                            descripcionparametros = request.POST.getlist('descripcionparametro[]')[contador]
                            tipoparametro = request.POST.getlist('tipoparametro[]')[contador]
                            claserelacionada = request.POST.getlist('claserelacionada[]')[contador]
                            filtroclaserelacionada = request.POST.getlist('filtroclaserelacionada[]')[contador]
                            #Consulta para verificar si el parámetro no es un nuevo parámetro
                            if not idparametroreporte == 'nuevoparametro':
                                #Consulta para verificar si el parámetro recibido no ha sido eliminado
                                editarparametro = ParametroReporte.objects.filter(id=idparametroreporte)
                                if editarparametro:
                                    editarparametro[0].nombre = nombreparametro
                                    editarparametro[0].descripcion = descripcionparametros
                                    editarparametro[0].tipo = tipoparametro
                                    editarparametro[0].extra = claserelacionada
                                    editarparametro[0].filtro = filtroclaserelacionada
                                    editarparametro[0].status = statusparametro
                                    editarparametro[0].save(request)
                                    log(u'%s Editó parametro: %s' % (persona, editarparametro[0]), request, "act")
                            else:
                                #Consultar si no existe un parámetro con el mismo nombre correspondiente al reporte seleccionado
                                if not ParametroReporte.objects.filter(nombre=nombreparametro, reporte_id=editreporte.id).exists():
                                    registrarparametro = ParametroReporte(reporte_id=editreporte.id,
                                                                          nombre=nombreparametro,
                                                                          descripcion=descripcionparametros,
                                                                          tipo=tipoparametro,
                                                                          extra=claserelacionada,
                                                                          filtro=filtroclaserelacionada,
                                                                          status=statusparametro)
                                    registrarparametro.save()
                                    log(u'%s Adicionó nuevo parametro: %s' % (persona, registrarparametro), request,"add")
                                else:
                                    return JsonResponse({'error': True, "mensaje": "Reporte existente"})
                            contador += 1

                    eliminarsubreporte = SubReporte.objects.filter(reporte_id=editreporte.id)

                    # Extraer lista id de los subreportes
                    extraersubreportes = request.POST.getlist('idstatusseleccionadosubreporte[]')
                    longitudlista = extraersubreportes.__len__()

                    # Si se añade un nuevo parámetro tendrá por defecto id 'nuevoparametro'
                    # Condición para verificar si se añadió un nuevo subreporte y lo extrae de la lista
                    if 'nuevoparametro' in extraersubreportes:
                        # Remueve id 'nuevoparametro' para convertir lista a int
                        for removernuevo in list(extraersubreportes):
                            if removernuevo == 'nuevoparametro':
                                extraersubreportes.remove('nuevoparametro')

                    # Lista id de los subreportes que ya estaban vinculados al reporte actual
                    subreportesextraidos_entero = list(map(int, extraersubreportes))

                    # Verifica si un subreporte del reporte ha sido removido
                    for eliminasubreporte in eliminarsubreporte:
                        # Si el id del subreporte no se encuentra en la lista significa que ha sido removido
                        if not eliminasubreporte.id in subreportesextraidos_entero:
                            subreporteeliminado = SubReporte.objects.get(id=int(eliminasubreporte.id))
                            log(u'%s Elimina subreporte: %s' % (persona, subreporteeliminado), request, "del")
                            subreporteeliminado.delete()
                    contador = 0
                    contadorsubreporteactualizado = 0
                    contadorsubreportenuevo = 0
                    if longitudlista > 0:
                        for idsubreport in request.POST.getlist('idstatusseleccionadosubreporte[]'):

                            #Inicializo variables con los datos recibidos
                            file = None
                            statussubreporte = True if request.POST.getlist('statusseleccionadosubreporte[]')[contador] == '1' else False
                            if not idsubreport == 'nuevoparametro':
                                file = request.POST.getlist('act_archivosubreporte[]')[contador]
                                if file == '1':
                                    archivosubreporte = request.FILES.getlist('archivosubreporte[]')[contadorsubreporteactualizado]
                                    valid_ext = [".jrxml",".jasper"]
                                    file = archivosubreporte
                                    if file:
                                        if file.size > 20480000:
                                            return JsonResponse(
                                                {"result": "bad", "mensaje": u"Error, archivo es mayor a 20 Mb."})
                                        else:
                                            newfilesd = file._name
                                            ext = newfilesd[newfilesd.rfind("."):]
                                            if not ext in valid_ext:
                                                return JsonResponse(
                                                    {"result": "bad",
                                                     "mensaje": f"Error, Solo archivos con extensión .jrxml o.jasper"})
                                    contadorsubreporteactualizado += 1

                            #Consulta para verificar si el subreporte no es un nuevo parámetro
                            if not idsubreport == 'nuevoparametro':
                                #Consulta para verificar si el parámetro recibido no ha sido eliminado
                                editarsubreporte = SubReporte.objects.filter(id=idsubreport)
                                if editarsubreporte:
                                    editarsubreporte[0].subreport = file
                                    editarsubreporte[0].status = statussubreporte
                                    editarsubreporte[0].save()
                                    log(u'%s Editó subreporte: %s' % (persona, editarsubreporte[0]), request, "act")
                            else:
                                nuevoarchivosubreporte = request.FILES.getlist('nuevoarchivosubreporte[]')[contadorsubreportenuevo]
                                valid_ext = [".jrxml", ".jasper"]
                                file = nuevoarchivosubreporte
                                if file:
                                    if file.size > 20480000:
                                        return JsonResponse(
                                            {"result": "bad", "mensaje": u"Error, archivo es mayor a 20 Mb."})
                                    else:
                                        newfilesd = file._name
                                        ext = newfilesd[newfilesd.rfind("."):]
                                        if not ext in valid_ext:
                                            return JsonResponse(
                                                {"result": "bad",
                                                 "mensaje": f"Error, Solo archivos con extensión .jrxml o.jasper"})
                                registrarsubreporte = SubReporte(reporte_id=editreporte.id,
                                                                 status=statussubreporte,
                                                                 subreport=file)
                                registrarsubreporte.save()
                                log(u'%s Adicionó nuevo subreporte: %s' % (persona, registrarsubreporte), request,"add")
                                contadorsubreportenuevo += 1
                            contador += 1
                else:
                    print([{k: v[0]} for k, v in form.errors.items()])
                    return JsonResponse({'error': True, "form": [{k: v[0]} for k, v in form.errors.items()],
                                         "message": "Error en el formulario"})

                return JsonResponse({"result": 'ok'}, safe=False)
            except Exception as ex:
                transaction.rollback()
                pass

        if action == 'delete':
            try:
                with transaction.atomic():
                    instancia = Reporte.objects.get(pk=int(request.POST['id']))
                    instancia.status = False
                    instancia.save(request)
                    log(u'Eliminó reporte: %s' % instancia, request, "del")
                    return JsonResponse({"result": 'ok',"mensaje":'El reporte ha sido eliminado!'}, safe=False)
            except Exception as ex:
                transaction.rollback()
                res_json = {'error': True, "message": "Error: {}".format(ex)}
            # return JsonResponse(res_json, safe=False)


        HttpResponseRedirect("/niveles?info=Solicitud incorrecta.")
    else:
        if 'action' in request.GET:
            action = data['action'] = request.GET['action']

            if action == 'buscarpermiso':
                try:
                    q = request.GET['q'].upper().strip()
                    per = Permission.objects.filter((Q(name__icontains=q) | Q(codename__icontains=q) | Q(content_type__app_label__icontains=q))).distinct().order_by('id')[:15]
                    data = {"result": "ok", "results": [{"id": x.id, "name": "{} | {} ({})".format(x.content_type, x.name, x.codename)} for x in per]}
                    return JsonResponse(data)
                except Exception as ex:
                    pass

            if action == 'buscarmodulo':
                try:
                    q = request.GET['q'].upper().strip()
                    modulo = Modulo.objects.filter((Q(nombre__icontains=q) | Q(url__icontains=q) | Q(descripcion__icontains=q))).distinct().order_by('id')[:15]
                    data = {"result": "ok", "results": [{"id": x.id, "name": "{} ({})".format(x.nombre, x.url)} for x in modulo]}
                    return JsonResponse(data)
                except Exception as ex:
                    pass

            if action == 'add':
                try:
                    form = ReportesForm()
                    form.archivorequerido()
                    data['title'] = u"Adicionar reporte"
                    data['form'] = form
                    return render(request, "adm_sistemas/report_list/crud/add.html", data)
                except Exception as ex:
                    pass

            if action == 'edit':
                try:
                    data['title'] = u"Editar reporte"
                    data['reporteform'] = consultareporte = Reporte.objects.get(id=int(request.GET['id']))
                    form = ReportesForm(initial={'nombre':consultareporte.nombre,
                                                 'descripcion':consultareporte.descripcion,
                                                 'detalle':consultareporte.detalle,
                                                 'archivo':consultareporte.archivo,
                                                 'categoria':CategoriaReporte.objects.filter(status=True),
                                                 'grupos':Group.objects.all(),
                                                 'interface':consultareporte.interface,
                                                 'formatoxls':consultareporte.formatoxls,
                                                 'formatocsv':consultareporte.formatocsv,
                                                 'formatoword':consultareporte.formatoword,
                                                 'formatopdf':consultareporte.formatopdf,
                                                 'certificado':consultareporte.certificado,
                                                 'vista':consultareporte.vista,
                                                 'html':consultareporte.html,
                                                 'activosga':consultareporte.sga,
                                                 'activosagest':consultareporte.sagest,
                                                 'activoposgrado':consultareporte.posgrado,
                                                 'versionreporte':consultareporte.version,
                                                 'ejecutarcomoproceso':consultareporte.es_background,
                                                 'enviarporcorreo':consultareporte.enviar_email})
                    form.renombrar()
                    data['categoriareporte'] = consultareporte.categoria_id
                    data['gruposreporte'] = list(Reporte.objects.filter(id=consultareporte.id, status=True).values_list('grupos', flat=True))
                    data['subreportes'] = parametrosreporte = SubReporte.objects.filter(reporte_id=int(request.GET['id']))
                    data['parametrosreporte'] = parametrosreporte = ParametroReporte.objects.filter(reporte_id=int(request.GET['id']))
                    data['action'] = 'edit'
                    data['form'] = form
                    return render(request, "adm_sistemas/report_list/crud/edit.html", data)
                except Exception as ex:
                    pass

            HttpResponseRedirect("/adm_sistemas?info=Solicitud incorrecta.")
        else:
            try:
                data['title'] = 'Reportes'
                filtros, s, m, url_vars = Q(status=True), request.GET.get('s', ''), request.GET.get('m', '0'), ''
                data['len'] = len = 50 #Number of items pr page

                if s:
                    if s.isdigit():
                        filtros = filtros & (Q(id=s))
                    else:
                        filtros = filtros & (Q(nombre__icontains=s) | Q(descripcion__icontains=s))
                    data['s'] = f"{s}"
                    url_vars += f"&s={s}"

                if int(m):
                    filtros = filtros & (Q(modulo_id=m))
                    data['m'] = f"{m}"
                    url_vars += f"&s={m}"

                paging = MiPaginador(Reporte.objects.filter(filtros).order_by('nombre'), len)
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
                data['listadoreportes'] = page.object_list
                data['url_vars'] = url_vars
                data['modulos'] = GestionPermisos.objects.values_list('modulo_id', 'modulo__nombre', 'modulo__url').filter(status=True).distinct()
                return render(request, "adm_sistemas/report_list/view.html", data)

            except Exception as ex:
                return JsonResponse({"result": "bad", "mensaje": u"Error al obtener los datos. %s" % ex.__str__()})