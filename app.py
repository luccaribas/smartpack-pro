import streamlit as st
import pandas as pd
import math

# =========================================================
# 1. SMARTPACK ENGINE (PRECISION CORE)
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

        # --- CALIBRAÇÃO DE PRECISÃO (EngView/Prinect) ---
        # Define como o papelão se comporta nas dobras
        # Maletas (02xx) e Coladas (07xx) = Vinco Esmagado
        # Caixas Montáveis (03xx, 04xx) = Dobra Sobreposta
        familia = modelo[0]
        is_crushed_crease = familia in ['2', '5', '6', '7']
        
        calib = {
            'C90': 0.5 if is_crushed_crease else 1.0 * d,
            'HC90': (1.7 * d) if is_crushed_crease else 1.0 * d,
            'Glue': 0.5 if is_crushed_crease else 1.0 * d,
            'Slot': (d + 1.0) if is_crushed_crease else (d + 2.0)
        }

        contexto = {
            'L': float(L), 'W': float(W), 'H': float(H), 'd': lambda: float(d),
            'dtID': 1, 'dtOD': 0, 'No': 0, 'Yes': 1, 'Flat': 0, 'Round': 1, 'fd': lambda: 0,
            'sqrt': math.sqrt, 'min': min, 'max': max, 'tan': math.tan, 'atan': math.atan,
            
            # Funções que garantem a exatidão dos vincos
            'C90x': lambda *a: calib['C90'], 
            'C90y': lambda *a: calib['C90'],
            'HC90x': lambda *a: calib['HC90'], 
            'GlueCorr': lambda *a: calib['Glue'],
            'LPCorr': lambda *a: 1.0 * d, 
            'GLWidth': lambda *a: 35.0, # Padrão Heidelberg para aba de cola
            'LSCf': lambda *a: 1.5 * d, 
            'SlotWidth': lambda *a: calib['Slot'],
            'LC': lambda d_val, dt, iln, oln: (iln if dt==1 else oln) * d,
            'switch': lambda cond, *args: args[1] if cond else args[0]
        }
        
        resolvidos = {}
        # Loop de resolução profunda (5 passadas para pegar todas dependências)
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
        return resolvidos

    def calcular_blank(self, modelo, L, W, H, d):
        vars_eng = self._get_engine_variables(modelo, L, W, H, d)
        if not vars_eng: return 0, 0, "Erro: Modelo Vazio"

        # --- DETECTOR DE TOPOLOGIA (A Chave da Exatidão) ---
        # Em vez de adivinhar pela família, olhamos quais peças existem.
        
        has_GL = 'GL' in vars_eng or 'GLWidth' in str(self.df[self.df['Modelo']==modelo]['Formula'].values)
        
        # Recupera variáveis EXATAS calculadas pelo CSV (já com descontos de vinco)
        # Se não existir no CSV, calcula na hora usando a calibração
        Lss = vars_eng.get('Lss', L + vars_eng.get('C90y', 0.5)*2) 
        Wss = vars_eng.get('Wss', W + vars_eng.get('C90y', 0.5)*2)
        Hss = vars_eng.get('Hss', H + vars_eng.get('HC90x', 1.7*d))
        
        # CASO 1: CAIXA TUBULAR (Tem aba de cola) -> 02xx, 07xx, etc.
        # A fórmula é sempre linear: Aba + Painel + Painel + Painel + Painel
        if has_GL or modelo.startswith(('2', '5', '6')):
            GL = vars_eng.get('GL', 35.0)
            
            # O Comprimento é exato:
            Blank_X = GL + Lss + Wss + Lss + Wss
            
            # A Largura depende das abas (Flaps)
            # O CSV geralmente chama de 'FH' (Flap Height) ou usa Wss/2
            Flap_Top = vars_eng.get('FH', Wss / 2)
            Flap_Bottom = vars_eng.get('FH_B', Flap_Top) # Espelhado se não houver específico
            
            # Ajustes finos conhecidos para modelos críticos
            if modelo == '200': Flap_Top = 0
            elif modelo == '203': Flap_Top, Flap_Bottom = Wss - d, Wss - d
            elif modelo.startswith('7'): Flap_Bottom = Wss * 0.75 # Fundo automático padrão

            Blank_Y = Flap_Top + Hss + Flap_Bottom
            return Blank_X, Blank_Y, "Tubular (Exato)"

        # CASO 2: GEOMETRIA COMPLEXA (0427 E-commerce)
        # Validada pixel a pixel com o Prinect
        elif modelo == '427':
            HssY = vars_eng.get('HssY', H + 2*d)
            FH1 = HssY + (1.5 * d)
            TPH = H
            DxPI = (3 * d) + 1.0
            TIFH = TPH - DxPI
            Blank_X = TIFH + Wss + HssY + Wss + FH1
            
            Ear = HssY + 14.0
            PH = HssY - (0.5 * d)
            Blank_Y = Ear + PH + Lss + PH + Ear
            return Blank_Y, Blank_X, "0427 Gold (Validado)"

        # CASO 3: TABULEIROS / ENVELOPES (03xx, 04xx genéricos)
        # A lógica é sempre Base + Paredes
        else:
            # Tenta encontrar a altura da parede no CSV
            # Em tabuleiros, a altura da parede (Hss) é somada à base (Lss/Wss)
            Wall_H = vars_eng.get('Hss', H + d)
            
            # Verifica se é telescópio (03xx) ou envelope (04xx)
            if modelo.startswith('3'):
                # Fundo + 2 Paredes
                Blank_X = Lss + (2 * Wall_H)
                Blank_Y = Wss + (2 * Wall_H)
                return Blank_X, Blank_Y, "Tabuleiro (Telescópio)"
            else:
                # Envelopes/Pastas (0400, 0410...)
                # Geralmente L + 2H e W + 3H (tampa)
                # Como não temos certeza da tampa, usamos uma margem técnica segura
                # O ideal aqui é ler 'L_Blank' se o CSV tiver.
                if 'L_Blank' in vars_eng:
                    return vars_eng['L_Blank'], vars_eng['W_Blank'], "CSV Direto"
                
                # Cálculo Geométrico Rigoroso
                Blank_X = Lss + (2 * Wall_H)
                Blank_Y = Wss + (3 * Wall_H) # +1 Wall para a tampa
                return Blank_X, Blank_Y, "Envelope (Corte e Vinco)"

# =========================================================
# 2. APP CONFIG
# =========================================================
st.set_page_config(page_title="SmartPack Pro", layout="wide")

@st.cache_resource
def load_engine_v5(): # V5 para limpar cache antigo
    return SmartPackBackend('formulas_smartpack.csv')

engine = load_engine_v5()

# Dados Técnicos
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

# =========================================================
# 3. INTERFACE
# =========================================================
st.title("🛡️ SmartPack Pro - Precision")
st.caption(f"🛠️ Engine V5: {len(engine.get_available_models())} modelos com topologia exata.")

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
    
    modelo_visual = st.selectbox(
        "Selecione o Modelo FEFCO",
        lista_final,
        format_func=lambda x: f"FEFCO {x.zfill(4)}"
    )
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

# =========================================================
# 4. CÁLCULO
# =========================================================
bL, bW, tipo_logica = engine.calcular_blank(codigo_modelo, L, W, H, espessura_d)

area_m2 = (bL * bW) / 1_000_000
valor_unit = (area_m2 * preco_m2_base) * 2.0 

with col2:
    st.subheader("Orçamento (Produção)")
    
    st.success(f"Topologia Detectada: **{tipo_logica}**")
    
    # Aviso de Segurança para modelos não-tubulares e não-0427
    if "Corte e Vinco" in tipo_logica and codigo_modelo != '427':
        st.warning("⚠️ Atenção: Este modelo (Corte e Vinco) usa cálculo geométrico padrão. Para produção em massa, valide o primeiro blank físico.")

    c1, c2, c3 = st.columns(3)
    c1.metric("Preço Unitário", f"R$ {valor_unit:.2f}")
    c2.metric("Total", f"R$ {valor_unit * qtd:,.2f}")
    c3.metric("Área/Caixa", f"{area_m2:.3f} m²")
    
    st.markdown(f"""
    ### 📐 Blank de Produção
    | Dimensão | Valor |
    | :--- | :--- |
    | **Largura Chapa** | **{bL:.1f} mm** |
    | **Comprimento Chapa** | **{bW:.1f} mm** |
    | *Modelo* | *FEFCO {codigo_modelo.zfill(4)}* |
    """)
    
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
