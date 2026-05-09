# Agente de Viagens — GRU → Japão

Agente automático que busca as passagens aéreas mais baratas de São Paulo (GRU) para o Japão e envia um relatório por **email** 2x ao dia usando GitHub Actions.

- **Rota**: GRU → Tokyo (NRT), Osaka (KIX) e outros aeroportos japoneses
- **Período**: Setembro a Novembro de 2026 (saída), duração de 21 a 30 noites
- **Viajantes**: 2 adultos
- **Horários**: 06h e 18h (horário de Brasília)
- **API de voos**: [SerpApi (Google Flights)](https://serpapi.com) — 100 buscas/mês gratuitas
- **Notificação**: Gmail SMTP (sem custo)

> **Atenção**: os preços são para embarque em GRU (Guarulhos). Quem parte de Brasília (BSB) precisa incluir o trecho BSB → GRU separadamente.

---

## Como funciona

A cada execução o script seleciona automaticamente uma janela de datas (rotação entre 10 combinações de destino e datas) e busca os voos mais baratos. Os resultados são ordenados por preço e enviados por email com rota completa, escala e duração.

Exemplo de email recebido:

```
✈️ TOP 5 PASSAGENS GRU → JAPÃO
Período: set–dez 2026 | 2 adultos | 21–30 noites
━━━━━━━━━━━━━━━━━━━━━━━━━

🏆 #1
DESTINO: Tóquio (NRT)
PRECO: R$ 8.450 total · R$ 4.225/pessoa
DATAS: Ida 2026-10-10  Volta 2026-11-04  (25 noites)
IDA:   GRU (São Paulo) → DFW (Dallas) → NRT (Tóquio)  [23h50m]
VOLTA: NRT (Tóquio) → DFW (Dallas) → GRU (São Paulo)  [24h30m]
CIA:   American Airlines
```

---

## Configuração

### 1. SerpApi — 100 buscas/mês gratuitas

1. Criar conta em [serpapi.com/users/sign_up](https://serpapi.com/users/sign_up)
2. Copiar a **API Key** do dashboard

### 2. Gmail — App Password

1. Ative a verificação em duas etapas na sua conta Google
2. Acesse: Conta Google → Segurança → Senhas de app
3. Crie uma senha para "Email" → copie os 16 caracteres gerados

### 3. GitHub Secrets

Adicionar em *Settings → Secrets and variables → Actions → New repository secret*:

| Secret | Valor |
|---|---|
| `SERPAPI_API_KEY` | Obtido no painel SerpApi |
| `GMAIL_USER` | `seuemail@gmail.com` |
| `GMAIL_APP_PASSWORD` | Senha de app (16 caracteres, com ou sem espaços) |
| `RECIPIENT_EMAIL` | Email que receberá os alertas (pode ser o mesmo; aceita múltiplos separados por vírgula) |

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
│   ├── serpapi_client.py   # Cliente SerpApi (Google Flights) com formatação de rotas
│   └── email_sender.py     # Envio via Gmail SMTP
├── main.py                 # Entry point — busca e envia o email
├── requirements.txt
└── .env.example
```
