import os
import sys
import time
from pathlib import Path
from django.core.files import File

SITE_ROOT = os.path.dirname(os.path.realpath(__file__))
your_djangoproject_home = os.path.split(SITE_ROOT)[0]
sys.path.append(your_djangoproject_home)

from django.core.wsgi import get_wsgi_application
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "settings")
application = get_wsgi_application()
from sga.funciones import generar_nombre
from sga.models import *
from sagest.models import *
import zipfile
from xlwt import *
try:
    font_style = XFStyle()
    hoy = datetime.now().date()
    cursor = connection.cursor()
    lista = []
    lista.append('jplacesc@unemi.edu.ec')
    lista.append('equipocomunicacion@unemi.edu.ec')
    url = 'https://sga.unemi.edu.ec/media/zipav/cumpleanio.zip'
    rutaexcelcumpleano=None
    fantasy_zip = zipfile.ZipFile(SITE_STORAGE + url, 'w')
    direccion = os.path.join(SITE_STORAGE, 'media', 'zipav')
    archivoname = generar_nombre('Cumpleanio mes%s'%(MESES_CHOICES[(hoy.month+1) - 1][1]), 'cumpleaniomes.xls')
    rutaexcelcumpleano = os.path.join(direccion, archivoname)
    url2='https://sga.unemi.edu.ec/media/zipav/%s' % (archivoname)
    wb = Workbook(encoding='utf-8')
    ws = wb.add_sheet('cumpleanio%s'%(MESES_CHOICES[(hoy.month+1) - 1][1]))
    columns = [
        (u"CÉDULA", 4000),
        (u"NOMBRES", 12000),
        (u"FECHA NACIMIENTO", 12000),
    ]
    row_num = 1
    for col_num in range(len(columns)):
        ws.write(row_num, col_num, columns[col_num][0], font_style)
        ws.col(col_num).width = columns[col_num][1]
     # distributivo = DistributivoPersona.objects.filter(status=True, estadopuesto__id=1, persona__nacimiento__month=(hoy.month+1)).distinct()
    sql = """SELECT DISTINCT sga_persona.id, sga_persona.cedula, sga_persona.apellido1 ||' ' ||sga_persona.apellido2||' ' || sga_persona.nombres AS nombres,sga_persona.nacimiento
            FROM sagest_distributivopersona
            INNER JOIN sga_persona ON (sagest_distributivopersona.persona_id = sga_persona.id)
            WHERE (EXTRACT('month'
            FROM sga_persona.nacimiento) = %s AND sagest_distributivopersona.status = TRUE AND sagest_distributivopersona.estadopuesto_id = 1)
            """ % (hoy.month+1)
    cursor.execute(sql)
    results = cursor.fetchall()
    row_num = row_num+1
    for dis in results:
        if FotoPersona.objects.filter(status=True,persona__id=dis[0]).exists():
            foto=FotoPersona.objects.filter(status=True,persona__id=dis[0])[0]
            if foto:
                ext = foto.foto.__str__()[foto.foto.__str__().rfind("."):]
                fantasy_zip.write(SITE_STORAGE + foto.foto.url, '%s_%s_%s%s' % (
                dis[1],
                dis[2].replace(' ', '_'),
                dis[0], ext.lower()))
        ws.write(row_num, 0, dis[1], font_style)
        ws.write(row_num, 1, dis[2], font_style)
        ws.write(row_num, 2, str(dis[3]), font_style)
        row_num=row_num+1
    wb.save(rutaexcelcumpleano)
    fantasy_zip.close()
    send_html_mail("Cumpleanieros del mes", "emails/cumpleanio_mes.html",
                   {'sistema': "SGA",'mes':MESES_CHOICES[(hoy.month+1) - 1][1],'hoy':hoy}, lista, [], [SITE_STORAGE + url, SITE_STORAGE + url2],
                   cuenta=CUENTAS_CORREOS[0][1])
except Exception as ex:
    print('error: %s' % ex)