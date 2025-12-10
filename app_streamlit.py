#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Dashboard Financeiro em Streamlit
Versão com tela separada para edição/exclusão de lançamentos
"""
import os
import streamlit as st
import pandas as pd
from datetime import datetime
from supabase import create_client, Client
import hashlib
from st_aggrid import AgGrid, GridOptionsBuilder, GridUpdateMode

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
# LOGIN/REGISTRO
# ==============================
if st.session_state.user is None:
    col1, col2, col3 = st.columns([1,2,1])
    with col2:
        st.title("💰 FinanceApp")
        tab_login, tab_registro = st.tabs(["Login", "Registrar"])
        with tab_login:
            email_login = st.text_input("Email", key="email_login")
            senha_login = st.text_input("Senha", type="password", key="senha_login")
            if st.button("Entrar", use_container_width=True, type="primary"):
                ok, user = login(email_login, senha_login)
                if ok:
                    st.session_state.user = user
                    st.success(f"Bem-vindo, {user['nome']}!")
                    st.experimental_rerun()
                else:
                    st.error("Email ou senha incorretos!")
        with tab_registro:
            nome_cad = st.text_input("Nome", key="nome_cad")
            email_cad = st.text_input("Email", key="email_cad")
            senha_cad = st.text_input("Senha", type="password", key="senha_cad")
            if st.button("Criar Conta", use_container_width=True, type="primary"):
                if nome_cad and email_cad and senha_cad:
                    criar_usuario(nome_cad, email_cad, senha_cad)
                    st.success("Conta criada com sucesso! Faça login.")
                else:
                    st.warning("Preencha todos os campos!")

# ==============================
# DASHBOARD PRINCIPAL
# ==============================
else:
    user = st.session_state.user

    st.title(f"💰 Dashboard Financeiro - {user['nome']}")
    if st.button("Sair"):
        st.session_state.user = None
        st.experimental_rerun()

    st.divider()

    # ==============================
    # MENU LATERAL
    # ==============================
    menu = st.sidebar.selectbox("Menu", ["Dashboard", "Gerenciar Lançamentos", "Novo Lançamento"])

    # ==============================
    # NOVO LANÇAMENTO
    # ==============================
    if menu == "Novo Lançamento":
        st.subheader("➕ Novo Lançamento")
        with st.form("form_novo_lancamento"):
            tipo_novo = st.selectbox("Tipo:", ["Mercado","Alimentação","Saude","Transporte","Carro","Casa","Emprestimo","Roupa","Lazer"])
            desc_novo = st.text_input("Descrição")
            valor_novo = st.number_input("Valor", min_value=0.0, step=0.01)
            data_novo = st.date_input("Data de Vencimento")
            parcelas_novo = st.number_input("Parcelas", min_value=1, value=1)
            cartao_novo = st.text_input("Cartão")
            submitted = st.form_submit_button("Adicionar")
            if submitted:
                inserir_parcelas_futuras(user["id"], tipo_novo, desc_novo, valor_novo, datetime.combine(data_novo, datetime.min.time()), int(parcelas_novo), cartao_novo)
                st.success("Lançamento adicionado!")

    # ==============================
    # DASHBOARD COM KPIs E GRÁFICOS
    # ==============================
    elif menu == "Dashboard":
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

            # Ano filtrado
            anos = sorted(df["ano"].unique(), reverse=True)
            ano_sel = st.sidebar.selectbox("Ano:", anos, index=0)
            df_filtrado = df[df["ano"] == ano_sel]

            # KPIs
            col1, col2, col3, col4 = st.columns(4)
            with col1:
                st.metric("💵 Total Geral", f"R$ {df['valor'].sum():,.2f}")
            with col2:
                st.metric("📊 Total Ano", f"R$ {df_filtrado['valor'].sum():,.2f}")
            with col3:
                st.metric("📈 Média", f"R$ {df_filtrado['valor'].mean():,.2f}")
            with col4:
                num_transacoes = len(df_filtrado)
                st.metric("📋 Transações", num_transacoes)

            # Gráfico de barras empilhadas por tipo
            st.subheader(f"Gastos Mensais por Tipo ({ano_sel})")
            df_plot = df_filtrado.copy()
            df_plot['mes_ano'] = df_plot['data_vencimento'].dt.strftime("%B de %Y")
            df_group = df_plot.groupby(['mes_ano','tipo'])['valor'].sum().reset_index()

            import plotly.express as px
            fig = px.bar(
                df_group,
                x='mes_ano',
                y='valor',
                color='tipo',
                text='valor',
                color_discrete_sequence=px.colors.qualitative.Pastel,
                title=f"Gastos Mensais por Tipo ({ano_sel})"
            )
            fig.update_traces(texttemplate="R$ %{text:,.2f}", textposition="inside")
            fig.update_layout(xaxis_title="Mês", yaxis_title="R$", barmode='stack', xaxis_tickangle=-45)
            st.plotly_chart(fig, use_container_width=True)

    # ==============================
    # GERENCIAR LANÇAMENTOS
    # ==============================
    elif menu == "Gerenciar Lançamentos":
        st.subheader("📝 Gerenciar Lançamentos")
        dados = listar_installments(user["id"])
        if not dados:
            st.warning("Nenhum lançamento encontrado!")
        else:
            df = pd.DataFrame(dados)
            df["data_vencimento"] = pd.to_datetime(df["data_vencimento"])
            df["valor"] = pd.to_numeric(df["valor"], errors="coerce").fillna(0.0)
            df["parcela"] = df["parcela_atual"].astype(str) + "/" + df["numero_parcela"].astype(str)

            gb = GridOptionsBuilder.from_dataframe(df)
            gb.configure_selection(selection_mode="single", use_checkbox=False)
            gb.configure_columns(["descricao","tipo","valor","data_vencimento","cartao","parcela"], editable=False)
            grid_options = gb.build()
            grid_response = AgGrid(
                df,
                gridOptions=grid_options,
                update_mode=GridUpdateMode.SELECTION_CHANGED,
                height=400,
                allow_unsafe_jscode=True
            )

            selected = grid_response['selected_rows']
            if selected and len(selected) > 0:
                selected_id = selected[0]['id']
                st.write("Você selecionou:", selected[0]['descricao'])
                col1, col2 = st.columns(2)
                with col1:
                    if st.button("✏️ Editar"):
                        st.session_state.edit_id = selected_id
                        st.experimental_rerun()
                with col2:
                    if st.button("🗑️ Excluir"):
                        delete_installment(selected_id)
                        st.success("Lançamento excluído!")
                        st.experimental_rerun()

            # Tela de edição
            if "edit_id" in st.session_state:
                edit_id = st.session_state.edit_id
                row = df[df["id"] == edit_id].iloc[0]
                st.subheader("✏️ Editar Lançamento")
                with st.form("form_editar"):
                    tipo_edit = st.selectbox("Tipo:", ["Mercado","Alimentação","Saude","Transporte","Carro","Casa","Emprestimo","Roupa","Lazer"], index=["Mercado","Alimentação","Saude","Transporte","Carro","Casa","Emprestimo","Roupa","Lazer"].index(row["tipo"]))
                    desc_edit = st.text_input("Descrição", value=row["descricao"])
                    valor_edit = st.number_input("Valor", value=row["valor"])
                    data_edit = st.date_input("Data de Vencimento", value=row["data_vencimento"])
                    cartao_edit = st.text_input("Cartão", value=row["cartao"])
                    parcelas_edit = st.number_input("Parcelas", min_value=1, value=row["numero_parcela"])
                    submitted_edit = st.form_submit_button("Salvar Alterações")
                    if submitted_edit:
                        update_installment(edit_id, {
                            "tipo": tipo_edit,
                            "descricao": desc_edit,
                            "valor": float(valor_edit),
                            "data_vencimento": data_edit.strftime("%Y-%m-%d"),
                            "numero_parcela": parcelas_edit,
                            "cartao": cartao_edit
                        })
                        st.success("Lançamento atualizado!")
                        del st.session_state.edit_id
                        st.experimental_rerun()
