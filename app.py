import streamlit as st

# =========================================================
# 1. ENGENHARIA NEW AGE (PARÂMETROS EXTRAÍDOS DO PRINECT)
# =========================================================
# d = Espessura da chapa | gl = Orelha de colagem (Glue Flap)
CONFIG_TECNICA = {
    "Onda B":           {"d": 3.0, "gl": 30},
    "Onda C":           {"d": 4.0, "gl": 30},
    "Onda BC (Dupla)":  {"d": 6.9, "gl": 40},
    "Onda E (Micro)":   {"d": 1.5, "gl": 25},
    "Onda EB (Dupla)":  {"d": 4.4, "gl": 30}
}

# =========================================================
# 2. TABELA COMPLETA FERNANDEZ 2024 (31 OPÇÕES)
# =========================================================
# Dados extraídos diretamente da planilha "Tabela de especificação NOVA 2024"
TABELA_FERNANDEZ = {
    # --- ONDA B ---
    "FK1L-B (Reciclado)": {"onda": "Onda B", "preco": 2.956},
    "FK2S-B (Reciclado)": {"onda": "Onda B", "preco": 2.770},
    "FK2-B (Reciclado)":  {"onda": "Onda B", "preco": 3.143},
    "FK2E1-B (Reciclado)": {"onda": "Onda B", "preco": 3.473},
    "FK2E3-B (Reciclado)": {"onda": "Onda B", "preco": 4.011},
    "FK2E4-B (Reciclado)": {"onda": "Onda B", "preco": 4.342},
    "KMKS-B (Kraft)":     {"onda": "Onda B", "preco": 2.948},
    "KMK-B (Kraft)":      {"onda": "Onda B", "preco": 3.344},
    "BMC-B (Branco)":     {"onda": "Onda B", "preco": 3.793},
    
    # --- ONDA C ---
    "FK1L-C (Reciclado)": {"onda": "Onda C", "preco": 3.038},
    "FK2S-C (Reciclado)": {"onda": "Onda C", "preco": 2.853},
    "FK2-C (Reciclado)":  {"onda": "Onda C", "preco": 3.225},
    "FK2E1-C (Reciclado)": {"onda": "Onda C", "preco": 3.556},
    "FK2E3-C (Reciclado)": {"onda": "Onda C", "preco": 4.094},
    "FK2E4-C (Reciclado)": {"onda": "Onda C", "preco": 4.424},
    "KMKS-C (Kraft)":     {"onda": "Onda C", "preco": 3.036},
    "KMK-C (Kraft)":      {"onda": "Onda C", "preco": 3.432},
    "BMC-C (Branco)":     {"onda": "Onda C", "preco": 3.885},
    
    # --- ONDA BC (DUPLA) ---
    "FK1L-BC (Reciclado)": {"onda": "Onda BC (Dupla)", "preco": 5.008},
    "FK2S-BC (Reciclado)": {"onda": "Onda BC (Dupla)", "preco": 4.673},
    "FK2L-BC (Reciclado)": {"onda": "Onda BC (Dupla)", "preco": 5.127},
    "FK2-BC (Reciclado)":  {"onda": "Onda BC (Dupla)", "preco": 5.458},
    "FK2E1-BC (Reciclado)": {"onda": "Onda BC (Dupla)", "preco": 6.120},
    "FK2E3-BC (Reciclado)": {"onda": "Onda BC (Dupla)", "preco": 6.699},
    "KMKS-BC (Kraft)":     {"onda": "Onda BC (Dupla)", "preco": 5.324},
    "KMK-BC (Kraft)":      {"onda": "Onda BC (Dupla)", "preco": 5.808},
    "BMC-BC (Branco)":     {"onda": "Onda BC (Dupla)", "preco": 6.383},

    # --- ONDA E / EB ---
    "FK1L-E (Micro)":     {"onda": "Onda E (Micro)", "preco": 2.961},
    "FK2L-E (Micro)":     {"onda": "Onda E (Micro)", "preco": 3.067},
    "FK1L-EB (Dupla)":    {"onda": "Onda EB (Dupla)", "preco": 5.034},
    "FK2L-EB (Dupla)":    {"onda": "Onda EB (Dupla)", "preco": 5.155}
}

# =========================================================
# 3. INTERFACE STREAMLIT
# =========================================================
st.set_page_config(page_title="New Age Embalagens - Orçador Master", layout="wide")

st.title("📦 Orçador Técnico New Age Embalagens")
st.markdown("---")

# --- MENU DE SELEÇÃO ---
with st.sidebar:
    st.header("1. Configurações")
    chapa_nome = st.selectbox("Selecione a Chapa (Fernandez 2024)", list(TABELA_FERNANDEZ.keys()))
    modelo_fefco = st.selectbox("Modelo FEFCO", ["0200 (Meia Maleta)", "0201 (Maleta)", "0427 (Corte e Vinco)"])
    
    # Busca automática de dados
    dados_chapa = TABELA_FERNANDEZ[chapa_nome]
    onda_ref = dados_chapa["onda"]
    preco_m2_base = dados_chapa["preco"]
    
    # Busca parâmetros técnicos do .par
    parametros = CONFIG_TECNICA[onda_ref]
    d = parametros["d"]
    gl = parametros["gl"]

# --- ENTRADA DE DIMENSÕES ---
st.subheader(f"Medidas Internas para: {chapa_nome}")
col1, col2, col3, col4 = st.columns(4)
L = col1.number_input("Comprimento (L) mm", value=300, min_value=10)
W = col2.number_input("Largura (W) mm", value=200, min_value=10)
H = col3.number_input("Altura (H) mm", value=150, min_value=10)
qtd = col4.number_input("Quantidade", value=500, step=100, min_value=1)

# =========================================================
# 4. MOTOR DE CÁLCULO (PRECISÃO 95%+)
# =========================================================
# Lógica baseada em padrões FEFCO com correções de espessura da New Age
if "0200" in modelo_fefco:
    # Meia Maleta: Largura da chapa considera apenas 1 aba (W/2)
    bL = (2 * L) + (2 * W) + gl
    bW = H + (W / 2) + d
elif "0201" in modelo_fefco:
    # Maleta Padrão: Largura considera abas superiores e inferiores (W)
    bL = (2 * L) + (2 * W) + gl
    bW = H + W + d
elif "0427" in modelo_fefco:
    # Corte e Vinco Complexo (Bandeja com orelhas de travamento)
    bL = L + (4 * H) + (6 * d)
    bW = (2 * W) + (3 * H) + 20 

# Cálculos de Área e Financeiro
area_unitaria_m2 = (bL * bW) / 1_000_000
custo_chapa_unid = area_unitaria_m2 * preco_m2_base
# FATOR 100: Preço de Venda = Custo da Chapa x 2 (Markup de 100%)
preco_venda_unit = custo_chapa_unid * 2.0

# --- RESULTADOS ---
st.divider()
res1, res2, res3 = st.columns(3)

with res1:
    st.metric("PREÇO DE VENDA UNIT.", f"R$ {preco_venda_unit:.2f}")
    st.write(f"**Total do Pedido:** R$ {preco_venda_unit * qtd:,.2f}")

with res2:
    st.info(f"**Chapa Aberta (Blank)**\n\n**{bL:.0f} x {bW:.0f} mm**")
    st.write(f"Área Unitária: {area_unitaria_m2:.4f} m²")

with res3:
    st.success(f"**Ficha Técnica**")
    st.write(f"**Onda:** {onda_ref} ({d}mm)")
    st.write(f"**Orelha de Cola:** {gl}mm")
    st.write(f"**Custo Base $m^2$:** R$ {preco_m2_base:.3f}")

st.markdown("---")
st.caption("New Age Embalagens - Cálculos baseados em Heidelberg Package Designer Suite")
