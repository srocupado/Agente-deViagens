# Agente de Viagens

Agente automático que busca passagens aéreas mais baratas para o destino configurado e envia um relatório por **email** 1x ao dia usando GitHub Actions.

- **Configurável**: origem, destino, duração, janela de meses e classe são lidos de `trip_config.yml` (editável pela web do GitHub).
- **API de voos**: [SerpApi (Google Flights)](https://serpapi.com) — 100 buscas/mês gratuitas.
- **Notificação**: Gmail SMTP (sem custo).
- **Critério**: ranqueamento por preço asc + menor número de escalas (configurável).

---

## Configuração da viagem — `trip_config.yml`

Edite este arquivo na raiz do repositório (pode ser pela interface web do GitHub) e faça commit. O próximo run agendado usará a nova configuração.

```yaml
trip:
  origin: "São Paulo"          # cidade ou IATA único (ex.: "GRU")
  destination: "Japão"         # país OU cidade (lookup interno)
  nights: 25                   # valor fixo único
  window:
    start: "2026-09"           # YYYY-MM
    end:   "2026-11"
  adults: 2

search:
  class: economy               # economy | premium_economy | business | first
  top_offers: 5
  ranking: "price_then_stops"  # ou "price_only"
  max_serpapi_calls: 2
```

### Regras importantes

- **Classe única por execução**: para comparar econômica vs. executiva, edite o campo `class`, faça commit, dispare o workflow novamente.
- **Executiva só fora do Brasil**: se `class` for `business`, `first` ou `premium_economy` E o destino for nacional, a execução falha com erro claro (envia email de erro).
- **Origem/destino**: aceita cidade ("São Paulo", "Tóquio"), país ("Japão", "Portugal") ou código IATA ("GRU", "NRT"). Se a localização não estiver no mapa interno (`src/locations.py`), o erro sugere alternativas próximas — ou use o IATA literal.
- **Janela de meses**: `start` é o primeiro dia do mês informado, `end` é o último dia do mês informado.
- **Quota SerpApi**: 100 chamadas/mês grátis. Com `max_serpapi_calls: 2` e cron 1x/dia o consumo é ~60/mês.

---

## Setup inicial

### 1. SerpApi — 100 buscas/mês gratuitas

1. Criar conta em [serpapi.com/users/sign_up](https://serpapi.com/users/sign_up)
2. Copiar a **API Key** do dashboard

### 2. Anthropic API

1. Criar conta em [console.anthropic.com](https://console.anthropic.com)
2. Gerar uma API Key

### 3. Gmail — App Password

1. Ative a verificação em duas etapas na sua conta Google
2. Acesse: Conta Google → Segurança → Senhas de app
3. Crie uma senha para "Email" → copie os 16 caracteres gerados

### 4. GitHub Secrets

Adicionar em *Settings → Secrets and variables → Actions → New repository secret*:

| Secret | Valor |
|---|---|
| `ANTHROPIC_API_KEY` | Chave da Anthropic |
| `SERPAPI_API_KEY` | Obtido no painel SerpApi |
| `GMAIL_USER` | `seuemail@gmail.com` |
| `GMAIL_APP_PASSWORD` | Senha de app (16 caracteres) |
| `RECIPIENT_EMAIL` | Email que receberá os alertas (aceita múltiplos separados por vírgula) |

---

## Execução local

```bash
cp .env.example .env
# Preencha o .env com suas credenciais

pip install -r requirements.txt
python main.py
```

## Execução automática

O workflow roda automaticamente às **06h (BRT)** todos os dias. Para disparar manualmente:
*GitHub → Actions → Flight Search → Run workflow*.

---

## Estrutura do projeto

```
├── .github/workflows/flight_search.yml  # Workflow GitHub Actions (cron 1x/dia)
├── src/
│   ├── config.py              # Secrets + caminho do trip_config.yml
│   ├── locations.py           # Lookup cidade/país → IATA + is_domestic
│   ├── trip_config.py         # Loader e validação do YAML
│   ├── serpapi_client.py      # Cliente SerpApi (Google Flights)
│   ├── tools.py               # Tool use schema + dispatcher (com counter de quota)
│   ├── agent.py               # System prompt parametrizável + loop do agente
│   └── email_sender.py        # Envio via Gmail SMTP
├── trip_config.yml            # Configuração editável da viagem
├── main.py                    # Entry point
├── requirements.txt
└── .env.example
```
