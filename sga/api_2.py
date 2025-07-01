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
from django.views.decorators.csrf import csrf_exempt

from helpdesk.models import HdBien
from med.models import Vacuna, Enfermedad, Alergia, Medicina, Cirugia, LugarAnatomico, Droga, MetodoAnticonceptivo, \
    Lesiones, AccionConsulta, PatologicoPersonal, Habito, PatologicoQuirurgicos
from sagest.models import Departamento, IndicadorPoa, ObjetivoOperativo, Rubro, DistributivoPersona
from settings import TIEMPO_CIERRE_SESION
from sga.funciones import variable_valor, salvaRubros
from sga.models import Aula, Carrera, PreInscrito, Periodo, Pais, Provincia, Canton, \
    AreaConocimientoTitulacion, SubAreaConocimientoTitulacion, Persona, Coordinacion, Profesor, ProyectosInvestigacion, \
    ArticuloInvestigacion, PonenciasInvestigacion, LibroInvestigacion, CapituloLibroInvestigacion, MateriaAsignada, \
    DetalleSilaboSemanalBibliografia, DetalleSilaboSemanalBibliografiaDocente, LibroKohaProgramaAnaliticoAsignatura, \
    TipoEstado, VisitasBiblioteca, AreaProgramasInvestigacion, ActividadesMundoCrai, Inscripcion, Matricula, Clase, \
    Sesion, Turno, AlumnosPracticaMateria, ProfesorDistributivoHoras, ComplexivoClase, PerfilInscripcion, \
    PreferenciaDetalleActividadesCriterio, InstitucionBeca, RevistaInvestigacion, SubLineaInvestigacion, \
    ProyectoInvestigacionExterno, ItinerariosMalla,SubAreaEspecificaConocimientoTitulacion
from sga.funcionesxhtml2pdf import conviert_html_to_pdf
from sga.templatetags.sga_extras import encrypt
from socioecon.models import ProveedorServicio

unicode = str


@csrf_exempt
@transaction.atomic()
def view(request):
    if request.method == 'POST':
        if 'a' in request.POST:
            action = request.POST['a']
            if action == 'uprubrounemi':
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