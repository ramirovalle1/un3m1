import re
from datetime import datetime

from django.core.files.base import ContentFile
from django.http import HttpResponse
from io import BytesIO
from django.template.loader import get_template

#------------REPORTLAB---------------------
from reportlab.graphics.charts.barcharts import VerticalBarChart
from reportlab.platypus.tables import Table
from reportlab.lib.colors import HexColor
from reportlab.lib.units import inch
from reportlab.platypus import Paragraph, SimpleDocTemplate, TableStyle, Image, Spacer
from reportlab.lib.styles import StyleSheet1, ParagraphStyle, LineStyle, getSampleStyleSheet
from reportlab.lib.enums import TA_LEFT, TA_RIGHT, TA_CENTER, TA_JUSTIFY
from reportlab.lib import colors
from reportlab.lib.pagesizes import letter, landscape
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont, TTFOpenFile
from reportlab.graphics.shapes import Drawing

# -------------CREACIÓN DE PDF EN REPORTLAB PURO CÓDIGO--------------------------
import settings

# -------------ESTILOS PREDEFINIDOS--------------------------
"""
Fuentes que pueden ser usadas en fontName
    Helvetica: Una fuente sans-serif clásica.
    Times-Roman: Una fuente serif clásica.
    Courier: Una fuente monoespaciada.
    Arial: Similar a Helvetica, pero más común en entornos Windows.
    Verdana: Una fuente sans-serif diseñada para legibilidad en pantalla.
    Symbol: Una fuente que contiene caracteres especiales y símbolos.
    ZapfDingbats: Una fuente que contiene símbolos y ornamentos.
"""
# -------------ESTILOS--------------------------

def title_h1():
    h1 = ParagraphStyle(
            'title_h1',
            fontName='Helvetica-Bold',  # Otra fuente si lo deseas
            fontSize=14,
            alignment=1,  # Alineación centrada (0 para izquierda, 1 para centro, 2 para derecha)
            textColor='black',  # Color del texto
            fontWeight='Bold'  # Negrita
        )
    return h1

def title_h2():
    h2 = ParagraphStyle(
            'title_h2',
            fontName='Helvetica-Bold',  # Otra fuente si lo deseas
            fontSize=11,
            alignment=1,  # Alineación centrada (0 para izquierda, 1 para centro, 2 para derecha)
            textColor='black',  # Color del texto
        )
    return h2

def subtitle():
    fs_default = ParagraphStyle(
            'subtitle',
            fontName='Helvetica',  # Otra fuente si lo deseas
            fontSize=11,
            alignment=1,  # Alineación centrada (0 para izquierda, 1 para centro, 2 para derecha)
            textColor='black',  # Color del texto
        )
    return fs_default

def style_letter(context={}):
    align = context.get('align', 0)
    fontName = context.get('fontname', 'Helvetica')
    fontSize = context.get('fontsize', 10)
    color = context.get('color', 'black')
    name = context.get('name', 'style')
    leading = fontSize + 2
    leading = context.get('leading', leading)
    marginTop = context.get('marginTop', 0)
    marginBottom = context.get('marginBottom', 0)
    style = ParagraphStyle(name,
                           fontName=fontName,  # Otra fuente si lo deseas
                           fontSize=fontSize,
                           alignment=align,  # Alineación centrada (0 para izquierda, 1 para centro, 2 para derecha)
                           textColor=color,  # Color del texto
                           leading=leading,
                           spaceBefore=marginTop,
                           spaceAfter=marginBottom
                           )
    return style

def style_table_type(page_width, column_widths, context={}):
    type_style = context.get('typeStyle', 'block')
    align = context.get('align', 'LEFT')
    textcolor = context.get('textColor', 'black')
    fontname = context.get('fontName', 'Helvetica-Bold')
    bg = context.get('bg', 'gray')
    if type_style == 'hidden':
        style = TableStyle([('LINEBELOW', (0, 0), (-1, -1), 0, 'white'),
                            ('LINEABOVE', (0, 0), (-1, -1), 0, 'white'),
                            ('LINEBEFORE', (0, 0), (-1, -1), 0, 'white'),
                            ('ALIGN', (0, 0), (-1, -1), align),
                            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),  # Alineación vertical en el centro
                            ('LINEAFTER', (0, 0), (-1, -1), 0, 'white')])
    elif type_style == 'blockFirmas':
        style = TableStyle([('LINEBELOW', (0, 0), (-1, 0), 2, 'BLACK'),
                            ('LINEABOVE', (0, 0), (-1, -1), 0, 'white'),
                            ('LINEBEFORE', (0, 0), (-1, 0), 20, 'white'),
                            ('LINEAFTER', (0, 0), (-1, 0), 20, 'white'),
                            ('ALIGN', (0, 0), (-1, -1), align),
                            ('TOPPADDING', (0, 0), (-1, 0), 50),
                            ('HORIZONTALPADDING', (0, 0), (-1, -1), 10),
                            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),  # Alineación vertical en el centro
                            # ('GRID', (0, 0), (-1, -1), 5, 'white')
                            ])
    else:
        style = TableStyle([('BACKGROUND', (0, 0), (-1, 0), bg),
                            ('TEXTCOLOR', (0, 0), (-1, 0), textcolor),
                            ('ALIGN', (0, 0), (-1, -1), align),  # Alineación horizontal en el centro
                            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),  # Alineación vertical en el centro
                            ('FONTNAME', (0, 0), (-1, 0), fontname),
                            ('BOTTOMPADDING', (0, 0), (-1, 0), 8),
                            ('TOPPADDING', (0, 0), (-1, 0), 8),
                            ('GRID', (0, 0), (-1, -1), 1, 'BLACK')])
    total_width = sum(column_widths)
    if total_width > page_width:
        column_widths = [width * (page_width / total_width) for width in column_widths]

    return style, column_widths

def addPageNumber(canvas, doc, textFooter='UNEMI'):
    from reportlab.lib.units import mm
    fecha = datetime.now().date()
    canvas.saveState()
    # Define el tamaño de la página y el ancho disponible para el contenido
    width, height = doc.pagesize
    available_width = width - 40  # 20 mm de margen a cada lado
    # ------------------------ENCABEZADO---------------------------------------------------------------------------
    header = Image(u'%s%s'%(settings.MEDIA_ROOT,'/reportes/encabezados_pies/cabecera_unemi.png'), width=555, height=75, hAlign='TOP')
    header.drawOn(canvas, 20, height-80)

    #----------------------------FOOTER--------------------------------------------------------------------------
    page_num = canvas.getPageNumber()
    text = f"{textFooter} - {fecha} - Página {page_num}"
    canvas.setFont('Helvetica', 9)
    canvas.drawRightString(available_width, 10 * mm, text)
    canvas.restoreState()
# -------------ESTILOS--------------------------

# -------------CREACIÓN DE PDF CON REPORTLAB CON CONTEXT ENVIADO--------------------------
def generar_pdf_reportlab_v1(file_name, context, type_return=None, title_browser_tab='Universidad Estatal de Milagro'):
    pdf_bytesio = BytesIO()
    pagesize = letter if context.get('pagesize') == 'A4' else landscape(letter)
    width_page = pagesize[0]-40
    contenido = []
    titulo = "UNIVERSIDAD ESTATAL DE MILAGRO"
    titulo = context.get('titulo', titulo)
    textFooter = context.get('textFooter', 'UNEMI')
    contenido.append(Paragraph(titulo, title_h1()))
    contenido.append(Spacer(1, 12))
    for sub in context.get('subtitulos', []):
        texto = sub.get('texto')
        style = sub.get('style')
        style = subtitle() if style and style == 'subtitle'else title_h2()
        contenido.append(Paragraph(texto, style))
        contenido.append(Spacer(1, 12))
    for infoTop in context.get('infoTop', []):
        infot = infoTop.get('texto')
        contenido.append(infot)
        contenido.append(Spacer(1, 12))
    for dict in context.get('tablas', []):
        listado = list(dict.get('listado'))
        colWidthDefault = []
        widthDefault = width_page/len(listado[0])
        for i in range(1, len(listado[0]) + 1):
            colWidthDefault.append(widthDefault)
        typeTable = dict.get('context', {})
        colWidth = dict.get('colWidth', colWidthDefault)
        style_table, colWidth = style_table_type(width_page, colWidth, typeTable)
        # Agregar tabla al PDF
        tabla = Table(data=listado,
                      colWidths=colWidth)

        tabla.setStyle(style_table)
        contenido.append(tabla)
        contenido.append(Spacer(1, 12))
    for infoBottom in context.get('infoBottom', []):
        infob = infoBottom.get('texto')
        contenido.append(infob)
        contenido.append(Spacer(1, 12))
    # Crear documento PDF
    doc = SimpleDocTemplate(pdf_bytesio, pagesize=pagesize, encoding='utf-8', title=title_browser_tab)
    doc.build(contenido, onFirstPage=addPageNumber, onLaterPages=lambda canvas, doc: addPageNumber(canvas, doc, textFooter=textFooter))
    pdf_bytes = pdf_bytesio.getvalue()
    if type_return == 'file':
        return ContentFile(pdf_bytes, name=file_name)
    elif type_return == 'httpresponse':
        response = HttpResponse(pdf_bytes, content_type='application/pdf')
        response['Content-Disposition'] = f'inline; filename="{file_name}"'
        return response
    else:
        return pdf_bytes
# -------------CREACIÓN DE PDF CON REPORTLAB CON CONTEXT ENVIADO--------------------------

# -------------CREACIÓN DE PDF EN REPORTLAB PARTIENDO DE UN HTML--------------------------
def generar_pdf_html_reportlab(template_src, context_dict, file_name, type_return=None):
    from bs4 import BeautifulSoup
    # Renderizar el HTML con los datos proporcionados
    template = get_template(template_src)
    html_content = template.render(context_dict)

    # Crear un objeto BytesIO para almacenar el PDF en memoria
    pdf_bytesio = BytesIO()

    # Crear un documento PDF
    if context_dict.get('pagesize') == 'horizontal':
        doc = SimpleDocTemplate(pdf_bytesio, pagesize=landscape(letter))
    else:
        doc = SimpleDocTemplate(pdf_bytesio, pagesize=letter)
    styles = get_estilos_pdf()

    # Crear un objeto BeautifulSoup para analizar el HTML
    soup = BeautifulSoup(html_content, 'html.parser')

    # Obtener todos los estilos del HTML y aplicarlos
    apply_css_styles(styles, soup)

    # Obtener los párrafos del HTML y agregarlos al contenido del PDF
    content = []
    for element in soup.find_all():
        # p = Paragraph(str(element), styles.get(element.name))
        # content.append(p)
        if element.name == 'h2':
            p = Paragraph(element.get_text(), styles['h2'])
            # p = Paragraph(str(element), styles.get(element.name))
            content.append(p)
        elif element.name == 'p':
            p = Paragraph(element.get_text(), styles['p'])
            # p = Paragraph(str(element), styles.get(element.name))
            content.append(p)
        elif element.name == 'table':
            # Procesar la tabla aquí
            table_data = obtener_datos_tabla(element)
            table = Table(table_data)
            # table.setStyle(TableStyle(styles['table']))
            content.append(table)

    # Construir el PDF
    doc.build(content)

    # Obtener los bytes del objeto BytesIO
    pdf_bytes = pdf_bytesio.getvalue()
    if type_return == 'file':
        return ContentFile(pdf_bytes, name=file_name)
    elif type_return == 'httpresponse':
        response = HttpResponse(pdf_bytes, content_type='application/pdf')
        response['Content-Disposition'] = f'inline; filename="{file_name}"'
        return response
    else:
        return pdf_bytes

def obtener_datos_tabla(table_element):
    # Procesar los datos de la tabla y devolver una lista de listas
    table_data = []
    for row in table_element.find_all('tr'):
        row_data = []
        for cell in row.find_all(['th', 'td']):
            row_data.append(cell.get_text())
        table_data.append(row_data)
    return table_data

def get_estilos_pdf():
    # Definir estilos personalizados
    styles = {
        'h2': ParagraphStyle(
            name='Heading2',
            fontSize=14,
            leading=16,
            spaceAfter=12,
        ),
        'p': ParagraphStyle(
            name='Normal',
            fontSize=10,
            leading=12,
            spaceAfter=6,
        ),
        'table': {
            'borderWidth': 0.5,
            'borderColor': '#000000',
            'GRID': (1, 1),  # Añade bordes a todas las celdas de la tabla
            'FONTNAME': 'Helvetica',  # Fuente de la tabla
            'FONTSIZE': 10,  # Tamaño de fuente de la tabla
        },
    }
    return styles

def apply_css_styles(styles, soup):
    # Obtener todos los estilos del HTML y aplicarlos a los estilos personalizados
    html_styles = soup.find_all('style')
    for html_style in html_styles:
        style_content = html_style.string
        apply_css_declarations(styles, style_content)

def apply_css_declarations(styles, declarations):
    # Aplicar las declaraciones de estilo CSS a los estilos personalizados
    pattern = r'([^{}]+)\s*{\s*([^}]+)\s*}'
    style_rules = re.findall(pattern, declarations)
    for selector, declarations in style_rules:
        selector = selector.strip()
        declarations = declarations.strip()
        if selector in styles:
            if isinstance(styles[selector], dict):
                # Para los estilos de tabla
                apply_table_css(styles[selector], declarations)
            else:
                # Para otros estilos de párrafo
                apply_paragraph_css(styles[selector], declarations)

def apply_table_css(table_style, declarations):
    pairs = declarations.split(';')
    for pair in pairs:
        key, value = pair.split(':')
        key = key.strip()
        value = value.strip()
        table_style[key] = value

def apply_paragraph_css(paragraph_style, declarations):
    pairs = declarations.split(';')
    for pair in pairs:
        key, value = pair.split(':')
        key = key.strip()
        value = value.strip()
        setattr(paragraph_style, key, value)
# -------------CREACIÓN DE PDF EN REPORTLAB PARTIENDO DE UN HTML--------------------------