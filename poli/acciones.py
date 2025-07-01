from django.db.models import Q

from poli.models import ActividadPolideportivo, AreaPolideportivo, InstructorPolideportivo, PoliticaPolideportivo, TituloWebSite, NoticiaDeportiva, PlanificacionActividad
from sagest.funciones import encrypt_id
from sga.funciones import MiPaginador
from sga.models import DIAS_CHOICES
from utils.filtros_genericos import filtro_persona

fondo = '/static/images/polideportivo/escuelasformativas.png'

def get_cabeceras(seccion):
    t = TituloWebSite.objects.filter(status=True, seccion=seccion).first()
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
        title = 'Noticias Deportivas'
        subtitle = '¡Conoce todas las noticias ocurridas en Unemi Deporte!'
    elif seccion == 5:
        title = 'Nuestros Logros'
        subtitle = '¡Conoce nuestros Logros!'
    elif seccion == 6:
        title = 'Nuestro Equipo'
        subtitle = '¡Conoce a nuestro Instructores de las diferentes actividades que disponemos!'

    return title, subtitle, t, imagen

def instructor(data, request=None):
    data['title'] = u'Nuestro Equipo'
    data['subtitle'] = u'¡"Conoce a nuestro Instructores de las diferentes disciplinas y formativas disponibles."!'
    data['tituloweb'] = t = TituloWebSite.objects.filter(status=True, seccion=6).first()
    data['img_header'] = t.get_fondo() if t and t.publicado else fondo
    data['viewactivo'] = 'instructores'
    data['instructor'] = InstructorPolideportivo.objects.get(id=encrypt_id(request.GET['id']))
    return 'unemideporte/instructor.html', data

def instructores(data, request=None):
    action = data['action']
    data['viewactivo'] = 'instructores'
    data['title'] = u'Nuestro Equipo'
    data['subtitle'] = u'¡"Conoce a nuestro Instructores de las diferentes actividades que disponemos."!'
    data['tituloweb'] = t = TituloWebSite.objects.filter(status=True, seccion=6).first()
    data['img_header'] = t.get_fondo() if t and t.publicado else fondo
    data['instructores'] = InstructorPolideportivo.objects.filter(status=True)
    search, filtro, url_vars = request.GET.get('s', ''), Q(status=True), f'&action={action}'
    if search:
        data['s'] = search
        url_vars += f'&s={search}'
        filtro = filtro_persona(search, filtro)
    listado = InstructorPolideportivo.objects.filter(filtro).order_by('-id')
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
    return 'unemideporte/instructores.html', data

def noticias(data, request=None):
    action = data['action']
    data['viewactivo'] = 'noticias'
    data['title'] = u'Noticias deportivas'
    data['subtitle'] = u'¡"Conoce las noticias mas relevantes del deporte."!'
    data['tituloweb'] = t = TituloWebSite.objects.filter(status=True, seccion=4).first()
    data['img_header'] = t.get_fondo() if t and t.publicado else fondo
    search, filtro, url_vars = request.GET.get('s', ''), Q(status=True, publicado=True), f'&action={action}'
    if search:
        data['s'] = search
        url_vars += f'&s={search}'
        filtro = filtro & Q(titulo__icontains=search) | Q(subtitulo__icontains=search)
    listado = NoticiaDeportiva.objects.filter(filtro).order_by('-principal', 'fecha_creacion')
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
    return 'unemideporte/noticias.html', data

def noticia(data, request=None):
    data['noticia'] = noticia = NoticiaDeportiva.objects.get(id=encrypt_id(request.GET['id']))
    data['title'] = f'{noticia.titulo}'
    data['subtitle'] = f'{noticia.subtitulo}'
    data['img_header'] = noticia.get_fondo()
    data['viewactivo'] = 'noticias'
    return 'unemideporte/noticia.html', data

def areas(data, request=None):
    data['viewactivo'] = 'areas'
    data['title'] = u'Nuestros Espacios Deportivos'
    data['subtitle'] = u'¡Conoce nuestros Espacios Deportivos!'
    data['tituloweb'] = t = TituloWebSite.objects.filter(status=True, seccion=2).first()
    data['img_header'] = t.get_fondo() if t and t.publicado else fondo
    data['areas'] = AreaPolideportivo.objects.filter(status=True).order_by('nombre')
    return 'unemideporte/espaciosdeportivos.html', data

def area(data, request=None):
    data['area'] = area = AreaPolideportivo.objects.get(id=encrypt_id(request.GET['id']))
    data['title'] = f'{area}'
    data['subtitle'] = u'¡Conoce nuestros Espacios Deportivo!'
    data['img_header'] = area.get_fondo()
    data['viewactivo'] = 'areas'
    return 'unemideporte/espaciodeportivo.html', data

def politicas(data, request=None):
    data['viewactivo'] = 'politicas'
    data['title'] = u'Políticas'
    data['politicas'] = PoliticaPolideportivo.objects.filter(status=True, mostrar=True).order_by('id')
    return 'politicaspolideportivo.html', data

def actividades(data, request=None):
    tipo = int(request.GET.get('type_act', 0))
    if tipo == 0:
        raise NameError('Sin parametros requeridos')
    if tipo == 2:
        seccion=1
        data['title'] = u'Nuestras Escuelas Formativas'
        data['subtitle'] = u'¡Conoce nuestras Escuelas Formativas!'
        data['viewactivo'] = 'formativas'
    else:
        seccion = 3
        data['title'] = u'Nuestras Vacacionales'
        data['subtitle'] = u'¡Conoce nuestras vacacionales!'
        data['viewactivo'] = 'vacacionales'
    data['tituloweb'] = t = TituloWebSite.objects.filter(status=True, seccion=seccion).first()
    data['img_header'] = t.get_fondo() if t and t.publicado else fondo
    data['planificaciones'] = PlanificacionActividad.objects.filter(status=True,
                                                               actividad__status=True,
                                                               actividad__mostrar=True,
                                                               actividad__tipoactividad=tipo,
                                                               activo=True).order_by('actividad_id').distinct()
    return 'unemideporte/actividades_paga.html', data

def actividad(data, request=None):
    data['planificacion'] = planificacion = PlanificacionActividad.objects.get(id=encrypt_id(request.GET['id']))
    data['actividad'] = actividad = planificacion.actividad
    data['title'] = f'{planificacion.actividad.nombre.capitalize()}'
    data['img_header'] = planificacion.actividad.get_portada()
    if actividad.tipoactividad == 2:
        data['viewactivo'] = 'formativas'
        data['subtitle'] = u'Escuela Formativa'
    else:
        data['viewactivo'] = 'vacacionales'
        data['subtitle'] = u'Vacacionales'
    data['turnos'] = planificacion.turnos_disponibles()
    data['semana'] = DIAS_CHOICES[:planificacion.tope_dias()]
    # data['formativas'] = PlanificacionActividad.objects.filter(status=True,
    #                                                            actividad__status=True,
    #                                                            actividad__mostrar=True,
    #                                                            actividad__tipoactividad=2,
    #                                                            activo=True).order_by('actividad_id').distinct()
    return 'unemideporte/actividad_paga.html', data

def view_inicio(data, request=None):
    data['title'] = u'Unemi Deporte'
    areas = AreaPolideportivo.objects.filter(status=True).order_by('nombre')[:6]
    data['img_header'] = fondo
    data['instructores'] = InstructorPolideportivo.objects.filter(status=True)[:6]
    data['formativas'] = PlanificacionActividad.objects.filter(status=True,
                                                               actividad__status=True,
                                                               actividad__mostrar=True,
                                                               actividad__tipoactividad=2,
                                                               activo=True).order_by('actividad_id').distinct()
    data['noticias'] = NoticiaDeportiva.objects.filter(status=True, publicado=True, principal=True)
    data['areas'] = areas
    return "unemideporte/view.html", data