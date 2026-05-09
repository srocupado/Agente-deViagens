# Agente de Viagens — BSB → Japão

Agente automático que busca as passagens aéreas mais baratas de Brasília (BSB) para o Japão e envia um relatório via **WhatsApp** 2x ao dia usando GitHub Actions.

- **Rota**: BSB → qualquer aeroporto do Japão (NRT, HND, KIX, NGO, FUK, CTS, OKA…)
- **Período**: Setembro a Dezembro de 2026
- **Duração**: 21 a 30 noites (ida e volta, 2 adultos)
- **Horários**: 06h e 18h (horário de Brasília)
- **APIs**: [Tequila by Kiwi.com](https://tequila.kiwi.com) + [Claude (Anthropic)](https://console.anthropic.com) + [Twilio WhatsApp](https://twilio.com)

---

## Configuração

### 1. Tequila API (Kiwi.com) — gratuito para uso pessoal

1. Criar conta em [tequila.kiwi.com](https://tequila.kiwi.com)
2. Após o cadastro, copiar a **API Key** disponível no painel
3. A API é gratuita para projetos pessoais — não exige cartão de crédito

> **Por que Tequila e não Amadeus?**
> O portal Amadeus Self-Service foi descontinuado em 2026 (encerramento total em julho/2026).
> A Tequila cobre os mesmos aeroportos e permite buscar toda a janela de datas em uma única chamada.

### 2. Anthropic API

1. Criar conta em [console.anthropic.com](https://console.anthropic.com)
2. Gerar uma **API Key** em *API Keys*

### 3. Twilio WhatsApp (sandbox gratuito)

1. Criar conta gratuita em [twilio.com](https://twilio.com)
2. Acessar o Sandbox: *Console → Messaging → Try it out → Send a WhatsApp message*
3. Enviar o código de opt-in (ex: `join <palavra>`) para o número do Twilio via WhatsApp — **feito uma única vez por destinatário**
4. Copiar **Account SID** e **Auth Token** do painel principal

### 4. GitHub Secrets

Adicionar em *Settings → Secrets and variables → Actions → New repository secret*:

| Secret | Valor |
|---|---|
| `ANTHROPIC_API_KEY` | `sk-ant-...` |
| `TEQUILA_API_KEY` | Obtido no painel Tequila |
| `TWILIO_ACCOUNT_SID` | `ACxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx` |
| `TWILIO_AUTH_TOKEN` | Token do painel Twilio |
| `TWILIO_WHATSAPP_FROM` | `whatsapp:+14155238886` (número do sandbox) |
| `WHATSAPP_TO` | `whatsapp:+5561XXXXXXXXX` (seu número com DDI+DDD) |

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
│   ├── tequila_client.py   # Cliente Tequila/Kiwi.com (busca de voos)
│   ├── tools.py            # Tool search_flights para o Claude
│   ├── agent.py            # Loop agentico com Claude (Anthropic SDK)
│   └── whatsapp_sender.py  # Envio via Twilio WhatsApp
├── main.py                 # Entry point
├── requirements.txt
└── .env.example
```
