#GenerarDocumentoForm
from sga.templatetags.sga_extras import fecha_natural, title2


class Strings:
    tooltipAntecedentesForm = ('Se debe establecer los indicios de todos aquellos documentos como: '
                               'informes, correos electrónicos, memorandos, oficios de entidades '
                               'externas, que preceden a la incidencia del cometimiento de una falta '
                               'disciplinaria que guardan relación con el objeto del informe.')

    tooltipMotivacionTecnicaForm = ('Se debe detallar la información principal (aclarar, explicar, ejemplificar, definir, '
                                    'describir, analizar, narrar, o informar) en muchos casos con subtítulos y elementos '
                                    'paratextuales, y eventualmente, los hechos que sucedieron para llegar a la '
                                    'incidencia del cometimiento de las solicitudes de las  faltas disciplinarias.')

    tooltipConclusionesForm = ('Se debe redactar los resultados más importantes y los puntos primordiales de '
                               'la actividad realizada en concordancia con el objeto del informe, además de indicar qué solicitudes '
                               'son las que proceden a dar inicio con el trámite.')

    tooltipRecomendacionesForm = (
                                'Se debe redactar sugerencias a la luz de las conclusiones, es decir que se debe sugerir respecto '
                                'a la forma de mejorar la motivación técnica del informe. '
                                'Sugerir acciones específicas en base a las consecuencias.]')

    tooltipFaltaDisciplinariaForm = (
                                'Una motivación jurídica es una justificación escrita basada en normas legales, jurisprudencia '
                                'y doctrina para sustentar una decisión, solicitud o interpretación en el ámbito legal. '
                                'Su propósito es argumentar de manera clara y fundamentada cómo se aplican las '
                                'disposiciones jurídicas a un caso concreto, presentando las leyes y '
                                'precedentes relevantes, y justificando la acción o resolución propuesta.')

    tooltipObjetoForm = 'Detallar cual es la finalidad de la elaboración del informe usando verbo+contenido+criterio+condición'

    tooltipFalta = 'Nombre de la falta disciplinaria, ejm: LEVE'

    tooltipDesFalta = 'Descripción de la falta disciplinaria'

    tooltipArticuloFalta = 'Artículo o artículos que sustentan la falta disciplinaria'

    ckeditorConclusionesForm = ('<p style="text-align:justify">'
                                'Con la presente argumentación jurídica y técnica del presente informe se concluye que:'
                                '</p>'
                                '<ol>'
                                '<li style="text-align:justify">Que,</li>'
                                '</ol>')

    ckeditorRecomendacionesForm = ('<ol>'
                                   '<li style="text-align:justify">Que, una vez que el servidor haya generado las '
                                   'pruebas de descargo se de inicio con el proceso.</li>'
                                   '<li style="text-align:justify">Que, </li>'
                                   '<li style="text-align:justify">Que, </li>'
                                   '</ol>')

    RecomendacionesInformeSustanciacion = ('<ol>'
                                           '<li style="text-align:justify">Que, </li>'
                                           '</ol>')

    correoCasoProcede = ("Por medio de la presente, le informamos que, tras una revisión exhaustiva de los hechos y "
                         "las pruebas presentadas en relación con la denuncia interpuesta en su contra, "
                         "hemos determinado que su caso procede conforme a lo establecido en el Régimen Disciplinario de esta institución. "
                         "En consecuencia, se iniciarán las acciones correspondientes, de las cuales será debidamente informado/a en su momento.")

    correoNoCasoProcede = ('Por medio de la presente, le informamos que, tras una revisión exhaustiva de los '
                           'hechos y las pruebas presentadas en relación con la denuncia interpuesta en su contra, hemos '
                           'determinado que su caso no procede conforme a lo establecido en el Régimen Disciplinario de esta institución. '
                           'En virtud de esta decisión, no se tomarán acciones adicionales respecto a la denuncia en su contra.')

    tiempoRespuestaDescargo = ('Tiempo restante para presentar respuesta de descargo:')

    tiempoRespuestaDescargoFin = ('Tiempo finalizado para presentar respuesta de descargo')

    tiempoRespuestaAudiencia = ('Tiempo restante para la confirmación de asistencia a la audiencia:')

    tiempoRespuestaAudienciaFin = ('Tiempo finalizado para la confirmación de asistencia a la audiencia')



#FUNCIONES
def get_text_campo_objeto(incidencia):
    try:
        servidores = incidencia.personas_sancion()
        count = servidores.count()
        text = 'los servidores' if count > 1 else 'el servidor'
        nombres = [f'{p.persona.nombre_completo().title()}' for p in servidores]
        if len(nombres) > 1:
            nombres_str = ', '.join(nombres[:-1]) + ' y ' + nombres[-1]
        else:
            nombres_str = nombres[0] if nombres else ''
        return (f'Informar incumplimiento enmarcado a la normativa del régimen {incidencia.falta.regimen_laboral} '
                f'motivando la aplicación de la sanción adecuado a {text} {nombres_str}'
                f' para determinar las medidas correctivas pertinentes.')
    except Exception as e:
        return ''

def get_text_campo_objeto_informe_sustanciacion(incidencia):
    try:
        servidores = incidencia.personas_sancion()
        count = servidores.count()
        text = 'los servidores' if count > 1 else 'el servidor'
        nombres = [f'{p.persona.nombre_completo().title()}' for p in servidores]
        if len(nombres) > 1:
            nombres_str = ', '.join(nombres[:-1]) + ' y ' + nombres[-1]
        else:
            nombres_str = nombres[0] if nombres else ''
        return (f'Informar medidas correctivas a {text} {nombres_str}'
                f' enmarcadas a la normativa del régimen {incidencia.falta.regimen_laboral}.')
    except Exception as e:
        return ''

def get_text_antecedentes_informe_echos(incidencia):
    try:
        text_director = 'de la directora' if incidencia.persona.sexo_id == 1 else 'del director'
        return(f'<p style="text-align: justify;">El {fecha_natural(incidencia.fecha_creacion)}, {title2(incidencia.departamento.nombre_text())} '
               f'a través {text_director} de {title2(incidencia.departamento.nombre_text())}, {incidencia.persona.nombre_completo_minus()} '
               f'presentó una incidencia de cometimiento de una falta disciplinaria contra {title2(incidencia.personas_sancion_text())}.'
               f' Debido a {title2(incidencia.motivo.motivoref.nombre)}, {title2(incidencia.motivo.nombre)}. '
               f'Mediante el requerimiento presentado, la Dirección de Talento Humano / Comisión de Acoso, Discriminación y Violencia de Género / '
               f'Comité de Régime Disciplinario inicia el trámite oportuno.</p>')
    except Exception as e:
        return ''


def get_text_motivacion_tecnica_informe_echos(incidencia):
    try:
        text_director = 'de la directora' if incidencia.persona.sexo_id == 1 else 'del director'
        return (
            f'<p style="text-align: justify;">Que, la Dirección de {title2(incidencia.departamento.nombre_text())}, a través {text_director} de '
            f'{title2(incidencia.departamento.nombre_text())},'
            f' {incidencia.persona.nombre_completo_minus()} presentó una incidencia de cometimiento de una falta disciplinaria '
            f'contra {title2(incidencia.personas_sancion_text())}.'
            f' Debido a {title2(incidencia.motivo.motivoref.nombre)}, {title2(incidencia.motivo.nombre)}. Mediante el requerimiento presentado,'
            f' la Dirección de Talento Humano inicia el procedimiento oportuno.</p>'
            f'<p style="text-align: justify;">Que, una vez validado el caso a cargo de la Dirección de Talento Humano se evidencia '
            f'que el requerimiento cuenta con los insumos necesarios para empezar el proceso de régimen disciplinario, '
            f'mismo que será notificado al servidor para dar inicio con el descargo correspondiente. Cuando se haya cumplido '
            f'con el tiempo establecido para subir las evidencias correspondientes, se le notificará al servidor, a cargo de la '
            f'Dirección de Talento Humano, la audiencia agendada, misma que el servidor sólo podrá pedir reprogramación una vez.</p>'
            f'<p style="text-align: justify;">Al momento que se dé por finalizada la audiencia el director de talento humano generará la acta '
            f'de audiencia correspondiente para que sea legalizada por las personas correspondientes, y a su vez generar la acción de personal '
            f'correspondiente. </p>')
    except Exception as e:
        return ''

def get_text_motivacion_tecnica_informe_sustanciacion(incidencia):
    try:
        text_director = 'de la directora' if incidencia.persona.sexo_id == 1 else 'del director'
        return (
            f'<p style="text-align: justify;">Que, la Dirección de {title2(incidencia.departamento.nombre_text())}, a través {text_director} de '
            f'{title2(incidencia.departamento.nombre_text())},'
            f' {incidencia.persona.nombre_completo_minus()} presentó una incidencia de cometimiento de una falta disciplinaria '
            f'contra {title2(incidencia.personas_sancion_text())}.'
            f' Debido a {title2(incidencia.motivo.motivoref.nombre)}, {title2(incidencia.motivo.nombre)}. Mediante el requerimiento presentado,'
            f' la Dirección de Talento Humano inició el trámite oportuno.</p>'
            f'<p style="text-align: justify;">Una vez validado el caso y haber seguido con el proceso correspondiente hasta la audiencia, '
            f'esta es concluida con las personas interesadas, en la cual se indicó lo siguiente:</p>')
    except Exception as e:
        return ''


def get_text_concluciones_informe_sustanciacion(incidencia):
    try:
        return (
            f'<p style="text-align: justify;">Con la presente argumentación jurídica y técnica del presente informe se concluye que:</p>'
            f'<ol>'
            '<li style="text-align:justify">Que, concluida la audiencia los resultados presentados por ésta Autoridad concluye que los hechos <b>no</b> o <b>si</b> constituyen existencia del incumplimiento, '
            'en definitiva <b>no</b> o <b>si</b> se ha justificado plenamente la existencia del mismo</li>'
            '</ol>')
    except Exception as e:
        return ''
