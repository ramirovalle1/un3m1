# -*- coding: latin-1 -*-
# decoradores
import json
import sys
from datetime import timedelta
from random import random, randint

from django.core.files import File
from django.contrib.auth.decorators import login_required
from django.db.models import Q
from django.shortcuts import render
from django.template.loader import get_template

from decorators import last_access, secure_module
from django.db import transaction
from django.http import HttpResponseRedirect, JsonResponse

from sagest.models import PazSalvo
from sga.tasks import send_html_mail, conectar_cuenta
from .forms import TitulacionPersonaPostulacionForm
from .models import *
from sga.commonviews import adduserdata
from sga.funciones import generar_nombre, log, email_valido, MiPaginador
from sga.models import Persona, NivelTitulacion, Titulacion, Graduado, Titulo, \
    RedPersona, FotoPersona, CertificadoIdioma, CamposTitulosPostulacion, \
    miinstitucion, CUENTAS_CORREOS, SubAreaConocimientoTitulacion, \
    SubAreaEspecificaConocimientoTitulacion, AreaConocimientoTitulacion
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


@login_required(redirect_field_name='ret', login_url='/loginpostulate')
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
                partida = Partida.objects.get(pk=int(encrypt(request.POST['partida'])))
                if persona.personaaplicarpartida_set.values('id').filter(partida__convocatoria=partida.convocatoria, status=True).exists():
                    return JsonResponse({"result": False, "mensaje": u"Solo puede aplicar a una partida por concurso."})
                if persona.personaaplicarpartida_set.filter(partida__convocatoria__vigente=True, status=True).count() >= 1:
                    return JsonResponse({"result": False, "mensaje": u"Solo puede aplicar a una partida por concurso."})
                if not partida.permite_aplicar():
                    return JsonResponse({"result": False, "mensaje": u"Lo sentimos, tiempo de postulación caduco"})
                aplicar = PersonaAplicarPartida(persona=persona, partida=partida)
                aplicar.save(request)
                listatitulossel = json.loads(request.POST['lista_items1'])
                listformacionacademica = persona.mi_formacionacademica() if len(listatitulossel) <= 0 else []
                for list in listatitulossel:
                    armonizacion = PartidaArmonizacionNomenclaturaTitulo.objects.get(status=True,partida=partida,combinacion_id=int(list['id']))
                    inst = InstitucionEducacionSuperior.objects.get(status=True,id=int(list['id_institucion']))
                    instancia = PersonaFormacionAcademicoPartida(personapartida=aplicar,titulo=armonizacion.combinacion.titulo,registro=list['registro'],
                                                                 institucion=inst, cursando=list['cursando'], educacionsuperior=True,combinacion=armonizacion.combinacion)
                    instancia.pais_id = int(list['pais']) if list['pais'] != '' else None
                    instancia.provincia_id = int(list['provincia']) if list['provincia'] != '' else None
                    instancia.canton_id = int(list['canton']) if list['canton'] != '' else None
                    instancia.parroquia_id = int(list['parroquia']) if list['parroquia'] != '' else None
                    text_archivo = f'archivo_{armonizacion.combinacion.id}'
                    if not text_archivo in request.FILES:
                        raise NameError("No se encontraron archivos validos, intentelo mas tarde.")
                    archivo = request.FILES[text_archivo]
                    ext = archivo._name.split('.')[-1]
                    if not ext in ['pdf']:
                        raise NameError("El archivo debe ser formato pdf.")
                    if archivo.size > 4194304:
                        raise NameError("El archivo es mayor a 4MB")
                    archivo._name = f'{persona.identificacion()}_{hoy.day}{hoy.month}{hoy.year}{randint(1, 10000).__str__()}.{ext}'
                    instancia.archivo = archivo if archivo else None
                    instancia.save(request)
                    instancia.campoamplio.add(armonizacion.combinacion.campoamplio)
                    instancia.campoespecifico.add(armonizacion.combinacion.campoespecifico)
                    instancia.campodetallado.add(armonizacion.combinacion.campodetallado)
                    instancia.save(request)
                for list in listformacionacademica:
                    instancia = PersonaFormacionAcademicoPartida(personapartida=aplicar, titulo=list.titulo, registro=list.registro, pais=list.pais, provincia=list.provincia,
                                                                 canton=list.canton, parroquia=list.parroquia, educacionsuperior=list.educacionsuperior,
                                                                 institucion=list.institucion, cursando=list.cursando)
                    instancia.archivo = list.archivo if list.archivo else None
                    instancia.save(request)
                    if CamposTitulosPostulacion.objects.filter(status=True, titulo=list.titulo).exists():
                        campotitulo = CamposTitulosPostulacion.objects.filter(status=True, titulo=list.titulo).first()
                        for ct in campotitulo.campoamplio.all():
                            instancia.campoamplio.add(ct)
                        for ct in campotitulo.campoespecifico.all():
                            instancia.campoespecifico.add(ct)
                        for ct in campotitulo.campodetallado.all():
                            instancia.campodetallado.add(ct)
                        instancia.save(request)
                listexperiencia = persona.mis_experienciaslaborales()
                for list in listexperiencia:
                    instancia = PersonaExperienciaPartida(personapartida=aplicar, institucion=list.institucion, actividadlaboral=list.actividadlaboral,
                                                          cargo=list.cargo, fechainicio=list.fechainicio, fechafin=list.fechafin)
                    instancia.archivo = list.archivo if list.archivo else None
                    instancia.save(request)
                listcapacitaciones = persona.mis_capacitaciones()
                for list in listcapacitaciones:
                    instancia = PersonaCapacitacionesPartida(personapartida=aplicar, institucion=list.institucion, tipo=list.tipo,
                                                             nombre=list.nombre, descripcion=list.descripcion, tipocurso=list.tipocurso,
                                                             tipocapacitacion=list.tipocapacitacion, tipocertificacion=list.tipocertificacion, tipoparticipacion=list.tipoparticipacion,
                                                             anio=list.anio, contextocapacitacion=list.contextocapacitacion, detallecontextocapacitacion=list.detallecontextocapacitacion,
                                                             auspiciante=list.auspiciante, areaconocimiento=list.areaconocimiento, subareaconocimiento=list.subareaconocimiento, subareaespecificaconocimiento=list.subareaespecificaconocimiento,
                                                             pais=list.pais, provincia=list.provincia, canton=list.canton, parroquia=list.parroquia, fechainicio=list.fechainicio, fechafin=list.fechafin, horas=list.horas,
                                                             expositor=list.expositor, modalidad=list.modalidad, otramodalidad=list.otramodalidad)
                    instancia.archivo = list.archivo if list.archivo else None
                    instancia.save(request)
                listpublicaciones = persona.mis_publicaciones()
                for list in listpublicaciones:
                    instancia = PersonaPublicacionesPartida(personapartida=aplicar, nombre=list.nombre, tiposolicitud=list.tiposolicitud, fecha=list.fecha)
                    instancia.archivo = list.archivo if list.archivo else None
                    instancia.save(request)
                listidiomas = CertificadoIdioma.objects.filter(status=True, persona=persona).order_by('id')
                for list in listidiomas:
                    instancia = PersonaIdiomaPartida(personapartida=aplicar, idioma=list.idioma,
                                                     institucioncerti=list.institucioncerti, validainst=list.validainst,
                                                     otrainstitucion=list.otrainstitucion, nivelsuficencia=list.nivelsuficencia,
                                                     fechacerti=list.fechacerti)
                    instancia.archivo = list.archivo if list.archivo else None
                    instancia.save(request)
                send_html_mail(u"Postulación registrada con exito, Postúlate-UNEMI.", "emails/postulate_aplica_partida.html",
                               {'sistema': u'Postúlate-UNEMI', 'fecha': datetime.now().date(), 'hora': datetime.now().time(), 'persona': persona,
                                'partida': partida, 't': miinstitucion(), 'tit': 'Postulate - Unemi'},
                               persona.lista_emails_envio(), [], [], cuenta=CUENTAS_CORREOS[30][1])
                log(u'Postulación exitosa : %s, partida[%s]' % (persona, partida), request, "add")
                return JsonResponse({"result": True})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": False, "mensaje": "Error al guardar los datos. %s" % ex})

        elif action == 'agregaramornhojavida':
            try:
                form = TitulacionPersonaPostulacionForm(request.POST,request.FILES)
                if not form.is_valid():
                    raise NameError(f"{[{k:v[0]} for k,v in form.errors.items()]}")
                if not 'archivo' in request.FILES:
                    raise NameError("Debe ingresar un archivo.")
                archivo = request.FILES['archivo']
                ext = archivo._name.split('.')[-1]
                if not ext in ['pdf']:
                    raise NameError("El archivo debe ser formato pdf.")
                if archivo.size > 4194304:
                    raise NameError("El archivo es mayor a 4MB")
                modelo = PersonaFormacionAcademicoPartida(
                    titulo=form.cleaned_data['titulo'].titulo,
                    registro=form.cleaned_data['registro'],
                    pais=form.cleaned_data['pais'],
                    provincia=form.cleaned_data['provincia'],
                    canton=form.cleaned_data['canton'],
                    parroquia=form.cleaned_data['parroquia'],
                    institucion=form.cleaned_data['institucion'],
                    archivo=archivo,
                    combinacion=form.cleaned_data['titulo']
                )
                modelo.save(request)
                log("Agrego formación academica: %s"%(modelo),request,'add')
                res_js = {"result": True, "mensaje": "Registro guardado con éxito!"}
            except Exception as ex:
                msg_ex = 'Error on line {} - {}'.format(sys.exc_info()[-1].tb_lineno, str(ex))
                transaction.set_rollback(True)
                res_js = {"result": False, "mensaje": msg_ex}
            return JsonResponse(res_js)

        return JsonResponse({"result": False, "mensaje": u"Solicitud Incorrecta."})
    else:
        if 'action' in request.GET:
            data['action'] = action = request.GET['action']

            if action == 'verdetalle':
                try:
                    data['id'] = id = encrypt(request.GET['id'])
                    data['filtro'] = filtro = Partida.objects.get(pk=id)
                    data['resp_campos'] = validar_campos(request, persona, filtro)
                    template = get_template("postulate/postular/verdetalle.html")
                    return JsonResponse({"result": True, 'data': template.render(data)})
                except Exception as ex:
                    pass

            if action == 'confirmar':
                try:
                    data['id'] = id = encrypt(request.GET['id'])
                    data['filtro'] = filtro = Partida.objects.get(pk=id)
                    amorituzacion = filtro.obtener_titulo_amortizacion()
                    titulos = ArmonizacionNomenclaturaTitulo.objects.filter(status=True,id__in=amorituzacion)
                    form = TitulacionPersonaPostulacionForm()
                    form.adicionar()
                    form.fields['titulo'].queryset = titulos
                    data['form'] = form
                    data['otrascertificaciones'] = CertificadoIdioma.objects.filter(status=True, persona=persona).order_by('id')
                    data['niveltitulo'] = NivelTitulacion.objects.filter(pk__in=[3,4], status=True).order_by('-rango')
                    data['resp_campos'] = validar_campos(request, persona, filtro)
                    template = get_template("postulate/postular/confirmar.html")
                    data['cumplimiento_requisitos_capacitaciones'] = filtro.cumple_con_capacitaciones_requeridas(persona.id)
                    return JsonResponse({"result": True, 'data': template.render(data)})
                except Exception as ex:
                    pass

            if action == 'buscarniveltitulo':
                try:
                    id = int(request.GET['id_armonizacion'])
                    registro = ArmonizacionNomenclaturaTitulo.objects.get(status=True,id=id)
                    titulo = registro.titulo.nivel.id
                    nivel=0
                    if titulo in [4,30]:
                        nivel = 4
                    if titulo in [3]:
                        nivel = 3
                    res_js = {"result": True, "mensaje": "Registro guardado con éxito!",'nivel':nivel}
                except Exception as ex:
                    msg_ex = 'Error on line {} - {}'.format(sys.exc_info()[-1].tb_lineno, str(ex))
                    res_js = {"result": False, "mensaje": msg_ex}
                return JsonResponse(res_js)

            return HttpResponseRedirect(request.path)
        else:
            try:
                data['title'] = u'Ofertas Laborales'
                titulos_persona = persona.titulacion_set.filter(status=True)
                data['NIVEL_INSTRUCCION_FORMACION'] = NIVEL_INSTRUCCION_FORMACION = ((3, u'TERCER NIVEL'), (4, u'CUARTO NIVEL'), (5, u'PHD'),)
                qscampostitulos = CamposTitulosPostulacion.objects.select_related().filter(status=True, titulo__in=titulos_persona.values_list('titulo__id', flat=True))
                lista_especificos = []
                for campotitulo in qscampostitulos:
                    lista_especificos += campotitulo.campoespecifico.all().values_list('id', flat=True)
                data['miscamposespecificos'] = SubAreaConocimientoTitulacion.objects.filter(id__in=lista_especificos)
                codpartida, nivelinst, filtro, url_vars = request.GET.get('codpartida', ''), request.GET.get('nivelinst', ''), (Q(status=True)), ''
                if codpartida:
                    data['codpartida'] = codpartida
                    url_vars += "&codpartida={}".format(codpartida)
                    filtro = filtro & (Q(titulo__icontains=codpartida) | Q(codpartida__icontains=codpartida))
                if nivelinst:
                    data['nivelinst'] = int(nivelinst)
                    url_vars += "&nivelinst={}".format(nivelinst)
                    filtro = filtro & (Q(nivel=nivelinst))
                fecha_actual = datetime.now()

                # Calcular la fecha hace 2 años desde la fecha actual
                fecha_hace_dos_anios = fecha_actual - timedelta(days=730)
                # desiste = PersonaDesiste.objects.filter(
                #     status=True, persona=persona,
                #     fecha__gte=fecha_hace_dos_anios.date()
                # ).order_by('-fecha')
                # data['desiste'] = desiste.exists()
                data['puedepostular'] = False if bloqueo_pazsalvo(persona) or bloqueo_desistir(persona) else True
                data['pazsalvo'] = bloqueo_pazsalvo(persona)
                # data['desisteobj'] = desiste.last()
                listado = Partida.objects.filter(filtro).filter(convocatoria__vigente=True, convocatoria__finicio__lte=hoy, convocatoria__ffin__gte=hoy, vigente=True).order_by('codpartida')
                paging = MiPaginador(listado, 20)
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
                data['listado'] = page.object_list
                data['list_count'] = len(listado)
                return render(request, "postulate/postular/view.html", data)
            except Exception as ex:
                pass
def bloqueo_pazsalvo(postulante):
    configuracion = ConfiguraRenuncia.objects.filter(status=True, activo=True).first()
    pazsalvo=None
    if configuracion:
        fechatope = datetime.now().date() - relativedelta(months=configuracion.meses)
        pazsalvo = PazSalvo.objects.filter(status=True, persona=postulante,
                                           motivosalida=configuracion.motivo,cargo__in=configuracion.cargos.all(),
                                           fecha__gte=fechatope)
    return pazsalvo

def bloqueo_desistir(postulante):
    configuracion = ConfiguraRenuncia.objects.filter(status=True, activo=True).first()
    renuncia=None
    if configuracion:
        fechatope = datetime.now().date() - relativedelta(months=configuracion.meses)
        renuncia = NotificacionGanador.objects.filter(status=True, personaaplicapartida__persona=postulante,
                                           fecharespuesta__gte=fechatope, estado=2)
    return renuncia