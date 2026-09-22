import streamlit as st
import pandas as pd
import zipfile
import os
import io
import base64
import streamlit.components.v1 as components

# --- IMPORTACIÓN SEGURA DE WEASYPRINT ---
try:
    from weasyprint import HTML
    WEASYPRINT_OK = True
except Exception:
    WEASYPRINT_OK = False

# --- CONFIGURACIÓN DE PÁGINA ---
st.set_page_config(page_title="Generador de Catálogos - ZAMBAS", layout="wide")

# --- CARGAR ARCHIVO DE ESTILOS CSS EXTERNO DE FORMA SEGURA ---
def cargar_css():
    ruta_css = os.path.join(os.path.dirname(__file__), "style.css")
    if os.path.exists(ruta_css):
        with open(ruta_css, "r", encoding="utf-8") as f:
            st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html=True)

cargar_css()

# --- CARGAR LOGO DE FORMA RELATIVA ---
dir_base = os.path.dirname(__file__)
posibles_logos = [
    os.path.join(dir_base, "logo.png"),
    os.path.join(dir_base, "assets", "logo.png"),
    os.path.join(dir_base, "logo.jpg")
]

LOGO_B64 = ""
PATH_LOGO_VALIDO = None

for p in posibles_logos:
    if os.path.exists(p):
        PATH_LOGO_VALIDO = p
        with open(p, "rb") as f:
            LOGO_B64 = f"data:image/png;base64,{base64.b64encode(f.read()).decode('utf-8')}"
        break

# Encabezado de la App
col_h1, col_h2 = st.columns([1, 6])
with col_h1:
    if PATH_LOGO_VALIDO:
        st.image(PATH_LOGO_VALIDO, width=105)
with col_h2:
    st.title("Generador Automático de Catálogos PDF")
    st.caption("Zambas Cotillon")

if not WEASYPRINT_OK:
    st.info("Aviso Windows: Podés diseñar y ver la Vista Previa en pantalla a la perfección. Para descargar el PDF en tu PC local, instalá GTK3 para Windows.")

# --- 1. BARRA LATERAL CON CONTROLES (IZQUIERDA) ---
st.sidebar.title("Personalización")

with st.sidebar.expander("1. Plantilla y Preset", expanded=True):
    template_elegido = st.selectbox(
        "Estilo de partida:",
        ["Zambas Oficial", "Grilla Comercial (Pastel)", "Editorial Magazine (Verde / Serif)", "Minimalista Lujo (Moderno)"]
    )

with st.sidebar.expander("2. Página de Portada", expanded=False):
    incluir_portada = st.checkbox("Incluir página de Portada", value=True)
    subtitulo_portada = "Catálogo Oficial de Productos"
    archivo_portada = None
    modo_img_portada = "Centrada Destacada"
    
    if incluir_portada:
        subtitulo_portada = st.text_input("Subtítulo / Bajada", value="Catálogo Oficial de Productos")
        archivo_portada = st.file_uploader("Imagen / Logo de Portada (Opcional)", type=['png', 'jpg', 'jpeg'])
        modo_img_portada = st.selectbox("Ajuste de Imagen de Portada:", ["Centrada Destacada", "Fondo Completo (Full Bleed)", "Sin Imagen"])

with st.sidebar.expander("3. Colores del Catálogo", expanded=False):
    color_fondo_hoja = st.color_picker("Fondo de la Hoja (A4)", value="#FFFFFF")
    color_texto_principal = st.color_picker("Títulos y Textos", value="#1A1A1A")
    color_precio_bg = st.color_picker("Color Principal / Botón Precio", value="#F29F05")
    color_precio_txt = st.color_picker("Texto del Precio", value="#FFFFFF")
    
    modo_fondo_tarjetas = st.selectbox(
        "Fondo de Cajas de Foto",
        ["Pastel Variado (como la muestra)", "Color Único Personalizado", "Blanco / Transparente"]
    )
    color_tarjeta_custom = st.color_picker("Color de Cajas de Foto", value="#FFF9F2") if modo_fondo_tarjetas == "Color Único Personalizado" else "#FFF9F2"

with st.sidebar.expander("4. Grilla, Orientación y Fotos", expanded=False):
    orientacion = st.radio("Orientación de Hoja:", ["Vertical (Portrait)", "Horizontal (Landscape)"])
    page_orientation_css = "portrait" if "Vertical" in orientacion else "landscape"
    
    num_cols = st.slider("Productos por fila (Columnas)", 1, 4, 3)
    num_rows = st.slider("Filas por página", 1, 4, 2)
    prods_por_pagina = num_cols * num_rows

    usar_circulo_foto = st.checkbox("Círculo contenedor blanco en la foto", value=True)
    mostrar_logo_header = st.checkbox("Mostrar Logo en encabezados de hoja", value=True)
    fit_imagen = st.selectbox("Ajuste de Fotos de Producto", ["Ajustar sin cortar (Contain)", "Rellenar recuadro (Cover)"])
    object_fit_css = "contain" if "Contain" in fit_imagen else "cover"

with st.sidebar.expander("5. Visibilidad de Elementos", expanded=False):
    titulo_pdf = st.text_input("Título / Marca principal", value="ZAMBAS")
    mostrar_sku = st.checkbox("Mostrar SKU / Código", value=True)
    mostrar_stock = st.checkbox("Mostrar estado de Stock", value=True)
    mostrar_precio = st.checkbox("Mostrar Precio", value=True)

PASTEL_COLORS = ["#FDEEF0", "#EEF2FD", "#EDF7ED", "#FFF5EA", "#F5EEFA", "#EBF7F8"]

def obtener_imagen_base64(sku, carpeta_base):
    if os.path.exists(carpeta_base):
        for root, _, archivos in os.walk(carpeta_base):
            for archivo in archivos:
                nombre_sin_ext = str(os.path.splitext(archivo)[0]).strip().lower()
                if nombre_sin_ext == str(sku).strip().lower():
                    abs_path = os.path.join(root, archivo)
                    try:
                        with open(abs_path, "rb") as f:
                            data = f.read()
                            ext = os.path.splitext(archivo)[1].lower().replace(".", "")
                            mime = "jpeg" if ext in ["jpg", "jpeg"] else ext
                            return f"data:image/{mime};base64,{base64.b64encode(data).decode('utf-8')}"
                    except Exception:
                        pass
    return "https://via.placeholder.com/400?text=Sin+Foto"

def format_precio(valor):
    try:
        return f"${valor:,.2f}".replace(',', 'X').replace('.', ',').replace('X', '.')
    except:
        return f"${valor}"

src_portada = LOGO_B64
if archivo_portada is not None:
    b64 = base64.b64encode(archivo_portada.getvalue()).decode()
    mime = archivo_portada.type
    src_portada = f"data:{mime};base64,{b64}"

# --- LAYOUT PRINCIPAL (2 COLUMNAS) ---
col_left, col_right = st.columns([1, 1.3], gap="large")

with col_left:
    st.subheader("1. Carga de Archivos")
    archivo_stock = st.file_uploader("Excel de Stock (.xlsx)", type=['xlsx'])
    archivo_precio = st.file_uploader("Excel de Precios (.xls / .xlsx)", type=['xls', 'xlsx'])
    archivo_zip = st.file_uploader("ZIP de Imágenes", type=['zip'])

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

    todos_rubros = list(df_catalogo['Rubro'].unique())

    with col_left:
        st.subheader("2. Selección de Categorías")
        
        # --- CALLBACKS DE SELECCIÓN SIN ERRORES ---
        for r in todos_rubros:
            if f"chk_{r}" not in st.session_state:
                st.session_state[f"chk_{r}"] = True

        if 'master_toggle' not in st.session_state:
            st.session_state.master_toggle = True

        def on_master_toggle():
            val = st.session_state.master_toggle
            for r in todos_rubros:
                st.session_state[f"chk_{r}"] = val

        def on_individual_toggle():
            st.session_state.master_toggle = all(st.session_state.get(f"chk_{r}", False) for r in todos_rubros)

        st.checkbox("SELECCIONAR TODOS LOS RUBROS", key="master_toggle", on_change=on_master_toggle)
        st.markdown("---")
        
        col_c1, col_c2, col_c3 = st.columns(3)
        cols = [col_c1, col_c2, col_c3]
        
        rubros_elegidos = []
        for idx, rubro in enumerate(todos_rubros):
            with cols[idx % 3]:
                if st.checkbox(rubro, key=f"chk_{rubro}", on_change=on_individual_toggle):
                    rubros_elegidos.append(rubro)

        st.info(f"Se incluirán **{len(rubros_elegidos)}** rubros ({len(df_catalogo[df_catalogo['Rubro'].isin(rubros_elegidos)])} productos).")

    # Cargar contenido de style.css
    css_content = ""
    ruta_css_file = os.path.join(dir_base, "style.css")
    if os.path.exists(ruta_css_file):
        with open(ruta_css_file, "r", encoding="utf-8") as f:
            css_content = f.read()

    box_h = "165px" if num_rows <= 2 else "115px"
    circle_s = "110px" if num_rows <= 2 else "80px"

    dynamic_css = f"""
    {css_content}
    .grilla {{ grid-template-columns: repeat({num_cols}, 1fr) !important; }}
    .box-imagen {{ height: {box_h} !important; }}
    .circulo-imagen {{ width: {circle_s} !important; height: {circle_s} !important; }}
    .imagen-producto {{ object-fit: {object_fit_css} !important; }}
    .precio-pill {{ background: {color_precio_bg} !important; color: {color_precio_txt} !important; }}
    .header-cat {{ border-bottom-color: {color_precio_bg} !important; }}
    .pagina {{ background-color: {color_fondo_hoja} !important; color: {color_texto_principal} !important; }}
    """

    paginas_html = []
    if incluir_portada:
        if modo_img_portada == "Fondo Completo (Full Bleed)" and src_portada:
            paginas_html.append(f"""
            <div class="pagina portada portada-fullbleed" style="background-image: url('{src_portada}');">
                <div class="portada-overlay">
                    <div class="titulo-portada">{titulo_pdf}</div>
                    <div class="subtitulo-portada">{subtitulo_portada}</div>
                </div>
            </div>""")
        else:
            img_html = f'<img class="img-portada" src="{src_portada}">' if (src_portada and modo_img_portada == "Centrada Destacada") else ''
            paginas_html.append(f"""
            <div class="pagina portada">
                <div class="titulo-portada">{titulo_pdf}</div>
                <div class="subtitulo-portada">{subtitulo_portada}</div>
                {img_html}
            </div>""")

    df_exportar = df_catalogo[df_catalogo['Rubro'].isin(rubros_elegidos)]
    header_logo_tag = f'<img class="header-logo-img" src="{LOGO_B64}">' if (LOGO_B64 and mostrar_logo_header) else ''

    for rubro, df_rubro in df_exportar.groupby('Rubro'):
        productos = list(df_rubro.iterrows())
        for page_idx in range(0, len(productos), prods_por_pagina):
            chunk_productos = productos[page_idx:page_idx + prods_por_pagina]
            
            h_code = '<div class="pagina">'
            header_title = f"{titulo_pdf} — {rubro}" if titulo_pdf else rubro
            h_code += f'<div class="header-cat"><h1>{header_title}</h1>{header_logo_tag}</div>'
            h_code += '<div class="grilla">'
            
            for prod_idx, (_, row) in enumerate(chunk_productos):
                sku_str = str(row['SKU']).strip()
                src_imagen = obtener_imagen_base64(sku_str, carpeta_img)
                precio_fmt = format_precio(row['Precio'])

                if modo_fondo_tarjetas == "Pastel Variado (como la muestra)":
                    bg_color = PASTEL_COLORS[(page_idx + prod_idx) % len(PASTEL_COLORS)]
                elif modo_fondo_tarjetas == "Color Único Personalizado":
                    bg_color = color_tarjeta_custom
                else:
                    bg_color = "transparent"

                txt_stock = "Stock Disponible" if row['Stock'] > 10 else "Últimas unidades"
                clase_stock = "stock-verde" if row['Stock'] > 10 else "stock-naranja"

                h_code += '<div class="tarjeta">'
                h_code += f'<div class="box-imagen" style="background-color: {bg_color};">'
                
                if usar_circulo_foto:
                    h_code += f'<div class="circulo-imagen"><img class="imagen-producto" src="{src_imagen}"></div>'
                else:
                    h_code += f'<img class="imagen-producto" src="{src_imagen}">'
                    
                h_code += '</div>'
                h_code += f'<div class="titulo">{row["Nombre"]}</div>'
                
                if mostrar_sku:
                    h_code += f'<div class="sku">COD: {sku_str}</div>'
                if mostrar_stock:
                    h_code += f'<div class="{clase_stock}">{txt_stock}</div>'
                if mostrar_precio:
                    h_code += f'<div class="precio-pill">{precio_fmt}</div>'
                    
                h_code += '</div>'
                    
            h_code += '</div></div>'
            paginas_html.append(h_code)

    # --- COLUMNA DERECHA: VISTA PREVIA INSTANTÁNEA JS ---
    with col_right:
        st.subheader("Vista Previa en Vivo")
        
        total_hojas = len(paginas_html)
        if total_hojas == 0:
            st.warning("No hay productos seleccionados para mostrar.")
        else:
            pages_rendered = ""
            for idx, p_code in enumerate(paginas_html):
                display_style = "block" if idx == 0 else "none"
                pages_rendered += f'<div class="page-item" id="page-{idx}" style="display:{display_style};">{p_code}</div>'

            js_viewer_html = f"""
            <!DOCTYPE html>
            <html>
            <head>
                <meta charset="uDFtf-8">
                <style>{dynamic_css}</style>
            </head>
            <body>
                <div class="nav-js-bar">
                    <button class="btn-nav" onclick="prevPage()">‹ Anterior</button>
                    <div>
                        <span id="page-lbl" style="font-weight:700;">Hoja 1</span> de {total_hojas} &nbsp;
                        (Ir a: <input type="number" id="page-num-inp" class="input-jump" value="1" min="1" max="{total_hojas}" onchange="jumpTo(this.value)">)
                    </div>
                    <button class="btn-nav" onclick="nextPage()">Siguiente ›</button>
                </div>
                
                <div id="pages-container">
                    {pages_rendered}
                </div>

                <script>
                    var idxActual = 0;
                    var total = {total_hojas};

                    function updatePage(idx) {{
                        if (idx < 0) idx = 0;
                        if (idx >= total) idx = total - 1;
                        
                        for (var i = 0; i < total; i++) {{
                            var el = document.getElementById('page-' + i);
                            if (el) el.style.display = (i === idx) ? 'block' : 'none';
                        }}
                        idxActual = idx;
                        document.getElementById('page-lbl').innerText = 'Hoja ' + (idxActual + 1);
                        document.getElementById('page-num-inp').value = idxActual + 1;
                    }}

                    function prevPage() {{ updatePage(idxActual - 1); }}
                    function nextPage() {{ updatePage(idxActual + 1); }}
                    function jumpTo(val) {{ updatePage(parseInt(val) - 1); }}
                </script>
            </body>
            </html>
            """
            
            components.html(js_viewer_html, height=880, scrolling=True)

    with col_left:
        if WEASYPRINT_OK:
            if st.button("Generar y Descargar PDF Completo", type="primary"):
                html_full = f'<!DOCTYPE html><html><head><meta charset="utf-8"><style>{dynamic_css}</style></head><body>{"".join(paginas_html)}</body></html>'
                pdf_buffer = io.BytesIO()
                HTML(string=html_full).write_pdf(pdf_buffer)
                pdf_buffer.seek(0)
                st.download_button("Guardar Archivo PDF", data=pdf_buffer, file_name="Catalogo_ZAMBAS.pdf", mime="application/pdf")
