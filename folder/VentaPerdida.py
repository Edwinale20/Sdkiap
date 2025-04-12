import pandas as pd
import os
import streamlit as st
import plotly.express as px
import numpy as np
import plotly.graph_objects as go
from io import BytesIO
import requests 
import plotly.io as pio

st.set_page_config(page_title="Reporte de Venta Pérdida Cigarros y RRPS", page_icon="🚬", layout="wide", initial_sidebar_state="expanded")
st.title("📊 Reporte de Venta Perdida Cigarros y RRPS 🚬")
st.markdown("Se incluyen datos de las últimas 5 semanas.", unsafe_allow_html=True)


# Función para obtener la lista de archivos en una carpeta de GitHub con URL raw
@st.cache_data(ttl=3600)
def list_files_in_github_folder(folder_url):
    response = requests.get(folder_url)
    response.raise_for_status()  # Verifica si la solicitud fue exitosa
    files_info = response.json()

    # Obtener las raw URLs
    raw_urls = [file_info['download_url'] for file_info in files_info if file_info['type'] == 'file']
    return raw_urls

# Función para descargar y leer archivos CSV y Excel desde GitHub (raw URLs)
@st.cache_data(ttl=3600)
def download_file_from_github(url):
    response = requests.get(url)
    response.raise_for_status()  # Verifica si la solicitud fue exitosa
    return BytesIO(response.content)

# URLs de las carpetas en GitHub usando la API (sin raw aún)
csv_folder_url = 'https://api.github.com/repos/Edwinale20/Sdkiap/contents/Venta%20Perdida'
venta_semanal_folder_url = 'https://api.github.com/repos/Edwinale20/Sdkiap/contents/Venta%20semanal'
master_github_url = 'https://raw.githubusercontent.com/Edwinale20/Sdkiap/main/MASTER.xlsx'

# Obtener las URLs de los archivos CSV en la carpeta "Venta Perdida" (usando la API)
csv_files = list_files_in_github_folder(csv_folder_url)

# Descargar y leer todos los archivos CSV en un solo DataFrame con la codificación correcta
csv_dataframes = [pd.read_csv(download_file_from_github(file_url), encoding='ISO-8859-1') for file_url in csv_files]

# Obtener las URLs de los archivos Excel en la carpeta "Venta Semanal"
venta_semanal = list_files_in_github_folder(venta_semanal_folder_url)

# Cargar el archivo MASTER desde GitHub
MASTER = pd.read_excel(download_file_from_github(master_github_url))


# Definir paleta de colores global 
pio.templates["colors"] = pio.templates["plotly"]
pio.templates["colors"].layout.colorway = ['#2C7865', '#EE2526', '#FF9800', '#000000']
pio.templates["colors2"] = pio.templates["plotly"]
pio.templates["colors2"].layout.colorway = ['#2C7865', '#EE2526', '#FF9800', '#000000']
# Aplicar plantilla personalizada por defecto
pio.templates.default = "colors"
pio.templates.default2 = "colors2"
#---------------------------------------------------------------------
@st.cache_data
def venta_perdida(csv_files):
    # Función para calcular la semana contable
    def calcular_dia(fecha):
        return fecha.isocalendar()[1]

    combined_df = pd.DataFrame()  # Crear un DataFrame vacío para almacenar todos los datos

    # Loop through each CSV file and append its contents to the combined dataframe
    for csv_file in csv_files:
        df = pd.read_csv(csv_file, encoding='ISO-8859-1')
        
        # Extraer el nombre del archivo sin la ruta completa y sin la extensión .csv
        file_name = os.path.splitext(os.path.basename(csv_file))[0]
        df['Día'] = file_name
        
        # Asumir que el nombre del archivo es la fecha en formato 'ddmmyyyy'
        df['Fecha'] = pd.to_datetime(file_name, format='%d%m%Y', errors='coerce')
        
        # Calcular la semana contable
        df['Semana Contable'] = df['Fecha'].apply(lambda x: f"{x.year}{str(x.isocalendar()[1]).zfill(2)}" if pd.notnull(x) else 'Fecha inválida')
        
        # Concatenar el DataFrame actual al DataFrame combinado
        combined_df = pd.concat([combined_df, df])

    # Eliminar las columnas no deseadas
    combined_df = combined_df.drop(columns=['UPC','CAMPO', 'INVENTARIO_UDS','INVENTARIO_PESOS','VENTA_UDS_PTD','VENTA_PESOS_PTD','NUM_TIENDA','NOMBRE_TIENDA','ESTATUS', 'PROVEEDOR', 'Fecha', 'CATEGORIA'])
    #combined_df.loc[combined_df['DESC_ARTICULO'].str.contains('Vuse', case=False, na=False), 'CATEGORIA'] = '062 RRPs (Vapor y tabaco calentado)'
    combined_df['DIVISION'] = combined_df['DIVISION'].astype(str).str[:2]
    combined_df['PLAZA'] = combined_df['PLAZA'].astype(str).str[:3]
    combined_df['MERCADO'] = combined_df['MERCADO'].astype(str).str[1:]
    combined_df = combined_df.dropna(subset=['VENTA_PERDIDA_PESOS','ID_ARTICULO'])
    combined_df['ID_ARTICULO'] = combined_df['ID_ARTICULO'].astype(float).astype(int).astype(str)
    combined_df['VENTA_PERDIDA_PESOS'] = combined_df['VENTA_PERDIDA_PESOS'].round(0).astype('int64')
    combined_df = combined_df.rename(columns={
        'ID_ARTICULO': 'ARTICULO',
    })

    # Mover la columna 'Día' a la primera posición
    cols = ['Día', 'Semana Contable'] + [col for col in combined_df.columns if col not in ['Día', 'Semana Contable']]
    combined_df = combined_df[cols]
    #combined_df = combined_df.drop(columns=['Día'])
    return combined_df

#---------------------------------------------------------------------
@st.cache_data
def venta(venta_semanal):
    concat_venta = pd.DataFrame()

    for xlsx_file in venta_semanal:
        try:
            df2 = pd.read_excel(xlsx_file)
            
            # Verificar si ya existe la columna 'Semana Contable'
            if 'Semana Contable' not in df2.columns:
                print(f"Advertencia: La columna 'Semana Contable' no existe en {xlsx_file}.")
                continue  # Salta este archivo si no tiene la columna necesaria
            
            # Asegúrate de que la columna 'Semana Contable' sea de tipo object
            df2['Semana Contable'] = df2['Semana Contable'].astype(str)
            
            # Concatenar los datos
            concat_venta = pd.concat([concat_venta, df2], ignore_index=True)
        
        except Exception as e:
            print(f"Error al procesar el archivo {xlsx_file}: {e}")
    
    # Reorganizar columnas si es necesario
    if 'Semana Contable' in concat_venta.columns:
        cols2 = ['Semana Contable'] + [col2 for col2 in concat_venta.columns if col2 not in ['Semana Contable']]
        concat_venta = concat_venta[cols2]

    # Eliminar columnas específicas no deseadas
    columnas_a_eliminar = [col for col in concat_venta.columns if 'Unnamed' in col] + ['Metrics']
    concat_venta = concat_venta.drop(columns=columnas_a_eliminar, errors='ignore') 
    #concat_venta = concat_venta.dropna(subset=['Venta Neta Total', 'Artículo' ])
    concat_venta['División'] = concat_venta['División'].astype(float).astype(int).astype(str)
    concat_venta['Plaza'] = concat_venta['Plaza'].astype(float).astype(int).astype(str)
    concat_venta['Mercado'] = concat_venta['Mercado'].astype(float).astype(int).astype(str)
    concat_venta['Artículo'] = concat_venta['Artículo'].astype(float).astype(int).astype(str)
    concat_venta['Semana Contable'] = concat_venta['Semana Contable'].astype('str')
    concat_venta['Venta Neta Total'] = concat_venta['Venta Neta Total'].fillna(0).round(0).astype('int64')
    concat_venta = concat_venta.rename(columns={
        'Artículo': 'ARTICULO',
        'División': 'DIVISION',
        'Plaza': 'PLAZA', 
        'Mercado': 'MERCADO',
    })
 
    return concat_venta



#---------------------------------------------------------------------

# Cargar los DataFrames por separado
VENTA_PERDIDA = venta_perdida(csv_files)
VENTA = venta(venta_semanal)
MASTER['ARTICULO'] = MASTER['ARTICULO'].astype(str)


familia_dict = MASTER.set_index('ARTICULO')['FAMILIA'].to_dict()
segmento_dict = MASTER.set_index('ARTICULO')['SEGMENTO'].to_dict()
subcategoria_dict = MASTER.set_index('ARTICULO')['SUBCATEGORIA'].to_dict()
proveedor_dict = MASTER.set_index('ARTICULO')['PROVEEDOR'].to_dict()

VENTA_PERDIDA['FAMILIA'] = VENTA_PERDIDA['ARTICULO'].map(familia_dict)
VENTA_PERDIDA['SEGMENTO'] = VENTA_PERDIDA['ARTICULO'].map(segmento_dict)
VENTA_PERDIDA['SUBCATEGORIA'] = VENTA_PERDIDA['ARTICULO'].map(subcategoria_dict)
VENTA_PERDIDA['PROVEEDOR'] = VENTA_PERDIDA['ARTICULO'].map(proveedor_dict)


VENTA['FAMILIA'] = VENTA['ARTICULO'].map(familia_dict)
VENTA['SEGMENTO'] = VENTA['ARTICULO'].map(segmento_dict)
VENTA['SUBCATEGORIA'] = VENTA['ARTICULO'].map(subcategoria_dict)
VENTA['PROVEEDOR'] = VENTA['ARTICULO'].map(proveedor_dict)

#VENTA = VENTA.dropna(subset=['PROVEEDOR'])
VENTA_PERDIDA = VENTA_PERDIDA.dropna(subset=['PROVEEDOR'])


# Diccionario de mapeo de códigos de plaza a nombres
map_plaza = {
    "100": "Reynosa",
    "110": "Matamoros",
    "200": "México",
    "300": "Jalisco",
    "400": "Coahuila (Saltillo)",
    "410": "Coahuila (Torreón)",
    "500": "Nuevo León",
    "600": "Baja California (Tijuana)",
    "610": "Baja California (Ensenada)",
    "620": "Baja California (Mexicali)",
    "650": "Sonora (Hermosillo)",
    "700": "Puebla",
    "720": "Morelos",
    "800": "Yucatán",
    "890": "Quintana Roo",
}

# Aplicar el mapeo al DataFrame
VENTA['PLAZA'] = VENTA['PLAZA'].apply(lambda x: map_plaza.get(x, x))
VENTA_PERDIDA['PLAZA'] = VENTA_PERDIDA['PLAZA'].apply(lambda x: map_plaza.get(x, x))

 
map_division = {
    "10": "Coah-Tamps",
    "20": "México-Península",
    "30": "Pacífico",
    "50": "Nuevo León",
}

# Aplicar el mapeo al DataFrame
VENTA['DIVISION'] = VENTA['DIVISION'].map(map_division)
VENTA_PERDIDA['DIVISION'] = VENTA_PERDIDA['DIVISION'].map(map_division)

plazas_acacia = {
    "100": "Reynosa",
    "110": "Matamoros",
    "200": "México",
    "300": "Jalisco",
    "400": "Coahuila (Saltillo)",
    "410": "Coahuila (Torreón)",
    "500": "Nuevo León",
    "600": "Baja California (Tijuana)",
    "610": "Baja California (Ensenada)",
    "620": "Baja California (Mexicali)",
    "650": "Sonora (Hermosillo)",
    "700": "Puebla",
    "720": "Morelos",
    "800": "Yucatán",
    "890": "Quintana Roo",
}
 

# Calcular la suma de 'Venta Neta Total'
if 'Venta Neta Total' in VENTA.columns:
    suma_venta_neta_total = VENTA['Venta Neta Total'].sum()
    print(f"Suma total de 'Venta Neta Total': {suma_venta_neta_total}")
else:
    print("La columna 'Venta Neta Total' no existe en el DataFrame.")

#---------------------------------------------------------------------

# Paso 1: Crear una lista de opciones para el filtro, incluyendo "Ninguno"
opciones_proveedor = ['Ninguno'] + list(VENTA_PERDIDA['PROVEEDOR'].unique())
proveedor = st.sidebar.selectbox('Seleccione el Proveedor', opciones_proveedor)

opciones_division = ['Ninguno'] + list(VENTA_PERDIDA['DIVISION'].unique())
division = st.sidebar.selectbox('Seleccione la División', opciones_division)

opciones_plaza = ['Ninguno'] + list(VENTA_PERDIDA['PLAZA'].unique())
plaza = st.sidebar.selectbox('Seleccione la Plaza', opciones_plaza)

# Paso 2 - Sidebar para elegir filtro
tipo_filtro_acacia = st.sidebar.selectbox(
    'Seleccione la Plaza ACACIA',
    ['Todas', 'Plazas ACACIA']
)

# Paso 3 - Mostrar multiselect solo si quiere filtrar
if tipo_filtro_acacia == 'Plazas ACACIA':
    opciones_plaza_acacia = list(set(plazas_acacia.values()))
    plazas_acacia_seleccionadas = st.sidebar.multiselect('Plazas ACACIA', opciones_plaza_acacia)
else:
    plazas_acacia_seleccionadas = []  # No selecciona nada


opciones_mercado = ['Ninguno'] + list(VENTA_PERDIDA['MERCADO'].unique())
mercado = st.sidebar.selectbox('Seleccione el Mercado', opciones_mercado)

opciones_semana = ['Ninguno'] + list(VENTA_PERDIDA['Semana Contable'].unique())
semana = st.sidebar.selectbox('Seleccione la semana', opciones_semana)

opciones_familia = ['Ninguno'] + list(VENTA_PERDIDA['FAMILIA'].unique())
familia = st.sidebar.selectbox('Seleccione la Familia', opciones_familia)

opciones_categoria = ['Ninguno'] + list(VENTA_PERDIDA['SUBCATEGORIA'].unique())
categoria = st.sidebar.selectbox('Seleccione la Categoria', opciones_categoria)




# Filtrar por Proveedor
if proveedor == 'Ninguno':
    df_venta_perdida_filtrada = VENTA_PERDIDA
    df_venta_filtrada = VENTA
else:
    df_venta_perdida_filtrada = VENTA_PERDIDA[VENTA_PERDIDA['PROVEEDOR'] == proveedor]
    df_venta_filtrada = VENTA[VENTA['PROVEEDOR'] == proveedor]


# Filtrar por División
if division != 'Ninguno':
    df_venta_perdida_filtrada = df_venta_perdida_filtrada[df_venta_perdida_filtrada['DIVISION'] == division]
    df_venta_filtrada = df_venta_filtrada[df_venta_filtrada['DIVISION'] == division]

# Filtrar por Plaza
if plaza != 'Ninguno':
    df_venta_perdida_filtrada = df_venta_perdida_filtrada[df_venta_perdida_filtrada['PLAZA'] == plaza]
    df_venta_filtrada = df_venta_filtrada[df_venta_filtrada['PLAZA'] == plaza]

# Paso 3 - Filtrar solo si seleccionó plazas
if plazas_acacia_seleccionadas:
    df_venta_perdida_filtrada = df_venta_perdida_filtrada[df_venta_perdida_filtrada['PLAZA'].isin(plazas_acacia_seleccionadas)]
    df_venta_filtrada = df_venta_filtrada[df_venta_filtrada['PLAZA'].isin(plazas_acacia_seleccionadas)]

# Filtrar por Mercado
if mercado != 'Ninguno':
    df_venta_perdida_filtrada = df_venta_perdida_filtrada[df_venta_perdida_filtrada['MERCADO'] == mercado]
    df_venta_filtrada = df_venta_filtrada[df_venta_filtrada['MERCADO'] == mercado]

# Filtrar por Semana
if semana != 'Ninguno':
    df_venta_perdida_filtrada = df_venta_perdida_filtrada[df_venta_perdida_filtrada['Semana Contable'] == semana]
    df_venta_filtrada = df_venta_filtrada[df_venta_filtrada['Semana Contable'] == semana]

# Filtrar por Familia
if familia != 'Ninguno':
    df_venta_perdida_filtrada = df_venta_perdida_filtrada[df_venta_perdida_filtrada['FAMILIA'] == familia]
    df_venta_filtrada = df_venta_filtrada[df_venta_filtrada['FAMILIA'] == familia]

# Filtrar por Categoria
if categoria != 'Ninguno':
    df_venta_perdida_filtrada = df_venta_perdida_filtrada[df_venta_perdida_filtrada['SUBCATEGORIA'] == categoria]
    df_venta_filtrada = df_venta_filtrada[df_venta_filtrada['SUBCATEGORIA'] == categoria]


# Modificar la columna 'Semana Contable' en ambos DataFrames
df_venta_perdida_filtrada['Semana Contable'] = df_venta_perdida_filtrada['Semana Contable'].apply(lambda x: f"Semana {str(x)[4:]}")
df_venta_filtrada['Semana Contable'] = df_venta_filtrada['Semana Contable'].apply(lambda x: f"Semana {str(x)[4:]}")
df_venta_perdida_filtrada = df_venta_perdida_filtrada[df_venta_perdida_filtrada['FAMILIA'] != 'BYE']
df_venta_filtrada = df_venta_filtrada[df_venta_filtrada['FAMILIA'] != 'BYE'] 



#--------------------------------------------------------------------

# Aplicar plantilla personalizada por defecto

@st.cache_data
def graficar_porcentaje_venta_perdida_por_semana(df_venta_filtrada, df_venta_perdida_filtrada):
    # Filtrar semanas comunes
    semanas_comunes = set(df_venta_filtrada['Semana Contable']).intersection(set(df_venta_perdida_filtrada['Semana Contable']))
    df_venta_filtrada_suma = df_venta_filtrada[df_venta_filtrada['Semana Contable'].isin(semanas_comunes)].groupby('Semana Contable')['Venta Neta Total'].sum().reset_index()
    df_venta_perdida_filtrada_suma = df_venta_perdida_filtrada[df_venta_perdida_filtrada['Semana Contable'].isin(semanas_comunes)].groupby('Semana Contable')['VENTA_PERDIDA_PESOS'].sum().reset_index()

    # Calcular el porcentaje de venta perdida sobre la venta neta total
    df_combined = pd.merge(df_venta_filtrada_suma, df_venta_perdida_filtrada_suma, on='Semana Contable')
    df_combined['% Venta Perdida'] = (df_combined['VENTA_PERDIDA_PESOS'] / df_combined['Venta Neta Total'].replace(0, np.nan)) * 100

    # Crear la gráfica de líneas solo con el % de venta perdida
    fig = go.Figure(go.Scatter(
        x=df_combined['Semana Contable'],
        y=df_combined['% Venta Perdida'],
        mode='lines+markers+text',
        name='% Venta Perdida',
        hovertemplate='% de Venta Perdida: %{y:.2f}%',
        text=df_combined['% Venta Perdida'].apply(lambda x: f'{x:.2f}%'),
        textposition='top center'  # Posición de las etiquetas
    ))

    # Configurar el diseño de la gráfica
    fig.update_layout(
        title='% de Venta Perdida por Semana 🗓️',
        title_font=dict(size=20),
        #xaxis=dict(title='Semana Contable'),
        yaxis=dict(title='% de Venta Perdida'),
        yaxis_tickformat=".2f",  # Formato de los ticks del eje y
        template="colors"  # Aplicar la plantilla personalizada
    )

    fig.update_traces(
    textposition="top left",
    textfont=dict(size=18)  # Ajusta el valor de size según tus preferencias
    )

    return fig

# Uso de la función
figura = graficar_porcentaje_venta_perdida_por_semana(df_venta_filtrada, df_venta_perdida_filtrada)


@st.cache_data
def graficar_venta_perdida_por_proveedor_y_semana(df_venta_perdida_filtrada, df_venta_filtrada):
    # Filtrar semanas comunes
    semanas_comunes = set(df_venta_filtrada['Semana Contable']).intersection(set(df_venta_perdida_filtrada['Semana Contable']))
    df_venta_perdida_filtrada_suma = df_venta_perdida_filtrada[df_venta_perdida_filtrada['Semana Contable'].isin(semanas_comunes)]

    # Agrupar por Proveedor y Semana Contable para sumar la venta perdida
    df_venta_perdida_por_proveedor_y_semana = df_venta_perdida_filtrada_suma.groupby(['Semana Contable', 'PROVEEDOR'])['VENTA_PERDIDA_PESOS'].sum().reset_index()

    # Agrupar por Semana Contable para sumar la venta neta total
    df_venta_filtrada_suma = df_venta_filtrada[df_venta_filtrada['Semana Contable'].isin(semanas_comunes)].groupby('Semana Contable')['Venta Neta Total'].sum().reset_index()

    # Calcular el porcentaje de venta perdida sobre la venta neta total
    df_combined = pd.merge(df_venta_perdida_por_proveedor_y_semana, df_venta_filtrada_suma, on='Semana Contable', how='left')
    df_combined['% Venta Perdida'] = (df_combined['VENTA_PERDIDA_PESOS'] / df_combined['Venta Neta Total'].replace(0, np.nan)) * 100

    # Crear la gráfica de líneas por proveedor
    fig = go.Figure()

    # Añadir una línea por cada proveedor
    proveedores = df_combined['PROVEEDOR'].unique()
    for proveedor in proveedores:
        df_proveedor = df_combined[df_combined['PROVEEDOR'] == proveedor]
        fig.add_trace(go.Scatter(
            x=df_proveedor['Semana Contable'],
            y=df_proveedor['% Venta Perdida'],
            mode='lines+markers',
            name=proveedor,
            hovertemplate='%{x}<br>% Venta Perdida: %{y:.2f}%<extra></extra>'
        ))

    # Configurar el diseño de la gráfica
    fig.update_layout(
        title='% de Venta Perdida por Proveedor y Semana 🗓️',
        title_font=dict(size=20),
        xaxis=dict(title='Semana Contable'),
        yaxis=dict(title='% de Venta Perdida'),
        yaxis_tickformat=".2f",  # Formato de los ticks del eje y
        template="plotly"  # Aplicar la plantilla personalizada
    )

    return fig

# Uso de la función
figura2 = graficar_venta_perdida_por_proveedor_y_semana(df_venta_perdida_filtrada, df_venta_filtrada)




@st.cache_data
def graficar_venta_perdida_por_subcategoria(df_venta_filtrada, df_venta_perdida_filtrada):
    # Filtrar semanas comunes y sumar las ventas por subcategoría y semana
    semanas_comunes = set(df_venta_filtrada['Semana Contable']).intersection(set(df_venta_perdida_filtrada['Semana Contable']))
    df_venta_perdida_filtrada_suma = df_venta_perdida_filtrada[df_venta_perdida_filtrada['Semana Contable'].isin(semanas_comunes)]
    df_venta_perdida_suma = df_venta_perdida_filtrada_suma.groupby(['Semana Contable', 'SUBCATEGORIA'])['VENTA_PERDIDA_PESOS'].sum().reset_index()
    
    # Calcular el porcentaje de venta perdida respecto a la venta neta
    df_venta_suma = df_venta_filtrada[df_venta_filtrada['Semana Contable'].isin(semanas_comunes)].groupby('Semana Contable')['Venta Neta Total'].sum().reset_index()
    df_venta_perdida_suma = pd.merge(df_venta_perdida_suma, df_venta_suma, on='Semana Contable')
    df_venta_perdida_suma['% Venta Perdida'] = (df_venta_perdida_suma['VENTA_PERDIDA_PESOS'] / df_venta_perdida_suma['Venta Neta Total'].replace(0, np.nan)) * 100

    # Crear la gráfica apilada
    fig = px.bar(
        df_venta_perdida_suma, 
        x='Semana Contable', 
        y=df_venta_perdida_suma['VENTA_PERDIDA_PESOS'] / 1e6,  # Convertir a millones
        color='SUBCATEGORIA', 
        text='% Venta Perdida',
        title='% Venta Perdida por Categoria 📊',
        labels={'VENTA_PERDIDA_PESOS': 'Venta Perdida en Pesos (M)'},
        hover_data={'% Venta Perdida': ':.1f'}
    )


    # Ajustar el diseño para mostrar las etiquetas de porcentaje
    fig.update_traces(
        texttemplate='%{text:.2f}%', 
        textposition='inside', 
        hovertemplate='%{x}<br>$%{y:.2f}M de pesos<br>%{text:.1f}% de Venta Perdida'
    )


    # Configurar el layout
    fig.update_layout(title_font=dict(size=20), barmode='stack',  template="colors", yaxis=dict(title='Venta Perdida en Pesos'))

    return fig

# Uso de la función
figura3 = graficar_venta_perdida_por_subcategoria(df_venta_filtrada, df_venta_perdida_filtrada)


@st.cache_data
def graficar_venta_perdida_por_mercado_lineas(df_venta_filtrada, df_venta_perdida_filtrada):
    # Filtrar semanas comunes
    semanas_comunes = set(df_venta_filtrada['Semana Contable']).intersection(set(df_venta_perdida_filtrada['Semana Contable']))
    df_venta_filtrada_suma = df_venta_filtrada[df_venta_filtrada['Semana Contable'].isin(semanas_comunes)]
    df_venta_perdida_filtrada_suma = df_venta_perdida_filtrada[df_venta_perdida_filtrada['Semana Contable'].isin(semanas_comunes)]
    
    # Sumar las ventas netas y perdidas por mercado y semana
    df_venta_suma = df_venta_filtrada_suma.groupby(['Semana Contable', 'MERCADO'])['Venta Neta Total'].sum().reset_index()
    df_venta_perdida_suma = df_venta_perdida_filtrada_suma.groupby(['Semana Contable', 'MERCADO'])['VENTA_PERDIDA_PESOS'].sum().reset_index()

    # Combinar los DataFrames para poder calcular el porcentaje
    df_combined = pd.merge(df_venta_perdida_suma, df_venta_suma, on=['Semana Contable', 'MERCADO'])

    # Calcular el porcentaje de venta perdida respecto a la venta neta total del mismo mercado
    df_combined['% Venta Perdida'] = (df_combined['VENTA_PERDIDA_PESOS'] / df_combined['Venta Neta Total']) * 100

    # Redondear el porcentaje a un decimal y formatear como texto con el símbolo %
    df_combined['% Venta Perdida'] = df_combined['% Venta Perdida'].round(1).astype(str) + '%'

    # Filtrar solo los mercados más grandes para reducir el tamaño de los datos
    mercados_a_mostrar = df_combined.groupby('MERCADO')['VENTA_PERDIDA_PESOS'].sum().nlargest(5).index
    df_combined = df_combined[df_combined['MERCADO'].isin(mercados_a_mostrar)]

    # Crear la gráfica de líneas con marcadores y texto
    fig = px.line(df_combined, 
                  x='Semana Contable', 
                  y='% Venta Perdida', 
                  color='MERCADO', 
                  title='Venta Perdida semanal por Mercado 🏙️',
                  labels={'% Venta Perdida': '% Venta Perdida'},
                  markers=True,
                  text='% Venta Perdida')  # Añadir el porcentaje de venta perdida como texto

    # Configurar el layout para que se muestre el % Venta Perdida en el texto sobre los puntos
    fig.update_traces(textposition="top center")

    # Configurar el layout general
    fig.update_layout(title_font=dict(size=20),template="colors", xaxis=dict(title='Semana Contable'), yaxis=dict(title='% Venta Perdida'))

    return fig

# Uso de la función
figura4 = graficar_venta_perdida_por_mercado_lineas(df_venta_filtrada, df_venta_perdida_filtrada)




@st.cache_data
def graficar_venta_perdida_por_familia(df_venta_filtrada, df_venta_perdida_filtrada):
    # Filtrar semanas comunes
    semanas_comunes = set(df_venta_filtrada['Semana Contable']).intersection(set(df_venta_perdida_filtrada['Semana Contable']))
    df_venta_filtrada_suma = df_venta_filtrada[df_venta_filtrada['Semana Contable'].isin(semanas_comunes)]
    df_venta_perdida_filtrada_suma = df_venta_perdida_filtrada[df_venta_perdida_filtrada['Semana Contable'].isin(semanas_comunes)]
    
    # Sumar las ventas netas y perdidas por familia
    df_venta_suma = df_venta_filtrada_suma.groupby(['Semana Contable', 'FAMILIA'])['Venta Neta Total'].sum().reset_index()
    df_venta_perdida_suma = df_venta_perdida_filtrada_suma.groupby(['Semana Contable', 'FAMILIA'])['VENTA_PERDIDA_PESOS'].sum().reset_index()

    # Combinar los DataFrames para poder calcular el porcentaje
    df_combined = pd.merge(df_venta_perdida_suma, df_venta_suma, on=['Semana Contable', 'FAMILIA'])

    # Calcular el porcentaje de venta perdida respecto a la venta neta total de la misma familia
    df_combined['% Venta Perdida'] = (df_combined['VENTA_PERDIDA_PESOS'] / df_combined['Venta Neta Total'].replace(0, np.nan)) * 100

    # Crear una tabla pivote para que la familia sea una columna y la semana se muestre en el eje x
    df_pivot = df_combined.pivot(index='Semana Contable', columns='FAMILIA', values='% Venta Perdida').reset_index()

    # Definir una paleta de colores personalizada similar a la gráfica de la izquierda
    custom_colors = [
     '#00712D', '#FF9800', '#000080', '#FFB347', '#33A85C', '#FF6347', '#000000', '#FFD700', 
     '#66C88B', '#FF4500', '#FFCC66', '#008080', '#CD5C5C', '#FF7F50', '#006400', '#FFA07A', 
     '#8B0000', '#FFDEAD', '#ADFF2F', '#2F4F4F'
     ]
    # Crear la gráfica de barras apiladas
    fig = px.bar(df_pivot, 
                 x='Semana Contable', 
                 y=df_pivot.columns[1:],  # Excluyendo la columna 'Semana Contable'
                 title='Venta Perdida por Familia 📚',
                 labels={'value': '% Venta Perdida', 'variable': 'Familia'},
                 hover_name='Semana Contable',
                 color_discrete_sequence=custom_colors)  # Aplicando la paleta de colores personalizada

    # Configurar el layout para que solo se muestre el % Venta Perdida en el hover
    fig.update_traces(hovertemplate='%{y:.1f}%')

    # Configurar el layout general
    fig.update_layout(title_font=dict(size=20),
                      xaxis=dict(title='Semana Contable'),
                      yaxis=dict(title='% Venta Perdida'))

    return fig

# Uso de la función
figura5 = graficar_venta_perdida_por_familia(df_venta_filtrada, df_venta_perdida_filtrada)


@st.cache_data
def graficar_venta_perdida_por_segmento(df_venta_filtrada, df_venta_perdida_filtrada):
    # Sumar las ventas netas y perdidas por segmento
    df_venta_suma = df_venta_filtrada.groupby('SEGMENTO').agg({'Venta Neta Total': 'sum'}).reset_index()
    df_venta_perdida_suma = df_venta_perdida_filtrada.groupby('SEGMENTO').agg({'VENTA_PERDIDA_PESOS': 'sum'}).reset_index()

    # Combinar los DataFrames para calcular el porcentaje
    df_combined = pd.merge(df_venta_perdida_suma, df_venta_suma, on='SEGMENTO', how='inner')
    df_combined['% Venta Perdida'] = (df_combined['VENTA_PERDIDA_PESOS'] / df_combined['Venta Neta Total']) * 100

    # Crear gráfico de barras apilado
    fig = px.bar(df_combined, 
                 x='SEGMENTO', 
                 y='VENTA_PERDIDA_PESOS', 
                 color='% Venta Perdida', 
                 text='% Venta Perdida',
                 title='Venta Perdida por segmento 🚬',
                 labels={'VENTA_PERDIDA_PESOS': 'Venta Perdida', 'SEGMENTO': 'SEGMENTO'},
                 color_continuous_scale=px.colors.sequential.Viridis)

    # Ajustar layout y formato de texto
    fig.update_layout( 
                      title_font=dict(size=20),
                      #xaxis=dict(title='SEGMENTO'),
                      yaxis=dict(title='Venta Perdida'),
                      template="colors2")
    
    fig.update_traces(
        texttemplate='%{text:.2f}%', 
        textposition='outside',
        hovertemplate='Venta Perdida: $%{y:,.2f}<br>% Venta Perdida: %{text:.2f}%'
    )

    return fig

# Uso de la función
figura6 = graficar_venta_perdida_por_segmento(df_venta_filtrada, df_venta_perdida_filtrada)



@st.cache_data
def graficar_venta_perdida_por_plaza(df_venta_perdida_filtrada, df_venta_filtrada):
    # Sumar la venta perdida y venta neta total por plaza y semana
    df_venta_perdida_por_plaza = df_venta_perdida_filtrada.groupby(['Semana Contable', 'PLAZA']).agg({'VENTA_PERDIDA_PESOS': 'sum'}).reset_index()
    df_venta_neta_por_plaza = df_venta_filtrada.groupby(['Semana Contable', 'PLAZA']).agg({'Venta Neta Total': 'sum'}).reset_index()

    # Combinar los DataFrames para calcular el porcentaje de venta perdida
    df_combined = pd.merge(df_venta_perdida_por_plaza, df_venta_neta_por_plaza, on=['Semana Contable', 'PLAZA'], how='inner')
    df_combined['% Venta Perdida'] = (df_combined['VENTA_PERDIDA_PESOS'] / df_combined['Venta Neta Total']) * 100
    df_combined['% Venta Perdida'] = df_combined['% Venta Perdida'].round(1)

    # Crear gráfico de líneas
    fig = go.Figure()

    for plaza in df_combined['PLAZA'].unique():
        df_plaza = df_combined[df_combined['PLAZA'] == plaza]
        fig.add_trace(go.Scatter(
            x=df_plaza['Semana Contable'],
            y=df_plaza['% Venta Perdida'],
            mode='lines+markers+text',
            text=df_plaza['% Venta Perdida'].apply(lambda x: f'{x:.1f}%'),
            textposition='top right',
            name=plaza
        ))

    fig.update_layout(
        title='Venta Perdida semanal por Plaza 🌄',
        yaxis_title='% Venta Perdida',
        hovermode='closest',
        title_font=dict(size=20),
        template="colors2",
        showlegend=True
    )

    return fig

# Uso de la función
figura7 = graficar_venta_perdida_por_plaza(df_venta_perdida_filtrada, df_venta_filtrada)


@st.cache_data
def graficar_venta_perdida(df_venta_filtrada, df_venta_perdida_filtrada):
    # Filtrar semanas comunes
    semanas_comunes = set(df_venta_filtrada['Semana Contable']).intersection(set(df_venta_perdida_filtrada['Semana Contable']))
    df_venta_filtrada_suma = df_venta_filtrada[df_venta_filtrada['Semana Contable'].isin(semanas_comunes)]
    df_venta_perdida_filtrada_suma = df_venta_perdida_filtrada[df_venta_perdida_filtrada['Semana Contable'].isin(semanas_comunes)]

    # Sumar las ventas netas y perdidas por división y semana
    df_venta_suma = df_venta_filtrada_suma.groupby(['Semana Contable', 'DIVISION'])['Venta Neta Total'].sum().reset_index()
    df_venta_perdida_suma = df_venta_perdida_filtrada_suma.groupby(['Semana Contable', 'DIVISION'])['VENTA_PERDIDA_PESOS'].sum().reset_index()

    # Combinar los DataFrames para calcular el porcentaje
    df_combined = pd.merge(df_venta_perdida_suma, df_venta_suma, on=['Semana Contable', 'DIVISION'])
    df_combined['% Venta Perdida'] = (df_combined['VENTA_PERDIDA_PESOS'] / df_combined['Venta Neta Total']) * 100

    # Crear el gráfico estático
    fig = go.Figure()

    # Agregar líneas de base con puntos
    for division in df_combined['DIVISION'].unique():
        df_div = df_combined[df_combined['DIVISION'] == division]
        fig.add_trace(go.Scatter(x=df_div['Semana Contable'], 
                                 y=df_div['% Venta Perdida'], 
                                 mode='lines+markers+text',
                                 text=df_div['% Venta Perdida'].apply(lambda x: f'{x:.1f}%'),
                                 textposition='top right',
                                 name=f'División {division}'))

    # Configurar el layout
    fig.update_layout(title="Venta Perdida semanal por División 🏴🏳️",
                      yaxis_title="% Venta Perdida",
                      hovermode="closest")

    return fig

# Uso de la función
figura8 = graficar_venta_perdida(df_venta_filtrada, df_venta_perdida_filtrada)

@st.cache_data
def graficar_top_venta_perdida_en_dinero(df_venta_filtrada, df_venta_perdida_filtrada, MASTER):
    # Convertir ARTICULO a string para garantizar la conexión con MASTER
    df_venta_filtrada['ARTICULO'] = df_venta_filtrada['ARTICULO'].astype(str)
    df_venta_perdida_filtrada['ARTICULO'] = df_venta_perdida_filtrada['ARTICULO'].astype(str)
    MASTER['ARTICULO'] = MASTER['ARTICULO'].astype(str)

    # Crear un diccionario de mapeo ARTICULO -> DESCRIPCIÓN
    articulo_a_descripcion = MASTER.set_index('ARTICULO')['DESCRIPCIÓN'].to_dict()

    # Filtrar semanas comunes
    semanas_comunes = set(df_venta_filtrada['Semana Contable']).intersection(set(df_venta_perdida_filtrada['Semana Contable']))
    df_venta_perdida_filtrada_suma = df_venta_perdida_filtrada[df_venta_perdida_filtrada['Semana Contable'].isin(semanas_comunes)]

    # Sumar las ventas perdidas por artículo
    df_venta_perdida_suma = df_venta_perdida_filtrada_suma.groupby(['Semana Contable', 'ARTICULO'])['VENTA_PERDIDA_PESOS'].sum().reset_index()

    # Calcular el total de venta perdida por artículo para determinar el Top 10
    top_articulos = (
        df_venta_perdida_suma.groupby('ARTICULO')['VENTA_PERDIDA_PESOS']
        .sum()
        .nlargest(10)
        .index
    )
    df_top_venta_perdida = df_venta_perdida_suma[df_venta_perdida_suma['ARTICULO'].isin(top_articulos)]

    # Mapear ARTICULO a DESCRIPCIÓN
    df_top_venta_perdida['DESCRIPCIÓN'] = df_top_venta_perdida['ARTICULO'].map(articulo_a_descripcion)

    # Crear la gráfica apilada
    fig = px.bar(
        df_top_venta_perdida, 
        x='Semana Contable', 
        y='VENTA_PERDIDA_PESOS', 
        color='DESCRIPCIÓN',  # Usamos DESCRIPCIÓN en lugar de ARTICULO
        color_discrete_sequence = ['#007074', '#FFBF00', '#9694FF', '#222831', '#004225', '#1230AE', '#8D0B41', '#522258', 
         '#1F7D53', '#EB5B00', '#0D1282', '#09122C', '#ADFF2F', '#2F4F4F', "#7C00FE", "#D10363", "#16404D"],
        text='VENTA_PERDIDA_PESOS',
        title='Top 10 Artículos con Mayor Venta Perdida (En Pesos)',
        labels={'VENTA_PERDIDA_PESOS': 'Venta Perdida en Pesos', 'DESCRIPCIÓN': 'Descripción del Artículo'},
        hover_data={'VENTA_PERDIDA_PESOS': ':,.2f'} )
    

    # Ajustar el diseño para mostrar las etiquetas de valores
    fig.update_traces(
        texttemplate='$%{text:,.2f}', 
        textposition='inside', 
        hovertemplate='%{x}<br>$%{y:,.2f} pesos<br>'
    )

    # Configurar el layout general
    fig.update_layout(
        title_font=dict(size=20), 
        barmode='stack', 
        #template="colors2",
        yaxis=dict(title='Venta Perdida en Pesos'),
        xaxis=dict(title='Semana Contable')
    )

    return fig

# Uso de la función
figura9 = graficar_top_venta_perdida_en_dinero(df_venta_filtrada, df_venta_perdida_filtrada, MASTER)

#---------------------------------------------------------------------
# Divisor y encabezado

st.divider()
st.subheader(':orange[Comparación de Ventas por Semana y Categoria]')

# Crear columnas
c1, c6, c3 = st.columns([4, 3, 4])

# Columna 1: Gráfica de Comparación de Venta Perdida y Venta Neta por Proveedor
with c1:
    st.plotly_chart(figura, use_container_width=True)
with c6:
    st.plotly_chart(figura6, use_container_width=True)
with c3:
    st.plotly_chart(figura3, use_container_width=True)

st.divider()
st.subheader(':orange[Revisión por División y Plaza]')

# Crear columnas
c4, c5 = st.columns([4, 4])

with c4:
    st.plotly_chart(figura7, use_container_width=True)

with c5:    
    st.plotly_chart(figura8, use_container_width=True)


st.divider()
st.subheader(':orange[Comparación de Ventas por Mercado y División]')

# Crear columnas
c6, c7, c8 = st.columns([4, 3, 4])

# Columna 1: Gráfica de Comparación de Venta Perdida y Venta Neta por Proveedor
with c6:
    st.plotly_chart(figura4, use_container_width=True)
with c7:
    st.plotly_chart(figura5, use_container_width=True)
with c8:
    st.plotly_chart(figura2, use_container_width=True)

st.divider()
st.subheader(':orange[Artículos con mayor venta perdida]')
c9 = st.columns([4])  # Si planeas añadir más columnas, ajusta los pesos.
with c9[0]:  # Accede explícitamente a la primera columna.
    st.plotly_chart(figura9, use_container_width=True)


 
