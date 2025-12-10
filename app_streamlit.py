#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Dashboard Financeiro em Streamlit
Versão completa com login, KPIs, gráficos e edição/exclusão de lançamentos
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
    .metric-box { background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                  padding: 20px; border-radius: 10px; color: white; text-align: center; }
    .metric-value { font-size: 28px; font-weight: bold; margin-top: 10px; }
    .metric-label { font-size: 12px; opacity: 0.8; text-transform: uppercase; }
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
    return supabase.table("users").insert({"nome": nome, "email": email, "senha": senha_hash}).execute()

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

def update_installment(installment_id, fields: dict):
    return supabase.table("installments").update(fields).eq("id", installment_id).execute()

def delete_installment(installment_id):
    return supabase.table("installments").delete().eq("id", installment_id).execute()

# ==============================
# INICIALIZAÇÃO DE SESSÃO
# ==============================
if "user" not in st.session_state:
    st.session_state.user = None

# ==============================
# LOGIN / REGISTRO
# ==============================
if st.session_state.user is None:
    col1, col2, col3 = st.columns([1, 2, 1])
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
    col_title, col_logout = st.columns([0.9, 0.1])
    with col_title:
        st.title(f"💰 Dashboard Financeiro - {user['nome']}")
    with col_logout:
        if st.button("Sair"):
            st.session_state.user = None
            st.rerun()
    st.divider()
    
    # ==============================
    # SIDEBAR - FILTROS
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
            
            anos = sorted(df["ano"].unique(), reverse=True)
            ano_sel = st.selectbox("Ano:", anos, index=0)
            
            tipos = sorted(df["tipo"].dropna().unique())
            tipo_sel = st.multiselect("Tipo:", tipos, default=tipos)
            
            cartoes = sorted(df["cartao"].fillna("").unique())
            cartao_sel = st.multiselect("Cartão:", cartoes, default=cartoes)
            
            df_filtrado = df[
                (df["ano"] == ano_sel) &
                (df["tipo"].isin(tipo_sel)) &
                (df["cartao"].isin(cartao_sel))
            ]
            
            # ==============================
            # NOVO LANÇAMENTO
            # ==============================
            st.divider()
            st.subheader("➕ Novo Lançamento")
            with st.form("form_novo_lancamento"):
                tipo_novo = st.selectbox("Tipo:", ["Mercado", "Alimentação", "Saude", "Transporte", "Carro", "Casa", "Emprestimo", "Roupa", "Lazer"], key="tipo_novo")
                desc_novo = st.text_input("Descrição", key="desc_novo")
                valor_novo = st.number_input("Valor", min_value=0.0, step=0.01, key="valor_novo")
                data_novo = st.date_input("Data de Vencimento", key="data_novo")
                parcelas_novo = st.number_input("Parcelas", min_value=1, value=1, key="parcelas_novo")
                cartao_novo = st.text_input("Cartão", key="cartao_novo")
                submitted = st.form_submit_button("Adicionar", use_container_width=True, type="primary")
                if submitted:
                    try:
                        inserir_parcelas_futuras(user["id"], tipo_novo, desc_novo, valor_novo, datetime.combine(data_novo, datetime.min.time()), int(parcelas_novo), cartao_novo)
                        st.success("Lançamento adicionado!")
                        st.rerun()
                    except Exception as e:
                        st.error(f"Erro ao adicionar: {e}")
    
    # ==============================
    # KPIs
    # ==============================
    if not df_filtrado.empty:
        col1, col2, col3, col4, col5 = st.columns(5)
        with col1:
            total_geral = df["valor"].sum()
            st.metric("💵 Total Geral", f"R$ {total_geral:,.2f}".replace(',', '_').replace('.', ',').replace('_', '.'))
        with col2:
            total_filtrado = df_filtrado["valor"].sum()
            st.metric("📊 Total Filtrado", f"R$ {total_filtrado:,.2f}".replace(',', '_').replace('.', ',').replace('_', '.'))
        with col3:
            media = df_filtrado["valor"].mean()
            st.metric("📈 Média", f"R$ {media:,.2f}".replace(',', '_').replace('.', ',').replace('_', '.'))
        with col4:
            num_transacoes = len(df_filtrado)
            st.metric("📋 Transações", num_transacoes)
        with col5:
            total_parceladas_valor = df_filtrado[df_filtrado["numero_parcela"] > 1]["valor"].sum()
            perc_parceladas_valor = (total_parceladas_valor / total_filtrado) * 100 if total_filtrado != 0 else 0
            st.metric("% Parceladas", f"{perc_parceladas_valor:.1f}%")
        st.divider()
        
        # ==============================
        # GRÁFICOS
        # ==============================
        col_pie, col_bar = st.columns(2)
        with col_pie:
            st.subheader("💧 Gastos por Tipo")
            df_tipo = df_filtrado.groupby("tipo")["valor"].sum().reset_index()
            fig_pie = px.pie(df_tipo, names="tipo", values="valor", color_discrete_sequence=px.colors.qualitative.Set3, hover_data={"valor": ":.2f"})
            fig_pie.update_traces(textposition='inside', textinfo='percent+label')
            st.plotly_chart(fig_pie, use_container_width=True)
        with col_bar:
            st.subheader("📅 Gastos por Mês")
            df_mes = df.groupby(df["data_vencimento"].dt.to_period("M"))["valor"].sum().reset_index()
            df_mes.columns = ["mes", "valor"]
            df_mes["mes"] = df_mes["mes"].astype(str)
            fig_bar = px.bar(df_mes, x="mes", y="valor", color="valor", color_continuous_scale="Viridis", hover_data={"valor": ":.2f"})
            fig_bar.update_layout(showlegend=False, xaxis_title="Mês", yaxis_title="R$")
            st.plotly_chart(fig_bar, use_container_width=True)
        
        # ==============================
        # GRÁFICO: Gastos Mensais por Tipo (Ano Selecionado)
        # ==============================
        st.subheader(f"💹 Gastos Mensais por Tipo ({ano_sel})")
        df_graf = df[df["ano"] == ano_sel].copy()
        df_graf_group = df_graf.groupby([df_graf["data_vencimento"].dt.to_period("M"), "tipo"])["valor"].sum().reset_index()
        df_graf_group["mes_label"] = df_graf_group["data_vencimento"].dt.strftime("%B de %Y")
        fig_stacked = px.bar(
            df_graf_group,
            x="mes_label",
            y="valor",
            color="tipo",
            text="valor",
            color_discrete_sequence=px.colors.qualitative.Pastel,
            labels={"mes_label": "Mês", "valor": "R$"},
            hover_data={"valor": ":.2f"}
        )
        fig_stacked.update_traces(texttemplate='%{text:,.2f}', textposition='inside')
        fig_stacked.update_layout(barmode='stack', xaxis_title="Mês", yaxis_title="R$", height=400)
        st.plotly_chart(fig_stacked, use_container_width=True)
        
        # ==============================
        # TABELA DETALHADA COM EDITAR/EXCLUIR
        # ==============================
        st.subheader("📋 Detalhamento")
        for idx, row in df_filtrado.iterrows():
            col1, col2, col3, col4, col5, col6, col7 = st.columns([2,3,1.5,2,2,1,1])
            col1.write(row["tipo"])
            col2.write(row["descricao"])
            col3.write(f"R$ {row['valor']:,.2f}".replace(',', '_').replace('.', ',').replace('_', '.'))
            col4.write(row["data_vencimento"].strftime("%d/%m/%Y"))
            col5.write(row["cartao"])
            col6.write(f"{row['parcela_atual']}/{row['numero_parcela']}")
            
            if col7.button("✏️", key=f"edit_{row['id']}"):
                with st.form(f"form_edit_{row['id']}"):
                    tipo_edit = st.selectbox("Tipo", tipos, index=tipos.index(row["tipo"]))
                    desc_edit = st.text_input("Descrição", value=row["descricao"])
                    valor_edit = st.number_input("Valor", min_value=0.0, value=row["valor"], step=0.01)
                    data_edit = st.date_input("Data de Vencimento", value=row["data_vencimento"])
                    parcelas_edit = st.number_input("Parcelas", min_value=1, value=row["numero_parcela"])
                    cartao_edit = st.text_input("Cartão", value=row["cartao"])
                    submitted_edit = st.form_submit_button("Salvar")
                    if submitted_edit:
                        update_installment(row["id"], {
                            "tipo": tipo_edit,
                            "descricao": desc_edit,
                            "valor": valor_edit,
                            "data_vencimento": data_edit.strftime("%Y-%m-%d"),
                            "numero_parcela": parcelas_edit,
                            "cartao": cartao_edit
                        })
                        st.success("Lançamento atualizado!")
                        st.experimental_rerun()
            
            if col7.button("🗑️", key=f"del_{row['id']}"):
                delete_installment(row["id"])
                st.success("Lançamento excluído!")
                st.experimental_rerun()
