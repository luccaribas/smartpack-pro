import streamlit as st
import pandas as pd
import math

# =========================================================
# 1. SMARTPACK BACKEND V5 (MANTIDO - CALIBRAÇÃO EXATA)
# =========================================================
class CalibrationEngine:
    @staticmethod
    def get_factors(modelo, d):
        fam = str(modelo)[0]
        if fam in ['2', '5', '6', '7']: # Tubulares
            return {'C90': 0.5, 'C180': 1.0*d, 'HC90': 1.7*d, 'Glue': 0.5, 'Slot': d+1.0, 'Profile': 'Tubular'}
        elif fam in ['3', '4']: # Tabuleiros
            return {'C90': 1.0*d, 'C180': 2.0*d, 'HC90': 1.0*d, 'Glue': 1.0*d, 'Slot': d+2.0, 'Profile': 'Tabuleiro'}
        else: return {'C90': 0.5*d, 'C180': d, 'HC90': d, 'Glue': 0, 'Slot': d, 'Profile': 'Generico'}

class SmartPackBackend:
    def __init__(self, csv_path='formulas_smartpack.csv'):
        try:
            self.df = pd.read_csv(csv_path, delimiter=';', dtype={'Modelo': str})
            self.df['Modelo'] = self.df['Modelo'].str.lstrip('0')
        except FileNotFoundError: return

    def get_available_models(self):
        if not hasattr(self, 'df'): return []
        return sorted(self.df['Modelo'].unique())

    def _get_engine_variables(self, modelo, L, W, H, d):
        modelo = str(modelo).lstrip('0')
        df_model = self.df[self.df['Modelo'] == modelo]
        if df_model.empty: return None

        k = CalibrationEngine.get_factors(modelo, d)
        contexto = {
            'L': float(L), 'W': float(W), 'H': float(H), 'd': lambda: float(d),
            'dtID': 1, 'dtOD': 0, 'No': 0, 'Yes': 1, 'Flat': 0, 'Round': 1, 'fd': lambda: 0,
            'sqrt': math.sqrt, 'min': min, 'max': max, 'tan': math.tan, 'atan': math.atan,
            'C90x': lambda *a: k['C90'], 'C90y': lambda *a: k['C90'],
            'HC90x': lambda *a: k['HC90'], 'GlueCorr': lambda *a: k['Glue'],
            'LPCorr': lambda *a: 1.0 * d, 'GLWidth': lambda *a: 35.0,
            'LSCf': lambda *a: 1.5 * d, 'SlotWidth': lambda *a: k['Slot'],
            'LC': lambda d_val, dt, iln, oln: (iln if dt==1 else oln) * d,
            'switch': lambda cond, *args: args[1] if cond else args[0]
        }
        
        resolvidos = {}
        for _ in range(5):
            for _, row in df_model.iterrows():
                param = row['Parametro']
                formula = str(row['Formula'])
                if param in ['L', 'W', 'H', 'UL', 'DT']: continue
                try:
                    if formula.replace('.','',1).isdigit(): val = float(formula)
                    else: val = eval(formula.replace('^', '**'), {}, contexto)
                    contexto[param] = val
                    resolvidos[param] = val
                except: pass
        resolvidos['_Profile'] = k['Profile']
        return resolvidos

    def calcular_blank(self, modelo, L, W, H, d):
        vars_eng = self._get_engine_variables(modelo, L, W, H, d)
        if not vars_eng: return 0, 0, "Erro"

        k = CalibrationEngine.get_factors(modelo, d)
        Lss = vars_eng.get('Lss', L + k['C90']*2)
        Wss = vars_eng.get('Wss', W + k['C90']*2)
        Hss = vars_eng.get('Hss', H + k['HC90'])
        
        has_GL = 'GL' in vars_eng or 'GLWidth' in str(self.df[self.df['Modelo']==modelo]['Formula'].values)
        
        if has_GL or modelo.startswith(('2', '5', '6', '7')):
            GL = vars_eng.get('GL', 35.0)
            Blank_X = GL + Lss + Wss + Lss + Wss
            Flap_Top = vars_eng.get('FH', Wss / 2)
            if modelo == '200': Flap_Top = 0
            elif modelo == '203': Flap_Top = Wss - d
            Blank_Y = Flap_Top + Hss + vars_eng.get('FH_B', Flap_Top)
            return Blank_X, Blank_Y, k['Profile']

        elif modelo == '427':
            HssY = vars_eng.get('HssY', H + 2*d)
            FH1 = HssY + (1.5 * d)
            TIFH = H - ((3 * d) + 1.0)
            Blank_X = TIFH + Wss + HssY + Wss + FH1
            PH = HssY - (0.5 * d)
            Ear = HssY + 14.0
            Blank_Y = Ear + PH + Lss + PH + Ear
            return Blank_Y, Blank_X, "0427 Gold"

        else:
            Wall_H = vars_eng.get('Hss', H + d)
            if modelo.startswith('3'):
                return Lss + (2 * Wall_H), Wss + (2 * Wall_H), k['Profile']
            else:
                return Lss + (2 * Wall_H), Wss + (3 * Wall_H), "Estimado"

# =========================================================
# 2. INTERFACE E CARREGAMENTO DE DADOS
# =========================================================
st.set_page_config(page_title="SmartPack Enterprise", layout="wide")

@st.cache_resource
def load_engine():
    return SmartPackBackend('formulas_smartpack.csv')

engine = load_engine()

if 'carrinho' not in st.session_state: st.session_state.carrinho = []

st.title("🏭 SmartPack Enterprise")
st.markdown("---")

# --- AREA DE GESTÃO (CARGA DE DADOS) ---
with st.sidebar:
    st.header("📂 Base de Dados")
    
    # 1. Upload da Tabela de Materiais
    uploaded_file = st.file_uploader("Carregar Tabela de Qualidades (CSV)", type="csv")
    
    df_materiais = None
    if uploaded_file is not None:
        try:
            df_materiais = pd.read_csv(uploaded_file, sep=';') # Tenta ponto e vírgula primeiro (Excel BR)
            if len(df_materiais.columns) < 2: 
                uploaded_file.seek(0)
                df_materiais = pd.read_csv(uploaded_file, sep=',') # Tenta vírgula
            st.success(f"✅ {len(df_materiais)} materiais carregados!")
        except:
            st.error("Erro ao ler CSV. Verifique o formato.")
    else:
        st.warning("⚠️ Por favor, suba o arquivo 'materiais.csv' para iniciar.")
        st.info("Colunas esperadas: Onda, Papel, Gramatura, Espessura, Coluna, Preco_m2")
        st.stop() # Para o código aqui até ter o arquivo

    st.divider()
    st.header("⚙️ Configuração do Pedido")

    # 2. Filtros em Cascata (Onda -> Papel -> Coluna)
    # Lista única de ondas disponíveis no CSV
    ondas_disponiveis = df_materiais['Onda'].unique()
    onda_sel = st.selectbox("1. Onda", ondas_disponiveis)
    
    # Filtra papéis dessa onda
    df_onda = df_materiais[df_materiais['Onda'] == onda_sel]
    papeis_disponiveis = df_onda['Papel'].unique()
    papel_sel = st.selectbox("2. Qualidade do Papel", papeis_disponiveis)
    
    # Filtra colunas desse papel
    df_final = df_onda[df_onda['Papel'] == papel_sel]
    colunas_disponiveis = df_final['Coluna'].unique()
    coluna_sel = st.selectbox("3. Resistência (Coluna)", colunas_disponiveis)
    
    # --- RECUPERAÇÃO DOS DADOS TÉCNICOS ---
    # Pega a linha exata da tabela que o usuário escolheu
    material_escolhido = df_final[df_final['Coluna'] == coluna_sel].iloc[0]
    
    espessura_real = float(material_escolhido['Espessura'])
    preco_base = float(material_escolhido['Preco_m2'])
    gramatura = material_escolhido['Gramatura']
    
    st.divider()
    st.header("📐 Modelo")
    modelos_disponiveis = engine.get_available_models()
    populares = ['201', '427', '200', '203', '300', '711']
    lista_final = [m for m in populares if m in modelos_disponiveis] + [m for m in modelos_disponiveis if m not in populares]
    
    modelo_visual = st.selectbox("Selecione o Modelo", lista_final, format_func=lambda x: f"FEFCO {x.zfill(4)}")

# =========================================================
# 3. ÁREA DO CLIENTE VS FÁBRICA
# =========================================================

col1, col2 = st.columns([1, 2])

with col1:
    st.subheader("📝 Medidas Internas")
    L = st.number_input("Comprimento (mm)", value=300)
    W = st.number_input("Largura (mm)", value=200)
    H = st.number_input("Altura (mm)", value=100)
    qtd = st.number_input("Quantidade", value=1000, step=100)
    
    st.markdown("---")
    st.caption("Resumo do Material:")
    st.text(f"Onda: {onda_sel} ({espessura_real}mm)\nPapel: {papel_sel}\nGramatura: {gramatura} g/m²")

# CÁLCULO
bL, bW, perfil = engine.calcular_blank(modelo_visual, L, W, H, espessura_real)
area_m2 = (bL * bW) / 1_000_000
custo_material = area_m2 * preco_base
preco_venda = custo_material * 2.0 # Margem de 100%

with col2:
    # ABAS PARA VISÃO DIFERENTE
    tab_cliente, tab_fabrica = st.tabs(["👤 Visão do Cliente (Orçamento)", "🏭 Visão da Fábrica (Produção)"])
    
    with tab_cliente:
        st.subheader("💰 Orçamento Final")
        c1, c2 = st.columns(2)
        c1.metric("Preço Unitário", f"R$ {preco_venda:.2f}")
        c2.metric("Total do Pedido", f"R$ {preco_venda * qtd:,.2f}")
        
        st.success(f"**Produto:** Caixa FEFCO {modelo_visual} em {papel_sel}")
        st.info("Este valor inclui material, produção e impostos estimados.")
        
        if st.button("🛒 Adicionar ao Pedido", type="primary", use_container_width=True):
            st.session_state.carrinho.append({
                "Modelo": modelo_visual,
                "Dimensões": f"{L}x{W}x{H}",
                "Material": f"{onda_sel} - {coluna_sel} Coluna",
                "Qtd": qtd,
                "Total": preco_venda * qtd
            })
            st.toast("Adicionado com sucesso!")

    with tab_fabrica:
        st.subheader("⚙️ Ordem de Produção Técnica")
        st.warning("Área Restrita - Dados para Programação de Máquina")
        
        st.markdown(f"""
        ### 1. Especificação da Chapa (Papelão)
        | Parâmetro | Valor |
        | :--- | :--- |
        | **Onda** | {onda_sel} (Espessura: {espessura_real}mm) |
        | **Composição** | {papel_sel} |
        | **Gramatura** | {gramatura} g/m² |
        | **Coluna (Resistência)** | **{coluna_sel} kgf** |
        
        ### 2. Dimensões de Corte (Blank)
        | Dimensão | Valor Calculado |
        | :--- | :--- |
        | **Largura da Chapa** | **{bL:.1f} mm** |
        | **Comprimento da Chapa** | **{bW:.1f} mm** |
        | **Área Unitária** | {area_m2:.4f} m² |
        | **Perfil de Vinco** | {perfil} |
        """)
        
        st.code(f"""
        CODIGO_MAQUINA: {modelo_visual}
        BLANK_X: {bL:.1f}
        BLANK_Y: {bW:.1f}
        ESPESSURA: {espessura_real}
        COLUNA: {coluna_sel}
        """, language="yaml")

# Carrinho no rodapé
if st.session_state.carrinho:
    st.markdown("---")
    st.subheader("Resumo dos Pedidos")
    st.dataframe(pd.DataFrame(st.session_state.carrinho), use_container_width=True)
