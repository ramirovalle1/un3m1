import os
from datetime import datetime

from django.db import transaction
from django.db.models import Q
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import Paragraph

from balcon.models import EncuestaProceso
from core.funciones_reportlab import generar_pdf_html_reportlab, generar_pdf_reportlab_v1, style_letter
from sagest.models import Rubro, SeccionDepartamento, Departamento
from settings import RUBRO_ARANCEL, RUBRO_MATRICULA, DEBUG, MEDIA_ROOT
from sga.funciones import generar_nombre
from sga.funcionesxhtml2pdf import conviert_html_to_pdfsave_generic_lotes, conviert_html_to_pdf_save_file_model
from sga.models import Matricula, Carrera, Materia
from sga.templatetags.sga_extras import encrypt, clean_text_parsereportlab
from django.contrib.contenttypes.models import ContentType

unicode = str

def slugs_rectorado_vicerrectorados():
    return ['REC', 'VAFG', 'VIP', 'VV']

def reajuste_rubro_matriculacion(fechaInicio, fechaFin, tipo_id):
    with transaction.atomic():
        try:
            if tipo_id in [RUBRO_ARANCEL, RUBRO_MATRICULA]:
                if DEBUG:
                    print(f"Fecha desde: {str(fechaInicio)} hasta: {str(fechaFin)}")
                eRubros = Rubro.objects.filter(epunemi=False, tipo__id=RUBRO_ARANCEL, matricula__isnull=False, fecha__gte=fechaInicio, fecha__lte=fechaFin, status=True).order_by('fecha')
                totalRubros = len(eRubros)
                if DEBUG:
                    print(f"Total de Rubros de Arancel: {len(eRubros)}")
                eMatriculas = Matricula.objects.filter(pk__in=eRubros.values_list('matricula_id', flat=True))
                if DEBUG:
                    print(f"Total de Matriculas con Rubro: {totalRubros}")
                    print(f"-----------------------------------------------------------------------------")
                    print(f"-----------------------------------------------------------------------------")
                    print(f"-----------------------------------------------------------------------------")
                contador = 0
                for eMatricula in eMatriculas:
                    if DEBUG:
                        print(f"({contador + 1} / {totalRubros}) - Matricula: {eMatricula.__str__()}")
                    eRubroMatriculas = eMatricula.rubro_set.filter(epunemi=False, tipo__id=RUBRO_MATRICULA, status=True).order_by('fecha')
                    eRubroAranceles = eMatricula.rubro_set.filter(epunemi=False, tipo__id=RUBRO_ARANCEL, status=True).order_by('fecha')
                    eRubroAranceles.update(relacionados=eRubroMatriculas.first() if eRubroMatriculas.values("id").exists() else None)
                    contador += 1
                    if DEBUG:
                        print(f"---------> ACTUALIZADO")
                if DEBUG:
                    print(f"PROCESO CULMINADO")
            return True, ''
        except Exception as ex:
            transaction.set_rollback(True)
            return False, f"{ex.__str__()}"


def dominio_sistema_base(request):
    h = 'http' if DEBUG else 'https'
    base_url = request.META['HTTP_HOST']
    return f"{h}://{unicode(base_url)}"

def encrypt_id(valor):
    return int(encrypt(valor)) if not valor.isdigit() else int(valor)

def crear_editar_encuesta(request, objeto, form=None, idcategoria=None):
    try:
        if not form:
            valoracion = request.POST.get('valoracion', 5)
            vigente = True if 'vigente' in request.POST else False
        else:
            valoracion = form.cleaned_data['valoracion']
            vigente = form.cleaned_data['vigente']
        content_type = ContentType.objects.get_for_model(objeto)
        encuesta = EncuestaProceso.objects.filter(object_id=objeto.id, content_type=content_type, status=True).first()
        if not encuesta:
            encuesta = EncuestaProceso(object_id=objeto.id,
                                       content_type=content_type,
                                       valoracion=valoracion,
                                       categoria_id=idcategoria,
                                       vigente=vigente)
        else:
            encuesta.valoracion = valoracion
            encuesta.vigente = vigente
        encuesta.save(request)
        return encuesta
    except Exception as ex:
        raise NameError(f'Error:{ex}')

def encuesta_objeto(objeto):
    try:
        content_type = ContentType.objects.get_for_model(objeto)
        return EncuestaProceso.objects.filter(object_id=objeto.id, content_type=content_type, status=True)
    except Exception as ex:
        raise NameError(f'Error:{ex}')

def formatear_cabecera_pd(df):
    return df.columns.str.split('.').str[-1].str.strip().str.lower().str.replace(' ', '')

def ext_archive(text):
   return text[text.rfind("."):].lower()

def generar_acta_constatacion(request, constatacion):
    data = {}
    directory_p = os.path.join(MEDIA_ROOT, 'activos')
    try:
        os.stat(directory_p)
    except:
        os.mkdir(directory_p)

    directory = os.path.join(MEDIA_ROOT, 'activos', 'actas_constatacion')
    try:
        os.stat(directory)
    except:
        os.mkdir(directory)
    gestion = SeccionDepartamento.objects.get(id=23)
    nombre_archivo = generar_nombre(f'acta_constatcion_{request.user.username}', 'generado') + '.pdf'
    data['constatacion'] = constatacion
    data['listado'] = constatacion.detalle_constatacion()
    data['fechahoy'] = datetime.now()
    data['responsable_af'] = gestion.responsable
    pdf_file, response = conviert_html_to_pdf_save_file_model('af_activofijo/informes/acta_constatacion.html',
        {
            'pagesize': 'A4 landscape',
            'data': data,
        },
        nombre_archivo
    )
    # if not valido:
    #     raise NameError('Error al generar el informe')
    # url_archivo = f'activos/actas_constatacion/{nombre_archivo}'
    return pdf_file

def generar_acta_constatacion_reportlab(request, constatacion):
    context = {}
    directory_p = os.path.join(MEDIA_ROOT, 'activos')
    directory = os.path.join(directory_p, 'actas_constatacion')
    os.makedirs(directory, exist_ok=True)
    gestion = SeccionDepartamento.objects.get(id=23)
    nombre_archivo = generar_nombre(f'acta_constatcion_{request.user.username}', 'generado') + '.pdf'

    # LISTA DE TITULOS Y SUBTITULOS A CARGAR AL PRINCIPIO DE LA HOJA
    context['subtitulos'] =[{'texto': 'DEPARTAMENTO DE ACTIOS FIJOS', 'style': 'h2'},
                            {'texto': 'MÓDULO DE ACTIVOS FIJOS', 'style': 'subtitle'}]

    tablas = []

    numeroacta = Paragraph(f'<b>N° de Acta: </b> {constatacion.numero}', style_letter())
    usuariobienes = Paragraph(f'<b>Usuario de los bienes: </b> {constatacion.usuariobienes.nombre_completo_minus()}', style_letter())
    fechainicio = Paragraph(f'<b>Fecha/Hora Inicio</b> {constatacion.fechainicio.date()} | {constatacion.fechainicio.strftime("%H:%M:%S")}', style_letter())
    fechafin = Paragraph(f'<b>Fecha/Hora Fin</b> {constatacion.fechafin.date()} | {constatacion.fechafin.strftime("%H:%M:%S")}', style_letter())
    estado = Paragraph(f'<b>Estado</b> {constatacion.get_estado_display().capitalize()}', style_letter())

    infoHeader = {'listado':[
                        [numeroacta, usuariobienes, ''],
                        [fechainicio, fechafin, estado]
                    ],
                    'context': {'typeStyle': 'hidden'},
                    'colWidth': [250, 300, 200]}
    tablas.append(infoHeader)
    listado = constatacion.detalle_constatacion()

    # TABLA DE CONTENIDO
    contenido = [['Códigos', 'Catálogo', 'Ubicación', 'Estado', 'Encontrado', 'Baja', 'Traspaso', 'En uso', 'Observaciones']]
    for l in listado:
        cods, cat = '',''
        if l.activo.codigogobierno:
            cods = f'<b>Gob: </b> {l.activo.codigogobierno}'
        if l.activo.codigointerno:
            cods += f'<br/> <b>Int: </b> {l.activo.codigointerno}'
        if l.activo.serie:
            cods += f'<br/> <b>Serie: </b> {l.activo.serie}'
        cat = f'{l.activo.catalogo} <br/> <b>Marca: </b> {l.activo.marca}'
        if l.activo.modelo:
            cat += f'<br/> <b>Modelo: </b> {l.activo.modelo}'
        codigos = Paragraph(cods, style_letter({'fontsize': 8}))
        catalogo = Paragraph(cat, style_letter({'fontsize': 8}))
        ubicacion = Paragraph(f'{l.ubicacionbienes}', style_letter({'fontsize': 8, 'align': 1}))
        estado = Paragraph(f'{l.estadoactual}', style_letter({'fontsize': 8, 'align': 1}))
        encontrado = Paragraph('Si' if l.encontrado else 'No', style_letter({'fontsize': 8, 'align': 1}))
        baja = Paragraph('Si' if l.requieredarbaja else 'No', style_letter({'fontsize': 8, 'align': 1}))
        traspaso = Paragraph('Si' if l.requieretraspaso else 'No', style_letter({'fontsize': 8, 'align': 1}))
        enuso = Paragraph('Si' if l.enuso else 'No', style_letter({'fontsize': 8, 'align': 1}))
        observacion = Paragraph(f'{l.observacion}', style_letter({'fontsize': 8, 'align': 1}))
        contenido.append([codigos, catalogo, ubicacion, estado, encontrado, baja, traspaso, enuso, observacion])
    encontrados = Paragraph(f'<b>T.Encontrados: </b> {constatacion.total_encontrados()}', style_letter({'fontsize': 8,}))
    faltantes = Paragraph(f'<b>T.Faltantes:</b> {constatacion.total_faltantes()}', style_letter({'fontsize': 8,}))
    malestado = Paragraph(f'<b>T.Mal Estado:</b> {constatacion.total_malestado()}', style_letter({'fontsize': 8,}))
    regulares = Paragraph(f'<b>T.Est.Regular:</b> {constatacion.total_regular()}', style_letter({'fontsize': 8,}))
    traspasos = Paragraph(f'<b>T.Traspaso:</b> {constatacion.total_traspaso()}', style_letter({'fontsize': 8,}))
    desuso = Paragraph(f'<b>T.En Desuso: </b>{constatacion.total_desuso()}', style_letter({'fontsize': 8,}))
    tEnuso = Paragraph(f'<b>T.En Uso:</b> {constatacion.total_uso()}', style_letter({'fontsize': 8,}))
    tConstataciones = Paragraph(f'<b>T.Activos:</b> {constatacion.t_constataciones()}', style_letter({'fontsize': 8, 'align': 1}))
    contenido.append([encontrados, faltantes, malestado, regulares, traspasos, '', desuso, tEnuso, tConstataciones])
    contenido = {'listado': contenido,
                 'context': {'typeStyle': 'block','bg':'#92BDDF', 'textcolor':'#122436'},
                 'colWidth': [100, 150, 100, 100, 70, 50, 60, 50, 150]}

    context['responsable_af'] = gestion.responsable

    tablas.append(contenido)

    # INFORMACIÓN DEBAJO DE TABLA
    baselegal=clean_text_parsereportlab(constatacion.periodo.baselegal)
    base = {'listado': [[Paragraph(f'<b>Base Legal:</b> <br/> {baselegal}', style_letter({'fontsize': 10, }))],
                        [Paragraph(f'<b>INTERVINIENTES</b>', style_letter({'fontsize': 10, 'align': 1}))]],
            'context': {'typeStyle': 'hidden'}}
    tablas.append(base)
    tablaFirmas={'listado': [['', '', ''],
                             [Paragraph(f'{constatacion.usuariofinaliza.nombre_completo_minus()} <br/><b>Responsable de constatación</b>', style_letter({'fontsize': 10, 'align': 1, 'marginTop': 50})),
                              Paragraph(f'{gestion.responsable.nombre_completo_minus()} <br/><b>Experto de activos fijos</b>', style_letter({'fontsize': 10, 'align': 1, 'marginTop': 50})),
                              Paragraph(f'{constatacion.usuariobienes.nombre_completo_minus()} <br/><b>Custodio / Usuario</b>', style_letter({'fontsize': 10, 'align': 1, 'marginTop': 50})), ]],
                 'context': {'typeStyle': 'blockFirmas', 'bg': '#92BDDF', 'textcolor': '#122436'},
                 'colWidth': [240, 240, 240, ]}
    tablas.append(tablaFirmas)
    context['tablas']=tablas
    context['pagesize'] = 'A5'
    context['textFooter'] = constatacion.usuariobienes.usuario.username
    pdf_file = generar_pdf_reportlab_v1(nombre_archivo, context, 'file')
    return pdf_file


def generar_reporte_requerimientos_reportlab(incidencias, desde, hasta):
    try:
        from reportlab.lib.enums import TA_CENTER
        context = {}
        directory_p = os.path.join(MEDIA_ROOT, 'evidenciapoa')
        directory = os.path.join(directory_p, 'reportes_generales')
        os.makedirs(directory, exist_ok=True)
        nombre_archivo = generar_nombre(f'Reporte_general_requerimientos', 'generado') + '.pdf'

        # LISTA DE TITULOS Y SUBTITULOS A CARGAR AL PRINCIPIO DE LA HOJA
        context['subtitulos'] = [{'texto': 'DIRECCIÓN DE TECNOLOGÍA DE LA INFORMACIÓN Y COMUNICACIONES', 'style': 'h2'},
                                 {'texto': 'REPORTE GENERAL DE REQUERIMIENTOS INSTITUCIONALES', 'style': 'subtitle'}]

        tablas = []

        fechainicio = Paragraph(f'<b>Fecha Inicio:</b> {desde}', style_letter())
        fechafin = Paragraph(f'<b>Fecha Fin:</b> {hasta}', style_letter())

        infoHeader = {'listado': [
            [fechainicio, fechafin]
        ],
            'context': {'typeStyle': 'hidden'},
            'colWidth': [500, 500]}
        tablas.append(infoHeader)
        listado = incidencias
        # TABLA DE CONTENIDO
        contenido = [['N°', 'Solicitante', 'Requerimiento', 'Fecha', 'Persona asignada', 'Estado']]
        for index, l in enumerate(listado):
            datosreporte = l.get_datos_reporte_encuesta_satisfaccion()
            solicitante = datosreporte['solicitante']
            requerimiento = datosreporte['requerimiento'].upper()
            fecha = datosreporte['fecha']
            personaasignada = datosreporte['asiganadoa']
            estado = l.get_estado_display().upper()

            # Wrap el texto utilizando Paragraph
            index_para = Paragraph(str(index + 1),
                                   style=ParagraphStyle(name='Normal', fontName='Helvetica', fontSize=8, leading=10,
                                                        alignment=TA_CENTER))
            solicitante_para = Paragraph(solicitante,
                                         style=ParagraphStyle(name='Normal', fontName='Helvetica', fontSize=8,
                                                              leading=10))
            requerimiento_para = Paragraph(requerimiento,
                                           style=ParagraphStyle(name='Normal', fontName='Helvetica', fontSize=8,
                                                                leading=10))
            fecha_para = Paragraph(fecha,
                                   style=ParagraphStyle(name='Normal', fontName='Helvetica', fontSize=8, leading=10))
            personaasignada_para = Paragraph(personaasignada,
                                             style=ParagraphStyle(name='Normal', fontName='Helvetica', fontSize=8,
                                                                  leading=10))
            estado_para = Paragraph(estado,
                                    style=ParagraphStyle(name='Normal', fontName='Helvetica', fontSize=8, leading=10))

            contenido.append(
                [index_para, solicitante_para, requerimiento_para, fecha_para, personaasignada_para, estado_para])

        contenido = {'listado': contenido,
                     # ajusta el texto a la celda
                     'context': {'typeStyle': 'block', 'bg': '#92BDDF', 'textcolor': '#122436'},
                     'colWidth': [75, 250, 300, 100, 250, 120],
                     }

        tablas.append(contenido)

        # INFORMACIÓN DEBAJO DE TABLA
        context['tablas'] = tablas
        context['pagesize'] = 'A4'
        pdf_file = generar_pdf_reportlab_v1(nombre_archivo, context, 'file', 'Reporte General de Requerimientos')
        return pdf_file
    except Exception as ex:
        raise NameError(f'Error:{ex}')


def carreras_departamento(eDepartamento, periodo):
    if eDepartamento.grupodepartamento and eDepartamento.grupodepartamento.coordinaciones:
        carreras = Carrera.objects.filter(status=True, malla__isnull=False, malla__vigente=True,
                                          coordinacion__id__in=eDepartamento.grupodepartamento.coordinaciones.all().values_list('id', flat=True),
                                          id__in=Materia.objects.values_list('asignaturamalla__malla__carrera_id').filter(nivel__periodo=periodo).distinct()).distinct()

        return carreras
    return Carrera.objects.none()

def get_departamento(slug='TH'):
    departamento = Departamento.objects.filter(grupodepartamento__alias=slug,
                                               status=True,
                                               integrantes__isnull=False).order_by('id').distinct().first()
    return departamento

def filter_departamentos(list_slug):
    departamentos = Departamento.objects.filter(grupodepartamento__alias__in=list_slug,
                                               status=True,
                                               integrantes__isnull=False).order_by('id').distinct()
    return departamentos
def choice_indice(choice, tupla):
    return [item for item in choice if item[0] in tupla]

def departamentos_vigentes(ids_departamentos=[]):
    filtro = (Q(integrantes__isnull=False) |
               Q(id__in=ids_departamentos)) & Q(status=True)
    return Departamento.objects.filter(filtro).order_by('nombre').distinct()