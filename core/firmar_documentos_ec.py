import json
import os
import subprocess
from datetime import datetime

from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives.serialization import pkcs12
from django.db import models
from .funciones_adicionales import customgetattr

import settings
from settings import BASE_DIR, MEDIA_ROOT


class JavaFirmaEc:
    def __init__(self, archivo_a_firmar, archivo_certificado, extension_certificado, password_certificado: str, page="1", reason="", type_file="pdf",
                    lx="10", ly="100", type_sign="QR"):
        self.archivo_a_firmar = archivo_a_firmar
        self.archivo_certificado = archivo_certificado
        self.password_certificado = password_certificado
        self.extension_certificado = extension_certificado
        self.page = str(int(page) + 1)
        self.reason = reason
        self.type_file = type_file
        self.lx = str(int(lx))
        self.ly = str(int(ly))
        self.type_sign = type_sign
        self.jar_file = os.path.join(BASE_DIR, "FIRMA_EC.jar")
        self.java_path = f"{hasattr(settings, 'JAVA_V20') and customgetattr(settings, 'JAVA_V20') or ''}java"
        self.datos_del_certificado = self.__obtener_datos_del_certificado()

    def __generar_nombre_archivo_temporal(self):
        return datetime.now().strftime("%Y%m%d%H%M%S%f")

    def __crear_archivo_temporal(self, bytes_to_write: bytes, extension: str):
        directorio = os.path.join(MEDIA_ROOT, 'archivos_temporales')
        not os.path.exists(directorio) and os.mkdir(directorio)
        path_archivo_temporal = os.path.join(directorio, f"{self.__generar_nombre_archivo_temporal()}.{extension}")
        while os.path.exists(path_archivo_temporal):
            path_archivo_temporal = os.path.join(directorio, self.__generar_nombre_archivo_temporal())
        io_archivo_temporal = open(path_archivo_temporal, "wb")
        io_archivo_temporal.write(bytes_to_write)
        io_archivo_temporal.close()
        return path_archivo_temporal

    def guardar_archivo_a_firmar_en_el_disco_and_get_path(self) -> str:
        bytes_archivo = self.archivo_a_firmar.read() if type(self.archivo_a_firmar).__name__.lower() != "bytes" else self.archivo_a_firmar
        return self.__crear_archivo_temporal(bytes_archivo, self.type_file.lower())

    def guardar_archivo_certificado_en_el_disco_and_get_path(self) -> str:
        bytes_archivo = self.archivo_certificado.read() if type(self.archivo_certificado).__name__.lower() != "bytes" else self.archivo_certificado
        return self.__crear_archivo_temporal(bytes_archivo, self.extension_certificado)

    def __validar_certificado(self):
        try:
            p12 = pkcs12.load_key_and_certificates(self.archivo_certificado,  self.password_certificado.encode("ascii"), default_backend())
            fecha_emision = p12[1].not_valid_before
            fecha_expiracion = p12[1].not_valid_after
            if datetime.now().date() >= fecha_expiracion.date():
                lista = []
                for c in p12[2]:
                    if c.not_valid_before >= fecha_emision and c.not_valid_after >= fecha_expiracion:
                        lista.append(c.not_valid_after)
                if lista:
                    fecha_expiracion = max(lista)
                if datetime.now().date() >= fecha_expiracion.date():
                    return False
            return self.datos_del_certificado["certificadoDigitalValido"]
        except Exception as ex:
            raise ValueError(f"Error al validar el certificado: {ex}")

    def __obtener_datos_del_certificado(self):
        datos_del_certificado = {}
        path_certificate = self.guardar_archivo_certificado_en_el_disco_and_get_path()
        try:
            jar_file = self.jar_file
            java_path = self.java_path
            completed_process = subprocess.run(
                [
                    java_path, "-jar", jar_file, "-path_certificate", path_certificate,
                    "-password_certificate", self.password_certificado, "-type_file", "validar_certificado"
                ], timeout=10000, text=True,
                capture_output=True
            )
            if not completed_process.stdout:
                raise ValueError(f"La API de firma EC está fuera de servicio. No es posible firmar documentos en este momento.")
            datos_del_certificado = json.loads(completed_process.stdout)
        except subprocess.TimeoutExpired:
            raise ValueError("El proceso de validación del certificado ha superado el tiempo de espera.")
        except json.JSONDecodeError:
            raise ValueError("La respuesta de la API de firma EC no es un JSON válido.")
        except Exception as ex:
            raise ValueError(f"Error al obtener datos del certificado: {ex}")
        finally:
            os.remove(path_certificate)
        return datos_del_certificado

    def sign_and_get_content_bytes(self):
        certificado_es_valido = self.__validar_certificado()

        if not certificado_es_valido:
            raise ValueError("Certificado no es válido")

        path_file_to_sign = self.guardar_archivo_a_firmar_en_el_disco_and_get_path()
        path_certificate = self.guardar_archivo_certificado_en_el_disco_and_get_path()
        path_signed_file = ""

        try:
            jar_file = self.jar_file
            java_path = self.java_path
            completed_process = subprocess.run(
                [
                    java_path, "-jar", jar_file, "-path_file", path_file_to_sign, "-path_certificate", path_certificate,
                    "-password_certificate", self.password_certificado, "-page", self.page, "-type_file",
                    self.type_file, "-lx", self.lx, "-ly", self.ly, "-type_sign", self.type_sign
                ] + (["-reason",
                    self.reason] if self.reason else []), timeout=10000, text=True,
                capture_output=True
            )
            if completed_process.returncode != 0:
                raise ValueError(f"Error en el proceso de firma: {completed_process.stderr}")
            data = json.loads(completed_process.stdout)
            path_signed_file = data["path_signed_file"]
            archivo_firmado = open(path_signed_file, "rb").read()
            return archivo_firmado
        except subprocess.TimeoutExpired:
            raise ValueError("El proceso de firma ha superado el tiempo de espera.")
        except json.JSONDecodeError:
            raise ValueError("La respuesta de la API de firma EC no es un JSON válido.")
        except Exception as ex:
            raise ValueError(f"Error al firmar el documento: {ex}")
        finally:
            os.remove(path_file_to_sign)
            os.remove(path_certificate)
            path_signed_file and os.remove(path_signed_file)