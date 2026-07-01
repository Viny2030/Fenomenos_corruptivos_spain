import os
import shutil
import webbrowser
import urllib.request
import zipfile
from fpdf import FPDF
from fpdf.enums import XPos, YPos


class PDFRepositorio(FPDF):
    def header(self):
        if self.page_no() > 1:
            self.set_font("Helvetica", "I", 8)
            self.set_text_color(113, 128, 150)
            self.cell(0, 10, "Documentacion de Codigo Fuente", align="L",
                      new_x=XPos.LMARGIN, new_y=YPos.NEXT)
            self.ln(5)

    def footer(self):
        self.set_y(-15)
        self.set_font("Helvetica", "I", 9)
        self.set_text_color(113, 128, 150)
        self.cell(0, 10, f"Pagina {self.page_no()}", align="R")


def exportar_repo_a_pdf_via_zip(url_repo, archivo_salida="reporte_codigo.pdf"):
    nombre_repo = url_repo.split("/")[-1]
    ruta_zip = os.path.join(os.getcwd(), "repo_descargado.zip")
    ruta_extraccion = os.path.join(os.getcwd(), "repo_extraido_temp")

    # Limpieza previa de carpetas temporales anteriores
    for ruta in [ruta_extraccion, os.path.join(os.getcwd(), f"temp_{nombre_repo}")]:
        if os.path.exists(ruta):
            try:
                shutil.rmtree(ruta, ignore_errors=True)
            except Exception:
                pass

    # 1. Descargar el repositorio directamente en formato ZIP desde GitHub
    print("📥 Descargando el repositorio desde GitHub en formato ZIP...")
    url_zip = url_repo.rstrip('/') + "/archive/refs/heads/main.zip"
    try:
        urllib.request.urlretrieve(url_zip, ruta_zip)
    except Exception:
        try:
            url_zip = url_repo.rstrip('/') + "/archive/refs/heads/master.zip"
            urllib.request.urlretrieve(url_zip, ruta_zip)
        except Exception as e:
            print(f"❌ No se pudo descargar el repositorio. Detalle: {e}")
            return

    # 2. Extraer el archivo ZIP
    print("📦 Extrayendo archivos...")
    try:
        with zipfile.ZipFile(ruta_zip, 'r') as zip_ref:
            zip_ref.extractall(ruta_extraccion)
    except Exception as e:
        print(f"❌ Error al extraer el archivo ZIP: {e}")
        return
    finally:
        if os.path.exists(ruta_zip):
            os.remove(ruta_zip)

    # Buscar la carpeta real extraída
    carpetas_dentro = os.listdir(ruta_extraccion)
    if not carpetas_dentro:
        print("❌ La extraccion fallo o el repositorio esta vacio.")
        return

    ruta_codigo_real = os.path.join(ruta_extraccion, carpetas_dentro[0])

    # Extensiones a incluir (puedes añadir más si las necesitas)
    extensiones_validas = ('.py', '.md', '.json', '.html', '.css', '.sql', '.csv', '.js', '.txt')

    # Inicializar PDF
    pdf = PDFRepositorio()
    pdf.set_auto_page_break(auto=True, margin=20)

    # --- PORTADA ---
    pdf.add_page()
    pdf.set_font("Helvetica", "B", 26)
    pdf.set_text_color(26, 54, 93)
    pdf.ln(80)
    pdf.cell(0, 15, "Estructura y Codigo Fuente", align="C", new_x=XPos.LMARGIN, new_y=YPos.NEXT)

    pdf.set_font("Helvetica", "", 14)
    pdf.set_text_color(74, 85, 104)
    pdf.cell(0, 10, f"Repositorio: {nombre_repo}", align="C", new_x=XPos.LMARGIN, new_y=YPos.NEXT)
    pdf.cell(0, 10, "Exportacion Automatizada a PDF", align="C", new_x=XPos.LMARGIN, new_y=YPos.NEXT)

    print("📄 Procesando e insertando archivos en el PDF...")
    archivos_procesados = 0

    for raiz, dirs, archivos in os.walk(ruta_codigo_real):
        # Ignorar carpetas ocultas, de entornos virtuales o de dependencias comunes
        dirs[:] = [d for d in dirs if
                   not any(x in d.lower() for x in ('venv', '.git', '.idea', '__pycache__', 'node_modules'))]

        for archivo in sorted(archivos):
            if archivo.endswith(extensiones_validas):
                ruta_completa = os.path.join(raiz, archivo)
                ruta_relativa = os.path.relpath(ruta_completa, ruta_codigo_real)

                archivos_procesados += 1
                pdf.add_page()

                # Encabezado del archivo en el PDF
                pdf.set_font("Courier", "B", 11)
                pdf.set_fill_color(247, 250, 252)
                pdf.set_text_color(43, 108, 176)
                pdf.cell(0, 10, f"  ARCHIVO: {ruta_relativa}", border="B", fill=True, new_x=XPos.LMARGIN,
                         new_y=YPos.NEXT)
                pdf.ln(5)

                # Código fuente
                pdf.set_font("Courier", "", 9)
                pdf.set_text_color(45, 55, 72)

                try:
                    with open(ruta_completa, 'r', encoding='utf-8', errors='ignore') as f:
                        codigo = f.read()

                    # Limpieza de caracteres que no son compatibles con fuentes estandar en fpdf2
                    codigo_limpio = codigo.encode('latin-1', 'replace').decode('latin-1')
                    pdf.multi_cell(0, 5, codigo_limpio)
                except Exception as e:
                    pdf.set_text_color(255, 0, 0)
                    pdf.multi_cell(0, 5, f"[ERROR: No se pudo leer el archivo. Detalle: {e}]")

    # Guardar archivo PDF final
    pdf.output(archivo_salida)

    # Limpieza final de la carpeta de extracción
    try:
        shutil.rmtree(ruta_extraccion, ignore_errors=True)
    except Exception:
        pass

    print(f"✅ ¡Proceso terminado exitosamente!")
    print(f"📊 Total de archivos añadidos al documento: {archivos_procesados}")
    print(f"📕 Archivo guardado como: '{archivo_salida}'")

    webbrowser.open(f"file://{os.path.abspath(archivo_salida)}")


if __name__ == "__main__":
    # Nueva URL asignada
    url_github = "https://github.com/Viny2030/Fenomenos_corruptivos_spain"
    exportar_repo_a_pdf_via_zip(url_repo=url_github)