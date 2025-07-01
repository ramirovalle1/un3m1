from __future__ import unicode_literals

import json
from datetime import datetime
from django.db import models
from sga.funciones import ModeloBase
from django.core.cache import cache


class Periodo(ModeloBase):
    periodo = models.ForeignKey('sga.Periodo', related_name='+', verbose_name=u"Periodo", on_delete=models.CASCADE)
    nombre = models.CharField(default='', max_length=200, verbose_name=u'Nombre')
    inicio = models.DateTimeField(verbose_name=u'Fecha/hora inicio')
    fin = models.DateTimeField(verbose_name=u'Fecha/hora fin')
    activo = models.BooleanField(default=True, verbose_name=u'Activo')

    def __str__(self):
        return u'%s: %s a %s' % (self.nombre, self.inicio.strftime('%d-%m-%Y'), self.fin.strftime('%d-%m-%Y'))

    class Meta:
        verbose_name = u"Periodo admisión y nivelación"
        verbose_name_plural = u"Periodos admisión y nivelación"
        ordering = ['inicio']
        unique_together = ('periodo', )

    def tiene_datos_relacionados(self):
        eCronogramaPeriodos = CronogramaPeriodo.objects.values("id").filter(periodo=self)
        if eCronogramaPeriodos.exists():
            return True
        eAspirantes = Aspirante.objects.values("id").filter(periodo=self)
        if eAspirantes.exists():
            return True
        eTestVocacionalPeriodos = TestVocacionalPeriodo.objects.values("id").filter(periodo=self)
        if eTestVocacionalPeriodos.exists():
            return True
        return False

    def puede_eliminar(self):
        return self.tiene_datos_relacionados() == False

    def save(self, *args, **kwargs):
        super(Periodo, self).save(*args, **kwargs)


TYPE_CRONOGRAMA_PERIODO = (
    (1, 'REGISTRO'),
    (2, 'TEST VOCACIONAL'),
)


class CronogramaPeriodo(ModeloBase):
    periodo = models.ForeignKey(Periodo, verbose_name=u"Periodo", on_delete=models.CASCADE)
    tipo = models.IntegerField(choices=TYPE_CRONOGRAMA_PERIODO, default=1, verbose_name=u"Tipo de cronograma")
    nombre = models.CharField(default='', max_length=200, verbose_name=u'Nombre')
    inicio = models.DateTimeField(verbose_name=u'Fecha/hora inicio')
    fin = models.DateTimeField(verbose_name=u'Fecha/hora fin')
    activo = models.BooleanField(default=True, verbose_name=u'Activo')

    def __str__(self):
        return u'%s - %s: %s a %s' % (
        self.periodo.nombre, self.nombre, self.inicio.strftime('%d-%m-%Y'), self.fin.strftime('%d-%m-%Y'))

    class Meta:
        verbose_name = u"Periodo admisión y nivelación"
        verbose_name_plural = u"Periodos admisión y nivelación"
        ordering = ['periodo', 'tipo', 'inicio']
        unique_together = ('periodo', 'tipo')

    def es_registro(self):
        return self.tipo == 1

    def save(self, *args, **kwargs):
        super(CronogramaPeriodo, self).save(*args, **kwargs)


class Inscripcion(ModeloBase):
    persona = models.ForeignKey('sga.Persona', related_name='+', verbose_name=u"Persona", on_delete=models.CASCADE)
    fecha = models.DateField(verbose_name=u'Fecha de inscripción')
    sede = models.ForeignKey('sga.Sede', related_name='+', default=1, verbose_name=u'Sede', on_delete=models.CASCADE)
    activo = models.BooleanField(default=False, verbose_name=u"Activo")

    def __str__(self):
        return f"{self.persona}"

    class Meta:
        verbose_name = u"Inscripción de admisión y nivelación"
        verbose_name_plural = u"Inscripciones de admisión y nivelación"
        ordering = ['persona']
        unique_together = ('persona',)

    def save(self, *args, **kwargs):
        super(Inscripcion, self).save(*args, **kwargs)


class Aspirante(ModeloBase):
    inscripcion = models.ForeignKey(Inscripcion, verbose_name=u"Inscripcion", on_delete=models.CASCADE)
    periodo = models.ForeignKey(Periodo, verbose_name=u"Periodo", on_delete=models.CASCADE)
    confirmodatos = models.BooleanField(default=False, verbose_name=u"Confirmo datos")
    fechahoraconfirmaciondatos = models.DateTimeField(blank=True, null=True, verbose_name=u"Fecha y hora confirmación de datos")
    activo = models.BooleanField(default=False, verbose_name=u"Activo")

    def __str__(self):
        return f"{self.inscripcion} - {self.periodo}"

    class Meta:
        verbose_name = u"Aspirante de admisión y nivelación"
        verbose_name_plural = u"Aspirantes de admisión y nivelación"
        ordering = ['inscripcion', 'periodo']
        unique_together = ('inscripcion', 'periodo',)

    def url_certificado_registro_datos(self):
        eArchivoProcesoAspirantes = ArchivoProcesoAspirante.objects.filter(aspirante=self, proceso=1, activo=True)
        if eArchivoProcesoAspirantes.values("id").exists():
            eArchivoProcesoAspirante = eArchivoProcesoAspirantes.last()
            if eArchivoProcesoAspirante.url:
                return eArchivoProcesoAspirante.url
        return None

    def tiene_test_vocacional(self):
        return AspiranteTestVocacional.objects.values("id").filter(aspirante=self).exists()

    def mi_test_vocacional(self):
        if not self.tiene_test_vocacional():
            return None
        return AspiranteTestVocacional.objects.filter(aspirante=self).first()

    def mis_respuesta_test_vocacional(self):
        eAspiranteTestVocacional = self.mi_test_vocacional()
        if eAspiranteTestVocacional is None:
            return AspiranteTestVocacionalRespuesta.objects.none()
        return eAspiranteTestVocacional.mis_respuestas()

    def url_certificado_test_vocacional(self):
        eArchivoProcesoAspirantes = ArchivoProcesoAspirante.objects.filter(aspirante=self, proceso=2, activo=True)
        if eArchivoProcesoAspirantes.values("id").exists():
            eArchivoProcesoAspirante = eArchivoProcesoAspirantes.last()
            if eArchivoProcesoAspirante.url:
                return eArchivoProcesoAspirante.url
        return None

    def delete_cache(self):
        from sga.templatetags.sga_extras import encrypt
        if self.id:
            enCache = cache.get(f"admision__aspirante__{encrypt(self.id)}")
            if enCache:
                cache.delete(f"admision__aspirante__{encrypt(self.id)}")

    def delete(self, *args, **kwargs):
        self.delete_cache()
        super(Aspirante, self).delete(*args, **kwargs)

    def save(self, *args, **kwargs):
        self.delete_cache()
        super(Aspirante, self).save(*args, **kwargs)


APPLICANT_PROCESS = (
    (0, "Ninguno"),
    (1, "Registro de datos"),
    (2, "Test Vocacional"),
)


class ArchivoProcesoAspirante(ModeloBase):
    aspirante = models.ForeignKey(Aspirante, verbose_name=u'Aspirante', on_delete=models.CASCADE)
    proceso = models.IntegerField(choices=APPLICANT_PROCESS, default=0, verbose_name=u'Proceso')
    url = models.URLField(verbose_name=u"URL de archivo", blank=True, null=True)
    activo = models.BooleanField(default=True, verbose_name=u"Activo")

    def __str__(self):
        return f"{self.aspirante} - {self.get_proceso_display()}"

    class Meta:
        verbose_name = u"Archivo del proceso del aspirante de admisión y nivelación"
        verbose_name_plural = u"Archivos del proceso del aspirante de admisión y nivelación"
        ordering = ['aspirante', 'proceso']

    def save(self, *args, **kwargs):
        super(ArchivoProcesoAspirante, self).save(*args, **kwargs)


TYPE_VERACITY_SECURITY = (
    (1, "Registro de datos"),
)


class VeracitySecurityCode(ModeloBase):
    aspirante = models.ForeignKey(Aspirante, verbose_name=u'Aspirante', on_delete=models.CASCADE)
    type = models.IntegerField(choices=TYPE_VERACITY_SECURITY, default=1, verbose_name=u'Tipo')
    date_expires = models.DateTimeField(verbose_name=u'Fecha/Hora de expiración', db_index=True)
    codigo = models.CharField(max_length=10, verbose_name=u'Código', db_index=True)
    isActive = models.BooleanField(default=True, verbose_name=u"Activo?")
    wasValidated = models.BooleanField(default=False, verbose_name=u"Fue validado?")

    def __str__(self):
        return f"{self.aspirante.__str__()}"

    class Meta:
        verbose_name = u"Código de seguridad de veracidad"
        verbose_name_plural = u"Códigos de seguridad de veracidad"
        ordering = ('aspirante', 'type', 'date_expires',)

    def isValidoCodigo(self, codigo):
        if self.isActive:
            return self.isValidoTime() and self.codigo == codigo
        return False

    def isValidoTime(self):
        return self.date_expires >= datetime.now()

    def inactiveToken(self):
        self.isActive = False
        self.save()

    def delete(self, *args, **kwargs):
        super(VeracitySecurityCode, self).delete(*args, **kwargs)

    def save(self, *args, **kwargs):
        super(VeracitySecurityCode, self).save(*args, **kwargs)


class TestVocacional(ModeloBase):
    nombre = models.CharField(max_length=500, verbose_name=u'Nombre')
    descripcion = models.TextField(default='', verbose_name=u'Descripción')
    activo = models.BooleanField(default=True, verbose_name=u'Activo?')

    def __str__(self):
        return u'%s' % self.nombre

    class Meta:
        verbose_name = u"Test vocacional"
        verbose_name_plural = u"Tests vocacionales"
        ordering = ['nombre']
        unique_together = ('nombre',)

    def tiene_datos_relacionados(self):
        eTestVocacionalOpciones = TestVocacionalOpcion.objects.values("id").filter(test=self)
        if eTestVocacionalOpciones.exists():
            return True
        eTestVocacionalPreguntas = TestVocacionalPregunta.objects.values("id").filter(test=self)
        if eTestVocacionalPreguntas.exists():
            return True
        eTestVocacionalPeriodos = TestVocacionalPeriodo.objects.values("id").filter(test=self)
        if eTestVocacionalPeriodos.exists():
            return True
        eAspiranteTestVocacionales = AspiranteTestVocacional.objects.values("id").filter(test=self)
        if eAspiranteTestVocacionales.exists():
            return True
        return False

    def puede_eliminar(self):
        return self.tiene_datos_relacionados() == False

    def puede_editar(self):
        return AspiranteTestVocacional.objects.values("id").filter(test=self).exists() == False

    def list_opciones(self):
        return TestVocacionalOpcion.objects.filter(test=self)

    def list_preguntas(self):
        return TestVocacionalPregunta.objects.filter(test=self)

    def save(self, *args, **kwargs):
        if self.nombre:
            self.nombre = self.nombre.strip()
        if self.descripcion:
            self.descripcion = self.descripcion.strip()
        super(TestVocacional, self).save(*args, **kwargs)


class TestVocacionalOpcion(ModeloBase):
    test = models.ForeignKey(TestVocacional, verbose_name=u"Test", on_delete=models.CASCADE)
    literal = models.CharField(default='', max_length=10, verbose_name=u'Literal')
    descripcion = models.CharField(default='', max_length=150, verbose_name=u'Descripción')

    def __str__(self):
        return u'(%s) - %s' % (self.literal, self.descripcion)

    class Meta:
        verbose_name = u"Opción del test vocacional"
        verbose_name_plural = u"Opciones del test vocacional"
        ordering = ['test', 'literal']

    def tiene_datos_relacionados(self):
        eTestVocacionalAlternativas = TestVocacionalAlternativa.objects.values("id").filter(opcion=self)
        if eTestVocacionalAlternativas.exists():
            return True
        eAspiranteTestVocacionalRespuestas = AspiranteTestVocacionalRespuesta.objects.values("id").filter(opcion=self)
        if eAspiranteTestVocacionalRespuestas.exists():
            return True
        return False

    def puede_eliminar(self):
        return self.tiene_datos_relacionados() == False

    def puede_editar(self):
        return AspiranteTestVocacionalRespuesta.objects.values("id").filter(opcion=self).exists() == False

    def save(self, *args, **kwargs):
        if self.literal:
            self.literal = self.literal.strip()
        if self.descripcion:
            self.descripcion = self.descripcion.strip()
        super(TestVocacionalOpcion, self).save(*args, **kwargs)


class TestVocacionalPregunta(ModeloBase):
    test = models.ForeignKey(TestVocacional, verbose_name=u"Test", on_delete=models.CASCADE)
    orden = models.IntegerField(default=0, verbose_name=u'Orden')
    descripcion = models.TextField(default='', verbose_name=u'Descripción')
    activo = models.BooleanField(default=True, verbose_name=u'Activo?')
    validar = models.BooleanField(default=True, verbose_name=u'Validar?')

    def __str__(self):
        return u'(%s) - %s' % (self.orden, self.descripcion)

    class Meta:
        verbose_name = u"Rúbrica Entrevista"
        verbose_name_plural = u"Rúbricas Entrevistas"
        ordering = ['orden']
        unique_together = ('test', 'descripcion',)

    def tiene_datos_relacionados(self):
        eTestVocacionalAlternativas = TestVocacionalAlternativa.objects.values("id").filter(pregunta=self)
        if eTestVocacionalAlternativas.exists():
            return True
        eAspiranteTestVocacionalRespuestas = AspiranteTestVocacionalRespuesta.objects.values("id").filter(pregunta=self)
        if eAspiranteTestVocacionalRespuestas.exists():
            return True
        return False

    def puede_eliminar(self):
        return self.tiene_datos_relacionados() == False

    def puede_editar(self):
        return AspiranteTestVocacionalRespuesta.objects.values("id").filter(pregunta=self).exists() == False

    def list_alternativas(self):
        return TestVocacionalAlternativa.objects.filter(pregunta=self)

    def save(self, *args, **kwargs):
        if self.descripcion:
            self.descripcion = self.descripcion.strip()
        super(TestVocacionalPregunta, self).save(*args, **kwargs)


class TestVocacionalAlternativa(ModeloBase):
    pregunta = models.ForeignKey(TestVocacionalPregunta, verbose_name=u"Pregunta", on_delete=models.CASCADE)
    orden = models.IntegerField(default=0, verbose_name=u'Orden')
    opcion = models.ForeignKey(TestVocacionalOpcion, verbose_name=u"Opcion", on_delete=models.CASCADE)
    valor = models.FloatField(default=0, verbose_name=u'Valor')

    def __str__(self):
        return u'%s - (%s):%s' % (self.orden, self.opcion.literal, self.opcion.descripcion)

    class Meta:
        verbose_name = u"Alternativa de pregunta del test"
        verbose_name_plural = u"Alternativas de pregunta del test"
        ordering = ['pregunta', 'orden']
        unique_together = ('pregunta', 'opcion',)

    def save(self, *args, **kwargs):
        super(TestVocacionalAlternativa, self).save(*args, **kwargs)


class TestVocacionalPeriodo(ModeloBase):
    test = models.ForeignKey(TestVocacional, verbose_name=u"Test", on_delete=models.CASCADE)
    periodo = models.ForeignKey(Periodo, verbose_name=u"Periodo", on_delete=models.CASCADE)
    activo = models.BooleanField(default=True, verbose_name=u'Activo?')

    def __str__(self):
        return u'%s - %s' % (self.test.nombre, self.periodo.nombre)

    class Meta:
        verbose_name = u"Test vocacional periodo"
        verbose_name_plural = u"Tests vocacionales en periodos"
        ordering = ['test', 'periodo']
        unique_together = ('test', 'periodo')

    def save(self, *args, **kwargs):
        super(TestVocacionalPeriodo, self).save(*args, **kwargs)


class AspiranteTestVocacional(ModeloBase):
    aspirante = models.ForeignKey(Aspirante, verbose_name=u"Aspirante", on_delete=models.CASCADE)
    test = models.ForeignKey(TestVocacional, verbose_name=u"Test", on_delete=models.CASCADE)

    def __str__(self):
        return u'%s - %s' % (self.aspirante.inscripcion.persona, self.test.nombre)

    class Meta:
        verbose_name = u"Test vocacional del aspirante"
        verbose_name_plural = u"Test vocacional de los aspirantes"
        ordering = ['aspirante', 'test']
        unique_together = ('aspirante', 'test')

    def tiene_respuestas(self):
        return AspiranteTestVocacionalRespuesta.objects.values("id").filter(aspirantetest=self).exists()

    def mis_respuestas(self):
        if not self.tiene_respuestas():
            return AspiranteTestVocacionalRespuesta.objects.none()
        return AspiranteTestVocacionalRespuesta.objects.filter(aspirantetest=self)

    def delete_cache(self):
        from sga.templatetags.sga_extras import encrypt
        if self.id:
            enCache = cache.get(f"admision__aspirante_test__{encrypt(self.aspirante_id)}")
            if enCache:
                cache.delete(f"admision__aspirante_test__{encrypt(self.aspirante_id)}")

    def delete(self, *args, **kwargs):
        self.delete_cache()
        super(AspiranteTestVocacional, self).delete(*args, **kwargs)

    def save(self, *args, **kwargs):
        self.delete_cache()
        super(AspiranteTestVocacional, self).save(*args, **kwargs)


class AspiranteTestVocacionalRespuesta(ModeloBase):
    aspirantetest = models.ForeignKey(AspiranteTestVocacional, verbose_name=u"Aspirante", on_delete=models.CASCADE)
    pregunta = models.ForeignKey(TestVocacionalPregunta, verbose_name=u"Pregunta", on_delete=models.CASCADE)
    opcion = models.ForeignKey(TestVocacionalOpcion, verbose_name=u"Opcion", on_delete=models.CASCADE)
    valor = models.FloatField(default=0, verbose_name=u'Valor')

    def __str__(self):
        return u'%s -> P: %s - R:%s' % (self.aspirante().inscripcion.persona, self.pregunta, self.opcion)

    class Meta:
        verbose_name = u"Respuesta del test vocacional del aspirante"
        verbose_name_plural = u"Respuestas del test vocacional del aspirante"
        ordering = ['aspirantetest', 'pregunta']
        unique_together = ('aspirantetest', 'pregunta')

    def aspirante(self):
        return self.aspirantetest.aspirante

    def save(self, *args, **kwargs):
        super(AspiranteTestVocacionalRespuesta, self).save(*args, **kwargs)


class Rubrica(ModeloBase):
    nombre = models.TextField(verbose_name=u"Nombre Rubrica", max_length=500)

    def __str__(self):
        return u'%s' % self.nombre

    class Meta:
        verbose_name = u"Rúbrica Entrevista"
        verbose_name_plural = u"Rúbricas Entrevistas"
        ordering = ['nombre']

    def save(self, *args, **kwargs):
        self.nombre = self.nombre.upper().strip()
        super(Rubrica, self).save(*args, **kwargs)


class RubricaCriterio(ModeloBase):
    orden = models.PositiveIntegerField()
    descripcion = models.TextField(verbose_name=u"Descripción del Criterio", max_length=500)

    def __str__(self):
        return u'%s - %s' % (self.descripcion, self.orden)

    class Meta:
        verbose_name = u"Rúbrica Criterio"
        verbose_name_plural = u"Rúbrica Criterios"
        ordering = ['orden']

    def save(self, *args, **kwargs):
        self.descripcion = self.descripcion.upper().strip()
        super(RubricaCriterio, self).save(*args, **kwargs)


class RubricaNivel(ModeloBase):
    calificacion = models.FloatField(verbose_name=u"Calificación")
    descripcion = models.TextField(verbose_name=u"Descripción del Nivel", max_length=500)

    def __str__(self):
        return u'Calificacion: %s - Descripcion: %s' % (self.calificacion, self.descripcion)

    class Meta:
        verbose_name = u"Rúbrica Nivel"
        verbose_name_plural = u"Rúbrica Niveles"

    def save(self, *args, **kwargs):
        self.descripcion = self.descripcion.upper().strip()
        super(RubricaNivel, self).save(*args, **kwargs)


class RubricaRelleno(ModeloBase):
    rubrica = models.ForeignKey(Rubrica, verbose_name=u"Rúbrica", on_delete=models.PROTECT)
    criterio = models.ForeignKey(RubricaCriterio, verbose_name=u"Criterio", on_delete=models.PROTECT)
    niveles = models.ManyToManyField(RubricaNivel, verbose_name=u"Niveles")

    def __str__(self):
        return u'Rubrica: %s - Criterio: %s - Niveles: [%s]' % (
        self.rubrica, self.criterio, ", ".join(list(self.niveles.all().values_list('descripcion', flat=True))))

    class Meta:
        verbose_name = u"Rúbrica Detalle"
        verbose_name_plural = u"Rúbrica Detalle"


class AreaPreguntaEntrevista(ModeloBase):
    descripcion = models.TextField(verbose_name=u"Descripción del Área", max_length=500)

    def __str__(self):
        return u'Descripcion: %s' % (self.descripcion)

    class Meta:
        verbose_name = u"Area Pregunta Entrevista"
        verbose_name_plural = u"Area Pregunta Entrevistas"

    def save(self, *args, **kwargs):
        self.descripcion = self.descripcion.upper().strip()
        super(AreaPreguntaEntrevista, self).save(*args, **kwargs)


class PreguntaEntrevista(ModeloBase):
    orden = models.PositiveIntegerField()
    area = models.ForeignKey(AreaPreguntaEntrevista, verbose_name=u"Área", on_delete=models.PROTECT)
    carrera = models.ForeignKey('sga.Carrera', verbose_name=u"Carrera", on_delete=models.PROTECT, null=True, blank=True)
    descripcion = models.TextField(verbose_name=u"Descripción de la pregunta", max_length=500)
    periodo = models.ForeignKey('sga.Periodo', verbose_name=u"Periodo", on_delete=models.PROTECT)  # periodo sesion

    def __str__(self):
        return u'Area: %s - Descripcion: %s' % (self.area, self.descripcion)

    class Meta:
        verbose_name = u"Pregunta Entrevista"
        verbose_name_plural = u"Pregunta Entrevistas"

    def save(self, *args, **kwargs):
        self.descripcion = self.descripcion.upper().strip()
        super(PreguntaEntrevista, self).save(*args, **kwargs)


class MatriculaProfesor(ModeloBase):
    matricula = models.ForeignKey('sga.Matricula', verbose_name=u"Matrícula", on_delete=models.PROTECT)
    profesor = models.ForeignKey('sga.Profesor', verbose_name=u"Profesor", on_delete=models.PROTECT)

    def __str__(self):
        return u'Inscripcion: %s - Profesor: %s' % (self.matricula.inscripcion, self.profesor)

    class Meta:
        verbose_name = u"Matricula Profesor"
        verbose_name_plural = u"Matricula Profesores"


class CalificacionEntrevista(ModeloBase):
    pregunta = models.ForeignKey(PreguntaEntrevista, verbose_name=u"Área", on_delete=models.PROTECT)
    matricula_profesor = models.ForeignKey(MatriculaProfesor, verbose_name=u"Área", on_delete=models.PROTECT)
    calificacion = models.FloatField(verbose_name=u"Calificación")
    observacion = models.TextField(verbose_name=u"Observación", max_length=10000, blank=True, null=True)

    def __str__(self):
        return u'%s - Calificación: %s' % (self.matricula_profesor, self.calificacion)

    class Meta:
        verbose_name = u"Calificación Entrevista"
        verbose_name_plural = u"Calificaciones Entrevistas"


class Calificacion(ModeloBase):
    materiaasignada = models.ForeignKey('sga.MateriaAsignada', null=True, blank=True, on_delete=models.CASCADE)
    detallemodeloevaluativo = models.ForeignKey('sga.DetalleModeloEvaluativo', null=True, blank=True,
                                                on_delete=models.CASCADE)
    calificacionmoodle = models.DecimalField(default=0, blank=True, null=True, max_digits=30, decimal_places=2,
                                             verbose_name=u"Calificaciòn")

    def __str__(self):
        return u'%s - %s %s' % (self.materiaasignada, self.detallemodeloevaluativo, self.calificacionmoodle)

    class Meta:
        verbose_name = u"Moodle Calificación"
        verbose_name_plural = u"Moodle Calificaciones"
        # ordering = ['username']

    def save(self, *args, **kwargs):
        super(Calificacion, self).save(*args, **kwargs)


class Actividad(ModeloBase):
    calificacion = models.ForeignKey(Calificacion, null=True, blank=True, on_delete=models.CASCADE)
    nombreactividad = models.CharField(default='', max_length=100, verbose_name=u'Nombre actividad', null=True,
                                       blank=True)
    idactividadmoodle = models.IntegerField(default=0, blank=True, null=True, verbose_name=u'Id Actividad Moodle')
    calificacionmoodle = models.DecimalField(default=0, blank=True, null=True, max_digits=30, decimal_places=2,
                                             verbose_name=u"Calificaciòn")
    numerointentos = models.IntegerField(default=0, blank=True, null=True, verbose_name=u'Número Intento')

    def __str__(self):
        return u'%s - %s - %s - %s' % (
        self.nombreactividad, self.idactividadmoodle, self.numerointentos, self.calificacionmoodle)

    class Meta:
        verbose_name = u"Moodle Actividad"
        verbose_name_plural = u"Moodle Actividades"
        # ordering = ['username']

    def save(self, *args, **kwargs):
        super(Actividad, self).save(*args, **kwargs)
