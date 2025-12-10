#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Dashboard Financeiro em Streamlit
Versão completa com gráficos atualizados em tons pastel e barras empilhadas por tipo
"""
import os
import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import datetime
from supabase import create_client, Client
import hashlib

# ==============================
# CONFIGURAÇÃO DO SUPABASE
# ==============================
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

# ==============================
# CONFIGURAÇÃO DE ESTILO
# ==============================
st.set_page_config(
    page_title="Dashboard Financeiro",
    page_icon="💰",
    layout="wide",
    initial_sidebar_state="expanded"
)

st.markdown("""
<style>
.main { padding-top: 0rem; }
.stMetric { padding: 10px; border-radius: 10px; text-align: center; }
</style>
""", unsafe_allow_html=True)

# ==============================
# FUNÇÕES DE BANCO
# ==============================
def login(email: str, senha: str):
    senha_hash = hashlib.sha256(senha.encode()).hexdigest()
    res = supabase.table("users").select("*").eq("email", email).eq("senha", senha_hash).execute()
    if res.data:
        return True, res.data[0]
    return False, None

def criar_usuario(nome: str, email: str, senha: str):
    senha_hash = hashlib.sha256(senha.encode()).hexdigest()
    return supabase.table("users").insert({
        "nome": nome,
        "email": email,
        "senha": senha_hash
    }).execute()

def listar_installments(user_id: str):
    res = supabase.table("installments").select("*").eq("user_id", user_id).order("data_vencimento", desc=False).execute()
    return res.data

def inserir_parcelas_futuras(user_id, tipo, descricao, valor, data_venc, parcelas, cartao):
    from dateutil.relativedelta import relativedelta
    for num in range(1, parcelas + 1):
        venc = data_venc + relativedelta(months=num-1)
        supabase.table("installments").insert({
            "user_id": user_id,
            "tipo": tipo,
            "descricao": descricao,
            "valor": float(valor),
            "data_vencimento": venc.strftime("%Y-%m-%d"),
            "numero_parcela": parcelas,
            "parcela_atual": num,
            "cartao": cartao
        }).execute()

# ==============================
# INICIALIZAÇÃO DE SESSÃO
# ==============================
if "user" not in st.session_state:
    st.session_state.user = None

# ==============================
# LOGIN / REGISTRO
# ==============================
if st.session_state.user is None:
    col1, col2, col3 = st.columns([1,2,1])
    with col2:
        st.image("https://via.placeholder.com/200?text=Financeiro", width=100)
        st.title("💰 FinanceApp")
        tab_login, tab_registro = st.tabs(["Login", "Registrar"])
        
        with tab_login:
            st.subheader("Fazer Login")
            email_login = st.text_input("Email", key="email_login")
            senha_login = st.text_input("Senha", type="password", key="senha_login")
            if st.button("Entrar", use_container_width=True, type="primary"):
                ok, user = login(email_login, senha_login)
                if ok:
                    st.session_state.user = user
                    st.success(f"Bem-vindo, {user['nome']}!")
                    st.rerun()
                else:
                    st.error("Email ou senha incorretos!")
        
        with tab_registro:
            st.subheader("Criar Conta")
            nome_cad = st.text_input("Nome", key="nome_cad")
            email_cad = st.text_input("Email", key="email_cad")
            senha_cad = st.text_input("Senha", type="password", key="senha_cad")
            if st.button("Criar Conta", use_container_width=True, type="primary"):
                if nome_cad and email_cad and senha_cad:
                    try:
                        criar_usuario(nome_cad, email_cad, senha_cad)
                        st.success("Conta criada com sucesso! Faça login.")
                    except Exception as e:
                        st.error(f"Erro ao criar conta: {e}")
                else:
                    st.warning("Preencha todos os campos!")

# ==============================
# DASHBOARD PRINCIPAL
# ==============================
else:
    user = st.session_state.user
    col_title, col_logout = st.columns([0.9,0.1])
    with col_title:
        st.title(f"💰 Dashboard Financeiro - {user['nome']}")
    with col_logout:
        if st.button("Sair"):
            st.session_state.user = None
            st.rerun()
    st.divider()
    
    # ==============================
    # SIDEBAR
    # ==============================
    with st.sidebar:
        st.header("🔍 Filtros")
        dados = listar_installments(user["id"])
        if not dados:
            st.warning("Nenhum lançamento encontrado!")
        else:
            df = pd.DataFrame(dados)
            df["data_vencimento"] = pd.to_datetime(df["data_vencimento"])
            df["valor"] = pd.to_numeric(df["valor"], errors="coerce").fillna(0.0)
            df["ano"] = df["data_vencimento"].dt.strftime("%Y")
            df["mes_num"] = df["data_vencimento"].dt.strftime("%m")
            # nome do mês + ano no formato "novembro de 2025"
            df["mes_label"] = df["data_vencimento"].dt.strftime("%B de %Y")
            
            # Filtros
            anos = sorted(df["ano"].unique(), reverse=True)
            ano_sel = st.selectbox("Ano:", anos, index=0)
            meses_disponiveis = sorted(df[df["ano"] == ano_sel]["mes_num"].unique())
            mes_sel = st.multiselect("Mês:", meses_disponiveis, default=meses_disponiveis)
            tipos = sorted(df["tipo"].dropna().unique
