# DGTAX Q&A Backend (POC)

## Visão Geral
Plataforma backend em FastAPI responsável por receber perguntas sobre empresas e incentivos fiscais, gerar consultas dinâmicas com suporte de IA (Ollama) e retornar respostas modeladas.

Fluxo principal:
1. Recebe a pergunta via endpoint `/perguntas`.
2. Envia a pergunta para o Ollama gerar uma consulta SQL segura.
3. Executa a consulta no PostgreSQL (somente leitura, com limitações de segurança).
4. Retorna as linhas ao Ollama para modelagem da resposta textual.
5. Entrega a resposta final ao consumidor da API.

## Requisitos
- Python 3.11+
- Acesso ao servidor Ollama (`http://caitanserver:5010`)
- Banco PostgreSQL com as tabelas fornecidas (`dgtax`)

## Setup rápido
```powershell
cd D:\Projetos\DGTAX\backend
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
copy .env.example .env  # ajuste as variáveis conforme necessário
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

## Variáveis de ambiente
| Variável | Descrição |
| --- | --- |
| `OLLAMA_BASE_URL` | URL base do servidor Ollama |
| `OLLAMA_MODEL` | Modelo padrão a ser utilizado (ex: `llama3`) |
| `OLLAMA_TIMEOUT_SECONDS` | Timeout em segundos para chamadas ao Ollama |
| `POSTGRES_HOST` | Host do banco PostgreSQL |
| `POSTGRES_PORT` | Porta do banco |
| `POSTGRES_DATABASE` | Nome da base |
| `POSTGRES_USER` | Usuário de conexão |
| `POSTGRES_PASSWORD` | Senha de conexão |
| `POSTGRES_MIN_POOL_SIZE` / `POSTGRES_MAX_POOL_SIZE` | Configuração do pool de conexões |
| `MAX_ROWS` | Limite máximo de linhas retornadas por consulta |

## Estrutura de pastas
```
backend/
├── app/
│   ├── api/
│   ├── llm/
│   ├── pipelines/
│   ├── repositories/
│   ├── services/
│   ├── utils/
│   ├── config.py
│   ├── main.py
│   └── schemas.py
├── requirements.txt
├── .env.example
└── README.md
```

## Próximos passos sugeridos
- Implementar cache de perguntas/resultados para reduzir custo de chamadas ao LLM.
- Adicionar logs estruturados e rastreamento de prompts/respostas para auditoria.
- Construir testes automatizados cobrindo o fluxo principal com mocks do Ollama e banco.
- Integrar camada de autenticação/autorização antes de expor o endpoint.

