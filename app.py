import streamlit as st
import pandas as pd

# =========================================================
# 1. BANCO DE DADOS ESTRUTURADO (MAPA TÉCNICO + PREÇOS)
# =========================================================
CONFIG_TECNICA = {
    "Onda B":           {"d": 3.0, "gl": 30},
    "Onda C":           {"d": 4.0, "gl": 30},
    "Onda BC (Dupla)":  {"d": 6.9, "gl": 40},
    "Onda E (Micro)":   {"d": 1.5, "gl": 25},
    "Onda EB (Dupla)":  {"d": 4.4, "gl": 30}
}

# Dados filtrados da Tabela Fernandez 2024
# Estrutura: Onda -> Papel -> Coluna -> Preço
DADOS_COMERCIAIS = {
    "Onda B": {
        "Reciclado": {3.5: 2.956, 4.0: 2.770, 5.0: 3.143, 5.5: 3.473, 6.0: 4.011, 7.0: 4.342},
        "Kraft":     {4.0: 2.948, 5.0: 3.344},
        "Branco":    {5.0: 3.793}
    },
    "Onda C": {
        "Reciclado": {3.5: 3.038, 4.0: 2.853, 4.8: 3.225, 5.0: 3.556, 5.5: 4.094, 6.0: 4.424},
        "Kraft":     {4.0: 3.036, 5.0: 3.432},
        "Branco":    {5.0: 3.885}
    },
    "Onda BC (Dupla)": {
        "Reciclado": {7.0: 5.008, 7.5: 4.673, 8.0: 5.127, 8.5: 6.120, 9.5: 6.699},
        "Kraft":     {8.0: 5.808},
        "Branco":    {8.0: 6.383}
    },
    "Onda E (Micro)": {
        "Reciclado": {3.5: 2.961, 4.0: 3.067}
    },
    "Onda EB (Dupla)": {
        "Reciclado": {7.5: 5.034, 8.0: 5.155}
    }
}

# =========================================================
# 2. INICIALIZAÇÃO DO CARRINHO
# =========================================================
if 'carrinho' not in st.session_state:
    st.session_state.carrinho = []

def adicionar_ao_carrinho(item):
    st.session_state.carrinho.append(item)
    st.toast("Item adicionado ao carrinho! 🛒")

# =========================================================
# 3. INTERFACE DO CLIENTE
# =========================================================
st.set_page_config(page_title="New Age Embalagens - Orçador", layout="wide")
st.title("📦 Orçador Digital New Age")

# --- BARRA LATERAL: FUNIL DE ESCOLHA ---
with st.sidebar:
    st.header("Configurações da Caixa")
    
    # 1. Escolha da Onda
    onda_sel = st.selectbox("1. Selecione a Onda", list(DADOS_COMERCIAIS.keys()))
    
    # 2. Escolha do Papel (Baseado na Onda)
    papeis_disp = list(DADOS_COMERCIAIS[onda_sel].keys())
    papel_sel = st.selectbox("2. Selecione o Papel", papeis_disp)
    
    # 3. Escolha da Coluna (Baseado no Papel)
    colunas_disp = list(DADOS_COMERCIAIS[onda_sel][papel_sel].keys())
    coluna_sel = st.selectbox("3. Selecione a Resistência (Coluna)", colunas_disp)
    
    st.divider()
    
    # 4. Seleção do Modelo FEFCO
    modelo_fefco = st.selectbox("4. Modelo da Caixa", [
        "0200 - Meia Maleta (Sem abas superiores)",
        "0201 - Maleta Padrão",
        "0202 - Maleta com Aba Sobreposta",
        "0203 - Maleta com Aba Total (FOL)",
        "0204 - Maleta Especial",
        "0427 - Correio / E-commerce (Corte e Vinco)",
        "0421 - Bandeja Montável",
        "0300 - Caixa Telescópica (Tampa e Fundo)",
        "0701 - Fundo Automático",
        "0901 - Divisória / Calço"
    ])

# --- ÁREA CENTRAL: MEDIDAS ---
st.subheader("Medidas Internas e Quantidade")
c1, c2, c3, c4 = st.columns(4)
L = c1.number_input("Comprimento (mm)", value=300)
W = c2.number_input("Largura (mm)", value=200)
H = c3.number_input("Altura (mm)", value=150)
qtd = c4.number_input("Quantidade Total", value=500, step=100)

# =========================================================
# 4. MOTOR DE CÁLCULO (GEOMETRIA PRINECT)
# =========================================================
d = CONFIG_TECNICA[onda_sel]["d"]
gl = CONFIG_TECNICA[onda_sel]["gl"]
preco_m2_base = DADOS_COMERCIAIS[onda_sel][papel_sel][coluna_sel]

if "0200" in modelo_fefco:
    bL, bW = (2*L + 2*W + gl), (H + W/2 + d)
elif "0201" in modelo_fefco:
    bL, bW = (2*L + 2*W + gl), (H + W + d)
elif "0203" in modelo_fefco:
    bL, bW = (2*L + 2*W + gl), (H + 2*W + d) # Aba Total
elif "0427" in modelo_fefco:
    bL, bW = (L + 4*H + 6*d), (2*W + 3*H + 20)
elif "0701" in modelo_fefco:
    bL, bW = (2*L + 2*W + gl), (H + W + d) # Baseado na 0201 para estimativa
else:
    bL, bW = L + 20, W + 20 # Cálculo genérico para outros modelos

area_m2 = (bL * bW) / 1_000_000
valor_unit = (area_m2 * preco_m2_base) * 2.0 # FATOR 100 (Markup 2.0x)

# --- QUADRO DE RESUMO ---
st.divider()
st.markdown(f"### Orçamento para **{modelo_fefco}**")
r1, r2, r3 = st.columns(3)

with r1:
    st.metric("Preço Unitário", f"R$ {valor_unit:.2f}")
    st.write(f"Total: R$ {valor_unit * qtd:,.2f}")

with r2:
    st.info(f"**Formato da Chapa:**\n\n{bL:.0f} x {bW:.0f} mm")
    st.write(f"Material: {onda_sel} | {papel_sel} | {coluna_sel} Kgf")

with r3:
    if st.button("➕ ADICIONAR AO CARRINHO", use_container_width=True):
        item = {
            "Modelo": modelo_fefco,
            "Medidas": f"{L}x{W}x{H}",
            "Chapa": f"{onda_sel} {papel_sel}",
            "Coluna": coluna_sel,
            "Qtd": qtd,
            "Unit.": valor_unit,
            "Total": valor_unit * qtd
        }
        adicionar_ao_carrinho(item)

# =========================================================
# 5. EXIBIÇÃO DO CARRINHO
# =========================================================
if st.session_state.carrinho:
    st.markdown("---")
    st.subheader("🛒 Itens no Orçamento")
    df_cart = pd.DataFrame(st.session_state.carrinho)
    st.table(df_cart)
    
    total_geral = df_cart["Total"].sum()
    st.markdown(f"## **Valor Total do Pedido: R$ {total_geral:,.2f}**")
    
    if st.button("Limpar Carrinho"):
        st.session_state.carrinho = []
        st.rerun()
