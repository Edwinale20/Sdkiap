import os
import pandas as pd
import streamlit as st
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, timedelta

# Configuración de la página
st.set_page_config(page_title="Reporte de Venta Pérdida Cigarros y RRPS", page_icon="📊", layout="wide", initial_sidebar_state="expanded")

# Título de la aplicación
st.title("📊 Reporte de Venta Perdida Cigarros y RRPS")
st.markdown("En esta página podrás visualizar la venta pérdida día con día, por plaza, división, proveedor y otros datos que desees. Esto con el fin de dar acción y reducir la Venta pérdida")

# Ruta de la carpeta con los archivos CSV
folder_path = "venta"

# Función para procesar archivos en la carpeta especificada
def process_data(folder_path):
    all_files = [f for f in os.listdir(folder_path) if f.endswith('.csv')]
    all_data = []
    file_dates = []
    for file in all_files:
        try:
            date_str = file.split('.')[0]
            date = datetime.strptime(date_str, '%d%m%Y')
            df = pd.read_csv(os.path.join(folder_path, file), encoding='ISO-8859-1')
            df['Fecha'] = date
            all_data.append(df)
            file_dates.append(date)
        except Exception as e:
            st.write(f"Error leyendo el archivo {file}: {e}")
    if not all_data:
        return None, file_dates
    else:
        data = pd.concat(all_data)
        data['Fecha'] = pd.to_datetime(data['Fecha'])
        data['Semana'] = data['Fecha'].dt.isocalendar().week
        data.loc[data['DESC_ARTICULO'].str.contains('VUSE', case=False, na=False), 'CATEGORIA'] = '062 RRPs (Vapor y tabaco calentado)'

        # Renombrar proveedores y eliminar proveedor dummy
        proveedores_renombrados = {
            "1822 PHILIP MORRIS MEXICO, S.A. DE C.V.": "PMI",
            "1852 BRITISH AMERICAN TOBACCO MEXICO COMERCIAL, S.A. DE C.V.": "BAT",
            "6247 MAS BODEGA Y LOGISTICA, S.A. DE C.V.": "JTI",
            "21864 ARTICUN DISTRIBUIDORA S.A. DE C.V.": "Articun",
            "2216 NUEVA DISTABAC, S.A. DE C.V.": "Nueva Distabac",
            "8976 DRUGS EXPRESS, S.A DE C.V.": "Drugs Express",
            "1 PROVEEDOR DUMMY MIGRACION": "Eliminar"
        }
        data['PROVEEDOR'] = data['PROVEEDOR'].replace(proveedores_renombrados)
        data = data[data['PROVEEDOR'] != "Eliminar"]
        return data, file_dates

# Procesar archivos en la carpeta especificada
data, file_dates = process_data(folder_path)

# Función para aplicar los filtros
def apply_filters(data, proveedor, plaza, categoria, fecha, semana, division):
    if proveedor: data = data[data['PROVEEDOR'] == proveedor]
    if plaza: data = data[data['PLAZA'] == plaza]
    if categoria: data = data[data['CATEGORIA'] == categoria]
    if fecha: data = data[data['Fecha'] == fecha]
    if semana: data = data[data['Semana'] == semana]
    if division: data = data[data['DIVISION'] == division]
    return data

# Función para aplicar la vista acumulativa
def apply_accumulated_view(data):
    accumulated_data = data.copy()
    accumulated_data['VENTA_PERDIDA_PESOS'] = accumulated_data.groupby(['PLAZA', 'DESC_ARTICULO', 'DIVISION', 'NOMBRE_TIENDA'])['VENTA_PERDIDA_PESOS'].cumsum()
    return accumulated_data

# Función para gráfico de barras de VENTA_PERDIDA_PESOS por PLAZA
def plot_venta_perdida_plaza(data):
    if 'PLAZA' not in data.columns: return "No se encontraron datos para la columna 'PLAZA'."
    fig = go.Figure()
    grouped_data = data.groupby('PLAZA')['VENTA_PERDIDA_PESOS'].sum().reset_index()
    fig.add_trace(go.Bar(x=grouped_data['PLAZA'], y=grouped_data['VENTA_PERDIDA_PESOS'], marker_color='rgb(26, 118, 255)'))
    fig.update_layout(title='Venta Perdida por Plaza', xaxis_title='Plaza', yaxis_title='Venta Perdida (Pesos)', yaxis=dict(tickformat="$,d"))
    return fig

# Función para gráfico de los artículos con más venta perdida
def plot_articulos_venta_perdida(data):
    if 'DESC_ARTICULO' not in data.columns: return "No se encontraron datos para la columna 'DESC_ARTICULO'."
    fig = go.Figure()
    grouped_data = data.groupby('DESC_ARTICULO')['VENTA_PERDIDA_PESOS'].sum().reset_index()
    grouped_data = grouped_data.sort_values(by='VENTA_PERDIDA_PESOS', ascending=False).head(10)
    fig.add_trace(go.Bar(x=grouped_data['DESC_ARTICULO'], y=grouped_data['VENTA_PERDIDA_PESOS'], marker_color='rgb(55, 83, 109)'))
    fig.update_layout(title='Top 10 Artículos con mayor Venta Perdida', xaxis_title='Artículo', yaxis_title='Venta Perdida (Pesos)', yaxis=dict(tickformat="$,d"))
    return fig

# Función para gráfico de serie temporal de venta perdida por día
def plot_venta_perdida_tiempo(data, venta_pr_data):
    fig = go.Figure()
    grouped_data = data.groupby('Fecha')['VENTA_PERDIDA_PESOS'].sum().reset_index()
    fig.add_trace(go.Scatter(x=grouped_data['Fecha'], y=grouped_data['VENTA_PERDIDA_PESOS'], mode='lines+markers', name='Venta Perdida', line=dict(color='rgb(219, 64, 82)')))
    venta_pr_grouped = venta_pr_data.groupby('Día Contable')['Venta Neta Total'].sum().reset_index()
    fig.add_trace(go.Scatter(x=venta_pr_grouped['Día Contable'], y=venta_pr_grouped['Venta Neta Total'], mode='lines+markers', name='Venta Neta', line=dict(color='rgb(55, 128, 191)')))
    fig.update_layout(title='Venta Total vs Venta Perdida por Día', xaxis_title='Fecha', yaxis_title='Monto (Pesos)', yaxis=dict(tickformat="$,d"))
    return fig

# Función para gráfico de serie temporal de venta perdida por día
def plot_venta_perdida(data):
    fig = go.Figure()
    grouped_data = data.groupby('Fecha')['VENTA_PERDIDA_PESOS'].sum().reset_index()
    fig.add_trace(go.Scatter(x=grouped_data['Fecha'], y=grouped_data['VENTA_PERDIDA_PESOS'], mode='lines+markers', name='Venta Perdida', line=dict(color='rgb(219, 64, 82)')))
    fig.update_layout(title='Venta Perdida Diaria', xaxis_title='Fecha', yaxis_title='Monto (Pesos)', yaxis=dict(tickformat="$,d"))
    return fig

# Función para gráfico de barras de venta perdida por día con línea de tendencia de cambio porcentual
def plot_venta_perdida_con_tendencia(data):
    grouped_data = data.groupby('Fecha')['VENTA_PERDIDA_PESOS'].sum().reset_index()
    grouped_data['Cambio (%)'] = grouped_data['VENTA_PERDIDA_PESOS'].pct_change() * 100
    fig = go.Figure()
    fig.add_trace(go.Bar(x=grouped_data['Fecha'], y=grouped_data['VENTA_PERDIDA_PESOS'], name='Venta Perdida', marker_color='rgb(219, 64, 82)'))
    fig.add_trace(go.Scatter(x=grouped_data['Fecha'], y=grouped_data['Cambio (%)'], mode='lines+markers', name='Cambio Porcentual', line=dict(color='white'), yaxis='y2'))
    fig.update_layout(title='Venta Perdida por Día y Cambio Porcentual', xaxis_title='Fecha', yaxis=dict(title='Monto (Pesos)', tickformat="$,d"), yaxis2=dict(title='Cambio Porcentual (%)', overlaying='y', side='right', tickformat=".2f", showgrid=False), legend=dict(x=0, y=1.1, orientation='h'), barmode='group')
    return fig

# Función para gráfico de pastel de VENTA_PERDIDA_PESOS por PROVEEDOR
def plot_venta_perdida_proveedor(data, selected_proveedor=None):
    if 'PROVEEDOR' not in data.columns:
        return "No se encontraron datos para la columna 'PROVEEDOR'."
    
    grouped_data = data.groupby('PROVEEDOR')['VENTA_PERDIDA_PESOS'].sum().reset_index()
    colors = ['gold', 'mediumturquoise', 'darkorange', 'lightgreen', 'lightblue', 'pink', 'red', 'purple', 'brown', 'gray']
    
    pull = [0.2 if proveedor == selected_proveedor else 0 for proveedor in grouped_data['PROVEEDOR']]

    fig = go.Figure(data=[go.Pie(labels=grouped_data['PROVEEDOR'], values=grouped_data['VENTA_PERDIDA_PESOS'], pull=pull)])
    fig.update_traces(hoverinfo='label+percent', textinfo='value', textfont_size=20,
                      marker=dict(colors=colors, line=dict(color='#000000', width=2)))
    fig.update_layout(title='Venta Perdida por Proveedor')

    return fig

# Función para gráfico de comparación de Venta Perdida vs Venta Neta Total
def plot_comparacion_venta_perdida_vs_neta(data, venta_pr_data, filtro_fechas):
    filtered_venta_pr = venta_pr_data[venta_pr_data['Día Contable'].isin(filtro_fechas)]
    venta_perdida_total = data['VENTA_PERDIDA_PESOS'].sum()
    venta_neta_total = filtered_venta_pr['Venta Neta Total'].sum()
    venta_no_perdida = venta_neta_total - venta_perdida_total
    fig = go.Figure(data=[go.Bar(name='Venta Perdida', x=['Venta Total'], y=[venta_perdida_total], marker_color='red', text=f'${venta_perdida_total:,.0f}', textposition='inside'), go.Bar(name='Venta Neta Total', x=['Venta Total'], y=[venta_no_perdida], marker_color='blue', text=f'${venta_no_perdida:,.0f}', textposition='inside')])
    fig.update_layout(barmode='stack', title='Venta Perdida vs Venta Neta Total', yaxis=dict(tickformat="$,d", title='Monto (Pesos)'), xaxis=dict(title='Tipo de Venta'))
    return fig

# Función para gráfico de comparación de Venta Perdida vs Venta Neta Total día por día
def plot_comparacion_venta_perdida_vs_neta_diaria(data, venta_pr_data, filtro_fechas, view_percentage=False):
    filtered_venta_pr = venta_pr_data[venta_pr_data['Día Contable'].isin(filtro_fechas)]
    comparacion_diaria = data.groupby('Fecha')['VENTA_PERDIDA_PESOS'].sum().reset_index()
    comparacion_diaria = comparacion_diaria.merge(filtered_venta_pr.groupby('Día Contable')['Venta Neta Total'].sum().reset_index(), left_on='Fecha', right_on='Día Contable')
    if view_percentage:
        comparacion_diaria['Venta Perdida (%)'] = (comparacion_diaria['VENTA_PERDIDA_PESOS'] / (comparacion_diaria['VENTA_PERDIDA_PESOS'] + comparacion_diaria['Venta Neta Total'])) * 100
        comparacion_diaria['Venta Neta Total (%)'] = (comparacion_diaria['Venta Neta Total'] / (comparacion_diaria['VENTA_PERDIDA_PESOS'] + comparacion_diaria['Venta Neta Total'])) * 100
        fig = go.Figure(data=[go.Bar(name='Venta Perdida (%)', x=comparacion_diaria['Fecha'], y=comparacion_diaria['Venta Perdida (%)'], marker_color='red'), go.Bar(name='Venta Neta Total (%)', x=comparacion_diaria['Fecha'], y=comparacion_diaria['Venta Neta Total (%)'], marker_color='blue')])
        fig.update_layout(barmode='stack', title='Venta Perdida vs Venta Neta Total (Porcentaje)', xaxis_title='Fecha', yaxis_title='Porcentaje (%)')
    else:
        fig = go.Figure(data=[go.Bar(name='Venta Perdida', x=comparacion_diaria['Fecha'], y=comparacion_diaria['VENTA_PERDIDA_PESOS'], marker_color='red'), go.Bar(name='Venta Neta Total', x=comparacion_diaria['Fecha'], y=comparacion_diaria['Venta Neta Total'], marker_color='blue')])
        fig.update_layout(barmode='stack', title='Venta Perdida vs Venta Neta Total', xaxis_title='Fecha', yaxis_title='Monto (Pesos)', yaxis=dict(tickformat="$,d"))
    return fig

# Función para gráfico de donut
def make_donut_chart(value, total, title, color):
    percentage = (value / total) * 100
    fig = go.Figure(go.Pie(values=[value, total - value], labels=[title, 'Restante'], marker_colors=[color, '#E2E2E2'], hole=0.7, textinfo='percent+label', hoverinfo='label+percent'))
    fig.update_traces(texttemplate='%{percent:.0f}%', textposition='inside')
    fig.update_layout(showlegend=False, margin=dict(t=0, b=0, l=0, r=0), height=200, width=200)
    return fig

# Función para procesar el archivo de Venta PR
@st.cache_data
def load_venta_pr(file_path):
    df = pd.read_excel(file_path)
    df['Día Contable'] = pd.to_datetime(df['Día Contable'], format='%d/%m/%Y')
    return df

venta_pr_path = "venta/Venta PR.xlsx"

# Procesar archivos en la carpeta especificada
data, file_dates = process_data(folder_path)
venta_pr_data = load_venta_pr(venta_pr_path)

# Función para gráfico de venta perdida por día y por mercado
def plot_venta_perdida_mercado(data):
    if 'MERCADO' not in data.columns or 'DIVISION' not in data.columns or 'PLAZA' not in data.columns: return "No se encontraron datos suficientes para 'MERCADO', 'DIVISION' o 'PLAZA'."
    fig = go.Figure()
    mercados = data['MERCADO'].unique()
    for mercado in mercados:
        mercado_data = data[data['MERCADO'] == mercado]
        grouped_data = mercado_data.groupby('Fecha')['VENTA_PERDIDA_PESOS'].sum().reset_index()
        fig.add_trace(go.Scatter(x=grouped_data['Fecha'], y=grouped_data['VENTA_PERDIDA_PESOS'], mode='lines+markers', name=mercado))
    fig.update_layout(title='Venta Perdida por Día y por Mercado', xaxis_title='Fecha', yaxis_title='Venta Perdida (Pesos)', yaxis=dict(tickformat="$,d"))
    return fig

# Mostrar dashboard si hay datos disponibles
if data is not None:
    st.sidebar.title('Configuración del Dashboard')
    proveedores = st.sidebar.selectbox("Selecciona un proveedor", options=[None] + data['PROVEEDOR'].unique().tolist())
    plaza = st.sidebar.selectbox("Selecciona una plaza", options=[None] + data['PLAZA'].unique().tolist())
    categoria = st.sidebar.selectbox("Selecciona una categoría", options=[None] + data['CATEGORIA'].unique().tolist())
    division = st.sidebar.selectbox("Selecciona una división", options=[None] + data['DIVISION'].unique().tolist())
    semana_opciones = [None] + sorted(data['Semana'].unique())
    semana_seleccionada = st.sidebar.selectbox("Selecciona una semana", options=semana_opciones)
    vista = st.sidebar.radio("Selecciona la vista:", ("Diaria", "Acumulada"))
    filtered_data = apply_filters(data, proveedores, plaza, categoria, None, semana_seleccionada, division)
    if vista == "Acumulada": filtered_data = apply_accumulated_view(filtered_data)
    col1, col2 = st.columns((1, 1))
    with col1:
        st.markdown('#### Venta Perdida Total 🧮')
        total_venta_perdida = data['VENTA_PERDIDA_PESOS'].sum()
        total_venta_perdida_filtrada = filtered_data['VENTA_PERDIDA_PESOS'].sum()
        porcentaje_acumulado = (total_venta_perdida_filtrada / total_venta_perdida) * 100
        comparacion_diaria = filtered_data.groupby('Fecha')['VENTA_PERDIDA_PESOS'].sum().reset_index()
        comparacion_diaria = comparacion_diaria.merge(venta_pr_data.groupby('Día Contable')['Venta Neta Total'].sum().reset_index(), left_on='Fecha', right_on='Día Contable')
        if not comparacion_diaria.empty:
            porcentaje_venta_perdida_dia = (comparacion_diaria['VENTA_PERDIDA_PESOS'] / (comparacion_diaria['VENTA_PERDIDA_PESOS'] + comparacion_diaria['Venta Neta Total'])) * 100
            st.metric(label="Total Venta Perdida", value=f"${total_venta_perdida_filtrada:,.0f}")
            st.metric(label="% Acumulado", value=f"{porcentaje_acumulado:.2f}%")
            st.metric(label="% Venta Perdida del Día", value=f"{porcentaje_venta_perdida_dia.iloc[-1]:.2f}%")
        else:
            st.metric(label="Total Venta Perdida", value=f"${total_venta_perdida_filtrada:,.0f}")
            st.metric(label="% Acumulado", value=f"{porcentaje_acumulado:.2f}%")
            st.metric(label="% Venta Perdida del Día", value="N/A")
        st.markdown('#### Venta Perdida diaria')
        venta_perdida_dia_chart = plot_venta_perdida(filtered_data)
        st.plotly_chart(venta_perdida_dia_chart, use_container_width=True)
    with col2:
        st.markdown('#### Venta Perdida Acumulada 📅')
        total_venta_perdida_acumulada = filtered_data['VENTA_PERDIDA_PESOS'].sum()
        venta_perdida_acumulada_chart = make_donut_chart(total_venta_perdida_acumulada, total_venta_perdida, 'Acumulada', 'orange')
        st.plotly_chart(venta_perdida_acumulada_chart, use_container_width=True)
    col3, col4 = st.columns((1, 1))
    with col3:
        st.markdown('#### Venta Perdida vs Venta Neta Total')
        comparacion_chart = plot_comparacion_venta_perdida_vs_neta(filtered_data, venta_pr_data, filtered_data['Fecha'])
        st.plotly_chart(comparacion_chart, use_container_width=True)
    with col4:
        st.markdown('#### Venta Perdida por Plaza')
        venta_perdida_plaza_chart = plot_venta_perdida_plaza(filtered_data)
        st.plotly_chart(venta_perdida_plaza_chart, use_container_width=True)
    col5, col6 = st.columns((1, 1))
    with col5:
        st.markdown('#### Top 10 Artículos con Mayor Venta Perdida')
        articulos_venta_perdida_chart = plot_articulos_venta_perdida(filtered_data)
        st.plotly_chart(articulos_venta_perdida_chart, use_container_width=True)
    with col6:
        st.markdown('#### Venta Perdida por Proveedor')
        selected_proveedor = proveedores  # Obtener el proveedor seleccionado para el gráfico de pastel
        venta_perdida_proveedor_chart = plot_venta_perdida_proveedor(filtered_data, selected_proveedor)
        st.plotly_chart(venta_perdida_proveedor_chart, use_container_width=True)
    col7, col8 = st.columns((1, 1))
    with col7:
        st.markdown('#### Cambio porcentual de venta perdida')
        articulos_por_division_chart = plot_venta_perdida_con_tendencia(filtered_data)
        st.plotly_chart(articulos_por_division_chart, use_container_width=True)
    with col8:
        st.markdown('#### Venta Perdida vs Venta Neta Total')
        comparacion_diaria_chart = plot_comparacion_venta_perdida_vs_neta_diaria(filtered_data, venta_pr_data, filtered_data['Fecha'])
        st.plotly_chart(comparacion_diaria_chart, use_container_width=True)
    st.markdown('#### Venta Perdida diaria por Mercado')
    venta_perdida_mercado_chart = plot_venta_perdida_mercado(filtered_data)
    st.plotly_chart(venta_perdida_mercado_chart, use_container_width=True)
else:
    st.warning("No se encontraron datos en la carpeta especificada.")
