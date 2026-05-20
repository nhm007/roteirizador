import streamlit as st
import pandas as pd
from ortools.constraint_solver import pywrapcp, routing_enums_pb2
import math

st.set_page_config(page_title="Roteirizador", layout="wide")

st.title("Roteirizador Simples (OK)")

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
    params.first_solution_strategy = routing_enums_pb2.FirstSolutionStrategy.PATH_CHEAPEST_ARC

    solution = routing.SolveWithParameters(params)

    rota=[]
    idx = routing.Start(0)
    while not routing.IsEnd(idx):
        rota.append(manager.IndexToNode(idx))
        idx = solution.Value(routing.NextVar(idx))

    return rota

if file:
    df = pd.read_excel(file)
    df.columns = df.columns.str.lower()

    df['lat'] = pd.to_numeric(df['lat'], errors='coerce')
    df['lon'] = pd.to_numeric(df['lon'], errors='coerce')

    df = df.dropna(subset=['lat','lon'])

    if df.empty:
        st.error("Arquivo inválido")
        st.stop()

    st.dataframe(df)

    if st.button("Gerar rota"):
        rota = calcular_rota(df)
        st.dataframe(df.iloc[rota].reset_index(drop=True))
        st.success("OK")
