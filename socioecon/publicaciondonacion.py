import random
import sys
import calendar
import datetime
import openpyxl
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db import transaction
import xlwt
from django.forms import model_to_dict
from django.http import HttpResponseRedirect, JsonResponse
from django.template.loader import get_template
from django.shortcuts import render, redirect
from decorators import secure_module, last_access
from settings import EMAIL_DOMAIN
from sga.commonviews import adduserdata
from socioecon.models import TipoDonacion, PublicacionDonacion, ContribuidorDonacion, DetalleContribuidorDonacion, DetalleAprobacionPublicacionDonacion, DetalleProductoPublicacion, UnidadMedidaDonacion, Producto, PUBLICACION_DONACION_ESTADO
from django.db.models import Sum, Q, F, FloatField
from socioecon.forms import PublicacionDonacionForm, ProductoForm, ContribuidorDonacionForm, DetalleProductoPublicacionForm
from sga.funciones import log, generar_nombre, MiPaginador, dia_semana_enletras_fecha, null_to_numeric, notificacion
from sga.tasks import send_html_mail
from sga.models import CUENTAS_CORREOS, Persona
from sga.templatetags.sga_extras import encrypt

#@login_required(redirect_field_name='ret', login_url='/loginsga')
@last_access
#@secure_module
@transaction.atomic()
def view(request):
    data = {}

    if 'persona' in request.session and 'tiposistema' in request.session:
        adduserdata(request, data)

    hoy = datetime.datetime.now().date()
    usuario = request.user if request.user else ''
    persona = request.session['persona'] if 'persona' in request.session else ''
    periodo = request.session['periodo'] if 'periodo' in request.session else ''
    perfilprincipal = request.session['perfilprincipal'] if 'perfilprincipal' in request.session else ''
    data['currenttime'] = currenttime = datetime.datetime.now()
    data['persona'] = persona
    data['url_'] = request.path

    # if not persona.es_estudiante() or persona.es_inscripcionaspirante():
    #     return HttpResponseRedirect("/?info=Usted no pertenece al grupo de estudiantes.")

    if request.method == 'POST':
        data = {}
        action = data['action'] = request.POST['action']
        if action == 'addpublicacion':
            try:
                form = PublicacionDonacionForm(request.POST, request.FILES)
                form.es_agregar()
                file = newfile = None
                valid_ext = ['.pdf', '.PDF', ".jpg", ".JPG", ".jpeg", ".JPEG", ".png", ".PNG"]
                if 'evidencianecesidad' in request.FILES:
                    file = request.FILES['evidencianecesidad']
                    if file:
                        if file.size > 4194304:
                            return JsonResponse({"result": "bad", "mensaje": u"Error, archivo es mayor a 4 Mb."})
                        else:
                            newfilesd = file._name
                            ext = newfilesd[newfilesd.rfind("."):]

                            if ext in valid_ext:
                                file._name = generar_nombre("evidencianecesidad", file._name)
                            else:
                                return JsonResponse(
                                    {"result": "bad", "mensaje": u"Error, Solo archivos con extención {}".format(
                                        ['.pdf', '.PDF', ".jpg", ".JPG", ".jpeg", ".JPEG", ".png", ".PNG"])})

                if 'evidenciaejecucion' in request.FILES:
                    newfile = request.FILES['evidenciaejecucion']
                    if newfile:
                        if newfile.size > 4194304:
                            return JsonResponse({"result": "bad", "mensaje": u"Error, archivo es mayor a 4 Mb."})
                        else:
                            newfilesd = newfile._name
                            ext = newfilesd[newfilesd.rfind("."):]

                            if ext in valid_ext:
                                newfile._name = generar_nombre("evidenciaejecucion", newfile._name)
                            else:
                                return JsonResponse(
                                    {"result": "bad", "mensaje": u"Error, Solo archivos con extención {}".format(['.pdf', '.PDF', ".jpg", ".JPG", ".jpeg", ".JPEG", ".png", ".PNG"])})

                if form.is_valid():
                    publicaciondonacion = PublicacionDonacion(persona=persona,
                                                              nombre=form.cleaned_data['nombre'],
                                                              objetivo=form.cleaned_data['objetivo'],
                                                              tipodonacion=form.cleaned_data['tipodonacion'],
                                                              fechainiciorecepcion=form.cleaned_data['fechainiciorecepcion'],
                                                              fechafinrecepcion=form.cleaned_data['fechafinrecepcion'],
                                                              fechainicioentrega=form.cleaned_data['fechainicioentrega'],
                                                              fechafinentrega=form.cleaned_data['fechafinentrega'],
                                                              mostrarfotoperfil=form.cleaned_data['mostrarfotoperfil'])
                    if file:
                        publicaciondonacion.evidencianecesidad = file

                    if newfile:
                        publicaciondonacion.evidenciaejecucion = newfile

                    publicaciondonacion.save(request)
                    publicaciondonacion.poblacion.clear()
                    for pb in form.cleaned_data['poblacion']:
                        publicaciondonacion.poblacion.add(pb)

                    for ca in request.POST.getlist('detalleproducto')[0].split(','):
                        if ca:
                            producto, cantidad, unidadmedida = ca.split(';')[0], ca.split(';')[1], ca.split(';')[2]
                            if not DetalleProductoPublicacion.objects.values('id').filter(publicaciondonacion_id=publicaciondonacion.id, producto_id=producto, unidadmedida_id=unidadmedida, status=True).exists():
                                p = DetalleProductoPublicacion(publicaciondonacion=publicaciondonacion, producto_id=producto, cantidad=cantidad, unidadmedida_id=unidadmedida)
                                p.save()
                            else:
                                p = DetalleProductoPublicacion.objects.filter(publicaciondonacion=publicaciondonacion, producto_id=producto, unidadmedida_id=unidadmedida, status=True).first()
                                p.cantidad, p.unidadmedida = cantidad, unidadmedida
                                p.save()
                    log(u'Adiciono nueva solicitud de donación: %s' % publicaciondonacion, request, "add")
                    # NOTIFICAR VIA EMAIL LA CREACIÓN DE LA SOLICITUD
                    # data['solicitud'] = solicitud
                    # asunto = u"SOLICITUD DE DONACIÓN "
                    # send_html_mail(asunto, "emails/notificacioncreaciondonacion.html",
                    #                {'sistema': request.session['nombresistema'], 'solicitud': solicitud, 'pk':publicaciondonacion.pk},
                    #                 ['jcuadradoh2@unemi.edu.ec'], [], cuenta=CUENTAS_CORREOS[16][1])
                    solicitud = PublicacionDonacion.objects.filter(pk=publicaciondonacion.id).annotate(ffinsolicitud=(F('fechafinentrega') - F('fechainiciorecepcion')),ffinentrega=(F('fechafinentrega') - hoy))[0]
                    mensaje = f"Ponemos a vuestro conocimiento que la persona { solicitud.persona } ha realizado una solicitud de donación de tipo <b>{ solicitud.tipodonacion }</b>, determinamos proceda con la revisión de la misma."
                    for r in Persona.objects.filter(emailinst__in=solicitud.lista_responsables()):
                        notificacion(u'Solicitud de Donación', mensaje, r, 0, f'/adm_publicaciondonacion?pk={encrypt(solicitud.pk)}', solicitud.pk, 1, 'sga', solicitud, request)

                    return JsonResponse({"result": 'ok'}, safe=False)
                else:
                    return JsonResponse({"result": "bad", "mensaje": u"Error al validar los datos."})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        if action == 'editpublicacion':
            try:
                form = PublicacionDonacionForm(request.POST, request.FILES)
                pd = PublicacionDonacion.objects.get(pk=int(encrypt(request.POST['id'])))

                file = newfile = None
                valid_ext = ['.pdf', '.PDF', ".jpg", ".JPG", ".jpeg", ".JPEG", ".png", ".PNG"]
                if 'evidencianecesidad' in request.FILES:
                    file = request.FILES['evidencianecesidad']
                    if file:
                        if file.size > 4194304:
                            return JsonResponse({"result": "bad", "mensaje": u"Error, archivo es mayor a 4 Mb."})
                        else:
                            newfilesd = file._name
                            ext = newfilesd[newfilesd.rfind("."):]

                            if ext in valid_ext:
                                file._name = generar_nombre("evidencianecesidad", file._name)
                            else:
                                return JsonResponse(
                                    {"result": "bad", "mensaje": u"Error, Solo archivos con extención {}".format(
                                        ['.pdf', '.PDF', ".jpg", ".JPG", ".jpeg", ".JPEG", ".png", ".PNG"])})

                if 'evidenciaejecucion' in request.FILES:
                    newfile = request.FILES['evidenciaejecucion']
                    if newfile:
                        if newfile.size > 4194304:
                            return JsonResponse({"result": "bad", "mensaje": u"Error, archivo es mayor a 4 Mb."})
                        else:
                            newfilesd = newfile._name
                            ext = newfilesd[newfilesd.rfind("."):]

                            if ext in valid_ext:
                                newfile._name = generar_nombre("evidenciaejecucion", newfile._name)
                            else:
                                return JsonResponse(
                                    {"result": "bad", "mensaje": u"Error, Solo archivos con extención {}".format(['.pdf', '.PDF', ".jpg", ".JPG", ".jpeg", ".JPEG", ".png", ".PNG"])})

                if pd.estado == 2:
                    form.editar_aprobado()
                else:
                    form.es_agregar()

                if form.is_valid():
                    pd.nombre = form.cleaned_data['nombre']
                    pd.objetivo = form.cleaned_data['objetivo']
                    pd.tipodonacion = form.cleaned_data['tipodonacion']
                    pd.fechainiciorecepcion = form.cleaned_data['fechainiciorecepcion']
                    pd.fechafinrecepcion = form.cleaned_data['fechafinrecepcion']
                    pd.fechainicioentrega = form.cleaned_data['fechainicioentrega']
                    pd.fechafinentrega = form.cleaned_data['fechafinentrega']
                    pd.mostrarfotoperfil = form.cleaned_data['mostrarfotoperfil']

                    if file:
                        pd.evidencianecesidad = file

                    if newfile:
                        pd.evidenciaejecucion = newfile

                    pd.save(request)
                    pd.poblacion.clear()
                    for pb in form.cleaned_data['poblacion']:
                        pd.poblacion.add(pb)

                    for ca in request.POST.getlist('detalleproducto')[0].split(','):
                        producto, cantidad, unidadmedida = ca.split(';')[0], ca.split(';')[1], ca.split(';')[2]
                        if not DetalleProductoPublicacion.objects.values('id').filter(publicaciondonacion_id=pd.id, producto_id=producto, unidadmedida_id=unidadmedida, status=True).exists():
                            p = DetalleProductoPublicacion(publicaciondonacion=pd, producto_id=producto, cantidad=cantidad, unidadmedida_id=unidadmedida)
                            p.save()
                        else:
                            p = DetalleProductoPublicacion.objects.filter(publicaciondonacion=pd, producto_id=producto, unidadmedida_id=unidadmedida, status=True).first()
                            p.cantidad, p.unidadmedida_id = cantidad, unidadmedida
                            p.save()


                    log(u'Editó solicitud de donación: %s' % pd, request, "edit")
                    return JsonResponse({"result": 'ok'}, safe=False)
                else:
                    return JsonResponse({"result": "bad", "mensaje": u"Error al validar los datos."})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        if action == 'deletepublicacion':
            try:
                soli = PublicacionDonacion.objects.get(pk=int(encrypt(request.POST['id'])))
                soli.status = False
                soli.save(request)
                log(u'Eliminó solicitud de donación: %s' % soli, request, "del")
                return JsonResponse({'error': False, "message": 'Registro eliminado correctamente.'}, safe=False)
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        if action == 'cargaradicionarproducto':
            try:
                data['form'] = ProductoForm()
                template = get_template('publicaciondonacion/modal/addproducto.html')
                json_content = template.render(data)
                return JsonResponse({"result": "ok", 'html': json_content})
            except Exception as ex:
                return JsonResponse({"result": "bad", "mensaje": u"Error al cargar los datos."})

        if action == 'addproducto':
            try:
                with transaction.atomic():
                    lista = []
                    if Producto.objects.filter(descripcion=request.POST['descripcion'].upper(), status=True).exists():
                        transaction.set_rollback(True)
                        return JsonResponse({'error': True, "message": 'Ya existe el tipo de producto.'}, safe=False)
                    form = ProductoForm(request.POST)
                    if form.is_valid():
                        instance = Producto(descripcion=form.cleaned_data['descripcion'],  tipoproducto_id=request.POST['tipoproducto'])
                        instance.save(request)
                        log(u'Adiciono producto: %s' % instance, request, "add")
                        lista.append([instance.id, instance.descripcion])
                        return JsonResponse({"result": 'ok', "lista":lista}, safe=False)
                    else:
                        return JsonResponse({'error': True, "form": [{k: v[0]} for k, v in form.errors.items()], "message": "Error en el formulario"})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": True, "message": "Intentelo más tarde."}, safe=False)

        if action == 'addcontribuidor':
            try:
                with transaction.atomic():
                    mensaje = person = ''
                    f = ContribuidorDonacionForm(request.POST)
                    if f.is_valid():
                        tipopersona = int(f.cleaned_data['tipodonante'])
                        if tipopersona == 1:
                            if not f.cleaned_data['cedula'] and not f.cleaned_data['pasaporte']:
                                return JsonResponse({"result": "bad", "mensaje": u"Debe especificar un numero de identificación."})

                            if not Persona.objects.filter(cedula=f.cleaned_data['cedula']).exists():
                                person = Persona(cedula=f.cleaned_data['cedula'],
                                                 pasaporte=f.cleaned_data['pasaporte'],
                                                 nombres=(u"%s %s" % (f.cleaned_data['nombre1'], f.cleaned_data['nombre2'])).upper(),
                                                 apellido1=f.cleaned_data['apellido1'].upper(),
                                                 apellido2=f.cleaned_data['apellido2'].upper(),
                                                 sexo=f.cleaned_data['sexo'] if f.cleaned_data['sexo'] else '')
                        elif tipopersona == 2:
                            if not f.cleaned_data['ruc']:
                                return JsonResponse({"result": "bad", "mensaje": u"Debe especificar un numero de identificación."})

                            if not Persona.objects.filter(ruc=f.cleaned_data['ruc']).exists():
                                person = Persona(ruc=f.cleaned_data['ruc'], nombres=f.cleaned_data['razonsocial'].upper())
                        if person:
                            person.save(request)
                        else:
                            person = Persona.objects.get(cedula=f.cleaned_data['cedula']) if tipopersona == 1 else Persona.objects.get(ruc=f.cleaned_data['ruc'])

                        if not ContribuidorDonacion.objects.filter(persona=person):
                            contribuidor = ContribuidorDonacion(persona=person, es_anonimo=f.cleaned_data['esanonimo'])
                            contribuidor.save(request)

                        request.session['persona'] = persona = person
                        request.user = person.usuario
                        return JsonResponse({"result": 'ok'}, safe=False)
                    else:
                        return JsonResponse({'error': True, "form": [{k: v[0]} for k, v in f.errors.items()], "message": "Error en el formulario"})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": True, "mensaje": "Intentelo más tarde."}, safe=False)

        if action == 'adddonacion':
            try:
                with transaction.atomic():
                    if request.session['persona']:
                        if not request.POST['cantidad']:
                            return JsonResponse({"result": False, "mensaje": "Ingrese la cantidad"})
                        cantidad = int(request.POST['cantidad'])
                        if ContribuidorDonacion.objects.values('id').filter(persona=persona, status=True).exists():
                            ctr = ContribuidorDonacion.objects.filter(persona=persona, status=True).first()
                            dpp = DetalleProductoPublicacion.objects.get(pk=int(encrypt(request.POST['iddp'])))
                            if DetalleContribuidorDonacion.objects.values('id').filter(contribuidordonacion=ctr, detalleproductopublicacion=dpp, status=True).exists():
                                dcd = DetalleContribuidorDonacion.objects.filter(contribuidordonacion=ctr, detalleproductopublicacion=dpp, status=True).order_by('-id').first()
                                dcd.cantidad = cantidad
                            else:
                                dcd = DetalleContribuidorDonacion(contribuidordonacion=ctr, detalleproductopublicacion=dpp, cantidad=cantidad)
                            dcd.save(request)
                            return JsonResponse({"result": 'ok', "porcentaje_actual": "%.2f" % dpp.get_porcentaje()}, safe=False)
            except Exception as ex:
                transaction.set_rollback(True)
                pass

        if action == 'loaddataproducto':
            try:
                publicacion = PublicacionDonacion.objects.filter(pk=int(encrypt(request.POST['id']))).first()
                productos = []
                contribuidores = []
                listacontribuidores = []
                contador = total_productos = total_recaudado = total_recaudado_por = total_por_confirmar = total_por_confirmar_por = 0
                modeloproducto = publicacion.get_productos() if publicacion.get_productos() else ''
                if modeloproducto:
                    total_productos = int(modeloproducto[0].total_productos_solicitud()) if modeloproducto[0].total_productos_solicitud() else 0
                    total_recaudado = int(DetalleContribuidorDonacion.objects.filter(detalleproductopublicacion_id__in=modeloproducto.values_list('id', flat=True), status=True).aggregate(valor=Sum('cantidad'))['valor']) if DetalleContribuidorDonacion.objects.filter(detalleproductopublicacion_id__in=modeloproducto.values_list('id', flat=True), status=True) else 0
                    if total_productos:
                        total_recaudado_por = (total_recaudado/total_productos)*100
                        total_por_confirmar = total_productos - total_recaudado
                        total_por_confirmar_por = (total_por_confirmar/total_productos)*100
                for producto in publicacion.get_productos():
                    contador += 1
                    productos.append({
                        'contador':"%s" % contador,
                        'nombre': "%s" % producto.producto,
                        'cantidad': "%s" % producto.cantidad,
                        'cantidad_estimada': "%s" % producto.get_cantidadrecaudada(),
                        'porcentaje': "%.0f" % producto.get_porcentaje(),
                    })

                if DetalleContribuidorDonacion.objects.filter(detalleproductopublicacion_id__in=(publicacion.get_productos().values_list('id', flat=True))).exists():
                    listacontribuidores = DetalleContribuidorDonacion.objects.filter(detalleproductopublicacion_id__in=(publicacion.get_productos().values_list('id', flat=True))) #.aggregate(cantidadtotal=Sum('cantidad'))
                contador = 0
                if len(listacontribuidores):
                    for c in set(listacontribuidores.values_list('contribuidordonacion_id', flat=True)):
                        contribuidor = DetalleContribuidorDonacion.objects.filter(contribuidordonacion_id=c, detalleproductopublicacion__producto__status=True, detalleproductopublicacion_id__in=(publicacion.get_productos().values_list('id', flat=True)))
                        if contribuidor:
                            numero_productos = len(set(contribuidor.values_list('detalleproductopublicacion__producto', flat=True)))
                            cantidad = int(contribuidor.aggregate(cantidadtotal=Sum('cantidad'))['cantidadtotal']) if contribuidor.aggregate(cantidadtotal=Sum('cantidad')) else 0
                            if contribuidor.filter(contribuidordonacion__es_anonimo=False):
                                contribuidores.append({
                                    'contador': "%s" % contador,
                                    'perfil': "%s" % contribuidor[0].contribuidordonacion.persona.get_foto(),
                                    'nombre': "%s" % contribuidor[0],
                                    'numero_productos': "[%s]" % numero_productos,
                                    'cantidad': "%s" % cantidad,
                                    'porcentaje': "%.0f" % (((cantidad / total_productos) * 100) if ((cantidad / total_productos) * 100) < 100 else 100) if total_productos else 0,
                                    'anonimo': False
                                })
                            else:
                                contribuidores.append({
                                    'contador': "%s" % contador,
                                    'numero_productos': "[%s]" % numero_productos,
                                    'cantidad': "%s" % cantidad,
                                    'porcentaje': "%.0f" % (((cantidad / total_productos) * 100) if ((cantidad / total_productos) * 100) < 100 else 100) if total_productos else 0,
                                    'anonimo': True
                                })
                return JsonResponse({"result": 'ok', "contribuidores": contribuidores, "productos":productos, 'total_productos':total_productos,
                                     "total_recaudado":total_recaudado, "total_recaudado_por": "%.0f" % total_recaudado_por, "total_por_confirmar":total_por_confirmar if total_por_confirmar > 0 else 0,
                                     "total_por_confirmar_por": "%.0f" % total_por_confirmar_por if total_por_confirmar_por > 0 else 0 }, safe=False)
            except Exception as ex:
                transaction.set_rollback(True)
                pass

        if action == 'editdonacion':
            try:
                # dpp = DetalleProductoPublicacion.objects.get(pk=int(encrypt(request.POST['iddp'])))
                # dpp.detallecontribuidordonacion_set.filter(contribuidordonacion__persona=persona, status=True).update(status=False)
                with transaction.atomic():
                    if request.session['persona']:
                        if not request.POST['cantidad']:
                            return JsonResponse({"result": False, "mensaje": "Ingrese la cantidad"})
                        cantidad = int(request.POST['cantidad'])
                        if ContribuidorDonacion.objects.values('id').filter(persona=persona, status=True).exists():
                            ctr = ContribuidorDonacion.objects.filter(persona=persona, status=True).first()
                            dpp = DetalleProductoPublicacion.objects.get(pk=int(encrypt(request.POST['iddp'])))
                            if DetalleContribuidorDonacion.objects.values('id').filter(contribuidordonacion=ctr, detalleproductopublicacion=dpp, status=True).exists():
                                dcd = DetalleContribuidorDonacion.objects.filter(contribuidordonacion=ctr, detalleproductopublicacion=dpp, status=True).order_by('-id').first()
                                dcd.cantidad = cantidad
                            else:
                                dcd = DetalleContribuidorDonacion(contribuidordonacion=ctr, detalleproductopublicacion=dpp, cantidad=cantidad)
                            dcd.save(request)
                            return JsonResponse({"result": 'ok', "porcentaje_actual": "%.2f" % dpp.get_porcentaje()}, safe=False)
            except Exception as ex:
                transaction.rollback()
                pass

        return HttpResponseRedirect('/publicaciondonacion')

    else:
        if 'action' in request.GET:
            action = data['action'] = request.GET['action']

            if action == 'email':
                data['solicitud'] = PublicacionDonacion.objects.filter(status=True).annotate(ffinsolicitud=(F('fechafinentrega') - F('fechainiciorecepcion')), ffinentrega=(F('fechafinentrega') - hoy))[2]
                data['pk'] = data['solicitud'].pk
                return render(request, "emails/notificacioncreaciondonacion.html", data)

            if action == 'addcontribuidor':
                try:
                    form = ContribuidorDonacionForm()
                    data['form'] = form
                    data['publicacionesexternas'] = PublicacionDonacion.objects.filter(estado=2, fechafinentrega__gte=hoy, status=True).annotate(PUBLICADO_HACE=(currenttime - F('fecha_creacion')), DIAS_FIN_RECEPCION=(F('fechafinrecepcion') - F('fechainiciorecepcion'))).order_by('estadoprioridad')
                    data['title'] = "Donaciones"
                    return render(request, "adm_publicaciondonacion/adddonacion.html", data)
                except Exception as ex:
                    pass

            #if action == 'adddonacion':
                # try:
                #     detallecontribuidordonacion = DetalleContribuidorDonacion.objects.filter(persona=persona,detalleproductopublicacion_id=int(encrypt(request.POST['iddp']))).order_by('-id').first()
                #     data['cantidaddonada'] = null_to_numeric(detallecontribuidordonacion.aggregate(cantidad=Sum('cantidad'))['cantidad'])
                    # data['solicitud'] = PublicacionDonacion.objects.filter(pk=int(encrypt(request.GET['id']))).annotate(PUBLICADO_HACE=(currenttime - F('fecha_creacion')), DIAS_FIN_RECEPCION=(F('fechafinrecepcion') - F('fechainiciorecepcion')))[0]
                    # data['es_donar'] = True
                    # template = get_template("publicaciondonacion/modal/detallepublicacion.html")
                    # json_content = template.render(data)
                    #return JsonResponse({"result": True, 'data': json_content})
                # except Exception as ex:
                #     pass

            if action == 'editdonacion':
                try:
                    dpp = DetalleProductoPublicacion.objects.get(id=int(encrypt(request.GET['iddp'])))
                    return JsonResponse({"result": True, 'data': dpp.mi_cantidad_donada(persona)})
                except Exception as ex:
                    pass

            if action == 'listaproductos':
                try:
                    pd = PublicacionDonacion.objects.filter(pk=int(encrypt(request.GET['id']))).first()
                    data['title'] = f"{pd.nombre}".capitalize()
                    s, filtro, url_vars = request.GET.get('s', ''), Q(status=True, publicaciondonacion_id =pd.pk ), ''

                    if s:
                        filtro = filtro & (Q(producto__descripcion__icontains=s) | Q(producto__tipoproducto__descripcion__icontains=s))
                        url_vars = '&s='+s

                    paging = MiPaginador(DetalleProductoPublicacion.objects.filter(filtro).order_by('producto__descripcion'), 20)
                    p=1
                    try:
                        paginasesion = 1
                        if 'paginador' in request.session:
                            paginasesion = int(request.session['paginador'])
                        if 'page' in request.GET:
                            p = int(request.GET['page'])
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
                    data['page_number'] = p
                    data['rangospaging'] = paging.rangos_paginado(p)
                    data['page'] = page
                    data['solicitud'] = page.object_list
                    data['url_vars'] = url_vars
                    data['idpd'] = int(encrypt(request.GET['id']))
                    return render(request, "publicaciondonacion/listaproductos.html", data)
                except Exception as ex:
                    pass

            if action == 'addpublicacion':
                try:
                    form = PublicacionDonacionForm()
                    form.es_agregar()
                    data['form'] = form
                    data['unidadmedida'] = UnidadMedidaDonacion.objects.filter(status=True)
                    data['title'] = "Agregar publicación"
                    return render(request, "publicaciondonacion/modal/addpublicacion.html", data)
                except Exception as ex:
                    pass

            if action == 'detallerecaudacion':
                try:
                    data['title'] = "Detalle de recaudación"
                    data['publicacion'] = PublicacionDonacion.objects.filter(pk=int(encrypt(request.GET['id']))).first()
                    return render(request, "publicaciondonacion/detallerecaudacion.html", data)
                except Exception as ex:
                    pass

            if action == 'editpublicacion':
                try:
                    data['title'] = "Editar publicación"
                    data['unidadmedida'] = UnidadMedidaDonacion.objects.filter(status=True)
                    id = int(encrypt(request.GET['id'])) if request.GET['id'] else 0
                    pd = PublicacionDonacion.objects.filter(pk=id)[0] if PublicacionDonacion.objects.filter(pk=id) else None
                    if pd:
                        form = PublicacionDonacionForm(initial=model_to_dict(pd))
                        if pd.estado == 2:
                            form.editar_aprobado()
                            detalle = pd.detalleaprobacionpublicaciondonacion_set.filter(status=True).order_by('-id').first()
                            form.fields['fechainicioentrega'].initial = detalle.fecha_creacion
                            data['ffentrega'] = form.fields['fechafinentrega'].initial = (detalle.fecha_creacion + datetime.timedelta(days=7))
                            data['aprobado'] = True
                        else:
                            form.es_agregar()

                    data['listaproductos'] = DetalleProductoPublicacion.objects.filter(publicaciondonacion_id=pd.pk)
                    data['id'] = id
                    data['form'] = form
                    return render(request, "publicaciondonacion/modal/addpublicacion.html", data)
                except Exception as ex:
                    pass

            if action == 'detallepublicacion':
                try:
                    data['tiene_datos_donacion'] = ContribuidorDonacion.objects.filter(persona=persona).exists()
                    data['solicitud'] = PublicacionDonacion.objects.filter(pk=int(encrypt(request.GET['id']))).annotate(PUBLICADO_HACE=(currenttime - F('fecha_creacion')), DIAS_FIN_RECEPCION=(F('fechafinrecepcion') - F('fechainiciorecepcion')))[0]
                    template = get_template("publicaciondonacion/modal/detallepublicacion.html")
                    json_content = template.render(data)
                    return JsonResponse({"result":True, 'data': json_content})
                except Exception as ex:
                    return JsonResponse({"result": "bad", "mensaje": u"Error al cargar los datos."})

            if action == 'addproducto':
                try:
                    data['form'] = ProductoForm()
                    template = get_template("publicaciondonacion/modal/addproducto.html")
                    json_content = template.render(data)
                    return JsonResponse({"result": "ok", 'html': json_content})
                except Exception as ex:
                    return JsonResponse({"result": "bad", "mensaje": u"Error al cargar los datos."})

            if action == 'adddetalleproducto':
                try:
                    form = DetalleProductoPublicacionForm()
                    if 'ids[]' in request.GET:
                        list = request.GET.getlist('ids[]')
                        if list:
                            form.fields['producto'].queryset = Producto.objects.filter(status=True).order_by('-id').exclude(pk__in=list)

                    data['form'] = form
                    template = get_template("publicaciondonacion/modal/addproducto.html")
                    json_content = template.render(data)
                    return JsonResponse({"result": "ok", 'html': json_content})
                except Exception as ex:
                    return JsonResponse({"result": "bad", "mensaje": u"Error al cargar los datos."})

            if action == 'editdetalleproducto':
                try:
                    form = DetalleProductoPublicacionForm()
                    exclude = {}

                    if 'render[]' in request.GET:
                        list = request.GET.getlist('render[]')
                        if len(list) == 3:
                            if 'ids[]' in request.GET:
                                exclude = set(request.GET.getlist('ids[]'))
                            #     if len(exclude) > 1:
                            #         list2 = exclude.remove(list[0]) if list[0] in exclude else exclude
                            #form.edit(list[0])
                            form.fields['producto'].queryset = Producto.objects.filter(status=True).exclude(id__in=exclude)
                            form.fields['producto'].initial = [int(list[0])] if list[0] else []
                            form.fields['cantidad'].initial = list[1]
                            form.fields['unidadmedida'].initial = list[2]

                    data['form'] = form
                    template = get_template("publicaciondonacion/modal/addproducto.html")
                    json_content = template.render(data)
                    return JsonResponse({"result": "ok", 'html': json_content})
                except Exception as ex:
                    return JsonResponse({"result": "bad", "mensaje": u"Error al cargar los datos."})

            if action == 'mostrardetalleaprobacion_view':
                try:
                    publicaciond = PublicacionDonacion.objects.filter(pk=int(encrypt(request.GET['id']))).first()
                    detalle = DetalleAprobacionPublicacionDonacion.objects.filter(publicaciondonacion_id=publicaciond.pk, status=True).order_by('fecha_creacion')
                    data['detalleaprobacion'] = detalle
                    data['publicaciondonacion'] = publicaciond
                    data['estadochoices'] = PUBLICACION_DONACION_ESTADO
                    template = get_template("adm_publicaciondonacion/modal/mostrardetalleaprobacion_view.html")
                    return JsonResponse({"result": True, 'data': template.render(data)})
                except Exception as ex:
                    pass

            return HttpResponseRedirect('/publicaciondonacion')
        else:
            try:
                data['title'] = u'Donaciones'

                url_vars = ''
                tab = 'tab-mis-publicaciones'
                search, tipodonacion, fi, ff = request.GET.get('s', ''), request.GET.get('td','0'), request.GET.get('fi', ''), request.GET.get('ff', '')
                filtro = Q(status=True)
                querybase = PublicacionDonacion.objects.filter(filtro).annotate(PUBLICADO_HACE=(currenttime - F('fecha_creacion')), DIAS_FIN_RECEPCION=(F('fechafinrecepcion') - F('fechainiciorecepcion')))

                url_vars_filter = []
                if search:
                    filtro = filtro & (Q(nombre__icontains=search.strip()) | Q(persona__cedula=search.strip()) | Q(persona__apellido1__icontains=search.strip()) | Q(persona__apellido2__icontains=search.strip()))
                    url_vars += '&s=' + search
                    data['s'] = search
                    url_vars_filter.append(['s', search])

                if fi:
                    filtro = filtro & Q(fecha_creacion__gte=fi)
                    url_vars += '&fi=' + fi
                    data['fi'] = fi
                    url_vars_filter.append(['fi', fi])

                if ff:
                    filtro = filtro & Q(fecha_creacion__lte=ff)
                    url_vars += '&ff=' + ff
                    data['ff'] = ff
                    url_vars_filter.append(['ff', ff])

                if int(tipodonacion):
                    filtro = filtro & (Q(tipodonacion_id=tipodonacion))
                    url_vars += '&td=' + tipodonacion
                    data['td'] = int(tipodonacion)
                    url_vars_filter.append(['td', TipoDonacion.objects.get(pk=tipodonacion)])

                tab_number = (int(request.GET['tab']) if request.GET['tab'] else 1) if 'tab' in request.GET else 1
                if tab_number == 2:
                    tab = 'tab-publicaciones-externas'
                    listado = querybase.filter(filtro & Q(estado=2)).order_by('estadoprioridad')
                elif tab_number == 1:
                    listado = querybase.filter(filtro & Q(persona=persona)) if persona else querybase.filter(filtro)
                else:
                    listado = querybase.filter(filtro)

                paging = MiPaginador(listado, 20)
                p = 1
                try:
                    paginasesion = 1
                    if 'paginador' in request.session:
                        paginasesion = int(request.session['paginador'])
                    if 'page' in request.GET:
                        p = int(request.GET['page'])
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
                data['page_number'] = p
                data['rangospaging'] = paging.rangos_paginado(p)
                data['page'] = page
                data['email_domain'] = EMAIL_DOMAIN
                data['listadonaciones'] = page.object_list
                data['url_vars'] = url_vars
                data['tab_number'] = tab_number

                if tab_number == 1:
                    data['url_vars_filter'] = url_vars_filter
                    data['mispublicaciones'] = page.object_list
                    data['publicacionesexternas'] = querybase.filter(estado=2).order_by('estadoprioridad')
                else:
                    data['url_vars_filter2'] = url_vars_filter
                    data['publicacionesexternas'] = page.object_list
                    data['mispublicaciones'] = querybase.filter(status=True, persona=persona) if persona else ''

                data['groupbymispublicaciones'] = data['groupbypublicacionesexternas'] = TipoDonacion.objects.values_list('id', 'nombre').filter(status=True)

                externo = not persona.perfilusuario_set.values('id').filter(status=True).exists()

                if not externo:
                    from bd.models import LogEntryLogin
                    logentry = LogEntryLogin.objects.values_list('action_time', flat=True).filter(user_id=usuario.pk).order_by('-id')
                    lastpublication = querybase.filter(status=True, persona=persona, estado=2).order_by('-id').first()
                    if lastpublication:
                        prelastlog = logentry[1] if len(logentry) >= 2 else ''
                        detallep = DetalleProductoPublicacion.objects.filter(status=True, publicaciondonacion=lastpublication).order_by('-id').first()
                        lastgift = DetalleContribuidorDonacion.objects.filter(status=True, detalleproductopublicacion=detallep, fecha_creacion__gte=prelastlog).order_by('-id')
                        if 'currentuserseenotification' not in request.session:
                            if len(lastgift):
                                data['notification'] = len(lastgift)
                                data['lastpublication'] = lastpublication.pk
                                request.session['currentuserseenotification'] = True

                data['externo'] = externo
                data['tab_init'] = tab if not externo else 'tab-publicaciones-externas'
                data['tiene_datos_donacion'] = ContribuidorDonacion.objects.filter(persona=request.session['persona']).exists() if persona else None
                return render(request, 'publicaciondonacion/view.html', data)
            except Exception as ex:
                return HttpResponseRedirect(f"/?info=Error de conexión. {ex.__str__()}")
