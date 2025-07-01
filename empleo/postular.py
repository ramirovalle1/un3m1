# -*- coding: latin-1 -*-
# decoradores
from django.core.files import File
from django.contrib.auth.decorators import login_required
from django.db.models import Q
from django.shortcuts import render
from django.template.loader import get_template

from decorators import last_access, secure_module
from django.db import transaction
from django.http import HttpResponseRedirect, JsonResponse
from sga.tasks import send_html_mail, conectar_cuenta
from .forms import SolicitudRevisionTituloForm
from .models import *
from sga.commonviews import adduserdata
from sga.funciones import generar_nombre, log, email_valido, MiPaginador
from sga.models import Persona, NivelTitulacion, Titulacion, Graduado, Titulo, RedPersona, FotoPersona, CertificadoIdioma, CamposTitulosPostulacion, miinstitucion, CUENTAS_CORREOS, SubAreaConocimientoTitulacion, SubAreaEspecificaConocimientoTitulacion, AreaConocimientoTitulacion
from sga.templatetags.sga_extras import encrypt


def validar_campos(request, persona, partida):
    try:
        titulos_persona = persona.titulacion_set.filter(status=True)
        qscampostitulos = CamposTitulosPostulacion.objects.select_related().filter(status=True, titulo__in=titulos_persona.values_list('titulo__id', flat=True))
        numcumplimiento, lista_amplios, lista_especificos, lista_detallados = 0, [], [], []
        for campotitulo in qscampostitulos:
            lista_amplios += campotitulo.campoamplio.all().values_list('id', flat=True)
            lista_especificos += campotitulo.campoespecifico.all().values_list('id', flat=True)
            lista_detallados += campotitulo.campodetallado.all().values_list('id', flat=True)
        cumpleamplios = len((set(lista_amplios) & set(list(partida.campoamplio.values_list('id', flat=True))))) > 0
        cumpleespecifico = len((set(lista_especificos) & set(list(partida.campoespecifico.values_list('id', flat=True))))) > 0
        cumpledetallado = len((set(lista_detallados) & set(list(partida.campodetallado.values_list('id', flat=True))))) > 0
        miscamposamplios = AreaConocimientoTitulacion.objects.filter(id__in=lista_amplios)
        miscamposespecificos = SubAreaConocimientoTitulacion.objects.filter(id__in=lista_especificos)
        miscamposdetallados = SubAreaEspecificaConocimientoTitulacion.objects.filter(id__in=lista_detallados)
        if not cumpleamplios:
            numcumplimiento += 1
        if not cumpleespecifico:
            numcumplimiento += 1
        if not cumpledetallado:
            numcumplimiento += 1
        return {'result': True, 'numcumplimiento': numcumplimiento, 'cumpleamplio': cumpleamplios, 'cumpleespecifico': cumpleespecifico, 'cumpledetallado': cumpledetallado, 'miscamposamplios': miscamposamplios, 'miscamposespecificos': miscamposespecificos, 'miscamposdetallados': miscamposdetallados}
    except Exception as ex:
        return {'result': False, 'numcumplimiento': 0, 'cumpleamplio': False, 'cumpleespecifico': False, 'cumpledetallado': False, 'msg': str(ex), 'miscamposamplios': [], 'miscamposespecificos': [], 'miscamposdetallados': []}


@login_required(redirect_field_name='ret', login_url='/loginempleo')
@secure_module
@last_access
@transaction.atomic()
def view(request):
    data = {}
    adduserdata(request, data)
    data['url_'] = request.path
    perfilprincipal = request.session['perfilprincipal']
    persona = request.session['persona']
    periodo = request.session['periodo']
    data['hoy'] = hoy = datetime.now().date()
    data['currenttime'] = datetime.now()
    data['perfil'] = persona.mi_perfil()
    data['periodo'] = periodo
    if request.method == 'POST':
        action = request.POST['action']

        if action == 'aplicar_partida':
            try:
                bloqueo = False
                oferta = OfertaLaboralEmpresa.objects.get(pk=int(encrypt(request.POST['oferta'])))
                if not request.POST['aceptatermino']:
                    return JsonResponse({"result": False, "mensaje": u"Debe aceptar los terminos y condiciones para aplicar a esta oferta."})
                if oferta.ffin < datetime.now().date():
                    return JsonResponse({"result": False, "mensaje": u"Lo sentimos esta oferta ya no se encuentra vigente."})
                if persona.personaaplicaoferta_set.values('id').filter(oferta=oferta, status=True).exists():
                    return JsonResponse({"result": False, "mensaje": u"Usted ya aplicó a esta oferta."})
                if not oferta.permite_aplicar():
                    return JsonResponse({"result": False, "mensaje": u"Lo sentimos, tiempo de postulación caducó"})
                aplicar = PersonaAplicaOferta(persona=persona, oferta=oferta)
                aplicar.save(request)
                log(u'Postulación exitosa : %s, oferta[%s]' % (persona, oferta), request, "add")

                send_html_mail(u"Postulación registrada con exito, UNEMI-EMPLEO.", "emails/postulate_aplica_partida.html",
                               {'sistema': u'UNEMI- EMPLEO', 'fecha': datetime.now().date(), 'hora': datetime.now().time(), 'persona': persona,
                                'oferta': oferta, 't': miinstitucion(), 'tit': 'Unemi-Empleo'},
                               persona.lista_emails_envio(), [], [], cuenta=CUENTAS_CORREOS[17][1])


                return JsonResponse({"result": True, "mensaje": u"Postulacion exitosa"})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": False, "mensaje": "Error al guardar los datos. %s" % ex})
        elif action == 'review':
            try:
                if not 'inscripcion' in request.POST:
                    raise NameError('Debe seleccionar una carrera para validar.')
                if Graduado.objects.filter(status=True,  inscripcion=request.POST['inscripcion']).exists():
                    raise NameError('Usted ya se encuenta registrado como graduado.')
                if SolicitudRevisionTitulo.objects.filter(status=True, inscripcion=request.POST['inscripcion'], estado__lte=1).exists():
                    raise NameError('Ya existe una solicitud para la carrera que seleccionó.')
                form = SolicitudRevisionTituloForm(request.POST, request.FILES)
                if not 'evidencia' in request.FILES:
                    raise NameError('Debe subir el archivo de registro del titulo en el SENECYT')
                newfile = request.FILES['evidencia']
                ext = newfile._name[newfile._name.rfind("."):]
                if ext not in ['.pdf', '.PDF']:
                    raise NameError('Debe subir un archivo en formato .pdf')
                if newfile.size > 20971520:
                    raise NameError('Debe subir un archivo no mayor a 20 Mb.')
                if form.is_valid():
                    newfile._name = generar_nombre("evidencia_titulo_", newfile._name)
                    solicitud = SolicitudRevisionTitulo()
                    solicitud.inscripcion = form.cleaned_data['inscripcion']
                    solicitud.descripcion = form.cleaned_data['descripcion']
                    solicitud.evicencia = newfile
                    solicitud.save(request)
                    log('Adiciono solicitud de revisión de titulo: {}'.format(solicitud.inscripcion.persona.nombre_completo_minus()), request, "add")
                    # notificacion('Solicitud de revisión de titulo', 'El estudiante {} ingresó una solicitud de revisión de titulo'.format(solicitud.inscripcion.persona.nombre_completo_minus()), para, None, '/pro_cronograma?action=listatutorias', add.pk, 1,
                    #              'sga', InquietudPracticasPreprofesionales, request)
                    return JsonResponse({'result': False, "cerrar": True, "mensaje": "Solicitud enviada correctamente"})
                else:
                    transaction.set_rollback(True)
                    return JsonResponse({'result': True, "form": [{k: v[0]} for k, v in form.errors.items()], "mensaje": "Error en el formulario"})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": True, "mensaje": "{}".format(ex)})
        elif action == 'deletesolicitud':
            try:
                solicitud = SolicitudRevisionTitulo.objects.filter(status=True, id=int(encrypt(request.POST['id']))).first()
                if not solicitud:
                    raise NameError('Solicitud no encontrada')
                solicitud.status = False
                solicitud.save(request, update_fields=['status'])
                log('Eliminó solicitud de revisión de titulo: {}'.format(
                    solicitud.inscripcion.persona.nombre_completo_minus()), request, "delete")
                return JsonResponse({"error": False})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": True, "mensaje": "{}".format(ex)})

        return JsonResponse({"result": False, "mensaje": u"Solicitud Incorrecta."})
    else:
        if 'action' in request.GET:
            data['action'] = action = request.GET['action']

            if action == 'verdetalle':
                try:
                    data['id'] = id = int(encrypt(request.GET['id']))
                    data['nopostula'] = nopostula = 'nopostula' in request.GET
                    data['filtro'] = filtro = OfertaLaboralEmpresa.objects.get(pk=id)

                    data['resp_campos'] = validar_campos(request, persona, filtro)
                    template = get_template("empleo/postular/verdetalle.html")
                    return JsonResponse({"result": True, 'data': template.render(data)})
                except Exception as ex:
                    pass

            elif action == 'confirmar':
                try:
                    data['id'] = id = encrypt(request.GET['id'])
                    data['filtro'] = filtro = OfertaLaboralEmpresa.objects.get(pk=id)
                    # data['otrascertificaciones'] = CertificadoIdioma.objects.filter(status=True, persona=persona).order_by('id')
                    data['niveltitulo'] = NivelTitulacion.objects.filter(pk__in=[3,4], status=True).order_by('-rango')
                    data['resp_campos'] = validar_campos(request, persona, filtro)
                    template = get_template("empleo/postular/confirmar.html")
                    return JsonResponse({"result": True, 'data': template.render(data)})
                except Exception as ex:
                    pass
            elif action == 'review':
                try:
                    insgraduado = Graduado.objects.filter(status=True, inscripcion__persona=persona).values_list('inscripcion_id', flat=True)
                    solicitudes = SolicitudRevisionTitulo.objects.filter(status=True, inscripcion__persona=persona, estado__lte=1).values_list('inscripcion_id', flat=True)
                    ids = []
                    for i in persona.inscripcion_set.filter(status=True).exclude(coordinacion_id__in=(9, 7)).exclude(id__in=solicitudes).exclude(id__in=insgraduado):
                        if i.perfil_inscripcion():
                            ids.append(i.id)
                    data['inscripciones'] = inscripciones = ids
                    form = SolicitudRevisionTituloForm()
                    form.cargar_inscripciones(inscripciones)
                    data['form'] = form
                    template = get_template("empleo/postular/solicitud.html")
                    return JsonResponse({"result": True, 'data': template.render(data)})
                except Exception as ex:
                    pass
            elif action == 'listreview':
                try:
                    data['solicitudes'] = solicitudes = SolicitudRevisionTitulo.objects.filter(status=True, inscripcion__persona=persona)
                    template = get_template("empleo/postular/listasolicitudes.html")
                    return JsonResponse({"result": True, 'data': template.render(data)})
                except Exception as ex:
                    pass

            return HttpResponseRedirect(request.path)
        else:
            try:
                data['title'] = u'Ofertas Laborales'

                titulos_persona = persona.titulacion_set.filter(status=True)
                data['NIVEL_INSTRUCCION_FORMACION'] = NIVEL_INSTRUCCION_FORMACION = ((3, u'TERCER NIVEL'), (4, u'CUARTO NIVEL'))
                carreras = persona.inscripcion_set.filter(status=True).exclude(coordinacion_id=9)
                carrerasaprobadas = []
                for carrera in carreras:
                    if carrera.mi_nivel().nivel_id >= 7:
                        carrerasaprobadas.append(carrera.carrera_id)
                ofertaids, empresa, search, nivelinst, filtro, url_vars = request.GET.get('ofertaids', ''),request.GET.get('empresa', ''), request.GET.get('search', ''), request.GET.get('nivelinst', ''), (Q(status=True)), ''
                if ofertaids:
                    data['ofertaids'] = int(encrypt(ofertaids))
                    url_vars += "&ofertaids={}".format(ofertaids)
                    filtro = filtro & (Q(pk=int(encrypt(ofertaids))))
                if nivelinst:
                    data['nivelinst'] = int(nivelinst)
                    url_vars += "&nivelinst={}".format(nivelinst)
                    filtro = filtro & (Q(nivel=nivelinst))
                if search:
                    data['search'] = search
                    url_vars += "&search={}".format(search)
                    filtro = filtro & (Q(titulo__icontains=search))
                if empresa:
                    data['empresa'] = empresa
                    url_vars += "&empresa={}".format(empresa)
                    filtro = filtro & (Q(empresa__nombre__icontains=empresa))
                # if persona.graduado():
                #     filtro = filtro & (Q(quienpostula__in=[0, 2]))
                postuladas = PersonaAplicaOferta.objects.filter(status=True, persona=persona).values_list('oferta_id', flat=True)
                listado = OfertaLaboralEmpresa.objects.filter(filtro).filter(estadooferta=1, ffinpostlacion__gte=datetime.now().date()).exclude(id__in=postuladas).order_by('-finicio').distinct()
                data['empresas'] = listado.values('empresa_id', 'empresa__nombrecorto').distinct('empresa_id').order_by('empresa_id')
                data['tienesolicitudes'] = SolicitudRevisionTitulo.objects.filter(status=True, inscripcion__persona=persona).exists()
                paging = MiPaginador(listado, 10)
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
                data["url_vars"] = url_vars
                data['hoy'] = datetime.now().date()
                data['listado'] = page.object_list
                data['list_count'] = len(listado)
                return render(request, "empleo/postular/view.html", data)
            except Exception as ex:
                pass
