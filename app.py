import streamlit as st
import pandas as pd
from ortools.constraint_solver import pywrapcp, routing_enums_pb2
import math
import folium
from streamlit_folium import st_folium

st.set_page_config(page_title="Roteirizador", layout="wide")

st.title("🗺️ Roteirizador com Mapa")

file = st.file_uploader("Enviar Excel", type=["xlsx"])

def calcular_rota(df):
    coords = list(zip(df['lat'], df['lon']))

    def dist(a, b):
        return int(math.sqrt((a[0]-b[0])**2 + (a[1]-b[1])**2) * 100000)

    matrix = [[dist(a,b) for b in coords] for a in coords]

    manager = pywrapcp.RoutingIndexManager(len(matrix), 1, 0)
    routing = pywrapcp.RoutingModel(manager)

    def callback(i,j):
        return matrix[manager.IndexToNode(i)][manager.IndexToNode(j)]

    transit = routing.RegisterTransitCallback(callback)
    routing.SetArcCostEvaluatorOfAllVehicles(transit)

    params = pywrapcp.DefaultRoutingSearchParameters()
    params.first_solution_strategy = routing_enums_pb2.FirstSolutionStrategy.AUTOMATIC
    params.local_search_metaheuristic = routing_enums_pb2.LocalSearchMetaheuristic.GUIDED_LOCAL_SEARCH
    params.time_limit.seconds = 5

    solution = routing.SolveWithParameters(params)

    rota = []
    idx = routing.Start(0)
    while not routing.IsEnd(idx):
        rota.append(manager.IndexToNode(idx))
        idx = solution.Value(routing.NextVar(idx))

    return rota

if file:
    df = pd.read_excel(file)

    df.columns = df.columns.str.lower()

    df['lat'] = df['lat'].astype(str).str.replace(',', '.')
    df['lon'] = df['lon'].astype(str).str.replace(',', '.')

    df['lat'] = pd.to_numeric(df['lat'], errors='coerce')
    df['lon'] = pd.to_numeric(df['lon'], errors='coerce')

    df = df.dropna(subset=['lat','lon'])

    if df.empty:
        st.error("Arquivo inválido")
        st.stop()

    st.dataframe(df)

    if st.button("Gerar rota"):
        rota = calcular_rota(df)
        resultado = df.iloc[rota].reset_index(drop=True)

        st.subheader("Ordem otimizada")
        st.dataframe(resultado)

        centro = [resultado['lat'].mean(), resultado['lon'].mean()]
        mapa = folium.Map(location=centro, zoom_start=7)

        pontos = []

        for i,row in resultado.iterrows():
            lat,lon = row['lat'], row['lon']
            pontos.append((lat,lon))

            folium.Marker([lat,lon], tooltip=f"Parada {i+1}").add_to(mapa)

        folium.PolyLine(pontos).add_to(mapa)

        st_folium(mapa, width=800, height=500)
