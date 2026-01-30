import streamlit as st
import pandas as pd
import math
import os

# =========================================================
# 1. SMARTPACK TRANSLATOR ENGINE (V14 - FULL PRINECT SUPPORT)
# =========================================================
class SmartPackBackend:
    def __init__(self, csv_path='formulas_smartpack.csv'):
        if os.path.exists(csv_path):
            try:
                # O parâmetro 'error_bad_lines' ou 'on_bad_lines' evita travar em linhas sujas
                self.df = pd.read_csv(csv_path, delimiter=';', dtype={'Modelo': str}, on_bad_lines='skip')
                self.df['Modelo'] = self.df['Modelo'].str.lstrip('0')
            except: self.df = pd.DataFrame()
        else: self.df = pd.DataFrame()

    def get_available_models(self):
        if self.df.empty: return []
        return sorted(self.df['Modelo'].unique())

    def _resolve_formulas(self, modelo, L, W, H, d):
        modelo = str(modelo).lstrip('0')
        if self.df.empty: return None
        df_model = self.df[self.df['Modelo'] == modelo]
        if df_model.empty: return None

        # --- O DICIONÁRIO DE TRADUÇÃO (ROSETTA STONE) ---
        # Aqui ensinamos ao Python o que cada código estranho do Prinect significa.
        
        # 1. Definição de Perfil (Tubular vs Plano)
        fam = modelo[0]
        is_tubular = fam in ['2','5','6','7']
        
        # Fatores de Compensação (K-Factors)
        k = {'C90': 0.5, 'HC90': 1.7*d, 'Glue': 0.5, 'Slot': d+1.0} if is_tubular else {'C90': 1.0*d, 'HC90': 1.0*d, 'Glue': 1.0*d, 'Slot': d+2.0}
        
        # 2. Contexto Matemático Completo
        contexto = {
            # Variáveis Básicas
            'L': float(L), 'W': float(W), 'H': float(H), 
            'd': lambda: float(d), # d() como função
            
            # Constantes Prinect (Flags)
            'dtID': 1, 'dtOD': 0, 'No': 0, 'Yes': 1, 'Flat': 0, 'Round': 1, 
            'fd': lambda: 0, # Flute Direction (ignorar para tamanho)
            'DT': 1, # Dimension Type (Inner Dimensions)
            'UL': 1, # Use Layers (Sim)
            
            # Matemática Pura
            'sqrt': math.sqrt, 'min': min, 'max': max, 'tan': math.tan, 'atan': math.atan,
            
            # --- TRADUÇÃO DAS FUNÇÕES DO SEU EXEMPLO ---
            'C90x': lambda *a: k['C90'],       # Correção X
            'C90y': lambda *a: k['C90'],       # Correção Y
            'HC90x': lambda *a: k['HC90'],     # Correção Altura
            'GlueCorr': lambda *a: k['Glue'],  # Correção Cola
            'LPCorr': lambda *a: 0.0,          # Line Correction (Geralmente 0 para corte)
            'GLWidth': lambda *a: 35.0,        # Largura Aba Cola Padrão
            'LSC': 0.0,                        # Layer Score Correction (Refinado)
            'Wlc': 0.0,                        # Width Correction (Refinado)
            'SlotWidth': lambda *a: k['Slot'],
            
            # Funções Genéricas para evitar erro
            'O90y': lambda *a: d, 'DC0y': lambda *a: 0, 'I90y': lambda *a: d
        }
        
        resolvidos = {}
        
        # 3. Processador Robusto (5 Passadas)
        # O Python lê as fórmulas várias vezes para resolver dependências (Ex: FH depende de Wlc)
        for _ in range(5):
            for _, row in df_model.iterrows():
                try:
                    param = row['Parametro']
                    formula = str(row['Formula'])
                    
                    # Limpeza de String (Remove caracteres invisíveis do copy-paste)
                    formula = formula.strip().replace('=', '')
                    
                    if param in ['L', 'W', 'H']: continue
                    
                    # Tenta calcular
                    if formula.replace('.','',1).isdigit(): 
                        val = float(formula)
                    else: 
                        # O segredo: eval() usa o nosso 'contexto' para traduzir
                        val = eval(formula.replace('^', '**'), {}, contexto)
                    
                    # Salva no contexto para a próxima linha poder usar
                    contexto[param] = val
                    resolvidos[param] = val
                except: 
                    # Se falhar (ex: variável desconhecida), define como 0.0 para não quebrar o resto
                    if param not in contexto:
                        contexto[param] = 0.0
                        
        return resolvidos

    def calcular_blank_exato(self, modelo, L, W, H, d):
        vars_eng = self._resolve_formulas(modelo, L, W, H, d)
        if not vars_eng: return 0, 0, "Modelo Inexistente"

        # Recupera as dimensões calculadas
        Lss = vars_eng.get('Lss', L + d)
        Wss = vars_eng.get('Wss', W + d)
        Hss = vars_eng.get('Hss', H + (1.7*d if modelo[0] in ['2','5','7'] else d))

        # --- MONTAGEM FINAL DO BLANK ---
        has_GL = 'GL' in vars_eng or 'GLWidth' in str(self.df[self.df['Modelo']==modelo]['Formula'].values)
        
        if has_GL:
            GL = vars_eng.get('GL', 35.0)
            
            # Correção Fundo Automático (07xx)
            setback = 2.0 * d if modelo.startswith('7') else 0
            Blank_X = GL + 2*(Lss + Wss) - setback
            
            # Altura (Soma dos Flaps calculados pelo CSV)
            FH_Top = vars_eng.get('FH', Wss/2)
            
            # Lógica Inteligente para Fundo
            if 'Ext' in vars_eng: # Se achou a extensão do fundo automático
                FH_Bottom = (Wss/2) + vars_eng['Ext']
            elif 'FH_B' in vars_eng: 
                FH_Bottom = vars_eng['FH_B']
            else:
                FH_Bottom = FH_Top
                
            Blank_Y = FH_Top + Hss + FH_Bottom
            return Blank_X, Blank_Y, "Cálculo Prinect (Traduzido)"
            
        elif modelo == '427':
            HssY = vars_eng.get('HssY', H + 2*d)
            FH1 = HssY + (1.5 * d)
            Blank_X = (H - ((3 * d) + 1.0)) + Wss + HssY + Wss + FH1
            Blank_Y = (HssY + 14.0)*2 + (HssY - 0.5*d)*2 + Lss
            return Blank_Y, Blank_X, "E-commerce (Gold)"
            
        else:
            # Genérico Tabuleiro
            Wall_H = vars_eng.get('Hss', H)
            return Lss + 2*Wall_H, Wss + 2*Wall_H, "Tabuleiro Genérico"

# =========================================================
# 2. INTERFACE
# =========================================================
st.set_page_config(page_title="SmartPack V14", layout="wide")

@st.cache_resource
def load_engine_v14():
    return SmartPackBackend('formulas_smartpack.csv')

engine = load_engine_v14()
if 'carrinho' not in st.session_state: st.session_state.carrinho = []

@st.cache_data
def load_prices_safe():
    try:
        arquivos = [f for f in os.listdir() if 'materiais' in f.lower() and 'csv' in f.lower()]
        if arquivos:
            df = pd.read_csv(arquivos[0], sep=';')
            if len(df.columns) < 2: df = pd.read_csv(arquivos[0], sep=',')
            return df
    except: pass
    return pd.DataFrame({
        'Onda': ['B', 'C', 'BC'], 'Papel': ['Padrão', 'Reforçado', 'Duplo'],
        'Gramatura': [380, 440, 700], 'Espessura': [3.0, 4.0, 6.9],
        'Coluna': [4.0, 5.5, 8.0], 'Preco_m2': [2.77, 3.88, 5.45]
    })

df_materiais = load_prices_safe()

st.title("🏭 SmartPack V14 - Prinect Interpreter")

with st.sidebar:
    st.header("1. Material")
    onda = st.selectbox("Onda", df_materiais['Onda'].unique())
    df_o = df_materiais[df_materiais['Onda'] == onda]
    papel = st.selectbox("Papel", df_o['Papel'].unique())
    df_p = df_o[df_o['Papel'] == papel]
    coluna = st.selectbox("Resistência", df_p['Coluna'].unique())
    
    mat = df_p[df_p['Coluna'] == coluna].iloc[0]
    d_real = float(mat['Espessura'])
    preco = float(mat['Preco_m2'])
    
    st.divider()
    st.header("2. Modelo")
    modelos = engine.get_available_models()
    tops = ['201', '427', '200', '711', '215']
    lista = [m for m in tops if m in modelos] + [m for m in modelos if m not in tops]
    modelo = st.selectbox("Código FEFCO", lista, format_func=lambda x: f"{x.zfill(4)}")

col1, col2 = st.columns([1, 2])
with col1:
    st.subheader("Medidas (mm)")
    L = st.number_input("Comprimento", value=300)
    W = st.number_input("Largura", value=200)
    H = st.number_input("Altura", value=100)
    qtd = st.number_input("Quantidade", value=500, step=100)

bL, bW, perfil = engine.calcular_blank_exato(modelo, L, W, H, d_real)
area = (bL * bW) / 1_000_000
total = (area * preco) * 2.0 * qtd

with col2:
    st.subheader("Resultado")
    st.success(f"Lógica: **{perfil}**")
    
    c1, c2 = st.columns(2)
    c1.metric("Largura Chapa", f"{bL:.1f} mm")
    c2.metric("Compr. Chapa", f"{bW:.1f} mm")
    
    st.info(f"Consumo: {area:.4f} m² | Total: R$ {total:,.2f}")
    
    if st.button("🛒 Adicionar"):
        st.session_state.carrinho.append({"Modelo": modelo, "Total": total})
