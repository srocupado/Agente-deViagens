# Agente de Viagens — BSB → Japão

Agente automático que busca as passagens aéreas mais baratas de Brasília (BSB) para o Japão e envia um relatório via **WhatsApp** 2x ao dia usando GitHub Actions.

- **Rota**: BSB → TYO / OSA / NGO / FUK / SPK (qualquer aeroporto japonês)
- **Período**: Setembro a Dezembro de 2026
- **Duração**: 21 a 30 dias (ida e volta, 2 adultos)
- **Horários**: 06h e 18h (horário de Brasília)
- **APIs**: [Amadeus](https://developers.amadeus.com) + [Claude (Anthropic)](https://console.anthropic.com) + [Twilio WhatsApp](https://twilio.com)

---

## Configuração

### 1. Amadeus API (sandbox gratuito)

1. Criar conta em [developers.amadeus.com](https://developers.amadeus.com)
2. Criar nova aplicação → copiar **Client ID** e **Client Secret**
3. O sandbox é gratuito e não exige cartão de crédito

### 2. Anthropic API

1. Criar conta em [console.anthropic.com](https://console.anthropic.com)
2. Gerar uma **API Key** em *API Keys*

### 3. Twilio WhatsApp (sandbox gratuito)

1. Criar conta gratuita em [twilio.com](https://twilio.com)
2. Acessar o Sandbox em: *Console → Messaging → Try it out → Send a WhatsApp message*
3. Enviar o código de opt-in (ex: `join <palavra>`) para o número do Twilio via WhatsApp — **feito uma única vez por destinatário**
4. Copiar **Account SID** e **Auth Token** do painel principal

### 4. GitHub Secrets

Adicionar em *Settings → Secrets and variables → Actions → New repository secret*:

| Secret | Valor |
|---|---|
| `ANTHROPIC_API_KEY` | `sk-ant-...` |
| `AMADEUS_CLIENT_ID` | Obtido no painel Amadeus |
| `AMADEUS_CLIENT_SECRET` | Obtido no painel Amadeus |
| `TWILIO_ACCOUNT_SID` | `ACxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx` |
| `TWILIO_AUTH_TOKEN` | Token do painel Twilio |
| `TWILIO_WHATSAPP_FROM` | `whatsapp:+14155238886` (número do sandbox) |
| `WHATSAPP_TO` | `whatsapp:+5561XXXXXXXXX` (seu número com DDD) |

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
├── .github/workflows/flight_search.yml  # Workflow GitHub Actions
├── src/
│   ├── config.py           # Constantes e variáveis de ambiente
│   ├── amadeus_client.py   # Cliente Amadeus (OAuth2 + busca)
│   ├── tools.py            # Tools para o Claude (search_cheapest_dates, search_flight_offers)
│   ├── agent.py            # Loop agentico com Claude (Anthropic SDK)
│   └── whatsapp_sender.py  # Envio via Twilio WhatsApp
├── main.py                 # Entry point
├── requirements.txt
└── .env.example
```
