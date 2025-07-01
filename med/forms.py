# -*- coding: latin-1 -*-
from datetime import datetime
from django import forms
from django.contrib.auth.models import Group
from django.db.models import Q
from django.forms.widgets import DateTimeInput, CheckboxInput, TimeInput, FileInput
from django.utils.safestring import mark_safe

from core.custom_forms import FormModeloBase
from med.models import PersonaEducacion, PersonaProfesion, IndicadorSobrepeso, \
    TIPOATENCIONMEDICA_CHOICES, TIPOATENCIONODONTOLOGICA_CHOICES, CAUSAPROFILAXIS_CHOICES, TIPOINVENTARIOMEDICO_CHOICES, \
    TIPOMOVIMIENTOMEDICAMENTO_CHOICES, TIPOCONSULTA_TERAPIA, Enfermedad, Parentesco, Vacuna, GRUPO_SANGRE_CHOICES, \
    Alergia, Cirugia, LugarAnatomico, FLUJO_MENSTRUAL, MetodoAnticonceptivo, TABAQUISMO, ALCOHOLISMO, Droga, \
    ALIMENTACCION_CANTIDAD, ALIMENTACCION_CALIDAD, VIVIENDA, ZONA, TIPO_CONSTRUCCION, VENTILACION, AGUA_POTABLE, LUZ, \
    TRANSPORTE, POSTURA, GRADO_ACTIVIDAD, ESTADO_MENTAL, FACIES, BIOTIPO, TALLA, ESTADO_NUTRICIONAL, Lesiones, \
    MOVIMIENTO, CRANEO, CRANEO_TAMANIO, TIPO_VEHICULO, TIEMPO, TipoActividad, UBICACION, FRECUENCIA, ESTADO_CARACTER, \
    TIPO_PACIENTE, FACTOR_RH_CHOICES, Medicina, CatalogoEnfermedad, TIPO_DROGA, TIPO_ALERGIA, ACTIVIDAD_FISICA, \
    FRECUENCIACONSUMO, Comidas, TipoServicioBienestar, ALTERNATIVAS, ALTERNATIVASVARIAS, AccionConsulta, \
    ESTADO_REVISION_EXLAB, Antropometria

TIPO_PACIENTE, FACTOR_RH_CHOICES, Medicina, CatalogoEnfermedad, ACTIVIDAD_FISICA, Comidas, FRECUENCIACONSUMO, TIPO_DROGA, TipoServicioBienestar
from sga.forms import campo_modolectura, ExtFileField

from sga.models import PersonaEstadoCivil, Raza, Coordinacion, Nivel, Carrera, NivelMalla, Paralelo, Persona
from sga.models import PersonaEstadoCivil, Raza, Idioma
from unidecode import unidecode

def deshabilitar_campo(form, campo):
    form.fields[campo].widget.attrs['readonly'] = True
    form.fields[campo].widget.attrs['disabled'] = True

def campo_solo_lectura(form, campo):
    form.fields[campo].widget.attrs['readonly'] = True

class PersonaExtensionForm(forms.Form):
    direccion = forms.CharField(label=u"Calle principal", max_length=100, required=False, widget=forms.TextInput(attrs={'class': 'imp-75'}))
    direccion2 = forms.CharField(label=u"Calle secundaria", max_length=100, required=False, widget=forms.TextInput(attrs={'class': 'imp-75'}))
    horanacimiento = forms.TimeField(label=u"Hora de Nacimiento", required=False, initial=str(datetime.now().time()), input_formats=['%H:%M'], widget=TimeInput(format='%H:%M', attrs={'class': 'selectorhora', 'formwidth': '50%'}))
    edadaparenta = forms.IntegerField(label=u'Edad que Aparenta', required=False, widget=forms.TextInput(attrs={'class': 'imp-number'}))
    estadocivil = forms.ModelChoiceField(label=u'Estado civil', queryset=PersonaEstadoCivil.objects, required=False, widget=forms.Select(attrs={'class': 'imp-50'}))
    tieneconyuge = forms.BooleanField(label=u"Vive con su cónyuge", required=False)
    hijos = forms.IntegerField(label=u'No. hijos', required=False, widget=forms.TextInput(attrs={'class': 'imp-number'}))
    contactoemergencia = forms.CharField(label=u'Contacto de emergencia', max_length=200, required=False, widget=forms.TextInput(attrs={'class': 'imp-75'}))
    telefonoemergencia = forms.CharField(label=u'Telefono de emergencia', max_length=50, required=False, widget=forms.TextInput(attrs={'class': 'imp-50'}))
    telefonos = forms.CharField(label=u"Teléfonos de familiares", max_length=100, required=False, widget=forms.TextInput(attrs={'class': 'imp-50'}))
    tienelicencia = forms.BooleanField(label=u'Licencia de conducción', required=False)
    tipolicencia = forms.CharField(label=u'Tipo de licencia', max_length=50, required=False, widget=forms.TextInput(attrs={'class': 'imp-number'}))
    gestacion = forms.BooleanField(label=u'Estado de gestación', required= False)


class PersonaFamiliaForm(forms.Form):
    padre = forms.CharField(label=u'Nombre completo', max_length=100, required=False, widget=forms.TextInput(attrs={'class': 'imp-75', 'separator': 'Datos del padre'}))
    edadpadre = forms.IntegerField(label=u'Edad', required=False, widget=forms.TextInput(attrs={'class': 'imp-number'}))
    estadopadre = forms.ModelChoiceField(label=u'Estado Civil', queryset=PersonaEstadoCivil.objects, required=False, widget=forms.Select(attrs={'class': 'imp-50'}))
    telefpadre = forms.CharField(label=u'Teléfono', max_length=50, required=False)
    educacionpadre = forms.ModelChoiceField(label=u'Educación', queryset=PersonaEducacion.objects, required=False, widget=forms.Select(attrs={'class': 'imp-50'}))
    profesionpadre = forms.ModelChoiceField(label=u'Profesión', queryset=PersonaProfesion.objects, required=False, widget=forms.Select(attrs={'class': 'imp-50'}))
    trabajopadre = forms.CharField(label=u'Trabajo', max_length=200, required=False)
    madre = forms.CharField(label=u'Nombre completo', max_length=100, required=False, widget=forms.TextInput(attrs={'class': 'imp-75', 'separator': 'Datos de la madre'}))
    edadmadre = forms.IntegerField(label=u'Edad', required=False, widget=forms.TextInput(attrs={'class': 'imp-number'}))
    estadomadre = forms.ModelChoiceField(label=u'Estado civil', queryset=PersonaEstadoCivil.objects, required=False, widget=forms.Select(attrs={'class': 'imp-50'}))
    telefmadre = forms.CharField(label=u'Teléfono', max_length=50, required=False)
    educacionmadre = forms.ModelChoiceField(label=u'Educación', queryset=PersonaEducacion.objects, required=False, widget=forms.Select(attrs={'class': 'imp-50'}))
    profesionmadre = forms.ModelChoiceField(label=u'Profesión', queryset=PersonaProfesion.objects, required=False, widget=forms.Select(attrs={'class': 'imp-50'}))
    trabajomadre = forms.CharField(label=u'Trabajo', max_length=200, required=False)
    conyuge = forms.CharField(label=u'Nombre completo', max_length=100, required=False, widget=forms.TextInput(attrs={'class': 'imp-75', 'separator': 'Datos del conyuge'}))
    edadconyuge = forms.IntegerField(label=u'Edad', required=False, widget=forms.TextInput(attrs={'class': 'imp-number'}))
    estadoconyuge = forms.ModelChoiceField(label=u'Estado civil', queryset=PersonaEstadoCivil.objects, required=False, widget=forms.Select(attrs={'class': 'imp-50'}))
    telefconyuge = forms.CharField(label=u'Teléfono', max_length=50, required=False)
    educacionconyuge = forms.ModelChoiceField(label=u'Educación', queryset=PersonaEducacion.objects, required=False, widget=forms.Select(attrs={'class': 'imp-50'}))
    profesionconyuge = forms.ModelChoiceField(label=u'Profesión', queryset=PersonaProfesion.objects, required=False, widget=forms.Select(attrs={'class': 'imp-50'}))
    trabajoconyuge = forms.CharField(label=u'Trabajo', max_length=200, required=False)


class VacunaForm(forms.Form):
    descripcionvacuna = forms.CharField(label=u'Descripción', max_length=300, required=False)


class EnfermedadForm(forms.Form):
    descripcionenfermedad = forms.CharField(label=u'Descripción', max_length=300, required=False)


class AlergiaForm(forms.Form):
    descripcionalergia = forms.CharField(label=u'Descripción', max_length=300, required=False)


class Alergia2Form(forms.Form):
    tipoalergia = forms.ChoiceField(label=u'Tipo', choices=TIPO_ALERGIA, required=False, widget=forms.Select(attrs={'width': '100%'}))
    descripcionalergia = forms.CharField(label=u'Descripción', max_length=300, required=False)

class FechaFichaMedicaForm(forms.Form):
    fechaficha = forms.DateField(label=u"Fecha ficha", input_formats=['%d-%m-%Y'], widget=DateTimeInput(format='%d-%m-%Y', attrs={'class': 'selectorfecha'}), required=False)


class RevisarRexmedForm(forms.Form):
    estado = forms.ChoiceField(label=u'Estado', choices=ESTADO_REVISION_EXLAB, required=False, widget=forms.Select(attrs={'class': 'imp-100'}))
    observacion = forms.CharField(label=u'Observaciones', widget=forms.Textarea(attrs={'rows': '4'}), required=False)

    def cargarestado(self):
        estados = [('', '--Seleccione--'), (2, u'VALIDADO'), (3, u'RECHAZADO')]
        self.fields['estado'].choices = estados


class MedicinaForm(forms.Form):
    descripcionmedicina = forms.CharField(label=u'Descripción', max_length=300, required=False)


class CirugiaForm(forms.Form):
    descripcioncirugia = forms.CharField(label=u'Descripción', max_length=300, required=False)


class LugarAnatomicoForm(forms.Form):
    descripcionlugaranatomico = forms.CharField(label=u'Descripción', max_length=300, required=False)


class DrogaForm(forms.Form):
    tipodroga = forms.ChoiceField(label=u'Tipo', choices=TIPO_DROGA, required=False, widget=forms.Select(attrs={'class': 'imp-1500'}))
    descripciondroga = forms.CharField(label=u'Descripción', max_length=300, required=False)


class MetodoAnticonceptivoForm(forms.Form):
    descripcionmetodo = forms.CharField(label=u'Descripción', max_length=300, required=False)


class LesionesForm(forms.Form):
    descripcionlesion = forms.CharField(label=u'Descripción', max_length=300, required=False)


class AccionConsultaForm(forms.Form):
    descripcionaccion = forms.CharField(label=u'Descripción', max_length=150, required=False)


class SubirDocumentoExamenLabForm(forms.Form):
    archivoexamenlaboratorio = ExtFileField(label=u'Documento Resultado', required=False, help_text=u'Tamaño Maximo permitido 4Mb, en formato pdf', ext_whitelist=(".pdf",), max_upload_size=4194304, widget=FileInput({'accept': 'application/pdf'}))


class PatologicoPersonalForm(forms.Form):
    nacio = forms.BooleanField(label=u'Nació a término?', required=False)
    partonormal = forms.BooleanField(label=u'Parto Normal?', required=False, widget=CheckboxInput(attrs={'formwidth': '30%'}))
    partocesarea = forms.BooleanField(label=u'Cesárea?', required=False, widget=CheckboxInput(attrs={'formwidth': '30%'}))
    partocomplicacion = forms.CharField(label=u'Complicaciones en Parto', max_length=200, required=False)
    lactanciamaterna = forms.BooleanField(label=u'Lactancia Materna?', required=False, widget=CheckboxInput(attrs={'formwidth': '30%'}))
    lactanciaartificial = forms.BooleanField(label=u'Lactancia Artificial?', required=False, widget=CheckboxInput(attrs={'formwidth': '30%'}))
    ablactacion = forms.CharField(label=u'Ablactación / Meses', max_length=20, required=False, widget=forms.TextInput(attrs={'class': 'imp-20','formwidth': '30%'}))
    vacuna = forms.BooleanField(label=u'Vacunas?', required=False)
    vacunas = forms.ModelMultipleChoiceField(label=mark_safe(u'<a href="javascript:;" class="btn btn-generar btn-success tu" title="Agregar vacuna" id="add_vacuna"><i class="fa fa-plus-square"></i></a>&nbsp;Vacunas'), queryset=Vacuna.objects.all(), required=False)
    enfermedadinfancia = forms.ModelMultipleChoiceField(label=mark_safe(u'<a href="javascript:;" class="btn btn-generar btn-success tu" title="Agregar enfermedad infantil" id="add_enfermedad" idte="1" dte="Infantil"><i class="fa fa-plus-square"></i></a>&nbsp;Enfermedades de la Infancia'), queryset=Enfermedad.objects.filter(tipo=1), required=False)
    letes = forms.BooleanField(label=u'Usa lentes?', required=False)
    enfermedadvisual = forms.ModelMultipleChoiceField(label=mark_safe(u'<a href="javascript:;" class="btn btn-generar btn-success tu" title="Agregar enfermedad visual" id="add_enfermedad_visual" idte="3" dte="Visual"><i class="fa fa-plus-square"></i></a>&nbsp;Enfermedades Visuales'),queryset=Enfermedad.objects.filter(tipo=3), required=False)
    transfusion = forms.BooleanField(label=u'Transfusiones?', required=False)
    gruposangre = forms.ChoiceField(label=u'Grupo Sangre', choices=GRUPO_SANGRE_CHOICES, required=False, widget=forms.Select(attrs={'class': 'imp-25'}))
    factorrh = forms.ChoiceField(label=u'Factor RH', choices=FACTOR_RH_CHOICES, required=False, widget=forms.Select(attrs={'class': 'imp-25'}))
    alergiamedicina = forms.BooleanField(label=u'Alergia a Medicinas?', required=False)
    alergiamedicinas = forms.ModelMultipleChoiceField(label=mark_safe(u'<a href="javascript:;" class="btn btn-generar btn-success tu" title="Agregar fármaco" id="add_alergia_farmaco" idte="FARMACOS" dte="Fármacos"><i class="fa fa-plus-square"></i></a>&nbsp;Medicinas'), queryset=Alergia.objects.filter(tipo='FARMACOS'), required=False)
    alergiaambiente = forms.BooleanField(label=u'Alergia a Sustancias Ambiente?', required=False)
    alergiaambientes = forms.ModelMultipleChoiceField(label=mark_safe(u'<a href="javascript:;" class="btn btn-generar btn-success tu" title="Agregar sustancia ambiente" id="add_alergia_ambiente" idte="MEDIO AMBIENTE" dte="Sustancias Ambiente"><i class="fa fa-plus-square"></i></a>&nbsp;Sustancias Ambiente'),queryset=Alergia.objects.filter(tipo='MEDIO AMBIENTE'), required=False)
    alergiaalimento = forms.BooleanField(label=u'Alergia por Alimientos?', required=False)
    alergiaalimentos = forms.ModelMultipleChoiceField(label=mark_safe(u'<a href="javascript:;" class="btn btn-generar btn-success tu" title="Agregar alimento" id="add_alergia_alimento" idte="ALIMENTOS" dte="Alimentos"><i class="fa fa-plus-square"></i></a>&nbsp;Alimentos'), queryset=Alergia.objects.filter(tipo='ALIMENTOS'), required=False)
    tomamedicina = forms.BooleanField(label=u'Toma Medicina?', required=False)
    medicinas = forms.ModelMultipleChoiceField(label=mark_safe(u'<a href="javascript:;" class="btn btn-generar btn-success tu" title="Agregar medicina" id="add_medicina"><i class="fa fa-plus-square"></i></a>&nbsp;Medicinas'), queryset=Medicina.objects.all(), required=False)
    enfermedad = forms.BooleanField(label=u'Enfermedades?', required=False)
    enfermedades = forms.ModelMultipleChoiceField(label=mark_safe(u'<a href="javascript:;" class="btn btn-generar btn-success tu" title="Agregar enfermedad general" id="add_enfermedad_general" idte="2" dte="General"><i class="fa fa-plus-square"></i></a>&nbsp;Enfermedades'), queryset=Enfermedad.objects.filter(tipo=2), required=False)
    enfermedadtrabajo = forms.ModelMultipleChoiceField(label=u'Enfermedades Durante el Trabajo', queryset=Enfermedad.objects.filter(tipo=2), required=False)
    enfermedadvenerea = forms.BooleanField(label=u'Infección Transm. Sexual?', required=False)
    enfermedadvenereas = forms.ModelMultipleChoiceField(label=mark_safe(u'<a href="javascript:;" class="btn btn-generar btn-success tu" title="Agregar infección TS" id="add_enfermedad_venerea" idte="4" dte="Transmisión sexual"><i class="fa fa-plus-square"></i></a>&nbsp;Infección T. Sexual'), queryset=Enfermedad.objects.filter(tipo=4), required=False)


class PatologicoQuirurgicosForm(forms.Form):
    cirugia = forms.BooleanField(label=u'Cirugía?', required=False)
    cirugias = forms.ModelMultipleChoiceField(label=mark_safe(u'<a href="javascript:;" class="btn btn-generar btn-success tu" title="Agregar cirugía" id="add_cirugia"><i class="fa fa-plus-square"></i></a>&nbsp;Cirugías'), queryset=Cirugia.objects.all(), required=False)
    fechacirugia = forms.DateField(label=u"Fecha ultima cirugia", input_formats=['%d-%m-%Y'], widget=DateTimeInput(format='%d-%m-%Y', attrs={'class': 'selectorfecha'}), required=False)
    complicacion = forms.CharField(label=u'Complicaciones', max_length=200, required=False)
    establecimiento = forms.CharField(label=u'En que Establecimiento', max_length=100, required=False)


class AntecedenteTraumatologicosForm(forms.Form):
    fractura = forms.BooleanField(label=u'Fracturas?', required=False)
    lugaranatomico = forms.ModelMultipleChoiceField(label=mark_safe(u'<a href="javascript:;" class="btn btn-generar btn-success tu" title="Agregar lugar anatómico" id="add_lugaranatomico"><i class="fa fa-plus-square"></i></a>&nbsp;Lugar Anatómico'), queryset=LugarAnatomico.objects.all(), required=False)
    accidentelaboral = forms.BooleanField(label=u'Accidente Laboral?', required=False)


class AntecedenteOdontologicoForm(forms.Form):
    bajotratamiento = forms.BooleanField(label=u'Bajo tratamiento odontológico?', required=False, widget=CheckboxInput({'class': 'imp-25'}))
    esalergico = forms.BooleanField(label=u'Alérgico a medicamento u otros?', required=False,  widget=CheckboxInput({'class': 'imp-25'}))
    alergias = forms.ModelMultipleChoiceField(label=mark_safe(u'<a href="javascript:;" class="btn btn-generar btn-success tu" title="Agregar alergia" id="add_alergia"><i class="fa fa-plus-square"></i></a>&nbsp;Alergias'), queryset=Alergia.objects.all(), required=False)
    propensohemorragia = forms.BooleanField(label=u'Propenso a hemorragia?', required=False, widget=forms.CheckboxInput(attrs={'formwidth': '50%'}))
    complicacionanestesiaboca = forms.BooleanField(label=u'Complicaciones aplicación anestesia?', required=False, widget=forms.CheckboxInput(attrs={'formwidth': '50%'}))
    toperatoria = forms.BooleanField(label=u'Tratamiendo operatoria?', required=False, widget=forms.CheckboxInput(attrs={'formwidth': '30%'}))
    tperiodoncia = forms.BooleanField(label=u'Tratamiendo periodoncia?', required=False, widget=forms.CheckboxInput(attrs={'formwidth': '30%'}))
    totro = forms.BooleanField(label=u'Tratamiendo otros?', required=False, widget=forms.CheckboxInput(attrs={'formwidth': '30%'}))
    periodontal = forms.BooleanField(label=u'Enfermedad periodontal?', required=False)
    materiaalba = forms.BooleanField(label=u'Materia Alba?', required=False, widget=forms.CheckboxInput(attrs={'formwidth': '30%'}))
    placabacteriana = forms.BooleanField(label=u'Placa Bacteriana?', required=False, widget=forms.CheckboxInput(attrs={'formwidth': '30%'}))
    calculossupra = forms.BooleanField(label=u'Cálculos sup/sub?', required=False, widget=forms.CheckboxInput(attrs={'formwidth': '30%'}))



class AntecedenteGinecoobstetricoForm(forms.Form):
    flujomenstrual = forms.ChoiceField(label=u'Flujo Menstrual', choices=FLUJO_MENSTRUAL, required=False, widget=forms.Select(attrs={'class': 'imp-25'}))
    menarquia = forms.CharField(label=u'Menarquia / Edad', max_length=20, required=False)
    catamenial = forms.CharField(label=u'Indice Catamenial', max_length=20, required=False)
    embrazos = forms.BooleanField(label=u'Embarazos?', required=False)
    partos = forms.IntegerField(label=u'No. partos', required=False, widget=forms.TextInput(attrs={'class': 'imp-number'}))
    partonormal = forms.BooleanField(label=u'Parto Normal?', required=False, widget=forms.CheckboxInput(attrs={'formwidth': '50%'}))
    partoprematuro = forms.BooleanField(label=u'Parto Prematuro?', required=False, widget=forms.CheckboxInput(attrs={'formwidth': '50%'}))
    cesareas = forms.IntegerField(label=u'No. cesareas', required=False, widget=forms.TextInput(attrs={'class': 'imp-number', 'formwidth': '30%'}))
    hijosvivos = forms.IntegerField(label=u'No. hijos Vivos', required=False, widget=forms.TextInput(attrs={'class': 'imp-number', 'formwidth': '30%'}))
    abortos = forms.IntegerField(label=u'No. abortos', required=False, widget=forms.TextInput(attrs={'class': 'imp-number', 'formwidth': '30%'}))
    abortonatural = forms.BooleanField(label=u'Causas Naturales?', required=False, widget=forms.CheckboxInput(attrs={'formwidth': '33%'}))
    abortoprovocado = forms.BooleanField(label=u'Provocado?', required=False, widget=forms.CheckboxInput(attrs={'formwidth': '33%'}))
    legrado = forms.BooleanField(label=u'Legrados?', required=False, widget=forms.CheckboxInput(attrs={'formwidth': '34%'}))
    puerperiocomplicacion = forms.CharField(label=u'Puerperios y Complicaciones', max_length=200, required=False)
    anticonceptivo = forms.BooleanField(label=u'Anticonceptivos?', required=False)
    metodoanticonceptivo = forms.ModelMultipleChoiceField(label=mark_safe(u'<a href="javascript:;" class="btn btn-generar btn-success tu" title="Agregar método anticonceptivo" id="add_metodo"><i class="fa fa-plus-square"></i></a>&nbsp;Métodos Anticonceptivos'), queryset=MetodoAnticonceptivo.objects.all(), required=False)


# hay que eliminar, tambein lo llama de alu_medical
# class PersonaPatologicoForm(forms.Form):
#     vacunas = forms.BooleanField(label=u'Vacunas basicas completas?', required=False)
#     nombrevacunas = forms.CharField(label=u'Vacunas', max_length=100, required=False)
#     enfermedades = forms.BooleanField(label=u'Enfermedades cronicas?', required=False)
#     nombreenfermedades = forms.CharField(label=u'Enfermedades', max_length=100, required=False)
#     alergiamedicina = forms.BooleanField(label=u'Alergias a medicamentos?', required=False)
#     nombremedicinas = forms.CharField(label=u'Medicamentos', max_length=100, required=False)
#     alergiaalimento = forms.BooleanField(label=u'Alergias o intoxicacion con alimentos?', required=False)
#     nombrealimentos = forms.CharField(label=u'Alimentos', max_length=100, required=False)
#     cirugias = forms.BooleanField(label=u'Cirugias?', required=False)
#     nombrecirugia = forms.CharField(label=u'Organos comprometidos', max_length=100, required=False)
#     fechacirugia = forms.DateField(label=u"Fecha ultima cirugia", input_formats=['%d-%m-%Y'], widget=DateTimeInput(format='%d-%m-%Y', attrs={'class': 'selectorfecha'}), required=False)
#     aparato = forms.BooleanField(label=u'Aparatos ortopedicos?', required=False)
#     tipoaparato = forms.CharField(label=u'Tipo aparato ortopedico', max_length=100, required=False)

# Eliminar y verificar que no se llama en otro formulario
# class PersonaGinecologicoForm(forms.Form):
#     gestacion = forms.BooleanField(label=u'Gestación actual?', required=False)
#     partos = forms.IntegerField(label=u'No. partos', required=False, widget=forms.TextInput(attrs={'class': 'imp-number'}))
#     abortos = forms.IntegerField(label=u'No. abortos', required=False, widget=forms.TextInput(attrs={'class': 'imp-number'}))
#     cesareas = forms.IntegerField(label=u'No. cesáreas', required=False, widget=forms.TextInput(attrs={'class': 'imp-number'}))
#     hijos2 = forms.IntegerField(label=u'No. hijos', required=False, widget=forms.TextInput(attrs={'class': 'imp-number'}))


class HabitoForm(forms.Form):
    cafecantidad = forms.CharField(label=u'Cafeísmo Cantidad', max_length=20, required=False, widget=forms.TextInput(attrs={'class': 'imp-20','formwidth': '30%'}))
    cafecalidad = forms.CharField(label=u'Calidad', max_length=20, required=False, widget=forms.TextInput(attrs={'class': 'imp-20','formwidth': '35%'}))
    cafefrecuencia = forms.CharField(label=u'Frecuencia', max_length=20, required=False, widget=forms.TextInput(attrs={'class': 'imp-20','formwidth': '35%'}))
    teismocantidad = forms.CharField(label=u'Teísmo Cantidad', max_length=20, required=False, widget=forms.TextInput(attrs={'class': 'imp-20','formwidth': '30%'}))
    tecalidad = forms.CharField(label=u'Calidad', max_length=20, required=False, widget=forms.TextInput(attrs={'class': 'imp-20','formwidth': '35%'}))
    tefrecuencia = forms.CharField(label=u'Frecuencia', max_length=20, required=False, widget=forms.TextInput(attrs={'class': 'imp-20','formwidth': '35%'}))
    consumetabaco = forms.BooleanField(label=u'Consume tabaco?', required=False)
    tabaquismo = forms.ChoiceField(label=u'Tabaquismo', choices=TABAQUISMO, required=False, widget=forms.Select(attrs={'class': 'imp-25','formwidth': '50%'}))
    consumealcohol = forms.BooleanField(label=u'Consume alcohol?', required=False)
    alcoholismo = forms.ChoiceField(label=u'Alcoholismo', choices=ALCOHOLISMO, required=False, widget=forms.Select(attrs={'class': 'imp-25','formwidth': '50%'}))
    consumedroga = forms.BooleanField(label=u'Consume droga?', required=False)
    droga = forms.ModelMultipleChoiceField(label=mark_safe(u'<a href="javascript:;" class="btn btn-generar btn-success tu" title="Agregar droga" id="add_droga"><i class="fa fa-plus-square"></i></a>&nbsp;Drogas'),queryset=Droga.objects.all(), required=False)
    alimentocantidad = forms.ChoiceField(label=u'Alimentación Cantidad', choices=ALIMENTACCION_CANTIDAD, required=False, widget=forms.Select(attrs={'class': 'imp-25','formwidth': '50%'}))
    alimentocalidad = forms.ChoiceField(label=u'Calidad', choices=ALIMENTACCION_CALIDAD, required=False, widget=forms.Select(attrs={'class': 'imp-25','formwidth': '50%'}))
    remuneracion = forms.DecimalField(label=u"Remuneración", required=False, initial="0.00", widget=forms.TextInput(attrs={'class': 'imp-moneda', 'decimal': '2'}))
    cargafamiliar = forms.IntegerField(label=u'Carga Familiar', required=False, widget=forms.TextInput(attrs={'class': 'imp-number'}))
    manutencion = forms.BooleanField(label=u'Pago de manutención de niños?', required=False)
    vivienda = forms.ChoiceField(label=u'Vivienda', choices=VIVIENDA, required=False, widget=forms.Select(attrs={'class': 'imp-25','formwidth': '50%'}))
    zona = forms.ChoiceField(label=u'Zona', choices=ZONA, required=False, widget=forms.Select(attrs={'class': 'imp-25','formwidth': '50%'}))
    tipoconstruccion = forms.ChoiceField(label=u'Tipo Construccion', choices=TIPO_CONSTRUCCION, required=False, widget=forms.Select(attrs={'class': 'imp-25','formwidth': '50%'}))
    ventilacion = forms.ChoiceField(label=u'Ventilación', choices=VENTILACION, required=False, widget=forms.Select(attrs={'class': 'imp-25','formwidth': '50%'}))
    numeropersonas = forms.IntegerField(label=u'No. Personas', required=False, widget=forms.TextInput(attrs={'class': 'imp-number'}))
    animalesdomesticos = forms.BooleanField(label=u'Animales Domesticos?', required=False)
    animalclase = forms.CharField(label=u'Clase de Animal', max_length=100, required=False)
    animalcantidad = forms.IntegerField(label=u'No. Animales', required=False, widget=forms.TextInput(attrs={'class': 'imp-number'}))
    servicioshigienicos = forms.IntegerField(label=u'No. Servicios Higiénicos', required=False, widget=forms.TextInput(attrs={'class': 'imp-number'}))
    aguapotable = forms.ChoiceField(label=u'Agua Potable', choices=AGUA_POTABLE, required=False, widget=forms.Select(attrs={'class': 'imp-25','formwidth': '50%'}))
    luz = forms.ChoiceField(label=u'Luz', choices=LUZ, required=False, widget=forms.Select(attrs={'class': 'imp-25','formwidth': '50%'}))
    transporte = forms.ChoiceField(label=u'Transporte', choices=TRANSPORTE, required=False, widget=forms.Select(attrs={'class': 'imp-25','formwidth': '50%'}))


class InspeccionSomaticaForm(forms.Form):
    postura = forms.ChoiceField(label=u'Actitud ó Postura', choices=POSTURA, required=False, widget=forms.Select(attrs={'class': 'imp-25','formwidth': '50%'}))
    gradoactividad = forms.ChoiceField(label=u'Grado de Actividad', choices=GRADO_ACTIVIDAD, required=False, widget=forms.Select(attrs={'class': 'imp-25','formwidth': '50%', 'separator': 'true'}))
    estadomental = forms.ChoiceField(label=u'Estado Mental', choices=ESTADO_MENTAL, required=False, widget=forms.Select(attrs={'class': 'imp-25','formwidth': '50%'}))
    orientaciontiempo = forms.BooleanField(label=u'Se orienta en Tiempo y espacio?', required=False, widget=forms.CheckboxInput(attrs={'formwidth': '50%'}))
    colaborainterrogantorio = forms.BooleanField(label=u'Colabora con el interrogatorio?', required=False, widget=forms.CheckboxInput(attrs={'formwidth': '50%'}))
    estadocaracter = forms.ChoiceField(label=u'Estado Caracter', choices=ESTADO_CARACTER, required=False, widget=forms.Select(attrs={'class': 'imp-25','formwidth': '50%'}))
    facies = forms.ChoiceField(label=u'Facies', choices=FACIES, required=False, widget=forms.Select(attrs={'class': 'imp-25','formwidth': '50%'}))
    biotipo = forms.ChoiceField(label=u'Biotipo', choices=BIOTIPO, required=False, widget=forms.Select(attrs={'class': 'imp-25','formwidth': '50%', 'separator': 'true'}))
    tallaclase = forms.ChoiceField(label=u'Talla clase', choices=TALLA, required=False, widget=forms.Select(attrs={'class': 'imp-25','formwidth': '50%'}))
    talla = forms.FloatField(label=u'Talla(Mts)', required=False, widget=forms.TextInput(attrs={'class': 'imp-number', 'formwidth': '33%'}))
    peso = forms.FloatField(label=u'Peso (Kg)', required=False, widget=forms.TextInput(attrs={'class': 'imp-number', 'formwidth': '33%'}))
    imc = forms.FloatField(label=u'IMC', required=False, widget=forms.TextInput(attrs={'class': 'imp-number', 'formwidth': '33%'}))
    nutricional = forms.ChoiceField(label=u'Estado Nutricional', choices=ESTADO_NUTRICIONAL, required=False, widget=forms.Select(attrs={'class': 'imp-25','formwidth': '50%', 'separator': 'true'}))
    color = forms.ModelChoiceField(label=u'Color', queryset=Raza.objects.all(), required=False, widget=forms.Select(attrs={'class': 'imp-25','formwidth': '50%', 'separator': 'true'}))
    humedad = forms.CharField(label=u'Humedad', max_length=100, required=False, widget=forms.TextInput(attrs={'class': 'imp-20','formwidth': '35%', 'separator': 'true'}))
    pilificacion = forms.CharField(label=u'Pilificación', max_length=100, required=False, widget=forms.TextInput(attrs={'class': 'imp-20','formwidth': '35%'}))
    lesioneprimaria = forms.ModelMultipleChoiceField(label=mark_safe(u'<a href="javascript:;" class="btn btn-generar btn-success tu" title="Agregar lesión primaria" tit="Agregar lesión primaria" tipo="PRIMARIAS" id="add_lesionpri"><i class="fa fa-plus-square"></i></a>&nbsp;Lesiones primarias'), queryset=Lesiones.objects.filter(tipo='PRIMARIAS'), required=False)
    lesionesecundaria = forms.ModelMultipleChoiceField(label=mark_safe(u'<a href="javascript:;" class="btn btn-generar btn-success tu" title="Agregar lesión secundaria" tit="Agregar lesión secundaria" tipo="SECUNDARIAS" id="add_lesionsec"><i class="fa fa-plus-square"></i></a>&nbsp;Lesiones secundarias'), queryset=Lesiones.objects.filter(tipo='SECUNDARIAS'), required=False)
    pelo = forms.CharField(label=u'Pelo', max_length=100, required=False, widget=forms.TextInput(attrs={'class': 'imp-20','formwidth': '35%'}))
    unas = forms.CharField(label=u'Uñas', max_length=100, required=False, widget=forms.TextInput(attrs={'class': 'imp-20','formwidth': '35%'}))
    marcha = forms.ChoiceField(label=u'Marcha', choices=TALLA, required=False, widget=forms.Select(attrs={'class': 'imp-25','formwidth': '50%', 'separator': 'true'}))
    movimiento = forms.ChoiceField(label=u'Movimientos', choices=MOVIMIENTO, required=False, widget=forms.Select(attrs={'class': 'imp-25','formwidth': '50%'}))

    def editar(self):
        campo_solo_lectura(self, 'imc')


class InspeccionTopograficaForm(forms.Form):
    craneo = forms.ChoiceField(label=u'Cabeza / Craneo', choices=CRANEO, required=False, widget=forms.Select(attrs={'class': 'imp-25','formwidth': '50%', 'separator': 'true'}))
    craneotamanio = forms.ChoiceField(label=u'Tamaño', choices=CRANEO_TAMANIO, required=False, widget=forms.Select(attrs={'class': 'imp-25','formwidth': '50%', 'separator': 'true'}))
    cabelloforma = forms.CharField(label=u'Cabello Forma', max_length=100, required=False, widget=forms.TextInput(attrs={'class': 'imp-20','formwidth': '35%', 'separator': 'true'}))
    cabellocolor = forms.CharField(label=u'Cabello Color', max_length=100, required=False, widget=forms.TextInput(attrs={'class': 'imp-20','formwidth': '35%'}))
    cabelloaspecto = forms.CharField(label=u'Cabello Aspecto', max_length=100, required=False, widget=forms.TextInput(attrs={'class': 'imp-20','formwidth': '35%'}))
    cabellodistribucion = forms.CharField(label=u'Cabello Distribución', max_length=100, required=False, widget=forms.TextInput(attrs={'class': 'imp-20','formwidth': '35%'}))
    cabellocantidad = forms.CharField(label=u'Cabello Cantidad', max_length=100, required=False, widget=forms.TextInput(attrs={'class': 'imp-20','formwidth': '35%'}))
    cabelloconsistencia = forms.CharField(label=u'Cabello Consistencia', max_length=100, required=False, widget=forms.TextInput(attrs={'class': 'imp-20','formwidth': '35%'}))
    cabelloimplantacion = forms.CharField(label=u'Cabello Implantación', max_length=100, required=False, widget=forms.TextInput(attrs={'class': 'imp-20','formwidth': '35%'}))
    caraterciosuperior = forms.CharField(label=u'Cara Tercio Superior', max_length=300, required=False)
    caraterciomedio = forms.CharField(label=u'Cara Tercio Medio', max_length=300, required=False)
    caratercioinferior = forms.CharField(label=u'Cara Tercio Inferior', max_length=300, required=False)
    cuellocaraanterior = forms.CharField(label=u'Cuello Cara Anterior', max_length=300, required=False)
    cuellocaralateralderecha = forms.CharField(label=u'Cuello Cara Lateral Derecha', max_length=300, required=False)
    cuellocaralateralizquierda = forms.CharField(label=u'Cuello Cara Lateral Izquierda', max_length=300, required=False)
    cuellocaraposterior = forms.CharField(label=u'Cuello Cara Posterior', max_length=300, required=False)
    toraxcaraanterior = forms.CharField(label=u'Torax Cara Anterior', max_length=300, required=False)
    toraxcaralateralderecha = forms.CharField(label=u'Torax Cara Lateral Derecha', max_length=300, required=False)
    toraxcaralateralizquierda = forms.CharField(label=u'Torax Cara Lateral Izquierda', max_length=300, required=False)
    toraxcaraposterior = forms.CharField(label=u'Torax Cara Posterior', max_length=300, required=False)
    abdomenanterior = forms.CharField(label=u'Abdomen Anterior', max_length=300, required=False)
    abdomenanteriorformas = forms.CharField(label=u'Abdomen Anterior Formas', max_length=300, required=False)
    abdomenanteriorvolumen = forms.CharField(label=u'Abdomen Anterior Volúmen', max_length=300, required=False)
    abdomenanteriorcicatrizumbilical = forms.CharField(label=u'Abdomen Anterior Cicatriz umbilical', max_length=300, required=False)
    abdomenanteriorcirculacionlateral = forms.CharField(label=u'Abdomen Anterior Circulación Lateral', max_length=300, required=False)
    abdomenanteriorcicatrices = forms.CharField(label=u'Abdomen Anterior Cicatrices', max_length=300, required=False)
    abdomenanteriornebus = forms.CharField(label=u'Abdomen Anterior Nebus', max_length=300, required=False)
    abdomenlateralizquierdo = forms.CharField(label=u'Abdomen Lateral Izquierdo', max_length=300, required=False)
    abdomenlateralderecho = forms.CharField(label=u'Abdomen Lateral Derecho', max_length=300, required=False)
    abdomenposterior = forms.CharField(label=u'Abdomen Posterior', max_length=300, required=False)
    inguinogenitalvello = forms.CharField(label=u'Región Inguinogenital vello', max_length=300, required=False)
    inguinogenitalhernias = forms.CharField(label=u'Región Inguinogenital Hernias', max_length=300, required=False)
    inguinogenitalpene = forms.CharField(label=u'Región Inguinogenital Pene', max_length=300, required=False)
    superioreshombro = forms.CharField(label=u'Superiores Hombro', max_length=300, required=False)
    superioresbrazo = forms.CharField(label=u'Superiores Brazo', max_length=300, required=False)
    superioresantebrazo = forms.CharField(label=u'Superiores Antebrazo', max_length=300, required=False)
    superioresmano = forms.CharField(label=u'Superiores Mano', max_length=300, required=False)
    inferiormuslo = forms.CharField(label=u'Inferior Muslo', max_length=300, required=False)
    inferiorpierna = forms.CharField(label=u'Inferior Pierna', max_length=300, required=False)
    inferiorpie = forms.CharField(label=u'Inferior Pie', max_length=300, required=False)


# eliminar tambien
# class PersonaHabitoForm(forms.Form):
#     cigarro = forms.BooleanField(label=u'Cigarrillo?', required=False)
#     numerocigarros = forms.IntegerField(label=u'No. cigarrillos por día', required=False, widget=forms.TextInput(attrs={'class': 'imp-number'}))
#     tomaalcohol = forms.BooleanField(label=u'Bebidas alcoholicas?', required=False)
#     tipoalcohol = forms.CharField(label=u'Tipo de bebidas', max_length=100, required=False)
#     copasalcohol = forms.IntegerField(label=u'No. copas a la semana', required=False, widget=forms.TextInput(attrs={'class': 'imp-number'}))
#     tomaantidepresivos = forms.BooleanField(label=u'Antidepresivos?', required=False)
#     antidepresivos = forms.CharField(label=u'Especifique antidepresivos', max_length=100, required=False)
#     tomaotros = forms.BooleanField(label=u'Otros?', required=False)
#     otros = forms.CharField(label=u'Especifique otros', max_length=100, required=False)
#     horassueno = forms.IntegerField(label=u'No. horas de sueño', required=False, widget=forms.TextInput(attrs={'class': 'imp-number'}))
#     calidadsuenno = forms.ChoiceField(label=u'Calidad de sueño', required=False, choices=CALIDAD_SUENNO, widget=forms.Select(attrs={'class': 'imp-50'}))


# class PersonaPatologicoFamiliarForm(forms.Form):
#     enfermedadpadre = forms.ModelMultipleChoiceField(label=u'Padre', queryset=Enfermedad.objects.all(), required=False)
#     enfermedadmadre = forms.ModelMultipleChoiceField(label=u'Madre', queryset=Enfermedad.objects.all(), required=False)
#     enfermedadabuelos = forms.ModelMultipleChoiceField(label=u'Abuelos', queryset=Enfermedad.objects.all(), required=False)
#     enfermedadhermanos = forms.ModelMultipleChoiceField(label=u'Hermanos', queryset=Enfermedad.objects.all(), required=False)
#     enfermedadotros = forms.ModelMultipleChoiceField(label=u'Familia', queryset=Enfermedad.objects.all(), required=False)


class PatologicoFamiliarForm(forms.Form):
    parentesco = forms.ModelChoiceField(Parentesco.objects.all(), label=u'Parentesco', required=True, widget=forms.Select(attrs={'formwidth': '50%'}))
    paterno = forms.BooleanField(label=u'Es Paterno?', required=False)
    enfermedades = forms.ModelMultipleChoiceField(label=mark_safe(u'<a href="javascript:;" class="btn btn-generar btn-success tu" title="Agregar enfermedad general" id="add_enfermedad_general" idte="2" dte="General"><i class="fa fa-plus-square"></i></a>&nbsp;Enfermedades'), queryset=Enfermedad.objects.filter(tipo=2), required=False)
    #enfermedades = forms.ModelMultipleChoiceField(label=u'Enfermedades', queryset=Enfermedad.objects.filter(tipo=2), required=False)


class RutagramaForm(forms.Form):
    direccion = forms.CharField(label=u"Calle principal", max_length=100, required=False,widget=forms.TextInput(attrs={'class': 'imp-75'}))
    direccion2 = forms.CharField(label=u"Calle secundaria", max_length=100, required=False,widget=forms.TextInput(attrs={'class': 'imp-75'}))
    tipovehiculo = forms.ChoiceField(label=u'Tipo Vehiculo', choices=TIPO_VEHICULO, required=False, widget=forms.Select(attrs={'class': 'imp-25','formwidth': '50%', 'separator': 'true'}))
    destinotrabajo = forms.BooleanField(label=u'Destino Trabajo?', required=False)
    tiempo = forms.ChoiceField(label=u'Tiempo', choices=TIEMPO, required=False, widget=forms.Select(attrs={'class': 'imp-25','formwidth': '50%', 'separator': 'true'}))
    horasalida = forms.TimeField(label=u"Hora de salida", required=False, initial=str(datetime.now().time()), input_formats=['%H:%M'], widget=TimeInput(format='%H:%M', attrs={'class': 'selectorhora', 'formwidth': '100px', 'separator': 'true'}))
    tiempoviaja = forms.TimeField(label=u"Tiempo de Viaje", required=False, initial=str(datetime.now().time()), input_formats=['%H:%M'], widget=TimeInput(format='%H:%M', attrs={'class': 'selectorhora', 'formwidth': '100px', 'separator': 'true'}))
    escala = forms.BooleanField(label=u'Escala?', required=False)
    tipoescala = forms.CharField(label=u'Indique Tipo de Escala', max_length=500, required=False)
    escala1 = forms.CharField(label=u'Escala Alterna 1', widget=forms.Textarea, required=False)
    escala2 = forms.CharField(label=u'Escala Alterna 2', widget=forms.Textarea, required=False)
    rutaalterna1 = forms.CharField(label=u'Ruta Alterna Posible 1', widget=forms.Textarea, required=False)
    rutaalterna2 = forms.CharField(label=u'Ruta Alterna Posible 2', widget=forms.Textarea, required=False)
    #archivo = ExtFileField(label=u'Seleccione Archivo Ruta', help_text=u'Tamaño Maximo permitido 4Mb, en formato pdf, jpg, jpeg, png', ext_whitelist=(".pdf", ".jpg", ".jpeg", ".png"), max_upload_size=4194304, widget=FileInput({'accept': 'application/pdf, image/jpeg, image/jpg, image/png'}))
    actividadsalir = forms.BooleanField(label=u'Actividades al Salir del Trabajo?', required=False)
    tipoactividad = forms.ModelMultipleChoiceField(label=u'Tipo de Actividades', queryset=TipoActividad.objects.all(), required=False)
    ubicacion = forms.ChoiceField(label=u'Ubicación', choices=UBICACION, required=False, widget=forms.Select(attrs={'class': 'imp-25','formwidth': '50%', 'separator': 'true'}))
    tiempoaproximado = forms.TimeField(label=u"Tiempo Aproximado", required=False, initial=str(datetime.now().time()), input_formats=['%H:%M'], widget=TimeInput(format='%H:%M', attrs={'class': 'selectorhora', 'formwidth': '100px', 'separator': 'true'}))
    frecuencia = forms.ChoiceField(label=u'Frecuencia', choices=FRECUENCIA, required=False, widget=forms.Select(attrs={'class': 'imp-25','formwidth': '50%', 'separator': 'true'}))
    actividad1 = forms.CharField(label=u'Actividad 1', max_length=600, required=False)
    actividad2 = forms.CharField(label=u'Actividad 2', max_length=600, required=False)
    actividadcalle = forms.CharField(label=u'Descripcion Breve Actividad en Calle', required=False, widget=forms.Textarea)


class PersonaExamenFisicoForm(forms.Form):
    #inspeccion = forms.CharField(label=u'Inspección', widget=forms.Textarea, required=False) # Eliminar despues ya esta en una tabla
    #usalentes = forms.BooleanField(label=u'Usa Lentes?', required=False) # Eliminar despues ya esta en una tabla
    #motivo = forms.ChoiceField(label=u'Motivo', choices=MOTIVO_LENTES, required=False, widget=forms.Select(attrs={'class': 'imp-50'})) # Eliminar despues ya esta en una tabla
    peso = forms.FloatField(label=u'Peso(Kg)', required=False, widget=forms.TextInput(attrs={'class': 'imp-number'}))
    talla = forms.FloatField(label=u'Talla(Mts)', required=False, widget=forms.TextInput(attrs={'class': 'imp-number'}))
    indicecorporal = forms.FloatField(label=u'Indice Corporal', required=False, widget=forms.TextInput(attrs={'class': 'imp-number'}))
    indicadorsobrepeso = forms.ModelChoiceField(label=u'Indicador sobrepeso', queryset=IndicadorSobrepeso.objects, required=False, widget=forms.Select(attrs={'class': 'imp-75'}))
    pa = forms.CharField(label=u'Presión arterial', required=False, widget=forms.TextInput(attrs={'class': 'imp-50'}))
    pulso = forms.CharField(label=u'Pulso', required=False, widget=forms.TextInput(attrs={'class': 'imp-50'}))
    rcar = forms.CharField(label=u'Ritmo cardiaco', required=False, widget=forms.TextInput(attrs={'class': 'imp-50'}))
    rresp = forms.FloatField(label=u'Ritmo respiratorio', required=False, widget=forms.TextInput(attrs={'class': 'imp-number'}))
    temp = forms.FloatField(label=u'Temperatura', required=False, widget=forms.TextInput(attrs={'class': 'imp-number'}))
    observaciones = forms.CharField(label=u'Observaciones', widget=forms.Textarea, required=False)

    def editar(self):
        deshabilitar_campo(self, 'indicecorporal')
        deshabilitar_campo(self, 'indicadorsobrepeso')


class PersonaConsultaMedicaForm(forms.Form):
    fechaatencion = forms.DateField(label=u"Fecha Atención", input_formats=['%d-%m-%Y'], required=False, widget=DateTimeInput(format='%d-%m-%Y', attrs={'class': 'selectorfecha'}))
    tipopaciente = forms.ChoiceField(label=u'Tipo de paciente', choices=TIPO_PACIENTE, required=False, widget=forms.Select(attrs={'class': 'imp-25'}))
    tipoatencion = forms.ChoiceField(label=u'Tipo de atención', choices=TIPOATENCIONMEDICA_CHOICES, required=False, widget=forms.Select(attrs={'class': 'imp-25'}))
    motivo = forms.CharField(label=u'Motivo Consulta', widget=forms.Textarea(attrs={'rows': '5'}), required=False)
    diagnostico = forms.CharField(label=u'Impresión Diagnóstico', widget=forms.Textarea(attrs={'rows': '5'}), required=False)
    enfermedad = forms.CharField(required=False, label=u'Código CIE-10', widget=forms.TextInput(attrs={'select2search': 'true'}))
    tratamiento = forms.CharField(label=u'Tratamiento', widget=forms.Textarea(attrs={'rows': '5'}), required=False)
    medicacion = forms.CharField(label=u'Medicación', widget=forms.Textarea(attrs={'rows': '5'}), required=False)
    cita = forms.BooleanField(label=u'Próxima cita', initial=False, required=False)
    fecha = forms.DateField(label=u"Fecha Cita", input_formats=['%d-%m-%Y'], required=False, widget=DateTimeInput(format='%d-%m-%Y', attrs={'class': 'selectorfecha'}))
    hora = forms.TimeField(label=u"Hora de entrevista", required=False, input_formats=['%H:%M'], widget=DateTimeInput(format='%H:%M', attrs={'class': 'selectorhora'}))
    indicaciones = forms.CharField(label=u'Indicaciones', max_length=300, required=False)
    accion = forms.ModelMultipleChoiceField(label=mark_safe(u'<a href="javascript:;" class="btn btn-generar btn-success tu" title="Agregar acciones" id="add_accion"><i class="fa fa-plus-square"></i></a>&nbsp;Acciones realizadas'), queryset=AccionConsulta.objects.filter(area=1), required=False)

    def grupos_paciente(self, grupos):
        self.fields['grupo'].queryset = grupos

    def tipos_paciente(self, tipoper, regimen):
        if tipoper == "ADT":
            if regimen == 1:
                tipos = [(1, u'ADMINISTRATIVO')]
            elif regimen == 2:
                tipos = [(6, u'TRABAJADOR')]
            else:
                tipos = [(2, u'DOCENTE')]
        elif tipoper == "ALU":
            tipos = [(3, u'ESTUDIANTE')]
        else:
            tipos = [('','--Seleccione--'), (4, u'PARTICULAR'), (5, u'PARTICULAR/EPUNEMI'), (7, u'NIVELACION')]

        self.fields['tipopaciente'].choices = tipos

    def editar(self, tipos, fechaatencion):
        del self.fields['cita']
        del self.fields['fecha']
        del self.fields['hora']
        del self.fields['indicaciones']
        #del self.fields['fechaatencion']
        self.fields['tipopaciente'].choices = [tipos]
        self.fields['fechaatencion'].initial = fechaatencion


class EntregaProductosConsultaForm(forms.Form):
    nombre = forms.CharField(label=u'Código', max_length=400, widget=forms.TextInput(attrs={'class': 'imp-codigo', 'autocomplete': 'off'}))


class PersonaConsultaOdontologicaForm(forms.Form):
    fechaatencion = forms.DateField(label=u"Fecha Atención", input_formats=['%d-%m-%Y'], required=False, widget=DateTimeInput(format='%d-%m-%Y', attrs={'class': 'selectorfecha'}))
    tipopaciente = forms.ChoiceField(label=u'Tipo de paciente', choices=TIPO_PACIENTE, required=False, widget=forms.Select(attrs={'class': 'imp-25'}))
    tipoatencion = forms.ChoiceField(label=u'Tipo de atención', choices=TIPOATENCIONODONTOLOGICA_CHOICES, required=False, widget=forms.Select(attrs={'class': 'imp-50'}))
    motivo = forms.CharField(label=u'Motivo', widget=forms.Textarea(attrs={'rows': '5'}), required=False)
    diagnostico = forms.CharField(label=u'Diagnóstico', widget=forms.Textarea(attrs={'rows': '5'}), required=False)
    enfermedad = forms.CharField(required=False, label=u'Código CIE-10', widget=forms.TextInput(attrs={'select2search': 'true'}))
    plantratamiento = forms.CharField(label=u'Plan tratamiento', widget=forms.Textarea(attrs={'rows': '5'}), required=False)
    #trabajosrealizados = forms.CharField(label=u'Trabajos realizados', widget=forms.Textarea(attrs={'rows': '5'}), required=False)
    indicaciones = forms.CharField(label=u'Indicaciones', widget=forms.Textarea(attrs={'rows': '5'}), required=False)
    accion = forms.ModelMultipleChoiceField(label=mark_safe(u'<a href="javascript:;" class="btn btn-generar btn-success tu" title="Agregar acciones" id="add_accion"><i class="fa fa-plus-square"></i></a>&nbsp;Acciones realizadas'), queryset=AccionConsulta.objects.filter(area=2), required=False)
    profilaxis = forms.BooleanField(label=u'Profilaxis', initial=False, required=False)
    causaprofilaxis = forms.ChoiceField(label=u'Causa Profilaxis', choices=CAUSAPROFILAXIS_CHOICES, required=False, widget=forms.Select(attrs={'class': 'imp-50'}))
    cita = forms.BooleanField(label=u'Próxima cita', initial=False, required=False)
    fecha = forms.DateField(input_formats=['%d-%m-%Y'], widget=DateTimeInput(format='%d-%m-%Y', attrs={'class': 'selectorfecha'}), label=u"Fecha", required=False)
    hora = forms.TimeField(label=u"Hora de entrevista", required=False, input_formats=['%H:%M'], widget=DateTimeInput(format='%H:%M', attrs={'class': 'selectorhora'}))
    indicacionescita = forms.CharField(max_length=300, label=u'Indicaciones Cita', required=False)



    def grupos_paciente(self, grupos):
        self.fields['grupo'].queryset = grupos

    def tipos_paciente(self, tipoper, regimen):
        if tipoper == "ADT":
            if regimen == 1:
                tipos = [(1, u'ADMINISTRATIVO')]
            elif regimen == 2:
                tipos = [(6, u'TRABAJADOR')]
            else:
                tipos = [(2, u'DOCENTE')]
        elif tipoper == "ALU":
            tipos = [(3, u'ESTUDIANTE')]
        else:
            tipos = [('','--Seleccione--'), (4, u'PARTICULAR'), (5, u'PARTICULAR/EPUNEMI'), (7, u'NIVELACION')]

        self.fields['tipopaciente'].choices = tipos


    def editar(self, tipos, fechaatencion):
        del self.fields['cita']
        del self.fields['fecha']
        del self.fields['hora']
        del self.fields['indicacionescita']
        #del self.fields['fechaatencion']
        self.fields['tipopaciente'].choices = [tipos]
        self.fields['fechaatencion'].initial = fechaatencion


class PersonaConsultaPsicologicaForm(forms.Form):
    fechaatencion = forms.DateField(label=u"Fecha Atención", input_formats=['%d-%m-%Y'], required=False, widget=DateTimeInput(format='%d-%m-%Y', attrs={'class': 'selectorfecha'}))
    tipopaciente = forms.ChoiceField(label=u'Tipo de paciente', choices=TIPO_PACIENTE, required=False, widget=forms.Select(attrs={'class': 'imp-25'}))
    tipoatencion = forms.ChoiceField(label=u'Tipo de atención', choices=TIPOATENCIONMEDICA_CHOICES, required=False, widget=forms.Select(attrs={'class': 'imp-25'}))
    tipoterapia = forms.ChoiceField(label=u'Tipo de terapia', choices=TIPOCONSULTA_TERAPIA, required=False, widget=forms.Select(attrs={'class': 'imp-50'}))
    motivo = forms.CharField(label=u'Motivo', widget=forms.Textarea(attrs={'rows': '5'}), required=False)
    diagnostico = forms.CharField(label=u'Diagnóstico', widget=forms.Textarea(attrs={'rows': '5'}), required=False)
    enfermedad = forms.CharField(required=False, label=u'Código CIE-10', widget=forms.TextInput(attrs={'select2search': 'true'}))
    tratamiento = forms.CharField(label=u'Tratamiento', widget=forms.Textarea(attrs={'rows': '5'}), required=False)
    medicacion = forms.CharField(label=u'Medicación', widget=forms.Textarea(attrs={'rows': '5'}), required=False)
    cita = forms.BooleanField(label=u'Próxima cita', initial=False, required=False)
    fecha = forms.DateField(label=u"Fecha", input_formats=['%d-%m-%Y'], required=False, widget=DateTimeInput(format='%d-%m-%Y', attrs={'class': 'selectorfecha'}))
    hora = forms.TimeField(label=u"Hora de entrevista", required=False, input_formats=['%H:%M'], widget=DateTimeInput(format='%H:%M', attrs={'class': 'selectorhora'}))
    indicaciones = forms.CharField(label=u'Indicaciones', max_length=300, required=False)
    accion = forms.ModelMultipleChoiceField(label=mark_safe(u'<a href="javascript:;" class="btn btn-generar btn-success tu" title="Agregar acciones" id="add_accion"><i class="fa fa-plus-square"></i></a>&nbsp;Acciones realizadas'), queryset=AccionConsulta.objects.filter(area=3), required=False)

    def grupos_paciente(self, grupos):
        self.fields['grupo'].queryset = grupos

    def tipos_paciente(self, tipoper, regimen):
        if tipoper == "ADT":
            if regimen == 1:
                tipos = [(1, u'ADMINISTRATIVO')]
            elif regimen == 2:
                tipos = [(6, u'TRABAJADOR')]
            else:
                tipos = [(2, u'DOCENTE')]
        elif tipoper == "ALU":
            tipos = [(3, u'ESTUDIANTE')]
        else:
            tipos = [('','--Seleccione--'), (4, u'PARTICULAR'), (5, u'PARTICULAR/EPUNEMI'), (7, u'NIVELACION')]

        self.fields['tipopaciente'].choices = tipos

    def editar(self, tipos):
        del self.fields['cita']
        del self.fields['fecha']
        del self.fields['hora']
        del self.fields['indicaciones']
        del self.fields['fechaatencion']
        self.fields['tipopaciente'].choices = [tipos]


class InventarioMedicoLoteForm(forms.Form):
    codigobarra = forms.CharField(label=u'Código barra', required=False, widget=forms.TextInput(attrs={'class': 'imp-25'}))
    nombre = forms.CharField(label=u'Nombre', required=False, widget=forms.TextInput(attrs={'class': 'imp-50'}))
    descripcion = forms.CharField(label=u'Descripción', required=False)
    tipo = forms.ChoiceField(label=u'Tipo', choices=TIPOINVENTARIOMEDICO_CHOICES, required=False, widget=forms.Select(attrs={'class': 'imp-50'}))
    numero = forms.CharField(label=u'No. Lote', required=False, widget=forms.TextInput(attrs={'class': 'imp-50'}))
    fechaelaboracion = forms.DateField(input_formats=['%d-%m-%Y'], widget=DateTimeInput(format='%d-%m-%Y', attrs={'class': 'selectorfecha'}), label=u"Fecha Elaboración", required=False)
    fechavencimiento = forms.DateField(input_formats=['%d-%m-%Y'], widget=DateTimeInput(format='%d-%m-%Y', attrs={'class': 'selectorfecha'}), label=u"Fecha Vencimiento", required=False)
    costo = forms.FloatField(label=u'Costo', required=False, widget=forms.TextInput(attrs={'class': 'imp-moneda'}))
    cantidad = forms.FloatField(label=u'Cantidad', required=False, widget=forms.TextInput(attrs={'class': 'imp-number'}))
    documento = forms.CharField(label=u'No. Documento', required=False, widget=forms.TextInput(attrs={'class': 'imp-25'}))
    detalle = forms.CharField(label=u'Detalle', required=False, widget=forms.Textarea())

    def editar(self):
        deshabilitar_campo(self, 'codigobarra')
        deshabilitar_campo(self, 'nombre')
        deshabilitar_campo(self, 'numero')
        del self.fields['documento']
        del self.fields['cantidad']
        del self.fields['detalle']


class AjusteInventarioMedicoLoteForm(forms.Form):
    tipo = forms.ChoiceField(label=u'Tipo', choices=TIPOMOVIMIENTOMEDICAMENTO_CHOICES, required=False, widget=forms.Select(attrs={'class': 'imp-50'}))
    cantidad = forms.FloatField(label=u'Cantidad', required=False, widget=forms.TextInput(attrs={'class': 'imp-number'}))
    documento = forms.CharField(label=u'No. Documento', required=False, widget=forms.TextInput(attrs={'class': 'imp-25'}))
    detalle = forms.CharField(label=u'Detalle', required=False, widget=forms.Textarea())


class PersonaConsultaNutricionForm(forms.Form):
    tipopaciente = forms.ChoiceField(label=u'Tipo de paciente', choices=TIPO_PACIENTE, required=False, widget=forms.Select(attrs={'class': 'imp-25'}))
    tipoatencion = forms.ChoiceField(label=u'Tipo de atención', choices=TIPOATENCIONODONTOLOGICA_CHOICES, required=False, widget=forms.Select(attrs={'class': 'imp-25'}))
    actividadfisica = forms.ChoiceField(label=u'Actividad Física', choices=ACTIVIDAD_FISICA, required=True, widget=forms.Select(attrs={'class': 'imp-25'}))
    motivo = forms.CharField(label=u'Motivo', widget=forms.Textarea(attrs={'rows': '5'}), required=False)
    diagnostico = forms.CharField(label=u'Diagnóstico Nutricional', widget=forms.Textarea(attrs={'rows': '5'}), required=False)
    recomendacion = forms.CharField(label=u'Recomendaciones Nutricionales', widget=forms.Textarea(attrs={'rows': '5'}), required=False)
    enfermedad = forms.CharField(required=False, label=u'Código CIE-10', widget=forms.TextInput(attrs={'select2search': 'true'}))
    fechaconsulta = forms.DateField(label=u"Fecha consulta", input_formats=['%d-%m-%Y'], required=False, widget=DateTimeInput(format='%d-%m-%Y', attrs={'class': 'selectorfecha'}))
    cita = forms.BooleanField(label=u'Próxima cita', initial=False, required=False)
    fecha = forms.DateField(label=u"Fecha", input_formats=['%d-%m-%Y'], required=False, widget=DateTimeInput(format='%d-%m-%Y', attrs={'class': 'selectorfecha'}))
    hora = forms.TimeField(label=u"Hora de entrevista", required=False, input_formats=['%H:%M'], widget=DateTimeInput(format='%H:%M', attrs={'class': 'selectorhora'}))
    indicaciones = forms.CharField(label=u'Indicaciones', max_length=300, required=False)

    def grupos_paciente(self, grupos):
        self.fields['grupo'].queryset = grupos

    def tipos_paciente(self, tipoper, regimen):
        if tipoper == "ADT":
            if regimen == 1:
                tipos = [(1, u'ADMINISTRATIVO')]
            elif regimen == 2:
                tipos = [(6, u'TRABAJADOR')]
            else:
                tipos = [(2, u'DOCENTE')]
        elif tipoper == "ALU":
            tipos = [(3, u'ESTUDIANTE')]
        else:
            tipos = [('','--Seleccione--'), (4, u'PARTICULAR'), (5, u'PARTICULAR/EPUNEMI'), (7, u'NIVELACION')]

        self.fields['tipopaciente'].choices = tipos

    def editar(self, tipos):
        del self.fields['cita']
        del self.fields['fecha']
        del self.fields['hora']
        del self.fields['indicaciones']
        self.fields['tipopaciente'].choices = [tipos]


class PersonaFichaNutricionForm(forms.Form):
    numeroficha = forms.IntegerField(label=u'Numero ficha', required=False, widget=forms.TextInput(attrs={'class': 'imp-number'}))
    consumoaldia = forms.IntegerField(label=u'Cuantas veces consume alimentos al dia', required=False, widget=forms.TextInput(attrs={'class': 'imp-number'}))
    fechaconsulta = forms.DateField(input_formats=['%d-%m-%Y'], widget=DateTimeInput(format='%d-%m-%Y', attrs={'class': 'selectorfecha'}), label=u"Fecha apertura ficha", required=False)
    patologia = forms.CharField(label=u"Patología", max_length=100, required=False, widget=forms.TextInput(attrs={'class': 'imp-75'}))
    antecedentespatologicos = forms.CharField(label=u"Antecedentes patológicos familiares", max_length=100, required=False, widget=forms.TextInput(attrs={'class': 'imp-75'}))


class ComidaFichaNutricionForm(forms.Form):
    comida = forms.ModelChoiceField(label=u"Comidas", queryset=Comidas.objects.filter(status=True).order_by('id'), required=True, widget=forms.Select())
    hora = forms.TimeField(label=u"Hora", required=True, input_formats=['%H:%M'], widget=DateTimeInput(format='%H:%M', attrs={'class': 'selectorhora'}))
    lugar = forms.CharField(label=u'Lugar', max_length=500, required=True)
    observacion = forms.CharField(label=u'Observacion', max_length=500, required=True)


class PruebasFichaNutricionForm(forms.Form):
    observacion = forms.CharField(label=u'Prueba', max_length=500, required=True)
    valor = forms.FloatField(label=u'Valor', initial="0.00", required=True, widget=forms.TextInput(attrs={'class': 'imp-numbermed-right', 'decimal': '2'}))


class ConsumoFichaNutricionForm(forms.Form):
    frecuencia = forms.ChoiceField(label=u'Frecuencia', choices=FRECUENCIACONSUMO, required=False, widget=forms.Select(attrs={'class': 'imp-25'}))
    valor = forms.IntegerField(label=u'Veces', required=False, widget=forms.TextInput(attrs={'class': 'imp-number'}))


class RegistrarIngresoBienestarForm(forms.Form):
    tiposerviciobienestar = forms.ModelChoiceField(label=u'Servicio', queryset=TipoServicioBienestar.objects.filter(status=True), required=False, widget=forms.Select(attrs={'class': 'imp-75'}))
    observacion = forms.CharField(required=False, label=u'Observación', widget=forms.Textarea({'rows': '4'}))


class DatosPsicologicoForm(forms.Form):
    relemointpadre = forms.ChoiceField(label=u'Relaciones emocionales interpersonales Padre', choices=ALTERNATIVAS, required=False, widget=forms.Select(attrs={'class': 'imp-25', 'formwidth': '33%', 'titulo': u'III. RELACIONES INTERPERSONALES Y EMOCIONALES DE LA FAMILIA'}))
    relemointmadre = forms.ChoiceField(label=u'Relaciones emocionales interpersonales Madre', choices=ALTERNATIVAS, required=False, widget=forms.Select(attrs={'class': 'imp-25', 'formwidth': '33%'}))
    relemointotros = forms.ChoiceField(label=u'Relaciones emocionales interpersonales Otros Miembros', choices=ALTERNATIVAS, required=False, widget=forms.Select(attrs={'class': 'imp-25', 'formwidth': '33%'}))

    antecedentes = forms.CharField(required=False, label=u'Antecedentes', widget=forms.Textarea({'rows': '4', 'separator': 'true', 'titulo': u'IV. ENFERMEDADES Y TRASTORNOS PSICOLOGICOS'}))
    alergia = forms.BooleanField(label=u'Alergias?', initial=False, required=False, widget=CheckboxInput(attrs={'formwidth': '25%'}))
    nauseas = forms.BooleanField(label=u'Nauseas?', initial=False, required=False, widget=CheckboxInput(attrs={'formwidth': '25%'}))
    vomito = forms.BooleanField(label=u'Vómito?', initial=False, required=False, widget=CheckboxInput(attrs={'formwidth': '25%'}))
    anorexia = forms.BooleanField(label=u'Anorexia?', initial=False, required=False, widget=CheckboxInput(attrs={'formwidth': '25%'}))
    bulimia = forms.BooleanField(label=u'Bulimia?', initial=False, required=False, widget=CheckboxInput(attrs={'formwidth': '25%'}))
    enuresis = forms.BooleanField(label=u'Enuresis?', initial=False, required=False, widget=CheckboxInput(attrs={'formwidth': '25%'}))
    encopresis = forms.BooleanField(label=u'Encopresis?', initial=False, required=False, widget=CheckboxInput(attrs={'formwidth': '25%'}))
    onicofagia = forms.BooleanField(label=u'Onicofagia?', initial=False, required=False, widget=CheckboxInput(attrs={'formwidth': '25%'}))
    ticsnervioso = forms.BooleanField(label=u'Tics nervioso?', initial=False, required=False, widget=CheckboxInput(attrs={'formwidth': '25%'}))
    trastornoneurologico = forms.BooleanField(label=u'Tiene trastornos Neurológicos?', initial=False, required=False, widget=CheckboxInput(attrs={'formwidth': '25%'}))
    tratamientotrastorno = forms.BooleanField(label=u'Tratamiento trastornos Neurológicos?', initial=False, required=False, widget=CheckboxInput(attrs={'formwidth': '25%'}))
    secuelastrastorno = forms.BooleanField(label=u'Secuelas trastornos Neurológicos?', initial=False, required=False, widget=CheckboxInput(attrs={'formwidth': '25%'}))
    edadtrastorno = forms.IntegerField(label=u'Edad trastornos Neurológicos', required=False, widget=forms.TextInput(attrs={'class': 'imp-numbersmall'}))
    actitudenfermedada = forms.CharField(required=False, label=u'Actitud frente a enfermedades', widget=forms.Textarea({'rows': '1'}))
    actitudmuerte = forms.CharField(required=False, label=u'Actitud frente a muerte', widget=forms.Textarea({'rows': '1'}))
    actitudpadre = forms.CharField(required=False, label=u'Actitud frente a padres', widget=forms.Textarea({'rows': '1'}))

    masturbacionarea = forms.BooleanField(label=u'Masturbación?', initial=False, required=False, widget=CheckboxInput(attrs={'formwidth': '33%', 'separator': 'true', 'titulo': u'V. ÁREA SEXUAL'}))
    curiosidadsexualinfancia = forms.BooleanField(label=u'Curiosidad Sexual Infancia?', initial=False, required=False, widget=CheckboxInput(attrs={'formwidth': '33%'}))
    edadcuriosidad = forms.IntegerField(label=u'Edad Curiodidad sexual', required=False, widget=forms.TextInput(attrs={'class': 'imp-numbersmall', 'formwidth': '33%'}))
    relaciones = forms.CharField(required=False, label=u'Relaciones', widget=forms.Textarea({'rows': '1'}))
    edaddesarrollosexual = forms.IntegerField(label=u'Edad desarrollo sexual', required=False, widget=forms.TextInput(attrs={'class': 'imp-numbersmall'}))
    actitudpadredesarrollosexual = forms.CharField(required=False, label=u'Actitud de padres frente al desarrollo sexual', widget=forms.Textarea({'rows': '1'}))

    amigospreferidos = forms.BooleanField(label=u'Amigos(as) preferidos?', initial=False, required=False, widget=CheckboxInput(attrs={'formwidth': '25%', 'separator': 'true', 'titulo': u'VI. SOCIABILIDAD'}))
    numeroamigos = forms.IntegerField(label=u'Numero de Amigos', required=False, widget=forms.TextInput(attrs={'class': 'imp-numbersmall', 'formwidth': '75%'}))
    comportamientoanteadulto = forms.ChoiceField(label=u'Relaciones emocionales interpersonales Padre', choices=ALTERNATIVASVARIAS, required=False, widget=forms.Select(attrs={'class': 'imp-25', 'formwidth': '33%'}))
    relacompaneros = forms.ChoiceField(label=u'Relaciones con compañeros', choices=ALTERNATIVAS, required=False, widget=forms.Select(attrs={'class': 'imp-25', 'formwidth': '33%'}))
    relamaestros = forms.ChoiceField(label=u'Relaciones con maestros', choices=ALTERNATIVAS, required=False, widget=forms.Select(attrs={'class': 'imp-25', 'formwidth': '33%'}))

    dificultadcaminar = forms.BooleanField(label=u'Dificultad al caminar?', initial=False, required=False, widget=CheckboxInput(attrs={'formwidth': '25%', 'separator': 'true', 'titulo': u'VII. ESTADO ACTUAL'}))
    lenguaje = forms.IntegerField(label=u'Lenguaje(Edad)', required=False, widget=forms.TextInput(attrs={'class': 'imp-numbersmall', 'formwidth': '70%'}))
    balbuceo = forms.BooleanField(label=u'Balbuceo?', initial=False, required=False, widget=CheckboxInput(attrs={'formwidth': '33%'}))
    imitasonido = forms.BooleanField(label=u'Imitación de sonidos?', initial=False, required=False, widget=CheckboxInput(attrs={'formwidth': '33%'}))
    silabas = forms.BooleanField(label=u'Silabas?', initial=False, required=False, widget=CheckboxInput(attrs={'formwidth': '33%'}))
    primerapalabra = forms.BooleanField(label=u'Primera palabras?', initial=False, required=False, widget=CheckboxInput(attrs={'formwidth': '33%'}))
    frases = forms.BooleanField(label=u'Frases?', initial=False, required=False, widget=CheckboxInput(attrs={'formwidth': '33%'}))
    dificultades = forms.BooleanField(label=u'Dificutades?', initial=False, required=False, widget=CheckboxInput(attrs={'formwidth': '33%'}))
    idiomas = forms.ModelMultipleChoiceField(label=u'Idioma', queryset=Idioma.objects.all(), required=False, widget=forms.SelectMultiple(attrs={'formwidth': '50%'}))
    estadoactual = forms.CharField(required=False, label=u'Estado Actual', widget=forms.Textarea({'rows': '1', 'formwidth': '49%'}))

    separacionmatrimonial = forms.BooleanField(label=u'Separaciones matrimoniales?', initial=False, required=False, widget=CheckboxInput(attrs={'formwidth': '33%', 'separator': 'true', 'titulo': u'SUCESOS IMPORTANTES A LO LARGO DE LA VIDA'}))
    cambioresidencia = forms.BooleanField(label=u'Cambios de residencia?', initial=False, required=False, widget=CheckboxInput(attrs={'formwidth': '33%'}))
    enfermedades = forms.BooleanField(label=u'Enfermedades?', initial=False, required=False, widget=CheckboxInput(attrs={'formwidth': '33%'}))
    defunciones = forms.BooleanField(label=u'Defunciones?', initial=False, required=False, widget=CheckboxInput(attrs={'formwidth': '33%'}))
    viajesprolongados = forms.BooleanField(label=u'Viajes Prolongados?', initial=False, required=False, widget=CheckboxInput(attrs={'formwidth': '33%'}))
    problemaeconomicos = forms.BooleanField(label=u'Problemas Económicos?', initial=False, required=False, widget=CheckboxInput(attrs={'formwidth': '33%'}))

    matrimoniounion = forms.BooleanField(label=u'Matrimonio/Unión?', initial=False, required=False, widget=CheckboxInput(attrs={'formwidth': '30%', 'separator': 'true', 'titulo': u'ADOLESCENCIA (Hasta los dieciocho años)'}))
    masturbacionadolecencia = forms.BooleanField(label=u'Masturbación Adolescencia?', initial=False, required=False, widget=CheckboxInput(attrs={'formwidth': '33%'}))
    edadprimerarelacion = forms.IntegerField(label=u'Edad primera relación sexual', required=False, widget=forms.TextInput(attrs={'formwidth': '30%', 'class': 'imp-numbersmall'}))
    compromisosociales = forms.BooleanField(label=u'Compromiso Sociales?', initial=False, required=False, widget=CheckboxInput(attrs={'formwidth': '30%'}))
    cargotrabajo = forms.CharField(required=False, label=u'Cargo de Trabajo', widget=forms.Textarea({'rows': '1', 'formwidth': '69%'}))
    alcoholadolecencia = forms.BooleanField(label=u'Alcohol Adolescencia?', initial=False, required=False, widget=CheckboxInput(attrs={'formwidth': '25%'}))
    edadalcohol = forms.IntegerField(label=u'Edad alcohol Adolescencia', required=False, widget=forms.TextInput(attrs={'class': 'imp-numbersmall', 'formwidth': '30%'}))
    motivoalcohol = forms.CharField(required=False, label=u'Motivo por ingerir alcohol', widget=forms.Textarea({'rows': '1', 'formwidth': '45%'}))
    drogasadolecencia = forms.BooleanField(label=u'Drogas Adolescencia?', initial=False, required=False, widget=CheckboxInput(attrs={'formwidth': '25%'}))
    edaddrogas = forms.IntegerField(label=u'Edad drogas Adolescencia', required=False, widget=forms.TextInput(attrs={'class': 'imp-numbersmall', 'formwidth': '30%'}))
    motivodrogas = forms.CharField(required=False, label=u'Motivo por ingerir drogas', widget=forms.Textarea({'rows': '1', 'formwidth': '45%'}))

    enamoramiento = forms.BooleanField(label=u'Enamoramiento?', initial=False, required=False, widget=CheckboxInput(attrs={'formwidth': '33%', 'separator': 'true', 'titulo': u'ADULTEZ (Conteste si / no, o de acuerdo a las instrucciones en caso de ser adulto)'}))
    cantidadrelaciones = forms.IntegerField(label=u'Cantidad de relaciones', required=False, widget=forms.TextInput(attrs={'formwidth': '33%', 'class': 'imp-numbersmall'}))
    ultimarelacion = forms.IntegerField(label=u'Tiempo de ultima Relación(En meses)', required=False, widget=forms.TextInput(attrs={'formwidth': '33%', 'class': 'imp-numbersmall'}))
    masturbacionadulto = forms.BooleanField(label=u'Masturbación Adultez?', initial=False, required=False, widget=CheckboxInput(attrs={'formwidth': '33%'}))
    matrimoniounionadulto = forms.BooleanField(label=u'Matrimonio/Unión?', initial=False, required=False, widget=CheckboxInput(attrs={'formwidth': '33%'}))
    edadultimarelacion = forms.IntegerField(label=u'Edad de ultima Relación', required=False, widget=forms.TextInput(attrs={'formwidth': '33%', 'class': 'imp-numbersmall'}))
    compromisosocialesadulto = forms.BooleanField(label=u'Compromiso Sociales?', initial=False, required=False, widget=CheckboxInput(attrs={'formwidth': '33%'}))
    cargotrabajoadulto = forms.CharField(required=False, label=u'Cargo de Trabajo', widget=forms.Textarea({'formwidth': '66%', 'rows': '1'}))
    alcoholadolecenciaadulto = forms.BooleanField(label=u'Alcohol Adultez?', initial=False, required=False, widget=CheckboxInput(attrs={'formwidth': '25%'}))
    edadalcoholadulto = forms.IntegerField(label=u'Edad alcohol Adultez', required=False, widget=forms.TextInput(attrs={'class': 'imp-numbersmall', 'formwidth': '30%'}))
    motivoalcoholadulto = forms.CharField(required=False, label=u'Motivo por ingerir alcohol', widget=forms.Textarea({'rows': '1', 'formwidth': '45%'}))
    drogasadolecenciaadulto = forms.BooleanField(label=u'Drogas Adultez?', initial=False, required=False, widget=CheckboxInput(attrs={'formwidth': '25%'}))
    edaddrogasadulto = forms.IntegerField(label=u'Edad drogas Adultez', required=False, widget=forms.TextInput(attrs={'class': 'imp-numbersmall', 'formwidth': '30%'}))
    motivodrogasadulto = forms.CharField(required=False, label=u'Motivo por ingerir drogas', widget=forms.Textarea({'rows': '1', 'formwidth': '45%'}))


class ControlBarNutricionForm(forms.Form):
    numeroficha = forms.IntegerField(label=u'Numero ficha', required=False,  widget=forms.TextInput(attrs={'class': 'imp-number', 'formwidth': '50%'}))
    fecha = forms.DateField(input_formats=['%d-%m-%Y'], widget=DateTimeInput(format='%d-%m-%Y', attrs={'class': 'selectorfecha', 'formwidth': '50%'}), label=u"Fecha apertura ficha", required=False)
    observaciones = forms.CharField(required=False, label=u'Observación', widget=forms.Textarea({'rows': '4'}))


class PlanificacionTemaForm(forms.Form):
    tema = forms.CharField(label=u"Tema", max_length=250, required=True, widget=forms.TextInput(attrs={'class': 'imp-100'}))
    objetivo = forms.CharField(required=True, label=u'Objetivo', widget=forms.Textarea({'rows': '4'}))


class CursoTemasPlanificacionForm(forms.Form):
    coordinacion = forms.ModelChoiceField(label=u"Coordinacion", queryset=Coordinacion.objects.filter(status=True).exclude(pk__in=[6,7,8,9,10,11]), required=False, widget=forms.Select(attrs={'class': 'imp-75'}))
    nivel = forms.ModelChoiceField(label=u"Nivel modalidad", queryset=Nivel.objects.all(), required=False, widget=forms.Select())
    carrera = forms.ModelChoiceField(label=u"Carrera", queryset=Carrera.objects.filter(status=True), required=False, widget=forms.Select())
    semestre = forms.ModelChoiceField(label=u"Nivel", queryset=NivelMalla.objects.filter(status=True), required=False, widget=forms.Select())
    paralelo = forms.ModelChoiceField(label=u"Paralelo", queryset=Paralelo.objects.filter(status=True), required=False, widget=forms.Select())
    fecha = forms.DateField(label=u"Fecha", input_formats=['%d-%m-%Y'], widget=DateTimeInput(format='%d-%m-%Y', attrs={'class': 'selectorfecha'}), required=False)

    def adicionar(self):
        self.fields['nivel'].queryset = Nivel.objects.filter(nivellibrecoordinacion__coordinacion_id=0)
        self.fields['carrera'].queryset = Carrera.objects.filter(pk=0)
        self.fields['paralelo'].queryset = Paralelo.objects.filter(pk=0)


class PreguntaTestForm(forms.Form):
    descripcion = forms.CharField(required=False, label=u'Descripción', widget=forms.Textarea({'rows': '4'}))
    leyenda = forms.CharField(required=False, label=u'Leyenda', widget=forms.Textarea({'rows': '4'}))


class EscalaPreguntaTestForm(forms.Form):
    descripcion = forms.CharField(required=False, label=u"Descripción", max_length=200, widget=forms.TextInput(attrs={'class': 'imp-50'}))
    leyenda = forms.CharField(required=False, label=u"Leyenda", max_length=200, widget=forms.TextInput(attrs={'class': 'imp-50'}))

class CompletarConsultaNutricionForm(FormModeloBase):
    medico = forms.ModelChoiceField(label=u"Médico", queryset=Persona.objects.filter(status=True), required=True, widget=forms.Select(attrs={'class': 'select2'}))
    tipopaciente = forms.ChoiceField(label=u'Tipo de paciente', choices=TIPO_PACIENTE, required=True, widget=forms.Select(attrs={'col': '6', 'class': 'select2'}))
    tipoatencion = forms.ChoiceField(label=u'Tipo de atención', choices=TIPOATENCIONODONTOLOGICA_CHOICES, required=True, widget=forms.Select(attrs={'col': '3', 'class': 'select2'}))
    actividadfisica = forms.ChoiceField(label=u'Actividad Física', choices=ACTIVIDAD_FISICA, required=True, widget=forms.Select(attrs={'col': '3', 'class': 'select2'}))
    motivo = forms.CharField(label=u'Motivo', widget=forms.Textarea(attrs={'rows': '5'}), required=True)
    diagnostico = forms.CharField(label=u'Diagnóstico Nutricional', widget=forms.Textarea(attrs={'rows': '5', 'col': '6'}), required=True)
    recomendacion = forms.CharField(label=u'Recomendaciones Nutricionales', widget=forms.Textarea(attrs={'rows': '5', 'col': '6'}), required=False)
    enfermedad = forms.ModelMultipleChoiceField(queryset=CatalogoEnfermedad.objects.filter(status=True), required=False, label=u'Código CIE-10', widget=forms.SelectMultiple(attrs={'col': '12', 'class': 'select2'}))
    cita = forms.BooleanField(label=u'Próxima cita', initial=False, required=False, widget=forms.CheckboxInput(attrs={'data-switchery': True, 'col': '4'}))
    fechacita = forms.DateTimeField(label=u"Fecha", required=False, widget=DateTimeInput(format='%Y-%m-%d', attrs={'class': 'selectorfecha', 'col': '4', 'type':'date'}))
    hora = forms.TimeField(label=u"Hora de entrevista", required=False, widget=forms.TimeInput(attrs={'class': 'selectorhora', 'col': '4'}))
    indicaciones = forms.CharField(label=u'Indicaciones', max_length=300, required=False)

    def grupos_paciente(self, grupos):
        self.fields['grupo'].queryset = grupos

    def tipos_paciente(self, tipoper, regimen):
        if tipoper == "ADT":
            if regimen == 1:
                tipos = [(1, u'ADMINISTRATIVO')]
            elif regimen == 2:
                tipos = [(6, u'TRABAJADOR')]
            else:
                tipos = [(2, u'DOCENTE')]
        elif tipoper == "ALU":
            tipos = [(3, u'ESTUDIANTE')]
        else:
            tipos = [('','--Seleccione--'), (4, u'PARTICULAR'), (5, u'PARTICULAR/EPUNEMI'), (7, u'NIVELACION')]

        self.fields['tipopaciente'].choices = tipos

    def editar(self, tipos):
        del self.fields['cita']
        del self.fields['fecha']
        del self.fields['hora']
        del self.fields['indicaciones']
        self.fields['tipopaciente'].choices = [tipos]

class AntropometriaForm(FormModeloBase):
    nombre = forms.CharField(label=u'Nombre', widget=forms.TextInput(attrs={'col': '12', 'placeholder':'Describa un nombre según requiera...'}), required=True)
    slug = forms.CharField(label=u'Nombre en Inbody', widget=forms.TextInput(attrs={'col': '12', 'placeholder':'Describa el nombre de la columna de InBody'}), required=False)

    def clean(self):
        cleaned_data=super().clean()
        nombre = unidecode(cleaned_data.get('nombre'))
        slug = unidecode(cleaned_data.get('slug'))
        id = getattr(self.instancia, 'id', 0)
        antropometria_n = Antropometria.objects.filter(nombre__iexact=nombre, status=True).exclude(id=id)
        antropometria_s = Antropometria.objects.filter(slug__iexact=slug, status=True).exclude(id=id)
        if antropometria_n.exists():
            self.add_error('nombre', 'Registro que desea ingresar ya existe')
        if antropometria_s.exists() and slug:
            self.add_error('slug', 'Registro que desea ingresar ya existe')
        return cleaned_data


class ConsultaMedicaForm(FormModeloBase):
    fechaatencion = forms.DateField(label=u"Fecha Atención", required=False, initial=datetime.now().date(), widget=DateTimeInput(format='%d-%m-%Y', attrs={'class': 'selectorfecha', 'col': '6'}), )
    tipopaciente = forms.ChoiceField(label=u'Tipo de Paciente', choices=TIPO_PACIENTE, required=False, widget=forms.Select(attrs={'col': '6'}))
    tipoatencion = forms.ChoiceField(label=u'Tipo de Atención', choices=TIPOATENCIONMEDICA_CHOICES, required=False, widget=forms.Select(attrs={'col': '6'}))
    motivo = forms.CharField(label=u'Motivo Consulta', widget=forms.Textarea(attrs={'rows': '5', 'col': '12'}), required=False)
    diagnostico = forms.CharField(label=u'Impresión Diagnóstico', widget=forms.Textarea(attrs={'rows': '5', 'col': '12'}), required=False)
    enfermedad = forms.ModelMultipleChoiceField(label=u'Código CIE-10', queryset=CatalogoEnfermedad.objects.filter(pk=0), required=False, widget=forms.SelectMultiple(attrs={'col': '12'}))
    tratamiento = forms.CharField(label=u'Tratamiento', widget=forms.Textarea(attrs={'rows': '5', 'col': '12'}), required=False)
    proximacita = forms.BooleanField(label=u"¿Próxima cita?", required=False, initial=False, widget=forms.CheckboxInput(attrs={'class': 'js-switch', 'col': '12'}))
    fechacita = forms.DateField(label=u"Fecha Cita", required=False, initial=datetime.now().date(), widget=DateTimeInput(format='%d-%m-%Y', attrs={'class': 'selectorfecha', 'col': '6'}), )
    horacita = forms.TimeField(label=u"Hora de entrevista", required=False, initial=str(datetime.now().time().strftime("%H:%M")), widget=DateTimeInput(format='%H:%M', attrs={'class': 'selectorhora', 'col': '6'}))
    indicaciones = forms.CharField(label=u"Indicaciones", max_length=250, widget=forms.TextInput(attrs={'col': '12', 'autocomplete': 'off'}), required=False)
    accion = forms.ModelMultipleChoiceField(label=mark_safe(u'<a href="javascript:;" class="btn btn-generar btn-success tu" title="Agregar acciones" id="add_accion"><i class="fa fa-plus-square"></i></a>&nbsp;Acciones realizadas'), queryset=AccionConsulta.objects.filter(area=1), required=False)

    def tipos_paciente(self, tipoper, regimen):
        if tipoper == "ADT":
            if regimen == 1:
                tipos = [(1, u'ADMINISTRATIVO')]
            elif regimen == 2:
                tipos = [(6, u'TRABAJADOR')]
            else:
                tipos = [(2, u'DOCENTE')]
        elif tipoper == "ALU":
            tipos = [(3, u'ESTUDIANTE')]
        else:
            tipos = [('','--Seleccione--'), (4, u'PARTICULAR'), (5, u'PARTICULAR/EPUNEMI'), (7, u'NIVELACION')]

        self.fields['tipopaciente'].choices = tipos

    def editar(self, tipos):
        self.fields['tipopaciente'].choices = [tipos]
