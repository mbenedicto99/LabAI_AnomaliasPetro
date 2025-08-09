
# Stack MQTT → InfluxDB → Grafana (com Bridge Python)

Este pacote levanta um ambiente completo para consumir mensagens MQTT do seu notebook,
escrever no InfluxDB e visualizar no Grafana.

## Conteúdo
- `docker-compose.yml`: Mosquitto, InfluxDB 2.x, Grafana e o **mqtt-influx-bridge** (Python).
- `bridge/mqtt_to_influx.py`: assina o tópico MQTT e grava pontos no InfluxDB.
- `grafana/provisioning/*`: configura automaticamente a fonte de dados (InfluxDB) e carrega um dashboard inicial.

## Subir o stack
```bash
cd iot_stack
docker compose up -d
# Primeira vez pode demorar ~ alguns segundos até o Influx inicializar
```

Acesse:
- InfluxDB: http://localhost:8086 (org=`lab`, bucket=`signals`, token=`dev-token`)
- Grafana:   http://localhost:3000  (user=`admin`, pass=`admin`)

## Conectar o notebook
No seu notebook de detecção, ajuste para publicar em:
- `MQTT_BROKER="localhost"` (ou `mosquitto` se estiver dentro do mesmo compose)
- `MQTT_PORT=1883`
- `MQTT_TOPIC="plataforma/anomalia"`

Cada janela publicada como JSON será ingerida pelo bridge e escrita no measurement `anomalias`
com os campos: `f1_obs`, `f1_pred`, `score`, `threshold`, `alert`, `damaged`, `t_mid`.

## Dashboard
O dashboard **"Offshore Anomalias (MQTT→InfluxDB)"** é provisionado automaticamente com:
- Série temporal de `f1_obs` e `f1_pred` (comparação).
- Série temporal de `score` e `threshold`.
- Linha do tempo de `alert` (0/1).

Se quiser mudar o intervalo padrão (1h) nos painéis, edite as queries Flux nos painéis.

## Notas e Pitfalls
- Em produção, gere e use um **token** seguro no InfluxDB (o compose provisiona `dev-token` para demo).
- Latência: o bridge usa `write_api` síncrono; para alto throughput, troque para `WriteOptions` assíncrono.
- Sincronização de tempo: o payload traz `timestamp` relativo (meio da janela). O bridge grava `time` com relógio de parede (agora). Se quiser usar o `timestamp` como tempo da medição, converta para uma `datetime` com base no relógio do produtor (requer sincronização).

