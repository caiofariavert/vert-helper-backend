# Documentação do Helper para o Frontend

**Data**: Julho 2026  
**Versão**: MVP 1.0  
**Audiência**: Time de Frontend  

Este documento descreve completamente o contrato das APIs locais do Helper, permitindo que o frontend seja desenvolvido de forma independente do backend, com exemplos testáveis.

---

## 1. Glossário de Termos

### 1.1 Entidades principais

#### Ecosystem
Agrupamento lógico de Sistemas (ex: "Infraestrutura de Análise", "Plataforma de Dados").
- Campos: `id`, `slug`, `name`, `is_active`
- Relacionamento: 1:N com System

#### System
Sistema de negócio monitorado (ex: "Data Lake", "Message Broker", "Analytics Platform").
- Campos: `id`, `slug`, `name`, `description`, `is_active`
- Relacionamentos:
  - N:N com Ecosystem
  - 1:N com Application
- Responsável por receber notificações de falha

#### Application
Instância de um sistema em um ambiente específico (ex: "Data Lake STG", "Message Broker PRD").
- Campos: `id`, `slug`, `name`, `base_url`, `environment` (STG/HML/PRD), `auth_type`, `is_active`
- Responsabilidade: origem das APIs monitoradas

#### Service
Componente interno de uma Application (ex: "PostgreSQL", "Redis", "Kafka").
- Campos: `id`, `name`, `status`, `last_checked_at`, `last_status_change_at`, `is_active`
- Estatuses possíveis:
  - `OK` — operacional
  - `FAILED` — indisponível ou com erro
  - `UNKNOWN` — nunca verificado ou sem informação
- Relacionamento: 1:N com Application
- Conciliação: por `name` dentro da Application

#### Action
Procedimento/comando executável em uma Application (ex: "Gerar Relatório", "Executar Backup").
- Campos: `id`, `slug`, `name`, `description`, `questions_schema`, `source_version`, `is_active`
- Relacionamentos:
  - 1:N com Application
  - N:N com Service (ações relacionadas a serviços)
- Versionamento: `source_version` incrementa quando definição muda

#### Incident
Registro de uma falha detectada em um Service.
- Campos: `id`, `service`, `previous_status`, `current_status`, `opened_at`, `recovered_at`, `is_active`
- Objetivo: rastrear mudanças de estado e notificações

### 1.2 Relação entre entidades (exemplo prático)

```
Ecosystem: "Infraestrutura Cloud"
└── System: "Kubernetes"
    ├── Application: "k8s-staging" (STG)
    │   ├── Service: "api-server" (OK)
    │   ├── Service: "etcd" (FAILED) ← Incident aberto
    │   └── Action: "Restart Pod" (linked to api-server)
    └── Application: "k8s-prod" (PRD)
        ├── Service: "api-server" (OK)
        └── Service: "scheduler" (OK)
```

### 1.3 Campo `is_recommended`

Uma Action é recomendada quando **pelo menos um dos Services vinculados está em FAILED**.

```javascript
// Exemplo
if (action.services.some(s => s.status === "FAILED")) {
  action.is_recommended = true; // Mostrar destaque/badge no frontend
}
```

---

## 2. Autenticação (CAS + SimpleJWT)

### 2.1 Fluxo completo

```
[Frontend]                [Backend Helper]              [CAS Server]
    |                            |                           |
    | (1) Login clicado          |                           |
    |------ redirect to /accounts/login ----->              |
    |                            |                           |
    |                    (2) Redireciona para CAS            |
    |                    <------ redirect -----------        |
    |-------------- redirect to CAS ---------->             |
    |                            |                       (3) Autenca
    |<----------- SSO Login ---------- (4) Ticket ---------|
    |                            |                           |
    |                    (5) Valida ticket, cria JWT
    |                    (6) Redireciona com token
    |<---- redirect to FRONTEND_AUTH_REDIRECT/token/refresh --|
    |
    | (7) Guarda token em localStorage
    | (8) Usa token em Authorization header
```

### 2.2 Variáveis de ambiente (informativas)

Backend:
```
CAS_SERVER_URL=https://cas.exemplo.com
FRONTEND_AUTH_REDIRECT=http://localhost:3000/auth
```

Frontend:
```
VITE_CAS_LOGIN_URL=http://localhost:8000/accounts/login
VITE_HELPER_API=http://localhost:8000/api/helper/v1
```

### 2.3 Obter o token

**Durante login (automático)**

O backend redireciona para:
```
http://localhost:3000/auth/<access_token>/<refresh_token>/
```

Frontend extrai dos parâmetros da URL e armazena:
```javascript
// src/auth.js
const params = window.location.pathname.split('/');
const accessToken = params[2];
const refreshToken = params[3];

localStorage.setItem('access_token', accessToken);
localStorage.setItem('refresh_token', refreshToken);
```

### 2.4 Renovar token (quando expirar)

**POST** `/api/token/refresh/`
```json
{
  "refresh": "eyJ0eXAiOiJKV1QiLCJhbGc..."
}
```

Response:
```json
{
  "access": "eyJ0eXAiOiJKV1QiLCJhbGc..."
}
```

### 2.5 Enviar token em requisições

```javascript
// Em todo fetch/axios
const token = localStorage.getItem('access_token');

fetch('http://localhost:8000/api/helper/v1/actions/', {
  headers: {
    'Authorization': `JWT ${token}`,
    'Content-Type': 'application/json'
  }
});

// Ou com axios interceptor
api.interceptors.request.use(config => {
  const token = localStorage.getItem('access_token');
  if (token) {
    config.headers.Authorization = `JWT ${token}`;
  }
  return config;
});
```

### 2.6 Verificar acesso

**GET** `/api/helper/v1/me/`  
Requer: `Authorization: JWT <token>`

Response:
```json
{
  "email": "user@example.com",
  "name": "João Silva",
  "is_superuser": true,
  "is_active": true
}
```

- Se `is_superuser: false` → usuário logado mas **sem acesso** às rotas funcionais (admin deve promover no Django Admin)
- Mostrar mensagem: "Sua conta não tem permissão. Contate o administrador."

---

## 3. Contrato das APIs Locais

### 3.1 Health (sem autenticação)

**GET** `/api/helper/v1/health/`

Autenticação: **Nenhuma**

Response (200):
```json
{
  "status": "ok"
}
```

Response (503 se DB indisponível):
```json
{
  "status": "failed",
  "message": "..."
}
```

---

### 3.2 Listar Ecosystems

**GET** `/api/helper/v1/ecosystems/`

Autenticação: **Requer JWT + is_superuser=true**

Query params:
- `search` — busca por nome (fuzzy)
- `page` — número da página (default: 1)
- `page_size` — itens por página (default: 10)

Response (200):
```json
{
  "count": 5,
  "next": "http://api/ecosystems/?page=2",
  "previous": null,
  "results": [
    {
      "id": "uuid-xxx",
      "slug": "infra-cloud",
      "name": "Infraestrutura Cloud",
      "is_active": true,
      "created_at": "2024-01-15T10:30:00Z"
    }
  ]
}
```

Erros:
- `401` — sem autenticação
- `403` — autenticado mas `is_superuser=false`

---

### 3.3 Detalhes de um Ecosystem

**GET** `/api/helper/v1/ecosystems/<slug>/`

Autenticação: **Requer JWT + is_superuser=true**

Response (200):
```json
{
  "id": "uuid-xxx",
  "slug": "infra-cloud",
  "name": "Infraestrutura Cloud",
  "is_active": true,
  "created_at": "2024-01-15T10:30:00Z"
}
```

---

### 3.4 Listar Systems

**GET** `/api/helper/v1/systems/`

Autenticação: **Requer JWT + is_superuser=true**

Query params:
- `search` — busca por nome
- `ecosystem` — filtrar por ecosystem slug
- `page`, `page_size` — paginação

Response (200):
```json
{
  "count": 2,
  "results": [
    {
      "id": "uuid-yyy",
      "slug": "kubernetes",
      "name": "Kubernetes",
      "description": "Orquestrador de containers",
      "is_active": true,
      "ecosystems": ["infra-cloud"],
      "created_at": "2024-01-20T14:00:00Z"
    }
  ]
}
```

---

### 3.5 Listar Applications

**GET** `/api/helper/v1/applications/`

Autenticação: **Requer JWT + is_superuser=true**

Query params:
- `search` — busca por nome
- `system` — filtrar por system slug
- `ecosystem` — filtrar por ecosystem slug (busca recursiva)
- `environment` — STG / HML / PRD

Response (200):
```json
{
  "count": 3,
  "results": [
    {
      "id": "uuid-app",
      "slug": "k8s-staging",
      "name": "Kubernetes Staging",
      "base_url": "http://k8s-stg.example.com",
      "environment": "STG",
      "auth_type": "JWT",
      "system": "kubernetes",
      "status": "FAILED",
      "is_active": true,
      "created_at": "2024-01-25T09:15:00Z"
    }
  ]
}
```

Regra do campo `status` em Application:
- `FAILED` se **qualquer** Service ativo estiver `FAILED`
- `OK` se **todos** os Services ativos estiverem `OK` (ou se não houver Services)

---

### 3.6 Listar Services

**GET** `/api/helper/v1/services/`

Autenticação: **Requer JWT + is_superuser=true**

Query params:
- `search` — busca por nome do serviço
- `application` — filtrar por application slug
- `system` — filtrar por system slug

Response:
```json
{
  "count": 2,
  "results": [
    {
      "id": "uuid-svc",
      "name": "etcd",
      "status": "FAILED",
      "last_checked_at": "2024-01-30T10:20:00Z",
      "last_status_change_at": "2024-01-30T09:45:00Z",
      "is_active": true
    }
  ]
}
```

---

### 3.7 Listar Actions

**GET** `/api/helper/v1/actions/`

Autenticação: **Requer JWT + is_superuser=true**

Query params:
- `search` — busca por nome
- `service` — filtrar por service name (no seu Application)
- `application` — filtrar por application slug

Response (200):
```json
{
  "count": 5,
  "results": [
    {
      "id": "uuid-act",
      "slug": "generate-report",
      "name": "Gerar Relatório",
      "description": "Gera relatório mensal completo",
      "services": ["postgresql", "kafka"],
      "is_recommended": true,
      "source_version": 2,
      "is_active": true,
      "created_at": "2024-01-10T08:00:00Z"
    }
  ]
}
```

- `is_recommended: true` → pelo menos um serviço vinculado está em FAILED

---

### 3.8 Detalhes de uma Action

**GET** `/api/helper/v1/actions/<slug>/`

Autenticação: **Requer JWT + is_superuser=true**

Response (200):
```json
{
  "id": "uuid-act",
  "slug": "generate-report",
  "name": "Gerar Relatório",
  "description": "Gera relatório mensal completo",
  "services": ["postgresql", "kafka"],
  "is_recommended": true,
  "source_version": 2,
  "is_active": true,
  "questions": [
    {
      "id": "q1",
      "label": "Formato do arquivo",
      "type": "radio",
      "options": ["CSV", "JSON"],
      "is_required": true,
      "parent_question": null,
      "parent_value": null,
      "action_kwarg": "file_format"
    },
    {
      "id": "q2",
      "label": "Período",
      "type": "text",
      "options": null,
      "is_required": true,
      "parent_question": null,
      "parent_value": null,
      "action_kwarg": "period"
    }
  ],
  "created_at": "2024-01-10T08:00:00Z"
}
```

---

### 3.9 Executar uma Action

**POST** `/api/helper/v1/actions/<slug>/execute/`

Autenticação: **Requer JWT + is_superuser=true**

Request:
```json
{
  "questions": {
    "q1": "CSV",
    "q2": "2024-01"
  }
}
```

Response (200 ou 422):
```json
{
  "status": "success",
  "message": "Relatório gerado com sucesso"
}
```

Ou:
```json
{
  "status": "error",
  "message": "Falha ao gerar relatório"
}
```

Ou:
```json
{
  "status": "info",
  "message": "Processamento iniciado",
  "steps": [
    {"name": "Conectar BD", "status": "completed"},
    {"name": "Extrair dados", "status": "in_progress"},
    {"name": "Formatar CSV", "status": "pending"}
  ]
}
```

Códigos de status HTTP:
- `200` — sucesso (`status: success`) ou informativo (`status: info`)
- `400` — erro de validação (ex: pergunta obrigatória faltando)
- `422` — erro na execução remota (`status: error`)
- `401` — sem autenticação
- `403` — sem permissão

---

## 4. Guia do Formulário Dinâmico

### 4.1 Estrutura de `questions_schema`

Cada pergunta é um objeto com:

```typescript
interface Question {
  id: string;                    // identificador único (ex: "q1")
  label: string;                 // texto exibido para o usuário
  type: "radio" | "text";        // tipo de campo
  options?: string[];            // valores possíveis (para radio)
  is_required: boolean;          // obrigatória?
  parent_question?: string|null; // pergunta que controla visibilidade
  parent_value?: string|null;    // valor do parent que ativa esta
  action_kwarg: string;          // nome do argumento no backend
}
```

### 4.2 Renderização condicional

**Regra**: Uma pergunta é exibida se:
1. Ela não tem `parent_question` (root), OU
2. Seu `parent_question` foi respondido com o valor `parent_value`

```javascript
function isQuestionActive(question, answers) {
  if (!question.parent_question) return true; // root question
  const parentAnswer = answers[question.parent_question];
  return parentAnswer === question.parent_value;
}

function getActiveQuestions(schema, answers) {
  return schema.filter(q => isQuestionActive(q, answers));
}
```

### 4.3 Exemplo completo

**Schema**:
```json
[
  {
    "id": "q1",
    "label": "Tipo de dados",
    "type": "radio",
    "options": ["Histórico", "Tempo Real"],
    "is_required": true,
    "parent_question": null,
    "parent_value": null,
    "action_kwarg": "data_type"
  },
  {
    "id": "q2",
    "label": "Período de início",
    "type": "text",
    "options": null,
    "is_required": true,
    "parent_question": "q1",
    "parent_value": "Histórico",
    "action_kwarg": "start_date"
  },
  {
    "id": "q3",
    "label": "Período de fim",
    "type": "text",
    "options": null,
    "is_required": true,
    "parent_question": "q1",
    "parent_value": "Histórico",
    "action_kwarg": "end_date"
  },
  {
    "id": "q4",
    "label": "Intervalo de atualização",
    "type": "radio",
    "options": ["1 minuto", "5 minutos", "1 hora"],
    "is_required": true,
    "parent_question": "q1",
    "parent_value": "Tempo Real",
    "action_kwarg": "refresh_interval"
  }
]
```

**Fluxo do usuário**:

1. Usuário vê Q1 (não tem parent)
   ```
   Tipo de dados: [ Histórico ] [ Tempo Real ]
   ```

2. Seleciona "Histórico" → Q2 e Q3 ativam
   ```
   Tipo de dados: [x Histórico]
   Período de início: [____________________]
   Período de fim:    [____________________]
   ```

3. Seleciona "Tempo Real" → Q2 e Q3 desaparecem, Q4 aparece
   ```
   Tipo de dados: [x Tempo Real]
   Intervalo de atualização: [ 1 minuto ] [ 5 minutos ] [ 1 hora ]
   ```

### 4.4 Validação no frontend (opcional)

```javascript
function validateForm(schema, answers) {
  const errors = {};
  const activeQuestions = schema.filter(q => isQuestionActive(q, answers));

  for (const question of activeQuestions) {
    if (question.is_required && !answers[question.id]) {
      errors[question.id] = `${question.label} é obrigatória`;
    }
    if (question.type === "radio" && question.options) {
      if (answers[question.id] && !question.options.includes(answers[question.id])) {
        errors[question.id] = `Valor inválido para ${question.label}`;
      }
    }
  }

  return { valid: Object.keys(errors).length === 0, errors };
}
```

### 4.5 Montar payload de execute

```javascript
async function executeAction(actionSlug, answers) {
  const token = localStorage.getItem('access_token');

  const response = await fetch(
    `http://localhost:8000/api/helper/v1/actions/${actionSlug}/execute/`,
    {
      method: 'POST',
      headers: {
        'Authorization': `JWT ${token}`,
        'Content-Type': 'application/json'
      },
      body: JSON.stringify({ questions: answers })
    }
  );

  const result = await response.json();

  if (response.status === 400) {
    // Erro de validação no frontend — nunca deveria chegar aqui se validar antes
    console.error('Validation error:', result);
    return;
  }

  if (response.status === 422) {
    // Erro na execução remota
    showError(`Falha: ${result.message}`);
    return;
  }

  if (response.status === 200) {
    handleSuccess(result);
  }
}
```

---

## 5. Interpretação das Respostas

### 5.1 Formato de resposta

Todos os responses de execute têm o campo `status` com um de três valores:

#### Status: `success`
Execução completou com sucesso.
```json
{
  "status": "success",
  "message": "Relatório gerado e enviado para seu email"
}
```

**HTTP**: 200  
**Ação no frontend**: Mostrar confirmação ao usuário, fechar formulário ou redirecionar

#### Status: `error`
Execução falhou.
```json
{
  "status": "error",
  "message": "Falha ao conectar com o banco de dados"
}
```

**HTTP**: 422  
**Ação no frontend**: Mostrar erro em alerta/toast, permitir retry  
**Nota**: O campo `details` (detalhes técnicos) **nunca** é retornado ao frontend — armazenado apenas no backend para auditoria

#### Status: `info`
Execução iniciada com progresso e passos intermediários.
```json
{
  "status": "info",
  "message": "Processamento iniciado com sucesso",
  "steps": [
    {"name": "Validar entrada", "status": "completed"},
    {"name": "Conectar BD", "status": "in_progress"},
    {"name": "Extrair dados", "status": "pending"},
    {"name": "Formatar saída", "status": "pending"}
  ]
}
```

**HTTP**: 200  
**Ação no frontend**: Mostrar barra de progresso ou lista de steps com status

### 5.2 Renderizar steps (quando status=info)

```javascript
function renderSteps(steps) {
  return steps.map(step => {
    const iconMap = {
      'completed': '✓',
      'in_progress': '⏳',
      'pending': '⊘'
    };
    return `${iconMap[step.status]} ${step.name}`;
  }).join('\n');
}

// Output:
// ✓ Validar entrada
// ⏳ Conectar BD
// ⊘ Extrair dados
// ⊘ Formatar saída
```

### 5.3 Tratamento de erros de rede

Se a chamada falhar antes de chegar no backend:

```javascript
try {
  const response = await fetch(...);
  // ...
} catch (error) {
  // Network error, timeout, etc
  showError(`Falha de comunicação: ${error.message}`);
}
```

---

## 6. Exemplo Completo de Implementação (React)

```jsx
import { useState, useEffect } from 'react';

export function ActionExecutor({ action }) {
  const [answers, setAnswers] = useState({});
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState(null);
  const [error, setError] = useState(null);

  const activeQuestions = action.questions.filter(q => {
    if (!q.parent_question) return true;
    return answers[q.parent_question] === q.parent_value;
  });

  async function handleExecute() {
    setLoading(true);
    setError(null);
    setResult(null);

    try {
      const token = localStorage.getItem('access_token');
      const response = await fetch(
        `http://localhost:8000/api/helper/v1/actions/${action.slug}/execute/`,
        {
          method: 'POST',
          headers: {
            'Authorization': `JWT ${token}`,
            'Content-Type': 'application/json'
          },
          body: JSON.stringify({ questions: answers })
        }
      );

      const data = await response.json();

      if (response.status === 422) {
        setError(data.message);
      } else if (response.status === 200) {
        setResult(data);
      }
    } catch (err) {
      setError(`Erro de comunicação: ${err.message}`);
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="action-executor">
      <h2>{action.name}</h2>

      {/* Formulário */}
      <form onSubmit={e => { e.preventDefault(); handleExecute(); }}>
        {activeQuestions.map(q => (
          <div key={q.id} className="question">
            <label>{q.label}</label>
            {q.type === 'radio' ? (
              <div className="radio-group">
                {q.options.map(opt => (
                  <label key={opt}>
                    <input
                      type="radio"
                      name={q.id}
                      value={opt}
                      checked={answers[q.id] === opt}
                      onChange={e => setAnswers({...answers, [q.id]: e.target.value})}
                    />
                    {opt}
                  </label>
                ))}
              </div>
            ) : (
              <input
                type="text"
                value={answers[q.id] || ''}
                onChange={e => setAnswers({...answers, [q.id]: e.target.value})}
                required={q.is_required}
              />
            )}
          </div>
        ))}
        <button type="submit" disabled={loading}>
          {loading ? 'Executando...' : 'Executar'}
        </button>
      </form>

      {/* Resultado */}
      {result && result.status === 'success' && (
        <div className="success">{result.message}</div>
      )}
      {result && result.status === 'info' && (
        <div className="info">
          <p>{result.message}</p>
          <ul>
            {result.steps.map(step => (
              <li key={step.name}>
                {step.status === 'completed' ? '✓' : '⏳'} {step.name}
              </li>
            ))}
          </ul>
        </div>
      )}
      {error && <div className="error">{error}</div>}
    </div>
  );
}
```

---

## 7. Checklist Pré-Desenvolvimento

- [ ] **Autenticação**: Frontend consegue fazer login via CAS e obter JWT
- [ ] **Endpoints de read**: Frontend consegue listar Ecosystems, Systems, Applications, Actions
- [ ] **Detalhes**: Frontend consegue carregar questions_schema completo de uma Action
- [ ] **Formulário dinâmico**: Perguntas condicionais renderizam corretamente
- [ ] **Execute**: Frontend consegue disparar uma Action com payload correto
- [ ] **Tratamento de erros**: Validação de campo faltando retorna 400; falha remota retorna 422
- [ ] **Segurança**: Token é enviado em todos os requests funcionais; sem token = 401
- [ ] **Permissão**: Usuário sem is_superuser não acessa rotas funcionais (403)
- [ ] **Testes**: Todos os exemplos deste documento foram testados contra API real em STG

---

**Última atualização**: Julho 2026  
**Suporte**: Time de Backend Helper
