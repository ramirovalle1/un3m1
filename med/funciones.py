# coding=utf-8
from __future__ import division

def actioncalculotestpsicologico(personatestpsicologica, nombreaccion):
    if nombreaccion == 'calculo_diagnostico_salamanca':
        return calculo_diagnostico_salamanca(personatestpsicologica)
    elif nombreaccion == 'calculo_diagnostico_ansiedad_depresion':
        return calculo_diagnostico_ansiedad_depresion(personatestpsicologica)
    elif nombreaccion == 'calculo_diagnostico_autoestima_rosermberg':
        return calculo_diagnostico_autoestima_rosermberg(personatestpsicologica)
    else:
        return {"result": False, "msg": "Calculo no encontrado"}


def calculo_diagnostico_salamanca(personatestpsicologica):
    try:
        if not personatestpsicologica:
            raise NameError("Error no se puedo calcular el diagnostico")
        repuestas = personatestpsicologica.respuestas.all()
        par = 0
        for repuesta in repuestas[0:2]:
            if repuesta.respuesta.valor == 1.0:
                if repuesta.respuesta_children:
                    par += int(repuesta.respuesta_children_valor)
        esq = 0
        for repuesta in repuestas[2:4]:
            if repuesta.respuesta.valor == 1.0:
                if repuesta.respuesta_children:
                    esq += int(repuesta.respuesta_children_valor)

        eqt = 0
        for repuesta in repuestas[4:6]:
            if repuesta.respuesta.valor == 1.0:
                if repuesta.respuesta_children:
                    eqt += int(repuesta.respuesta_children_valor)

        hist = 0
        for repuesta in repuestas[6:8]:
            if repuesta.respuesta.valor == 1.0:
                if repuesta.respuesta_children:
                    hist += int(repuesta.respuesta_children_valor)

        ant = 0
        for repuesta in repuestas[8:10]:
            if repuesta.respuesta.valor == 1.0:
                if repuesta.respuesta_children:
                    ant += int(repuesta.respuesta_children_valor)

        nar = 0
        for repuesta in repuestas[10:12]:
            if repuesta.respuesta.valor == 1.0:
                if repuesta.respuesta_children:
                    nar += int(repuesta.respuesta_children_valor)

        ie_imp = 0
        for repuesta in repuestas[12:14]:
            if repuesta.respuesta.valor == 1.0:
                if repuesta.respuesta_children:
                    ie_imp += int(repuesta.respuesta_children_valor)

        ie_lim = 0
        for repuesta in repuestas[14:16]:
            if repuesta.respuesta.valor == 1.0:
                if repuesta.respuesta_children:
                    ie_lim += int(repuesta.respuesta_children_valor)

        anan = 0
        for repuesta in repuestas[16:18]:
            if repuesta.respuesta.valor == 1.0:
                if repuesta.respuesta_children:
                    anan += int(repuesta.respuesta_children_valor)

        dep = 0
        for repuesta in repuestas[18:20]:
            if repuesta.respuesta.valor == 1.0:
                if repuesta.respuesta_children:
                    dep += int(repuesta.respuesta_children_valor)

        ans = 0
        for repuesta in repuestas[20:22]:
            if repuesta.respuesta.valor == 1.0:
                if repuesta.respuesta_children:
                    ans += int(repuesta.respuesta_children_valor)

        msgPAR = 'GRUPO A - [PAR] PARANOIDE: tiene (%s) puntos <br>' % par
        msgPARVerbose = '[PAR] PARANOIDE: (%s) <br>' % par

        msgESQ = 'GRUPO A - [ESQ] ESQUIZOIDE: tiene (%s) puntos <br>' % esq
        msgESQVerbose = '[ESQ] ESQUIZOIDE: (%s) <br>' % esq

        msgEQT = 'GRUPO A - [EQT] ESQUIZOTÍPICO: tiene (%s) puntos <br>' % eqt
        msgEQTVerbose = '[EQT] ESQUIZOTÍPICO: (%s) <br>' % eqt

        msgHIST = 'GRUPO B - [HIST] HISTRIÓNICO: tiene (%s) puntos <br>' % hist
        msgHISTVerbose = '[HIST] HISTRIÓNICO: (%s) <br>' % hist

        msgANT = 'GRUPO B - [ANT] ANTISOCIAL: tiene (%s) puntos <br>' % ant
        msgANTVerbose = '[ANT] ANTISOCIAL: (%s) <br>' % ant

        msgNAR = 'GRUPO B - [NAR] NARCISISTA: tiene (%s) puntos <br>' % nar
        msgNARVerbose = '[NAR] NARCISISTA: (%s) <br>' % nar

        msgIE_IMP = 'GRUPO B - [IE IMP] Trastorno de inestabilidad emocional de la personalidad:<br> SUBTIPO IMPULSIVO: tiene (%s) puntos <br>' % ie_imp
        msgIE_IMPVerbose = '[IE IMP] Trastorno de inestabilidad emocional de la personalidad:<br> SUBTIPO IMPULSIVO: (%s) <br>' % ie_imp

        msgIE_LIM = 'GRUPO B - [IE LIM] Trastorno de inestabilidad emocional de la personalidad:<br> SUBTIPO LÍMITE: tiene (%s) puntos <br>' % ie_lim
        msgIE_LIMVerbose = '[IE LIM] Trastorno de inestabilidad emocional de la personalidad:<br> SUBTIPO LÍMITE: (%s) <br>' % ie_lim

        msgANAN = 'GRUPO C - [ANAN] ANANCÁSTICO: tiene (%s) puntos <br>' % anan
        msgANANVerbose = '[ANAN] ANANCÁSTICO: (%s) <br>' % anan

        msgDEP = 'GRUPO C - [DEP] DEPENDIENTE: tiene (%s) puntos <br>' % dep
        msgDEPVerbose = '[DEP] DEPENDIENTE: (%s) <br>' % dep

        msgANS = 'GRUPO C - [ANS] ANSIOSO: tiene (%s) puntos <br>' % ans
        msgANSVerbose = '[ANS] ANSIOSO: (%s) <br>' % ans

        return {"result": True,
                "msg": "",
                'diagnostico': "%s %s %s %s %s %s %s %s %s %s %s" % (msgPAR, msgESQ, msgEQT, msgHIST, msgANT, msgNAR, msgIE_IMP, msgIE_LIM, msgANAN, msgDEP, msgANS),
                'diagnosticoverbose': "%s %s %s %s %s %s %s %s %s %s %s" % (msgPARVerbose, msgESQVerbose, msgEQTVerbose, msgHISTVerbose, msgANTVerbose, msgNARVerbose, msgIE_IMPVerbose, msgIE_LIMVerbose, msgANANVerbose, msgDEPVerbose, msgANSVerbose),
                }
    except Exception as ex:
        return {"result": False,
                "msg": "Error en calculo no encontrado"
                }


def calculo_diagnostico_ansiedad_depresion(personatestpsicologica):
    """
        CRITERIOS DE EVALUACIÓN
            Subescala de ANSIEDAD: 4 o más respuestas afirmativas.
            Subescala de DEPRERSIÓN: 2 o más respuestas afirmativas
    :return:
    """
    try:
        if not personatestpsicologica:
            raise NameError("Error no se puedo calcular el diagnostico")
        ansiedad = 0
        repuestas = personatestpsicologica.respuestas.all()
        for repuesta in repuestas[0:9]:
            if repuesta.respuesta.valor == 1.0:
                ansiedad += 1
        depresion = 0
        for repuesta in repuestas[9:18]:
            if repuesta.respuesta.valor == 1.0:
                depresion += 1

        msgAnsiedad = 'Subescala de ANSIEDAD: tiene (%s) afirmativas' % ansiedad
        msgDepresion = 'Subescala de DEPRERSIÓN: tiene (%s) afirmativas' % depresion
        msgAnsiedadVerbose = ''
        msgDepresionVerbose = ''
        if ansiedad >= 4:
            msgAnsiedadVerbose = 'Tiene ANSIEDAD'
        else:
            msgAnsiedadVerbose = 'No tiene ANSIEDAD'

        if depresion >= 2:
            msgDepresionVerbose = 'Tiene DEPRERSIÓN'
        else:
            msgDepresionVerbose = 'No tiene DEPRERSIÓN'

        return {"result": True,
                "msg": "",
                'diagnostico': "%s y %s" % (msgAnsiedad, msgDepresion),
                 'diagnosticoverbose': "%s y %s" % (msgAnsiedadVerbose, msgDepresionVerbose)
                }
    except Exception as ex:
        return {"result": False,
                "msg": "Error en calculo no encontrado"
                }


def calculo_diagnostico_autoestima_rosermberg(personatestpsicologica):
    """
        Interpretación:
            De los ítems 1 al 5, las respuestas A a D se puntúan de 4 a 1
            De los ítems del 6 al 10, las respuestas A a D se puntúan de 1 a 4.
            De 30 a 40 puntos: Autoestima elevada. Considerada como autoestima normal.
            De 26 a 29 puntos. Autoestima media. No presenta problemas de autoestima grave, pero es
            conveniente mejorarla.
            Menos de 25 puntos: autoestima baja. Existen problemas significativos de autoestima
    :return:
    """
    try:
        if not personatestpsicologica:
            raise NameError("Error no se puedo calcular el diagnostico")
        puntos = 0
        repuestas = personatestpsicologica.respuestas.all()
        for repuesta in repuestas[0:5]:
            if repuesta.respuesta.valor == 1.0:
                puntos += 4
            elif repuesta.respuesta.valor == 2.0:
                puntos += 3
            elif repuesta.respuesta.valor == 3.0:
                puntos += 2
            elif repuesta.respuesta.valor == 4.0:
                puntos += 1

        for repuesta in repuestas[5:10]:
            if repuesta.respuesta.valor == 1.0:
                puntos += 1
            elif repuesta.respuesta.valor == 2.0:
                puntos += 2
            elif repuesta.respuesta.valor == 3.0:
                puntos += 3
            elif repuesta.respuesta.valor == 4.0:
                puntos += 4
        msg = ''
        msgVerbose = ''
        if puntos < 25:
            msg = '(Puntos: %s) - Menos de 25 puntos: autoestima baja. Existen problemas significativos de autoestima.' % puntos
            msgVerbose = 'Autoestima baja. Existen problemas significativos de autoestima'
        elif 26 <= puntos <= 29:
            msg = '(Puntos: %s) - De 26 a 29 puntos. Autoestima media. No presenta problemas de autoestima grave, pero es conveniente mejorarla.' % puntos
            msgVerbose = 'Autoestima media. No presenta problemas de autoestima grave, pero es conveniente mejorarla'
        elif 30 <= puntos <= 40:
            msg = '(Puntos: %s) - De 30 a 40 puntos: Autoestima elevada. Considerada como autoestima normal.' % puntos
            msgVerbose = 'Autoestima elevada. Considerada como autoestima normal.'

        return {"result": True,
                "msg": "",
                'diagnostico': msg,
                'diagnosticoverbose': msgVerbose
                }
    except Exception as ex:
        return {"result": False,
                "msg": "Error en calculo no encontrado"
                }
