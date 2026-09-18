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
    titulo_pdf = st.text_input("Título principal", value="Catálogo Oficial")
    color_fondo = st.color_picker("Color de encabezado", value="#004080")
    color_precio = st.color_picker("Color del precio", value="#0066cc")
    mostrar_sku = st.checkbox("Mostrar SKU", value=True)

# --- 3. CARGA DE ARCHIVOS ---
col1, col2, col3 = st.columns(3)
with col1:
    archivo_stock = st.file_uploader("1. Excel de Stock (.xlsx)", type=['xlsx'])
with col2:
    archivo_precio = st.file_uploader("2. Excel de Precios (.xls)", type=['xls', 'xlsx'])
with col3:
    archivo_zip = st.file_uploader("3. ZIP de Imágenes", type=['zip'])

# Función para buscar la foto localmente
def buscar_foto_local(sku, carpeta_base):
    if not os.path.exists(carpeta_base):
        return "https://via.placeholder.com/150?text=Sin+Foto"
    for root, _, archivos in os.walk(carpeta_base):
        for archivo in archivos:
            if str(os.path.splitext(archivo)[0]).lower() == str(sku).lower():
                return f"file://{os.path.abspath(os.path.join(root, archivo))}"
    return "https://via.placeholder.com/150?text=Sin+Foto"

# --- 4. PROCESAMIENTO Y GENERACIÓN ---
if archivo_stock and archivo_precio:
    # Descomprimir imágenes en una carpeta temporal si se subió el ZIP
    carpeta_img = "temp_imagenes"
    if archivo_zip:
        with zipfile.ZipFile(archivo_zip, 'r') as zip_ref:
            zip_ref.extractall(carpeta_img)

    # Procesar con Pandas
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

    st.success(f"¡Datos procesados! Se encontraron {len(df_catalogo)} productos en stock.")

    # Selector de Categoría
    categorias = ["Catálogo Completo"] + list(df_catalogo['Rubro'].unique())
    rubro_elegido = st.selectbox("Seleccioná el rubro a exportar:", categorias)

    if rubro_elegido == "Catálogo Completo":
        df_exportar = df_catalogo
        nombre_archivo = "Catalogo_Completo.pdf"
    else:
        df_exportar = df_catalogo[df_catalogo['Rubro'] == rubro_elegido]
        nombre_archivo = f"Catalogo_{rubro_elegido.replace(' ', '_')}.pdf"

    # --- 5. RENDERIZADO DEL PDF ---
    if st.button("Generar PDF"):
        with st.spinner('Ensamblando el PDF, por favor esperá...'):
            css = f"""
            <style>
                body {{ font-family: Arial, sans-serif; color: #333; margin: 0; padding: 15px; }}
                .encabezado {{ text-align: center; background: {color_fondo}; color: white; padding: 15px; border-radius: 8px; margin-bottom: 20px; }}
                .titulo-cat {{ background: #f0f0f0; color: {color_fondo}; padding: 10px; border-left: 5px solid {color_fondo}; margin: 20px 0; page-break-after: avoid; }}
                .seccion:not(:first-child) {{ page-break-before: always; }} 
                .grilla {{ display: grid; grid-template-columns: repeat(3, 1fr); gap: 15px; }}
                .tarjeta {{ border: 1px solid #ddd; border-radius: 10px; padding: 15px; text-align: center; page-break-inside: avoid; }}
                .imagen-producto {{ width: 100%; height: 130px; object-fit: contain; margin-bottom: 10px; }}
                .titulo {{ font-size: 12px; height: 30px; overflow: hidden; font-weight: bold; }}
                .precio {{ font-size: 20px; color: {color_precio}; font-weight: bold; margin: 10px 0; }}
                .sku {{ font-size: 10px; color: #666; margin-bottom: 5px; }}
                .stock-verde {{ color: #2e8b57; font-weight: bold; font-size: 11px; }}
                .stock-naranja {{ color: #d2691e; font-weight: bold; font-size: 11px; }}
            </style>
            """

            html = f'<!DOCTYPE html><html><head><meta charset="utf-8">{css}</head><body>'
            html += f'<div class="encabezado"><h1>{titulo_pdf}</h1><p>{rubro_elegido}</p></div>'

            for rubro, df_rubro in df_exportar.groupby('Rubro'):
                html += '<div class="seccion">'
                if rubro_elegido == "Catálogo Completo": 
                    html += f'<h2 class="titulo-cat">{rubro}</h2>'
                    
                html += '<div class="grilla">'
                
                for _, row in df_rubro.iterrows():
                    clase_stock, txt_stock = ("stock-verde", "Stock Disponible") if row['Stock'] > 10 else ("stock-naranja", "Últimas unidades")
                    sku_str = str(row['SKU']).strip()
                    src_imagen = buscar_foto_local(sku_str, carpeta_img)
                    
                    html += f"""
                    <div class="tarjeta">
                        <img class="imagen-producto" src="{src_imagen}">
                        <div class="titulo">{row['Nombre']}</div>
                        <div class="precio">${row['Precio']:.2f}</div>"""
                    
                    if mostrar_sku:
                        html += f'<div class="sku">SKU: {sku_str}</div>'
                        
                    html += f"""
                        <div class="{clase_stock}">{txt_stock}</div>
                    </div>"""
                    
                html += '</div></div>'
            html += '</body></html>'

            # Guardar el PDF en memoria en lugar de disco
            pdf_buffer = io.BytesIO()
            HTML(string=html).write_pdf(pdf_buffer)
            pdf_buffer.seek(0)

            st.download_button(
                label="📥 Descargar Catálogo Generado",
                data=pdf_buffer,
                file_name=nombre_archivo,
                mime="application/pdf"
            )