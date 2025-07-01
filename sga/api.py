# -*- coding: latin-1 -*-
import json
from datetime import datetime, timedelta
import string
from django.contrib.auth import logout
from django.contrib.auth import authenticate
from django.db import connection, transaction
from django.db.models import Q
from django.forms.models import model_to_dict
from django.http import JsonResponse, HttpResponse
from django.template.loader import get_template

from helpdesk.models import HdBien
from inno.models import FechaPlanificacionSedeVirtualExamen, TurnoPlanificacionSedeVirtualExamen, \
    AulaPlanificacionSedeVirtualExamen, MateriaAsignadaPlanificacionSedeVirtualExamen
from investigacion.models import ProyectoInvestigacionCronogramaActividad
from med.models import Vacuna, Enfermedad, Alergia, Medicina, Cirugia, LugarAnatomico, Droga, MetodoAnticonceptivo, \
    Lesiones, AccionConsulta, PatologicoPersonal, Habito, PatologicoQuirurgicos
from sagest.funciones import carreras_departamento
from sagest.models import Departamento, IndicadorPoa, ObjetivoOperativo, Rubro, DistributivoPersona, Ubicacion
from settings import TIEMPO_CIERRE_SESION
from sga.funciones import variable_valor, salvaRubros, MiPaginador, validarcedula
from sga.models import Aula, Carrera, PreInscrito, Periodo, Pais, Provincia, Canton, \
    AreaConocimientoTitulacion, SubAreaConocimientoTitulacion, Persona, Coordinacion, Profesor, ProyectosInvestigacion, \
    ArticuloInvestigacion, PonenciasInvestigacion, LibroInvestigacion, CapituloLibroInvestigacion, MateriaAsignada, \
    DetalleSilaboSemanalBibliografia, DetalleSilaboSemanalBibliografiaDocente, LibroKohaProgramaAnaliticoAsignatura, \
    TipoEstado, VisitasBiblioteca, AreaProgramasInvestigacion, ActividadesMundoCrai, Inscripcion, Matricula, Clase, \
    Sesion, Turno, AlumnosPracticaMateria, ProfesorDistributivoHoras, ComplexivoClase, PerfilInscripcion, \
    PreferenciaDetalleActividadesCriterio, InstitucionBeca, RevistaInvestigacion, SubLineaInvestigacion, \
    ProyectoInvestigacionExterno, ItinerariosMalla, SubAreaEspecificaConocimientoTitulacion, Asignatura, FotoPersona, \
    ParticipantesArticulos, BaseIndexadaInvestigacion, RevistaInvestigacionBase, SedeVirtual, Titulo, Titulacion
from sga.funcionesxhtml2pdf import conviert_html_to_pdf
from sga.templatetags.sga_extras import encrypt
from socioecon.models import ProveedorServicio
from django.db.models import Q, Case, When, Value, CharField, Func, F, Sum, Count, Max, FloatField
from django.db.models.functions import Coalesce, Concat

from utils.filtros_genericos import filtro_persona_select, consultarPersona

unicode = str

@transaction.atomic()
def view(request):
    if request.method == 'POST':
        if 'a' in request.POST:
            action = request.POST['a']

            if action == 'subareaconocimiento':
                try:
                    area = AreaConocimientoTitulacion.objects.get(pk=request.POST['id'])
                    lista = []
                    for subarea in SubAreaConocimientoTitulacion.objects.filter(areaconocimiento=area, status=True, tipo=1, vigente=True):
                        lista.append([subarea.id, '[' + subarea.codigo + '] - ' + subarea.nombre])
                    return JsonResponse({'result': 'ok', 'lista': lista})
                except Exception as ex:
                    return JsonResponse({"result": "bad", "mensaje": u"Error al obtener los datos."})

            # if action == 'solicitudes':
            #     try:
            #         idsolicitud = SolicitudProblemas.objects.values_list('tipolsolicitud__id', flat=True).filter(status=True, inscripcion_id=request.POST['idinscripcion']).exclude(estado=4)
            #         tipos = TipolSolicitud.objects.filter(status=True, tipo=request.POST['id']).exclude(id__in=idsolicitud).order_by('-id')
            #         lista = []
            #         for t in tipos:
            #             lista.append([t.id, t.descripcion])
            #         return JsonResponse({'result': 'ok', 'lista': lista})
            #     except Exception as ex:
            #         return JsonResponse({"result": "bad", "mensaje": u"Error al obtener los datos."})

            elif action == 'subareaconocimiento1':
                try:
                    subareas = AreaProgramasInvestigacion.objects.values_list('subareaconocimiento__id', flat=True).filter(status=True, programasinvestigacion__id=request.POST['idp']).order_by('-id').distinct()
                    area = AreaConocimientoTitulacion.objects.get(pk=request.POST['id'])
                    lista = []
                    for subarea in SubAreaConocimientoTitulacion.objects.filter(areaconocimiento=area,status=True,id__in=subareas, tipo=1):
                        lista.append([subarea.id, subarea.nombre])
                    return JsonResponse({'result': 'ok', 'lista': lista})
                except Exception as ex:
                    return JsonResponse({"result": "bad", "mensaje": u"Error al obtener los datos."})

            elif action == 'subareaespecificaconocimiento':
                try:
                    area = SubAreaConocimientoTitulacion.objects.get(pk=request.POST['id'])
                    lista = []
                    for subarea in SubAreaEspecificaConocimientoTitulacion.objects.filter(status=True, areaconocimiento=area, tipo=1, vigente=True):
                        lista.append([subarea.id, '[' + subarea.codigo + '] - ' + subarea.nombre])
                    return JsonResponse({'result': 'ok', 'lista': lista})
                except Exception as ex:
                    return JsonResponse({"result": "bad", "mensaje": u"Error al obtener los datos."})

            elif action == 'subareaespecificaconocimiento1':
                try:
                    subareaespecificas = AreaProgramasInvestigacion.objects.values_list('subareaespecificaconocimiento__id', flat=True).filter(status=True,programasinvestigacion__id=request.POST['idp']).order_by('-id').distinct()
                    area = SubAreaConocimientoTitulacion.objects.get(pk=request.POST['id'])
                    lista = []
                    for subarea in SubAreaEspecificaConocimientoTitulacion.objects.filter(status=True,areaconocimiento=area,id__in=subareaespecificas, tipo=1):
                        lista.append([subarea.id, subarea.nombre])
                    return JsonResponse({'result': 'ok', 'lista': lista})
                except Exception as ex:
                    return JsonResponse({"result": "bad", "mensaje": u"Error al obtener los datos."})

            elif action == 'itinerariomalla':
                try:
                    lista = []
                    for itinerario in ItinerariosMalla.objects.filter(status=True, malla__carrera_id=request.POST['idc']).order_by('nivel__orden'):
                        lista.append([itinerario.id, str(itinerario)])
                    return JsonResponse({'result': 'ok', 'lista': lista})
                except Exception as ex:
                    return JsonResponse({"result": "bad", "mensaje": u"Error al obtener los datos."})

            elif action == 'datosrevista':
                try:
                    revista = RevistaInvestigacion.objects.get(pk=int(request.POST['id']))
                    enlace = revista.enlace

                    baseindexada = ",".join([base.baseindexada.nombre for base in revista.revistainvestigacionbase_set.filter(status=True).order_by('baseindexada__nombre')])

                    if baseindexada:
                        if revista.tiporegistro == 1:
                            categoriaid = revista.basesindexadascategoria()[0].baseindexada.categoria.id
                            categorianombre = revista.basesindexadascategoria()[0].baseindexada.categoria.nombre
                        else:
                            categoriaid = 5
                            categorianombre = "PROCEEDING"

                        tienebasescielo = "S" if revista.revistainvestigacionbase_set.filter(status=True, baseindexada_id=9).exists() else "N"
                    else:
                        if revista.tiporegistro == 1:
                            categoriaid = -1
                            categorianombre = ""
                        else:
                            categoriaid = 5
                            categorianombre = "PROCEEDING"

                        tienebasescielo = "N"

                    return JsonResponse({'result': 'ok', 'enlace': enlace, 'baseindexada': baseindexada, 'categoriaid': categoriaid, 'categorianombre': categorianombre, 'tienebasescielo': tienebasescielo})
                except Exception as ex:
                    return JsonResponse({"result": "bad", "mensaje": u"Error al obtener los datos."})

            elif action == 'consultapersonacedula':
                try:
                    if Persona.objects.filter(cedula=request.POST['cedula']).exists():
                        return JsonResponse({'result': 'ok', 'existe': 'SI'})
                    else:
                        return JsonResponse({'result': 'ok', 'existe': 'NO'})

                except Exception as ex:
                    return JsonResponse({"result": "bad", "mensaje": u"Error al obtener los datos."})

            elif action == 'revistas':
                try:
                    tiporegistro = int(request.POST['tiporegistro'])
                    # revistas = RevistaInvestigacion.objects.filter(status=True, tiporegistro=tiporegistro, borrador=False).order_by('nombre')
                    revistas = RevistaInvestigacion.objects.filter(status=True, tiporegistro=tiporegistro).order_by('nombre')
                    lista = [[revista.id, revista.nombre] for revista in revistas]
                    return JsonResponse({'result': 'ok', 'lista': lista})
                except Exception as ex:
                    return JsonResponse({"result": "bad", "mensaje": u"Error al obtener los datos."})

            elif action == 'proveedorinternet':
                try:
                    proveedores = ProveedorServicio.objects.filter(status=True, tiposervicio=1).order_by('nombre')
                    lista = [[proveedor.id, proveedor.nombre] for proveedor in proveedores]
                    return JsonResponse({'result': 'ok', 'lista': lista})
                except Exception as ex:
                    return JsonResponse({"result": "bad", "mensaje": u"Error al obtener los datos."})

            elif action == 'sublineainvestigacion':
                try:
                    sublineas = SubLineaInvestigacion.objects.filter(lineainvestigacion=int(request.POST['id']), status=True).order_by('nombre')
                    lista = [[sublinea.id, sublinea.nombre] for sublinea in sublineas]
                    return JsonResponse({'result': 'ok', 'lista': lista})
                except Exception as ex:
                    return JsonResponse({"result": "bad", "mensaje": u"Error al obtener los datos."})

            elif action == 'actividadobjetivoespecifico':
                try:
                    actividades = ProyectoInvestigacionCronogramaActividad.objects.filter(status=True, estado__in=[1, 2, 4], objetivo__id=int(request.POST['id'])).order_by('fechainicio', 'fechafin')
                    lista = [[actividad.id, actividad.actividad] for actividad in actividades]
                    return JsonResponse({'result': 'ok', 'lista': lista})
                except Exception as ex:
                    return JsonResponse({"result": "bad", "mensaje": u"Error al obtener los datos."})

            elif action == 'areaconocimientotitulopersona':
                try:
                    titulo = Titulacion.objects.get(pk=int(request.POST['id'])).titulo
                    idarea = titulo.areaconocimiento.id if titulo.areaconocimiento else 0
                    nombrearea = titulo.areaconocimiento.nombre if titulo.areaconocimiento else ''
                    return JsonResponse({'result': 'ok', 'idarea': idarea, 'nombrearea': nombrearea})
                except Exception as ex:
                    return JsonResponse({"result": "bad", "mensaje": u"Error al obtener los datos."})

            elif action == 'proyectoinvestigacion':
                try:
                    tipoproyecto = int(request.POST['tipo'])
                    if tipoproyecto != 3:
                        proyectos = ProyectosInvestigacion.objects.filter(status=True, aprobacion=1, tipo=tipoproyecto).order_by('nombre')
                    else:
                        proyectos = ProyectoInvestigacionExterno.objects.filter(status=True).order_by('nombre')

                    lista = [[proyecto.id, proyecto.nombre] for proyecto in proyectos]
                    return JsonResponse({'result': 'ok', 'lista': lista})
                except Exception as ex:
                    return JsonResponse({"result": "bad", "mensaje": u"Error al obtener los datos."})

            elif action == 'profesorcarreraperiodo':
                try:
                    carrera = int(request.POST['idc'])
                    periodo = int(request.POST['idp'])

                    profesores = Profesor.objects.filter(status=True, profesordistributivohoras__status=True, profesordistributivohoras__periodo_id=periodo, profesordistributivohoras__carrera_id=carrera).order_by('persona__apellido1', 'persona__apellido2', 'persona__nombres')

                    lista = [[profesor.id, str(profesor.persona)] for profesor in profesores]
                    return JsonResponse({'result': 'ok', 'lista': lista})
                except Exception as ex:
                    return JsonResponse({"result": "bad", "mensaje": u"Error al obtener los datos."})

            elif action == 'areaconocimiento':
                try:
                    lista = []
                    for area in AreaConocimientoTitulacion.objects.filter(status=True).order_by('nombre'):
                        datosarea = {'id': area.id,
                                     'nombre': area.nombre}
                        lista.append(datosarea)

                    response = HttpResponse(json.dumps({'result': 'ok', 'mensaje': 'Este es un mensaje', 'areasconocimiento': lista}))
                    response.__setitem__("Content-type", "application/json")
                    response.__setitem__("Access-Control-Allow-Origin", "*")
                    return response
                except Exception as ex:
                    response = HttpResponse(json.dumps({'result': 'bad', 'mensaje': 'Error al consultar áreas de conocimiento'}))
                    response.__setitem__("Content-type", "application/json")
                    response.__setitem__("Access-Control-Allow-Origin", "*")
                    return response
                    # return JsonResponse({"result": "bad", "mensaje": u"Error al obtener los datos."})

            elif action == 'acciones':
                try:
                    lista = []
                    accion = AccionConsulta.objects.filter(area=int(request.POST['area']))

                    for a in accion:
                        lista.append([a.id, a.descripcion])
                    return JsonResponse({'result': 'ok', 'lista': lista})
                except Exception as ex:
                    return JsonResponse({"result": "bad", "mensaje": u"Error al obtener los datos."})

            elif action == 'instituciones':
                try:
                    lista = []
                    institucion = InstitucionBeca.objects.filter(status=True)

                    for i in institucion:
                        lista.append([i.id, i.nombre])
                    return JsonResponse({'result': 'ok', 'lista': lista})
                except Exception as ex:
                    return JsonResponse({"result": "bad", "mensaje": u"Error al obtener los datos."})

            elif action == 'carreras':
                try:
                    lista = []
                    facultad = Coordinacion.objects.get(pk=int(request.POST['facultad']))
                    carrera = Carrera.objects.filter(coordinacion=facultad, pk__in=list(request.POST['cc'].split(','))).order_by('nombre')

                    for c in carrera:
                        lista.append([c.id, c.nombre])
                    return JsonResponse({'result': 'ok', 'lista': lista})
                except Exception as ex:
                    return JsonResponse({"result": "bad", "mensaje": u"Error al obtener los datos."})

            elif action == 'carrera_periodo':
                try:
                    lista = []
                    periodo = Periodo.objects.get(pk=int(request.POST['id']))
                    persona = Persona.objects.get(pk=int(request.POST['idpersona']))
                    idcarreras = persona.mis_carreras().values_list('id', flat=True).all()
                    carrera = Carrera.objects.filter(id__in=idcarreras, malla__asignaturamalla__materia__nivel__periodo=periodo, malla__vigente=True, malla__status=True, malla__asignaturamalla__status=True).distinct().order_by('nombre')
                    if not carrera:
                        carrera = Carrera.objects.filter(id__in=idcarreras).distinct().order_by('nombre')
                    for c in carrera:
                        lista.append([c.id, c.nombre])
                    return JsonResponse({'result': 'ok', 'lista': lista})
                except Exception as ex:
                    return JsonResponse({"result": "bad", "mensaje": u"Error al obtener los datos."})

            elif action == 'lesiones':
                try:
                    lista = []
                    tipo = request.POST['tipo']
                    lesion = Lesiones.objects.filter(tipo=tipo)
                    for v in lesion:
                        lista.append([v.id, v.descripcion])
                    return JsonResponse({'result': 'ok', 'lista': lista})
                except Exception as ex:
                    return JsonResponse({"result": "bad", "mensaje": u"Error al obtener los datos."})

            elif action == 'metodos':
                try:
                    lista = []
                    metodo = MetodoAnticonceptivo.objects.all()
                    for v in metodo:
                        lista.append([v.id, v.descripcion])
                    return JsonResponse({'result': 'ok', 'lista': lista})
                except Exception as ex:
                    return JsonResponse({"result": "bad", "mensaje": u"Error al obtener los datos."})

            elif action == 'drogas':
                try:
                    lista = []
                    droga = Droga.objects.all()
                    for v in droga:
                        lista.append([v.id, v.descripcion])
                    return JsonResponse({'result': 'ok', 'lista': lista})
                except Exception as ex:
                    return JsonResponse({"result": "bad", "mensaje": u"Error al obtener los datos."})

            elif action == 'lugaranatomico':
                try:
                    lista = []
                    lugar = LugarAnatomico.objects.all()
                    for v in lugar:
                        lista.append([v.id, v.descripcion])
                    return JsonResponse({'result': 'ok', 'lista': lista})
                except Exception as ex:
                    return JsonResponse({"result": "bad", "mensaje": u"Error al obtener los datos."})

            elif action == 'cirugias':
                try:
                    lista = []
                    cirugias = Cirugia.objects.all()
                    for v in cirugias:
                        lista.append([v.id, v.descripcion])
                    return JsonResponse({'result': 'ok', 'lista': lista})
                except Exception as ex:
                    return JsonResponse({"result": "bad", "mensaje": u"Error al obtener los datos."})

            elif action == 'vacunas':
                try:
                    lista = []
                    vacunas = Vacuna.objects.all()
                    for v in vacunas:
                        lista.append([v.id, v.descripcion])
                    return JsonResponse({'result': 'ok', 'lista': lista})
                except Exception as ex:
                    return JsonResponse({"result": "bad", "mensaje": u"Error al obtener los datos."})

            elif action == 'enfermedades':
                try:
                    tipo = request.POST['tipo']
                    lista = []
                    enfermedad = Enfermedad.objects.filter(tipo=tipo)
                    for v in enfermedad:
                        lista.append([v.id, v.descripcion])
                    return JsonResponse({'result': 'ok', 'lista': lista})
                except Exception as ex:
                    return JsonResponse({"result": "bad", "mensaje": u"Error al obtener los datos."})

            elif action == 'alergias':
                try:
                    tipo = request.POST['tipo']
                    lista = []
                    alergia = Alergia.objects.filter(tipo=tipo)
                    for v in alergia:
                        lista.append([v.id, v.descripcion])
                    return JsonResponse({'result': 'ok', 'lista': lista})
                except Exception as ex:
                    return JsonResponse({"result": "bad", "mensaje": u"Error al obtener los datos."})

            elif action == 'alergiastodas':
                try:
                    lista = []
                    alergia = Alergia.objects.all()
                    for v in alergia:
                        lista.append([v.id, v.descripcion])
                    return JsonResponse({'result': 'ok', 'lista': lista})
                except Exception as ex:
                    return JsonResponse({"result": "bad", "mensaje": u"Error al obtener los datos."})

            elif action == 'medicinas':
                try:
                    lista = []
                    medicina = Medicina.objects.all()
                    for v in medicina:
                        lista.append([v.id, v.descripcion])
                    return JsonResponse({'result': 'ok', 'lista': lista})
                except Exception as ex:
                    return JsonResponse({"result": "bad", "mensaje": u"Error al obtener los datos."})

            elif action == 'paises':
                try:
                    lista = []
                    pais = Pais.objects.filter(status=True).order_by('nombre')
                    for p in pais:
                        lista.append([p.id, p.nombre])
                    return JsonResponse({'result': 'ok', 'lista': lista})
                except Exception as ex:
                    return JsonResponse({"result": "bad", "mensaje": u"Error al obtener los datos."})

            elif action == 'paise_solo_provincias':
                try:
                    lista = []
                    pais = Pais.objects.filter(status=True, provincia__isnull=False).order_by('nombre')
                    for p in pais.distinct():
                        lista.append([p.id, p.nombre])
                    return JsonResponse({'result': 'ok', 'lista': lista})
                except Exception as ex:
                    return JsonResponse({"result": "bad", "mensaje": u"Error al obtener los datos."})

            elif action == 'paises_solo_universidades':
                try:
                    lista = []
                    pais = Pais.objects.filter(status=True, institucioneducacionsuperior__isnull=False).order_by('nombre')
                    for p in pais.distinct():
                        lista.append([p.id, p.nombre])
                    return JsonResponse({'result': 'ok', 'lista': lista})
                except Exception as ex:
                    return JsonResponse({"result": "bad", "mensaje": u"Error al obtener los datos."})

            elif action == 'provincias':
                try:
                    pais = Pais.objects.get(pk=request.POST['id'])
                    lista = []
                    for provincia in pais.provincia_set.all():
                        lista.append([provincia.id, provincia.nombre])
                    return JsonResponse({'result': 'ok', 'lista': lista,'nacionalidad':pais.nacionalidad})
                except Exception as ex:
                    return JsonResponse({"result": "bad", "mensaje": u"Error al obtener los datos."})
            elif action == 'bien':
                try:
                    bien = HdBien.objects.filter(gruposistema=int(request.POST['id']))
                    lista = []
                    for bienes in bien:
                        lista.append([bienes.id, bienes.nombre])
                    return JsonResponse({'result': 'ok', 'lista': lista})
                except Exception as ex:
                    return JsonResponse({"result": "bad", "mensaje": u"Error al obtener los datos."})

            elif action == 'actividadesmundocrai':
                try:
                    actividadesmundocrais = ActividadesMundoCrai.objects.filter(tipomundocrai=int(request.POST['id']),principal=True, status=True).order_by('id')
                    lista = []
                    for actividadesmundocrai in actividadesmundocrais:
                        lista.append([actividadesmundocrai.id, ('%s - Nivel: %s' % (actividadesmundocrai.descripcion,actividadesmundocrai.orden))])
                    return JsonResponse({'result': 'ok', 'lista': lista})
                except Exception as ex:
                    return JsonResponse({"result": "bad", "mensaje": u"Error al obtener los datos."})

            elif action == 'carrerascoordinacion':
                try:
                    facultad = Coordinacion.objects.get(pk=request.POST['id'])
                    lista = []
                    carreras = facultad.carreras()
                    for carrera in carreras:
                        lista.append([carrera.id, carrera.__str__()])
                    return JsonResponse({'result': 'ok', 'lista': lista})
                except Exception as ex:
                    return JsonResponse({"result": "bad", "mensaje": u"Error al obtener los datos."})

            elif action == 'cantones':
                try:
                    provincia = Provincia.objects.get(pk=request.POST['id'])
                    lista = []
                    for canton in provincia.canton_set.all():
                        lista.append([canton.id, canton.nombre])
                    return JsonResponse({'result': 'ok', 'lista': lista})
                except Exception as ex:
                    return JsonResponse({"result": "bad", "mensaje": u"Error al obtener los datos."})

            elif action == 'parroquias':
                try:
                    canton = Canton.objects.get(pk=request.POST['id'])
                    lista = []
                    for parroquia in canton.parroquia_set.all():
                        lista.append([parroquia.id, parroquia.nombre])
                    return JsonResponse({'result': 'ok', 'lista': lista})
                except Exception as ex:
                    return JsonResponse({"result": "bad", "mensaje": u"Error al obtener los datos."})

            elif action == 'objetivooperativo':
                try:
                    departamento = Departamento.objects.get(pk=request.POST['id'])
                    lista = []
                    for objetivooperativo in departamento.objetivos_operativos(request.POST['anio']):
                        lista.append([objetivooperativo.id, objetivooperativo.descripcion])
                    return JsonResponse({'result': 'ok', 'lista': lista})
                except Exception as ex:
                    return JsonResponse({"result": "bad", "mensaje": u"Error al obtener los datos."})

            elif action == 'objetivooperativogeneral':
                try:
                    departamento = Departamento.objects.get(pk=request.POST['id'])
                    lista = []
                    for objetivooperativo in departamento.objetivos_operativosgeneral(request.POST['anio']):
                        lista.append([objetivooperativo.id, objetivooperativo.descripcion])
                    return JsonResponse({'result': 'ok', 'lista': lista})
                except Exception as ex:
                    return JsonResponse({"result": "bad", "mensaje": u"Error al obtener los datos."})

            elif action == 'indicadorpoa':
                try:
                    objetivooperativo = ObjetivoOperativo.objects.get(pk=request.POST['id'])
                    lista = []
                    for indicadorpoa in objetivooperativo.indicadorpoa_set.filter(status=True):
                        lista.append([indicadorpoa.id, indicadorpoa.descripcion])
                    return JsonResponse({'result': 'ok', 'lista': lista})
                except Exception as ex:
                    return JsonResponse({"result": "bad", "mensaje": u"Error al obtener los datos."})

            elif action == 'indicadorperiodo':
                try:
                    anioselect = request.POST['anio']
                    cursor = connection.cursor()
                    sqlperiodo = "select id, nombre, extract(year from inicio) from sga_periodo where status=true and tipo_id=2 and extract(year from inicio)=" + str(anioselect) + " order by inicio"
                    cursor.execute(sqlperiodo)
                    lista = []
                    for periodo in cursor.fetchall():
                        lista.append([int(periodo[0]), periodo[1]])
                    return JsonResponse({'result': 'ok', 'lista': lista})
                except Exception as ex:
                    return JsonResponse({"result": "bad", "mensaje": u"Error al obtener los datos."})

            elif action == 'acciondocumento':
                try:
                    indicadorpoa = IndicadorPoa.objects.get(pk=request.POST['id'])
                    lista = []
                    for acciondocumento in indicadorpoa.acciondocumento_set.filter(status=True):
                        lista.append([acciondocumento.id, acciondocumento.descripcion])
                    return JsonResponse({'result': 'ok', 'lista': lista})
                except Exception as ex:
                    return JsonResponse({"result": "bad", "mensaje": u"Error al obtener los datos."})

            elif action == 'profesormateria':
                try:
                    profesores = Profesor.objects.filter(profesormateria__materia__nivel__periodo_id=request.POST['idperiodo']).distinct().order_by('persona__apellido1','persona__apellido2')
                    lista = []
                    for profesor in profesores:
                        lista.append([profesor.id, profesor.persona.nombre_completo_inverso()])
                    return JsonResponse({'result': 'ok', 'lista': lista})
                except Exception as ex:
                    return JsonResponse({"result": "bad", "mensaje": u"Error al obtener los datos."})

            elif action == 'secciones':
                try:
                    departamento = Departamento.objects.get(pk=request.POST['id'])
                    departamento = Departamento.objects.get(pk=request.POST['id'])
                    lista = []
                    for seccion in departamento.secciondepartamento_set.all():
                        lista.append([seccion.id, seccion.descripcion])
                    return JsonResponse({'result': 'ok', 'lista': lista})
                except Exception as ex:
                    return JsonResponse({"result": "bad", "mensaje": u"Error al obtener los datos."})

            elif action == 'checkmail':
                try:
                    if 'persona' in request.session:
                        persona = request.session['persona']
                        return JsonResponse({'result': 'ok', 'mensajes': persona.tiene_mensajes()})
                    else:
                        raise NameError('Error')
                except Exception as ex:
                    return JsonResponse({"result": "bad", "mensaje": u"Error al obtener los datos."})

            elif action == 'checksession':
                from datetime import datetime,timedelta
                try:
                    if 'ultimo_acceso' in request.session:
                        fa = request.session['ultimo_acceso']
                    else:
                        request.session['ultimo_acceso'] = fa = datetime.now()
                    nuevasesion = False
                    if TIEMPO_CIERRE_SESION:
                        if (fa + timedelta(seconds=TIEMPO_CIERRE_SESION)) < datetime.now():
                            nuevasesion = True
                    return JsonResponse({'result': 'ok', 'nuevasesion': nuevasesion})
                except Exception as ex:
                    return JsonResponse({"result": "bad", "mensaje": u"Error al obtener los datos."})

            elif action == 'logout':
                try:
                    if 'tiposistema' in request.session:
                        tipo = request.session['tiposistema']
                        if tipo == 'sga':
                            urlreturn = '/loginsga'
                        else:
                            if tipo == 'posgrado':
                                urlreturn = '/loginposgrado'
                            else:
                                if tipo == 'seleccionposgrado':
                                    urlreturn = '/loginpostulacion'
                                elif tipo == 'postulate':
                                    urlreturn = '/loginpostulate'
                                elif tipo == 'empleo':
                                    urlreturn = '/loginempleo'
                                elif tipo == 'empresa':
                                    urlreturn = '/empresa/loginempresa'
                                else:
                                    urlreturn = '/loginsagest'
                        logout(request)
                        return JsonResponse({'result': 'ok', 'url': urlreturn})
                    else:
                        logout(request)
                        return JsonResponse({'result': 'ok', 'url': '/loginsga'})
                except Exception as ex:
                    return JsonResponse({"result": "bad", "mensaje": u"Error al cerrar session."})

            elif action == 'uprubrounemi':
                try:
                    lista_jsondoc = {}
                    sal = '04m76#5&*fg8^6677d8lv0+2t$hkjw=8emvaed(an118!y6a'
                    idrubro = int(encrypt(request.POST['irubro']))
                    if request.POST['tk'] == '%s%s' % (sal, request.POST['irubro']):
                        with transaction.atomic():
                            if Rubro.objects.filter(pk=idrubro).exists():
                                # qs_anterior = list(Rubro.objects.filter(pk=idrubro).values())
                                rubro = Rubro.objects.get(pk=idrubro)
                                rubro.save()
                                # GUARDA AUDITORIA
                                # qs_nuevo = list(Rubro.objects.filter(pk=rubro.id).values())
                                # salvaRubros(request, rubro, action,
                                #             qs_anterior=qs_anterior,
                                #             qs_nuevo=qs_nuevo)
                                # GUARDA AUDITORIA
                        lista_jsondoc['result'] = 'ok'
                    else:
                        lista_jsondoc['result'] = 'bad'
                    response = HttpResponse(json.dumps(lista_jsondoc))
                    response.__setitem__("Content-type", "application/json")
                    # response.__setitem__("Access-Control-Allow-Origin", "http://127.0.0.1:8000")
                    response.__setitem__("Access-Control-Allow-Origin", "https://sagest.epunemi.gob.ec")
                    return response
                except Exception as ex:
                    return JsonResponse({'result': 'bad', "mensaje": u"Error al obtener los datos de pre-inscripcion"})


        return JsonResponse(['ACADEMIC-OK', 'OKSOFTWR S.A. (C) Todos los derechos reservados'])
    else:
        if 'a' in request.GET:
            action = request.GET['a']

            if action == 'buscarpreinscripcion':
                try:
                    if PreInscrito.objects.filter(cedula=request.GET['ced']).exists():
                        preinscrito = PreInscrito.objects.filter(cedula=request.GET['ced'])[0]
                        return JsonResponse({'result': 'ok', 'preinscrito': unicode(preinscrito), 'preinscrito_id': preinscrito.id})
                    return JsonResponse({'result': 'no-data'})
                except Exception as ex:
                    return JsonResponse({'result': 'bad', "mensaje": u"Error al obtener los datos de pre-inscripcion"})

            # if action == 'apihorasdistributivo':
            #     try:
            #         cursor = connection.cursor()
            #         lista_json = []
            #         data = {}
            #         cursor.execute("select p.apellido1,p.apellido2,p.nombres,a.nombre as materia,c.dia,cast(t.comienza as text),cast(t.termina as text) from sga_persona p left join sga_profesor pro on pro.persona_id=p.id left join sga_profesormateria pm on pm.profesor_id=pro.id left join sga_materia m on pm.materia_id=m.id left join sga_nivel n on m.nivel_id=n.id left join sga_asignatura a on m.asignatura_id=a.id left join sga_clase c on c.materia_id=m.id left join sga_turno t on c.turno_id=t.id where n.periodo_id='" + request.GET["periodo"] + "' and c.activo=true order by p.apellido1,p.apellido2,a.nombre,c.dia")
            #         results = cursor.fetchall()
            #         for r in results:
            #             datadoc = {}
            #             datadoc['apellidosdocentes'] = r[0] + ' ' + r[1]
            #             datadoc['nombredocente'] = r[2]
            #             datadoc['materiadocente'] = r[3]
            #             datadoc['dia'] = r[4]
            #             datadoc['inicio'] = r[5]
            #             datadoc['fin'] = r[6]
            #
            #             lista_json.append(datadoc)
            #         listado_docentes = json.dumps(lista_json)
            #         return HttpResponse(listado_docentes
            #     except Exception as ex:
            #         return JsonResponse({'result': 'bad', "mensaje": u"Error al obtener los datos del distributivo"})

            # if action == 'apilistaestudiantes':
            #     try:
            #         lista_json = []
            #         listado = Inscripcion.objects.values_list('persona__apellido1',
            #                                                   'persona__apellido2',
            #                                                   'persona__nombres',
            #                                                   'persona__cedula',
            #                                                   'persona__email',
            #                                                   'persona__emailinst',
            #                                                   'inscripcionnivel__nivel__id',
            #                                                   'inscripcionnivel__nivel__nombre',
            #                                                   'carrera__nombre',
            #                                                   'coordinacion__nombre')._next_is_sticky().filter(matricula__nivel__periodo__id=request.GET['periodo']).order_by('persona__apellido1')
            #         for per in listado:
            #             per_col = {}
            #             per_col['apellidosestudiantes'] = per[0] + ' ' + per[1]
            #             per_col['nombresestudiantes'] = per[2]
            #             per_col['cedula'] = per[3]
            #             per_col['correo'] = per[4]
            #             per_col['correoinstitucion'] = per[5]
            #             per_col['nivel'] = per[7]
            #             per_col['facultad'] = per[9]
            #             lista_json.append(per_col)
            #         listado_periodos = json.dumps(lista_json)
            #         return HttpResponse(listado_periodos
            #
            #     except Exception as ex:
            #         return JsonResponse({'result': 'bad', "mensaje": u"Error al obtener los datos de profesores"})

            # if action == 'apilistaestudiantescedula':
            #     try:
            #         lista_json = []
            #         listado = Inscripcion.objects.values_list('persona__apellido1',
            #                                                   'persona__apellido2',
            #                                                   'persona__nombres',
            #                                                   'persona__cedula',
            #                                                   'persona__email',
            #                                                   'persona__emailinst',
            #                                                   'inscripcionnivel__nivel__id',
            #                                                   'inscripcionnivel__nivel__nombre',
            #                                                   'carrera__nombre',
            #                                                   'coordinacion__nombre')._next_is_sticky().filter(matricula__nivel__periodo__id=request.GET['periodo'],persona__cedula=request.GET['cedula']).order_by('persona__apellido1')
            #         for per in listado:
            #             per_col = {}
            #             per_col['apellidosestudiantes'] = per[0] + ' ' + per[1]
            #             per_col['nombresestudiantes'] = per[2]
            #             per_col['cedula'] = per[3]
            #             per_col['correo'] = per[4]
            #             per_col['correoinstitucion'] = per[5]
            #             per_col['nivel'] = per[7]
            #             per_col['facultad'] = per[9]
            #             lista_json.append(per_col)
            #         listado_periodos = json.dumps(lista_json)
            #         return HttpResponse(listado_periodos
            #
            #     except Exception as ex:
            #         return JsonResponse({'result': 'bad', "mensaje": u"Error al obtener los datos de profesores"})

            # if action == 'apilistadocentes':
            #     try:
            #         cursor = connection.cursor()
            #         lista_jsondoc = []
            #         cursor.execute("select per.email,per.emailinst,peri.nombre,per.apellido1,per.apellido2,per.nombres,asi.nombre as nom_materia,carr.nombre as carrera,coordi.nombre as facultad,nmalla.nombre as nivel,coalesce(cate.nombre,'CATEGORIA NO ASIGNADA') as categorizacion,coalesce(dedi.nombre,'DEDICACION NO ASIGNADA') as dedicacion,c.dia,cast(t.comienza as text),cast(t.termina as text),per.cedula from sga_profesormateria pm left join sga_profesor pro on pro.id=profesor_id left join sga_persona per on per.id=pro.persona_id left join sga_materia mate on mate.id=pm.materia_id left join sga_nivel niv on niv.id=mate.nivel_id left join sga_periodo peri on peri.id=niv.periodo_id left join sga_asignatura asi on asi.id=mate.asignatura_id left join sga_asignaturamalla asimalla on asimalla.id=mate.asignaturamalla_id left join sga_nivelmalla nmalla on nmalla.id=asimalla.nivelmalla_id left join sga_malla malla on malla.id=asimalla.malla_id left join sga_carrera carr on carr.id=malla.carrera_id left join sga_coordinacion_carrera corcar on corcar.carrera_id=carr.id left join sga_coordinacion coordi on coordi.id=corcar.coordinacion_id left join sga_categorizaciondocente cate on cate.id=pro.categoria_id left join sga_tiempodedicaciondocente dedi on dedi.id=pro.dedicacion_id left join sga_clase c on c.materia_id=mate.id left join sga_turno t on c.turno_id=t.id where peri.id='" + request.GET["periodo"] + "' and c.activo=true order by per.apellido1,per.apellido2,asi.nombre,c.dia")
            #         results = cursor.fetchall()
            #         for r in results:
            #             datadoc = {}
            #             datadoc['correo'] = r[0]
            #             datadoc['correoinst'] = r[1]
            #             datadoc['nombreperiodo'] = r[2]
            #             datadoc['primerapellido'] = r[3]
            #             datadoc['segundoapellido'] = r[4]
            #             datadoc['nombredocente'] = r[5]
            #             datadoc['materias'] = r[6]
            #             datadoc['carrera'] = r[7]
            #             datadoc['facultad'] = r[8]
            #             datadoc['nivelcurso'] = r[9]
            #             datadoc['cargo'] = 'DOCENTE ' + r[10] + ' ' + r[11]
            #             datadoc['dia'] = r[12]
            #             datadoc['inicio'] = r[13]
            #             datadoc['fin'] = r[14]
            #             lista_jsondoc.append(datadoc)
            #         listado_docentes = json.dumps(lista_jsondoc)
            #         response = HttpResponse(json.dumps(lista_jsondoc))
            #         response.__setitem__("Content-type", "application/json")
            #         response.__setitem__("Access-Control-Allow-Origin", "*")
            #         return response
            #     except Exception as ex:
            #         return JsonResponse({'result': 'bad', "mensaje": u"Error al obtener los datos del docente"})

            # if action == 'apimatriculadosfacultad':
            #     try:
            #         cursor = connection.cursor()
            #         lista_jsondoc = []
            #         listafacultad = "select coor.id,coor.nombre as nomfacultad,coor.alias as nomalias, " \
            #         "count(distinct matri.inscripcion_id) as numero " \
            #         "from sga_matricula matri,sga_inscripcion ins,sga_coordinacion coor,sga_nivel ni " \
            #         "where ins.coordinacion_id=coor.id " \
            #         "and matri.inscripcion_id=ins.id " \
            #         "and matri.retiradomatricula=false " \
            #         "and matri.status=true " \
            #         "and matri.nivel_id=ni.id " \
            #         "and ni.periodo_id='" + request.GET["periodo"] + "' " \
            #         "and matri.estado_matricula in (2,3) " \
            #         "and matri.id not in (select tabla.matricula_id from " \
            #         "(select count(matri.id) as contar, matri.id as matricula_id " \
            #         "from sga_matricula matri,sga_inscripcion ins,sga_coordinacion coor,sga_nivel ni, " \
            #         "sga_materiaasignada matasig,sga_materia mate, sga_asignatura asig,sga_carrera carr " \
            #         "where ins.coordinacion_id=coor.id " \
            #         "and ins.carrera_id=carr.id " \
            #         "and matri.inscripcion_id=ins.id " \
            #         "and matri.retiradomatricula=false " \
            #         "and matri.status=true " \
            #         "and matri.nivel_id=ni.id " \
            #         "and matasig.matricula_id=matri.id " \
            #         "and matasig.materia_id=mate.id " \
            #         "and mate.asignatura_id=asig.id " \
            #         "and ni.periodo_id='" + request.GET["periodo"] + "' " \
            #         "and matri.estado_matricula in (2,3) " \
            #         "GROUP by matri.id) as tabla, " \
            #         "sga_materiaasignada matasig1,sga_materia mate1, sga_asignatura asig1 " \
            #         "where tabla.contar = 1 and matasig1.matricula_id=tabla.matricula_id " \
            #         "and matasig1.materia_id=mate1.id and mate1.asignatura_id=asig1.id " \
            #         "and asig1.modulo=True) " \
            #         "group by coor.id,coor.nombre,coor.alias"
            #         cursor.execute(listafacultad)
            #         results = cursor.fetchall()
            #         total = 0
            #         for re in results:
            #             total += re[3]
            #         for r in results:
            #             datadoc = {}
            #             datadoc['codigo'] = r[0]
            #             datadoc['facultad'] = r[1]
            #             datadoc['alias'] = r[2]
            #             datadoc['numero'] = r[3]
            #             datadoc['porcentaje'] = round(((r[3] * 100) / total),2)
            #             lista_jsondoc.append(datadoc)
            #         listado_docentes = json.dumps(lista_jsondoc)
            #         response = HttpResponse(json.dumps(lista_jsondoc))
            #         response.__setitem__("Content-type", "application/json")
            #         response.__setitem__("Access-Control-Allow-Origin", "*")
            #         return response
            #     except Exception as ex:
            #         return JsonResponse({'result': 'bad', "mensaje": u"Error al obtener los datos del docente"})
            #


            # if action == 'apiincidentes':
            #     try:
            #         cursor = connection.cursor()
            #         lista_jsondoc = []
            #         cursor.execute("select extract(YEAR FROM h.fechareporte), extract(month FROM h.fechareporte),extract(day FROM h.fechareporte), h.asunto, p.nombres,p.apellido1, h.estado_id, e.nombre, p.telefono from sagest_hdincidente h inner join sga_persona p on p.id=h.persona_id inner join sagest_hdestado e on e.id=h.estado_id where h.estado_id in (1,2) order by h.fechareporte desc;")
            #         results = cursor.fetchall()
            #         for r in results:
            #             datadoc = {}
            #             datadoc['anio'] =(r[0])
            #             datadoc['mes'] =(r[1])
            #             datadoc['dia'] =(r[2])
            #             datadoc['asunto'] = r[3]
            #             datadoc['nombres'] = r[4]
            #             datadoc['apellido1'] = r[5]
            #             datadoc['estado_id'] = r[6]
            #             datadoc['estado'] = r[7]
            #             datadoc['tel'] = r[8]
            #             lista_jsondoc.append(datadoc)
            #         listado_docentes = json.dumps(lista_jsondoc)
            #         response = HttpResponse(json.dumps(lista_jsondoc))
            #         response.__setitem__("Content-type", "application/json")
            #         response.__setitem__("Access-Control-Allow-Origin", "*")
            #         return response
            #     except Exception as ex:
            #         return JsonResponse({'result': 'bad', "mensaje": u"Error al obtener los datos de incidentes"})
            #


            # if action == 'apimatriculadosperiodos':
            #     try:
            #         cursor = connection.cursor()
            #         lista_jsondoc = []
            #         listafacultad = "select id,nombre,numero,total,round(((numero*100::decimal)/total),0) as porcentaje from " \
            #         "(select per.id,per.nombre,count(i.persona_id) as numero, " \
            #         "(select count(i.persona_id) as numero from sga_matricula mat,sga_inscripcion i,sga_persona p,sga_nivel n, " \
            #         "sga_carrera car,sga_coordinacion coor,sga_coordinacion_carrera cca, sga_periodo per, sga_nivelmalla nv, " \
            #         "sga_inscripcionnivel inniv,sga_sesion ses where mat.estado_matricula in (2,3) and mat.inscripcion_id=i.id and i.persona_id=p.id " \
            #         "and mat.nivel_id=n.id and i.carrera_id=car.id and car.id=cca.carrera_id and cca.coordinacion_id=coor.id " \
            #         "and n.periodo_id=per.id and i.id=inniv.inscripcion_id and inniv.nivel_id=nv.id " \
            #         "and i.sesion_id=ses.id and mat.id not in(select ma.id from (select  mat.id as id,count(ma.materia_id) " \
            #         "as numero from sga_Matricula mat , sga_Nivel n,sga_materiaasignada ma,sga_materia mate, sga_asignatura asi " \
            #         "where mat.nivel_id=n.id and mat.id=ma.matricula_id and ma.materia_id=mate.id and mate.asignatura_id=asi.id " \
            #         "and asi.modulo=True group by mat.id) ma,(select  mat.id as id, " \
            #         "count(ma.materia_id) as numero " \
            #         "from sga_Matricula mat , sga_Nivel n,sga_materiaasignada ma, sga_materia mate, sga_asignatura asi " \
            #         "where mat.nivel_id=n.id and mat.id=ma.matricula_id and ma.materia_id=mate.id and mate.asignatura_id=asi.id " \
            #         "group by mat.id) mo " \
            #         "where ma.id=mo.id and ma.numero=mo.numero)) as total, 0.00 as porcentaje " \
            #         "from sga_matricula mat,sga_inscripcion i,sga_persona p,sga_nivel n,sga_carrera car,sga_coordinacion coor, " \
            #         "sga_coordinacion_carrera cca, sga_periodo per, sga_nivelmalla nv,sga_inscripcionnivel inniv,sga_sesion ses " \
            #         "where mat.inscripcion_id=i.id and i.persona_id=p.id and mat.nivel_id=n.id and i.carrera_id=car.id " \
            #         "and car.id=cca.carrera_id and cca.coordinacion_id=coor.id and n.periodo_id=per.id " \
            #         "and i.id=inniv.inscripcion_id and inniv.nivel_id=nv.id " \
            #         "and i.sesion_id=ses.id and mat.id not in(select ma.id from (select  mat.id as id,count(ma.materia_id)  as numero " \
            #         "from sga_Matricula mat , sga_Nivel n,sga_materiaasignada ma,sga_materia mate, sga_asignatura asi " \
            #         "where mat.nivel_id=n.id and mat.id=ma.matricula_id and ma.materia_id=mate.id and mate.asignatura_id=asi.id " \
            #         "and asi.modulo=True group by mat.id) ma,(select  mat.id as id, count(ma.materia_id) as numero " \
            #         "from sga_Matricula mat , sga_Nivel n,sga_materiaasignada ma, sga_materia mate, sga_asignatura asi " \
            #         "where mat.nivel_id=n.id and mat.id=ma.matricula_id and ma.materia_id=mate.id and mate.asignatura_id=asi.id " \
            #         "group by mat.id) mo " \
            #         "where ma.id=mo.id and ma.numero=mo.numero) group by per.id,per.nombre) ko order by id"
            #         cursor.execute(listafacultad)
            #         results = cursor.fetchall()
            #         for r in results:
            #             datadoc = {}
            #             datadoc['periodo'] = r[1]
            #             datadoc['numero'] = r[2]
            #             datadoc['porcentaje'] = int(r[3])
            #             lista_jsondoc.append(datadoc)
            #         listado_docentes = json.dumps(lista_jsondoc)
            #         response = HttpResponse(json.dumps(lista_jsondoc))
            #         response.__setitem__("Content-type", "application/json")
            #         response.__setitem__("Access-Control-Allow-Origin", "*")
            #         return response
            #     except Exception as ex:
            #         return JsonResponse({'result': 'bad', "mensaje": u"Error al obtener los datos del docente"})

            # if action == 'apimatriculadossexo':
            #     try:
            #         cursor = connection.cursor()
            #         lista_jsondoc = []
            #         listaestudiantes = "select nombre,numero,total,round(((numero*100::decimal)/total),0) as porcentaje from " \
            #                            "(select sex.nombre,count(i.persona_id) as numero,(select count(i.persona_id) from sga_matricula mat, " \
            #                            "sga_inscripcion i,sga_persona p,sga_nivel n,sga_carrera car,   " \
            #                            "sga_coordinacion coor, sga_coordinacion_carrera cca, sga_periodo per, sga_nivelmalla nv,   " \
            #                            "sga_inscripcionnivel inniv,sga_sesion ses, sga_sexo sex where mat.estado_matricula in (2,3) and mat.inscripcion_id=i.id    " \
            #                            "and i.persona_id=p.id and mat.nivel_id=n.id and i.carrera_id=car.id and p.sexo_id=sex.id  " \
            #                            "and car.id=cca.carrera_id and cca.coordinacion_id=coor.id and n.periodo_id=per.id " \
            #                            "and i.id=inniv.inscripcion_id and inniv.nivel_id=nv.id    and n.periodo_id='" + request.GET["periodo"] + "'    " \
            #                            "and i.sesion_id=ses.id and mat.id not in(select ma.id from " \
            #                            "(select  mat.id as id,count(ma.materia_id)  as numero " \
            #                            "from sga_Matricula mat , sga_Nivel n,sga_materiaasignada ma,sga_materia mate,  sga_asignatura asi " \
            #                            "where mat.nivel_id=n.id and mat.id=ma.matricula_id and ma.materia_id=mate.id  " \
            #                            "and mate.asignatura_id=asi.id and n.periodo_id='" + request.GET["periodo"] + "' " \
            #                            "and asi.modulo=True group by mat.id) ma,(select   mat.id as id, count(ma.materia_id) as numero from sga_Matricula mat , sga_Nivel n," \
            #                            "sga_materiaasignada ma, sga_materia mate, sga_asignatura asi where mat.nivel_id=n.id    " \
            #                            "and mat.id=ma.matricula_id and ma.materia_id=mate.id and mate.asignatura_id=asi.id  " \
            #                            "and n.periodo_id='" + request.GET["periodo"] + "' group by mat.id) mo    " \
            #                            "where ma.id=mo.id and ma.numero=mo.numero)) as total, " \
            #                            "0.00 as porcentaje    from sga_matricula mat,sga_inscripcion i,sga_persona p,sga_nivel n,sga_carrera car," \
            #                            "sga_coordinacion coor, sga_coordinacion_carrera cca, sga_periodo per, sga_nivelmalla nv,   " \
            #                            "sga_inscripcionnivel inniv,sga_sesion ses, sga_sexo sex where mat.inscripcion_id=i.id   " \
            #                            "and i.persona_id=p.id and mat.nivel_id=n.id and i.carrera_id=car.id and p.sexo_id=sex.id " \
            #                            "and car.id=cca.carrera_id and cca.coordinacion_id=coor.id and n.periodo_id=per.id    " \
            #                            "and i.id=inniv.inscripcion_id and inniv.nivel_id=nv.id    and n.periodo_id='" + request.GET["periodo"] + "'   " \
            #                            "and i.sesion_id=ses.id and mat.id not in(select ma.id from " \
            #                            "(select  mat.id as id,count(ma.materia_id)  as numero " \
            #                            "from sga_Matricula mat , sga_Nivel n,sga_materiaasignada ma,sga_materia mate,  sga_asignatura asi " \
            #                            "where mat.nivel_id=n.id and mat.id=ma.matricula_id and ma.materia_id=mate.id  " \
            #                            "and mate.asignatura_id=asi.id and n.periodo_id='" + request.GET["periodo"] + "' " \
            #                           "and asi.modulo=True group by mat.id) ma,(select   mat.id as id, count(ma.materia_id) as numero from sga_Matricula mat , sga_Nivel n," \
            #                           "sga_materiaasignada ma, sga_materia mate, sga_asignatura asi where mat.nivel_id=n.id    " \
            #                           "and mat.id=ma.matricula_id and ma.materia_id=mate.id and mate.asignatura_id=asi.id  " \
            #                           "and n.periodo_id='" + request.GET["periodo"] + "' group by mat.id) mo    " \
            #                           "where ma.id=mo.id and ma.numero=mo.numero) group by sex.nombre) li"
            #         cursor.execute(listaestudiantes)
            #         results = cursor.fetchall()
            #         for r in results:
            #             datadoc = {}
            #             datadoc['sexo'] = r[0]
            #             datadoc['numero'] = r[1]
            #             datadoc['porcentaje'] = int(r[3])
            #             lista_jsondoc.append(datadoc)
            #         listado_docentes = json.dumps(lista_jsondoc)
            #         response = HttpResponse(json.dumps(lista_jsondoc))
            #         response.__setitem__("Content-type", "application/json")
            #         response.__setitem__("Access-Control-Allow-Origin", "*")
            #         return response
            #     except Exception as ex:
            #         return JsonResponse({'result': 'bad', "mensaje": u"Error al obtener los datos del docente"})


            #             if action == 'apimatriculadoscarsexo':
            # try:
            #         cursor = connection.cursor()
            #         lista_jsondoc = []
            #         listaestudiantes = "select nombre,numero from " \
            #         "(select sex.nombre,count(i.persona_id) as numero " \
            #         "from sga_matricula mat,sga_inscripcion i,sga_persona p,sga_nivel n, " \
            #         "sga_carrera car, " \
            #         "sga_coordinacion coor, sga_coordinacion_carrera cca, sga_periodo per, sga_nivelmalla nv, " \
            #         "sga_inscripcionnivel inniv,sga_sesion ses, sga_sexo sex where mat.estado_matricula in (2,3) and mat.inscripcion_id=i.id " \
            #         "and i.persona_id=p.id and mat.nivel_id=n.id and i.carrera_id=car.id and p.sexo_id=sex.id " \
            #         "and car.id=cca.carrera_id and cca.coordinacion_id=coor.id and n.periodo_id=per.id " \
            #         "and i.id=inniv.inscripcion_id and inniv.nivel_id=nv.id    and n.periodo_id='" + request.GET["periodo"] + "' " \
            #         "and i.sesion_id=ses.id and i.carrera_id='" + request.GET["carrera"] + "' and mat.id not in(select ma.id from " \
            #         "(select  mat.id as id,count(ma.materia_id)  as numero " \
            #         "from sga_Matricula mat , sga_Nivel n,sga_materiaasignada ma,sga_materia mate,  sga_asignatura asi " \
            #         "where mat.nivel_id=n.id and mat.id=ma.matricula_id and ma.materia_id=mate.id " \
            #         "and mate.asignatura_id=asi.id and n.periodo_id='" + request.GET["periodo"] + "' " \
            #         "and asi.modulo=True group by mat.id) ma,(select   mat.id as id, count(ma.materia_id) as numero " \
            #         "from sga_Matricula mat , sga_Nivel n, " \
            #         "sga_materiaasignada ma, sga_materia mate, sga_asignatura asi where mat.nivel_id=n.id " \
            #         "and mat.id=ma.matricula_id and ma.materia_id=mate.id and mate.asignatura_id=asi.id " \
            #         "and n.periodo_id='" + request.GET["periodo"] + "' group by mat.id) mo " \
            #         "where ma.id=mo.id and ma.numero=mo.numero) group by sex.nombre) li "
            #         cursor.execute(listaestudiantes)
            #         results = cursor.fetchall()
            #         for r in results:
            #             datadoc = {}
            #             datadoc['sexo'] = r[0]
            #             datadoc['numero'] = r[1]
            #             lista_jsondoc.append(datadoc)
            #         response = HttpResponse(json.dumps(lista_jsondoc))
            #         response.__setitem__("Content-type", "application/json")
            #         response.__setitem__("Access-Control-Allow-Origin", "*")
            #         return response
            #     except Exception as ex:
            #         return JsonResponse({'result': 'bad', "mensaje": u"Error al obtener los datos del docente"})

            # if action == 'apimatriculadosetnia':
            #     try:
            #         cursor = connection.cursor()
            #         lista_jsondoc = []
            #         listaetnia = "select nombre,numero,total,round(((numero*100::decimal)/total),0) as porcentaje from " \
            #                      "(select ra.nombre,count(i.persona_id) as numero,(select count(i.persona_id) as numero " \
            #                      "from sga_matricula mat,sga_inscripcion i,sga_persona p,sga_nivel n,sga_carrera car,  " \
            #                      "sga_coordinacion coor, sga_coordinacion_carrera cca, sga_periodo per, sga_nivelmalla nv,  " \
            #                      "sga_inscripcionnivel inniv,sga_sesion ses, sga_sexo sex,sga_perfilinscripcion pins, sga_raza ra " \
            #                      "where mat.estado_matricula in (2,3) and mat.inscripcion_id=i.id and i.persona_id=p.id and mat.nivel_id=n.id and i.carrera_id=car.id " \
            #                      "and p.sexo_id=sex.id   and car.id=cca.carrera_id and cca.coordinacion_id=coor.id and n.periodo_id=per.id " \
            #                      "and i.id=inniv.inscripcion_id and inniv.nivel_id=nv.id and p.id=pins.persona_id and pins.raza_id=ra.id " \
            #                      "and n.periodo_id='" + request.GET["periodo"] + "'  and i.sesion_id=ses.id and mat.id not in(select ma.id from (select  mat.id as id,count(ma.materia_id)  as numero " \
            #                      "from sga_Matricula mat , sga_Nivel n,sga_materiaasignada ma,sga_materia mate,  sga_asignatura asi " \
            #                      "where mat.nivel_id=n.id and mat.id=ma.matricula_id and ma.materia_id=mate.id  and mate.asignatura_id=asi.id " \
            #                      "and n.periodo_id='" + request.GET["periodo"] + "'  and asi.modulo=True group by mat.id) ma," \
            #                      "(select  mat.id as id, count(ma.materia_id) as numero " \
            #                      "from sga_Matricula mat , sga_Nivel n,  sga_materiaasignada ma, sga_materia mate, sga_asignatura asi " \
            #                      "where mat.nivel_id=n.id  and mat.id=ma.matricula_id and ma.materia_id=mate.id " \
            #                      "and mate.asignatura_id=asi.id  and n.periodo_id='" + request.GET["periodo"] + "' group by mat.id) mo  " \
            #                      "where ma.id=mo.id and ma.numero=mo.numero)) as total," \
            #                      "0.00 as porcentaje    from sga_matricula mat,sga_inscripcion i,sga_persona p,sga_nivel n,sga_carrera car,  " \
            #                      "sga_coordinacion coor, sga_coordinacion_carrera cca, sga_periodo per, sga_nivelmalla nv,   " \
            #                      "sga_inscripcionnivel inniv,sga_sesion ses, sga_sexo sex,sga_perfilinscripcion pins, sga_raza ra " \
            #                      "where mat.inscripcion_id=i.id and i.persona_id=p.id and mat.nivel_id=n.id and i.carrera_id=car.id " \
            #                      "and p.sexo_id=sex.id   and car.id=cca.carrera_id and cca.coordinacion_id=coor.id and n.periodo_id=per.id   " \
            #                      "and i.id=inniv.inscripcion_id and inniv.nivel_id=nv.id and p.id=pins.persona_id and pins.raza_id=ra.id " \
            #                      "and n.periodo_id='" + request.GET["periodo"] + "'  and i.sesion_id=ses.id and mat.id not in(select ma.id from (select  mat.id as id,count(ma.materia_id)  as numero " \
            #                      "from sga_Matricula mat , sga_Nivel n,sga_materiaasignada ma,sga_materia mate,  sga_asignatura asi " \
            #                      "where mat.nivel_id=n.id and mat.id=ma.matricula_id and ma.materia_id=mate.id  and mate.asignatura_id=asi.id " \
            #                      "and n.periodo_id='" + request.GET["periodo"] + "'  and asi.modulo=True group by mat.id) ma," \
            #                      "(select  mat.id as id, count(ma.materia_id) as numero " \
            #                      "from sga_Matricula mat , sga_Nivel n,  sga_materiaasignada ma, sga_materia mate, sga_asignatura asi " \
            #                      "where mat.nivel_id=n.id  and mat.id=ma.matricula_id and ma.materia_id=mate.id " \
            #                      "and mate.asignatura_id=asi.id  and n.periodo_id='" + request.GET["periodo"] + "' group by mat.id) mo  " \
            #                      "where ma.id=mo.id and ma.numero=mo.numero) group by ra.nombre) n"
            #         cursor.execute(listaetnia)
            #         results = cursor.fetchall()
            #         for r in results:
            #             datadoc = {}
            #             datadoc['etnia'] = r[0]
            #             datadoc['numero'] = r[1]
            #             datadoc['porcentaje'] = int(r[3])
            #             lista_jsondoc.append(datadoc)
            #         listado_docentes = json.dumps(lista_jsondoc)
            #         response = HttpResponse(json.dumps(lista_jsondoc))
            #         response.__setitem__("Content-type", "application/json")
            #         response.__setitem__("Access-Control-Allow-Origin", "*")
            #         return response
            #     except Exception as ex:
            #         return JsonResponse({'result': 'bad', "mensaje": u"Error al obtener los datos del docente"})


            # if action == 'apimatriculadoscaretnia':
            #     try:
            #         cursor = connection.cursor()
            #         lista_jsondoc = []
            #         listaetnia = "select nombre,numero from " \
            #         "(select ra.nombre,count(i.persona_id) as numero    from sga_matricula mat,sga_inscripcion i,sga_persona p,sga_nivel n,sga_carrera car, " \
            #         "sga_coordinacion coor, sga_coordinacion_carrera cca, sga_periodo per, sga_nivelmalla nv, " \
            #         "sga_inscripcionnivel inniv,sga_sesion ses, sga_sexo sex,sga_perfilinscripcion pins, sga_raza ra " \
            #         "where mat.estado_matricula in (2,3) and mat.inscripcion_id=i.id and i.persona_id=p.id and mat.nivel_id=n.id and i.carrera_id=car.id " \
            #         "and p.sexo_id=sex.id   and car.id=cca.carrera_id and cca.coordinacion_id=coor.id and n.periodo_id=per.id " \
            #         "and i.id=inniv.inscripcion_id and inniv.nivel_id=nv.id and p.id=pins.persona_id and pins.raza_id=ra.id " \
            #         "and n.periodo_id='" + request.GET["periodo"] + "'  and i.sesion_id=ses.id and i.carrera_id='" + request.GET["carrera"] + "' and mat.id not in(select ma.id from (select  mat.id as id,count(ma.materia_id)  as numero " \
            #         "from sga_Matricula mat , sga_Nivel n,sga_materiaasignada ma,sga_materia mate,  sga_asignatura asi " \
            #         "where mat.nivel_id=n.id and mat.id=ma.matricula_id and ma.materia_id=mate.id  and mate.asignatura_id=asi.id " \
            #         "and n.periodo_id='" + request.GET["periodo"] + "'  and asi.modulo=True group by mat.id) ma, " \
            #         "(select  mat.id as id, count(ma.materia_id) as numero " \
            #         "from sga_Matricula mat , sga_Nivel n,  sga_materiaasignada ma, sga_materia mate, sga_asignatura asi " \
            #         "where mat.nivel_id=n.id  and mat.id=ma.matricula_id and ma.materia_id=mate.id " \
            #         "and mate.asignatura_id=asi.id  and n.periodo_id='" + request.GET["periodo"] + "' group by mat.id) mo " \
            #         "where ma.id=mo.id and ma.numero=mo.numero) group by ra.nombre) n"
            #         cursor.execute(listaetnia)
            #         results = cursor.fetchall()
            #         for r in results:
            #             datadoc = {}
            #             datadoc['etnia'] = r[0]
            #             datadoc['numero'] = r[1]
            #             lista_jsondoc.append(datadoc)
            #         response = HttpResponse(json.dumps(lista_jsondoc))
            #         response.__setitem__("Content-type", "application/json")
            #         response.__setitem__("Access-Control-Allow-Origin", "*")
            #         return response
            #     except Exception as ex:
            #         return JsonResponse({'result': 'bad', "mensaje": u"Error al obtener los datos del docente"})

            #             if action == 'apiproacdedicacion':
            # try:
            #         cursor = connection.cursor()
            #         lista_jsondoc = []
            #         cursor.execute("SELECT d.nombre as dedicacion, count(p.id) as total from sga_profesor p, sga_tiempodedicaciondocente d , sga_persona per, sagest_distributivopersona dp where d.id=p.dedicacion_id and  per.id=p.persona_id and dp.persona_id=per.id and  dp.estadopuesto_id=1 and dp.regimenlaboral_id=2  group by d.nombre;")
            #         results = cursor.fetchall()
            #         for r in results:
            #             datadoc = {}
            #             datadoc['dedicacion'] = r[0]
            #             datadoc['total'] = r[1]
            #             lista_jsondoc.append(datadoc)
            #         listado_docentes = json.dumps(lista_jsondoc)
            #         response = HttpResponse(json.dumps(lista_jsondoc))
            #         response.__setitem__("Content-type", "application/json")
            #         response.__setitem__("Access-Control-Allow-Origin", "*")
            #         return response
            #     except Exception as ex:
            #         return JsonResponse({'result': 'bad', "mensaje": u"Error al obtener los datos del docente"})


            # if action == 'apiproactipo':
            #     try:
            #         cursor = connection.cursor()
            #         lista_jsondoc = []
            #         cursor.execute("select t.nombre as tipo, count(p.id) as total from sga_profesor p, sga_profesortipo t , sga_persona per, sagest_distributivopersona dp where t.id=p.nivelcategoria_id and  per.id=p.persona_id and dp.persona_id=per.id and  dp.estadopuesto_id=1 and dp.regimenlaboral_id=2  group by t.nombre;")
            #         results = cursor.fetchall()
            #         for r in results:
            #             datadoc = {}
            #             datadoc['tipo'] = r[0]
            #             datadoc['total'] = r[1]
            #             lista_jsondoc.append(datadoc)
            #         listado_docentes = json.dumps(lista_jsondoc)
            #         response = HttpResponse(json.dumps(lista_jsondoc))
            #         response.__setitem__("Content-type", "application/json")
            #         response.__setitem__("Access-Control-Allow-Origin", "*")
            #         return response
            #     except Exception as ex:
            #         return JsonResponse({'result': 'bad', "mensaje": u"Error al obtener los datos del docente"})

            # if action == 'apiproaccategoria':
            #     try:
            #         cursor = connection.cursor()
            #         lista_jsondoc = []
            #         cursor.execute("select c.nombre as categoria, count(p.id) as total from sga_profesor p, sga_categorizaciondocente c , sga_persona per, sagest_distributivopersona dp where c.id=p.categoria_id and  per.id=p.persona_id and dp.persona_id=per.id and  dp.estadopuesto_id=1 and dp.regimenlaboral_id=2 and c.id in(5,4,6) group by c.nombre;")
            #         results = cursor.fetchall()
            #         for r in results:
            #             datadoc = {}
            #             datadoc['categoria'] = r[0]
            #             datadoc['total'] = r[1]
            #             lista_jsondoc.append(datadoc)
            #         listado_docentes = json.dumps(lista_jsondoc)
            #         response = HttpResponse(json.dumps(lista_jsondoc))
            #         response.__setitem__("Content-type", "application/json")
            #         response.__setitem__("Access-Control-Allow-Origin", "*")
            #         return response
            #     except Exception as ex:
            #         return JsonResponse({'result': 'bad', "mensaje": u"Error al obtener los datos del docente"})

            # if action == 'apilistainiscripciones':
            #     try:
            #         lista_jsondoc = []
            #         listainscripciones = Inscripcion.objects.filter(status=True)
            #         for r in listainscripciones:
            #             datadoc = {}
            #             datadoc['identificacion'] = r.persona.cedula
            #             datadoc['primerapellido'] = r.persona.apellido1
            #             datadoc['segundoapellido'] = r.persona.apellido2
            #             datadoc['nombregenero'] = r.persona.sexo.nombre
            #             datadoc['nombreestudiante'] = r.persona.nombres
            #             datadoc['nombrefacultad'] = r.coordinacion.nombre
            #             datadoc['nombrecarrera'] = r.carrera.nombre
            #             lista_jsondoc.append(datadoc)
            #         listado_docentes = json.dumps(lista_jsondoc)
            #         response = JsonResponse(lista_jsondoc))
            #         response.__setitem__("Content-type", "application/json")
            #         response.__setitem__("Access-Control-Allow-Origin", "*")
            #         return response
            #     except Exception as ex:
            #         return JsonResponse({'result': 'bad', "mensaje": u"Error al obtener los datos del docente"})

            # if action == 'apilistaprofesores':
            #     try:
            #         lista_jsondoc = []
            #         listainscripciones = Profesor.objects.filter(status=True)
            #         for r in listainscripciones:
            #             datadoc = {}
            #             datadoc['identificacion'] = r.persona.cedula
            #             datadoc['primerapellido'] = r.persona.apellido1
            #             datadoc['segundoapellido'] = r.persona.apellido2
            #             datadoc['nombregenero'] = r.persona.sexo.nombre
            #             datadoc['nombredocente'] = r.persona.nombres
            #             datadoc['nombrefacultad'] = r.coordinacion.nombre
            #             lista_jsondoc.append(datadoc)
            #         listado_docentes = json.dumps(lista_jsondoc)
            #         response = JsonResponse(lista_jsondoc))
            #         response.__setitem__("Content-type", "application/json")
            #         response.__setitem__("Access-Control-Allow-Origin", "*")
            #         return response
            #     except Exception as ex:
            #         return JsonResponse({'result': 'bad', "mensaje": u"Error al obtener los datos del docente"})

            # if action == 'apiinvestigacion':
            #     try:
            #         lista_jsondoc = []
            #         datadoc = {}
            #         totalarticulo = ArticuloInvestigacion.objects.filter(status=True).count()
            #         totalponencias = PonenciasInvestigacion.objects.filter(status=True).count()
            #         totallibros = LibroInvestigacion.objects.filter(status=True).count()
            #         totalcapitulos = CapituloLibroInvestigacion.objects.filter(status=True).count()
            #         lista_jsondoc.append(datadoc)
            #         response = HttpResponse(json.dumps({"totalarticulo": totalarticulo, "totalponencias": totalponencias, "totallibros": totallibros, "totalcapitulos": totalcapitulos, }), mimetype="application/json")
            #         response.__setitem__("Content-type", "application/json")
            #         response.__setitem__("Access-Control-Allow-Origin", "*")
            #         return response
            #     except Exception as ex:
            #         return JsonResponse({'result': 'bad', "mensaje": u"Error al obtener los datos del docente"})

            # if action == 'apilistaproyectosvinculacion':
            #     try:
            #         lista_jsondoc = []
            #         listainscripciones = ProyectosInvestigacion.objects.filter(tipo=1,status=True)
            #         for r in listainscripciones:
            #             datadoc = {}
            #             datadoc['nombreprograma'] = r.programa.nombre
            #             datadoc['nombreproyecto'] = r.nombre
            #             lista_jsondoc.append(datadoc)
            #         listado_docentes = json.dumps(lista_jsondoc)
            #         response = HttpResponse(json.dumps(lista_jsondoc))
            #         response.__setitem__("Content-type", "application/json")
            #         response.__setitem__("Access-Control-Allow-Origin", "*")
            #         return response
            #     except Exception as ex:
            #         return JsonResponse({'result': 'bad', "mensaje": u"Error al obtener los datos del docente"})

            # if action == 'apiproacocacional':
            #     try:
            #         cursor = connection.cursor()
            #         lista_jsondoc = []
            #         cursor.execute("select c.nombre as categoria, count(p.id) as total from sga_profesor p, sga_categorizaciondocente c , sga_persona per, sagest_distributivopersona dp where c.id=p.categoria_id and  per.id=p.persona_id and dp.persona_id=per.id and  dp.estadopuesto_id=1 and dp.regimenlaboral_id=2 and c.id in(1,8) group by c.nombre;")
            #         results = cursor.fetchall()
            #         for r in results:
            #             datadoc = {}
            #             datadoc['categoria'] = r[0]
            #             datadoc['total'] = r[1]
            #             lista_jsondoc.append(datadoc)
            #         listado_docentes = json.dumps(lista_jsondoc)
            #         response = HttpResponse(json.dumps(lista_jsondoc))
            #         response.__setitem__("Content-type", "application/json")
            #         response.__setitem__("Access-Control-Allow-Origin", "*")
            #         return response
            #     except Exception as ex:
            #         return JsonResponse({'result': 'bad', "mensaje": u"Error al obtener los datos del docente"})

            # if action == 'apiproacescalafon':
            #     try:
            #         cursor = connection.cursor()
            #         lista_jsondoc = []
            #         cursor.execute("select ( 'TITULAR ' ||c.nombre ||' '  || e.nombre) as escalafon, count(p.id) as total from sga_profesor p, sga_categorizaciondocente c , sga_nivelescalafondocente e, sga_persona per, sagest_distributivopersona dp where c.id=p.categoria_id and e.id=p.nivelescalafon_id and  per.id=p.persona_id and dp.persona_id=per.id and  dp.estadopuesto_id=1 and dp.regimenlaboral_id=2 and c.id in(5,4,6) group by c.nombre, e.nombre ; ")
            #         results = cursor.fetchall()
            #         for r in results:
            #             datadoc = {}
            #             datadoc['escalafon'] = r[0]
            #             datadoc['total'] = r[1]
            #             lista_jsondoc.append(datadoc)
            #         listado_docentes = json.dumps(lista_jsondoc)
            #         response = HttpResponse(json.dumps(lista_jsondoc))
            #         response.__setitem__("Content-type", "application/json")
            #         response.__setitem__("Access-Control-Allow-Origin", "*")
            #         return response
            #     except Exception as ex:
            #         return JsonResponse({'result': 'bad', "mensaje": u"Error al obtener los datos del docente"})

            # if action == 'apimatriculadoscarerera':
            #     try:
            #         cursor = connection.cursor()
            #         lista_jsondoc = []
            #         listacarreras = "select carreras,alias,numero,total,round(((numero*100::decimal)/total),0) as porcentaje from " \
            #                         "(select car.nombre as carreras,car.alias,count(i.persona_id) as numero," \
            #                         "(select count(i.persona_id) as numero " \
            #                         "from sga_matricula mat,sga_inscripcion i,sga_persona p,sga_nivel n,sga_carrera car,   sga_coordinacion coor, " \
            #                         "sga_coordinacion_carrera cca, sga_periodo per, sga_nivelmalla nv,   sga_inscripcionnivel inniv," \
            #                         "sga_sesion ses, sga_sexo sex where mat.estado_matricula in (2,3) and mat.inscripcion_id=i.id    and i.persona_id=p.id and mat.nivel_id=n.id " \
            #                         "and i.carrera_id=car.id and p.sexo_id=sex.id    and car.id=cca.carrera_id and cca.coordinacion_id=coor.id " \
            #                         "and n.periodo_id=per.id    and i.id=inniv.inscripcion_id and inniv.nivel_id=nv.id    " \
            #                         "and n.periodo_id='" + request.GET["periodo"] + "'   and i.sesion_id=ses.id " \
            #                                                                         "and coor.id='" + request.GET["facultad"] + "' and mat.id not in(select ma.id " \
            #                                                                                                                     "from (select  mat.id as id,count(ma.materia_id)  as numero " \
            #                                                                                                                     "from sga_Matricula mat , sga_Nivel n,sga_materiaasignada ma,sga_materia mate,  sga_asignatura asi " \
            #                                                                                                                     "where mat.nivel_id=n.id and mat.id=ma.matricula_id and ma.materia_id=mate.id  " \
            #                                                                                                                     "and mate.asignatura_id=asi.id and n.periodo_id='" + request.GET["periodo"] + "'  " \
            #                                                                                                                                                                                                   "and asi.modulo=True group by mat.id) ma,(select   mat.id as id, count(ma.materia_id) as numero " \
            #                                                                                                                                                                                                   "from sga_Matricula mat , sga_Nivel n,   sga_materiaasignada ma, sga_materia mate, sga_asignatura asi " \
            #                                                                                                                                                                                                   "where mat.nivel_id=n.id    and mat.id=ma.matricula_id and ma.materia_id=mate.id " \
            #                                                                                                                                                                                                   "and mate.asignatura_id=asi.id    and n.periodo_id='" + request.GET["periodo"] + "' group by mat.id) mo    " \
            #                                                                                                                                                                                                                                                                                    "where ma.id=mo.id and ma.numero=mo.numero)) as total, 0.00 as porcentaje  " \
            #                                                                                                                                                                                                                                                                                    "from sga_matricula mat,sga_inscripcion i,sga_persona p,sga_nivel n,sga_carrera car,   sga_coordinacion coor," \
            #                                                                                                                                                                                                                                                                                    "sga_coordinacion_carrera cca, sga_periodo per, sga_nivelmalla nv,   sga_inscripcionnivel inniv," \
            #                                                                                                                                                                                                                                                                                    "sga_sesion ses, sga_sexo sex where mat.inscripcion_id=i.id    and i.persona_id=p.id and mat.nivel_id=n.id " \
            #                                                                                                                                                                                                                                                                                    "and i.carrera_id=car.id and p.sexo_id=sex.id    and car.id=cca.carrera_id and cca.coordinacion_id=coor.id " \
            #                                                                                                                                                                                                                                                                                    "and n.periodo_id=per.id    and i.id=inniv.inscripcion_id and inniv.nivel_id=nv.id    " \
            #                                                                                                                                                                                                                                                                                    "and n.periodo_id='" + request.GET["periodo"] + "'   and i.sesion_id=ses.id " \
            #                                                                                                                                                                                                                                                                                                                                    "and coor.id='" + request.GET["facultad"] + "' and mat.id not in(select ma.id " \
            #                                                                                                                                                                                                                                                                                                                                                                                "from (select  mat.id as id,count(ma.materia_id)  as numero " \
            #                                                                                                                                                                                                                                                                                                                                                                                "from sga_Matricula mat , sga_Nivel n,sga_materiaasignada ma,sga_materia mate,  sga_asignatura asi " \
            #                                                                                                                                                                                                                                                                                                                                                                                "where mat.nivel_id=n.id and mat.id=ma.matricula_id and ma.materia_id=mate.id  " \
            #                                                                                                                                                                                                                                                                                                                                                                                "and mate.asignatura_id=asi.id and n.periodo_id='" + request.GET["periodo"] + "'  " \
            #                                                                                                                                                                                                                                                                                                                                                                                                                                                              "and asi.modulo=True group by mat.id) ma,(select   mat.id as id, count(ma.materia_id) as numero " \
            #                                                                                                                                                                                                                                                                                                                                                                                                                                                              "from sga_Matricula mat , sga_Nivel n,   sga_materiaasignada ma, sga_materia mate, sga_asignatura asi " \
            #                                                                                                                                                                                                                                                                                                                                                                                                                                                              "where mat.nivel_id=n.id    and mat.id=ma.matricula_id and ma.materia_id=mate.id " \
            #                                                                                                                                                                                                                                                                                                                                                                                                                                                              "and mate.asignatura_id=asi.id    and n.periodo_id='" + request.GET["periodo"] + "' group by mat.id) mo    " \
            #                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                               "where ma.id=mo.id and ma.numero=mo.numero) group by car.nombre,car.alias) tab"
            #         cursor.execute(listacarreras)
            #         results = cursor.fetchall()
            #         for r in results:
            #             datadoc = {}
            #             datadoc['carreras'] = r[0]
            #             datadoc['numero'] = r[2]
            #             datadoc['porcentaje'] = int(r[4])
            #             lista_jsondoc.append(datadoc)
            #         listado_docentes = json.dumps(lista_jsondoc)
            #         response = HttpResponse(json.dumps(lista_jsondoc))
            #         response.__setitem__("Content-type", "application/json")
            #         response.__setitem__("Access-Control-Allow-Origin", "*")
            #         return response
            #     except Exception as ex:
            #         return JsonResponse({'result': 'bad', "mensaje": u"Error al obtener los datos del docente"})

            # if action == 'apicarreras':
            #     try:
            #         cursor = connection.cursor()
            #         lista_jsondoc = []
            #         cursor.execute("select car.id as codigo, car.nombre, car.alias from sga_carrera car, sga_coordinacion_carrera cc where cc.coordinacion_id='" + request.GET["facultad"] + "' and cc.carrera_id=car.id; ")
            #         results = cursor.fetchall()
            #         for r in results:
            #             datadoc = {}
            #             datadoc['codigo'] = r[0]
            #             datadoc['nombre'] = r[1]
            #             datadoc['alias'] = r[2]
            #             lista_jsondoc.append(datadoc)
            #         listado_docentes = json.dumps(lista_jsondoc)
            #         response = HttpResponse(json.dumps(lista_jsondoc))
            #         response.__setitem__("Content-type", "application/json")
            #         response.__setitem__("Access-Control-Allow-Origin", "*")
            #         return response
            #     except Exception as ex:
            #         return JsonResponse({'result': 'bad', "mensaje": u"Error al obtener los datos del docente"})

            # if action == 'apititularessexo':
            #     try:
            #         cursor = connection.cursor()
            #         lista_jsondoc = []
            #         cursor.execute("select sex.nombre as sexo, count(p.id) as total from sga_profesor p, sga_profesortipo t , sga_persona per, sagest_distributivopersona dp , sga_sexo sex where t.id=p.nivelcategoria_id and  per.id=p.persona_id and dp.persona_id=per.id and  dp.estadopuesto_id=1 and dp.regimenlaboral_id=2  and t.id= 1 and sex.id=per.sexo_id group by sex.nombre;")
            #         results = cursor.fetchall()
            #         for r in results:
            #             datadoc = {}
            #             datadoc['sexo'] = r[0]
            #             datadoc['total'] = r[1]
            #             lista_jsondoc.append(datadoc)
            #         listado_docentes = json.dumps(lista_jsondoc)
            #         response = HttpResponse(json.dumps(lista_jsondoc))
            #         response.__setitem__("Content-type", "application/json")
            #         response.__setitem__("Access-Control-Allow-Origin", "*")
            #         return response
            #     except Exception as ex:
            #         return JsonResponse({'result': 'bad', "mensaje": u"Error al obtener los datos del docente"})

            # if action == 'apiestudiantesvinculacion':
            #     try:
            #         cursor = connection.cursor()
            #         lista_jsondoc = []
            #         cursor.execute("select pr.id, per.cedula, per.apellido1, per.apellido2, per.nombres, car.nombre as carrera, UPPER(pr.nombre) as proyecto , par.horas  from sga_participantesmatrices par left join sga_inscripcion ins on ins.id=par.inscripcion_id left join sga_carrera car on car.id=ins.carrera_id left join sga_persona per on per.id=ins.persona_id  left join sga_proyectosinvestigacion pr on pr.id=par.proyecto_id where par.status=true and par.inscripcion_id is not null and per.cedula= '" + request.GET["cedula"] + "' and pr.tipo=1")
            #         results = cursor.fetchall()
            #         for r in results:
            #             datadoc = {}
            #             datadoc['codiproyecto'] = r[0]
            #             datadoc['identificacion'] = r[1]
            #             datadoc['primerapellido'] = r[2]
            #             datadoc['segundoapellido'] = r[3]
            #             datadoc['nombres'] = r[4]
            #             datadoc['carreras'] = r[5]
            #             datadoc['proyectos'] = r[6]
            #             datadoc['horas'] = r[7]
            #             lista_jsondoc.append(datadoc)
            #         listado_docentes = json.dumps(lista_jsondoc)
            #         response = JsonResponse(lista_jsondoc))
            #         response.__setitem__("Content-type", "application/json")
            #         response.__setitem__("Access-Control-Allow-Origin", "*")
            #         return response
            #     except Exception as ex:
            #         return JsonResponse({'result': 'bad', "mensaje": u"Error al obtener los datos del docente"})

            # if action == 'apidocentesvinculacion':
            #     try:
            #         cursor = connection.cursor()
            #         lista_jsondoc = []
            #         cursor.execute("select per.apellido1, per.apellido2, per.nombres, UPPER(pr.nombre) as proyecto from sga_participantesmatrices par left join sga_profesor ins on ins.id=par.profesor_id left join sga_persona per on per.id=ins.persona_id  left join sga_proyectosinvestigacion pr on pr.id=par.proyecto_id where par.status=true and par.profesor_id is not null  and pr.tipo=1 and pr.id='" + request.GET["proyecto"] + "'")
            #         results = cursor.fetchall()
            #         for r in results:
            #             datadoc = {}
            #             datadoc['primerapellido'] = r[0]
            #             datadoc['segundoapellido'] = r[1]
            #             datadoc['nombres'] = r[2]
            #             datadoc['proyecto'] = r[3]
            #             lista_jsondoc.append(datadoc)
            #         listado_docentes = json.dumps(lista_jsondoc)
            #         response = JsonResponse(lista_jsondoc))
            #         response.__setitem__("Content-type", "application/json")
            #         response.__setitem__("Access-Control-Allow-Origin", "*")
            #         return response
            #     except Exception as ex:
            #         return JsonResponse({'result': 'bad', "mensaje": u"Error al obtener los datos del docente"})

            # if action == 'apiprofesordireccion':
            #     try:
            #         cursor = connection.cursor()
            #         lista_jsondoc = []
            #         cursor.execute("select sex.nombre as sexo, count(p.id) as total from sga_profesor p , sga_persona per, sagest_distributivopersona dp , sga_sexo sex where  per.id=p.persona_id and dp.persona_id=per.id and dp.estadopuesto_id=1 and dp.regimenlaboral_id=2 and sex.id=per.sexo_id and nivelocupacional_id=5 group by sex.nombre;")
            #         results = cursor.fetchall()
            #         for r in results:
            #             datadoc = {}
            #             datadoc['sexo'] = r[0]
            #             datadoc['total'] = r[1]
            #             lista_jsondoc.append(datadoc)
            #         listado_docentes = json.dumps(lista_jsondoc)
            #         response = JsonResponse(lista_jsondoc))
            #         response.__setitem__("Content-type", "application/json")
            #         response.__setitem__("Access-Control-Allow-Origin", "*")
            #         return response
            #     except Exception as ex:
            #         return JsonResponse({'result': 'bad', "mensaje": u"Error al obtener los datos del docente"})

            # if action == 'apipersonalnodocente':
            #     try:
            #         cursor = connection.cursor()
            #         lista_jsondoc = []
            #         cursor.execute("select CASE WHEN dp.regimenlaboral_id=4 THEN 'TRABAJADORES' ELSE 'ADMINISTRATIVOS' END as tipo, COUNT(per.id) from sagest_distributivopersona dp ,sga_persona per where dp.persona_id=per.id and dp.estadopuesto_id=1 and dp.regimenlaboral_id in(1,4) group by dp.regimenlaboral_id;")
            #         results = cursor.fetchall()
            #         for r in results:
            #             datadoc = {}
            #             datadoc['tipo'] = r[0]
            #             datadoc['total'] = r[1]
            #             lista_jsondoc.append(datadoc)
            #         response = HttpResponse(json.dumps(lista_jsondoc))
            #         response.__setitem__("Content-type", "application/json")
            #         response.__setitem__("Access-Control-Allow-Origin", "*")
            #         return response
            #     except Exception as ex:
            #         return JsonResponse({'result': 'bad', "mensaje": u"Error al obtener los datos del docente"})

            if action == 'apilistatelefonia':
                try:
                    #a = request.META.get('HTTP_REFERER')
                    cursor = connection.cursor()
                    lista_jsondoc = []
                    cursor.execute("select p.apellido1 , p.apellido2, initcap(p.nombres),de.descripcion, dep.nombre, p.telefonoextension ,p.emailinst,p.cedula,p.id, (SELECT fperso.foto FROM sga_fotopersona fperso WHERE fperso.persona_id=p.id LIMIT 1) AS foto,p.sexo_id from sga_persona p, auth_user usua, sagest_distributivopersona d, sagest_nivelocupacional nio, sagest_modalidadlaboral mod, sagest_regimenlaboral r, sagest_denominacionpuesto de, sagest_departamento dep where p.id=d.persona_id and d.status=true and d.estadopuesto_id=1 and r.id=d.regimenlaboral_id and usua.id=p.usuario_id and d.nivelocupacional_id=nio.id and d.modalidadlaboral_id=mod.id and de.id=d.denominacionpuesto_id and dep.id=d.unidadorganica_id order by p.apellido1,p.apellido2")
                    results = cursor.fetchall()
                    for r in results:
                        datadoc = {}
                        datadoc['apellidos'] = r[0].lower().capitalize() + ' ' + r[1].lower().capitalize()
                        datadoc['nombres'] = r[2]
                        # datadoc['nombres'] = a
                        datadoc['cargo'] = r[3].lower().capitalize()
                        datadoc['departamento'] = r[4].lower().capitalize()
                        if r[5]=='':
                            numero = 0
                        else:
                            numero = r[5]
                        datadoc['extension'] = numero
                        if r[6] == '':
                            correo = 0
                        else:
                            correo = r[6]
                        datadoc['email'] = correo
                        if r[9]:
                            datadoc['foto'] = "https://sga.unemi.edu.ec/media/" + r[9]
                        else:
                            if r[10] == 2:
                                datadoc['foto'] = "https://sga.unemi.edu.ec/static/images/iconos/hombre.png"
                            else:
                                datadoc['foto'] = "https://sga.unemi.edu.ec/static/images/iconos/mujer.png"
                        # datadoc['email'] = 'PRIVADO'
                        lista_jsondoc.append(datadoc)
                    # response = JsonResponse(lista_jsondoc)
                    response = HttpResponse(json.dumps(lista_jsondoc))
                    response.__setitem__("Content-type", "application/json")
                    response.__setitem__("Access-Control-Allow-Origin", "*")
                    return response

                except Exception as ex:
                    return JsonResponse({'result': 'bad', "mensaje": u"Error al obtener los datos del docente"})

            if action == 'apilistatelefonianew':
                try:
                    datapage = {}
                    search = None
                    if 's' in request.GET:
                        search = request.GET['s'].strip()
                        ss = search.split(' ')
                        if len(ss) == 1:
                            listadopersonalactivo = DistributivoPersona.objects.filter(Q(persona__nombres__icontains=search) |
                                                                                       Q(persona__apellido1__icontains=search) |
                                                                                       Q(persona__apellido2__icontains=search) |
                                                                                       Q(persona__cedula__icontains=search) |
                                                                                       Q(denominacionpuesto__descripcion__icontains=search) |
                                                                                       Q(unidadorganica__nombre__icontains=search) |
                                                                                       Q(persona__telefonoextension__icontains=search) |
                                                                                       Q(persona__emailinst__icontains=search) |
                                                                                       Q(persona__pasaporte__icontains=search), estadopuesto_id=1, nivelocupacional__status=True,status=True)
                        else:
                            listadopersonalactivo = DistributivoPersona.objects.filter((Q(persona__apellido1__icontains=ss[0]) &
                                                                                        Q(persona__apellido2__icontains=ss[1])) |
                                                                                       Q(denominacionpuesto__descripcion__icontains=search) |
                                                                                       Q(unidadorganica__nombre__icontains=search) |
                                                                                       Q(persona__telefonoextension__icontains=search) |
                                                                                       Q(persona__emailinst__icontains=search), estadopuesto_id=1, nivelocupacional__status=True,status=True)
                    else:
                        listadopersonalactivo = DistributivoPersona.objects.filter(estadopuesto_id=1, nivelocupacional__status=True,status=True)
                    paging = MiPaginador(listadopersonalactivo, 12)
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
                    datapage['paging'] = paging
                    datapage['rangospaging'] = paging.rangos_paginado(p)
                    datapage['page'] = page
                    datapage['search'] = search if search else ""
                    datapage['listado'] = page.object_list
                    template = get_template("apitelefonia.html")
                    html_content = template.render(datapage)
                    response = HttpResponse(json.dumps({'listapaginado': html_content }))
                    response.__setitem__("Content-type", "application/json")
                    response.__setitem__("Access-Control-Allow-Origin", "*")
                    return response

                except Exception as ex:
                    return JsonResponse({'result': 'bad', "mensaje": u"Error al obtener los datos del docente"})


            # if action == 'marcadauser':
            #     from datetime import datetime, timedelta
            #     from sagest.models import LogDia, LogMarcada, RegistroMarcada, MarcadasDia, TrabajadorDiaJornada, PermisoInstitucionalDetalle, MarcadaActividad
            #     from faceid.views.adm_marcadas import calculando_marcadasotro
            #     user = authenticate(username=request.GET['user'].lower().strip(), password=request.GET['pass'])
            #     if user is None:
            #         return JsonResponse({"result": "bad", 'mensaje': u'Login fallido, usuario no activo.'})
            #     else:
            #         if Persona.objects.filter(usuario=user).exists():
            #             persona = Persona.objects.filter(usuario=user)[0]
            #             fecha = datetime.now().date()
            #             time = datetime.now()
            #             horaactual = datetime.now().time().hour
            #             minutoactual = datetime.now().time().minute
            #             segundoactual = datetime.now().time().second
            #             if persona.logdia_set.filter(fecha=fecha).exists():
            #                 logdia = persona.logdia_set.filter(fecha=fecha)[0]
            #                 if logdia.persona.historialjornadatrabajador_set.filter(fechainicio__lte=logdia.fecha, fechafin__gte=logdia.fecha).exists():
            #                     logdia.jornada = logdia.persona.historialjornadatrabajador_set.filter(fechainicio__lte=logdia.fecha, fechafin__gte=logdia.fecha).order_by('fechainicio')[0].jornada
            #                 elif logdia.persona.historialjornadatrabajador_set.filter(fechainicio__lte=logdia.fecha, fechafin=None).exists():
            #                     logdia.jornada = logdia.persona.historialjornadatrabajador_set.filter(fechainicio__lte=logdia.fecha, fechafin=None)[0].jornada
            #                 logdia.cantidadmarcadas += 1
            #                 logdia.procesado = False
            #             else:
            #                 logdia = LogDia(persona=persona,
            #                                 fecha=fecha,
            #                                 cantidadmarcadas=1)
            #             logdia.save()
            #             if not logdia.logmarcada_set.filter(time=time).exists():
            #                 registro = LogMarcada(logdia=logdia,
            #                                       time=time,
            #                                       direccion='/adm_marcadas',
            #                                       secuencia=logdia.cantidadmarcadas)
            #                 registro.save(request)
            #             for l in LogDia.objects.filter(persona=persona, status=True, procesado=False).order_by("fecha"):
            #                 if not l.jornada:
            #                     if l.persona.historialjornadatrabajador_set.filter(fechainicio__lte=l.fecha, fechafin__gte=l.fecha).exists():
            #                         l.jornada = l.persona.historialjornadatrabajador_set.filter(fechainicio__lte=l.fecha, fechafin__gte=l.fecha).order_by('fechainicio')[0].jornada
            #                     elif l.persona.historialjornadatrabajador_set.filter(fechainicio__lte=l.fecha, fechafin=None).exists():
            #                         l.jornada = l.persona.historialjornadatrabajador_set.filter(fechainicio__lte=l.fecha, fechafin=None)[0].jornada
            #
            #                 cm = l.logmarcada_set.filter(status=True).count()
            #                 MarcadasDia.objects.filter(persona=l.persona, fecha=l.fecha).delete()
            #                 l.cantidadmarcadas = cm
            #                 if (cm % 2) == 0:
            #                     marini = 1
            #                     for dl in l.logmarcada_set.filter(status=True).order_by("time"):
            #                         if marini == 2:
            #                             salida = dl.time
            #                             marini = 1
            #                             if l.persona.marcadasdia_set.filter(fecha=l.fecha).exists():
            #                                 marcadadia = l.persona.marcadasdia_set.filter(fecha=l.fecha)[0]
            #                             else:
            #                                 marcadadia = MarcadasDia(persona=l.persona,
            #                                                          fecha=l.fecha,
            #                                                          logdia=l,
            #                                                          segundos=0)
            #                                 marcadadia.save()
            #                             if not marcadadia.registromarcada_set.filter(entrada=entrada).exists():
            #                                 registro = RegistroMarcada(marcada=marcadadia,
            #                                                            entrada=entrada,
            #                                                            salida=salida,
            #                                                            segundos=(salida - entrada).seconds)
            #                                 registro.save()
            #                             marcadadia.actualizar_marcadas()
            #                         else:
            #                             entrada = dl.time
            #                             marini += 1
            #                     l.procesado = True
            #                 else:
            #                     l.cantidadmarcadas = 0
            #                 l.save()
            #             calculando_marcadasotro(fecha, fecha, persona)
            #             nombres = persona.apellido1 + ' ' + persona.apellido2 + ' ' + persona.nombres
            #             return JsonResponse({"result": "ok", "persona": nombres, "fecha": fecha, "horaactual": horaactual, "minutoactual": minutoactual, "segundoactual": segundoactual})

            if action == 'apitelefoniatotaldepatamento':
                try:
                    cursor = connection.cursor()
                    lista_jsondoc = []
                    queryss= """
                        SELECT 
                            depar.nombre as departamento, 
                            COUNT(per.id) AS cantidad_personas
                        FROM 
                            sagest_distributivopersona plantilla
                            INNER JOIN sga_persona per ON per.id = plantilla.persona_id
                            INNER JOIN sagest_denominacionpuesto puesto ON puesto.id = plantilla.denominacionpuesto_id 
                            INNER JOIN sagest_departamento depar ON depar.id = plantilla.unidadorganica_id
                        WHERE 
                            plantilla."status" = TRUE 
                            AND plantilla.estadopuesto_id = 1
                        GROUP BY 
                            depar.nombre;
                    """
                    cursor.execute(queryss)
                    results = cursor.fetchall()
                    for r in results:
                        datadoc = {}
                        datadoc['departamento'] = r[0]
                        datadoc['total'] = r[1]
                        lista_jsondoc.append(datadoc)
                    listado_docentes = json.dumps(lista_jsondoc)
                    response = HttpResponse(json.dumps(lista_jsondoc))
                    response.__setitem__("Content-type", "application/json")
                    response.__setitem__("Access-Control-Allow-Origin", "*")
                    return response
                except Exception as ex:
                    return JsonResponse({'result': 'bad', "mensaje": u"Error al obtener los datos del docente"})

            if action == 'apitelefoniatotalsexo':
                try:
                    cursor = connection.cursor()
                    lista_jsondoc = []
                    queryss= """
                        SELECT 
                        sx.nombre as sexo, 
                        COUNT(per.id) AS cantidad_personas
                    FROM 
                        sagest_distributivopersona plantilla
                        INNER JOIN sga_persona per ON per.id = plantilla.persona_id
                        INNER JOIN sagest_denominacionpuesto puesto ON puesto.id = plantilla.denominacionpuesto_id 
                        INNER JOIN sagest_departamento depar ON depar.id = plantilla.unidadorganica_id
                        inner join sga_sexo sx on sx.id=per.sexo_id
                    WHERE 
                        plantilla."status" = TRUE 
                        AND plantilla.estadopuesto_id = 1
                    GROUP BY 
                        sx.nombre;
                    """
                    cursor.execute(queryss)
                    results = cursor.fetchall()
                    for r in results:
                        datadoc = {}
                        datadoc['sexo'] = r[0]
                        datadoc['total'] = r[1]
                        lista_jsondoc.append(datadoc)
                    listado_docentes = json.dumps(lista_jsondoc)
                    response = HttpResponse(json.dumps(lista_jsondoc))
                    response.__setitem__("Content-type", "application/json")
                    response.__setitem__("Access-Control-Allow-Origin", "*")
                    return response
                except Exception as ex:
                    return JsonResponse({'result': 'bad', "mensaje": u"Error al obtener los datos del docente"})

            if action == 'apitelefoniadatos':
                try:
                    cursor = connection.cursor()
                    lista_jsondoc = []
                    queryss= """
                        SELECT per.nombres||' '||per.apellido1||' '||per.apellido2 AS persona, 
                        depar.nombre as departamento,puesto.descripcion as puesto,sx.nombre as sexo, per.email 
                        FROM sagest_distributivopersona plantilla
                        INNER JOIN sga_persona per ON per.id=plantilla.persona_id
                        INNER JOIN sagest_denominacionpuesto puesto ON puesto.id=plantilla.denominacionpuesto_id 
                        inner join sagest_departamento depar on depar.id=plantilla.unidadorganica_id
                        inner join sga_sexo sx on sx.id=per.sexo_id
                        WHERE plantilla."status"=TRUE and plantilla.estadopuesto_id=1
                                            """
                    cursor.execute(queryss)
                    results = cursor.fetchall()
                    for r in results:
                        datadoc = {}
                        datadoc['persona'] = r[0]
                        datadoc['departamento'] = r[1]
                        datadoc['puesto'] = r[2]
                        datadoc['sexo'] = r[3]
                        datadoc['email'] = r[4]
                        lista_jsondoc.append(datadoc)
                    listado_docentes = json.dumps(lista_jsondoc)
                    response = HttpResponse(json.dumps(lista_jsondoc))
                    response.__setitem__("Content-type", "application/json")
                    response.__setitem__("Access-Control-Allow-Origin", "*")
                    return response
                except Exception as ex:
                    return JsonResponse({'result': 'bad', "mensaje": u"Error al obtener los datos del docente"})

            if action == 'apipreferenciaactividad':
                try:
                    lista_jsondoc = []
                    idperiodo = request.GET['idperiodo']
                    preferenciasdoc = PreferenciaDetalleActividadesCriterio.objects.filter(criteriodocenciaperiodo__periodo_id=idperiodo, criteriodocenciaperiodo__isnull=False, status=True)
                    preferenciasinv = PreferenciaDetalleActividadesCriterio.objects.filter(criterioinvestigacionperiodo__periodo_id=idperiodo, criterioinvestigacionperiodo__isnull=False, status=True)
                    preferenciasges = PreferenciaDetalleActividadesCriterio.objects.filter(criteriogestionperiodo__periodo_id=idperiodo, criteriogestionperiodo__isnull=False, status=True)
                    for prefe in preferenciasdoc:
                        datadoc = {}
                        datadoc['Profesor'] = prefe.profesor.persona.apellido1 + ' ' + prefe.profesor.persona.apellido2 + ' ' + prefe.profesor.persona.nombres
                        datadoc['Actividad'] = prefe.criteriodocenciaperiodo.actividad.nombre
                        datadoc['Tipo'] = 'DOCENCIA'
                        lista_jsondoc.append(datadoc)

                    for prefe in preferenciasinv:
                        datadoc = {}
                        datadoc['Profesor'] = prefe.profesor.persona.apellido1 + ' ' + prefe.profesor.persona.apellido2 + ' ' + prefe.profesor.persona.nombres
                        datadoc['Actividad'] = prefe.criterioinvestigacionperiodo.actividad.nombre
                        datadoc['Tipo'] = 'INVESTIGACIÓN'
                        lista_jsondoc.append(datadoc)

                    for prefe in preferenciasges:
                        datadoc = {}
                        datadoc['Profesor'] = prefe.profesor.persona.apellido1 + ' ' + prefe.profesor.persona.apellido2 + ' ' + prefe.profesor.persona.nombres
                        datadoc['Actividad'] = prefe.criteriogestionperiodo.actividad.nombre
                        datadoc['Tipo'] = 'GESTIÓN'
                        lista_jsondoc.append(datadoc)

                    response = HttpResponse(json.dumps(lista_jsondoc))
                    response.__setitem__("Content-type", "application/json")
                    response.__setitem__("Access-Control-Allow-Origin", "*")
                    return response

                except Exception as ex:
                    return JsonResponse({'result': 'bad', "mensaje": u"Error al obtener los datos del docente"})

            if action == 'apitelefoniatotaldepatamentosexo':
                try:
                    cursor = connection.cursor()
                    lista_jsondoc = []
                    queryss= """
                        SELECT 
                        depar.nombre AS departamento,
                        SUM(CASE WHEN sx.id = 1 THEN 1 ELSE 0 END) AS MUJER,
                        SUM(CASE WHEN sx.id = 2 THEN 1 ELSE 0 END) AS HOMBRE
                    FROM 
                        sagest_distributivopersona plantilla
                        INNER JOIN sga_persona per ON per.id = plantilla.persona_id
                        INNER JOIN sagest_denominacionpuesto puesto ON puesto.id = plantilla.denominacionpuesto_id 
                        INNER JOIN sagest_departamento depar ON depar.id = plantilla.unidadorganica_id
                        INNER JOIN sga_sexo sx ON sx.id = per.sexo_id
                    WHERE 
                        plantilla."status" = TRUE 
                        AND plantilla.estadopuesto_id = 1
                    GROUP BY 
                        depar.nombre;
                    """
                    cursor.execute(queryss)
                    results = cursor.fetchall()
                    for r in results:
                        datadoc = {}
                        datadoc['departamento'] = r[0]
                        datadoc['mujer'] = r[1]
                        datadoc['hombre'] = r[2]
                        lista_jsondoc.append(datadoc)
                    listado_docentes = json.dumps(lista_jsondoc)
                    response = HttpResponse(json.dumps(lista_jsondoc))
                    response.__setitem__("Content-type", "application/json")
                    response.__setitem__("Access-Control-Allow-Origin", "*")
                    return response
                except Exception as ex:
                    return JsonResponse({'result': 'bad', "mensaje": u"Error al obtener los datos del docente"})

            if action == 'apitelefoniadepartamentos':
                try:
                    cursor = connection.cursor()
                    lista_jsondoc = []
                    queryss= """ SELECT distinct depar.nombre as departamento
                        FROM sagest_distributivopersona plantilla
                        inner join sagest_departamento depar on depar.id=plantilla.unidadorganica_id
                        WHERE plantilla."status"=TRUE and plantilla.estadopuesto_id=1 """
                    cursor.execute(queryss)
                    results = cursor.fetchall()
                    for r in results:
                        datadoc = {}
                        datadoc['departamento'] = r[0]
                        lista_jsondoc.append(datadoc)
                    listado_docentes = json.dumps(lista_jsondoc)
                    response = HttpResponse(json.dumps(lista_jsondoc))
                    response.__setitem__("Content-type", "application/json")
                    response.__setitem__("Access-Control-Allow-Origin", "*")
                    return response
                except Exception as ex:
                    return JsonResponse({'result': 'bad', "mensaje": u"Error al obtener los datos del docente"})

            # if action == 'apilistatelefoniapdf':
            #     try:
            #         #a = request.META.get('HTTP_REFERER')
            #         data = {}
            #         cursor = connection.cursor()
            #         lista_jsondoc = []
            #         cursor.execute("select p.apellido1 , p.apellido2, p.nombres,de.descripcion, dep.nombre, p.telefonoextension ,p.emailinst,p.cedula,p.id from sga_persona p, auth_user usua, sagest_distributivopersona d, sagest_nivelocupacional nio, sagest_modalidadlaboral mod, sagest_regimenlaboral r, sagest_denominacionpuesto de, sagest_departamento dep where p.id=d.persona_id and d.status=true and d.estadopuesto_id=1 and r.id=d.regimenlaboral_id and usua.id=p.usuario_id and d.nivelocupacional_id=nio.id and d.modalidadlaboral_id=mod.id and de.id=d.denominacionpuesto_id and dep.id=d.unidadorganica_id order by p.apellido1,p.apellido2")
            #         results = cursor.fetchall()
            #         data['result'] = results
            #
            #         return conviert_html_to_pdf(
            #             'api_pdf/telefonia_pdf.html',
            #             {
            #                 'pagesize': 'A4',
            #                 'data': data,
            #             }
            #         )
            #     except Exception as ex:
            #         pass

            if action == 'consultaperfiles':
                try:
                    lista_jsondoc = []
                    datadoc = {}
                    if Persona.objects.filter(cedula=request.GET["cedula"]).exists():
                        person = Persona.objects.get(cedula=request.GET["cedula"])
                        datadoc['confirma'] = 1
                        lista_jsondoc.append(datadoc)
                        response = HttpResponse(json.dumps(lista_jsondoc))
                    else:
                        datadoc['confirma'] = 0
                        lista_jsondoc.append(datadoc)
                        response = HttpResponse(json.dumps(lista_jsondoc))
                    response.__setitem__("Content-type", "application/json")
                    response.__setitem__("Access-Control-Allow-Origin", "*")
                    return response
                except Exception as ex:
                    return JsonResponse({'result': 'bad', "mensaje": u"Error al obtener los datos del docente"})

            if action == 'ingresotable':
                try:
                    lista_jsondoc = []
                    listas = request.GET["listas"]
                    ippermiso = request.GET["ippermiso"]
                    listaip = variable_valor('IP_BIBLIOTECA')
                    elementos = listaip.split(',')
                    permiso = 0
                    for elemento in elementos:
                        if elemento == ippermiso:
                            permiso = 1
                            break
                    if permiso==1:
                        codcedula = request.GET["codcedula"]
                        tip = request.GET["tip"]
                        elementos = listas.split(',')
                        if tip == '1':
                            codmateria = request.GET["codmateria"]
                            codpersona = request.GET["codpersona"]
                            for elemento in elementos:
                                ingresos = VisitasBiblioteca(persona_id=codpersona, materia_id=codmateria, libro_id=elemento)
                                ingresos.save()
                        if tip == '2':
                            tipoperfil = request.GET["tipoperfil"]
                            codpersona = request.GET["codpersona"]
                            for elemento in elementos:
                                ingresos = VisitasBiblioteca(persona_id=codpersona, libro_id=elemento, tipoperfil=tipoperfil)
                                ingresos.save()
                        if tip == '3':
                            tipoperfil = request.GET["tipoperfil"]
                            for elemento in elementos:
                                ingresos = VisitasBiblioteca(cedula=codcedula, libro_id=elemento, tipoperfil=tipoperfil)
                                ingresos.save()
                        datadoc = {}
                        datadoc['respuesta'] = 'ok'
                    else:
                        datadoc = {}
                        datadoc['respuesta'] = 'bad'
                    lista_jsondoc.append(datadoc)
                    response = HttpResponse(json.dumps(lista_jsondoc))
                    response.__setitem__("Content-type", "application/json")
                    response.__setitem__("Access-Control-Allow-Origin", "*")
                    return response
                except Exception as ex:
                    return JsonResponse({'result': 'bad', "mensaje": u"Error al obtener los datos del docente"})

            if action == 'listaperfiles':
                try:
                    lista_jsondoc = []
                    tienedatos = True
                    if Persona.objects.filter(cedula=request.GET["cedula"]).exists():

                        person = Persona.objects.get(cedula=request.GET["cedula"])
                        listaperfiles = person.mis_perfilesusuarios()
                        for lista in listaperfiles:
                            datadoc = {}
                            if lista.es_estudiante():
                                datadoc['nom_tipo'] = 1
                            if lista.es_administrativo():
                                datadoc['nom_tipo'] = 2
                            if lista.es_profesor():
                                datadoc['nom_tipo'] = 3
                            if lista.es_externo():
                                datadoc['nom_tipo'] = 4
                            datadoc['exite'] = True
                            datadoc['codpersona'] = person.id
                            datadoc['nom_persona'] = person.apellido1 + ' ' + person.apellido2 + ' ' + person.nombres
                            datadoc['nom_a1'] = lista.tipo()
                            lista_jsondoc.append(datadoc)
                    else:
                        tienedatos = False
                    response = HttpResponse(json.dumps({"existe":tienedatos,"results":lista_jsondoc}))
                    response.__setitem__("Content-type", "application/json")
                    response.__setitem__("Access-Control-Allow-Origin", "*")
                    return response
                except Exception as ex:
                    return JsonResponse({'result': 'bad', "mensaje": u"Error al obtener los datos del docente"})

            if action == 'apiasignaturamatricula':
                try:
                    lista_jsondoc = []
                    cedula = request.GET["cedula"]
                    masignaturas = MateriaAsignada.objects.filter(matricula__inscripcion__persona__cedula=cedula, matricula__cerrada=False, status=True).order_by('materia__asignatura__nombre')
                    for lista in masignaturas:
                        datadoc = {}
                        datadoc['nom_a1'] = lista.matricula.inscripcion.persona.apellido1 + ' ' + lista.matricula.inscripcion.persona.apellido2 + ' ' + lista.matricula.inscripcion.persona.nombres
                        datadoc['nom_a2'] = lista.materia.asignatura.nombre
                        datadoc['nom_a3'] = lista.materia.id
                        lista_jsondoc.append(datadoc)
                    response = HttpResponse(json.dumps(lista_jsondoc))
                    response.__setitem__("Content-type", "application/json")
                    response.__setitem__("Access-Control-Allow-Origin", "*")
                    return response
                except Exception as ex:
                    return JsonResponse({'result': 'bad', "mensaje": u"Error al obtener los datos del docente"})

            if action == 'listalibros':
                try:
                    lista_jsondoc = []
                    nlibros = request.GET["q"]
                    listalibros = LibroKohaProgramaAnaliticoAsignatura.objects.filter(nombre__icontains=nlibros,status=True).order_by('nombre')
                    for lista in listalibros:
                        datadoc = {}
                        datadoc['id'] = lista.id
                        datadoc['name'] = lista.nombre.upper()
                        datadoc['nameautor'] = lista.autor.upper()
                        lista_jsondoc.append(datadoc)
                    response = HttpResponse(json.dumps({"results":lista_jsondoc}))
                    response.__setitem__("Content-type", "application/json")
                    response.__setitem__("Access-Control-Allow-Origin", "*")
                    return response
                except Exception as ex:
                    return JsonResponse({'result': 'bad', "mensaje": u"Error al obtener los datos del docente"})

            # if action == 'tokenbiblioteca':
            #     try:
            #         lista_jsondoc = []
            #         datadoc = {}
            #         token = request.GET["token"]
            #         if token == variable_valor('TOKEN_BIBLIOTECA'):
            #             datadoc['respuesta'] = token
            #         else:
            #             datadoc = {}
            #             datadoc['respuesta'] = 'bad'
            #         lista_jsondoc.append(datadoc)
            #         response = HttpResponse(json.dumps(lista_jsondoc))
            #         response.__setitem__("Content-type", "application/json")
            #         response.__setitem__("Access-Control-Allow-Origin", "*")
            #         return response
            #     except Exception as ex:
            #         return JsonResponse({'result': 'bad', "mensaje": u"Error al obtener los datos del docente"})

            # if action == 'consultarlibro':
            #     try:
            #         lista_jsondoc = []
            #         ncodigo = request.GET["codigo"]
            #         listalibros = LibroKohaProgramaAnaliticoAsignatura.objects.get(pk=ncodigo,status=True)
            #         datadoc = {}
            #         datadoc['id'] = listalibros.id
            #         datadoc['name'] = listalibros.nombre.upper()
            #         datadoc['nameautor'] = listalibros.autor.upper()
            #         lista_jsondoc.append(datadoc)
            #         response = HttpResponse(json.dumps(lista_jsondoc))
            #         response.__setitem__("Content-type", "application/json")
            #         response.__setitem__("Access-Control-Allow-Origin", "*")
            #         return response
            #     except Exception as ex:
            #         return JsonResponse({'result': 'bad', "mensaje": u"Error al obtener los datos del docente"})

            # if action == 'apilistadobibliografia':
            #     try:
            #         lista_jsondoc = []
            #         materiasverificadas = []
            #         codigomateria = request.GET["codigomateria"]
            #         librosbasicos = DetalleSilaboSemanalBibliografia.objects.values_list('bibliografiaprogramaanaliticoasignatura__librokohaprogramaanaliticoasignatura__id','bibliografiaprogramaanaliticoasignatura__librokohaprogramaanaliticoasignatura__nombre','bibliografiaprogramaanaliticoasignatura__librokohaprogramaanaliticoasignatura__autor').filter(silabosemanal__silabo__materia_id=codigomateria).distinct()
            #         if librosbasicos:
            #             for lista1 in librosbasicos:
            #                 materiasverificadas.append(lista1[0])
            #         libroscomplementarios = DetalleSilaboSemanalBibliografiaDocente.objects.values_list('librokohaprogramaanaliticoasignatura__id','librokohaprogramaanaliticoasignatura__nombre','librokohaprogramaanaliticoasignatura__autor').filter(silabosemanal__silabo__materia_id=codigomateria).distinct()
            #         if librosbasicos:
            #             for lista2 in libroscomplementarios:
            #                 materiasverificadas.append(lista2[0])
            #         todoslibros = LibroKohaProgramaAnaliticoAsignatura.objects.filter(pk__in=materiasverificadas,status=True).distinct()
            #         for libros in todoslibros:
            #             datadoc = {}
            #             datadoc['codlibro'] = libros.id
            #             datadoc['nomlibro'] = libros.nombre.upper()
            #             datadoc['nomautor'] = libros.autor.upper()
            #             lista_jsondoc.append(datadoc)
            #         response = HttpResponse(json.dumps(lista_jsondoc))
            #         response.__setitem__("Content-type", "application/json")
            #         response.__setitem__("Access-Control-Allow-Origin", "*")
            #         return response
            #     except Exception as ex:
            #         return JsonResponse({'result': 'bad', "mensaje": u"Error al obtener los datos del docente"})

            if action == 'apilistaarticulos':
                try:
                    cursor = connection.cursor()
                    lista_jsondoc = []
                    sql = """
                        select per.apellido1,per.apellido2,per.nombres,ar.nombre as articulos,extract(year from  ar.fechapublicacion) as fecha ,rev.nombre as revista,
                                   (select string_agg(base.nombre,',' ) from sga_baseindexadainvestigacion base,sga_articulosbaseindexada bindex 
                                   where base.id=bindex.baseindexada_id and bindex.articulo_id=ar.id and base.status=True 
                                     and bindex.status=True) as bases,
                                   ar.enlace ,
                                   COALESCE((SELECT de.archivo FROM sga_detalleevidencias AS de 
								   		  WHERE de.evidencia_id=1 and de.articulo_id=ar.id and de.status=True LIMIT 1),'') AS enlaceinterno,
											  acon.nombre AS areaconocimiento 
                                   from sga_articuloinvestigacion ar,sga_participantesarticulos par, sga_profesor pro,sga_persona per,
                                   sga_revistainvestigacion rev,sga_areaconocimientotitulacion AS acon 
                                   where ar.id=par.articulo_id and par.profesor_id=pro.id and pro.persona_id=per.id and ar.revista_id=rev.id 
                                   and par.status=True and ar.status=True
								AND ar.areaconocimiento_id=acon.id 
                                
                    """
                    idarea=0
                    if 'ida' in request.GET:
                        idarea = int(request.GET['ida'])
                        if idarea > 0:
                            sql = sql + " and acon.id=" + str(idarea)

                    sql = sql + " ORDER BY ar.fechapublicacion DESC,per.apellido1,per.apellido2"

                    cursor.execute(sql)
                    results = cursor.fetchall()
                    for r in results:
                        datadoc = {}
                        datadoc['apellidos'] = u"%s %s %s"%(r[0] if r[0] else "",r[1] if r[1] else "",r[2] if r[2] else "")
                        datadoc['articulos'] = u"%s" % r[3]
                        datadoc['fecha'] = u"%s" % r[4]
                        datadoc['revista'] = u"%s" % r[5]
                        datadoc['base'] = u"%s" % r[6]
                        datadoc['links'] = u"%s" % r[7]
                        datadoc['enlaceinterno'] = u"%s" % r[8]
                        lista_jsondoc.append(datadoc)
                    response = HttpResponse(json.dumps(lista_jsondoc))
                    response.__setitem__("Content-type", "application/json")
                    response.__setitem__("Access-Control-Allow-Origin", "*")
                    return response
                except Exception as ex:
                    return JsonResponse({'result': 'bad', "mensaje": u"Error al obtener los datos del docente %s"%ex})

            if action == 'apirevistas':
                try:
                    lista_jsondoc = []
                    listadorevistas = RevistaInvestigacion.objects.filter(status=True)
                    for rev in listadorevistas:
                        datadoc = {}
                        datadoc['nombre'] = rev.nombre
                        # datadoc['institucion'] = rev.institucion
                        datadoc['tipo'] = rev.get_tipo_display()
                        datadoc['codigoissn'] = rev.codigoissn
                        datadoc['enlace'] = rev.enlace
                        # datadoc['cuartil'] = rev.get_cuartil_display()
                        # datadoc['sjr'] = rev.sjr
                        # datadoc['jcr'] = rev.jcr
                        # datadoc['tiporegistro'] = rev.get_tiporegistro_display()
                        # datadoc['borrador'] = rev.borrador
                        lista_jsondoc.append(datadoc)
                    response = HttpResponse(json.dumps(lista_jsondoc))
                    response.__setitem__("Content-type", "application/json")
                    response.__setitem__("Access-Control-Allow-Origin", "*")
                    return response

                except Exception as ex:
                    return JsonResponse({'result': 'bad', "mensaje": u"Error al obtener los datos del docente"})

            elif action == 'apiareasconocimiento':
                try:
                    lista_jsondoc = []
                    for area in AreaConocimientoTitulacion.objects.filter(status=True).order_by('nombre'):
                        datadoc = {}
                        datadoc['codigo'] = area.id
                        datadoc['nombre'] = area.nombre
                        lista_jsondoc.append(datadoc)
                    response = HttpResponse(json.dumps(lista_jsondoc))
                    response.__setitem__("Content-type", "application/json")
                    response.__setitem__("Access-Control-Allow-Origin", "*")
                    return response
                except Exception as ex:
                    response = HttpResponse(json.dumps({'result': 'bad', 'mensaje': 'Error al consultar áreas de conocimiento'}))
                    response.__setitem__("Content-type", "application/json")
                    response.__setitem__("Access-Control-Allow-Origin", "*")
                    return response

            if action == 'apiinvestigadores':
                try:
                    lista_jsondoc = []
                    listadoautores = Profesor.objects.filter(pk__in=ParticipantesArticulos.objects.values_list('profesor_id').filter(status=True), status=True).distinct()
                    for autor in listadoautores:
                        datadoc = {}
                        datadoc['nombrecompleto'] = autor.persona.apellido1 + ' ' + autor.persona.apellido2 + ' ' + autor.persona.nombres
                        datadoc['correoinstitucional'] = autor.persona.emailinst
                        datadoc['orcid'] = autor.persona.identificador_orcid()
                        lista_jsondoc.append(datadoc)
                    response = HttpResponse(json.dumps(lista_jsondoc))
                    response.__setitem__("Content-type", "application/json")
                    response.__setitem__("Access-Control-Allow-Origin", "*")
                    return response

                except Exception as ex:
                    return JsonResponse({'result': 'bad', "mensaje": u"Error al obtener los datos del docente"})

            if action == 'apibasesindexadas':
                try:
                    lista_jsondoc = []
                    listbases = BaseIndexadaInvestigacion.objects.filter(status=True).distinct()
                    for base in listbases:
                        datadoc = {}
                        datadoc['nombre'] = base.nombre
                        datadoc['tipo'] = base.get_tipo_display() if base.tipo else ''
                        lista_jsondoc.append(datadoc)
                    response = HttpResponse(json.dumps(lista_jsondoc))
                    response.__setitem__("Content-type", "application/json")
                    response.__setitem__("Access-Control-Allow-Origin", "*")
                    return response

                except Exception as ex:
                    return JsonResponse({'result': 'bad', "mensaje": u"Error al obtener los datos"})

            if action == 'apitotaltiporevista':
                try:
                    revistasregionalesid_ = RevistaInvestigacionBase.objects.filter(status=True, baseindexada__tipo=1).values_list('revista__id', flat=True)
                    regionales_count = ArticuloInvestigacion.objects.values('id').filter(status=True, revista__in=revistasregionalesid_).count()
                    revistasidcientificas_ = RevistaInvestigacionBase.objects.filter(status=True, baseindexada__tipo=2).values_list('revista__id', flat=True)
                    cientificas_count = ArticuloInvestigacion.objects.values('id').filter(status=True, revista__in=revistasidcientificas_).count()
                    datadoc = {}
                    datadoc['regionales'] = regionales_count
                    datadoc['cientificas'] = cientificas_count
                    response = HttpResponse(json.dumps(datadoc))
                    response.__setitem__("Content-type", "application/json")
                    response.__setitem__("Access-Control-Allow-Origin", "*")
                    return response

                except Exception as ex:
                    return JsonResponse({'result': 'bad', "mensaje": u"Error al obtener los datos del docente"})

            if action == 'apitotalareapublicacion':
                try:
                    totalporarea = ArticuloInvestigacion.objects.filter(status=True).values('areaconocimiento').annotate(totalarticulos=Count('areaconocimiento')).values('areaconocimiento__nombre', 'totalarticulos').order_by('-totalarticulos')
                    lista_jsondoc = []
                    for area in totalporarea:
                        datadoc = {}
                        datadoc['area'] = f'{area["areaconocimiento__nombre"]}'
                        datadoc['totalarticulos'] = area["totalarticulos"]
                        lista_jsondoc.append(datadoc)
                    response = HttpResponse(json.dumps(lista_jsondoc))
                    response.__setitem__("Content-type", "application/json")
                    response.__setitem__("Access-Control-Allow-Origin", "*")
                    return response

                except Exception as ex:
                    return JsonResponse({'result': 'bad', "mensaje": u"Error al obtener los datos"})

            if action == 'apirankingautorespublicacion':
                try:
                    rankingautores = ParticipantesArticulos.objects.filter(status=True, tipo=1).values('profesor').annotate(totalarticulos=Count('profesor')).values('profesor__persona__nombres', 'profesor__persona__apellido1',  'profesor__persona__apellido2', 'totalarticulos').order_by('-totalarticulos')[:10]
                    lista_jsondoc = []
                    for autor in rankingautores:
                        datadoc = {}
                        datadoc['autor'] = f'{autor["profesor__persona__nombres"]} {autor["profesor__persona__apellido1"]} {autor["profesor__persona__apellido2"]}'
                        datadoc['totalarticulos'] = autor["totalarticulos"]
                        lista_jsondoc.append(datadoc)
                    response = HttpResponse(json.dumps(lista_jsondoc))
                    response.__setitem__("Content-type", "application/json")
                    response.__setitem__("Access-Control-Allow-Origin", "*")
                    return response

                except Exception as ex:
                    return JsonResponse({'result': 'bad', "mensaje": u"Error al obtener los datos"})

            if action == 'apigrupoautores':
                try:
                    lista_jsondoc = []
                    if 'area' in request.GET:
                        area_ = request.GET['area']
                        qsarticulos = ArticuloInvestigacion.objects.filter(status=True, areaconocimiento__id=area_).order_by('nombre')
                        for articulo_ in qsarticulos:
                            datadoc = {}
                            datadoc['paper'] = f'{articulo_.nombre}'
                            datadoc['autores'] = [ x.profesor.persona.nombre_completo() for x in articulo_.participantesarticulos_set.filter(status=True, profesor__isnull=False).order_by('tipo')]
                            lista_jsondoc.append(datadoc)
                    else:
                        return JsonResponse({'result': 'bad', "mensaje": u"Debe enviar código de área"})
                    response = HttpResponse(json.dumps(lista_jsondoc))
                    response.__setitem__("Content-type", "application/json")
                    response.__setitem__("Access-Control-Allow-Origin", "*")
                    return response

                except Exception as ex:
                    return JsonResponse({'result': 'bad', "mensaje": u"Error al obtener los datos"})

            if action == 'apitotales':
                try:
                    data = {}
                    cursor = connection.cursor()
                    sql = """SELECT distinct ar.nombre as articulos, extract(year from  ar.fechapublicacion) as fecha ,rev.nombre as revista, ar.doy
                             from sga_articuloinvestigacion ar, sga_revistainvestigacion rev,sga_areaconocimientotitulacion AS acon 
                             where ar.revista_id=rev.id and ar.status=True AND ar.areaconocimiento_id=acon.id ORDER BY ar.nombre"""
                    cursor.execute(sql)
                    results = cursor.fetchall()
                    data['totalarticulos'] = len(results)
                    data['totalrevistas'] = RevistaInvestigacion.objects.values('id').filter(status=True).count()
                    data['totalareasconocimientos'] = AreaConocimientoTitulacion.objects.values('id').filter(status=True).count()
                    data['totalautores'] = Profesor.objects.values('id').filter(pk__in=ParticipantesArticulos.objects.values_list('profesor_id').filter(status=True), status=True).count()
                    response = HttpResponse(json.dumps(data))
                    response.__setitem__("Content-type", "application/json")
                    response.__setitem__("Access-Control-Allow-Origin", "*")
                    return response

                except Exception as ex:
                    return JsonResponse({'result': 'bad', "mensaje": u"Error al obtener los datos del docente"})

            if action == 'apiarticulosanios':
                try:
                    from datetime import datetime
                    data = {}
                    cursor = connection.cursor()
                    listanios = []
                    for l in range(0, 5):
                        listanios.append(int(datetime.now().year) - l)
                    for l in listanios:
                        sql = f"""SELECT distinct ar.nombre as articulos, extract(year from  ar.fechapublicacion) as fecha ,rev.nombre as revista, ar.doy
                                 from sga_articuloinvestigacion ar, sga_revistainvestigacion rev,sga_areaconocimientotitulacion AS acon 
                                 where ar.revista_id=rev.id and ar.status=True AND ar.areaconocimiento_id=acon.id and extract(year from  ar.fechapublicacion)={l} ORDER BY ar.nombre"""
                        cursor.execute(sql)
                        data[l] = len(cursor.fetchall())
                    response = HttpResponse(json.dumps(data))
                    response.__setitem__("Content-type", "application/json")
                    response.__setitem__("Access-Control-Allow-Origin", "*")
                    return response

                except Exception as ex:
                    return JsonResponse({'result': 'bad', "mensaje": u"Error al obtener los datos del docente"})

            if action == 'apiarticulos':
                try:
                    cursor = connection.cursor()
                    lista_jsondoc = []
                    sql = """
                           SELECT distinct ar.nombre as articulos,
                            extract(year from  ar.fechapublicacion) as fecha ,rev.nombre as revista,
                            ar.doy
                            from sga_articuloinvestigacion ar, 
                            sga_revistainvestigacion rev,sga_areaconocimientotitulacion AS acon 
                            where ar.revista_id=rev.id 
                            and ar.status=True
                            AND ar.areaconocimiento_id=acon.id 
                            ORDER BY ar.nombre

                                        """
                    cursor.execute(sql)
                    results = cursor.fetchall()
                    for r in results:
                        datadoc = {}
                        datadoc['nombre'] = u"%s"%(r[0] if r[0] else "")
                        datadoc['revista'] = u"%s"%(r[2] if r[2] else "")
                        datadoc['anio'] = u"%s"%(r[1] if r[1] else "")
                        datadoc['doi'] = u"%s"%(r[3] if r[3] else "")
                        lista_jsondoc.append(datadoc)
                    response = HttpResponse(json.dumps(lista_jsondoc))
                    response.__setitem__("Content-type", "application/json")
                    response.__setitem__("Access-Control-Allow-Origin", "*")
                    return response

                except Exception as ex:
                    return JsonResponse({'result': 'bad', "mensaje": u"Error al obtener los datos. %s"%ex})

            if action == 'apilistaarticulos2':
                try:
                    idarea = int(request.GET['ida'])
                    cursor = connection.cursor()
                    lista_jsondoc = []

                    sql = """
                            SELECT per.id as cedula, per.apellido1 || ' ' || per.apellido2 || ' ' || per.nombres AS persona,ar.nombre as articulos,extract(year from  ar.fechapublicacion) as fecha ,rev.nombre as revista,
                                    (select base.nombre
                                    from sga_baseindexadainvestigacion base,sga_articulosbaseindexada bindex 
                                    where base.id=bindex.baseindexada_id and bindex.articulo_id=ar.id and base.status=True 
                                    and bindex.status=TRUE ORDER BY base.id LIMIT 1 ) as bases,
                                    (select case WHEN base.tipo=1 THEN 'REGIONALES' WHEN base.tipo=2 THEN 'CIENTIFICAS' end
                                    from sga_baseindexadainvestigacion base,sga_articulosbaseindexada bindex 
                                    where base.id=bindex.baseindexada_id and bindex.articulo_id=ar.id and base.status=True 
                                    and bindex.status=TRUE ORDER BY base.id LIMIT 1 ) as tipobases,
                                    acon.nombre AS areaconocimiento 
                                    from sga_articuloinvestigacion ar,sga_participantesarticulos par, sga_profesor pro,sga_persona per,
                                    sga_revistainvestigacion rev,sga_areaconocimientotitulacion AS acon 
                                    where ar.id=par.articulo_id and par.profesor_id=pro.id and pro.persona_id=per.id and ar.revista_id=rev.id 
                                    and par.status=True and ar.status=True
                                    AND ar.areaconocimiento_id=acon.id 

                        """


                    sql = sql + " ORDER BY ar.fechapublicacion DESC,per.apellido1,per.apellido2"

                    cursor.execute(sql)
                    results = cursor.fetchall()
                    for r in results:
                        if r[3] !=None and r[5]!=None:
                            datadoc = {}
                            datadoc['codigo'] = r[0]
                            datadoc['apellidos'] = r[1]
                            datadoc['articulos'] = r[2]
                            datadoc['fecha'] = r[3]
                            datadoc['revista'] = r[4]
                            datadoc['base'] = r[5]
                            datadoc['tipobases'] = r[6]
                            datadoc['area'] = r[7]
                            lista_jsondoc.append(datadoc)
                    response = HttpResponse(json.dumps(lista_jsondoc))
                    response.__setitem__("Content-type", "application/json")
                    response.__setitem__("Access-Control-Allow-Origin", "*")
                    return response

                except Exception as ex:
                    return JsonResponse({'result': 'bad', "mensaje": u"Error al obtener los datos del docente"})

            elif action == 'areaconocimiento':
                try:
                    lista = []
                    for area in AreaConocimientoTitulacion.objects.filter(status=True).order_by('nombre'):
                        datosarea = {'id': area.id,
                                     'nombre': area.nombre}
                        lista.append(datosarea)

                    response = HttpResponse(json.dumps({'result': 'ok', 'mensaje': 'Este es un mensaje', 'areasconocimiento': lista}))
                    response.__setitem__("Content-type", "application/json")
                    response.__setitem__("Access-Control-Allow-Origin", "*")
                    return response
                except Exception as ex:
                    response = HttpResponse(json.dumps({'result': 'bad', 'mensaje': 'Error al consultar áreas de conocimiento'}))
                    response.__setitem__("Content-type", "application/json")
                    response.__setitem__("Access-Control-Allow-Origin", "*")
                    return response

            if action == 'apilistaarticulosdocente':
                try:
                    cursor = connection.cursor()
                    lista_jsondoc = []
                    cursor.execute("select per.apellido1,per.apellido2,per.nombres,upper(ar.nombre) as articulos,extract(year from  ar.fechapublicacion) as fecha ,upper(rev.nombre) as revista,(select string_agg(base.nombre,',' ) from sga_baseindexadainvestigacion base,sga_articulosbaseindexada bindex where base.id=bindex.baseindexada_id and bindex.articulo_id=ar.id and base.status=True and bindex.status=True) as bases,ar.enlace,ar.volumen,ar.paginas,rev.codigoissn from sga_articuloinvestigacion ar,sga_participantesarticulos par, sga_profesor pro,sga_persona per,sga_revistainvestigacion rev where ar.id=par.articulo_id and par.profesor_id=pro.id and pro.persona_id=per.id and ar.revista_id=rev.id and par.status=True and ar.status=True and per.cedula='" + request.GET["cedula"] + "' order by 5 desc,per.apellido1,per.apellido2")
                    results = cursor.fetchall()
                    for r in results:
                        datadoc = {}
                        datadoc['apellidos'] = '%s %s %s' % (r[0], r[1], r[2])
                        datadoc['articulos'] = '%s' % r[3]
                        datadoc['fecha'] = '%s' % r[4]
                        datadoc['revista'] = '%s' % r[5]
                        datadoc['base'] = '%s' % r[6]
                        datadoc['links'] = '%s' % r[7]
                        datadoc['volumen'] = '%s' % r[8]
                        datadoc['paginas'] = '%s' % r[9]
                        datadoc['codigoissn'] = '%s' % r[10]
                        lista_jsondoc.append(datadoc)
                    response = HttpResponse(json.dumps(lista_jsondoc))
                    response.__setitem__("Content-type", "application/json")
                    response.__setitem__("Access-Control-Allow-Origin", "*")
                    return response

                except Exception as ex:
                    return JsonResponse({'result': 'bad', "mensaje": u"Error al obtener los datos del docente"})

            if action == 'apilistadomapeo':
                from datetime import datetime
                try:
                    lista_jsondoc = []
                    hoy = datetime.now().date()
                    if Persona.objects.filter(cedula=request.GET['identificacion']):
                        nompersona = Persona.objects.get(cedula=request.GET['identificacion'])
                        if nompersona.es_estudiante():
                            # insi = Inscripcion.objects.get(persona=nompersoona)
                            if Matricula.objects.filter(inscripcion__persona=nompersona, nivel__periodo__inicio__lte=hoy,nivel__periodo__fin__gte=hoy):
                                matri = Matricula.objects.get(inscripcion__persona=nompersona, nivel__periodo__inicio__lte=hoy,nivel__periodo__fin__gte=hoy)
                                datadoc = {}
                                datadoc['personaactiva'] = 'alumno'
                                datadoc['ci'] = matri.inscripcion.persona.cedula
                                datadoc['apellidosynombres'] = matri.inscripcion.persona.apellido1 + ' ' + matri.inscripcion.persona.apellido2 + ' ' + matri.inscripcion.persona.nombres
                                datadoc['direccion'] = matri.inscripcion.persona.direccion + ' ' + matri.inscripcion.persona.direccion2
                                datadoc['correo'] = matri.inscripcion.persona.email
                                datadoc['celular'] = matri.inscripcion.persona.telefono
                                datadoc['facultad'] = matri.inscripcion.coordinacion.nombre
                                datadoc['carrera'] = matri.inscripcion.carrera.nombre
                                datadoc['nivelmatricula'] = matri.nivelmalla.nombre
                                datadoc['jornada'] = matri.nivel.sesion.nombre
                                # datadoc['peridoacademico'] =
                                lista_jsondoc.append(datadoc)
                                # response = HttpResponse(json.dumps(lista_jsondoc))
                        if nompersona.es_profesor():
                            if ProfesorDistributivoHoras.objects.filter(profesor__persona=nompersona, periodo__inicio__lte=hoy, periodo__fin__gte=hoy):
                                listadistri = ProfesorDistributivoHoras.objects.filter(profesor__persona=nompersona, periodo__inicio__lte=hoy, periodo__fin__gte=hoy)
                                for lis in listadistri:
                                    datadoc = {}
                                    datadoc['personaactiva'] = 'profesor'
                                    datadoc['ci'] = lis.profesor.persona.cedula
                                    datadoc['apellidosynombres'] = lis.profesor.persona.apellido1 + ' ' + lis.profesor.persona.apellido2 + ' ' +lis.profesor.persona.nombres
                                    datadoc['direccion'] = lis.profesor.persona.direccion + ' ' + lis.profesor.persona.direccion2
                                    datadoc['correo'] = lis.profesor.persona.email
                                    datadoc['celular'] = lis.profesor.persona.telefono
                                    if lis.coordinacion:
                                        datadoc['facultad'] = lis.coordinacion.nombre
                                    else:
                                        datadoc['facultad'] = 'SIN COORDINACION'
                                    if lis.carrera:
                                        datadoc['carrera'] = lis.carrera.nombre
                                    else:
                                        datadoc['carrera'] = 'SIN CARRERA'
                                    lista_jsondoc.append(datadoc)
                                    # response = HttpResponse(json.dumps(lista_jsondoc))
                        if nompersona.es_administrativo_perfilactivo():
                            if DistributivoPersona.objects.filter(persona=nompersona):
                                distripersona = DistributivoPersona.objects.filter(persona=nompersona, estadopuesto=1, status=True)
                                for lis in distripersona:
                                    datadoc = {}
                                    datadoc['personaactiva'] = 'administrativo'
                                    datadoc['ci'] = lis.persona.cedula
                                    datadoc['apellidosynombres'] = lis.persona.apellido1 + ' ' + lis.persona.apellido2 + ' ' +lis.persona.nombres
                                    datadoc['direccion'] = lis.persona.direccion + ' ' + lis.persona.direccion2
                                    datadoc['correo'] = lis.persona.email
                                    datadoc['celular'] = lis.persona.telefono
                                    datadoc['lugartrabajo'] = lis.unidadorganica.nombre
                                    lista_jsondoc.append(datadoc)
                                    # response = HttpResponse(json.dumps(lista_jsondoc))
                        response = HttpResponse(json.dumps(lista_jsondoc))
                    response.__setitem__("Content-type", "application/json")
                    response.__setitem__("Access-Control-Allow-Origin", "*")
                    return response
                except Exception as ex:
                    return JsonResponse({'result': 'bad', "mensaje": u"Error al obtener los datos del docente"})

            if action == 'apihorarioalumno':
                from datetime import datetime
                try:
                    lista_jsondoc = []
                    hoy = datetime.now().date()
                    semanas = [[1, 'Lunes'], [2, 'Martes'], [3, 'Miercoles'], [4, 'Jueves'], [5, 'Viernes'], [6, 'Sabado'], [7, 'Domingo']]
                    if Persona.objects.filter(cedula=request.GET['identificacion']):
                        nompersona = Persona.objects.get(cedula=request.GET['identificacion'])
                        if nompersona.es_estudiante():
                            # insi = Inscripcion.objects.get(persona=nompersoona)
                            if Matricula.objects.filter(inscripcion__persona=nompersona, nivel__periodo__inicio__lte=hoy,nivel__periodo__fin__gte=hoy):
                                matri = Matricula.objects.get(inscripcion__persona=nompersona, nivel__periodo__inicio__lte=hoy,nivel__periodo__fin__gte=hoy)
                                clases = Clase.objects.filter(activo=True, materia__materiaasignada__matricula_id=matri, materia__materiaasignada__retiramateria=False).distinct().order_by('inicio')
                                sesiones = Sesion.objects.filter(turno__clase__in=clases.values_list("id")).distinct()
                                for listasesion in sesiones:
                                    for listaturno in Turno.objects.filter(status=True, mostrar=True, sesion=listasesion, clase__in=clases).distinct().order_by('comienza'):
                                        for sem in semanas:
                                            clasessinpracticas = listaturno.clase_set.values_list('id').filter(dia=sem[0],
                                                                                                               activo=True,
                                                                                                               status=True,
                                                                                                               materia__status=True,
                                                                                                               materia__materiaasignada__retiramateria=False,
                                                                                                               materia__materiaasignada__matricula=matri,
                                                                                                               materia__nivel__periodo__inicio__lte=hoy,
                                                                                                               materia__nivel__periodo__fin__gte = hoy
                                                                                                               # , materia__nivel__periodo__id=90
                                                                                                               ).distinct()
                                            profesorespracticascongrupo = AlumnosPracticaMateria.objects.values_list(
                                                'grupoprofesor__id').filter(materiaasignada__matricula=matri,
                                                                            materiaasignada__retiramateria=False,
                                                                            status=True, grupoprofesor__isnull=False)
                                            clasespracticascongrupo = listaturno.clase_set.values_list('id').filter(dia=sem[0],
                                                                                                                    activo=True,
                                                                                                                    status=True,
                                                                                                                    materia__status=True,
                                                                                                                    tipoprofesor__id=2,
                                                                                                                    grupoprofesor__id__in=profesorespracticascongrupo,
                                                                                                                    materia__materiaasignada__retiramateria=False,
                                                                                                                    materia__materiaasignada__matricula=matri,
                                                                                                                    materia__nivel__periodo__inicio__lte=hoy,
                                                                                                                    materia__nivel__periodo__fin__gte=hoy
                                                                                                                    # materia__nivel__periodo__id=90
                                                                                                                    ).distinct()
                                            for horario in  listaturno.clase_set.filter(Q(id__in=clasessinpracticas) | Q(id__in=clasespracticascongrupo)).distinct().order_by('inicio'):
                                                datadoc = {}
                                                datadoc['dia'] = sem[1]
                                                datadoc['horainicio'] = str(listaturno.comienza)
                                                datadoc['horafin'] = str(listaturno.termina)
                                                datadoc['materia'] = horario.materia.asignatura.nombre
                                                datadoc['nivel'] = horario.materia.asignaturamalla.nivelmalla.nombre
                                                datadoc['paralelo'] = horario.materia.paralelo
                                                datadoc['carreraasignatura'] = horario.materia.asignaturamalla.malla.carrera.alias
                                                datadoc['aula'] = horario.aula.nombre
                                                datadoc['fechainicio'] = str(horario.inicio)
                                                datadoc['fechafin'] = str(horario.fin)
                                                datadoc['tipohorario'] = horario.get_tipohorario_display()
                                                lista_jsondoc.append(datadoc)
                                                response = HttpResponse(json.dumps(lista_jsondoc))
                    response.__setitem__("Content-type", "application/json")
                    response.__setitem__("Access-Control-Allow-Origin", "*")
                    return response
                except Exception as ex:
                    return JsonResponse({'result': 'bad', "mensaje": u"Error al obtener los datos del alumno"})

            if action == 'apihorariodocente':
                from datetime import datetime
                try:
                    lista_jsondoc = []
                    hoy = datetime.now().date()
                    semanas = [[1, 'Lunes'], [2, 'Martes'], [3, 'Miercoles'], [4, 'Jueves'], [5, 'Viernes'], [6, 'Sabado'], [7, 'Domingo']]
                    if Persona.objects.filter(cedula=request.GET['identificacion']):
                        nompersona = Persona.objects.get(cedula=request.GET['identificacion'])
                        if nompersona.es_profesor():
                            # insi = Inscripcion.objects.get(persona=nompersoona)
                            if ProfesorDistributivoHoras.objects.filter(profesor__persona=nompersona, periodo__inicio__lte=hoy,periodo__fin__gte=hoy):
                                # distri = ProfesorDistributivoHoras.objects.get(profesor__persona=nompersona, periodo__inicio__lte=hoy,periodo__fin__gte=hoy)
                                profe = Profesor.objects.get(persona=nompersona)
                                clases = Clase.objects.filter(status=True, activo=True, materia__fechafinasistencias__gte=hoy, fin__gte=hoy, materia__nivel__periodo__visible=True, materia__nivel__periodo__visiblehorario=True, materia__profesormateria__profesor=profe, materia__profesormateria__principal=True, materia__profesormateria__tipoprofesor_id__in=[1,5,8,7], tipoprofesor_id__in=[1,5,8,7]).order_by('inicio')
                                complexivo = ComplexivoClase.objects.filter(status=True, activo=True, materia__profesor__profesorTitulacion_id=profe.id, materia__status=True)
                                sesiones = Sesion.objects.filter(Q(turno__id__in=clases.values_list('turno__id').distinct()) | Q(turno__complexivoclase__in=complexivo)).distinct()
                                for listasesion in sesiones:
                                    if not complexivo:
                                        listadeturnos = Turno.objects.filter(status=True, mostrar=True, sesion=listasesion, clase__in=clases).distinct().order_by('comienza')
                                    else:
                                        listadeturnos = Turno.objects.filter(Q(status=True, mostrar=True), Q(sesion=listasesion, clase__in=clases) | Q(sesion=listasesion, complexivoclase__in=complexivo)).distinct().order_by('comienza')
                                    for listaturno in listadeturnos:
                                        for sem in semanas:
                                            todoslosturnos = listaturno.clase_set.filter(status=True, dia=sem[0], materia__nivel__periodo__visible=True, materia__nivel__periodo__visiblehorario=True, activo=True, materia__fechafinasistencias__gte=datetime.now().date(), inicio__lte=datetime.now().date(), fin__gte=datetime.now().date(), materia__profesormateria__profesor=profe, profesor=profe, materia__profesormateria__principal=True, materia__profesormateria__tipoprofesor_id__in=[1, 5,8,7], tipoprofesor_id__in=[1, 5,8,7]).distinct().order_by('inicio')
                                            for horario in  todoslosturnos:
                                                datadoc = {}
                                                datadoc['dia'] = sem[1]
                                                datadoc['horainicio'] = str(listaturno.comienza)
                                                datadoc['horafin'] = str(listaturno.termina)
                                                datadoc['materia'] = horario.materia.asignatura.nombre
                                                datadoc['nivel'] = horario.materia.asignaturamalla.nivelmalla.nombre
                                                datadoc['paralelo'] = horario.materia.paralelo
                                                datadoc['carreraasignatura'] = horario.materia.asignaturamalla.malla.carrera.alias
                                                datadoc['aula'] = horario.aula.nombre
                                                datadoc['fechainicio'] = str(horario.inicio)
                                                datadoc['fechafin'] = str(horario.fin)
                                                datadoc['tipohorario'] = horario.get_tipohorario_display()
                                                lista_jsondoc.append(datadoc)
                                                response = HttpResponse(json.dumps(lista_jsondoc))
                    response.__setitem__("Content-type", "application/json")
                    response.__setitem__("Access-Control-Allow-Origin", "*")
                    return response
                except Exception as ex:
                    return JsonResponse({'result': 'bad', "mensaje": u"Error al obtener los datos del docente"})

            if action == 'apihorarioadministrativo':
                try:
                    lista_jsondoc = []
                    if Persona.objects.filter(cedula=request.GET['identificacion']):
                        nompersona = Persona.objects.get(cedula=request.GET['identificacion'])
                        if nompersona.historialjornadatrabajador_set.filter(jornada__activa=True, fechafin__isnull=True, status=True):
                            listadojornada = nompersona.historialjornadatrabajador_set.filter(jornada__activa=True, fechafin__isnull=True, status=True)
                            for lisjor in listadojornada:
                                datadoc = {}
                                datadoc['jornada'] = lisjor.jornada.nombre
                                datadoc['fechainicial'] = str(lisjor.fechainicio)
                                datadoc['fechafinal'] = str(lisjor.fechafin)
                                lista_jsondoc.append(datadoc)
                                response = HttpResponse(json.dumps(lista_jsondoc))
                    response.__setitem__("Content-type", "application/json")
                    response.__setitem__("Access-Control-Allow-Origin", "*")
                    return response
                except Exception as ex:
                    return JsonResponse({'result': 'bad', "mensaje": u"Sin horario"})

            if action == 'apipersonadatosmedicos':
                try:
                    lista_jsondoc = []
                    if Persona.objects.filter(cedula=request.GET['identificacion']):
                        nompersona = Persona.objects.get(cedula=request.GET['identificacion'])
                        if PatologicoPersonal.objects.filter(personafichamedica__personaextension__persona=nompersona, status=True):
                            listado = PatologicoPersonal.objects.filter(personafichamedica__personaextension__persona=nompersona, status=True)
                            for lista in listado:
                                datadoc = {}
                                datadoc['tienevacuna'] = lista.vacuna
                                datadoc['vacunas'] = list(lista.vacunas.values_list('descripcion', flat=True))
                                datadoc['enfermedades'] = list(lista.enfermedades.values_list('descripcion', flat=True))
                                datadoc['medicinas'] = list(lista.medicinas.values_list('descripcion', flat=True))
                                datadoc['alergiamedicinas'] = list(lista.alergiamedicinas.values_list('descripcion', flat=True))
                                datadoc['alergiaambientes'] = list(lista.alergiaambientes.values_list('descripcion', flat=True))
                                datadoc['alergiaalimentos'] = list(lista.alergiaalimentos.values_list('descripcion', flat=True))
                                datadoc['discapacidad'] = list(nompersona.perfilinscripcion_set.values_list('tipodiscapacidad__nombre', flat=True))
                                datadoc['tabaquismo'] = list(Habito.objects.values_list('tabaquismo', flat=True).filter(personafichamedica=lista.personafichamedica))
                                datadoc['alcoholismo'] = list(Habito.objects.values_list('alcoholismo', flat=True).filter(personafichamedica=lista.personafichamedica))
                                datadoc['cirugias'] = list(PatologicoQuirurgicos.objects.values_list('cirugias__descripcion', flat=True).filter(personafichamedica=lista.personafichamedica))
                                lista_jsondoc.append(datadoc)
                                response = HttpResponse(json.dumps(lista_jsondoc))
                    response.__setitem__("Content-type", "application/json")
                    response.__setitem__("Access-Control-Allow-Origin", "*")
                    return response
                except Exception as ex:
                    return JsonResponse({'result': 'bad', "mensaje": u"No existen datos medico"})


            if action == 'apimapeototal':
                try:
                    lista_jsondoc = []
                    import datetime
                    # hoy = datetime.now().date()
                    hoy = datetime.datetime.now().date()
                    hoytexto = str(datetime.datetime.now().date())
                    diasemanahoy = datetime.datetime.strptime(hoytexto, "%Y-%m-%d").weekday() + 1
                    ahora = datetime.datetime.now()
                    semanas = [[1, 'Lunes'], [2, 'Martes'], [3, 'Miercoles'], [4, 'Jueves'], [5, 'Viernes'], [6, 'Sabado'], [7, 'Domingo']]
                    if Matricula.objects.filter(nivel__periodo__inicio__lte=hoy,nivel__periodo__fin__gte=hoy, estado_matricula__in=[2,3], status=True, retiradomatricula=False).exclude(nivel__modalidad_id=3):
                        for matri in Matricula.objects.filter(nivel__periodo__inicio__lte=hoy,nivel__periodo__fin__gte=hoy, estado_matricula__in=[2,3], status=True, retiradomatricula=False).exclude(nivel__modalidad_id=3):
                            clases = Clase.objects.filter(turno__comienza__lte=ahora.time(),turno__termina__gte=ahora.time(),inicio__lte=hoy,fin__gte=hoy, dia=diasemanahoy, activo=True, materia__materiaasignada__matricula_id=matri, materia__materiaasignada__retiramateria=False).distinct().order_by('inicio')
                            sesiones = Sesion.objects.filter(turno__clase__in=clases.values_list("id")).distinct()
                            for listasesion in sesiones:
                                for listaturno in Turno.objects.filter(status=True, mostrar=True, comienza__lte=ahora.time(),termina__gte=ahora.time(), sesion=listasesion, clase__in=clases).distinct().order_by('comienza'):
                                    for sem in semanas:
                                        if diasemanahoy == sem[0]:
                                            clasessinpracticas = listaturno.clase_set.values_list('id').filter(dia=sem[0],
                                                                                                               activo=True,
                                                                                                               status=True,
                                                                                                               materia__status=True,
                                                                                                               materia__materiaasignada__retiramateria=False,
                                                                                                               materia__materiaasignada__matricula=matri,
                                                                                                               materia__nivel__periodo__inicio__lte=hoy,
                                                                                                               materia__nivel__periodo__fin__gte = hoy
                                                                                                               # , materia__nivel__periodo__id=90
                                                                                                               ).distinct()
                                            profesorespracticascongrupo = AlumnosPracticaMateria.objects.values_list(
                                                'grupoprofesor__id').filter(materiaasignada__matricula=matri,
                                                                            materiaasignada__retiramateria=False,
                                                                            status=True, grupoprofesor__isnull=False)
                                            clasespracticascongrupo = listaturno.clase_set.values_list('id').filter(dia=sem[0],
                                                                                                                    activo=True,
                                                                                                                    status=True,
                                                                                                                    materia__status=True,
                                                                                                                    tipoprofesor__id=2,
                                                                                                                    grupoprofesor__id__in=profesorespracticascongrupo,
                                                                                                                    materia__materiaasignada__retiramateria=False,
                                                                                                                    materia__materiaasignada__matricula=matri,
                                                                                                                    materia__nivel__periodo__inicio__lte=hoy,
                                                                                                                    materia__nivel__periodo__fin__gte=hoy
                                                                                                                    # materia__nivel__periodo__id=90
                                                                                                                    ).distinct()
                                            for horario in  listaturno.clase_set.filter(Q(id__in=clasessinpracticas) | Q(id__in=clasespracticascongrupo)).distinct().order_by('inicio'):
                                                datadoc = {}
                                                datadoc['identificacion'] = matri.inscripcion.persona.cedula
                                                datadoc['nombrespersona'] = matri.inscripcion.persona.apellido1 + ' ' + matri.inscripcion.persona.apellido2 + ' ' + matri.inscripcion.persona.nombres
                                                datadoc['diasemana'] = sem[1]
                                                datadoc['horainicio'] = str(listaturno.comienza)
                                                datadoc['horafin'] = str(listaturno.termina)
                                                datadoc['materia'] = horario.materia.asignatura.nombre
                                                datadoc['nivelsemestre'] = horario.materia.asignaturamalla.nivelmalla.nombre
                                                datadoc['paralelo'] = horario.materia.paralelo
                                                datadoc['carreraasignatura'] = horario.materia.asignaturamalla.malla.carrera.alias
                                                datadoc['nombreaula'] = horario.aula.nombre
                                                datadoc['fechainicio'] = str(horario.inicio)
                                                datadoc['fechafin'] = str(horario.fin)
                                                datadoc['tipohorario'] = horario.get_tipohorario_display()
                                                if PatologicoPersonal.objects.filter(personafichamedica__personaextension__persona=matri.inscripcion.persona,status=True):
                                                    listado = PatologicoPersonal.objects.filter(personafichamedica__personaextension__persona=matri.inscripcion.persona, status=True)
                                                    for lista in listado:
                                                        datadoc = {}
                                                        datadoc['tienevacuna'] = lista.vacuna
                                                        datadoc['vacunas'] = list(lista.vacunas.values_list('descripcion', flat=True))
                                                        datadoc['enfermedades'] = list(lista.enfermedades.values_list('descripcion', flat=True))
                                                        datadoc['medicinas'] = list(lista.medicinas.values_list('descripcion', flat=True))
                                                        datadoc['alergiamedicinas'] = list(lista.alergiamedicinas.values_list('descripcion',flat=True))
                                                        datadoc['alergiaambientes'] = list(lista.alergiaambientes.values_list('descripcion',flat=True))
                                                        datadoc['alergiaalimentos'] = list(lista.alergiaalimentos.values_list('descripcion',flat=True))
                                                        datadoc['discapacidad'] = list(matri.inscripcion.persona.perfilinscripcion_set.values_list('tipodiscapacidad__nombre', flat=True))
                                                        datadoc['tabaquismo'] = list(Habito.objects.values_list('tabaquismo', flat=True).filter(personafichamedica=lista.personafichamedica))
                                                        datadoc['alcoholismo'] = list(Habito.objects.values_list('alcoholismo', flat=True).filter(personafichamedica=lista.personafichamedica))
                                                        datadoc['cirugias'] = list(PatologicoQuirurgicos.objects.values_list('cirugias__descripcion', flat=True).filter(personafichamedica=lista.personafichamedica))
                                                lista_jsondoc.append(datadoc)
                                                response = HttpResponse(json.dumps(lista_jsondoc))
                        response.__setitem__("Content-type", "application/json")
                        response.__setitem__("Access-Control-Allow-Origin", "*")
                        return response
                except Exception as ex:
                    return JsonResponse({'result': 'bad', "mensaje": u"Error al obtener los datos del alumno"})

            if action == 'asignaturas':
                try:
                    asignaturas = Asignatura.objects.filter(nombre__icontains=request.GET['q'])
                    lista = []
                    for asignatura in asignaturas:
                        lista.append({'id':asignatura.id ,'name':f'{asignatura.nombre} ({asignatura.id})', 'text':asignatura.nombre })
                    return JsonResponse({'result': 'ok', 'lista': lista})
                except Exception as ex:
                    return JsonResponse({"result": "bad", "mensaje": u"Error al obtener los datos."})
            # if action == 'apilistapersonaladm':
            #     try:
            #         cursor = connection.cursor()
            #         lista_jsondoc = []
            #         cursor.execute("select p.apellido1 , p.apellido2, p.nombres,de.descripcion, dep.nombre,p.email,p.emailinst from sga_persona p, auth_user usua, sagest_distributivopersona d,sagest_nivelocupacional nio, sagest_modalidadlaboral mod, sagest_regimenlaboral r,sagest_denominacionpuesto de, sagest_departamento dep where p.id=d.persona_id and d.status=true and d.estadopuesto_id=1 and r.id=d.regimenlaboral_id and usua.id=p.usuario_id and d.nivelocupacional_id=nio.id and d.modalidadlaboral_id=mod.id and de.id=d.denominacionpuesto_id and dep.id=d.unidadorganica_id order by p.apellido1,p.apellido2")
            #         results = cursor.fetchall()
            #         for r in results:
            #             datadoc = {}
            #             datadoc['apellidos'] = r[0] + ' ' + r[1]
            #             datadoc['nombres'] = r[2]
            #             # datadoc['nombres'] = a
            #             datadoc['cargo'] = r[3]
            #             datadoc['departamento'] = r[4]
            #             if r[5] == '':
            #                 numero = 0
            #             else:
            #                 numero = r[5]
            #             datadoc['correo'] = numero
            #             if r[6] == '':
            #                 correo = 0
            #             else:
            #                 correo = r[6]
            #             datadoc['correoinstitucional'] = correo
            #             lista_jsondoc.append(datadoc)
            #         response = JsonResponse(lista_jsondoc))
            #         response.__setitem__("Content-type", "application/json")
            #         response.__setitem__("Access-Control-Allow-Origin", "*")
            #         return response
            #     except Exception as ex:
            #         return JsonResponse({'result': 'bad', "mensaje": u"Error al obtener los datos del docente"})

            # if action == 'apilistadocentescedula':
            #     try:
            #         cursor = connection.cursor()
            #         lista_jsondoc = []
            #         cursor.execute("select per.email,per.emailinst,peri.nombre,per.apellido1,per.apellido2,per.nombres,asi.nombre as nom_materia,carr.nombre as carrera,coordi.nombre as facultad,nmalla.nombre as nivel,coalesce(cate.nombre,'CATEGORIA NO ASIGNADA') as categorizacion,coalesce(dedi.nombre,'DEDICACION NO ASIGNADA') as dedicacion from sga_profesormateria pm left join sga_profesor pro on pro.id=profesor_id left join sga_persona per on per.id=pro.persona_id left join sga_materia mate on mate.id=pm.materia_id left join sga_nivel niv on niv.id=mate.nivel_id left join sga_periodo peri on peri.id=niv.periodo_id left join sga_asignatura asi on asi.id=mate.asignatura_id left join sga_asignaturamalla asimalla on asimalla.id=mate.asignaturamalla_id left join sga_nivelmalla nmalla on nmalla.id=asimalla.nivelmalla_id left join sga_malla malla on malla.id=asimalla.malla_id left join sga_carrera carr on carr.id=malla.carrera_id left join sga_coordinacion_carrera corcar on corcar.carrera_id=carr.id left join sga_coordinacion coordi on coordi.id=corcar.coordinacion_id left join sga_categorizaciondocente cate on cate.id=pro.categoria_id left join sga_tiempodedicaciondocente dedi on dedi.id=pro.dedicacion_id where peri.id='" + request.GET["periodo"] + "' and per.cedula='" + request.GET["cedula"] + "' order by peri.id,per.apellido1,asi.nombre")
            #         results = cursor.fetchall()
            #         for r in results:
            #             datadoc = {}
            #             datadoc['correo'] = r[0]
            #             datadoc['correoinst'] = r[1]
            #             datadoc['nombreperiodo'] = r[2]
            #             datadoc['primerapellido'] = r[3]
            #             datadoc['segundoapellido'] = r[4]
            #             datadoc['nombredocente'] = r[5]
            #             datadoc['materias'] = r[6]
            #             datadoc['carrera'] = r[7]
            #             datadoc['facultad'] = r[8]
            #             datadoc['nivelcurso'] = r[9]
            #             datadoc['cargo'] = 'DOCENTE ' + r[10] + ' ' + r[11]
            #
            #             lista_jsondoc.append(datadoc)
            #         response = HttpResponse(json.dumps(lista_jsondoc))
            #         response.__setitem__("Content-type", "application/json")
            #         response.__setitem__("Access-Control-Allow-Origin", "*")
            #         return response
            #     except Exception as ex:
            #         return JsonResponse({'result': 'bad', "mensaje": u"Error al obtener los datos del docente"})

            # if action == 'apilistadoscentes':
            #     try:
            #         cursor = connection.cursor()
            #         lista_jsondoc = []
            #         cursor.execute("select per.email,per.emailinst,peri.nombre,per.apellido1,per.apellido2,per.nombres,asi.nombre as nom_materia,carr.nombre as carrera,coordi.nombre as facultad,nmalla.nombre as nivel,coalesce(cate.nombre,'CATEGORIA NO ASIGNADA') as categorizacion,coalesce(dedi.nombre,'DEDICACION NO ASIGNADA') as dedicacion from sga_profesormateria pm left join sga_profesor pro on pro.id=profesor_id left join sga_persona per on per.id=pro.persona_id left join sga_materia mate on mate.id=pm.materia_id left join sga_nivel niv on niv.id=mate.nivel_id left join sga_periodo peri on peri.id=niv.periodo_id left join sga_asignatura asi on asi.id=mate.asignatura_id left join sga_asignaturamalla asimalla on asimalla.id=mate.asignaturamalla_id left join sga_nivelmalla nmalla on nmalla.id=asimalla.nivelmalla_id left join sga_malla malla on malla.id=asimalla.malla_id left join sga_carrera carr on carr.id=malla.carrera_id left join sga_coordinacion_carrera corcar on corcar.carrera_id=carr.id left join sga_coordinacion coordi on coordi.id=corcar.coordinacion_id left join sga_categorizaciondocente cate on cate.id=pro.categoria_id left join sga_tiempodedicaciondocente dedi on dedi.id=pro.dedicacion_id where peri.id='" + request.GET["periodo"] + "' order by peri.id,per.apellido1,asi.nombre")
            #         results = cursor.fetchall()
            #         for r in results:
            #             datadoc = {}
            #             datadoc['correo'] = r[0]
            #             datadoc['correoinst'] = r[1]
            #             datadoc['nombreperiodo'] = r[2]
            #             datadoc['primerapellido'] = r[3]
            #             datadoc['segundoapellido'] = r[4]
            #             datadoc['nombredocente'] = r[5]
            #             datadoc['materias'] = r[6]
            #             datadoc['carrera'] = r[7]
            #             datadoc['facultad'] = r[8]
            #             datadoc['nivelcurso'] = r[9]
            #             datadoc['cargo'] = 'DOCENTE ' + r[10] + ' ' + r[11]
            #
            #             lista_jsondoc.append(datadoc)
            #         listado_docentes = json.dumps(lista_jsondoc)
            #         return HttpResponse(listado_docentes
            #     except Exception as ex:
            #         return JsonResponse({'result': 'bad', "mensaje": u"Error al obtener los datos del docente"})

            # if action == 'apilistaadministrativos':
            #     try:
            #         lista_jsonadm = []
            #         listadoadm = Administrativo.objects.all().order_by('persona__apellido1')
            #
            #         for peradm in listadoadm:
            #             per_adm = {}
            #             per_adm['nombrespersona'] = peradm.persona.nombre_completo()
            #             per_adm['cedula'] = peradm.persona.cedula
            #             per_adm['correo'] = peradm.persona.email
            #             per_adm['correoinstitucional'] = peradm.persona.emailinst
            #
            #             lista_jsonadm.append(per_adm)
            #         listado_periodos = simplejson.dumps(lista_jsonadm)
            #         return HttpResponse(listado_periodos
            #     except Exception as ex:
            #         return JsonResponse({'result': 'bad', "mensaje": u"Error al obtener los datos de administrativos"})

            # if action == 'apilistaadministrativoscedula':
            #     try:
            #         lista_jsonadm = []
            #         listadoadm = Administrativo.objects.filter(persona__cedula=request.GET['cedula']).order_by('persona__apellido1')
            #
            #         for peradm in listadoadm:
            #             per_adm = {}
            #             per_adm['nombrespersona'] = peradm.persona.nombre_completo()
            #             per_adm['cedula'] = peradm.persona.cedula
            #             per_adm['correo'] = peradm.persona.email
            #             per_adm['correoinstitucional'] = peradm.persona.emailinst
            #
            #             lista_jsonadm.append(per_adm)
            #         listado_periodos = simplejson.dumps(lista_jsonadm)
            #         return HttpResponse(listado_periodos
            #     except Exception as ex:
            #         return JsonResponse({'result': 'bad', "mensaje": u"Error al obtener los datos de administrativos"})

            # if action == 'apiautenticacion':
            #     try:
            #         #a = request.META.get('HTTP_REFERER')
            #         cursor = connection.cursor()
            #         lista_jsondoc = []
            #         user = authenticate(username=request.GET['user'].lower(), password=request.GET['pass'])
            #         if user is not None:
            #             if not user.is_active:
            #                 datamal = {}
            #                 datamal['result'] = 'bad'
            #                 datamal['mensaje'] = 'Login fallido, usuario no activo'
            #                 lista_jsondoc.append(datamal)
            #                 response = JsonResponse(lista_jsondoc)
            #                 response.__setitem__("Content-type", "application/json")
            #                 response.__setitem__("Access-Control-Allow-Origin", "*")
            #                 return response
            #             else:
            #                 if Persona.objects.filter(usuario__username=user).exists():
            #                     persona = Persona.objects.get(usuario__username=user)
            #                     datas = {}
            #                     datas['result'] = 'ok'
            #                     datas['nombres'] = persona.nombre_completo()
            #                     datas['usuario'] = persona.usuario
            #                     datas['mensaje'] = 'Login correcto, usuario esta activo'
            #                     response = HttpResponse(json.dumps(
            #                         {'result': 'ok', "mensaje": u"correcto", "usuario": persona.usuario.username, "nombres": persona.nombre_completo()}))
            #                     response.__setitem__("Content-type", "application/json")
            #                     response.__setitem__("Access-Control-Allow-Origin", "*")
            #                     return response
            #         else:
            #             datamal = {}
            #             datamal['result'] = 'ok'
            #             datamal['mensaje'] = 'Login incorrecto, usuario o clave estan incorrectos'
            #             lista_jsondoc.append(datamal)
            #             response = HttpResponse(json.dumps(lista_jsondoc))
            #             response.__setitem__("Content-type", "application/json")
            #             response.__setitem__("Access-Control-Allow-Origin", "*")
            #             return response
            #
            #     except Exception as ex:
            #         return JsonResponse({'result': 'bad', "mensaje": u"Error al obtener los datos del docente"})

            # if action == 'apiperiodos':
            #     try:
            #         lista_json = []
            #         listado = Periodo.objects.all().order_by("-inicio")
            #         for per in listado:
            #             per_col = {}
            #             per_col['nombreperiodo'] = per.nombre
            #             per_col['codigoperiodo'] = per.id
            #             lista_json.append(per_col)
            #         response = HttpResponse(json.dumps(lista_json))
            #         response.__setitem__("Content-type", "application/json")
            #         response.__setitem__("Access-Control-Allow-Origin", "*")
            #         return response
            #     except Exception as ex:
            #         return JsonResponse({'result': 'bad', "mensaje": u"Error al obtener los datos de apiperiodos"})

            # if action == 'carreras':
            #     try:
            #         carreras = Carrera.objects.all()
            #         return JsonResponse([model_to_dict(x) for x in carreras])
            #     except Exception as ex:
            #         return JsonResponse({"result": "bad"})
            #
            # if action == 'aulas':
            #     try:
            #         lista = []
            #         for x in Aula.objects.all():
            #             d = model_to_dict(x)
            #             d['sede'] = x.sede.nombre.encode("ascii", "ignore")
            #             d['tipo'] = x.tipo.nombre.encode("ascii", "ignore")
            #             lista.append(d)
            #         resultado = {"total": Aula.objects.all().count(), "aulas": lista}
            #         return JsonResponse(resultado)
            #     except Exception as ex:
            #         return JsonResponse({"result": "bad"})

            if action == 'consultarSedes':
                try:
                    sedes_id = FechaPlanificacionSedeVirtualExamen.objects.filter(status=True, periodo_id=177).values('sede_id').distinct()
                    sedeobject = SedeVirtual.objects.filter(status=True, id__in=sedes_id).values('nombre', 'id')
                    response = JsonResponse({'result': True, 'queryset': list(sedeobject)})
                    return HttpResponse(response.content)
                except Exception as ex:
                    response = JsonResponse({'result': False, 'message': str(ex)})
                    return HttpResponse(response.content)
            if action == 'consultarFecha':
                try:
                    idsede = request.GET['idsede']
                    sede_ = SedeVirtual.objects.get(status=True, id=idsede)
                    eFechaPlanificacionSedeVirtualExamen = FechaPlanificacionSedeVirtualExamen.objects.filter(status=True, periodo_id=177, sede_id=idsede).order_by('fecha').values('fecha', 'id')
                    response = JsonResponse({'result': True, 'titulo': sede_.nombre, 'queryset': list(eFechaPlanificacionSedeVirtualExamen)})
                    return HttpResponse(response.content)
                except Exception as ex:
                    response = JsonResponse({'result': False, 'message': str(ex)})
                    return HttpResponse(response.content)
            if action == 'consultarTurno':
                try:
                    idfecha = request.GET['idfecha']
                    fecha_ = FechaPlanificacionSedeVirtualExamen.objects.get(status=True, id=idfecha)
                    eTurnoPlanificacionSedeVirtualExamenes = TurnoPlanificacionSedeVirtualExamen.objects.filter(fechaplanificacion_id=idfecha).order_by('horainicio').values('horainicio', 'horafin', 'id')
                    response = JsonResponse({'result': True, 'titulo': str(fecha_.fecha),  'queryset': list(eTurnoPlanificacionSedeVirtualExamenes)})
                    return HttpResponse(response.content)
                except Exception as ex:
                    response = JsonResponse({'result': False, 'message': str(ex)})
                    return HttpResponse(response.content)
            if action == 'consultarAulas':
                try:
                    idturno = request.GET['idturno']
                    dataaulas = []
                    eAulaPlanificacionSedeVirtualExamen = AulaPlanificacionSedeVirtualExamen.objects.filter(
                        turnoplanificacion_id=idturno)
                    for aula in eAulaPlanificacionSedeVirtualExamen:
                        dataaulas.append({'aula': aula.aula.nombre, 'idaula': aula.id})
                    response = JsonResponse({'result': True,
                                             'aulas': dataaulas})
                    return HttpResponse(response.content)
                except Exception as ex:
                    response = JsonResponse({'result': False, 'message': str(ex)})
                    return HttpResponse(response.content)
            if action == 'consultarMaterias':
                try:
                    idaula = request.GET['idaula']
                    datamaterias = []
                    eMateriaAsignadaPlanificacionSedeVirtualExamen = MateriaAsignadaPlanificacionSedeVirtualExamen.objects.filter(
                        aulaplanificacion_id=idaula)
                    for materia in eMateriaAsignadaPlanificacionSedeVirtualExamen:
                        datamaterias.append(
                            {'materia': materia.materiaasignada.materia.__str__(), 'idmateria': materia.id})
                    response = JsonResponse({'result': True,
                                             'materias': datamaterias})
                    return HttpResponse(response.content)
                except Exception as ex:
                    response = JsonResponse({'result': False, 'message': str(ex)})
                    return HttpResponse(response.content)

            elif action == 'buscarpersonas':
                try:
                    resp = filtro_persona_select(request)
                    return HttpResponse(json.dumps({'status': True, 'results': resp}))
                except Exception as ex:
                    pass

            elif action == 'cargargestiones':
                try:
                    departamento = Departamento.objects.get(id=request.GET['id'])
                    resp = [{'value': qs.pk, 'text': f"{qs.descripcion}"}
                            for qs in departamento.gestiones()]
                    return JsonResponse({'result': True, 'data': resp})
                except Exception as ex:
                    pass

            elif action == 'cargarcarrerasdepartamento':
                try:
                    periodo = request.session['periodo']
                    departamento = Departamento.objects.get(id=request.GET['id'])
                    carreras = carreras_departamento(departamento, periodo)
                    resp = [{'value': qs.pk, 'text': f"{qs}"}
                            for qs in carreras]
                    return JsonResponse({'result': True, 'data': resp})
                except Exception as ex:
                    pass

            elif action == 'cargarubicaciones':
                try:
                    ubicaciones = Ubicacion.objects.filter(status=True, bloque_id=int(request.GET['id']))
                    resp = [{'value': qs.pk, 'text': f"{qs.nombre}"}
                            for qs in ubicaciones]
                    return JsonResponse({'result': True, 'data': resp})
                except Exception as ex:
                    pass

            elif action == 'consultarcedula':
                try:
                    identificacion = request.GET['value'].strip().upper()
                    tipoidentificacion = int(request.GET.get('args',0))
                    if tipoidentificacion == 1:
                        result = validarcedula(identificacion)
                        if result != 'Ok':
                            return JsonResponse({'results': True, 'errorForm': True, 'validacion': True, 'mensaje': result})
                    elif identificacion[:2] != 'VS':
                        return JsonResponse({'results': True, 'errorForm': True, 'validacion': True, 'mensaje': 'Pasaporte incorrecto, recuerde colocar VS al inicio.'})

                    pers = consultarPersona(identificacion)
                    if pers and not pers.usuario:
                        context = {'nombres': pers.nombres,
                                   'apellido1': pers.apellido1,
                                   'apellido2': pers.apellido2,
                                   'cedula': pers.cedula != '',
                                   'nacimiento': pers.nacimiento,
                                   'sexo': pers.sexo.id,
                                   'telefono': pers.telefono,
                                   'email': pers.email}
                        return JsonResponse({'results': True, 'data': context})
                    return JsonResponse({'results': True, 'errorForm': pers != None, 'mensaje': 'Identificación ingresada ya se encuentra registrada.'})
                except Exception as ex:
                    return JsonResponse({'results': False, 'mensaje': f'Error: {ex}'})

            # elif action == 'validarusuario':
            #     tipo=''
            #     try:
            #         from django.contrib.auth.models import User
            #         from faceid.models import ControlAccesoFaceId
            #         username = request.GET['usuario'].lower().strip()
            #         password = request.GET['password']
            #         profile = request.GET.get('profile', None)
            #         app = request.GET.get('app', '')
            #         faceid = False
            #         user = User.objects.filter(username=username).first()
            #         if not user:
            #             raise NameError(f"Usuario no existe")
            #         if not user.is_active:
            #             raise NameError(f"Usuario no activo")
            #         if not user.check_password(password):
            #             tipo='password'
            #             raise NameError(f"Contraseña incorrecta")
            #         persona = Persona.objects.filter(usuario=user).first()
            #         if not persona:
            #             tipo = 'usuario'
            #             raise NameError(f"Usuario no existe")
            #         if not persona.perfilusuario_set.values("id").filter(Q(administrativo__isnull=False) | Q(profesor__isnull=False), status=True):
            #             tipo = 'usuario'
            #             raise NameError(f"Usuario no activo")
            #
            #         if profile and app:
            #             app_control = 1 if app == 'sga' else 2
            #             profile_control = 1 if profile == 'administrativo' else 2
            #             control = ControlAccesoFaceId.objects.filter(status=True, activo=True, profile=profile_control, app=app_control).last()
            #             if control:
            #                 perfiles = persona.mis_perfilesusuarios_app(app)
            #                 perfilprincipal = persona.perfilusuario_principal(perfiles, app, profile)
            #                 if not perfilprincipal:
            #                     raise NameError('No existe un perfil para esta aplicación.')
            #                 if not perfilprincipal.externo and not perfilprincipal.instructor:
            #                     if control.todos:
            #                         faceid = True
            #                     else:
            #                         cargos = control.cargos.all().values_list('id', flat=True)
            #                         distributivo = persona.distributivopersona_set.filter(status=True, denominacionpuesto_id__in=cargos)
            #                         faceid = True if distributivo else False
            #
            #         return JsonResponse({"result": True, "mensaje": f"Datos correctos", 'faceid':faceid})
            #     except Exception as ex:
            #         return JsonResponse({"result": False, "mensaje": f"{ex}", 'tipo':tipo})

        return JsonResponse(['SGA UNEMI', '(C) Todos los derechos reservados'])
