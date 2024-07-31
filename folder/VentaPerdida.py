import pandas as pd
import streamlit as st
import plotly.graph_objects as go
from io import BytesIO
import requests

# Configuración de la página
st.set_page_config(page_title="Reporte de Venta Pérdida Cigarros y RRPS", page_icon="📊", layout="wide", initial_sidebar_state="expanded")

# Título de la aplicación
st.title("📊 Reporte de Venta Perdida Cigarros y RRPS")
st.markdown("En esta página podrás visualizar la venta pérdida día con día, por plaza, división, proveedor y otros datos que desees. Esto con el fin de dar acción y reducir la Venta pérdida")

# Fetch GitHub token from secrets
try:
    github_token = st.secrets["github"]["token"]
except KeyError:
    st.error("GitHub token not found. Please add it to the secrets.")
    st.stop()

# GitHub repository details
repo_owner = "Edwinale20"
repo_name = "317B"

# File paths
venta_pr_path = "venta/Venta PR.xlsx"

# Function to process Venta PR file
def load_venta_pr(file_path):
    url = f"https://api.github.com/repos/{repo_owner}/{repo_name}/contents/{file_path}"
    headers = {
        "Authorization": f"token {github_token}",
        "Accept": "application/vnd.github.v3.raw"
    }
    response = requests.get(url, headers=headers)
    response.raise_for_status()
    excel_content = BytesIO(response.content)
    df = pd.read_excel(excel_content)

    # Eliminar columnas innecesarias como "Unnamed"
    df = df.loc[:, ~df.columns.str.contains('^Unnamed')]

    # Renombrar las columnas según se requiera
    df = df.rename(columns={
        'Plaza': 'PLAZA',
        'División': 'DIVISIÓN',
        'Categoría': 'CATEGORIA',
        'Artículo': 'ID_ARTICULO',
        'Semana Contable': 'Semana Contable',
        'Venta Neta Total': 'Venta Neta Total',
        'Proveedor': 'PROVEEDOR'
    })

    # Verificar si la columna VENTA_PERDIDA_PESOS está presente
    if 'VENTA_PERDIDA_PESOS' not in df.columns:
        st.error("La columna 'VENTA_PERDIDA_PESOS' no se encontró en los datos de 'Venta PR'")
        return pd.DataFrame()  # Retorna un DataFrame vacío en caso de error
    return df

# Cargar datos
venta_pr_data = load_venta_pr(venta_pr_path)

# Verifica si los datos se cargaron correctamente antes de continuar
if venta_pr_data.empty:
    st.error("No se pudo cargar los datos desde 'Venta PR.xlsx'")
    st.stop()

# Muestra las primeras filas del dataframe para verificar
st.write("Vista previa de los datos cargados:", venta_pr_data.head())

# Function to apply filters
def apply_filters(data, proveedor, plaza, categoria, semana, division, articulo):
    if proveedor: data = data[data['PROVEEDOR'] == proveedor]
    if plaza: data = data[data['PLAZA'] == plaza]
    if categoria: data = data[data['CATEGORIA'] == categoria]
    if semana: data = data[data['Semana Contable'] == semana]
    if division: data = data[data['DIVISIÓN'] == division]
    if articulo: data = data[data['ID_ARTICULO'].str.contains(articulo, case=False, na=False)]
    return data

# Function to apply weekly view
def apply_weekly_view(data):
    required_columns = ['Semana Contable', 'PROVEEDOR', 'PLAZA', 'CATEGORIA', 'DIVISIÓN', 'ID_ARTICULO', 'VENTA_PERDIDA_PESOS']
    if all(col in data.columns for col in required_columns):
        weekly_data = data.groupby(['Semana Contable', 'PROVEEDOR', 'PLAZA', 'CATEGORIA', 'DIVISIÓN', 'ID_ARTICULO']).agg({'VENTA_PERDIDA_PESOS': 'sum'}).reset_index()
        return weekly_data
    else:
        missing_columns = [col for col in required_columns if col not in data.columns]
        st.error(f"Faltan las siguientes columnas en los datos: {missing_columns}")
        return pd.DataFrame()  # Retorna un DataFrame vacío en caso de error

# Function to apply monthly view
def apply_monthly_view(data):
    if 'Semana Contable' in data.columns:
        data['Mes'] = pd.to_datetime(data['Semana Contable'], format='%Y%U').dt.to_period('M')
        monthly_data = data.groupby(['Mes', 'PROVEEDOR', 'PLAZA', 'CATEGORIA', 'DIVISIÓN', 'ID_ARTICULO']).agg({'VENTA_PERDIDA_PESOS': 'sum'}).reset_index()
        return monthly_data
    else:
        st.error("La columna 'Semana Contable' no se encontró en los datos.")
        return pd.DataFrame()

# Function to plot venta perdida vs venta neta total
def plot_comparacion_venta_perdida_vs_neta(data, venta_pr_data, view):
    if venta_pr_data.empty:
        st.warning("No hay datos disponibles para 'Venta PR'")
        return go.Figure()

    if view == "semanal":
        venta_pr_data_grouped = venta_pr_data.groupby('Semana Contable')['Venta Neta Total'].sum().reset_index()
        comparacion = data.groupby('Semana Contable')['VENTA_PERDIDA_PESOS'].sum().reset_index()
        comparacion = comparacion.merge(venta_pr_data_grouped, left_on='Semana Contable', right_on='Semana Contable', how='left')
    else:
        venta_pr_data['Mes'] = pd.to_datetime(venta_pr_data['Semana Contable'], format='%Y%U').dt.to_period('M')
        venta_pr_data_grouped = venta_pr_data.groupby('Mes')['Venta Neta Total'].sum().reset_index()
        comparacion = data.groupby('Mes')['VENTA_PERDIDA_PESOS'].sum().reset_index()
        comparacion = comparacion.merge(venta_pr_data_grouped, left_on='Mes', right_on='Mes', how='left')

    comparacion['Venta No Perdida'] = comparacion['Venta Neta Total'] - comparacion['VENTA_PERDIDA_PESOS']
    comparacion['% Venta Perdida'] = (comparacion['VENTA_PERDIDA_PESOS'] / comparacion['Venta Neta Total']) * 100

    fig = go.Figure(data=[
        go.Bar(
            name='Venta Perdida',
            x=comparacion['Semana Contable' if view == "semanal" else 'Mes'],
            y=comparacion['VENTA_PERDIDA_PESOS'],
            marker_color='red',
            text=comparacion['% Venta Perdida'].apply(lambda x: f'{x:.0f}%'),
            textposition='inside'
        ),
        go.Bar(
            name='Venta No Perdida',
            x=comparacion['Semana Contable' if view == "semanal" else 'Mes'],
            y=comparacion['Venta No Perdida'],
            marker_color='blue'
        )
    ])
    fig.update_layout(
        barmode='stack',
        title='Venta Perdida vs Venta Neta Total',
        xaxis_title='Semana Contable' if view == "semanal" else 'Mes',
        yaxis=dict(tickformat="$,d", title='Monto (Pesos)'),
        xaxis=dict(title='Tipo de Venta')
    )
    return fig

# Mostrar dashboard
if not venta_pr_data.empty:
    st.sidebar.title('📈📉 Dashboard de Venta Perdida')
    articulo = st.sidebar.text_input("Buscar artículo o familia de artículos 🚬")
    proveedores = st.sidebar.selectbox("Selecciona un proveedor 🏳️🏴🚩", options=[None] + venta_pr_data['PROVEEDOR'].unique().tolist())
    division = st.sidebar.selectbox("Selecciona una división 🗺️", options=[None] + venta_pr_data['DIVISIÓN'].unique().tolist())
    plaza = st.sidebar.selectbox("Selecciona una plaza 🏙️", options=[None] + venta_pr_data['PLAZA'].unique().tolist())
    categoria = st.sidebar.selectbox("Selecciona una categoría 🗃️", options=[None] + venta_pr_data['CATEGORIA'].unique().tolist())
    semana_opciones = [None] + sorted(venta_pr_data['Semana Contable'].unique())
    semana_seleccionada = st.sidebar.selectbox("Selecciona una semana 🗓️", options=semana_opciones)
    view = st.sidebar.radio("Selecciona la vista:", ("semanal", "mensual"))

    # Aplicar filtros
    filtered_data = apply_filters(venta_pr_data, proveedores, plaza, categoria, semana_seleccionada, division, articulo)
    
    # Verificar si hay datos filtrados
    st.write("Datos filtrados:", filtered_data.head())

    if not filtered_data.empty:
        if view == "semanal":
            filtered_data = apply_weekly_view(filtered_data)
        else:
            filtered_data = apply_monthly_view(filtered_data)

        if not filtered_data.empty:
            col1, col2 = st.columns((1, 1))
            with col1:
                st.markdown('#### 🧮 KPI´s de Venta Perdida ')
                total_venta_perdida = venta_pr_data['VENTA_PERDIDA_PESOS'].sum()
                total_venta_perdida_filtrada = filtered_data['VENTA_PERDIDA_PESOS'].sum()
                porcentaje_acumulado = (total_venta_perdida_filtrada / total_venta_perdida) * 100
                st.metric(label="Total Venta Perdida (21/6/2024-Presente)", value=f"${total_venta_perdida_filtrada:,.0f}")
                st.metric(label="Proporción de la Venta Perdida Filtrada al Total", value=f"{porcentaje_acumulado:.0f}%")
                st.markdown(f'#### 🕰️ Venta Perdida {view} ')
                st.plotly_chart(plot_venta_perdida(filtered_data, view), use_container_width=True)
            with col2:
                st.markdown('#### 📅 Venta Perdida Acumulada ')
                st.plotly_chart(make_donut_chart(filtered_data['VENTA_PERDIDA_PESOS'].sum(), total_venta_perdida, 'Acumulada', 'orange'), use_container_width=True)
            col3, col4 = st.columns((1, 1))
            with col3:
                st.markdown('#### 🏝️ Venta Perdida por Plaza ')
                st.plotly_chart(plot_venta_perdida_plaza(filtered_data), use_container_width=True)
            with col4:
                st.markdown('#### 🔝 Top 10 Artículos con Mayor Venta Perdida ')
                st.plotly_chart(plot_articulos_venta_perdida(filtered_data), use_container_width=True)
            col5, col6 = st.columns((1, 1))
            with col5:
                st.markdown('#### 🚩 Venta Perdida por Proveedor ')
                st.plotly_chart(plot_venta_perdida_proveedor(filtered_data, proveedores), use_container_width=True)
            col7, col8 = st.columns((1, 1))
            with col7:
                st.markdown('#### 🎢 Cambio porcentual de venta perdida ')
                st.plotly_chart(plot_venta_perdida_con_tendencia(filtered_data, view), use_container_width=True)
            with col8:
                st.markdown('#### 📶 Venta Perdida vs Venta Neta Total ')
                st.plotly_chart(plot_comparacion_venta_perdida_vs_neta(filtered_data, venta_pr_data, view), use_container_width=True)
            st.markdown(f'#### Venta Perdida {view} por Mercado')
            st.plotly_chart(plot_venta_perdida_mercado(filtered_data, view), use_container_width=True)
        else:
            st.warning("No se encontraron datos después de aplicar la vista semanal/mensual.")
    else:
        st.warning("No se encontraron datos filtrados.")
else:
    st.warning("No se encontraron datos en la carpeta especificada.")

