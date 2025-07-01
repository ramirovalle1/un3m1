from django.core.exceptions import ValidationError
from django import forms


def NumerosYLetras(cadena, name):
    mensaje = f'En el campo {name} debe ingresar solo números y letras sin ningún espacio.'
    if cadena.isalnum():
        if cadena.isdigit():
            raise forms.ValidationError(mensaje)
    else:
        raise forms.ValidationError(mensaje)
    return cadena


def SoloLetras(palabra, name_camp):
    if palabra:
        for x in palabra:
            if not x.isspace():
                cadena = x
        if not cadena.isalpha():
            raise ValidationError('El campo ' + name_camp + ' solo tiene que contener letras.')
    return palabra


def SoloNumeros(value):
    if not value.isdigit():
        raise ValidationError('El campo solo tiene que contener números.')
    return value


def Min_lenght(value):
    if len(value) < 10:
        raise ValidationError('Asegúrese de que este valor tenga 10 caracteres')


def dividirCadena(cadena, separador, numeroCaracteres):
    cifra = ""
    contador = 0
    for numero in cadena[::-1]:
        if contador == numeroCaracteres:
            cifra += separador
            contador = 0

        contador += 1
        cifra += numero

    return (cifra)


def v_cedula(value):
    # sin ceros a la izquierda
    SoloNumeros(value)
    cont = 0
    cedula = ""
    suma = 0
    validador = 0
    try:
        for digit in value:
            cedula += digit
            cont = cont + 1
            if cont == 2:
                pro = int(cedula)
                if not (pro > 0 and pro <= 24):
                    raise ValidationError('Error provincia')

            if cont == 3:
                indi = int(digit)
                if not indi < 6:
                    raise ValidationError('Error digito 3')
            if cont < 10:
                if cont % 2 == 0:
                    mult = int(digit) * 1
                else:
                    mult = int(digit) * 2

                if mult >= 10:
                    mult = mult - 9
                suma += mult

            if cont == 10:
                while suma % 10 != 0:
                    suma += 1
                    validador += 1

                if validador != int(digit):
                    raise ValidationError('Cédula Incorrecta')
    except ValueError:
        raise ValidationError('Algo fallo en la validación de cédula')


# VALIDACIONES PARA FORMULARIOS
def v_cedulaform(self, value, campo):
    try:
        cont = 0
        cedula = ""
        suma = 0
        validador = 0
        if not value.isdigit():
            return self.add_error(campo, 'El número de cédula no es válido, debe contener solo números')
        if len(value) != 10:
            return self.add_error(campo, 'El número de cédula no es válido, debe tener 10 dígitos')
        for digit in value:
            cedula += digit
            cont = cont + 1
            if cont == 2:
                pro = int(cedula)
                if not (pro > 0 and pro <= 24):
                    return self.add_error(campo, 'El código de la provincia (dos primeros dígitos) es inválido')
            if cont == 3:
                indi = int(digit)
                if not indi < 6:
                    return self.add_error(campo, 'El tercer dígito ingresado es inválido')
            if cont < 10:
                if cont % 2 == 0:
                    mult = int(digit) * 1
                else:
                    mult = int(digit) * 2

                if mult >= 10:
                    mult = mult - 9
                suma += mult

            if cont == 10:
                while suma % 10 != 0:
                    suma += 1
                    validador += 1

                if validador != int(digit):
                    return self.add_error(campo, 'El número de cédula introducido es incorrecto')
    except ValueError:
        self.add_error(campo, 'Algo fallo en la validación de cédula')


def v_solonumerosform(self, value, campo):
    if value and not value.isdigit():
        return self.add_error(campo, 'El campo solo tiene que contener números.')


def v_sololetrasform(self, value, campo):
    if value:
        for x in value:
            if not x.isspace():
                cadena = x
        if not cadena.isalpha():
            return self.add_error(campo, 'El campo solo tiene que contener letras')
