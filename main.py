from fastapi import FastAPI, UploadFile, File
from supabase import create_client
import pandas as pd
import io
import os

app = FastAPI()

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")

supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

@app.get("/")
def home():
    return {"status": "Backend funcionando"}

@app.post("/upload/{nome_empreendimento}")
async def upload_excel(nome_empreendimento: str, file: UploadFile = File(...)):

    contents = await file.read()

    df_dist = pd.read_excel(io.BytesIO(contents), sheet_name="Distribuição da verba")
    df_real = pd.read_excel(io.BytesIO(contents), sheet_name="Verba Real Gasta")

    vgv = df_dist[df_dist.iloc[:,0].astype(str).str.contains("VGV", na=False)].iloc[:,1].values[0]
    verba_total = df_dist[df_dist.iloc[:,0].astype(str).str.contains("Verba", na=False)].iloc[:,1].values[0]

    emp = supabase.table("empreendimentos").insert({
        "nome": nome_empreendimento,
        "vgv": float(vgv),
        "verba_total": float(verba_total)
    }).execute()

    empreendimento_id = emp.data[0]["id"]

    fases = []
    fase_atual = None

    for _, row in df_real.iterrows():
        primeira_coluna = str(row.iloc[0]).strip()

        if primeira_coluna.isupper() and "SALDO" not in primeira_coluna:
            fase_atual = {
                "nome_fase": primeira_coluna,
                "saldo_inicial": 0,
                "saldo_final": 0,
                "total_gasto": 0
            }
            fases.append(fase_atual)
            continue

        if "Saldo Inicial" in primeira_coluna:
            fase_atual["saldo_inicial"] = abs(float(row.iloc[1]))
            continue

        if "Saldo Final" in primeira_coluna:
            fase_atual["saldo_final"] = abs(float(row.iloc[1]))
            continue

        if fase_atual and isinstance(row.iloc[1], (int, float)):
            fase_atual["total_gasto"] += abs(float(row.iloc[1]))

    for fase in fases:
        supabase.table("fases").insert({
            "empreendimento_id": empreendimento_id,
            "nome_fase": fase["nome_fase"],
            "saldo_inicial": fase["saldo_inicial"],
            "saldo_final": fase["saldo_final"],
            "total_gasto": fase["total_gasto"]
        }).execute()

    return {"status": "Upload processado com sucesso"}
