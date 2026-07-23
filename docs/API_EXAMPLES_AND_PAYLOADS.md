# Exemplos de Payloads e Respostas — Helper API

**Data**: Julho 2026  
**Objetivo**: Facilitar testes manuais em ferramentas como Postman, Insomnia ou curl

---

## Setup Inicial

### Ambiente

```
Backend: http://localhost:8000
API Base: http://localhost:8000/api/helper/v1
Auth: JWT (SimpleJWT)
```

### Obter Token (via dev endpoint)

**POST** `http://localhost:8000/auth/user/login/`

```json
{
  "username": "admin",
  "password": "admin"
}
```

Response (200):
```json
{
  "refresh": "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9...",
  "access": "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9...",
  "user": {
    "email": "admin@example.com",
    "name": "Admin User",
    "is_superuser": true,
    "is_active": true
  }
}
```

**Usar `access` token em todos os próximos requests no header**:
```
Authorization: JWT <access_token>
```

---

## 1. Health Check (sem autenticação)

### Request

```bash
curl -X GET "http://localhost:8000/api/helper/v1/health/"
```

### Response (200)

```json
{
  "status": "ok"
}
```

---

## 2. Verificar Acesso (WhoAmI)

### Request

```bash
curl -X GET "http://localhost:8000/api/helper/v1/me/" \
  -H "Authorization: JWT eyJ0eXAiOiJKV1QiLCJhbGc..."
```

### Response (200)

```json
{
  "email": "admin@example.com",
  "name": "Admin User",
  "is_superuser": true,
  "is_active": true
}
```

---

## 3. Listar Ecosystems

### Request

```bash
curl -X GET "http://localhost:8000/api/helper/v1/ecosystems/?search=cloud&page=1" \
  -H "Authorization: JWT eyJ0eXAiOiJKV1QiLCJhbGc..."
```

### Response (200)

```json
{
  "count": 1,
  "next": null,
  "previous": null,
  "results": [
    {
      "id": "550e8400-e29b-41d4-a716-446655440000",
      "slug": "infra-cloud",
      "name": "Infraestrutura Cloud",
      "is_active": true,
      "created_at": "2024-01-15T10:30:00Z",
      "updated_at": "2024-01-15T10:30:00Z"
    }
  ]
}
```

---

## 4. Detalhes de um Ecosystem

### Request

```bash
curl -X GET "http://localhost:8000/api/helper/v1/ecosystems/infra-cloud/" \
  -H "Authorization: JWT eyJ0eXAiOiJKV1QiLCJhbGc..."
```

### Response (200)

```json
{
  "id": "550e8400-e29b-41d4-a716-446655440000",
  "slug": "infra-cloud",
  "name": "Infraestrutura Cloud",
  "is_active": true,
  "created_at": "2024-01-15T10:30:00Z",
  "updated_at": "2024-01-15T10:30:00Z"
}
```

---

## 5. Listar Systems

### Request com filtro

```bash
curl -X GET "http://localhost:8000/api/helper/v1/systems/?ecosystem=infra-cloud" \
  -H "Authorization: JWT eyJ0eXAiOiJKV1QiLCJhbGc..."
```

### Response (200)

```json
{
  "count": 2,
  "results": [
    {
      "id": "660e8400-e29b-41d4-a716-446655440001",
      "slug": "kubernetes",
      "name": "Kubernetes",
      "description": "Orquestrador de containers para aplicações",
      "is_active": true,
      "ecosystems": [
        "infra-cloud"
      ],
      "created_at": "2024-01-20T14:00:00Z",
      "updated_at": "2024-01-20T14:00:00Z"
    },
    {
      "id": "660e8400-e29b-41d4-a716-446655440002",
      "slug": "redis-cache",
      "name": "Redis Cache",
      "description": "Cache distribuído em memória",
      "is_active": true,
      "ecosystems": [
        "infra-cloud"
      ],
      "created_at": "2024-01-22T09:15:00Z",
      "updated_at": "2024-01-22T09:15:00Z"
    }
  ]
}
```

---

## 6. Listar Applications

### Request com múltiplos filtros

```bash
curl -X GET "http://localhost:8000/api/helper/v1/applications/?system=kubernetes&environment=STG" \
  -H "Authorization: JWT eyJ0eXAiOiJKV1QiLCJhbGc..."
```

### Response (200)

```json
{
  "count": 1,
  "results": [
    {
      "id": "770e8400-e29b-41d4-a716-446655440010",
      "slug": "k8s-staging",
      "name": "Kubernetes Staging",
      "base_url": "http://k8s-stg.example.com",
      "environment": "STG",
      "auth_type": "JWT",
      "system": "kubernetes",
      "status": "FAILED",
      "is_active": true,
      "created_at": "2024-01-25T09:15:00Z",
      "updated_at": "2024-01-25T09:15:00Z"
    }
  ]
}
```

Regra do campo `status` em Application:
- `FAILED` se qualquer Service ativo estiver `FAILED`
- `OK` se nenhum Service ativo estiver `FAILED`

### auth_type possíveis

- `NONE` — sem autenticação
- `BEARER` — token Bearer genérico
- `JWT` — token JWT

---

## 7. Listar Services

### Request com filtro por application

```bash
curl -X GET "http://localhost:8000/api/helper/v1/services/?application=k8s-staging" \
  -H "Authorization: JWT eyJ0eXAiOiJKV1QiLCJhbGc..."
```

### Request com filtro por system

```bash
curl -X GET "http://localhost:8000/api/helper/v1/services/?system=kubernetes" \
  -H "Authorization: JWT eyJ0eXAiOiJKV1QiLCJhbGc..."
```

### Response (200)

```json
{
  "count": 3,
  "results": [
    {
      "id": "880e8400-e29b-41d4-a716-446655440020",
      "name": "api-server",
      "status": "OK",
      "last_checked_at": "2024-01-30T10:20:00Z",
      "last_status_change_at": "2024-01-30T08:00:00Z",
      "is_active": true
    },
    {
      "id": "880e8400-e29b-41d4-a716-446655440021",
      "name": "etcd",
      "status": "FAILED",
      "last_checked_at": "2024-01-30T10:20:00Z",
      "last_status_change_at": "2024-01-30T09:45:00Z",
      "is_active": true
    },
    {
      "id": "880e8400-e29b-41d4-a716-446655440022",
      "name": "scheduler",
      "status": "OK",
      "last_checked_at": "2024-01-30T10:15:00Z",
      "last_status_change_at": "2024-01-29T12:30:00Z",
      "is_active": true
    }
  ]
}
```

### Status possíveis

- `OK` — componente operacional
- `FAILED` — componente indisponível ou com erro
- `UNKNOWN` — nunca foi verificado

---

## 8. Listar Actions

### Request com filtro por application

```bash
curl -X GET "http://localhost:8000/api/helper/v1/actions/?application=k8s-staging" \
  -H "Authorization: JWT eyJ0eXAiOiJKV1QiLCJhbGc..."
```

### Response (200)

```json
{
  "count": 3,
  "results": [
    {
      "id": "990e8400-e29b-41d4-a716-446655440030",
      "slug": "restart-pod",
      "name": "Restart Pod",
      "description": "Reinicia um pod específico no cluster",
      "services": ["api-server"],
      "is_recommended": false,
      "source_version": 1,
      "is_active": true,
      "created_at": "2024-01-10T08:00:00Z",
      "updated_at": "2024-01-10T08:00:00Z"
    },
    {
      "id": "990e8400-e29b-41d4-a716-446655440031",
      "slug": "repair-etcd",
      "name": "Reparar etcd",
      "description": "Executa procedimento de recuperação do etcd",
      "services": ["etcd"],
      "is_recommended": true,
      "source_version": 2,
      "is_active": true,
      "created_at": "2024-01-15T10:30:00Z",
      "updated_at": "2024-01-28T15:45:00Z"
    },
    {
      "id": "990e8400-e29b-41d4-a716-446655440032",
      "slug": "generate-report",
      "name": "Gerar Relatório",
      "description": "Gera relatório de saúde do cluster",
      "services": ["api-server", "etcd", "scheduler"],
      "is_recommended": true,
      "source_version": 1,
      "is_active": true,
      "created_at": "2024-01-20T14:00:00Z",
      "updated_at": "2024-01-20T14:00:00Z"
    }
  ]
}
```

**Nota**: `is_recommended: true` significa que pelo menos um dos `services` listados tem `status: FAILED`.

---

## 9. Detalhes de uma Action (com questions_schema)

### Request

```bash
curl -X GET "http://localhost:8000/api/helper/v1/actions/generate-report/" \
  -H "Authorization: JWT eyJ0eXAiOiJKV1QiLCJhbGc..."
```

### Response (200)

```json
{
  "id": "990e8400-e29b-41d4-a716-446655440032",
  "slug": "generate-report",
  "name": "Gerar Relatório",
  "description": "Gera relatório de saúde do cluster",
  "services": ["api-server", "etcd", "scheduler"],
  "is_recommended": true,
  "source_version": 1,
  "is_active": true,
  "questions": [
    {
      "id": "q1",
      "label": "Formato do arquivo",
      "type": "radio",
      "options": ["CSV", "JSON", "PDF"],
      "is_required": true,
      "parent_question": null,
      "parent_value": null,
      "action_kwarg": "file_format"
    },
    {
      "id": "q2",
      "label": "Período de análise",
      "type": "text",
      "options": null,
      "is_required": true,
      "parent_question": null,
      "parent_value": null,
      "action_kwarg": "period"
    },
    {
      "id": "q3",
      "label": "Nível de detalhe",
      "type": "radio",
      "options": ["Básico", "Completo"],
      "is_required": true,
      "parent_question": "q1",
      "parent_value": "CSV",
      "action_kwarg": "detail_level"
    },
    {
      "id": "q4",
      "label": "Incluir gráficos",
      "type": "radio",
      "options": ["Sim", "Não"],
      "is_required": true,
      "parent_question": "q1",
      "parent_value": "PDF",
      "action_kwarg": "include_charts"
    }
  ],
  "created_at": "2024-01-20T14:00:00Z",
  "updated_at": "2024-01-20T14:00:00Z"
}
```

---

## 10. Executar uma Action — Sucesso

### Request

```bash
curl -X POST "http://localhost:8000/api/helper/v1/actions/generate-report/execute/" \
  -H "Authorization: JWT eyJ0eXAiOiJKV1QiLCJhbGc..." \
  -H "Content-Type: application/json" \
  -d '{
    "questions": {
      "q1": "CSV",
      "q2": "2024-01",
      "q3": "Completo"
    }
  }'
```

### Response (200)

```json
{
  "status": "success",
  "message": "Relatório gerado com sucesso e enviado para seu email"
}
```

---

## 11. Executar uma Action — Erro de Validação

### Request (faltando pergunta obrigatória)

```bash
curl -X POST "http://localhost:8000/api/helper/v1/actions/generate-report/execute/" \
  -H "Authorization: JWT eyJ0eXAiOiJKV1QiLCJhbGc..." \
  -H "Content-Type: application/json" \
  -d '{
    "questions": {
      "q1": "CSV"
    }
  }'
```

### Response (400)

```json
{
  "questions": {
    "q2": ["Este campo é obrigatório."]
  }
}
```

---

## 12. Executar uma Action — Com Progresso (status: info)

### Request

```bash
curl -X POST "http://localhost:8000/api/helper/v1/actions/repair-etcd/execute/" \
  -H "Authorization: JWT eyJ0eXAiOiJKV1QiLCJhbGc..." \
  -H "Content-Type: application/json" \
  -d '{
    "questions": {}
  }'
```

### Response (200)

```json
{
  "status": "info",
  "message": "Processamento iniciado com sucesso",
  "steps": [
    {
      "name": "Conectar ao Kubernetes",
      "status": "completed"
    },
    {
      "name": "Validar estado do etcd",
      "status": "completed"
    },
    {
      "name": "Executar recuperação",
      "status": "in_progress"
    },
    {
      "name": "Verificar saúde",
      "status": "pending"
    }
  ]
}
```

---

## 13. Executar uma Action — Erro Remoto

### Request

```bash
curl -X POST "http://localhost:8000/api/helper/v1/actions/restart-pod/execute/" \
  -H "Authorization: JWT eyJ0eXAiOiJKV1QiLCJhbGc..." \
  -H "Content-Type: application/json" \
  -d '{
    "questions": {}
  }'
```

### Response (422)

```json
{
  "status": "error",
  "message": "Falha ao conectar com a API do Kubernetes: timeout após 30 segundos"
}
```

**Nota**: O campo `details` não é incluído na resposta para o frontend — fica armazenado apenas no backend em `ActionExecutionLog.result_details` para auditoria.

---

## 14. Erro de Autenticação

### Request (sem token ou token inválido)

```bash
curl -X GET "http://localhost:8000/api/helper/v1/actions/" \
  -H "Authorization: JWT invalid-token"
```

### Response (401)

```json
{
  "detail": "Token is invalid or expired"
}
```

---

## 15. Erro de Permissão

### Request (usuário logado mas sem is_superuser)

```bash
curl -X GET "http://localhost:8000/api/helper/v1/actions/" \
  -H "Authorization: JWT eyJ0eXAiOiJKV1QiLCJhbGc..."
```

(Assumindo que o token pertence a um usuário com `is_superuser: false`)

### Response (403)

```json
{
  "detail": "You do not have permission to perform this action."
}
```

---

## Resumo de Status HTTP

| Código  | Situação                | Exemplo                                            |
| ------- | ----------------------- | -------------------------------------------------- |
| **200** | Sucesso / Info          | Health OK, Execute com sucesso ou em progresso     |
| **400** | Validação do cliente    | Pergunta obrigatória faltando                      |
| **401** | Sem autenticação        | Token faltando ou expirado                         |
| **403** | Sem permissão           | is_superuser=false tentando acessar rota funcional |
| **404** | Não encontrado          | Slug de action inexistente                         |
| **422** | Erro na execução remota | API externa retornou erro                          |
| **500** | Erro interno            | Bug no backend (raro)                              |

---

## Fluxo Recomendado de Teste Manual

1. **Setup**: Obter token via login
2. **Health**: Chamar health (sem auth)
3. **WhoAmI**: Verificar acesso (com auth)
4. **Browse**: Listar ecosystems → systems → applications
5. **Services**: Listar serviços de uma application
6. **Actions**: Listar actions disponíveis
7. **Detail**: Pegar questions_schema de uma action
8. **Execute**: Testar execute com payload válido
9. **Errors**: Testar execute com dados inválidos (missing required, invalid option)
10. **Edge**: Testar sem auth, com user não-superuser

---

**Última atualização**: Julho 2026  
**Ferramentas recomendadas**: Postman, Insomnia, curl, VS Code REST Client
