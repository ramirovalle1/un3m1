from datetime import datetime
from datetime import timedelta
from django.utils import timezone

from django.db.models import Q
from empleo.models import *
from sga.models import OfertaLaboral, AplicanteOferta,  \
     Empleador, \
     Persona, Notificacion, CarreraGrupo, Inscripcion
from empresa.models import *
from bd.models import LogEntryLogin
from cita.models import ServicioCita, ResponsableGrupoServicio, TituloWebSiteServicio, NoticiasVinculacion, \
    ServicioConfigurado, CuerpoWebSiteServicio, CardInformativo, MotivoCita,  TerminosCondicion
from sagest.funciones import encrypt_id
from sga.funciones import MiPaginador
from sga.funcionesxhtml2pdf import  conviert_html_to_2pdf
from sga.models import DIAS_CHOICES
from sga.templatetags.sga_extras import encrypt
from utils.filtros_genericos import filtro_persona, filtro_responsable

fondo = '/static/images/serviciovinculacion/CRAI.jpg'

def get_cabeceras(seccion):
    t = TituloWebSiteServicio.objects.filter(status=True, seccion=seccion).first()
    imagen = t.get_fondo() if t and t.publicado else fondo
    if seccion == 1:
        title = 'Nuestras Escuelas Formativas'
        subtitle = '¡Conoce nuestras Escuelas Formativas!'
    elif seccion == 2:
        title = 'Nuestros Espacios Deportivos'
        subtitle = '¡Conoce nuestros Espacios Deportivos!'
    elif seccion == 3:
        title = 'Nuestros Vacacionales'
        subtitle = '¡Conoce nuestros Vacacionales!'
    elif seccion == 4:
        title = 'Noticias'
        subtitle = '¡Conoce todas las noticias !'
    elif seccion == 5:
        title = 'Nuestros Logros'
        subtitle = '¡Conoce nuestros Logros!'
    elif seccion == 6:
        title = 'Nuestro Equipo'
        subtitle = '¡Conoce a nuestro equipo de trabajo que disponemos!'

    return title, subtitle, t, imagen

def responsables(data, request=None):
    gruposervicio = data['gruposervicio']
    site = gruposervicio.id
    action = data['action']
    data['viewactivo'] = 'responsables'
    data['title'] = u'Nuestro Equipo'
    data['subtitle'] = u'¡"Conoce a nuestro personal de las diferentes actividades que disponemos.."!'
    data['tituloweb'] = t = TituloWebSiteServicio.objects.filter(status=True, seccion=5, departamentoservicio__id=site).first()
    try:
        data['CuerpoWebSite'] = CuerpoWebSiteServicio.objects.get(titulowebsite=t)
    except CuerpoWebSiteServicio.DoesNotExist:
        data['CuerpoWebSite'] = ''
    data['img_header'] = t.get_fondo() if t and t.publicado else fondo
    data['responsable'] = ResponsableGrupoServicio.objects.filter(status=True,activo=True)
    depservicio = data['gruposervicio']
    search, filtro, url_vars = request.GET.get('s', ''), Q(status=True), f'&sistema={gruposervicio.tiposistema}&action={action}'
    if search:
        data['s'] = search
        url_vars += f'&s={search}'
        # filtro &= Q(persona__nombres__icontains=search) | Q(persona__apellidos__icontains=search) | Q(
        #     persona__cedula__icontains=search)
        filtro = filtro_responsable(search, filtro)
    listado = ResponsableGrupoServicio.objects.filter(filtro,departamentoservicio = depservicio, activo=True).order_by('id')
    paging = MiPaginador(listado, 9)
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
    data['totcount'] = listado.count()

    return 'serviciosvinculacion/responsablesservicios.html', data

def responsable(data, request=None):
    gruposervicio = data['gruposervicio']
    site = gruposervicio.id
    data['viewactivo'] = 'responsables'
    data['subtitle'] = u'¡Conoce a nuestro equipo altamente capacitado, listo para ofrecerte la mejor ayuda posible.!'
    data['tituloweb'] = t = TituloWebSiteServicio.objects.filter(status=True, seccion=5, departamentoservicio__id=site).first()
    try:
        data['CuerpoWebSite'] = CuerpoWebSiteServicio.objects.get(titulowebsite=t)
    except CuerpoWebSiteServicio.DoesNotExist:
        data['CuerpoWebSite'] = ''
    data['img_header'] = t.get_fondo() if t and t.publicado else fondo
    data['responsable'] = ResponsableGrupoServicio.objects.get(id=encrypt_id(request.GET['id']))
    return 'serviciosvinculacion/responsableservicio.html', data

def noticias(data, request=None, depservicio=None):
    action = data['action']
    gruposervicio = data['gruposervicio']
    site = gruposervicio.id
    data['viewactivo'] = 'noticias'
    data['title'] = u'Noticias Informativas'
    data['subtitle'] = u'¡"Conoce las noticias mas relevantes de los servicios."!'
    data['tituloweb'] = t = TituloWebSiteServicio.objects.filter(status=True, seccion=3, departamentoservicio__id=site).first()
    try:
        data['CuerpoWebSite'] = CuerpoWebSiteServicio.objects.get(titulowebsite=t)
    except CuerpoWebSiteServicio.DoesNotExist:
        data['CuerpoWebSite'] = ''
    data['img_header'] = t.get_fondo() if t and t.publicado else fondo
    depservicio = data['gruposervicio']
    search, filtro, url_vars = request.GET.get('s', ''), Q(status=True, publicado=True), f'&sistema={gruposervicio.tiposistema}&action={action}'
    if search:
        data['s'] = search
        url_vars += f'&s={search}'
        filtro = filtro & Q(titulo__icontains=search) | Q(subtitulo__icontains=search)
    listado = NoticiasVinculacion.objects.filter(filtro, departamentoservicio=depservicio,tipopuplicacion=1).order_by('-principal', 'fecha_creacion')
    paging = MiPaginador(listado, 9)
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
    data['totcount'] = listado.count()
    return 'serviciosvinculacion/noticiasvin.html', data

def noticia(data, request=None):
    noticia_id = encrypt_id(request.GET['id'])
    noticia = NoticiasVinculacion.objects.get(id=noticia_id)

    # Set the common fields
    data['noticia'] = noticia
    data['title'] = u'Noticias'
    data['subtitle'] = u'Conoce la información más relevante de nuestros servicios.'
    # data['title'] = f'{noticia.titulo}'
    # data['subtitle'] = f'{noticia.subtitulo}'
    data['viewactivo'] = 'noticias'

    # Retrieve the title and body web site information, similar to the 'noticias' function
    gruposervicio = data['gruposervicio']
    site = gruposervicio.id
    tituloweb = TituloWebSiteServicio.objects.filter(status=True, seccion=3, departamentoservicio__id=site).first()

    try:
        data['CuerpoWebSite'] = CuerpoWebSiteServicio.objects.get(titulowebsite=tituloweb)
    except CuerpoWebSiteServicio.DoesNotExist:
        data['CuerpoWebSite'] = ''

    # Set the image header
    data['img_header'] = tituloweb.get_fondo() if tituloweb and tituloweb.publicado else noticia.get_fondo()

    return 'serviciosvinculacion/noticiavin.html', data

def eventos(data, request=None, depservicio=None):
    action = data['action']
    gruposervicio = data['gruposervicio']
    site = gruposervicio.id
    data['viewactivo'] = 'eventos'
    data['title'] = u'Eventos Informativos'
    data['subtitle'] = u'"Conoce los eventos mas relevantes de nuestros servicios."'
    data['tituloweb'] = t = TituloWebSiteServicio.objects.filter(status=True, seccion=4, departamentoservicio__id=site).first()
    try:
        data['CuerpoWebSite'] = CuerpoWebSiteServicio.objects.get(titulowebsite=t)
    except CuerpoWebSiteServicio.DoesNotExist:
        data['CuerpoWebSite'] = ''
    data['img_header'] = t.get_fondo() if t and t.publicado else fondo
    depservicio = data['gruposervicio']
    search, filtro, url_vars = request.GET.get('s', ''), Q(status=True, publicado=True), f'&sistema={gruposervicio.tiposistema}&action={action}'
    if search:
        data['s'] = search
        url_vars += f'&s={search}'
        filtro = filtro & Q(titulo__icontains=search) | Q(subtitulo__icontains=search)
    listado = NoticiasVinculacion.objects.filter(filtro, departamentoservicio=depservicio,tipopuplicacion=3).order_by('-principal', '-fecha_creacion')
    paging = MiPaginador(listado, 9)
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
    data['totcount'] = listado.count()
    return 'serviciosvinculacion/eventosvin.html', data

def evento(data, request=None):
    noticia_id = encrypt_id(request.GET['id'])
    noticia = NoticiasVinculacion.objects.get(id=noticia_id)

    # Set the common fields
    data['noticia'] = noticia
    data['title'] = u'Eventos Informativos'
    data['subtitle'] = u'Conoce los eventos relevantes de los servicios'
    # data['title'] = f'{noticia.titulo}'
    # data['subtitle'] = f'{noticia.subtitulo}'
    data['viewactivo'] = 'evento'
    # Retrieve the title and body web site information, similar to the 'noticias' function
    gruposervicio = data['gruposervicio']
    site = gruposervicio.id
    tituloweb = TituloWebSiteServicio.objects.filter(status=True, seccion=4, departamentoservicio__id=site).first()

    # Set the image header
    data['img_header'] = tituloweb.get_fondo() if tituloweb and tituloweb.publicado else noticia.get_fondo()
    return 'serviciosvinculacion/eventovin.html', data


def acercanosotros(data, request=None):
    gruposervicio = data['gruposervicio']
    site = gruposervicio.id
    data['viewactivo'] = 'acercanosotros'
    data['title'] = u'Acerca de Nosotros'
    data['subtitle'] = u'¡Quienes Somos!'
    data['tituloweb'] = t = TituloWebSiteServicio.objects.filter(status=True, seccion=1, departamentoservicio__id = site).first()
    try:
        data['CuerpoWebSite'] = CuerpoWebSiteServicio.objects.filter(titulowebsite=t).first()
    except CuerpoWebSiteServicio.DoesNotExist:
        data['CuerpoWebSite'] = ''
    data['img_header'] = t.get_fondo() if t and t.publicado else fondo
    # data['servicios'] = ServicioCita.objects.filter(status=True, departamentoservicio__id = site).order_by('nombre')
    return 'serviciosvinculacion/acercanosotros.html', data


def terminosvin(data, request=None):
    data['viewactivo'] = 'terminovin'
    hoy = datetime.now().date()
    terminosvin = TerminosCondicion.objects.filter(status=True, mostrar=True).order_by('id')
    data['terminovin'] = terminosvin
    data['title'] = 'Términos y Condiciones'

    context = {
        'pagesize': 'A4',
        'data': {
            'hoy': hoy,
            'terminovin': terminosvin
        }
    }
    return conviert_html_to_2pdf('serviciosvinculacion/politicasvin.html', context)

def serviciosvinculacion(data, request=None):
    gruposervicio = data['gruposervicio']
    site = gruposervicio.id
    data['viewactivo'] = 'servicios'
    data['title'] = u'Nuestros Servicios'
    data['subtitle'] = u'¡Conoce nuestros servicios!'
    data['tituloweb'] = t = TituloWebSiteServicio.objects.filter(status=True, seccion=2, departamentoservicio_id=site).first()
    # data['CuerpoWebSite'] = CuerpoWebSiteServicio.objects.get(titulowebsite=t)
    data['img_header'] = t.get_fondo() if t and t.publicado else fondo
    data['servicios'] = ServicioCita.objects.filter(status=True, departamentoservicio_id=site,mostrar=True ).order_by('nombre')
    return 'serviciosvinculacion/servicios_agenda.html', data


def servicio(data, request=None):
    data['servicio'] = servicio = ServicioCita.objects.get(id=encrypt_id(request.GET['id']))
    # motivos_cita = servicio.motivos.all()

    data['title'] = f'{servicio}'
    data['subtitle'] = u'¡Conoce nuestros servicios!'
    data['img_header'] = servicio.get_fondo()
    data['viewactivo'] = 'areas'
    # data['motivos_cita'] = motivos_cita
    return 'serviciosvinculacion/servicios_agenda.html', data

def informacionservicio(data, request=None):
    # Obtener el valor del id del servicio
    idservicio = int(encrypt(request.GET.get('idp')))
    gruposervicio = data['gruposervicio']
    site = gruposervicio.id
    data['viewactivo'] = 'servicios'
    data['title'] = u'Nuestros Servicios'
    data['subtitle'] = u'¡Conoce nuestros servicios!'
    data['tituloweb'] = t = TituloWebSiteServicio.objects.filter(status=True, seccion=2, departamentoservicio__id=site).first()
    data['img_header'] = t.get_fondo() if t and t.publicado else fondo
    servicio = ServicioCita.objects.get(status=True, id=idservicio)
    data['servicios'] = servicio

    # Verificar si el servicio tiene una configuración activa para agendar citas
    tiene_planificacion = ServicioConfigurado.objects.filter(serviciocita=servicio, mostrar=True, status=True).exists()
    data['tiene_planificacion'] = tiene_planificacion

    # Verificar si el servicio es "Unemi Empleo"
    if servicio.gestion_servicio == 1:  # Corresponde a "Unemi Empleo"
        hoy = timezone.now().date()
        nDays = 7  # Número de días para calcular los registros recientes
        lastNDays = hoy - timedelta(nDays)

        # Empresas registradas
        cEmpresas = Empleador.objects.filter(solicitudaprobacionempresa__estadoempresa=1, status=True)
        data['numempresas'] = {
            'count': cEmpresas.count(),
            'last_records': cEmpresas.filter(fecha_creacion__gte=lastNDays).count()
        }

        # Ofertas laborales
        cOfertas = OfertaLaboralEmpresa.objects.filter(empresa__solicitudaprobacionempresa__estadoempresa=1,
                                                       empresa__status=True, estadooferta=1, status=True)
        data['numofertas'] = {
            'count': cOfertas.count(),
            'last_records': cOfertas.filter(fecha_creacion__gte=lastNDays).count()
        }

        # Ofertas disponibles
        data['numofertasdisp'] = {
            'count': cOfertas.filter(finiciopostulacion__lte=hoy, ffinpostlacion__gte=hoy).count(),
            'last_records': cOfertas.filter(finiciopostulacion__lte=hoy, ffinpostlacion__gte=hoy,
                                            fecha_creacion__gte=lastNDays).count()
        }

        # Postulantes
        cPostulantes = PersonaAplicaOferta.objects.filter(oferta__status=True, oferta__empresa__status=True, status=True)
        data['numpostulantes'] = {
            'count': cPostulantes.count(),
            'last_records': cPostulantes.filter(fecha_creacion__gte=lastNDays).count()
        }

        # Usuarios
        cUsuarios = LogEntryLogin.objects.filter(action_app=7, action_flag=1, action_time__date__lte=hoy)
        data['numusuarios'] = {
            'count': cUsuarios.count(),
            'last_records': cUsuarios.filter(action_time__date__exact=hoy).count()
        }

    # Retornar la plantilla y el contexto
    return 'serviciosvinculacion/serviciodescipcion.html', data

def agendarcita(data, request=None):
    data['title'] = 'Disponibilidad de citas'

    # Validar y obtener el ID del servicio
    try:
        idservicio = int(encrypt(request.GET.get('servicio')))
    except (ValueError, KeyError, TypeError):
        data['error'] = "El servicio seleccionado no es válido."
        return 'error_page.html', data

    # Obtener el servicio correspondiente
    try:
        servicio = ServicioCita.objects.get(id=idservicio)
    except ServicioCita.DoesNotExist:
        data['error'] = "El servicio solicitado no se encontró."
        return 'error_page.html', data

    departamento = servicio.departamentoservicio
    data['subtitle'] = f'Selecciona un día y una hora disponible para tu cita en {servicio.nombre.title()}'
    data['listadomotivo'] = MotivoCita.objects.filter(status=True, departamentoservicio=departamento)

    # Obtener términos y condiciones
    termino = TerminosCondicion.objects.filter(servicio=servicio, mostrar=True, status=True).first()
    data['termino'] = termino

    # Obtener el fondo del servicio
    data['img_header'] = servicio.get_portada()

    # Procesar datos del formulario si se ha enviado
    if request.method == 'POST':
        motivo_seleccionado = request.POST.get('motivos_cita')
        descripcion_motivo = request.POST.get('descripcionmotivo', '')

        if motivo_seleccionado == 'otro':
            # Crear un nuevo motivo si se seleccionó "Otro" y guardar la descripción
            motivo_cita = MotivoCita.objects.create(
                descripcion=descripcion_motivo,
                status=True,  # Asumiendo que el nuevo motivo está activo por defecto
                departamentoservicio=departamento
            )
        else:
            try:
                motivo_cita = MotivoCita.objects.get(id=int(motivo_seleccionado))
            except (ValueError, MotivoCita.DoesNotExist):
                data['error'] = "El motivo seleccionado no es válido."
                return 'error_page.html', data

        # Aquí puedes guardar la cita o realizar otras acciones con `motivo_cita`

    return 'serviciosvinculacion/agendamiento_cita.html', data

def inicio(data, request=None):
    data['title'] = u'Servicios Vinculación'
    depservicio = data['gruposervicio']
    servicios = ServicioCita.objects.filter(mostrar=True, departamentoservicio = depservicio).order_by('nombre')[:5]
    data['img_header'] = fondo
    data['responsables'] = ResponsableGrupoServicio.objects.filter(status=True, departamentoservicio = depservicio, activo=True)[:7]
    data['noticias'] = NoticiasVinculacion.objects.filter(status=True, publicado=True, principal=True, departamentoservicio = depservicio)
    data['noticiasgenerales'] = NoticiasVinculacion.objects.filter(status=True, publicado=True, principal=False,
                                                          departamentoservicio=depservicio,tipopuplicacion=1)
    data['servicios'] = servicios
    card = CardInformativo.objects.filter(departamentoservicio=depservicio)
    if card.exists():
        data['cardInformativo'] = card.latest('id')
    return "serviciosvinculacion/view.html", data


