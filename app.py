import streamlit as st
import pandas as pd
from ortools.constraint_solver import pywrapcp, routing_enums_pb2
import math
import folium
from streamlit_folium import st_folium
from io import BytesIO
import requests

# ✅ SUA API KEY ORS
API_KEY = "eyJvcmciOiI1YjNjZTM1OTc4NTExMTAwMDFjZjYyNDgiLCJpZCI6ImRlYzE4OTZhMTQzNjQ1MDA5NWFkZTA2NTY4MDZjMDM0IiwiaCI6Im11cm11cjY0In0="

st.set_page_config(page_title="Roteirizador PRO API", layout="wide")
st.title("🗺️ Roteirizador com Rotas Reais (API)")

file = st.file_uploader("Enviar Excel", type=["xlsx"])

if "resultado" not in st.session_state:
    st.session_state.resultado = None

# 🔧 otimização local
def calcular_rota(df, inicio):
    coords = list(zip(df['lat'], df['lon']))

    def dist(a, b):
        return int(math.sqrt((a[0]-b[0])**2 + (a[1]-b[1])**2) * 100000)

    matrix = [[dist(a,b) for b in coords] for a in coords]

    manager = pywrapcp.RoutingIndexManager(len(matrix), 1, inicio)
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

# 🌍 rota real via API

def rota_real(coords):
    url = "https://api.openrouteservice.org/v2/directions/driving-car"

    body = {
        "coordinates": [[c[1], c[0]] for c in coords]
    }

    headers = {
        "Authorization": API_KEY,
        "Content-Type": "application/json"
    }

    response = requests.post(url, json=body, headers=headers)
    data = response.json()

    dist = data["features"][0]["properties"]["summary"]["distance"] / 1000
    tempo = data["features"][0]["properties"]["summary"]["duration"] / 60

    geometry = data["features"][0]["geometry"]["coordinates"]

    return dist, tempo, geometry


if file:
    df = pd.read_excel(file)
    df.columns = df.columns.str.lower()

    df['lat'] = pd.to_numeric(df['lat'].astype(str).str.replace(',', '.'), errors='coerce')
    df['lon'] = pd.to_numeric(df['lon'].astype(str).str.replace(',', '.'), errors='coerce')

    df = df.dropna(subset=['lat','lon'])

    if df.empty:
        st.error("Arquivo inválido")
        st.stop()

    st.dataframe(df)

    inicio = st.number_input("Ponto inicial", 0, len(df)-1, 0)

    col1, col2 = st.columns(2)

    if col1.button("Gerar rota real"):
        rota = calcular_rota(df, inicio)
        resultado = df.iloc[rota].reset_index(drop=True)

        coords = list(zip(resultado['lat'], resultado['lon']))
        dist, tempo, geometry = rota_real(coords)

        resultado['ordem'] = range(1, len(resultado)+1)

        st.session_state.resultado = (resultado, dist, tempo, geometry)

    if col2.button("Nova rota"):
        st.session_state.resultado = None


if st.session_state.resultado is not None:
    resultado, dist, tempo, geometry = st.session_state.resultado

    st.subheader("✅ Resultado")
    st.dataframe(resultado)

    st.success(f"Distância total: {dist:.2f} km")
    st.success(f"Tempo total: {tempo:.2f} min")

    # download
    buffer = BytesIO()
    resultado.to_excel(buffer, index=False, engine='openpyxl')

    st.download_button("📥 Baixar Excel", data=buffer.getvalue(), file_name="rota_real.xlsx")

    # mapa
    centro = [resultado['lat'].mean(), resultado['lon'].mean()]
    mapa = folium.Map(location=centro, zoom_start=7)

    rota_coords = [(c[1], c[0]) for c in geometry]
    folium.PolyLine(rota_coords, color="blue").add_to(mapa)

    for i,row in resultado.iterrows():
        folium.Marker([row['lat'], row['lon']], tooltip=f"Parada {i+1}").add_to(mapa)

    st_folium(mapa, width=800, height=500)
