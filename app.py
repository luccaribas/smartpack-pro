import streamlit as st
import pandas as pd
import math

# =========================================================
# 1. ENGINE DE CALIBRAÇÃO (A INTELIGÊNCIA AUTOMÁTICA)
# =========================================================
class CalibrationEngine:
    """
    Define os fatores K (Compensação) para cada família FEFCO.
    Isso garante o 'Ajuste Fino' automático para as 6000 caixas.
    """
    @staticmethod
    def get_factors(modelo, d):
        # 1. Identifica a Família
        fam = str(modelo)[0] # '2', '3', '4'...
        
        # --- PERFIL A: TUBULARES (Maletas 02xx, Coladas 07xx, Deslizantes 05xx) ---
        # Característica: O vinco "quebra" a fibra e esmaga o papelão.
        # A compensação é mínima no comprimento e alta na altura.
        if fam in ['2', '5', '6', '7']:
            return {
                'C90': 0.5,             # Perda no Comprimento (Quase zero, fixo)
                'C180': 1.0 * d,        # Dobra total (se houver)
                'HC90': 1.7 * d,        # Ganho na Altura (Onda 3mm -> +5.1mm)
                'Glue': 0.5,            # Ganho na Aba de Cola
                'Slot': d + 1.0,        # Abertura do Slot (Justa)
                'Profile': 'Tubular (Crushed Crease)'
            }
            
        # --- PERFIL B: TABULEIROS (Tampas 03xx, Corte e Vinco 04xx) ---
        # Característica: O papelão dobra sobre si mesmo (parede dupla).
        # A compensação é geometricamente igual à espessura.
        elif fam in ['3', '4']:
            return {
                'C90': 1.0 * d,         # Perda = Espessura (Geometria Pura)
                'C180': 2.0 * d,        # Dobra dupla (Travas)
                'HC90': 1.0 * d,        # Ganho na Altura = Espessura
                'Glue': 1.0 * d,        # (Raro em 04xx, mas segue espessura)
                'Slot': d + 2.0,        # Abertura do Slot (Folgada para encaixe)
                'Profile': 'Tray (Rolling Fold)'
            }
            
        # --- PERFIL C: INTERNOS (09xx) ---
        else:
            return {
                'C90': 0.5 * d, 'C180': d, 'HC90': d, 'Glue': 0, 'Slot': d,
                'Profile': 'Generic'
            }

# =========================================================
# 2. SMARTPACK BACKEND (PROCESSADOR)
# =========================================================
class SmartPackBackend:
    def __init__(self, csv_path='formulas_smartpack.csv'):
        try:
            self.df = pd.read_csv(csv_path, delimiter=';', dtype={'Modelo': str})
            self.df['Modelo'] = self.df['Modelo'].str.lstrip('0')
        except FileNotFoundError:
            st.error("❌ Erro CRÍTICO: 'formulas_smartpack.csv' não encontrado.")
            st.stop()

    def get_available_models(self):
        if self.df.empty: return []
        return sorted(self.df['Modelo'].unique())

    def _get_engine_variables(self, modelo, L, W, H, d):
        modelo = str(modelo).lstrip('0')
        df_model = self.df[self.df['Modelo'] == modelo]
        
        if df_model.empty: return None

        # --- APLICAÇÃO DO AJUSTE FINO AUTOMÁTICO ---
        # Pega o perfil exato para este modelo
        k = CalibrationEngine.get_factors(modelo, d)

        # Injeta os fatores no contexto matemático
        contexto = {
            'L': float(L), 'W': float(W), 'H': float(H), 'd': lambda: float(d),
            'dtID': 1, 'dtOD': 0, 'No': 0, 'Yes': 1, 'Flat': 0, 'Round': 1, 'fd': lambda: 0,
            'sqrt': math.sqrt, 'min': min, 'max': max, 'tan': math.tan, 'atan': math.atan,
            
            # --- MAPEAMENTO DIRETO DE ENGENHARIA ---
            # Aqui garantimos que TODAS as fórmulas do CSV usem os valores calibrados
            'C90x': lambda *a: k['C90'], 
            'C90y': lambda *a: k['C90'],
            'HC90x': lambda *a: k['HC90'], 
            'GlueCorr': lambda *a: k['Glue'],
            'LPCorr': lambda *a: 1.0 * d, 
            'GLWidth': lambda *a: 35.0, # Padrão
            'LSCf': lambda *a: 1.5 * d, 
            'SlotWidth': lambda *a: k['Slot'],
            'LC': lambda d_val, dt, iln, oln: (iln if dt==1 else oln) * d,
            'switch': lambda cond, *args: args[1] if cond else args[0]
        }
        
        resolvidos = {}
        # Resolve todas as 6000 fórmulas com os novos fatores
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
        
        # Adiciona o perfil ao resultado para debug
        resolvidos['_Profile'] = k['Profile']
        return resolvidos

    def calcular_blank(self, modelo, L, W, H, d):
        vars_eng = self._get_engine_variables(modelo, L, W, H, d)
        if not vars_eng: return 0, 0, "Erro"

        # Variáveis base do CSV (Já calibradas)
        # Se o CSV falhar, usa o fator K correspondente como fallback
        k = CalibrationEngine.get_factors(modelo, d)
        
        Lss = vars_eng.get('Lss', L + k['C90']*2)
        Wss = vars_eng.get('Wss', W + k['C90']*2)
        Hss = vars_eng.get('Hss', H + k['HC90'])
        
        # --- TOPOLOGIA AUTOMÁTICA ---
        has_GL = 'GL' in vars_eng or 'GLWidth' in str(self.df[self.df['Modelo']==modelo]['Formula'].values)
        
        # 1. TOPOLOGIA TUBULAR (Maletas e afins)
        if has_GL or modelo.startswith(('2', '5', '6', '7')):
            GL = vars_eng.get('GL', 35.0)
            Blank_X = GL + Lss + Wss + Lss + Wss
            
            Flap_Top = vars_eng.get('FH', Wss / 2)
            if modelo == '200': Flap_Top = 0
            elif modelo == '203': Flap_Top = Wss - d
            elif modelo.startswith('7'): Flap_Top = Wss * 0.5 # Padrão
            
            # Espelhamento inteligente do fundo
            Flap_Bottom = vars_eng.get('FH_B', Flap_Top)
            
            Blank_Y = Flap_Top + Hss + Flap_Bottom
            return Blank_X, Blank_Y, k['Profile']

        # 2. TOPOLOGIA COMPLEXA (0427 E-commerce)
        elif modelo == '427':
            # Usa geometria validada, mas alimentada pelos K-Factors calibrados
            HssY = vars_eng.get('HssY', H + 2*d)
            FH1 = HssY + (1.5 * d)
            TPH = H
            DxPI = (3 * d) + 1.0
            TIFH = TPH - DxPI
            Blank_X = TIFH + Wss + HssY + Wss + FH1
            Ear = HssY + 14.0
            PH = HssY - (0.5 * d)
            Blank_Y = Ear + PH + Lss + PH + Ear
            return Blank_Y, Blank_X, "0427 Gold Standard"

        # 3. TOPOLOGIA TABULEIRO (Caixas Telescópio / Corte e Vinco Genérico)
        else:
            Wall_H = vars_eng.get('Hss', H + d)
            
            if modelo.startswith('3'): # Telescópio
                Blank_X = Lss + (2 * Wall_H)
                Blank_Y = Wss + (2 * Wall_H)
                return Blank_X, Blank_Y, k['Profile']
            else: # Envelopes 04xx Genéricos
                # Se não temos a geometria exata, confiamos nas variáveis do CSV
                # Se o CSV tiver 'L_Blank', usamos ele.
                bL = vars_eng.get('L_Blank', 0)
                bW = vars_eng.get('W_Blank', 0)
                
                if bL > 0: return bL, bW, "CSV Nativo"
                
                # Estimativa geométrica baseada em K-Factor
                Blank_X = Lss + (2 * Wall_H)
                Blank_Y = Wss + (3 * Wall_H)
                return Blank_X, Blank_Y, "Tray (Estimado)"

# =========================================================
# 3. APP CONFIG E INTERFACE
# =========================================================
st.set_page_config(page_title="SmartPack Auto-Tuning", layout="wide")

@st.cache_resource
def load_engine_v6(): # Nova versão para limpar cache
    return SmartPackBackend('formulas_smartpack.csv')

engine = load_engine_v6()

# Configuração de Materiais
CONFIG_TECNICA = {
    "Onda B": {"d": 3.0}, "Onda C": {"d": 4.0},
    "Onda BC (Dupla)": {"d": 6.9}, "Onda E (Micro)": {"d": 1.5},
    "Onda EB (Dupla)": {"d": 4.4}
}
MATERIAIS = {
    "Onda B": {"Papel Padrão (Reciclado)": {3.5: 2.956, 4.0: 2.770, 5.0: 3.143}, "Papel Branco": {5.0: 3.793}},
    "Onda C": {"Papel Padrão (Reciclado)": {3.5: 3.038, 4.0: 2.853, 6.0: 4.424}, "Papel Branco": {5.0: 3.885}},
    "Onda BC (Dupla)": {"Papel Padrão (Reciclado)": {7.0: 5.008, 9.5: 6.699}, "Papel Branco": {8.0: 6.383}}
}

if 'carrinho' not in st.session_state: st.session_state.carrinho = []
def add_to_cart(item):
    st.session_state.carrinho.append(item)
    st.toast("Adicionado! 🛒", icon="✅")

st.title("🛡️ SmartPack Pro - Auto Tuning")
st.caption(f"🤖 Engine V6: {len(engine.get_available_models())} modelos com calibração automática por família.")

with st.sidebar:
    st.header("1. Material")
    onda_sel = st.selectbox("Onda", list(MATERIAIS.keys()))
    papel_sel = st.selectbox("Papel", list(MATERIAIS[onda_sel].keys()))
    coluna_sel = st.selectbox("Resistência", list(MATERIAIS[onda_sel][papel_sel].keys()))
    
    st.divider()
    st.header("2. Modelo")
    
    modelos_disponiveis = engine.get_available_models()
    populares = ['201', '427', '200', '203', '300', '301', '409', '711']
    lista_final = [m for m in populares if m in modelos_disponiveis] + [m for m in modelos_disponiveis if m not in populares]
    
    modelo_visual = st.selectbox("Selecione o Modelo FEFCO", lista_final, format_func=lambda x: f"FEFCO {x.zfill(4)}")
    codigo_modelo = modelo_visual

espessura_d = CONFIG_TECNICA[onda_sel]["d"]
preco_m2_base = MATERIAIS[onda_sel][papel_sel][coluna_sel]

col1, col2 = st.columns([1, 2])
with col1:
    st.subheader("Medidas Internas")
    L = st.number_input("Comprimento (mm)", value=300)
    W = st.number_input("Largura (mm)", value=200)
    H = st.number_input("Altura (mm)", value=100)
    qtd = st.number_input("Quantidade", value=500, step=100)

bL, bW, perfil = engine.calcular_blank(codigo_modelo, L, W, H, espessura_d)
area_m2 = (bL * bW) / 1_000_000
valor_unit = (area_m2 * preco_m2_base) * 2.0 

with col2:
    st.subheader("Orçamento Calibrado")
    st.success(f"Perfil de Engenharia: **{perfil}**")
    
    c1, c2, c3 = st.columns(3)
    c1.metric("Preço Unitário", f"R$ {valor_unit:.2f}")
    c2.metric("Total", f"R$ {valor_unit * qtd:,.2f}")
    c3.metric("Área/Caixa", f"{area_m2:.3f} m²")
    
    st.markdown(f"**Blank Final:** {bL:.1f} x {bW:.1f} mm")
    
    if st.button("➕ ADICIONAR AO CARRINHO", type="primary", use_container_width=True):
        add_to_cart({
            "Modelo": f"FEFCO {codigo_modelo}",
            "Medidas": f"{L}x{W}x{H}",
            "Material": f"{onda_sel}",
            "Blank": f"{bL:.0f}x{bW:.0f}mm",
            "Total": valor_unit * qtd
        })

if st.session_state.carrinho:
    st.markdown("---")
    st.subheader("🛒 Carrinho")
    st.dataframe(pd.DataFrame(st.session_state.carrinho), use_container_width=True, hide_index=True)
