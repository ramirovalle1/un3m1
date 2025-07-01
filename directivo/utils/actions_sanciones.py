import json
from datetime import datetime

from django.core.files.storage import default_storage
from django.db import transaction
from django.http import JsonResponse
from django.template.loader import get_template

from core.choices.models.sagest import ROL_FIRMA_DOCUMENTO, ESTADO_SANCION_PERSONA, ETAPA_INCIDENCIA
from directivo.forms import (PlanificarAudienciaForm,ValidarAudienciaForm,
                             GenerarActaForm, AccionPersonalForm)
from directivo.models import IncidenciaSancion, AudienciaSancion, PersonaAudienciaSancion, DocumentoEtapaIncidencia, \
    PersonaSancion, PersonaFirmaDocumento
from directivo.utils.funciones import resposables_firma_doc, notificacion_validacion_caso, \
    notify_persona_decision_audiencia, obtener_tiempo_restante_seg, secciones_etapa_verificacion, \
    secciones_etapa_analisis, \
    secciones_etapa_audiencia, permisos_sanciones, notify_persona_sancion, notify_persona_audiencia, \
    resposable_firma_doc_rol, notify_director_legalizacion_accion_personal
from directivo.utils.strings import Strings
from sagest.funciones import encrypt_id, get_departamento, choice_indice
from sagest.models import Ubicacion, AccionPersonal, TipoAccionPersonal, MotivoAccionPersonal, DistributivoPersona, MotivoAccionPersonalDetalle, DenominacionPuesto, LogDia, PermisoInstitucional
from sga.funciones import log, generar_nombre, puede_realizar_accion_afirmativo, convertir_fecha_invertida
from sga.funcionesxhtml2pdf import conviert_html_to_pdf_save_file_model
from sga.models import Persona, MESES_CHOICES


#Acciones para planificar una audiencia
def get_planificaraudiencia(data={}, request=None):
    incidencia = IncidenciaSancion.objects.get(id=encrypt_id(request.GET['id']))
    form = PlanificarAudienciaForm(initial={'id_incidencia': incidencia.id, 'ubicacion': 107})
    form.fields['ubicacion'].queryset = Ubicacion.objects.filter(bloque_id=13, status=True)
    data['form'] = form
    data['incidencia'] = incidencia
    data['switchery'] = True
    roles = [4,5,6,12,13]
    data['responsables_firma'] = responsables_firms= resposables_firma_doc(2, roles)
    data['numDetalle'] = len(responsables_firms)
    data['roles'] = choice_indice(ROL_FIRMA_DOCUMENTO,roles)
    template = get_template('adm_directivos/forms/formplanificar.html')
    return template, data

def post_planificaraudiencia(data={}, request=None):
    try:
        hoy, audiencia, notificar = datetime.now(), None, False
        participantes = json.loads(request.POST['lista_items1'])
        action_ = request.POST.get('action', 'planificar')
        reprogramar = action_ == 'reprogramaraudiencia'
        id_audiencia = encrypt_id(request.POST.get('id',0))
        is_edit = id_audiencia > 0 and not reprogramar
        if len(participantes) < 4:
            raise NameError('Necesita seleccionar 4 participantes con los distintos roles disponibles')

        if is_edit:
            audiencia = AudienciaSancion.objects.get(id=id_audiencia)

        form = PlanificarAudienciaForm(request.POST, instancia=audiencia)
        if not form.is_valid():
            form_error = [{k: v[0]} for k, v in form.errors.items()]
            return {'result': True, "form": form_error, "mensaje": "Error en el formulario"}
        notificar = form.cleaned_data['notificar']
        estado = 1 if notificar else 0
        incidencia = IncidenciaSancion.objects.get(id=form.cleaned_data['id_incidencia'])
        if is_edit:
            notificar = notificar and audiencia.estado == 0
            text_log, action_log = 'Edito', 'edit'
            if audiencia.estado == 0:
                audiencia.fecha = form.cleaned_data['fecha']
                audiencia.horainicio = form.cleaned_data['horainicio']
                audiencia.horafin = form.cleaned_data['horafin']
                audiencia.estado = estado
            audiencia.referencia = form.cleaned_data['referencia']
            audiencia.bloque = form.cleaned_data['bloque']
            audiencia.ubicacion = form.cleaned_data['ubicacion']
            audiencia.descripcion = form.cleaned_data['descripcion']
            audiencia.save(request)
        else:
            text_log, action_log = 'Creo', 'add'
            audiencia = AudienciaSancion(incidencia_id=form.cleaned_data['id_incidencia'],
                                         fecha=form.cleaned_data['fecha'],
                                         horainicio=form.cleaned_data['horainicio'],
                                         horafin=form.cleaned_data['horafin'],
                                         referencia=form.cleaned_data['referencia'],
                                         bloque=form.cleaned_data['bloque'],
                                         ubicacion=form.cleaned_data['ubicacion'],
                                         estado=estado,
                                         descripcion=form.cleaned_data['descripcion'])
            audiencia.save(request)
            if reprogramar:
                aud_pro = AudienciaSancion.objects.get(id=id_audiencia)
                aud_pro.estado = 3
                aud_pro.save(request)

            for per_sancion in incidencia.personas_sancion_prodecedente():
                per_aud = PersonaAudienciaSancion(audiencia=audiencia, persona=per_sancion.persona, rol_firma=7)
                per_aud.save(request)

        audiencia.personaaudienciasancion_set.filter(status=True).exclude(rol_firma=7).update(status=False)
        roles_existentes = set()
        for p in participantes:
            rol = int(p['rol'])
            if rol in roles_existentes:
                raise NameError('No puede seleccionar dos veces el mismo rol')
            roles_existentes.add(rol)
            per_aud = PersonaAudienciaSancion(audiencia=audiencia, persona_id=int(p['id_persona']), rol_firma=rol, asistira=True)
            per_aud.save(request)

        if notificar:
            incidencia.personas_sancion_prodecedente().update(bloqueo=True)
            audiencia.fecha_notify = hoy
            audiencia.save(request)
            notificar_audiencia_bloqueo(request, audiencia)

        log(f'{text_log} planificación de audiencia: {audiencia}', request, action_log)
        return {'result': False, 'mensaje': 'Guardado con éxito'}
    except Exception as ex:
        transaction.set_rollback(True)
        return {'result': True, 'mensaje': f'{ex}'}
def get_detalleaudiencia(data={}, request=None):
    audiencia = AudienciaSancion.objects.get(id=encrypt_id(request.GET['id']))
    data['audiencia'] = audiencia
    template = get_template('adm_sanciones/modal/involucrados_audiencia.html')
    return template, data


#Acciones para generar un acta de audiencia
def generar_acta(documento, request):
    from directivo.models import PersonaFirmaDocumento, HistorialDocumentoFirma
    try:
        data = {}
        audiencia = documento.audiencia
        # Eliminar firmantes anteriores
        documento.responsables_legalizacion().update(status=False)

        # Guardar firmantes nuevos
        responsables = audiencia.personas_audiencia()
        for orden, r in enumerate(responsables):
            #se excluye al abogado para la firma
            if not r.rol_firma == 13:
                firmante = PersonaFirmaDocumento(documento=documento,
                                                 cargo=r.get_cargo(), persona=r.persona,
                                                 orden=orden+1, rol_firma=r.rol_firma)
                firmante.save(request)

        sustanciador = responsables.filter(rol_firma=4).first()
        secretario = responsables.filter(rol_firma=5).first()
        abogado = responsables.filter(rol_firma=13).first()
        nombre_archivo = generar_nombre(f'acta_audiencia_{documento.id}', 'generado') + '.pdf'
        data['documento'] = documento
        data['fechainicio'] = audiencia.fecha_inicio
        data['fechafin'] = audiencia.fecha_fin
        data['sustanciador'] = sustanciador.persona if sustanciador else ''
        data['secretario'] = secretario.persona if secretario else ''
        data['abogado'] = abogado.persona if abogado else ''
        data['servidor'] = responsables.filter(rol_firma=7).first().persona if responsables.filter(rol_firma=7).exists() else ''
        data['es_procedente'] = audiencia.estado_desicion == 2
        data['horainicio'] = audiencia.horainicio
        data['horafin'] = audiencia.horafin
        data['page_size'] = 'A4 landscape'
        template = 'adm_sanciones/documentos/acta_audiencia_pdf.html'
        pdf_file, response = conviert_html_to_pdf_save_file_model(template, data, nombre_archivo)
        documento.archivo = pdf_file
        documento.estado = 1
        documento.save(request)
        historial = HistorialDocumentoFirma(documento=documento, archivo=pdf_file, persona=documento.persona_elabora, estado=1)
        historial.save(request)
    except Exception as ex:
        raise NameError(f'Error al generar documento: {ex}')
def post_generaracta(data={}, request=None):
    try:
        id = encrypt_id(request.POST['id'])
        persona = request.session['persona']
        documento = DocumentoEtapaIncidencia.objects.get(id=id) if id > 0 else None
        form = GenerarActaForm(request.POST, instancia=documento)
        if not form.is_valid():
            transaction.set_rollback(True)
            form_error = [{k: v[0]} for k, v in form.errors.items()]
            return {'result': True, "form": form_error, "mensaje": "Error en el formulario"}
        if documento:
            audiencia = documento.audiencia
            documento = DocumentoEtapaIncidencia.objects.get(id=id)
            documento.persona_elabora = persona
            documento.save(request)
            log(f'Edito documento de etapa de sanción: {documento}', request, 'edit')
        else:
            audiencia = AudienciaSancion.objects.get(id=form.cleaned_data['id_audiencia'])
            documento = DocumentoEtapaIncidencia(incidencia=audiencia.incidencia,
                                                 audiencia=audiencia,
                                                 tipo_doc=2,
                                                 persona_elabora=persona)
            documento.save(request)
            log(f'Genero documento de etapa de sanción: {documento}', request, 'add')
        audiencia.numerodelegacion = form.cleaned_data['numerodelegacion']
        audiencia.save(request)
        generar_acta(documento, request)
        return {'result': False, 'mensaje': 'Guardado con éxito'}
    except Exception as ex:
        transaction.set_rollback(True)
        raise NameError(f"{ex}")
def get_generaracta(data={}, request=None):
    id, tipo_doc = encrypt_id(request.GET['id']), request.GET['idex']
    if not tipo_doc:
        documento = DocumentoEtapaIncidencia.objects.get(id=id)
        audiencia = documento.audiencia
        data['documento'] = documento
        data['id'] = documento.id
    else:
        data['tipo_doc'] = tipo_doc
        audiencia = AudienciaSancion.objects.get(id=id)

    data['audiencia'] = audiencia
    form = GenerarActaForm(initial={'id_audiencia': audiencia.id,
                                    'numerodelegacion': audiencia.numerodelegacion})
    data['form'] = form
    template = get_template('adm_sanciones/modal/formgeneraracta.html')
    return template, data


#Accion para el hisotrial de firmas
def get_historialfirmas(data={}, request=None):
    documento = DocumentoEtapaIncidencia.objects.get(id=encrypt_id(request.GET['id']))
    data['documento'] = documento
    template = get_template('adm_sanciones/modal/historial_firmas.html')
    return template, data


#Acciones para generar una acción personal
def get_generar_accionpersonal(data={}, request=None):
    id, tipo_doc = encrypt_id(request.GET['id']), request.GET['idex']
    depa_th = get_departamento()
    documento = None
    if not tipo_doc:
        documento = DocumentoEtapaIncidencia.objects.get(id=id)
        persona_sancion = documento.get_persona_sancion()
        data['documento'] = documento
        data['id'] = documento.id
    else:
        data['tipo_doc'] = tipo_doc
        persona_sancion = PersonaSancion.objects.get(id=id)

    denominaciones_id = DistributivoPersona.objects.filter(persona=persona_sancion.persona,
                                                           status=True).values_list('denominacionpuesto_id', flat=True)
    denominaciones = DenominacionPuesto.objects.filter(id__in=denominaciones_id)

    if persona_sancion.accionpersonal:
        form = AccionPersonalForm(initial={'id_personasancion': persona_sancion.id,
                                           # 'tipo': persona_sancion.accionpersonal.tipo,
                                           'motivoaccion': persona_sancion.accionpersonal.motivoaccion,
                                           'explicacion': persona_sancion.accionpersonal.explicacion,
                                           # 'partidapresupuestariaactual': persona_sancion.accionpersonal.partidapresupuestariaactual,
                                           'denominacionpuesto': persona_sancion.accionpersonal.denominacionpuestoactual,
                                           'fechadesde': persona_sancion.accionpersonal.fechadesde,
                                           'fechahasta': persona_sancion.accionpersonal.fechahasta,
                                           'procesoinstitucional': persona_sancion.accionpersonal.procesoinstitucional,
                                           'declaracion': persona_sancion.accionpersonal.declaracionjuramentada,
                                           'nivelgestion': persona_sancion.accionpersonal.nivelgestion,
                                           })
    else:
        form = AccionPersonalForm(initial={'id_personasancion': persona_sancion.id,
                                           # 'explicacion': persona_sancion.incidencia.falta.articulo,
                                           'denominacionpuesto': denominaciones.last() if len(denominaciones) == 1 else None
                                           })

    motivo_sanciones = MotivoAccionPersonal.objects.filter(status=True, id=26).first()
    if motivo_sanciones:
        detalle_motivo_accion = MotivoAccionPersonalDetalle.objects.filter(motivo=motivo_sanciones,
                                                                           regimenlaboral=persona_sancion.incidencia.falta.regimen_laboral,
                                                                           status=True).last()
        form.fields['explicacion'].initial = detalle_motivo_accion.baselegal.descripcion if detalle_motivo_accion.baselegal else ''
        form.fields['motivoaccion'].initial = motivo_sanciones

    if documento:
        responsables_firma = documento.responsables_legalizacion()
        director = responsables_firma.filter(rol_firma=14).first()
        nominador = responsables_firma.filter(rol_firma=9).first()
        form.fields['nominador'].queryset = Persona.objects.filter(id=nominador.persona.id)
        form.fields['nominador'].initial = nominador.persona
        form.fields['director'].queryset = Persona.objects.filter(id=director.persona.id)
        form.fields['director'].initial = director.persona
        form.fields['subrogante'].initial = director.subrogante
        form.fields['nominadordelegdo'].initial = nominador.subrogante
    else:
        director = resposable_firma_doc_rol(3, 14)
        nominador = resposable_firma_doc_rol(3, 9)
        form.fields['nominador'].queryset = Persona.objects.filter(id=nominador.id)
        form.fields['nominador'].initial = nominador
        form.fields['director'].queryset = Persona.objects.filter(id=director.id)
        form.fields['director'].initial = director

    form.fields['denominacionpuesto'].queryset = denominaciones
    data['form'] = form
    data['switchery'] = True
    data['persona_sancion'] = persona_sancion

    data['firma_servidor'] = firma_servidor = persona_sancion.servidor_firma_accion_personal()

    roles = [2, 8, 15]
    if not firma_servidor:
        roles.append(12) # Agregar testigo a responsables de firma
    data['roles'] = choice_indice(ROL_FIRMA_DOCUMENTO, roles)
    data['responsables_firma'] = responsables_firms = resposables_firma_doc(3, roles)
    data['numDetalle'] = len(responsables_firms)

    template = get_template('adm_sanciones/modal/formgeneraraccionpersonal.html')
    return template, data

def post_generar_accionpersonal(data={}, request=None):
    try:
        hoy = datetime.now()
        id = encrypt_id(request.POST['id'])
        persona = request.session['persona']
        documento = DocumentoEtapaIncidencia.objects.get(id=id) if id > 0 else None
        form = AccionPersonalForm(request.POST, instancia=documento)
        if not form.is_valid():
            transaction.set_rollback(True)
            form_error = [{k: v[0]} for k, v in form.errors.items()]
            return {'result': True, "form": form_error, "mensaje": "Error en el formulario"}

        personasancion = PersonaSancion.objects.get(id=form.cleaned_data['id_personasancion'])

        firma_servidor = personasancion.servidor_firma_accion_personal()

        participantes = json.loads(request.POST['lista_items1'])
        roles_obligatorios = [2, 8, 15]
        roles_enviados = [int(p['rol']) for p in participantes]
        if not firma_servidor:
            roles_obligatorios.append(12) # Agregar testigo a responsables de firma

        for rol in roles_obligatorios:
            if rol not in roles_enviados:
                raise NameError(f'Falta seleccionar un responsable de firma con el rol {ROL_FIRMA_DOCUMENTO[rol][1]}')

        motivo_accion = form.cleaned_data['motivoaccion']

        distributivo = DistributivoPersona.objects.filter(persona=personasancion.persona,
                                                          denominacionpuesto=form.cleaned_data['denominacionpuesto'],
                                                          regimenlaboral=personasancion.incidencia.falta.regimen_laboral,
                                                          status=True).last()
        motivo = MotivoAccionPersonalDetalle.objects.filter(motivo=motivo_accion,
                                                            regimenlaboral=distributivo.regimenlaboral, status=True).last()
        declaracionjuramentada = form.cleaned_data['declaracion']

        director = form.cleaned_data['director']
        es_director_subrogante = form.cleaned_data['subrogante']
        autoridadnominadora = form.cleaned_data['nominador']
        es_nominador_subrogante = form.cleaned_data['nominadordelegdo']

        if documento:
            documento = DocumentoEtapaIncidencia.objects.get(id=id)
            documento.persona_elabora = persona
            documento.save(request)
            log(f'Edito documento de etapa de sanción: {documento}', request, 'edit')
            accionpersonal = personasancion.accionpersonal
            # accionpersonal.tipo = form.cleaned_data['tipo']
            accionpersonal.subroganterrhh = form.cleaned_data['subrogante']
            accionpersonal.personauath = form.cleaned_data['director']
            accionpersonal.motivo = motivo
            accionpersonal.abreviatura = motivo_accion.abreviatura,
            accionpersonal.fechadesde=form.cleaned_data['fechadesde']
            accionpersonal.motivoaccion = form.cleaned_data['motivoaccion']
            accionpersonal.explicacion = form.cleaned_data['explicacion']
            # accionpersonal.partidapresupuestariaactual = form.cleaned_data['partidapresupuestariaactual']
            accionpersonal.procesoinstitucional = form.cleaned_data['procesoinstitucional']
            accionpersonal.fechahasta = form.cleaned_data['fechahasta']
            accionpersonal.declaracionjuramentada = declaracionjuramentada
            accionpersonal.nivelgestion = form.cleaned_data['nivelgestion']
            accionpersonal.estructuraprogramatica = distributivo.estructuraprogramatica
            accionpersonal.partidaindividual = distributivo.partidaindividual
            accionpersonal.save(request)
            log(f'Edito acción de personal: {accionpersonal}', request, 'edit')
        else:
            tipogrado = nummaximo = 0
            anioactual = hoy.year
            accion_per_last = AccionPersonal.objects.filter(anio=int(anioactual), status=True, motivoaccion=motivo_accion).order_by('numero').last()
            if accion_per_last:
                nummaximo = accion_per_last.numero
            doc = 'REGISTRO EN EL SISTEMA DE SANCIONES DE LA INSTITUCIÓN'
            accionpersonal = AccionPersonal(persona=personasancion.persona,
                                            subroganterrhh=es_director_subrogante,
                                            personauath=director,
                                            personaregistrocontrol=persona,
                                            numero=nummaximo + 1,
                                            fechaelaboracion=hoy,
                                            # tipo=form.cleaned_data['tipo'],
                                            motivoaccion=motivo_accion,
                                            anio=anioactual,
                                            # fechaaprobacion=permiso.permisoinstitucional.fecha_aprobacion(),
                                            fechadesde=form.cleaned_data['fechadesde'],
                                            # fechahasta=permiso.fechafin,
                                            explicacion=form.cleaned_data['explicacion'],
                                            regimenlaboral=distributivo.regimenlaboral,
                                            documento=doc,
                                            motivo=motivo,
                                            lugartrabajoactual='MILAGRO',
                                            abreviatura=motivo_accion.abreviatura,
                                            departamentoactual=distributivo.unidadorganica,
                                            denominacionpuestoactual=distributivo.denominacionpuesto,
                                            escalaocupacionalactual=distributivo.escalaocupacional,
                                            tipogradoactual=distributivo.grado,
                                            rmuactual=distributivo.rmupuesto,
                                            # partidapresupuestariaactual=form.cleaned_data['partidapresupuestariaactual'],
                                            tipogrado=tipogrado,
                                            fecharegistroaccion=hoy,
                                            procesoinstitucional=form.cleaned_data['procesoinstitucional'],
                                            fechahasta=form.cleaned_data['fechahasta'],
                                            declaracionjuramentada=declaracionjuramentada,
                                            nivelgestion=form.cleaned_data['nivelgestion'],
                                            estructuraprogramatica=distributivo.estructuraprogramatica,
                                            partidaindividual=distributivo.partidaindividual,
                                            )
            accionpersonal.save()
            log(f'Genero acción de personal: {accionpersonal}', request, 'add')
            personasancion.accionpersonal = accionpersonal
            personasancion.save(request)
            documento = DocumentoEtapaIncidencia(incidencia=personasancion.incidencia,
                                                 persona_recepta=personasancion.persona,
                                                 tipo_doc=3,
                                                 persona_elabora=persona,
                                                 accionpersonal=accionpersonal)
            documento.save(request)

        # Eliminar firmantes anteriores
        documento.responsables_legalizacion().update(status=False)

        crear_responsable_firma(documento, director, rol_firma=14, subrogante=es_director_subrogante, request=request)
        crear_responsable_firma(documento, autoridadnominadora, rol_firma=9, subrogante=es_nominador_subrogante, request=request)
        crear_responsable_firma(documento, persona, rol_firma=1, request=request)

        if firma_servidor:
            crear_responsable_firma(documento, personasancion.persona, rol_firma=7, request=request)
        else:
            crear_responsable_firma(documento, personasancion.persona, rol_firma=7, request=request, negativa=True)

        roles_existentes = set()
        for p in participantes:
            rol = int(p['rol'])
            if rol in roles_existentes:
                raise NameError('No puede seleccionar dos veces el mismo rol')
            roles_existentes.add(rol)
            pers = Persona.objects.get(id=int(p['id_persona']))
            per_firma = PersonaFirmaDocumento(documento=documento,
                                              cargo=pers.mi_cargo_administrativo(),
                                              persona=pers,
                                              rol_firma=rol)
            per_firma.save(request)

        log(f'Genero documento de acción de personal: {documento}', request, 'add')

        generar_accionpesonal({'documento': documento, 'persona_sancion': personasancion, 'firma_servidor': firma_servidor}, request)
        return {'result': False, 'mensaje': 'Guardado con éxito'}
    except Exception as ex:
        transaction.set_rollback(True)
        raise NameError(f"{ex}")

def generar_accionpesonal(context={}, request=None):
    from directivo.models import PersonaFirmaDocumento, HistorialDocumentoFirma
    try:
        personasancion = context['persona_sancion']
        documento = context['documento']

        context['accionpersona'] = accionpersonal = personasancion.accionpersonal
        context['numero'] = str(accionpersonal.numero).zfill(4)
        context['tipoacciones'] = TipoAccionPersonal.objects.filter(status=True)

        responsables_firma = documento.responsables_legalizacion()
        context['director'] = director =  responsables_firma.filter(rol_firma=14).first()

        context['nominador'] = nominador = responsables_firma.filter(rol_firma=9).first()

        context['elabora'] = elabora =  responsables_firma.filter(rol_firma=1).first()

        context['revisa'] = revisa = responsables_firma.filter(rol_firma=2).first()
        if not revisa:
            raise NameError('No se ha definido responsable de revisión')
        context['registro'] = registro = responsables_firma.filter(rol_firma=8).first()
        if not registro:
            raise NameError('No se ha definido responsable de registro y control')
        context['notifica'] = notifica = responsables_firma.filter(rol_firma=15).first()
        if not notifica:
            raise NameError('No se ha definido responsable de notificación')
        context['testigo'] = testigo = responsables_firma.filter(rol_firma=12).first()
        if not testigo and not context['firma_servidor']:
            raise NameError('No se ha definido testigo')
        context['servidor'] = responsables_firma.filter(rol_firma=7).first()

        context['fecha_actual'] = datetime.now()

        num_columnas = 4
        items_por_columna = 6  # Cantidad fija de ítems por columna
        motivoaccion = MotivoAccionPersonal.objects.filter(status=True, activo=True).order_by('orden')
        cantidad = len(motivoaccion)
        total_elementos_necesarios = num_columnas * items_por_columna
        if cantidad < total_elementos_necesarios:
            num_columnas = (cantidad + items_por_columna - 1) // items_por_columna  # Ajustar número de columnas si hay menos elementos

        # Diccionario para almacenar las columnas
        motivoseccion = {}

        # Variables de control para definir los índices de inicio y fin
        inicio = 0

        for i in range(num_columnas):
            # Calcular el índice final para la columna actual
            fin = inicio + items_por_columna

            # Si es la última columna, agregar todos los elementos restantes
            if fin > cantidad:
                fin = cantidad

            # Asignar la queryset de Accionpersona relacionada a la columna actual
            motivoseccion[f'columna_{i+1}'] = MotivoAccionPersonal.objects.filter(status=True, activo=True).order_by('orden')[inicio:fin]

            # Actualizar el índice de inicio para la próxima iteración
            inicio = fin
        context['motivoseccion'] = motivoseccion
        nombre_archivo = generar_nombre(f'accion_personal_{accionpersonal.id}', 'generado') + '.pdf'
        context['page_size'] = 'A4 landscape'
        template = 'adm_sanciones/documentos/accionpersonal_pdf_new.html'
        pdf_file, response = conviert_html_to_pdf_save_file_model(template, {'data':context}, nombre_archivo)

        #Documento de etapa de sanción
        documento.archivo = pdf_file
        documento.estado = 1
        documento.save(request)

        #Acción de personal
        accionpersonal.archivo = pdf_file
        accionpersonal.save(request)

        #Historial de firmas
        historial = HistorialDocumentoFirma(documento=documento, archivo=pdf_file, persona=documento.persona_elabora, estado=1)
        historial.save(request)
    except Exception as ex:
        raise NameError(f'Error al generar documento: {ex}')

def post_cambiarestado_audiencia(data={}, request=None):
    try:
        hoy = datetime.now()
        id, estado = request.POST['id'].split(',')
        audiencia = AudienciaSancion.objects.get(pk=encrypt_id(id))
        estado = int(estado)
        incidencia = audiencia.incidencia
        if estado in [4, 5]:
            # CAMBIOS DE ESTADOS CUANDO SE EJECUTA LA AUDIENCIA
            audiencia.estado = estado
            if estado == 4:
                incidencia.personas_sancion_prodecedente().update(bloqueo=False)
                incidencia.estado = 7
                audiencia.fecha_inicio = hoy
                if not audiencia.detalle_audiencia().exists():
                    audiencia.detalle_inicial_audiencia()
            else:
                incidencia.estado = 8
                audiencia.fecha_fin = hoy
            incidencia.save(request)
            audiencia.save(request)
        else:
            # CAMBIOS DE ESTADOS CUANDO SE PLANIFICAN LA AUDIENCIA
            audiencia.estado = int(estado)
            if audiencia.estado == 1:
                audiencia.fecha_notify = hoy
                notificar_audiencia_bloqueo(request, audiencia)

            audiencia.save(request)
        log(f'Actualizo estado de audiencia: {audiencia}', request, 'edit')
        return {'result': False, 'mensaje': 'Guardado con éxito'}
    except Exception as ex:
        transaction.set_rollback(True)
        raise NameError(f"{ex}")

def post_validar_audiencia(data={}, request=None):
    try:
        form = ValidarAudienciaForm(request.POST)
        if not form.is_valid():
            form_error = [{k: v[0]} for k, v in form.errors.items()]
            return {'result': True, "form": form_error, "mensaje": "Error en el formulario"}

        audiencia = AudienciaSancion.objects.get(id=encrypt_id(form.cleaned_data['id_audiencia']))
        audiencia.estado_desicion = form.cleaned_data['estado_desicion']
        audiencia.observacion = form.cleaned_data['observacion']
        audiencia.save(request)

        incidencia = audiencia.incidencia
        if int(audiencia.estado_desicion) == 1:
            incidencia.estado = 11
        else:
            incidencia.estado = 8
        incidencia.save(request)

        personas_sancion = json.loads(request.POST['lista_items1'])
        for elemento in personas_sancion:
            estado = int(elemento['estado'])
            persona_sancion = PersonaSancion.objects.get(id=elemento['id_personasancion'])
            persona_sancion.estado = estado
            persona_sancion.save(request)
            # ENVIA NOTIFICACION
            notify_persona_decision_audiencia(request, persona_sancion, audiencia)
        log(f'Actualizo estado de decisión de audiencia: {audiencia}', request, 'edit')
        return {'result': False, 'mensaje': 'Guardado con éxito'}
    except Exception as ex:
        transaction.set_rollback(True)
        raise NameError(f"{ex}")

def get_validar_audiencia(data={}, request=None):
    audiencia = AudienciaSancion.objects.get(id=encrypt_id(request.GET['id']))
    data['audiencia'] = audiencia
    data['form'] = ValidarAudienciaForm(initial={'id_audiencia': audiencia.id})
    data['estados_persona'] = ESTADO_SANCION_PERSONA[3:]
    data['personas_sancion'] = audiencia.incidencia.personas_sancion_prodecedente()
    template = get_template('adm_sanciones/modal/formvalidaraudiencia.html')
    return template, data

def get_revisar_audiencia(data={}, request=None):
    try:
        persona = request.session['persona']
        data['title'] = 'Caso delegado'
        id = encrypt_id(request.GET['id'])
        incidencia = IncidenciaSancion.objects.get(id=id)
        data['incidencia'] = incidencia
        audiencia = incidencia.audiencia_actual()
        pers_sancion = incidencia.personas_sancion_prodecedente().first()

        if pers_sancion and incidencia.estado == 5 and pers_sancion.fecha_notify:
            data['mostrar_notificacion'] = True
            data['text_tiempo_restante'] = Strings.tiempoRespuestaDescargo
            data['text_tiempo_fin'] = Strings.tiempoRespuestaDescargoFin
            data['tiempo_restante'] = obtener_tiempo_restante_seg(pers_sancion.fecha_notify, 24)

        elif audiencia and incidencia.estado == 6 and audiencia.fecha_notify:
            data['mostrar_notificacion'] = True
            data['text_tiempo_restante'] = Strings.tiempoRespuestaAudiencia
            data['text_tiempo_fin'] = Strings.tiempoRespuestaAudienciaFin
            data['tiempo_restante'] = obtener_tiempo_restante_seg(audiencia.fecha_notify, 24)

        data['etapas'] = ETAPA_INCIDENCIA
        data['secciones_verificacion'] = secciones_etapa_verificacion()
        data['secciones'] = secciones_etapa_analisis()
        data['secciones_audiencia'] = secciones_etapa_audiencia()
        data['permisos'] = permisos = permisos_sanciones(persona)
        if request.path == '/adm_sanciones':
            param = '?biometrico=True' if incidencia.persona.id == 1 else ''
        if request.path == '/adm_directivos':
            param = '?action=incidencias'
        else:
            param = '?action=sanciones'
        data['url_atras'] = f'{request.path}{param}'
        template = 'adm_directivos/forms/formrevision.html'
        return template, data
    except Exception as ex:
        raise NameError(f"Error inesperado: {ex}")

def post_remitir_descargo(data={}, request=None):
    try:
        hoy= datetime.now()
        instancia = IncidenciaSancion.objects.get(pk=encrypt_id(request.POST['id']))
        instancia.estado = 5
        instancia.save(request)
        personas_sancion = instancia.personas_sancion_prodecedente()
        for per in personas_sancion:
            per.bloqueo = True
            per.fecha_notify = hoy
            per.save(request)
            notify_persona_sancion(request, per)
        log(f'Se remite para respuesta de descargo: {instancia}', request, 'edit')
        return {'result': 'ok','showSwal':True,'titulo':'Caso remitido' ,'mensaje': 'Se remitio y notifico al servidor para su respuesta de descargo.'}
    except Exception as ex:
        raise NameError(f"{ex}")

def get_render_marcadas(data={}, request=None):
    try:
        data['title'] = u'LOG de Marcadas'
        data['subtitle'] = 'Consulte las marcadas laborales del funcionario a su cargo.'
        data['funcionario'] = persona = data.get('funcionario', request.session['persona'])
        data['anios'] = sorted(persona.lista_anios_trabajados_log(), reverse=True)
        data['jornadas'] = persona.historialjornadatrabajador_set.all()
        data['destino'] = 'th_hojavida'
        data['pued_modificar'] = 1
        data['hora'] = str(datetime.now().time())[0:5]
        return data
    except Exception as ex:
        raise NameError(f"Error inesperado: {ex}")


def get_cargar_meses_marcadas(data={}, request=None):
    try:
        personad = Persona.objects.get(pk=encrypt_id(request.GET['value']))
        anio = int(request.GET['args'])
        lista = []
        for e in LogDia.objects.filter(persona=personad, fecha__year=anio, status=True).order_by('fecha').distinct():
            if [e.fecha.month, MESES_CHOICES[e.fecha.month - 1][1]] not in lista:
                lista.append([e.fecha.month, MESES_CHOICES[e.fecha.month - 1][1]])
        return {"lista": lista, 'result': True, 'action': request.GET['action']}
    except Exception as ex:
        raise NameError(f"{ex}")

def get_cargar_marcadas(data={}, request=None):
    try:
        hoy = datetime.now()
        data['persona'] = personad = Persona.objects.get(pk=int(request.GET['value']))
        data['administrativo'] = personad
        anio = request.GET['args[anio]']
        mes = request.GET['args[mes]']
        puede_modificar = int(request.GET.get('args[puede_modificar]', 0))
        data['puede_modificar'] = False
        data['dias'] = LogDia.objects.filter(persona=personad, fecha__year=anio, fecha__month=mes, status=True).order_by('fecha')
        template = get_template("th_marcadas/detallejornadatrab_log.html")
        json_content = template.render(data)
        return {"result": True, 'data': json_content, 'action': request.GET['action']}
    except Exception as ex:
        raise NameError(f"{ex}")

def generar_reporte_marcada(data={}, request=None):
    data['punto_control'] = punto_control = int(request.GET['args[punto_control]'])
    data['id_persona'] = id_persona = int(request.GET['args[id_persona]'])
    data['id_requisito'] = id_requisito = int(request.GET['args[id_requisito]'])
    data['persona_sancion'] = persona = Persona.objects.get(id=id_persona)
    name_file = f'reporte_evidecia_{id_persona}_{id_requisito}_{punto_control}.pdf'
    if punto_control == 2:
        data['fecha_inicio'] = fecha_inicio = convertir_fecha_invertida(request.GET['args[fecha_inicio]'])
        data['fecha_fin'] = fecha_fin = convertir_fecha_invertida(request.GET['args[fecha_fin]'])
        permisos = PermisoInstitucional.objects.filter(solicita_id=id_persona, status=True,
                                                        permisoinstitucionaldetalle__fechainicio__gte=fecha_inicio,
                                                        permisoinstitucionaldetalle__fechafin__lte=fecha_fin).exclude(estadosolicitud=4)
        if permisos.exists():
            permiso = permisos.first()
            raise NameError(f'No se puede generar el reporte, el funcionario tiene permisos institucionales activos {permiso.secuencia} en el rango de fechas seleccionado.')
        marcadas = LogDia.objects.filter(persona=persona, fecha__gte=fecha_inicio, fecha__lte=fecha_fin, status=True).order_by('fecha')
        context = {'pagesize': 'A4',
                    'marcadas': marcadas,
                    'persona': persona, 'fechainicio': fecha_inicio, 'fechafin': fecha_fin, 'hoy': datetime.now().date()
                    }
        template = 'th_hojavida/informemarcadas.html'

    pdf_file, response = conviert_html_to_pdf_save_file_model(template, context,name_file)
    path = default_storage.save(f'temp/{name_file}', pdf_file)
    # Obtener la URL para acceder al archivo
    data['file_url'] = default_storage.url(path)
    return data

def notificar_audiencia_bloqueo(request, audiencia):
    try:
        for per_aud in audiencia.get_personas_audiencia_procedentes():
            notify_persona_audiencia(request, per_aud)
        audiencia.incidencia.personas_sancion_prodecedente().update(bloqueo=True)
    except Exception as ex:
        transaction.set_rollback(True)
        raise NameError(f"{ex}")

def crear_responsable_firma(documento, persona, rol_firma, subrogante=False, request=None, negativa=False):
    PersonaFirmaDocumento(
        documento=documento,
        cargo=persona.mi_cargo_administrativo(),
        persona=persona,
        subrogante=subrogante,
        rol_firma=rol_firma,
        negativa=negativa
    ).save(request)