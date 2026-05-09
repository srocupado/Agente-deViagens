# Agente de Viagens — BSB → Japão

Agente automático que busca as passagens aéreas mais baratas de Brasília (BSB) para o Japão e envia um relatório por **email** 2x ao dia usando GitHub Actions.

- **Rota**: BSB → qualquer aeroporto do Japão (NRT/HND, KIX, NGO, FUK…)
- **Período**: Setembro a Dezembro de 2026
- **Duração**: 21 a 30 noites (ida e volta, 2 adultos)
- **Horários**: 06h e 18h (horário de Brasília)
- **APIs**: [SerpApi (Google Flights)](https://serpapi.com) + [Claude (Anthropic)](https://console.anthropic.com) + Gmail SMTP

---

## Configuração

### 1. SerpApi — 100 searches/mês gratuitos

1. Criar conta em [serpapi.com/users/sign_up](https://serpapi.com/users/sign_up)
2. Copiar a **API Key** do dashboard

### 2. Anthropic API

1. Criar conta em [console.anthropic.com](https://console.anthropic.com)
2. Gerar uma **API Key** em *API Keys*

### 3. Gmail — App Password

1. Ative a verificação em duas etapas na sua conta Google
2. Acesse: Conta Google → Segurança → Senhas de app
3. Crie uma senha de app para "Email" → copie os 16 caracteres gerados

### 4. GitHub Secrets

Adicionar em *Settings → Secrets and variables → Actions → New repository secret*:

| Secret | Valor |
|---|---|
| `ANTHROPIC_API_KEY` | `sk-ant-...` |
| `SERPAPI_API_KEY` | Obtido no painel SerpApi |
| `GMAIL_USER` | `seuemail@gmail.com` |
| `GMAIL_APP_PASSWORD` | Senha de app (16 caracteres, com ou sem espaços) |
| `RECIPIENT_EMAIL` | Email que receberá os alertas (pode ser o mesmo) |

---

## Execução local

```bash
cp .env.example .env
# Preencha o .env com suas credenciais
pip install -r requirements.txt
python main.py
```

## Execução automática

O workflow roda automaticamente às **06h e 18h (BRT)**.

Para disparar manualmente: *GitHub → Actions → Japan Flight Search → Run workflow*

---

## Estrutura do projeto

```
├── .github/workflows/flight_search.yml  # Workflow GitHub Actions (cron 2x/dia)
├── src/
│   ├── config.py           # Constantes e variáveis de ambiente
│   ├── serpapi_client.py   # Cliente SerpApi (Google Flights)
│   ├── tools.py            # Tool search_flights para o Claude
│   ├── agent.py            # Loop agentico com Claude (Anthropic SDK)
│   └── email_sender.py     # Envio via Gmail SMTP
├── main.py                 # Entry point
├── requirements.txt
└── .env.example
```
