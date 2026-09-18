import streamlit as st
import pandas as pd
import zipfile
import os
import io
from weasyprint import HTML

# --- 1. CONFIGURACIÓN DE LA PÁGINA ---
st.set_page_config(page_title="Generador de Catálogos", layout="wide")
st.title("Generador Automático de Catálogos PDF")

# --- 2. BARRA LATERAL: PERSONALIZACIÓN VISUAL ---
with st.sidebar:
    st.header("⚙️ Diseño del Catálogo")
    titulo_pdf = st.text_input("Título / Marca principal", value="CARIOCA")
    color_precio = st.color_picker("Color etiqueta de precio", value="#FF477E")
    color_linea = st.color_picker("Color línea divisoria", value="#CCCCCC")
    mostrar_sku = st.checkbox("Mostrar SKU / Código", value=True)
    mostrar_stock = st.checkbox("Mostrar estado de Stock", value=True)
    usar_pastel = st.checkbox("Usar fondos pastel en tarjetas", value=True)

# Paleta de colores pastel para rotar en las cajas de productos
PASTEL_COLORS = [
    "#FDEEF0",  # Soft Pink
    "#EEF2FD",  # Soft Blue
    "#EDF7ED",  # Soft Green
    "#FFF5EA",  # Soft Yellow
    "#F5EEFA",  # Soft Purple
    "#EBF7F8"   # Soft Mint
]

# --- 3. FUNCIONES AUXILIARES ---
def buscar_foto_local(sku, carpeta_base):
    """Busca la imagen del producto por SKU en la carpeta descomprimida."""
    if not os.path.exists(carpeta_base):
        return "https://via.placeholder.com/200?text=Sin+Foto"
    for root, _, archivos in os.walk(carpeta_base):
        for archivo in archivos:
            if str(os.path.splitext(archivo)[0]).lower() == str(sku).lower():
                return f"file://{os.path.abspath(os.path.join(root, archivo))}"
    return "https://via.placeholder.com/200?text=Sin+Foto"

def format_precio(valor):
    """Formatea números a formato de moneda con punto de mil y coma decimal ($1.044,00)."""
    try:
        return f"${valor:,.2f}".replace(',', 'X').replace('.', ',').replace('X', '.')
    except:
        return f"${valor}"

# --- 4. CARGA DE ARCHIVOS ---
col1, col2, col3 = st.columns(3)
with col1:
    archivo_stock = st.file_uploader("1. Excel de Stock (.xlsx)", type=['xlsx'])
with col2:
    archivo_precio = st.file_uploader("2. Excel de Precios (.xls / .xlsx)", type=['xls', 'xlsx'])
with col3:
    archivo_zip = st.file_uploader("3. ZIP de Imágenes", type=['zip'])

# --- 5. PROCESAMIENTO Y GENERACIÓN ---
if archivo_stock and archivo_precio:
    carpeta_img = "temp_imagenes"
    if archivo_zip:
        with zipfile.ZipFile(archivo_zip, 'r') as zip_ref:
            zip_ref.extractall(carpeta_img)

    # Procesar dataframes
    df_stock = pd.read_excel(archivo_stock, header=2)
    df_precio = pd.read_excel(archivo_precio, header=6)

    df_stock['SKU'] = df_stock['Código Producto'].astype(str).str.strip()
    df_precio['SKU'] = df_precio['Código'].astype(str).str.strip()
    df_stock['Rubro'] = df_stock['Rubro'].fillna('Otras Categorías').astype(str).str.title()
    df_stock['Stock Disponible'] = pd.to_numeric(df_stock['Stock Disponible'], errors='coerce').fillna(0)
    df_stock_pos = df_stock[df_stock['Stock Disponible'] > 0]

    df_catalogo = pd.merge(df_precio, df_stock_pos[['SKU', 'Stock Disponible', 'Rubro']], on='SKU', how='inner')
    df_catalogo = df_catalogo.rename(columns={'Producto': 'Nombre', 'Precio De Venta Con IVA($)': 'Precio', 'Stock Disponible': 'Stock'})
    df_catalogo = df_catalogo.sort_values(by=['Rubro', 'Nombre'])

    st.success(f"¡Datos procesados con éxito! Se encontraron {len(df_catalogo)} productos con stock activo.")

    # Selector de Rubro
    categorias = ["Catálogo Completo"] + list(df_catalogo['Rubro'].unique())
    rubro_elegido = st.selectbox("Seleccioná el rubro a exportar:", categorias)

    if rubro_elegido == "Catálogo Completo":
        df_exportar = df_catalogo
        nombre_archivo = "Catalogo_Completo.pdf"
    else:
        df_exportar = df_catalogo[df_catalogo['Rubro'] == rubro_elegido]
        nombre_archivo = f"Catalogo_{rubro_elegido.replace(' ', '_')}.pdf"

    # --- 6. GENERACIÓN DEL PDF ESTILIZADO ---
    if st.button("🚀 Generar PDF de Alta Calidad"):
        with st.spinner('Ensamblando el PDF, por favor esperá unos segundos...'):
            css = f"""
            <style>
                @page {{
                    size: A4 portrait;
                    margin: 10mm 12mm 12mm 12mm;
                }}
                body {{
                    font-family: 'Helvetica Neue', Helvetica, Arial, sans-serif;
                    color: #111111;
                    margin: 0;
                    padding: 0;
                    background-color: #ffffff;
                }}
                .pagina {{
                    page-break-after: always;
                    height: 100%;
                    box-sizing: border-box;
                }}
                .pagina:last-child {{
                    page-break-after: avoid;
                }}
                .header-cat {{
                    text-align: center;
                    margin-bottom: 18px;
                    padding-bottom: 10px;
                    border-bottom: 2px dashed {color_linea};
                }}
                .header-cat h1 {{
                    font-size: 22px;
                    font-weight: 800;
                    letter-spacing: 5px;
                    text-transform: uppercase;
                    color: #111111;
                    margin: 0;
                }}
                .grilla {{
                    display: grid;
                    grid-template-columns: repeat(3, 1fr);
                    gap: 22px 14px;
                }}
                .tarjeta {{
                    text-align: center;
                    display: flex;
                    flex-direction: column;
                    align-items: center;
                    page-break-inside: avoid;
                }}
                .box-imagen {{
                    width: 100%;
                    height: 165px;
                    border-radius: 12px;
                    display: flex;
                    align-items: center;
                    justify-content: center;
                    margin-bottom: 10px;
                }}
                .circulo-imagen {{
                    width: 115px;
                    height: 115px;
                    border-radius: 50%;
                    background: #ffffff;
                    box-shadow: 0 4px 10px rgba(0, 0, 0, 0.04);
                    display: flex;
                    align-items: center;
                    justify-content: center;
                    overflow: hidden;
                }}
                .imagen-producto {{
                    max-width: 80%;
                    max-height: 80%;
                    object-fit: contain;
                }}
                .titulo {{
                    font-size: 11px;
                    font-weight: 700;
                    text-transform: uppercase;
                    color: #111111;
                    line-height: 1.25;
                    height: 2.5em;
                    overflow: hidden;
                    margin-bottom: 4px;
                    padding: 0 4px;
                }}
                .sku {{
                    font-size: 10px;
                    color: #555555;
                    font-weight: 600;
                    margin-bottom: 3px;
                }}
                .stock-verde {{
                    color: #2b8a3e;
                    font-weight: 700;
                    font-size: 10px;
                    margin-bottom: 8px;
                }}
                .stock-naranja {{
                    color: #e65100;
                    font-weight: 700;
                    font-size: 10px;
                    margin-bottom: 8px;
                }}
                .precio-pill {{
                    background-color: {color_precio};
                    color: #ffffff;
                    font-size: 15px;
                    font-weight: 800;
                    padding: 5px 18px;
                    border-radius: 20px;
                    display: inline-block;
                    box-shadow: 0 4px 8px rgba(0, 0, 0, 0.12);
                    margin-top: 4px;
                }}
            </style>
            """

            html = f'<!DOCTYPE html><html><head><meta charset="utf-8">{css}</head><body>'

            # Agrupar por rubro y paginar de a 6 productos (3 columnas x 2 filas)
            for rubro, df_rubro in df_exportar.groupby('Rubro'):
                productos = list(df_rubro.iterrows())
                # Bloques de 6 productos por hoja
                for page_idx in range(0, len(productos), 6):
                    chunk_productos = productos[page_idx:page_idx + 6]
                    
                    html += '<div class="pagina">'
                    
                    # Encabezado por hoja
                    header_title = titulo_pdf if titulo_pdf else rubro
                    html += f'<div class="header-cat"><h1>{header_title}</h1></div>'
                    
                    html += '<div class="grilla">'
                    
                    for prod_idx, (_, row) in enumerate(chunk_productos):
                        sku_str = str(row['SKU']).strip()
                        src_imagen = buscar_foto_local(sku_str, carpeta_img)
                        precio_fmt = format_precio(row['Precio'])
                        
                        # Asignar color pastel alternado
                        bg_color = PASTEL_COLORS[(page_idx + prod_idx) % len(PASTEL_COLORS)] if usar_pastel else "#F9F9F9"
                        
                        # Estado del stock
                        if row['Stock'] > 10:
                            clase_stock, txt_stock = "stock-verde", "✔ Stock Disponible"
                        else:
                            clase_stock, txt_stock = "stock-naranja", "⚡ ¡Últimas unidades!"

                        html += f"""
                        <div class="tarjeta">
                            <div class="box-imagen" style="background-color: {bg_color};">
                                <div class="circulo-imagen">
                                    <img class="imagen-producto" src="{src_imagen}">
                                </div>
                            </div>
                            <div class="titulo">{row['Nombre']}</div>
                        """
                        
                        if mostrar_sku:
                            html += f'<div class="sku">COD: {sku_str}</div>'
                            
                        if mostrar_stock:
                            html += f'<div class="{clase_stock}">{txt_stock}</div>'
                            
                        html += f"""
                            <div class="precio-pill">{precio_fmt}</div>
                        </div>
                        """
                        
                    html += '</div></div>' # Cierra grilla y página

            html += '</body></html>'

            # Generación en memoria con WeasyPrint
            pdf_buffer = io.BytesIO()
            HTML(string=html).write_pdf(pdf_buffer)
            pdf_buffer.seek(0)

            st.download_button(
                label="📥 Descargar Catálogo Generado en PDF",
                data=pdf_buffer,
                file_name=nombre_archivo,
                mime="application/pdf"
            )
