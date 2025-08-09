# LabAI_AnomaliasPetro
Validar detecção de anomalias em colunas de plataformas offshore near-realtime

Objetivo do lab (o que provar)
1. Detectar desvios estruturais sutis (ex.: queda de frequência natural, aumento de amortecimento, mudança de rigidez) em tempo quase real;
2. O modelo aprende continuamente via SGD online;
3. Alertas e gráficos aparecem num dashboard simples (Grafana opcional).

Sinais e “verdades” (mínimo viável)
Sensores simulados (para começar):

Acelerômetro vertical (Hz: 100–500) → extrair modos/frequência natural.
Strain gauge (Hz: 10–50) → deformação lenta e tendência térmica.
Temperatura/vento/onda (Hz: 1–10) → covariáveis.
Rótulos (para teste controlado): injete eventos:
“microfissura” (queda de 1–3% na f₁),
impacto/choque (transiente RMS alto),
sensor drift (lento, não-físico),
ruído de mar grosso (falso positivo clássico).

--- Por que simular?
--- Porque te permite controlar a física (rigidez, massa, amortecimento) e separar o que é dano do que é mar/vento. Depois você pluga sensores reais mantendo a mesma arquitetura.

Arquitetura do experimento
Ingestão: Python gerando streams (ou MQTT/Kafka, se quiser real time de verdade).

Feature em janelas deslizantes (1–10 s):
acel: RMS, kurtosis, picos; f₁ estimada por Welch/peak picking; banda de energia por FFT;
strain: média, derivada, z-score; detrend térmico por regressão linear.

Modelos com SGD (treino online):
Regressão linear multivariada (baseline físico): prediz f₁ a partir de mar/vento/T; anomalia = |f₁_obs − f₁_pred|. Otimizador: SGD(lr=η).
Autoencoder raso (PyTorch/Keras) com 1–2 camadas (tanh/ReLU), perda MSE, atualização a cada janela com SGD → score = erro de reconstrução.
Classificador raso (opcional): logística binária com SGD para “anomalia/ok” usando features acima (útil quando começar a rotular eventos simulados).
Fusão de scores: média ponderada ou EWMA para suavizar; threshold adaptativo por quantil móvel (ex.: 99º quantil do score nas últimas N janelas).

Visualização/alerta:
simples: Matplotlib em notebook + prints de alerta,
completo: InfluxDB/TimescaleDB + Grafana (panels: f₁, score, threshold, eventos).

Repo/Notebook com 3 células grandes:
Simulador: SDOF/2DOF com m, c, k. Injete dano: k := k*(1−δ) por δ∈[0.01,0.03]. Gere acel/strain + ruídos.
Pipeline: janelas → FFT/Welch → features → modelos (SGD update por janela).
Monitoração: curva de f₁, curva de score, alerta quando score > thr.

Hiperparâmetros iniciais:
janela FFT: 4 s, overlap 50%;
lr (SGD): 1e-3 a 1e-2 (decay leve);
autoencoder: latente 8–16; batch=1 (online);
quantil adaptativo: 0.99 com histórico de 30–60 min.

Testes:
ruído ↑ sem dano → false positives devem ser baixos;
dano δ=1% → TPR aceitável (<5 min para ultrapassar thr);

sensor drift → baseline físico (modelo 1) deve filtrar melhor que AE puro.
