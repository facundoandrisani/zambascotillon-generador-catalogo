import streamlit as st
import pandas as pd
import zipfile
import os
import io
import streamlit.components.v1 as components

# --- IMPORTACIÓN SEGURA DE WEASYPRINT ---
try:
    from weasyprint import HTML
    WEASYPRINT_OK = True
except Exception as e:
    WEASYPRINT_OK = False

# --- 1. CONFIGURACIÓN DE LA PÁGINA ---
st.set_page_config(page_title="Generador de Catálogos", layout="wide")
st.title("Generador Automático de Catálogos PDF")

if not WEASYPRINT_OK:
    st.info("Aviso Windows: GTK3 no está instalado localmente. Podés diseñar y ver la Vista Previa en pantalla a la perfección. Para habilitar la descarga del archivo PDF en tu PC, consultá las instrucciones de instalación de GTK3.")

# --- 2. BARRA LATERAL: PERSONALIZACIÓN VISUAL Y ESTRUCTURA ---
with st.sidebar:
    st.header("Diseño del Catálogo")
    titulo_pdf = st.text_input("Título / Marca principal", value="CARIOCA")
    
    st.subheader("Estructura de Página")
    num_cols = st.slider("Productos por fila (Columnas)", min_value=2, max_value=4, value=3)
    num_rows = st.slider("Filas por página", min_value=1, max_value=4, value=2)
    prods_por_pagina = num_cols * num_rows
    st.info(f"Total: {prods_por_pagina} productos por hoja A4.")

    st.subheader("Colores y Estilo")
    color_precio = st.color_picker("Color etiqueta de precio", value="#FF477E")
    color_linea = st.color_picker("Color línea divisoria", value="#CCCCCC")
    
    modo_fondo = st.selectbox(
        "Estilo de fondo de imágenes",
        ["Pastel Variado (como la muestra)", "Color Único Personalizado", "Blanco / Sin Fondo"]
    )
    
    color_fondo_tarjeta = "#FDEEF0"
    if modo_fondo == "Color Único Personalizado":
        color_fondo_tarjeta = st.color_picker("Elegí el color de fondo para las tarjetas", value="#F4F4F9")

    st.subheader("Elementos a Mostrar")
    mostrar_sku = st.checkbox("Mostrar SKU / Código", value=True)
    mostrar_stock = st.checkbox("Mostrar estado de Stock", value=True)

# Paleta de colores pastel alternados
PASTEL_COLORS = [
    "#FDEEF0", "#EEF2FD", "#EDF7ED", "#FFF5EA", "#F5EEFA", "#EBF7F8"
]

# --- 3. FUNCIONES AUXILIARES ---
def buscar_foto_local(sku, carpeta_base):
    if not os.path.exists(carpeta_base):
        return "https://via.placeholder.com/200?text=Sin+Foto"
    for root, _, archivos in os.walk(carpeta_base):
        for archivo in archivos:
            if str(os.path.splitext(archivo)[0]).lower() == str(sku).lower():
                return f"file://{os.path.abspath(os.path.join(root, archivo))}"
    return "https://via.placeholder.com/200?text=Sin+Foto"

def format_precio(valor):
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

# --- 5. PROCESAMIENTO ---
if archivo_stock and archivo_precio:
    carpeta_img = "temp_imagenes"
    if archivo_zip:
        with zipfile.ZipFile(archivo_zip, 'r') as zip_ref:
            zip_ref.extractall(carpeta_img)

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

    st.success(f"¡Datos procesados! {len(df_catalogo)} productos listos.")

    # Multiselect de rubros
    rubros_disponibles = list(df_catalogo['Rubro'].unique())
    rubros_elegidos = st.multiselect(
        "Seleccioná el o los rubros a incluir en el catálogo:",
        options=rubros_disponibles,
        default=rubros_disponibles
    )

    if not rubros_elegidos:
        st.warning("Seleccioná al menos un rubro para generar el catálogo.")
    else:
        df_exportar = df_catalogo[df_catalogo['Rubro'].isin(rubros_elegidos)]

        # --- GENERACIÓN DEL HTML ---
        box_height = "165px" if num_rows <= 2 else "120px"
        circle_size = "115px" if num_rows <= 2 else "85px"

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
                background-color: #f0f2f5;
            }}
            .pagina {{
                background-color: #ffffff;
                width: 210mm;
                min-height: 297mm;
                margin: 0 auto 25px auto;
                padding: 10mm 12mm;
                box-shadow: 0 4px 15px rgba(0,0,0,0.1);
                box-sizing: border-box;
                page-break-after: always;
            }}
            .header-cat {{
                text-align: center;
                margin-bottom: 15px;
                padding-bottom: 8px;
                border-bottom: 2px dashed {color_linea};
            }}
            .header-cat h1 {{
                font-size: 20px;
                font-weight: 800;
                letter-spacing: 4px;
                text-transform: uppercase;
                color: #111111;
                margin: 0;
            }}
            .grilla {{
                display: grid;
                grid-template-columns: repeat({num_cols}, 1fr);
                gap: 16px 12px;
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
                height: {box_height};
                border-radius: 12px;
                display: flex;
                align-items: center;
                justify-content: center;
                margin-bottom: 8px;
            }}
            .circulo-imagen {{
                width: {circle_size};
                height: {circle_size};
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
                font-size: 10px;
                font-weight: 700;
                text-transform: uppercase;
                color: #111111;
                line-height: 1.2;
                height: 2.4em;
                overflow: hidden;
                margin-bottom: 3px;
                padding: 0 2px;
            }}
            .sku {{
                font-size: 9px;
                color: #555555;
                font-weight: 600;
                margin-bottom: 2px;
            }}
            .stock-verde {{
                color: #2b8a3e;
                font-weight: 700;
                font-size: 9px;
                margin-bottom: 6px;
            }}
            .stock-naranja {{
                color: #e65100;
                font-weight: 700;
                font-size: 9px;
                margin-bottom: 6px;
            }}
            .precio-pill {{
                background-color: {color_precio};
                color: #ffffff;
                font-size: 14px;
                font-weight: 800;
                padding: 4px 14px;
                border-radius: 20px;
                display: inline-block;
                box-shadow: 0 4px 8px rgba(0, 0, 0, 0.12);
            }}
        </style>
        """

        html = f'<!DOCTYPE html><html><head><meta charset="utf-8">{css}</head><body>'

        for rubro, df_rubro in df_exportar.groupby('Rubro'):
            productos = list(df_rubro.iterrows())
            for page_idx in range(0, len(productos), prods_por_pagina):
                chunk_productos = productos[page_idx:page_idx + prods_por_pagina]
                
                html += '<div class="pagina">'
                header_title = f"{titulo_pdf} - {rubro}" if titulo_pdf else rubro
                html += f'<div class="header-cat"><h1>{header_title}</h1></div>'
                html += '<div class="grilla">'
                
                for prod_idx, (_, row) in enumerate(chunk_productos):
                    sku_str = str(row['SKU']).strip()
                    src_imagen = buscar_foto_local(sku_str, carpeta_img)
                    precio_fmt = format_precio(row['Precio'])
                    
                    if modo_fondo == "Pastel Variado (como la muestra)":
                        bg_color = PASTEL_COLORS[(page_idx + prod_idx) % len(PASTEL_COLORS)]
                    elif modo_fondo == "Color Único Personalizado":
                        bg_color = color_fondo_tarjeta
                    else:
                        bg_color = "#FFFFFF"
                    
                    # Texto de stock limpio sin emojis / stickers
                    if row['Stock'] > 10:
                        clase_stock, txt_stock = "stock-verde", "Stock Disponible"
                    else:
                        clase_stock, txt_stock = "stock-naranja", "¡Últimas unidades!"

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
                html += '</div></div>'
        html += '</body></html>'

        # --- PESTAÑAS DE VISTA PREVIA Y DESCARGA ---
        tab_prev, tab_pdf = st.tabs(["Vista Previa en Pantalla", "Descargar PDF"])

        with tab_prev:
            st.caption("Resumen en vivo de tus hojas A4 (Podés ajustar los colores y columnas en la izquierda):")
            components.html(html, height=900, scrolling=True)

        with tab_pdf:
            if WEASYPRINT_OK:
                if st.button("Generar y Descargar PDF"):
                    pdf_buffer = io.BytesIO()
                    HTML(string=html).write_pdf(pdf_buffer)
                    pdf_buffer.seek(0)
                    st.download_button(
                        label="Guardar PDF en mi equipo",
                        data=pdf_buffer,
                        file_name="Catalogo_Personalizado.pdf",
                        mime="application/pdf"
                    )
            else:
                st.error("Para descargar el archivo .pdf en tu PC de Windows, instalá GTK3. En la nube (Streamlit Cloud) funcionará automáticamente.")
