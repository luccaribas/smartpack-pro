import streamlit as st
import pandas as pd

# --- BANCO DE DADOS COMPLETO (Fernandez S/A - Tabela 2024) ---
# Extraído integralmente do seu arquivo CSV
BASE_MATERIAIS = [
    # ONDA B
    {"id": "FK1L-B", "onda": "B", "tipo": "Reciclado", "coluna": "3.5", "m2": 2.956, "gram": 360},
    {"id": "FK2S-B", "onda": "B", "tipo": "Reciclado", "coluna": "4.0", "m2": 2.770, "gram": 335},
    {"id": "FK2-B", "onda": "B", "tipo": "Reciclado", "coluna": "5.0", "m2": 3.143, "gram": 380},
    {"id": "FK2E1-B", "onda": "B", "tipo": "Reciclado", "coluna": "5.5", "m2": 3.473, "gram": 420},
    {"id": "FK2E3-B", "onda": "B", "tipo": "Reciclado", "coluna": "6.0", "m2": 4.011, "gram": 485},
    {"id": "FK2E4-B", "onda": "B", "tipo": "Reciclado", "coluna": "7.0", "m2": 4.342, "gram": 525},
    {"id": "KMKS-B", "onda": "B", "tipo": "Kraft", "coluna": "4.0", "m2": 2.948, "gram": 335},
    {"id": "KMK-B", "onda": "B", "tipo": "Kraft", "coluna": "5.0", "m2": 3.344, "gram": 380},
    {"id": "BMC-B", "onda": "B", "tipo": "Branco", "coluna": "4.5", "m2": 3.793, "gram": 410},
    # ONDA C
    {"id": "FK1L-C", "onda": "C", "tipo": "Reciclado", "coluna": "3.3", "m2": 3.038, "gram": 370},
    {"id": "FK2S-C", "onda": "C", "tipo": "Reciclado", "coluna": "3.8", "m2": 2.853, "gram": 345},
    {"id": "FK2-C", "onda": "C", "tipo": "Reciclado", "coluna": "4.8", "m2": 3.225, "gram": 390},
    {"id": "FK2E1-C", "onda": "C", "tipo": "Reciclado", "coluna": "5.3", "m2": 3.556, "gram": 430},
    {"id": "FK2E3-C", "onda": "C", "tipo": "Reciclado", "coluna": "6.0", "m2": 4.094, "gram": 495},
    {"id": "FK2E4-C", "onda": "C", "tipo": "Reciclado", "coluna": "7.0", "m2": 4.424, "gram": 535},
    {"id": "KMKS-C", "onda": "C", "tipo": "Kraft", "coluna": "4.0", "m2": 3.036, "gram": 345},
    {"id": "KMK-C", "onda": "C", "tipo": "Kraft", "coluna": "5.0", "m2": 3.432, "gram": 390},
    {"id": "BMC-C", "onda": "C", "tipo": "Branco", "coluna": "4.5", "m2": 3.885, "gram": 420},
    # ONDA BC
    {"id": "FK1L-BC", "onda": "BC", "tipo": "Reciclado", "coluna": "6.5", "m2": 5.008, "gram": 610},
    {"id": "FK2S-BC", "onda": "BC", "tipo": "Reciclado", "coluna": "6.5", "m2": 4.673, "gram": 565},
    {"id": "FK2L-BC", "onda": "BC", "tipo": "Reciclado", "coluna": "7.0", "m2": 5.127, "gram": 620},
    {"id": "FK2-BC", "onda": "BC", "tipo": "Reciclado", "coluna": "8.0", "m2": 5.458, "gram": 660},
    {"id": "FK2E1-BC", "onda": "BC", "tipo": "Reciclado", "coluna": "9.0", "m2": 6.120, "gram": 740},
    {"id": "FK2E3-BC", "onda": "BC", "tipo": "Reciclado", "coluna": "10.0", "m2": 6.699, "gram": 810},
    {"id": "KMKS-BC", "onda": "BC", "tipo": "Kraft", "coluna": "7.0", "m2": 5.324, "gram": 605},
    {"id": "KMK-BC", "onda": "BC", "tipo": "Kraft", "coluna": "8.0", "m2": 5.808, "gram": 660},
    {"id": "BMC-BC", "onda": "BC", "tipo": "Branco", "coluna": "7.5", "m2": 6.383, "gram": 690},
    # MICROONDULADO E / EB
    {"id": "FK1L-E", "onda": "E (Micro)", "tipo": "Reciclado", "coluna": "4.0", "m2": 2.961, "gram": 350},
    {"id": "FK2L-E", "onda": "E (Micro)", "tipo": "Reciclado", "coluna": "4.5", "m2": 3.067, "gram": 360},
    {"id": "FK1L-EB", "onda": "EB (Dupla)", "tipo": "Reciclado", "coluna": "6.5", "m2": 5.034, "gram": 595},
    {"id": "FK2L-EB", "onda": "EB (Dupla)", "tipo": "Reciclado", "coluna": "7.0", "m2": 5.155, "gram": 605}
]

# --- MAPEAMENTO FEFCO ---
MODELOS_BIBLIOTECA = {
    "Série 0200 (Maletas)": ["0200", "0201", "0202", "0203", "0204", "0205", "0206"],
    "Série 0300 (Telescópicas)": ["0300", "0301", "0306", "0310", "0320"],
    "Série 0400 (Corte e Vinco)": ["0420", "0421", "0422", "0426", "0427", "0429"],
    "Série 0900 (Acessórios)": ["0900", "0901", "0903", "0933"]
}

st.set_page_config(page_title="New Age Embalagens - Orçador Master", layout="wide")

if 'carrinho' not in st.session_state:
    st.session_state.carrinho = []

st.title("📦 Sistema de Orçamentos Master - New Age")

# --- 1. CONFIGURAÇÃO ---
with st.container():
    col1, col2 = st.columns([2, 1])
    
    with col1:
        st.subheader("Configurar Novo Item")
        c_fam, c_mod = st.columns(2)
        familia = c_fam.selectbox("Família de Modelo", list(MODELOS_BIBLIOTECA.keys()))
        modelo = c_mod.selectbox("Modelo FEFCO", MODELOS_BIBLIOTECA[familia])
        
        c_l, c_w, c_h, c_q = st.columns(4)
        L = c_l.number_input("Comp (mm)", value=300)
        W = c_w.number_input("Larg (mm)", value=200)
        H = c_h.number_input("Alt (mm)", value=50)
        qtd = c_q.number_input("Qtd", value=500, step=100)

        st.markdown("---")
        st.subheader("Selecione o Material")
        f1, f2, f3 = st.columns(3)
        onda_sel = f1.selectbox("Onda", sorted(list(set(m['onda'] for m in BASE_MATERIAIS))))
        tipo_sel = f2.selectbox("Papel", sorted(list(set(m['tipo'] for m in BASE_MATERIAIS if m['onda'] == onda_sel))))
        coluna_sel = f3.selectbox("ECT", sorted(list(set(m['coluna'] for m in BASE_MATERIAIS if m['onda'] == onda_sel and m['tipo'] == tipo_sel))))

    # --- MOTOR GEOMÉTRICO (LEITURA INDIVIDUAL) ---
    chapa = next(m for m in BASE_MATERIAIS if m['onda'] == onda_sel and m['tipo'] == tipo_sel and m['coluna'] == coluna_sel)
    d_map = {"B": 3.0, "C": 4.0, "BC": 6.5, "E (Micro)": 1.5, "EB (Dupla)": 4.5}
    d = d_map.get(onda_sel, 3.0)

    # Fórmulas extraídas dos arquivos .evr
    if "02" in modelo:
        bL, bW = (2*L + 2*W + 45), (H + W + d)
    elif "04" in modelo:
        bL, bW = (L + 4*H + 6*d), (2*W + 3*H + 20)
    elif "03" in modelo: # Telescópicas
        bL, bW = (L + 2*H + 4*d), (W + 2*H + 4*d)
    else: # Acessórios 0900
        bL, bW = L, W

    area_m2 = (bL * bW) / 1_000_000
    preco_venda = (area_m2 * chapa['m2']) * 2.0 # Fator 100

    with col2:
        st.subheader("Análise do Item")
        st.metric("Venda Unitária", f"R$ {preco_venda:.2f}")
        st.info(f"**Chapa Líquida:** {bL:.0f} x {bW:.0f} mm")
        if st.button("➕ Adicionar ao Orçamento", use_container_width=True):
            st.session_state.carrinho.append({
                "Modelo": modelo, "Medidas": f"{L}x{W}x{H}", "Chapa (Blank)": f"{bL:.0f}x{bW:.0f}",
                "Material": f"{onda_sel} {tipo_sel} (ECT {coluna_sel})", "Qtd": qtd,
                "Unitário": f"R$ {preco_venda:.2f}", "Subtotal": round(preco_venda * qtd, 2),
                "Peso (kg)": round(area_m2 * chapa['gram'] * qtd / 1000, 2)
            })
            st.rerun()

# --- TABELA DE ORÇAMENTO ---
st.divider()
if st.session_state.carrinho:
    st.header("🛒 Resumo Geral")
    df = pd.DataFrame(st.session_state.carrinho)
    st.table(df)
    st.metric("Total do Pedido", f"R$ {df['Subtotal'].sum():.2f}")
