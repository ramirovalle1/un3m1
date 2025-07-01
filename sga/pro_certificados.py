from datetime import date, datetime
import os
from django.http import HttpResponse, HttpResponseRedirect, JsonResponse

from sagest.models import Departamento
from settings import SITE_ROOT, SITE_STORAGE, DEBUG
from django.contrib.auth.decorators import login_required
from django.db.models import Avg
from django.shortcuts import render
import pyqrcode
import code128
from decorators import secure_module, last_access
from sga.commonviews import adduserdata, obtener_reporte
from sga.funciones import null_to_decimal
from sga.funcionesxhtml2pdf import conviert_html_to_pdfsave
from sga.models import RespuestaEvaluacionAcreditacion, ResumenFinalProcesoEvaluacionIntegral, \
    MigracionEvaluacionDocente, ResumenFinalEvaluacionAcreditacion, ResumenParcialEvaluacionIntegral, null_to_numeric, \
    ResponsableEvaluacion, RubricaPreguntas, ProcesoEvaluativoAcreditacion, FirmaPersona


@login_required(redirect_field_name='ret', login_url='/loginsga')
@secure_module
@last_access
def view(request):
    global ex
    data = {'title': u'Certificados del Docente'}
    if request.method == 'POST':
        return render(request, "pro_certificados/certificado_porperiodo.html", data)
    else:
        if 'action' in request.GET:
            action = request.GET['action']
            if action == 'pdf':
                try:
                    data['title'] = u'Adicionar Programa'
                    adduserdata(request, data)
                    persona = request.session['persona']
                    profesor = persona.profesor().id
                    data['datospersona'] = persona
                    data['profesor'] = profesor
                    data['periodoslect'] = MigracionEvaluacionDocente.objects.values('idperiodo','tipoeval').filter(idprofesor=profesor,idperiodo=request.GET['idperiodo']).distinct()
                    data['detalleevaluacion'] = migra = MigracionEvaluacionDocente.objects.filter(idprofesor=profesor,idperiodo=request.GET['idperiodo']).order_by('tipoeval','idperiodo','carrera','semestre','materia')
                    data['detalleevalconmodulo'] = migra.filter(modulo=1)
                    data['moduloevalcuatro'] = migra.filter(modulo=1,tipoeval=4)[0] if migra.filter(modulo=1,tipoeval=4).exists() else {}
                    data['detalleevalsinmodulo'] = migra.filter(modulo=0)
                    data['sinmoduloevalcuatro'] = migra.filter(modulo=0,tipoeval=4)[0] if migra.filter(modulo=0,tipoeval=4).exists() else {}
                    data['promperiodosinmodulo'] = promfinalc = round(null_to_numeric(migra.filter(modulo=0).aggregate(prom=Avg('promedioasignatura'))['prom']), 2)
                    data['promperiodoconmodulo'] = promfinal = round(null_to_numeric(migra.filter(modulo=1).aggregate(prom=Avg('promedioasignatura'))['prom']), 2)
                    if promfinal:
                        notaf = str(request.GET['idperiodo']) + "-" + persona.cedula + "-" + str(promfinal)
                    else:
                        notaf = str(request.GET['idperiodo']) + "-" + persona.cedula + "-" + str(promfinalc)
                    data['nomperiodo'] = request.GET['nomperiodo']
                    data['tipoev'] = request.GET['tipoev']
                    qrname = 'qrce_evam_' + request.GET['idperiodo'] + persona.cedula
                    folder = os.path.join(os.path.join(SITE_STORAGE, 'media', 'qrcode', 'evaluaciondocente', 'qr'))
                    # folder = '/mnt/nfs/home/storage/media/qrcode/evaluaciondocente/'
                    rutapdf = folder + qrname + '.pdf'
                    rutaimg = folder + qrname + '.png'
                    if os.path.isfile(rutapdf):
                        os.remove(rutaimg)
                        os.remove(rutapdf)
                    url = pyqrcode.create('http://sga.unemi.edu.ec//media/qrcode/evaluaciondocente/' + qrname + '.pdf')
                    imageqr = url.png(folder + qrname + '.png', 16, '#000000')
                    imagebarcode = code128.image(notaf).save(folder + qrname + "_bar.png")
                    data['qrname'] = 'qr' + qrname
                    data['fechactual'] = datetime.now().strftime("%d")  + '/' + datetime.now().strftime("%m") + '/' + datetime.now().strftime("%y")+ ' ' + datetime.now().strftime("%H:%M")
                    return conviert_html_to_pdfsave(
                        'pro_certificados/certificado_porperiodo.html',
                        {
                            'pagesize': 'A4',
                            'listadoevaluacion': data,
                        },qrname + '.pdf'
                    )
                except Exception as ex:
                    pass

            if action == 'pdfmodelo2015':
                try:
                    data['title'] = u'Adicionar Programa'
                    adduserdata(request, data)
                    persona = request.session['persona']
                    profesor = persona.profesor().id
                    data['datospersona'] = persona
                    data['profesor'] = profesor
                    data['nomperiodo'] = request.GET['nomperiodo']
                    data['resultados'] = notaporcentaje = ResumenParcialEvaluacionIntegral.objects.filter(profesor=profesor,proceso=request.GET['idperiodo']).order_by('materia__asignaturamalla__malla__carrera__id', 'materia__asignaturamalla__nivelmalla__id')
                    data['porcentaje'] = round(null_to_numeric(notaporcentaje.aggregate(prom=Avg('totalmateriadocencia'))['prom']), 2)
                    data['fechactual'] = datetime.now().strftime("%d") + '/' + datetime.now().strftime("%m") + '/' + datetime.now().strftime("%y")+ ' ' + datetime.now().strftime("%H:%M")
                    notaporcen = "0"+ str(request.GET['idperiodo']) + "-" + persona.cedula + "-" + str(data['porcentaje'])
                    qrname = 'qrce_2015_0' + request.GET['idperiodo'] + persona.cedula
                    # folder = SITE_STORAGE + 'media/qrcode/evaluaciondocente/'
                    folder = os.path.join(os.path.join(SITE_STORAGE, 'media', 'qrcode', 'evaluaciondocente', 'qr'))
                    rutapdf = folder + qrname + '.pdf'
                    rutaimg = folder + qrname + '.png'
                    if os.path.isfile(rutapdf):
                        os.remove(rutaimg)
                        os.remove(rutapdf)
                    url = pyqrcode.create('http://sga.unemi.edu.ec//media/qrcode/evaluaciondocente/' + qrname + '.pdf')
                    imageqr = url.png(folder + qrname + '.png', 16, '#000000')
                    imagebarcode = code128.image(notaporcen).save(folder + qrname + "_bar.png")
                    data['qrname'] = 'qr' + qrname
                    return conviert_html_to_pdfsave(
                        'pro_certificados/pdfqrce_2015.html',
                        {
                            'pagesize': 'A4',
                            'listadoevaluacion': data,
                        },qrname + '.pdf'
                    )
                except Exception as ex:
                    pass

            if action == 'pdfmodeloactual':
                try:
                    import statistics
                    data['title'] = u'Adicionar Programa'
                    adduserdata(request, data)
                    persona = request.session['persona']
                    profesor = persona.profesor().id
                    data['datospersona'] = persona
                    data['profesor'] = profesor
                    data['nomperiodo'] = request.GET['nomperiodo']
                    respuestas = []
                    promediovirtual = 0
                    data['departamento'] = departamento = Departamento.objects.get(pk=128)
                    data['firma'] = FirmaPersona.objects.get(persona=departamento.responsable)
                    data['procesoperiodo'] = ProcesoEvaluativoAcreditacion.objects.get(periodo=request.GET['idperiodo'], status=True)
                    if RubricaPreguntas.objects.filter(rubrica__tipo_criterio=1, rubrica__informativa=False, rubrica__para_nivelacionvirtual=True,  detallerespuestarubrica__respuestarubrica__respuestaevaluacion__tipoinstrumento=1, detallerespuestarubrica__respuestarubrica__respuestaevaluacion__profesor=profesor, detallerespuestarubrica__respuestarubrica__respuestaevaluacion__proceso__periodo=request.GET['idperiodo']).distinct().exists():
                        for prome in RubricaPreguntas.objects.values_list('id').filter(rubrica__tipo_criterio=1,
                                                                                       rubrica__informativa=False,
                                                                                       rubrica__para_nivelacionvirtual=True,
                                                                                       detallerespuestarubrica__respuestarubrica__respuestaevaluacion__tipoinstrumento=1,
                                                                                       detallerespuestarubrica__respuestarubrica__respuestaevaluacion__profesor=profesor,
                                                                                       detallerespuestarubrica__respuestarubrica__respuestaevaluacion__proceso__periodo=request.GET['idperiodo']).annotate(prom=Avg('detallerespuestarubrica__valor')):
                            respuestas.append(null_to_decimal(prome[1], 2))
                        promedio = statistics.mean(respuestas) if respuestas else 0
                        promediovirtual = null_to_decimal(promedio, 2) if promedio else 0
                    data['promediovirtual'] = promediovirtual
                    promedionovirtual = 0
                    respuestas2 = []
                    if RubricaPreguntas.objects.filter(rubrica__tipo_criterio=1, rubrica__informativa=False, rubrica__para_nivelacionvirtual=False,  detallerespuestarubrica__respuestarubrica__respuestaevaluacion__tipoinstrumento=1, detallerespuestarubrica__respuestarubrica__respuestaevaluacion__profesor=profesor, detallerespuestarubrica__respuestarubrica__respuestaevaluacion__proceso__periodo=request.GET['idperiodo']).distinct().exists():
                        for prome in RubricaPreguntas.objects.values_list('id').filter(rubrica__tipo_criterio=1,
                                                                                       rubrica__informativa=False,
                                                                                       rubrica__para_nivelacionvirtual=False,
                                                                                       detallerespuestarubrica__respuestarubrica__respuestaevaluacion__tipoinstrumento=1,
                                                                                       detallerespuestarubrica__respuestarubrica__respuestaevaluacion__profesor=profesor,
                                                                                       detallerespuestarubrica__respuestarubrica__respuestaevaluacion__proceso__periodo=request.GET['idperiodo']).annotate(prom=Avg('detallerespuestarubrica__valor')):
                            respuestas2.append(null_to_decimal(prome[1], 2))
                        promedio = statistics.mean(respuestas2) if respuestas2 else 0
                        promedionovirtual = null_to_decimal(promedio, 2) if promedio else 0
                    data['promedionovirtual'] = promedionovirtual
                    data['resultados'] = porcentaje = ResumenFinalEvaluacionAcreditacion.objects.get(distributivo__profesor=profesor,distributivo__periodo=request.GET['idperiodo'])
                    data['porcentaje'] = notaporcentaje = round(((porcentaje.resultado_total * 100) / 5), 2)
                    data['fechactual'] = datetime.now().strftime("%d") + '/' + datetime.now().strftime("%m") + '/' + datetime.now().strftime("%y")+ ' ' + datetime.now().strftime("%H:%M")
                    notaporcen = str(request.GET['idperiodo']) + "-" + persona.cedula + "-" + str(notaporcentaje)
                    qrname = 'qrce_mied_' + request.GET['idperiodo'] + persona.cedula
                    # folder = SITE_STORAGE + 'media/qrcode/evaluaciondocente/'
                    folder = os.path.join(os.path.join(SITE_STORAGE, 'media', 'qrcode', 'evaluaciondocente', 'qr'))
                    # folder = os.path.join(SITE_STORAGE, 'media', 'qrcode', 'evaluaciondocente')
                    rutapdf = folder + qrname + '.pdf'
                    rutaimg = folder + qrname + '.png'
                    if os.path.isfile(rutapdf):
                        os.remove(rutaimg)
                        os.remove(rutapdf)
                    url = pyqrcode.create('http://sga.unemi.edu.ec//media/qrcode/evaluaciondocente/' + qrname + '.pdf')
                    imageqr = url.png(folder + qrname + '.png', 16, '#000000')
                    imagebarcode = code128.image(notaporcen).save(folder + qrname + "_bar.png")
                    data['qrname'] = 'qr' + qrname
                    data['storage'] = SITE_STORAGE
                    data['url_path'] = 'http://127.0.0.1:8000'
                    if not DEBUG:
                        data['url_path'] = 'https://sga.unemi.edu.ec'
                    return conviert_html_to_pdfsave(
                        'pro_certificados/pdfqrce_modeloactual.html',
                        {
                            'pagesize': 'A4',
                            'listadoevaluacion': data,
                        },qrname + '.pdf'
                    )
                except Exception as ex:
                    pass

        else:

            data = {'title': u'Certificados del Docente'}
            adduserdata(request, data)
            persona = request.session['persona']
            profesor = persona.profesor().id
            data['nprofesor'] = persona.profesor()
            data['periodo'] = periodo = request.session['periodo']
            data['proceso'] = proceso = periodo.proceso_evaluativo()
            data['profesor'] = profesor
            # data['existeactual'] = RespuestaEvaluacionAcreditacion.objects.values('profesor', 'proceso', 'proceso__mostrarresultados', 'proceso__periodo', 'proceso__periodo__nombre').filter(profesor=profesor, tipoinstrumento=1).distinct().order_by('proceso')
            data['existeactual'] = RespuestaEvaluacionAcreditacion.objects.values('profesor', 'proceso', 'proceso__mostrarresultados', 'proceso__periodo', 'proceso__periodo__nombre', 'proceso__periodo__tipo_id').filter(profesor=profesor).distinct().order_by('proceso')
            # data['existe'] = RespuestaEvaluacionAcreditacion.objects.filter(profesor=profesor, tipoinstrumento=1).exists()
            # data['existe'] = RespuestaEvaluacionAcreditacion.objects.filter(profesor=profesor).exists()
            data['existeanterior'] = ResumenFinalProcesoEvaluacionIntegral.objects.filter(profesor=profesor).exists()
            data['periodoslect'] = MigracionEvaluacionDocente.objects.values('idperiodo','descperiodo','tipoeval').filter(idprofesor=profesor).distinct().order_by('idperiodo')
            data['reporte_0'] = obtener_reporte('certificado_evaluacion_docente_profesor')
            data['reporte_1'] = obtener_reporte('certificado_resultado_docente')
            return render(request, "pro_certificados/view.html", data)