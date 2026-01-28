import streamlit as st

# TABELA DE PREÇOS FERNANDEZ (SETEMBRO/2024)
PRECOS = {
    "FK1L-B": {"m2": 2.633, "gram": 360, "onda": "B", "min": 250},
    "FK2-B": {"m2": 2.801, "gram": 380, "onda": "B", "min": 250},
    "FK2-C": {"m2": 2.874, "gram": 390, "onda": "C", "min": 250},
    "FK2-BC": {"m2": 4.864, "gram": 660, "onda": "BC", "min": 250},
    "KMK-BC": {"m2": 5.387, "gram": 660, "onda": "BC", "min": 300},
    "BMC-BC": {"m2": 6.543, "gram": 690, "onda": "BC", "min": 300}
}

st.set_page_config(page_title="New Age - Orçador", layout="wide")
st.title("📦 Calculadora New Age Embalagens")

# ENTRADA DE DADOS
with st.sidebar:
    st.header("Dados do Pedido")
    modelo = st.selectbox("Modelo FEFCO", ["0201", "0200", "0202", "0427", "0426", "0424", "0901", "0903"])
    chapa = st.selectbox("Qualidade", list(PRECOS.keys()))
    L = st.number_input("Comprimento (mm)", value=300)
    W = st.number_input("Largura (mm)", value=200)
    H = st.number_input("Altura (mm)", value=200)
    qtd = st.number_input("Quantidade", value=1000)

# REGRAS TÉCNICAS
info = PRECOS[chapa]
# Espessura aproximada baseada nos arquivos .evr
d = 3.0 if info['onda'] == "B" else 6.5 

# REGRA DE REFILE: 30mm para Corte e Vinco, 0mm para Maletas/Acessórios
refile = 30 if modelo.startswith("04") else 0

# GEOMETRIA (Lógica Prinect)
if modelo.startswith("02"):
    blank_L = (2 * L) + (2 * W) + 40 + (4 * 6)
    blank_W = H + W + (d * 0.8) # Correção DxT
elif modelo.startswith("04"):
    blank_L = L + (4 * H) + (6 * d)
    blank_W = (2 * W) + (3 * H) + 20
else:
    blank_L, blank_W = L, W

# RESULTADO (Fator 100 = Dobro do Custo)
area_m2 = ((blank_L + refile) * (blank_W + refile)) / 1_000_000
preco_unit = (area_m2 * info['m2']) * 2.0
peso_total = (area_m2 * info['gram'] * qtd) / 1000

# EXIBIÇÃO
col_res1, col_res2 = st.columns(2)
with col_res1:
    st.metric("Preço Unitário (Fator 100)", f"R$ {preco_unit:.2f}")
    st.write(f"**Chapa aberta:** {blank_L + refile:.0f} x {blank_W + refile:.0f} mm")

with col_res2:
    st.write(f"**Peso Total:** {peso_total:.1f} kg")
    if peso_total < info['min']:
        st.error(f"⚠️ Abaixo do mínimo de {info['min']}kg (Fernandez)") #
    else:
        st.success("✅ Pedido dentro do mínimo para produção.")
