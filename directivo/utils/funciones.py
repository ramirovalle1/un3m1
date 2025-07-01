import io
import os
import sys

from datetime import datetime, timedelta
from django.core.files.base import File
from django.core.files.storage import default_storage
from django.db.models import Max

from core.firmar_documentos import obtener_posicion_x_y_saltolinea
from core.firmar_documentos_ec import JavaFirmaEc
from directivo.models import HistorialDocumentoFirma, PersonaSancion, DocumentoEtapaIncidencia
from directivo.utils.strings import Strings
from sagest.funciones import filter_departamentos, slugs_rectorado_vicerrectorados, get_departamento, encrypt_id, dominio_sistema_base
from sga.funciones import generar_nombre, log, notificacion
from sga.funcionesxhtml2pdf import conviert_html_to_pdf_save_file_model
from sga.models import CUENTAS_CORREOS
from sga.tasks import send_html_mail
from sga.templatetags.sga_extras import encrypt, persona_genero, get_consulta_firma_persona_sancion, title2


def generar_codigo_incidencia(nombres, departamento=''):
    from directivo.models import IncidenciaSancion
    nombres, departamento = str(nombres).upper(), str(departamento.alias).upper()
    incidencia = IncidenciaSancion.objects.filter(status=True).order_by('fecha_creacion').last()
    numero = num = str(incidencia.numero + 1 if incidencia else 1)
    if len(num) == 1:
        num = '000' + num
    elif len(num) == 2:
        num = '00' + num
    elif len(num) == 3:
        num = '0' + num
    codigo = ''
    if departamento:
        codigo += departamento + '-'
    arreglo = nombres.split()
    for letra in arreglo:
        codigo += letra[:1]
    codigo += f'-{num}'
    return codigo, int(numero)

def generar_secuencia_doc_etapa_incidencia(tipo_doc):
    doc = DocumentoEtapaIncidencia.objects.filter(status=True, tipo_doc=tipo_doc).aggregate(secuencia=Max('secuencia'))
    ultima_secuencia = (doc['secuencia'] or 0) + 1
    return ultima_secuencia

def generar_codigo_doc_etapa_incidencia(sec, persona, tipo_doc):
    nombres = persona.nombres.split()
    nombre1 = nombres[0][:1] if len(nombres) > 0 else ''
    nombre2 = nombres[1][:1] if len(nombres) > 1 else ''

    apellido1 = persona.apellido1[:1] if persona.apellido1 else ''
    apellido2 = persona.apellido2[:1] if persona.apellido2 else ''

    iniciales = f'{nombre1}{nombre2}{apellido1}{apellido2}'
    secuencia = str(sec).zfill(4)
    anio = datetime.now().year
    if tipo_doc == 5:
        return f'{secuencia}-DTH-{anio}'
    return f'ITI-UNEMI-DTH-{iniciales.upper()}-{anio}-{secuencia}'

def es_director_departamento(persona, slug):
    departamento = get_departamento(slug)
    return departamento and departamento.responsable == persona

def permisos_sanciones(persona):
    ids_autoridades = list(filter_departamentos(slugs_rectorado_vicerrectorados()).values_list('responsable_id', 'responsable_subrogante__id'))
    context = {'lector': True, 'revisor': False, 'gestor_th': False, 'director_th': False, 'secretaria': False}
    context['secretaria'] = puede_gestionar_audiencia = persona.usuario.has_perm('sagest.puede_gestionar_audiencia')
    context['genera_informes'] = persona.usuario.has_perm('sagest.puede_generar_informes_sanciones')
    context['revisor'] = puede_gestionar_audiencia or persona.id in ids_autoridades
    context['gestor_th'] = persona.usuario.has_perm('sagest.puede_gestionar_sanciones_th')
    context['director_th'] = es_director_departamento(persona, 'TH')
    return context

def resposables_firma_doc(tipo_doc, rol_doc=[1, 2, 3]):
    from directivo.models import ResponsableFirma
    return ResponsableFirma.objects.filter(status=True, tipo_doc=tipo_doc, rol_doc__in=rol_doc, firma_doc=True).order_by('orden')

def resposable_firma_doc_rol(tipo_doc, rol_doc):
    from directivo.models import ResponsableFirma
    responsablefirma =  ResponsableFirma.objects.filter(status=True, tipo_doc=tipo_doc, rol_doc=rol_doc, firma_doc=True).first()
    if responsablefirma:
        return responsablefirma.persona
    return None


def secciones_etapa_verificacion():
    secciones = [
        {'seccion': 'validación', 'nombre': 'Validación de caso', 'icono': 'bi bi-patch-check'},
        {'seccion': 'acta_reunion', 'nombre': 'Acta de reunión', 'icono': 'bi bi-file-break'},
    ]
    return secciones
def secciones_etapa_analisis():
    secciones = [
        # {'seccion': 'validacion', 'nombre': 'Validación de caso', 'icono': 'bi bi-patch-check'},
        {'seccion': 'informe', 'nombre': 'Informe de fundamentos de hecho, de derecho y documentos de respaldo', 'icono': 'bi bi-file-break'},
        {'seccion': 'descargo', 'nombre': 'Respuesta de descargo', 'icono': 'bi bi-archive'}
    ]
    return secciones
def secciones_etapa_audiencia():
    secciones = [
        {'seccion': 'cronograma', 'nombre': 'Cronograma de audiencia', 'icono': 'bi bi-calendar-week'},
        {'seccion': 'audiencia', 'nombre': 'Audiencia', 'icono': 'bi bi-people'},
        {'seccion': 'acta', 'nombre': 'Acta de audiencia', 'icono': 'bi bi-file-earmark-text'},
        {'seccion': 'informe', 'nombre': 'Informe técnico de sustanciación', 'icono': 'bi bi-file-break'},
        {'seccion': 'accion_personal', 'nombre': 'Acción de personal', 'icono': 'bi bi-person-video2'},
    ]
    return secciones

def get_cargo_persona(persona):
    cargo = persona.mi_cargo_administrativo() if persona.mi_cargo_administrativo() else persona.mi_cargo()
    return cargo
def generar_documento_etapa(documento, request):
    from directivo.models import PersonaFirmaDocumento, HistorialDocumentoFirma
    try:
        data = {}
        # Eliminar firmantes anteriores
        documento.responsables_legalizacion().update(status=False)

        # Guardar firmantes nuevos
        cargo = get_cargo_persona(documento.persona_elabora)
        elabora = PersonaFirmaDocumento(documento=documento, cargo=cargo,
                                        persona=documento.persona_elabora, orden=0, rol_firma=1)
        elabora.save(request)
        responsables = resposables_firma_doc(documento.tipo_doc, [2, 3, 11])
        for r in responsables:
            firmante = PersonaFirmaDocumento(documento=documento,
                                             cargo=r.get_cargo(), persona=r.persona,
                                             orden=r.orden, rol_firma=r.rol_doc)
            firmante.save(request)


        nombre_archivo = generar_nombre(f'documento_{documento.id}', 'generado') + '.pdf'
        data['documento'] = documento
        data['page_size'] = 'A4 landscape'
        template = 'adm_sanciones/documentos/documento_etapa_pdf.html'
        pdf_file, response = conviert_html_to_pdf_save_file_model(template, data, nombre_archivo)
        documento.archivo = pdf_file
        documento.estado = 1
        documento.save(request)
        historial = HistorialDocumentoFirma(documento=documento, archivo=pdf_file, persona=documento.persona_elabora, estado=1)
        historial.save(request)
    except Exception as ex:
        raise NameError(f'Error al generar documento: {ex}')

def generar_acta_reunion(documento, request, lista_convocados, lista_planes):
    from sga.models import Persona
    from directivo.models import PersonaFirmaDocumento, HistorialDocumentoFirma
    try:
        data = {}
        # Eliminar firmantes anteriores
        documento.responsables_legalizacion().update(status=False)

        reunion = documento.reunion
        # Guardar firmantes nuevos
        list_resp_th = [reunion.convocador, reunion.organizador, reunion.apuntador]
        list_ids_resp_th = []
        for resp in list_resp_th:
            if not resp.id in list_ids_resp_th:
                cargo = get_cargo_persona(resp)
                firma = PersonaFirmaDocumento(documento=documento, cargo=cargo, persona=resp, orden=0, rol_firma=0)
                firma.save(request)
                list_ids_resp_th.append(resp.id)

        for c in lista_convocados:
            if not c['id_convocado'] in list_ids_resp_th:
                per = Persona.objects.get(pk=c['id_convocado'])
                cargo = get_cargo_persona(per)
                firma = PersonaFirmaDocumento(documento=documento, cargo=cargo, persona=per, orden=0, rol_firma=0)
                firma.save(request)

        for p in lista_planes:
            id = p['funcionario_id']
            firma = PersonaFirmaDocumento.objects.filter(status=True, documento=documento, persona_id=id).first()
            if not firma:
                per = Persona.objects.get(pk=id)
                cargo = get_cargo_persona(per)
                firma = PersonaFirmaDocumento(documento=documento, cargo=cargo, persona=per, orden=0, rol_firma=0, planaccion=p['descripcion_plan'])
                firma.save(request)
            else:
                firma.planaccion = p['descripcion_plan']
                firma.save(request)

        data['convocados'] = documento.responsables_legalizacion().exclude(persona__id__in=list_ids_resp_th)
        nombre_archivo = generar_nombre(f'documento_{documento.id}', 'generado') + '.pdf'
        data['documento'] = documento
        data['reunion'] = reunion
        data['page_size'] = 'A4 landscape'
        template = 'adm_sanciones/documentos/acta_reunion.html'
        pdf_file, response = conviert_html_to_pdf_save_file_model(template, data, nombre_archivo)
        documento.archivo = pdf_file
        documento.estado = 1
        documento.save(request)
        historial = HistorialDocumentoFirma(documento=documento, archivo=pdf_file, persona=documento.persona_elabora, estado=1)
        historial.save(request)
    except Exception as ex:
        raise NameError(f'Error al generar documento: {ex}')

def firmar_documento_etapa(request, persona, args={}):
    from directivo.models import DocumentoEtapaIncidencia
    try:
        certificado = request.FILES["firma"]
        contrasenaCertificado = request.POST['palabraclave']
        razon = request.POST['razon'] if 'razon' in request.POST else ''
        extension_certificado = os.path.splitext(certificado.name)[1][1:]
        bytes_certificado = certificado.read()
        documento = DocumentoEtapaIncidencia.objects.get(pk=encrypt_id(request.POST['id']))
        archivo_ = documento.archivo
        name_doc = args.get('name_doc', documento.name_doc())

        if documento.tipo_doc == 5:
            args['ly_menos'] = 40

        if documento.tipo_doc == 3:
            args['ly_menos'] = 20
            # tipo_estadoarchivo = {10: 1, 8: 2, 9: 3, 0: 3}
            firmas = ubicacion_firmas_accionpersonal(documento, persona, archivo_, args)
        else:
            firmas = ubicacion_firma_documento(documento, persona, archivo_, args)

        for membrete in firmas:
            datau = JavaFirmaEc(
                archivo_a_firmar=archivo_, archivo_certificado=bytes_certificado,
                extension_certificado=extension_certificado,
                password_certificado=contrasenaCertificado,
                page=int(membrete["page"]), reason=razon, lx=membrete["x"], ly=membrete["y"]).sign_and_get_content_bytes()
            archivo_ = io.BytesIO()
            archivo_.write(datau)
            archivo_.seek(0)
            responsable_firma = membrete['responsable']
            responsable_firma.firmado = True
            responsable_firma.save(request)
            # if documento.tipo_doc == 3:
            #     estadoarchivo = tipo_estadoarchivo.get(responsable_firma.rol_firma, 0)

        _name = f'{name_doc}_{documento.incidencia.codigo}_firmado'
        _name = generar_nombre(_name, '')
        file_obj = File(archivo_, name=f"{_name}.pdf")
        all_signature = documento.firmado_all()
        documento.archivo = file_obj
        documento.estado = 3 if all_signature else 2
        documento.save(request)

        # Actualizar archivo y estado archivo en acción de personal
        if documento.tipo_doc == 3:
            update_accionpersona_file(documento, file_obj, all_signature, request)

        # Historial de firma
        historial = HistorialDocumentoFirma(documento=documento, archivo=file_obj, persona=persona, estado=3)
        historial.save(request)
        log(f'Firmo documento: {documento}', request, 'edit')
    except Exception as ex:
        textoerror = '{} Linea:{}'.format(ex, sys.exc_info()[-1].tb_lineno)
        raise NameError(textoerror)

def update_accionpersona_file(documento, file_obj, all_signature, request):
    persona_sancion = documento.get_persona_sancion()
    accionpersonal = persona_sancion.accionpersonal
    accionpersonal.archivo = file_obj
    if all_signature:
        # estadoarchivo = 4 = aprobado
        accionpersonal.estadoarchivo = 4
        # enviar notificación al director cuando se legaliza accion personal
        notify_director_legalizacion_accion_personal(request, persona_sancion.incidencia, persona_sancion)
    else:
        accionpersonal.estadoarchivo = 6
    accionpersonal.save()

def ubicacion_firmas_accionpersonal(documento, persona, archivo_, args={}):
    firmas = []
    ly_menos = args.get('ly_menos', 0)
    nombres = persona.un_nombre_dos_apellidos().title()
    responsables = documento.responsables_legalizacion().filter(persona=persona, firmado=False).order_by('orden')
    for responsable_firma in responsables:
        rol_text = responsable_firma.get_rol_firma_display().upper()
        # if responsable_firma.rol_firma == 0:
        #     accion = documento.get_persona_sancion().accionpersonal
        #     art = persona_genero(persona, '', 'A')
        #     art += '(S)' if accion.subroganterrhh else ''
        #     rol_text = f'DIRECTOR{art} DE TALENTO HUMANO'
        abreviatura = ''
        if persona.titulacionmaximavalida() and persona.titulacionmaximavalida().titulo:
            abreviatura = persona.titulacionmaximavalida().titulo.abreviatura.title()

        es_subrogante = responsable_firma.subrogante
        palabras = f'{abreviatura} {nombres}' if abreviatura else f'{nombres}'
        palabras += f'{responsable_firma.rol_firma}'

        # palabras = f'{abreviatura} {nombres}{responsable_firma.rol_firma}' if abreviatura else f'{nombres}{responsable_firma.rol_firma}'
        x, y, numPage = obtener_posicion_x_y_saltolinea(archivo_.url, palabras, False, True)
        if not x and not y:
            raise NameError('No se encontró la posición para la firma.')
        pos_y = y-ly_menos
        if responsable_firma.rol_firma == 15:
            y += 28
        else:
            y = y - 17
        firmas.append({'x': x+4, 'y': y, 'page': numPage, 'responsable': responsable_firma})
    return firmas

def ubicacion_firma_documento(documento, persona, archivo_, args={}):
    lx = args.get('lx', None)
    ly_menos = args.get('ly_menos', 0)
    last_page = args.get('last_page', True)
    nombres = persona.nombre_completo_titulo()
    responsable_firma = documento.get_persona_firma(persona)
    cargo = responsable_firma.cargo if responsable_firma.cargo else ''
    palabras = f'{nombres} {cargo}'
    if responsable_firma.firmado:
        raise NameError('El archivo ya se encuentra firmado por sus usuario.')

    x, y, numPage = obtener_posicion_x_y_saltolinea(archivo_.url, palabras, last_page, True)
    if not x and not y:
        raise NameError('No se encontró la posición para la firma.')

    lx = x if not lx else lx
    return [{'x': lx, 'y': y-ly_menos, 'page': numPage, 'responsable': responsable_firma}]

def notificar_personas_sancion(request, personas_sancion):
    from directivo.models import PersonaSancion
    for ps in personas_sancion:
        notify_persona_sancion(request, ps)

def notify_persona_sancion(request, ps):
    from directivo.models import PersonaSancion
    responsable = ps.persona
    titulo = f"Caso de sanción disciplinaria remitida ({ps.get_estado_display()})"
    mensaje = f'La Dirección de Talento Humano ha procedido con la revisión del ' \
              f'caso de sanción disciplinaria de código <b>{ps.incidencia.codigo}</b> correspondiente a' \
              f'una falta  <b>{ps.incidencia.falta}</b> se require que usted revise su caso y posterior a su revisión la carga de las respuesta de descargo'
    url_redirect = f'/th_hojavida?action=revisarincidencia&id={encrypt(ps.incidencia.id)}'
    notificacion(titulo, mensaje, responsable, None,
                 url_redirect, ps.pk, 1, 'sga-sagest',
                 PersonaSancion, request)
    lista_email = responsable.lista_emails()
    # lista_email = ['walarconr@unemi.edu.ec', ]
    datos_email = {'sistema': request.session['nombresistema'],
                   'tiposistema_': 2,
                   'fecha': datetime.now().date(),
                   'hora': datetime.now().time(),
                   'persona': responsable,
                   'mensaje': mensaje,
                   'observacion': '',
                   'titulo_': titulo,
                   'url_redirect': url_redirect,
                   }
    template = "adm_directivos/emails/email_notify_sancion.html"
    send_html_mail(titulo, template, datos_email, lista_email, [], [], cuenta=CUENTAS_CORREOS[0][1])


def notify_director_legalizacion_accion_personal(request, incidencia, persona_sancion):
    from directivo.models import PersonaSancion
    responsable = persona_sancion.persona
    director = incidencia.persona
    tipo = incidencia.falta
    motivo = incidencia.motivo
    firma_servidor = persona_sancion.servidor_firma_accion_personal()
    resp_servidor = 'legalización' if firma_servidor else 'negativa'
    titulo = f"Finalización de proceso disciplinario"
    mensaje = f'Por medio de la presente, le informo que el proceso disciplinario iniciado en contra del servidor {persona_sancion.persona.nombre_completo_minus()},' \
              f'en relación con la falta: {title2(motivo)}, ' \
              f'ha concluido con la correspondiente <b>{resp_servidor}</b> de la acción de personal. <br><br>'\
               f'En virtud de lo anterior, se han tomado las medidas disciplinarias pertinentes conforme a lo establecido en el reglamento de régimen disciplinario institucional. '\
               f'El expediente del proceso ha sido debidamente cerrado, y la documentación relacionada ha sido archivada en el expediente personal del servidor para su respectivo control. <br><br>'\
                f'Agradecemos su colaboración y quedamos a disposición para cualquier aclaración adicional.'

    url_redirect = f'/adm_directivos?action=revisarincidencia&id={encrypt(incidencia.id)}'
    lista_email = director.lista_emails()
    # lista_email = ['walarconr@unemi.edu.ec', ]
    datos_email = {'sistema': request.session['nombresistema'],
                   'tiposistema_': 2,
                   'fecha': datetime.now().date(),
                   'hora': datetime.now().time(),
                   'persona': responsable,
                   'director': director,
                   'mensaje': mensaje,
                   'titulo_': titulo,
                   'accion_personal_legalizada': True,
                   'url_redirect': url_redirect,
                   }
    template = "adm_directivos/emails/email_notify_sancion.html"
    send_html_mail(titulo, template, datos_email, lista_email, [], [], cuenta=CUENTAS_CORREOS[0][1])

def notify_persona_audiencia(request, pa):
    from directivo.models import PersonaAudienciaSancion
    responsable = pa.persona
    titulo = f"Audiencia de sanción disciplinaria ({pa.audiencia.fecha} | {pa.audiencia.horainicio} a {pa.audiencia.horafin})"
    mensaje = (f'La Dirección de Talento Humano ha procedido '
               f'con la planificación de la audiencia según el caso de sanción disciplinaria de código '
               f'<b>{pa.audiencia.incidencia.codigo}</b>, '
               f'correspondiente a una falta <b>{pa.audiencia.incidencia.falta}</b>. '
               f'Se requiere que usted revise la fecha y hora de la audiencia y, posterior a su'
               f' revisión, indique si asistirá o no a la audiencia según su disponibilidad.')
    url_redirect = f'/th_hojavida?action=revisarincidencia&id={encrypt(pa.audiencia.incidencia.id)}'
    notificacion(titulo, mensaje, responsable, None,
                 url_redirect, pa.pk, 1, 'sga-sagest',
                 PersonaAudienciaSancion, request)
    lista_email = responsable.lista_emails()
    # lista_email = ['walarconr@unemi.edu.ec', ]
    datos_email = {'sistema': request.session['nombresistema'],
                   'tiposistema_': 2,
                   'fecha': datetime.now().date(),
                   'hora': datetime.now().time(),
                   'persona': responsable,
                   'mensaje': mensaje,
                   'observacion': '',
                   'titulo_': titulo,
                   'url_redirect': url_redirect,
                   }
    template = "adm_directivos/emails/email_notify_sancion.html"
    send_html_mail(titulo, template, datos_email, lista_email, [], [], cuenta=CUENTAS_CORREOS[0][1])

def notify_persona_decision_audiencia(request, persona_sancion, audiencia):
    from directivo.models import PersonaAudienciaSancion
    from sga.templatetags.sga_extras import fecha_natural
    responsable = persona_sancion.persona
    fecha_natural = fecha_natural(audiencia.fecha)
    inicio = audiencia.fecha_inicio.time().strftime('%H:%M')
    fin = audiencia.fecha_fin.time().strftime('%H:%M')
    titulo = f"Resolución de audiencia ({persona_sancion.get_estado_display()})"
    mensaje = (f'La Dirección de Talento Humano ha procedido '
               f'con la resolución de la audiencia según el caso de sanción disciplinaria de código '
               f'<b>{audiencia.incidencia.codigo}</b>, '
               f'correspondiente a una falta <b>{audiencia.incidencia.falta}</b>. <br>'
               f'La cual fue realizada el <b>{fecha_natural}</b> en horario de <b>{inicio}</b> a <b>{fin}</b>. '
               f'y se determino lo siguiente: <br><br> <b>{persona_sancion.get_estado_display().upper()}</b>.')
    url_redirect = f'/th_hojavida?action=revisarincidencia&id={encrypt(audiencia.incidencia.id)}'
    notificacion(titulo, mensaje, responsable, None,
                 url_redirect, persona_sancion.pk, 1, 'sga-sagest',
                 PersonaSancion, request)
    lista_email = responsable.lista_emails()
    # lista_email = ['jguachuns@unemi.edu.ec', ]
    datos_email = {'sistema': request.session['nombresistema'],
                   'tiposistema_': 2,
                   'fecha': datetime.now().date(),
                   'hora': datetime.now().time(),
                   'persona': responsable,
                   'mensaje': mensaje,
                   'observacion': '',
                   'titulo_': titulo,
                   'url_redirect': url_redirect,
                   }
    template = "adm_directivos/emails/email_notify_sancion.html"
    send_html_mail(titulo, template, datos_email, lista_email, [], [], cuenta=CUENTAS_CORREOS[0][1])


def notificacion_validacion_caso(request, persona_sancion):
    list_mail = persona_sancion.persona.lista_emails()
    # list_mail = ['walarconr@unemi.edu.ec', ]
    texto = Strings.correoCasoProcede if persona_sancion.estado == 1 else Strings.correoNoCasoProcede
    per = persona_sancion.persona
    titulo = f'Incidencia por falta disciplinaria: {persona_sancion.incidencia.motivo}'
    template = "adm_sanciones/emails/email_notify_validacion_caso.html"
    url = f'/th_hojavida?action=revisarincidencia&id={encrypt(persona_sancion.incidencia.id)}'
    url_completa = dominio_sistema_base(request) + url
    datos_email = {'sistema': 'SAGEST',
                   'titulo': titulo,
                   'persona': per,
                   'url_redirect': url_completa,
                   'mensaje': texto
                   }
    send_html_mail(titulo, template, datos_email, list_mail, [], [], CUENTAS_CORREOS[1][1])
    if per.sexo.id == 1:
        cuerpo = 'Estimada'
    elif per.sexo.id == 2:
        cuerpo = 'Estimado'
    else:
        cuerpo = 'Estimado/a'
    cuerpo += f' {per.nombre_completo()}, {texto}'
    notificacion(titulo, cuerpo, per, None, url, per.pk, 2, 'sga-sagest', PersonaSancion, request)

def obtener_tiempo_restante_seg(fecha_notify, horas=24):
    hoy = datetime.now()
    fecha_cierre = (fecha_notify + timedelta(hours=horas))
    return (fecha_cierre - hoy).total_seconds() if fecha_cierre > hoy else 0

def recover_file_temp(url_archivo, name_file):
    url_archivo = url_archivo.replace('/media/', '')
    if default_storage.exists(url_archivo):
        pdf_file = default_storage.open(url_archivo, 'rb')
        archivo_objeto = File(pdf_file, name=name_file)
        return archivo_objeto
    else:
        raise NameError('No se encontró el archivo temporal.')

