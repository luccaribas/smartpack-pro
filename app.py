import streamlit as st
import pandas as pd

# --- BANCO DE DADOS ESTRUTURADO (Tabela Fernandez) ---
# Adicionei a 'coluna' (ECT) e o 'tipo' para permitir o filtro em cascata
BASE_MATERIAIS = [
    {"id": "FK1L-B", "onda": "B", "tipo": "Reciclado", "coluna": "3.5", "m2": 2.633, "gram": 360, "min": 250},
    {"id": "FK2-B", "onda": "B", "tipo": "Reciclado", "coluna": "4.0", "m2": 2.801, "gram": 380, "min": 250},
    {"id": "KMK-B", "onda": "B", "tipo": "Kraft", "coluna": "5.0", "m2": 3.102, "gram": 380, "min": 300},
    {"id": "FK2-C", "onda": "C", "tipo": "Reciclado", "coluna": "4.5", "m2": 2.874, "gram": 390, "min": 250},
    {"id": "FK2-BC", "onda": "BC", "tipo": "Reciclado", "coluna": "7.0", "m2": 4.864, "gram": 660, "min": 250},
    {"id": "KMK-BC", "onda": "BC", "tipo": "Kraft", "coluna": "8.0", "m2": 5.387, "gram": 660, "min": 300},
    {"id": "BMC-BC", "onda": "BC", "tipo": "Branco", "coluna": "7.5", "m2": 6.543, "gram": 690, "min": 300},
    # Exemplo solicitado por você:
    {"id": "FK2E4", "onda": "B", "tipo": "Reciclado", "coluna": "7.0", "m2": 3.200, "gram": 420, "min": 250}
]

st.set_page_config(page_title="New Age - Sistema de Orçamentos", layout="wide")

if 'carrinho' not in st.session_state:
    st.session_state.carrinho = []

st.title("📦 Sistema de Orçamentos New Age")

# --- 1. CONFIGURAÇÃO DO ITEM ---
with st.expander("📝 Configurar Nova Embalagem", expanded=True):
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.subheader("Modelo e Medidas")
        modelo = st.selectbox("Modelo FEFCO", ["0201", "0200", "0427", "0426", "0901", "0903"])
        L = st.number_input("Comp. (L) mm", value=300)
        W = st.number_input("Larg. (W) mm", value=200)
        H = st.number_input("Alt. (H) mm", value=50)
        qtd = st.number_input("Quantidade", value=500, step=100)

    with col2:
        st.subheader("Escolha da Chapa")
        
        # FILTROS EM CASCATA
        ondas_disp = sorted(list(set(m['onda'] for m in BASE_MATERIAIS)))
        onda_sel = st.selectbox("1. Selecione a Onda", ondas_disp)
        
        tipos_disp = sorted(list(set(m['tipo'] for m in BASE_MATERIAIS if m['onda'] == onda_sel)))
        tipo_sel = st.selectbox("2. Selecione o Papel", tipos_disp)
        
        colunas_disp = sorted(list(set(m['coluna'] for m in BASE_MATERIAIS if m['onda'] == onda_sel and m['tipo'] == tipo_sel)))
        coluna_sel = st.selectbox("3. Selecione a Coluna (Resistência)", colunas_disp)
        
        # Busca o item final no banco de dados
        chapa_final = next(m for m in BASE_MATERIAIS if m['onda'] == onda_sel and m['tipo'] == tipo_sel and m['coluna'] == coluna_sel)

    with col3:
        st.subheader("Resumo Técnico")
        # Lógica de Refile e Geometria
        refile = 30 if modelo.startswith("04") else 0
        d = 3.0 if chapa_final['onda'] == "B" else 6.5
        
        if modelo.startswith("02"):
            bL, bW = (2*L + 2*W + 50), (H + W + d)
        elif modelo.startswith("04"):
            bL, bW = (L + 4*H + 6*d), (2*W + 3*H + 20)
        else:
            bL, bW = L, W
            
        area_m2 = ((bL + refile) * (bW + refile)) / 1_000_000
        preco_unit = (area_m2 * chapa_final['m2']) * 2.0 # Fator 100
        peso_item = (area_m2 * chapa_final['gram'] * qtd) / 1000
        
        st.info(f"**Código Interno:** {chapa_final['id']}\n\n**Chapa Aberta:** {bL+refile:.0f}x{bW+refile:.0f} mm")
        st.metric("Preço Unitário", f"R$ {preco_unit:.2f}")

    if st.button("➕ Adicionar ao Carrinho"):
        st.session_state.carrinho.append({
            "Modelo": modelo,
            "Medidas": f"{L}x{W}x{H}",
            "Chapa Aberta": f"{bL+refile:.0f}x{bW+refile:.0f}",
            "Material": f"{onda_sel} {tipo_sel} (Col: {coluna_sel})",
            "Qtd": qtd,
            "Subtotal": round(preco_unit * qtd, 2),
            "Peso (kg)": round(peso_item, 2)
        })
        st.toast("Item adicionado!")

# --- 2. CARRINHO ---
st.divider()
if st.session_state.carrinho:
    st.header("🛒 Orçamento Consolidado")
    df = pd.DataFrame(st.session_state.carrinho)
    st.table(df)
    
    t_valor = df["Subtotal"].sum()
    t_peso = df["Peso (kg)"].sum()
    
    c1, c2, c3 = st.columns(3)
    c1.metric("Total Geral", f"R$ {t_valor:.2f}")
    c2.metric("Peso Total", f"{t_peso:.1f} kg")
    if st.button("🗑️ Limpar Carrinho"):
        st.session_state.carrinho = []
        st.rerun()
