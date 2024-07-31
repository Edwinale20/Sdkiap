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

    # Verificar si las columnas clave están presentes
    if 'Semana Contable' not in df.columns or 'Venta Neta Total' not in df.columns:
        st.error("Las columnas 'Semana Contable' o 'Venta Neta Total' no se encontraron en los datos de 'Venta PR'")
        return pd.DataFrame()  # Retorna un DataFrame vacío en caso de error
    return df

# Cargar datos
venta_pr_data = load_venta_pr(venta_pr_path)

# Verifica si los datos se cargaron correctamente antes de continuar
if venta_pr_data.empty:
    st.error("No se pudo cargar los datos desde 'Venta PR.xlsx'")
    st.stop()

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
    if 'VENTA_PERDIDA_PESOS' in data.columns:
        weekly_data = data.groupby(['Semana Contable', 'PROVEEDOR', 'PLAZA', 'CATEGORIA', 'DIVISIÓN', 'ID_ARTICULO']).agg({'VENTA_PERDIDA_PESOS': 'sum'}).reset_index()
        return weekly_data
    else:
        st.error("La columna 'VENTA_PERDIDA_PESOS' no se encontró en los datos.")
        return pd.DataFrame()  # Retorna un DataFrame vacío en caso de error

# Function to apply monthly view
def apply_monthly_view(data):
    data['Mes'] = pd.to_datetime(data['Semana Contable'], format='%Y%U').dt.to_period('M')
    monthly_data = data.groupby(['Mes', 'PROVEEDOR', 'PLAZA', 'CATEGORIA', 'DIVISIÓN', 'ID_ARTICULO']).agg({'VENTA_PERDIDA_PESOS': 'sum'}).reset_index()
    return monthly_data

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

# Function to plot venta perdida por plaza
def plot_venta_perdida_plaza(data):
    fig = go.Figure()
    grouped_data = data.groupby('PLAZA')['VENTA_PERDIDA_PESOS'].sum().reset_index()
    
    fig.add_trace(go.Bar(
        x=grouped_data['PLAZA'], 
        y=grouped_data['VENTA_PERDIDA_PESOS'], 
        marker_color='rgb(26, 118, 255)',
        text=grouped_data['VENTA_PERDIDA_PESOS'],
        texttemplate='%{text:$,.2f}',
        hovertemplate='Venta Perdida: %{text:$,.2f}<br>%{y:.2f}%'
    ))
    
    fig.update_layout(
        title='Venta Perdida por Plaza',
        xaxis_title='Plaza',
        yaxis_title='Venta Perdida (Pesos)',
        yaxis=dict(tickformat="$,d")
    )
    
    return fig

# Function to plot top 10 artículos con mayor venta perdida
def plot_articulos_venta_perdida(data):
    fig = go.Figure()
    grouped_data = data.groupby('ID_ARTICULO')['VENTA_PERDIDA_PESOS'].sum().reset_index()
    grouped_data = grouped_data.sort_values(by='VENTA_PERDIDA_PESOS', ascending=False).head(10)
    fig.add_trace(go.Bar(
        x=grouped_data['ID_ARTICULO'], 
        y=grouped_data['VENTA_PERDIDA_PESOS'], 
        marker_color='rgb(55, 83, 109)',
        text=grouped_data['VENTA_PERDIDA_PESOS'],
        texttemplate='%{text:$,.2f}',
        hovertemplate='Venta Perdida: %{text:$,.2f}<br>%{y:.2f}%'
    ))
    fig.update_layout(
        title='Top 10 Artículos con mayor Venta Perdida',
        xaxis_title='Artículo',
        yaxis_title='Venta Perdida (Pesos)',
        yaxis=dict(tickformat="$,d")
    )
    return fig

# Function to plot venta perdida por semana/mes
def plot_venta_perdida(data, view):
    fig = go.Figure()
    if view == "semanal":
        grouped_data = data.groupby('Semana Contable')['VENTA_PERDIDA_PESOS'].sum().reset_index()
        x_title = 'Semana Contable'
    else:
        grouped_data = data.groupby('Mes')['VENTA_PERDIDA_PESOS'].sum().reset_index()
        x_title = 'Mes'
    fig.add_trace(go.Scatter(
        x=grouped_data[x_title], 
        y=grouped_data['VENTA_PERDIDA_PESOS'], 
        mode='lines+markers', 
        name='Venta Perdida',
        line=dict(color='rgb(219, 64, 82)'),
        text=grouped_data['VENTA_PERDIDA_PESOS'],
        texttemplate='%{text:$,.2f}',
        hovertemplate='Venta Perdida: %{text:$,.2f}<br>%{y:.2f}%'
    ))
    fig.update_layout(
        title=f'Venta Perdida por {x_title}',
        xaxis_title=x_title,
        yaxis_title='Monto (Pesos)',
        yaxis=dict(tickformat="$,d")
    )
    return fig

# Function to plot venta perdida con tendencia
def plot_venta_perdida_con_tendencia(data, view):
    if view == "semanal":
        grouped_data = data.groupby('Semana Contable')['VENTA_PERDIDA_PESOS'].sum().reset_index()
        x_title = 'Semana Contable'
    else:
        grouped_data = data.groupby('Mes')['VENTA_PERDIDA_PESOS'].sum().reset_index()
        x_title = 'Mes'
    grouped_data['Cambio (%)'] = grouped_data['VENTA_PERDIDA_PESOS'].pct_change() * 100
    fig = go.Figure()
    fig.add_trace(go.Bar(
        x=grouped_data[x_title], 
        y=grouped_data['VENTA_PERDIDA_PESOS'], 
        name='Venta Perdida', 
        marker_color='rgb(219, 64, 82)',
        text=grouped_data['VENTA_PERDIDA_PESOS'],
        texttemplate='%{text:$,.2f}',
        hovertemplate='Venta Perdida: %{text:$,.2f}<br>%{y:.2f}%'
    ))
    fig.add_trace(go.Scatter(
        x=grouped_data[x_title], 
        y=grouped_data['Cambio (%)'], 
        mode='lines+markers', 
        name='Cambio Porcentual', 
        line=dict(color='white'), 
        yaxis='y2'
    ))
    fig.update_layout(
        title=f'Venta Perdida por {x_title} y Cambio Porcentual',
        xaxis_title=x_title,
        yaxis=dict(title='Monto (Pesos)', tickformat="$,d"),
        yaxis2=dict(title='Cambio Porcentual (%)', overlaying='y', side='right', tickformat=".2f", showgrid=False),
        legend=dict(x=0, y=1.1, orientation='h'),
        barmode='group'
    )
    return fig

# Function to plot venta perdida por proveedor
def plot_venta_perdida_proveedor(data, selected_proveedor=None):
    grouped_data = data.groupby('PROVEEDOR')['VENTA_PERDIDA_PESOS'].sum().reset_index()
    colors = ['gold', 'mediumturquoise', 'darkorange', 'lightgreen', 'lightblue', 'pink', 'red', 'purple', 'brown', 'gray']
    pull = [0.2 if proveedor == selected_proveedor else 0 for proveedor in grouped_data['PROVEEDOR']]
    fig = go.Figure(data=[go.Pie(
        labels=grouped_data['PROVEEDOR'], 
        values=grouped_data['VENTA_PERDIDA_PESOS'], 
        pull=pull,
        text=grouped_data['VENTA_PERDIDA_PESOS'],
        texttemplate='%{text:$,.2f}',
        hovertemplate='Venta Perdida: %{text:$,.2f}<br>%{y:.2f}%'
    )])
    fig.update_traces(
        hoverinfo='label+percent', 
        textinfo='value', 
        textfont_size=20, 
        marker=dict(colors=colors, line=dict(color='#000000', width=2))
    )
    fig.update_layout(title='Venta Perdida por Proveedor')
    return fig

# Function to make a donut chart
def make_donut_chart(value, total, title, color):
    fig = go.Figure(go.Pie(
        values=[value, total - value], 
        labels=[title, 'Restante'], 
        marker_colors=[color, '#E2E2E2'], 
        hole=0.7, 
        textinfo='label', 
        hoverinfo='label+percent'
    ))
    fig.update_traces(texttemplate='', textposition='inside')
    fig.update_layout(
        title="Proporción de la Venta Perdida Filtrada respecto al Total",
        showlegend=True,
        margin=dict(t=50, b=0, l=0, r=0),
        height=300,
        width=300
    )
    return fig

# Function to plot venta perdida por mercado
def plot_venta_perdida_mercado(data, view):
    fig = go.Figure()
    if view == "semanal":
        grouped_data = data.groupby(['Semana Contable', 'MERCADO'])['VENTA_PERDIDA_PESOS'].sum().reset_index()
        x_title = 'Semana Contable'
    else:
        grouped_data = data.groupby(['Mes', 'MERCADO'])['VENTA_PERDIDA_PESOS'].sum().reset_index()
        x_title = 'Mes'
    mercados = grouped_data['MERCADO'].unique()
    for mercado in mercados:
        mercado_data = grouped_data[grouped_data['MERCADO'] == mercado]
        fig.add_trace(go.Scatter(
            x=mercado_data[x_title], 
            y=mercado_data['VENTA_PERDIDA_PESOS'], 
            mode='lines+markers', 
            name=mercado,
            text=mercado_data['VENTA_PERDIDA_PESOS'],
            texttemplate='%{text:$,.2f}',
            hovertemplate='Venta Perdida: %{text:$,.2f}<br>%{y:.2f}%'
        ))
    fig.update_layout(
        title=f'Venta Perdida por {x_title} y por Mercado',
        xaxis_title=x_title,
        yaxis_title='Venta Perdida (Pesos)',
        yaxis=dict(tickformat="$,d")
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
    if view == "semanal":
        filtered_data = apply_weekly_view(filtered_data)
    else:
        filtered_data = apply_monthly_view(filtered_data)

    # Verificar si hay datos filtrados
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
        st.warning("No se encontraron datos filtrados.")
else:
    st.warning("No se encontraron datos en la carpeta especificada.")
