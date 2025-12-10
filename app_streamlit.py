#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Dashboard Financeiro em Streamlit
Versão completa com gráfico de barras empilhadas atualizado
"""
import os
import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import datetime
from supabase import create_client, Client
import hashlib
from dateutil.relativedelta import relativedelta

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
            df["mes_nome"] = df["data_vencimento"].dt.strftime("%B")
            
            # Filtros
            anos = sorted(df["ano"].unique(), reverse=True)
            ano_sel = st.selectbox("Ano:", anos, index=0)
            meses_disponiveis = sorted(df[df["ano"]==ano_sel]["mes_num"].unique())
            mes_sel = st.multiselect("Mês:", meses_disponiveis, default=meses_disponiveis)
            tipos = sorted(df["tipo"].dropna().unique())
            tipo_sel = st.multiselect("Tipo:", tipos, default=tipos)
            cartoes = sorted(df["cartao"].fillna("").unique())
            cartao_sel = st.multiselect("Cartão:", cartoes, default=cartoes)
            
            df_filtrado = df[
                (df["ano"]==ano_sel) &
                (df["mes_num"].isin(mes_sel)) &
                (df["tipo"].isin(tipo_sel)) &
                (df["cartao"].isin(cartao_sel))
            ]
            
            # ==============================
            # NOVO LANÇAMENTO
            # ==============================
            st.divider()
            st.subheader("➕ Novo Lançamento")
            with st.form("form_novo_lancamento"):
                tipo_novo = st.selectbox(
                    "Tipo:", ["Mercado","Alimentação","Saude","Transporte","Carro","Casa","Emprestimo","Roupa","Lazer"], key="tipo_novo"
                )
                desc_novo = st.text_input("Descrição", key="desc_novo")
                valor_novo = st.number_input("Valor", min_value=0.0, step=0.01, key="valor_novo")
                data_novo = st.date_input("Data de Vencimento", key="data_novo")
                parcelas_novo = st.number_input("Parcelas", min_value=1, value=1, key="parcelas_novo")
                cartao_novo = st.text_input("Cartão", key="cartao_novo")
                submitted = st.form_submit_button("Adicionar", use_container_width=True, type="primary")
                if submitted:
                    try:
                        inserir_parcelas_futuras(
                            user["id"], tipo_novo, desc_novo, valor_novo,
                            datetime.combine(data_novo, datetime.min.time()),
                            int(parcelas_novo), cartao_novo
                        )
                        st.success("Lançamento adicionado!")
                        st.rerun()
                    except Exception as e:
                        st.error(f"Erro ao adicionar: {e}")

    # ==============================
    # KPIs OTIMIZADOS
    # ==============================
    if not df_filtrado.empty:
        total_geral = df["valor"].sum()
        total_filtrado = df_filtrado["valor"].sum()
        media = df_filtrado["valor"].mean()
        num_transacoes = len(df_filtrado)
        total_parceladas_valor = df_filtrado[df_filtrado["numero_parcela"]>1]["valor"].sum()
        perc_parceladas_valor = (total_parceladas_valor / total_filtrado * 100) if total_filtrado>0 else 0
        
        kpi_cols = st.columns(5)
        kpi_cols[0].metric("💵 Total Geral", f"R$ {total_geral:,.2f}".replace(',', '_').replace('.', ',').replace('_', '.'))
        kpi_cols[1].metric("📊 Total Filtrado", f"R$ {total_filtrado:,.2f}".replace(',', '_').replace('.', ',').replace('_', '.'))
        kpi_cols[2].metric("📈 Média", f"R$ {media:,.2f}".replace(',', '_').replace('.', ',').replace('_', '.'))
        kpi_cols[3].metric("📋 Transações", num_transacoes)
        kpi_cols[4].metric("📦 % Parceladas", f"{perc_parceladas_valor:.2f}%")
        st.divider()
        
        # ==============================
        # GRÁFICOS
        # ==============================
        col1, col2 = st.columns([0.5,0.5])
        with col1:
            st.subheader("💧 Gastos por Tipo (Donut)")
            df_tipo = df_filtrado.groupby("tipo")["valor"].sum().reset_index()
            fig_pie = px.pie(df_tipo, names="tipo", values="valor", hole=0.4,
                             color_discrete_sequence=px.colors.qualitative.Pastel,
                             hover_data={"valor": ":.2f"})
            fig_pie.update_traces(textposition='inside', textinfo='percent+label')
            st.plotly_chart(fig_pie, use_container_width=True)
        
        with col2:
            st.subheader("📅 Gastos por Mês")
            df_mes = df.groupby(df["data_vencimento"].dt.to_period("M"))["valor"].sum().reset_index()
            df_mes.columns = ["mes", "valor"]
            df_mes["mes"] = df_mes["mes"].astype(str)
            fig_bar = px.bar(
                df_mes,
                x="mes",
                y="valor",
                color="mes",
                color_discrete_sequence=px.colors.qualitative.Pastel,
                hover_data={"valor": ":.2f"}
            )
            fig_bar.update_layout(showlegend=False, xaxis_title="Mês", yaxis_title="R$")
            st.plotly_chart(fig_bar, use_container_width=True)
        
        # ==============================
        # GRÁFICO BARRA EMPILHADA POR MÊS E TIPO
        # ==============================
        st.subheader("📊 Gastos Mensais por Tipo (Ano Selecionado)")
        df_mes_tipo = df_filtrado.groupby([df_filtrado["data_vencimento"].dt.to_period("M"), "tipo"])["valor"].sum().reset_index()
        df_mes_tipo["mes_ano"] = df_mes_tipo["data_vencimento"].dt.strftime("%B de %Y")
        df_mes_tipo.sort_values("data_vencimento", inplace=True)
        
        fig_stacked_tipo = px.bar(
            df_mes_tipo,
            x="mes_ano",
            y="valor",
            color="tipo",
            text=df_mes_tipo["tipo"] + ": R$" + df_mes_tipo["valor"].map(lambda x: f"{x:,.2f}".replace(',', '_').replace('.', ',').replace('_', '.')),
            barmode="stack",
            color_discrete_sequence=px.colors.qualitative.Pastel,
            hover_data={"valor": ":.2f"}
        )
        fig_stacked_tipo.update_layout(xaxis_title="Mês", yaxis_title="R$", legend_title="Tipo de Gasto", height=450)
        st.plotly_chart(fig_stacked_tipo, use_container_width=True)
        
        # ==============================
        # TABELA DETALHADA
        # ==============================
        st.subheader("📋 Detalhamento")
        df_tabela = df_filtrado[["tipo","descricao","valor","data_vencimento","cartao","parcela_atual","numero_parcela"]].copy()
        df_tabela["data_vencimento"] = df_tabela["data_vencimento"].dt.strftime("%d/%m/%Y")
        df_tabela["parcela"] = df_tabela["parcela_atual"].astype(str)+"/"+df_tabela["numero_parcela"].astype(str)
        df_tabela = df_tabela[["tipo","descricao","valor","data_vencimento","cartao","parcela"]]
        df_tabela["valor"] = df_tabela["valor"].apply(lambda x:f"R$ {x:,.2f}".replace(',', '_').replace('.', ',').replace('_', '.'))
        st.dataframe(df_tabela, use_container_width=True, hide_index=True)
        st.markdown(f"**💰 Total Filtrado:** R$ {total_filtrado:,.2f}".replace(',', '_').replace('.', ',').replace('_', '.'))
