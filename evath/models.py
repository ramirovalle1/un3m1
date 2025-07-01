from django.db import models
from sga.funciones import ModeloBase
from sga.models import Persona
from django.db.models import Sum, Q, F, FloatField
from django.db.models.functions import Coalesce

TIPO_PREGUNTA = (
    (1, "Opción Multiple"),
    # (2, "Respuesta"),
)


class BancoPreguntas(ModeloBase):
    enunciado = models.TextField(default='', blank=True, null=True, verbose_name='Enunciado Pregunta')
    ayuda = models.TextField(default='', blank=True, null=True, verbose_name='Retroalimentación General')
    tiporespuesta = models.PositiveIntegerField(verbose_name="Tipo Respuesta", blank=True, null=True,
                                                choices=TIPO_PREGUNTA)

    def total_respuestas(self):
        return self.bancopreguntasrespuestas_set.filter(status=True).order_by('pregunta__enunciado')

    def respuesta(self):
        return self.bancopreguntasrespuestas_set.filter(status=True, es_correcta=True).order_by('detalle')

    def noeliminar(self):
        return EvaluacionPregunta.objects.filter(status=True, pregunta=self).exists()

    def __str__(self):
        return "{}".format(self.enunciado)

    class Meta:
        verbose_name = "Banco Preguntas"
        verbose_name_plural = "Banco de Preguntas"


class BancoPreguntasRespuestas(ModeloBase):
    pregunta = models.ForeignKey(BancoPreguntas, on_delete=models.PROTECT, null=True, blank=True,
                                 verbose_name='Pregunta')
    detalle = models.TextField(default='', blank=True, null=True, verbose_name='Detalle')
    es_correcta = models.BooleanField(default=False, verbose_name='¿Si/No?')

    def str_es_correcta(self):
        return 'fa fa-check-circle text-success' if self.es_correcta else 'fa fa-times-circle text-error'

    def get_es_correcta(self):
        return 'SI' if self.es_correcta else 'NO'

    def __str__(self):
        return "{} {}".format(self.pregunta.enunciado, self.detalle)

    def save(self, *args, **kwargs):
        if self.detalle:
            self.detalle = self.detalle.upper().strip()
        super(BancoPreguntasRespuestas, self).save(*args, **kwargs)

    class Meta:
        verbose_name = "Banco Preguntas Respuesta"
        verbose_name_plural = "Banco Preguntas Respuestas"


CONFIGURACION_RESULTADOS = (
    (1, "MANTENER OCULTOS"),
    (2, "AL FINALIZAR EXAMEN"),
    (3, "15 MINUTOS DESPUÉS DE FINALIZAR"),
    (4, "30 MINUTOS DESPUÉS DE FINALIZAR"),
)


class Evaluacion(ModeloBase):
    nombre = models.CharField(max_length=1000, blank=True, null=True, verbose_name='Nombre')
    nombreurl = models.CharField(max_length=1000, blank=True, null=True, verbose_name='Url Evaluación')
    detalle = models.TextField(default='', blank=True, null=True, verbose_name='Detalle')
    password = models.CharField(max_length=1000, blank=True, null=True, verbose_name='Contraseña')
    verresultados = models.PositiveIntegerField(verbose_name="Mostrar Resultados", blank=True, null=True,
                                                choices=CONFIGURACION_RESULTADOS)
    notamin = models.FloatField(default=0, blank=True, null=True, verbose_name="Nota Minima")
    notamax = models.FloatField(default=0, blank=True, null=True, verbose_name="Nota Máxima")
    numpreguntas = models.IntegerField(default=0, blank=True, null=True, verbose_name="Número de Preguntas")
    numintentos = models.IntegerField(default=0, blank=True, null=True, verbose_name="Número de Intentos")
    minevaluacion = models.IntegerField(default=0, blank=True, null=True, verbose_name="Minutos Evaluación")
    publicar = models.BooleanField(default=True, verbose_name='¿Visible?')

    def valorpreguntas(self):
        return self.evaluacionpregunta_set.filter(status=True).aggregate(total=Coalesce(Sum(F('valor'), output_field=FloatField()), 0)).get('total')

    def excedeValorMinimo(self):
        if self.valorpreguntas() > self.notamax:
            return True
        else:
            return False

    def get_publicar(self):
        return 'fa fa-check-circle text-success' if self.publicar else 'fa fa-times-circle text-error'

    def save(self, force_insert=False, force_update=False, using=None, **kwargs):
        if self.nombre:
            self.nombre = self.nombre.upper()
        super(Evaluacion, self).save(force_insert, force_update, using)

    def __str__(self):
        return "{}".format(self.nombre)

    class Meta:
        verbose_name = "Evaluación"
        verbose_name_plural = "Evaluaciones"
        unique_together = ('nombreurl',)


class EvaluacionPregunta(ModeloBase):
    cab = models.ForeignKey(Evaluacion, on_delete=models.PROTECT, null=True, blank=True, verbose_name='Evaluación')
    pregunta = models.ForeignKey(BancoPreguntas, on_delete=models.PROTECT, null=True, blank=True, verbose_name='Pregunta')
    valor = models.FloatField(default=0, blank=True, null=True, verbose_name="Valor Nota")

    def traer1respuesta(self):
        return self.pregunta.bancopreguntasrespuestas_set.filter(status=True, es_correcta=True).first()

    def noeliminar(self):
        return PersonaEvaluacionPregunta.objects.filter(status=True, pregunta=self).exists()

    def metodo_evaluar(self):
        return self.pregunta.bancopreguntasrespuestas_set.filter(status=True)

    def __str__(self):
        return "{} {}".format(self.cab.nombre, self.pregunta.enunciado)

    class Meta:
        verbose_name = "Evaluacion Preguntas"
        verbose_name_plural = "Evaluaciones Preguntas"


ESTADO_EVALUACION = (
    (1, "Pendiente"),
    (2, "Finalizada"),
)


class PersonaEvaluacion(ModeloBase):
    evaluacion = models.ForeignKey(Evaluacion, on_delete=models.PROTECT, null=True, blank=True, verbose_name='Evaluación')
    persona = models.ForeignKey('sga.Persona', on_delete=models.PROTECT, null=True, blank=True, verbose_name='Persona')
    numintentos = models.IntegerField(default=0, blank=True, null=True, verbose_name="Número de Intentos")

    def ultimointento(self):
        return self.personaevaluacionintento_set.filter(status=True).order_by('numintento').last()

    def calificacionmaxima(self):
        return self.personaevaluacionintento_set.filter(status=True).order_by('calificacion').last()

    def existependiente(self):
        return self.personaevaluacionintento_set.filter(status=True, estado=1).first()

    def intentosrealizados(self):
        return self.personaevaluacionintento_set.filter(status=True, estado=2).count()

    def permiteintento(self):
        return (self.intentosrealizados() >= self.numintentos)

    def __str__(self):
        return "{}, {}".format(self.persona, self.evaluacion.nombre)

    class Meta:
        verbose_name = "Persona Evaluada"
        verbose_name_plural = "Personas Evaluadas"


class PersonaEvaluacionIntento(ModeloBase):
    personaevaluada = models.ForeignKey(PersonaEvaluacion, on_delete=models.PROTECT, null=True, blank=True, verbose_name='Evaluación')
    numintento = models.IntegerField(default=0, blank=True, null=True, verbose_name="Número de Intento")
    fechainicio = models.DateTimeField(blank=True, null=True, verbose_name=u'Fecha Inicio')
    fechaexpira = models.DateTimeField(blank=True, null=True, verbose_name=u'Fecha Expira Evaluación')
    fechafin = models.DateTimeField(blank=True, null=True, verbose_name=u'Fecha Fin')
    calificacion = models.FloatField(default=0, blank=True, null=True, verbose_name="Calificación")
    estado = models.PositiveIntegerField(verbose_name="Estado", blank=True, null=True, choices=ESTADO_EVALUACION)

    def tiempoempleado(self):
        if self.fechafin:
            return self.fechafin - self.fechainicio
        else:
            return 0

    def get_preguntas(self):
        return self.personaevaluacionpregunta_set.filter(status=True).order_by('pk')

    def tiposresultadospreguntass(self):
        try:
            correctas, incorrectas, sinresponder = 0, 0, 0
            for pre in self.get_preguntas():
                if pre.escorrecta() == 1:
                    correctas += 1
                elif pre.escorrecta() == 2:
                    incorrectas += 1
                elif pre.escorrecta() == 3:
                    sinresponder += 1
            return [correctas, incorrectas, sinresponder]
        except Exception as ex:
            return [0, 0, 0]


    def __str__(self):
        return "{}, Intento: {}".format(self.personaevaluada, self.numintento)

    class Meta:
        verbose_name = "Persona Evaluada Intento"
        verbose_name_plural = "Personas Evaluadas Intentos"


class PersonaEvaluacionPregunta(ModeloBase):
    cab = models.ForeignKey(PersonaEvaluacionIntento, on_delete=models.PROTECT, null=True, blank=True, verbose_name='Evaluación')
    pregunta = models.ForeignKey(EvaluacionPregunta, on_delete=models.PROTECT, null=True, blank=True, verbose_name='Pregunta')
    respondido = models.BooleanField(default=False, verbose_name='Respondido')
    valor = models.FloatField(default=0, blank=True, null=True, verbose_name="Calificación Respuesta")

    def str_respondido(self):
        return  'fa fa-check-circle text-success' if self.respondido else 'fa fa-times-circle text-error'

    def get_respuesta(self):
        return self.personaevaluacionrespuesta_set.filter(status=True).first()

    def escorrecta(self):
        #1 CORRECTA, 2 INCORRECTA, 3 NO RESPONDIO
        if self.get_respuesta():
            return 1 if self.get_respuesta().respuesta.es_correcta else 2
        else:
            return 3

    def escorrecta_style(self):
        style = ''
        if self.escorrecta() == 1:
            style = 'color: #ffffff; background-color: #08c767;!important;'
        elif self.escorrecta() == 2:
            style = 'color: #ffffff; background-color: #E74C3C;!important;'
        elif self.escorrecta() == 3:
            style = 'color: #ffffff; background-color: #E74C3C;!important;'
        return style


    def __str__(self):
        return "{}".format(self.pregunta.pregunta.enunciado)

    class Meta:
        verbose_name = "Persona Evaluaciones Pregunta"
        verbose_name_plural = "Persona Evaluaciones Preguntas"


class PersonaEvaluacionRespuesta(ModeloBase):
    pregunta = models.ForeignKey(PersonaEvaluacionPregunta, on_delete=models.PROTECT, null=True, blank=True,  verbose_name='Pregunta')
    respuesta = models.ForeignKey(BancoPreguntasRespuestas, on_delete=models.PROTECT, null=True, blank=True, verbose_name='Respuesta')

    def str_es_correcta(self):
        return 'fa fa-check-circle text-success' if self.respuesta.es_correcta else 'fa fa-times-circle text-error'

    def get_es_correcta(self):
        return 'SI' if self.respuesta.es_correcta else 'NO'

    def __str__(self):
        return "{} ({})".format(self.respuesta.detalle, self.respuesta.get_es_correcta())

    class Meta:
        verbose_name = "Persona Evaluaciones Respuesta"
        verbose_name_plural = "Persona Evaluaciones Respuestas"
