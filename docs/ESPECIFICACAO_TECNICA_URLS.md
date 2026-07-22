## 🔌 Especificacao de APIs

## 1. Contrato Externo dos Sistemas Monitorados

Importante:

- Os endpoints desta secao sao APIs dos sistemas/aplicacoes monitorados pelo Helper.
- Esses endpoints sao consumidos pelo Helper para monitoramento e sincronizacao.
- Eles nao representam as APIs locais do MVP do Helper.
- Os detalhes completos das APIs locais do MVP (expostas pelo Helper) estao no documento de arquitetura funcional.

Documento complementar:

- Arquitetura funcional do MVP: `docs/ARQUITETURA_FUNCIONAL_MVP.md`
- Plano de proximos passos: `docs/PLANO_PROXIMOS_PASSOS_DESENVOLVIMENTO.md`

### 1.1 Healthcare Status

Status dos serviços de uma aplicação

**Endpoint:** `GET /api/helper/v1/healthcare/`

**Autenticação:** Conforme `VERT_HELPER["PERMISSION_CLASS"]`

**Response:**
```json
{
    "S3": {
        "status": "OK",
        "last_updated": "2024-06-10T12:34:56Z"
    },
    "POSTGRESQL": {
        "status": "FAILED",
        "message": "Connection timeout",
        "last_updated": "2024-06-10T12:35:00Z"
    },
    "KAFKA": {
        "status": "UNKNOWN",
        "message": "Service not configured",
        "last_updated": null
    }
}
```

**Opção:** Query param `?force_refresh=true` para forçar check imediato

---

### 1.2 Listar Actions

Ações de uma aplicação

**Endpoint:** `GET /api/helper/v1/actions/`

**Autenticação:** Conforme `VERT_HELPER["PERMISSION_CLASS"]`

**Query Params:**
- `service=<service_name>` - Filtrar por serviço
- `search=<termo>` - Buscar por nome/descrição
- `page=<num>` - Paginação
- `page_size=<num>` - Itens por página (padrão: 10)
- `ordering=-name` - Ordenar por campo

**Response:**
```json
{
    "count": 15,
    "next": "http://api.example.com/helper/v1/actions/?page=2",
    "previous": null,
    "results": [
        {
            "id": "uuid-123",
            "slug": "execute-without-kafka",
            "name": "Executar sem Kafka",
            "description": "Executa operação sem dependência do Kafka",
            "services": ["S3", "KAFKA"],
            "status": "active",
            "is_recommended": true,  // se serviço falhou
            "created_at": "2024-06-01T10:00:00Z"
        }
    ]
}
```

**Ordenação Automática:** Se algum serviço em `services` está `FAILED`, action aparece com `is_recommended: true` no topo

---

### 1.3 Detalhes da Action + Formulario

Receber mais informações de uma ação, inclusive um formulário dinamico que deverá ser preenchido para executa-la

**Endpoint:** `GET /api/helper/v1/actions/<slug>/`

**Autenticação:** Conforme `VERT_HELPER["PERMISSION_CLASS"]`

**Response:**
```json
{
    "id": "uuid-123",
    "slug": "generate-document",
    "name": "Gerar Documento",
    "description": "Gera documento em CSV ou JSON",
    "services": ["S3"],
    "status": "active",
    "questions": [
        {
            "id": "q1",
            "label": "O arquivo é CSV ou JSON?",
            "type": "radio",
            "options": ["CSV", "JSON"],
            "is_required": true,
            "parent_question": null,
            "parent_value": null,
            "action_kwarg": "file_type"
        },
        {
            "id": "q2",
            "label": "Você irá mandar o arquivo ou URL?",
            "type": "radio",
            "options": ["Arquivo", "URL"],
            "is_required": true,
            "parent_question": "q1",
            "parent_value": "CSV",
            "action_kwarg": "csv_source"
        },
        {
            "id": "q3",
            "label": "Qual ID do workflow?",
            "type": "text",
            "options": null,
            "is_required": true,
            "parent_question": "q1",
            "parent_value": "JSON",
            "action_kwarg": "workflow_id"
        }
    ],
    "created_at": "2024-06-01T10:00:00Z"
}
```

---

### 1.4 Executar Action
**Endpoint:** `POST /api/helper/v1/actions/<slug>/execute/`

**Autenticação:** Conforme `VERT_HELPER["PERMISSION_CLASS"]`

**Request Body:**
```json
{
    "questions": {
        "q1": "CSV",
        "q2": "Arquivo",
        "q3": "workflow-123"
    }
}
```

**Response (Sucesso):**
```json
{
    "status": "success",
    "message": "Documento gerado com sucesso"
}
```

**Response (Erro):**
```json
{
    "status": "error",
    "message": "Falha ao gerar documento",
    "details": "S3 connection failed" // Será apenas armazenado, não será exibido no front
}
```

**Response (Info):**
```json
{
    "status": "info",
    "message": "Documento não pode ser gerado no momento",
    "steps": [
        "Verifique se o workflow 123 está ativo",
        "Confirme se o bucket S3 está acessível",
        "Tente novamente em alguns minutos"
    ]
}
```

---

### 1.5 App Health (Sem Django) 

Objetivo: Consultar saúde da aplicação pelo Dockerfile

Importante: este endpoint e obrigatorio para cada sistema monitorado pelo Helper.
Ele representa a saude da aplicacao remota (stable/failed) e nao substitui o endpoint interno do proprio Helper.

**Endpoint:** `GET /api/helper/v1/app-health/`

**Autenticação:** ❌ Nenhuma

**Response:**
```json
{
    "status": "stable"
}
```

ou

```json
{
    "status": "failed",
    "message": "Application startup failed"
}
```

---

## 2. Contrato Interno do MVP (API do Helper)

Importante:

- Esta secao descreve APIs expostas pelo proprio Helper.
- No MVP, as rotas funcionais locais ficam restritas a superusuarios.

### 2.1 Helper Internal Health

Objetivo: endpoint de saude do proprio servico Helper para liveness/readiness.

Importante: este endpoint e apenas operacional do servico Helper.
Para monitoramento de sistemas externos, a referencia continua sendo o endpoint /api/helper/v1/app-health/ de cada aplicacao monitorada.

**Endpoint:** `GET /api/helper/v1/health/`

**Autenticacao:** ❌ Nenhuma (uso operacional)

**Response:**
```json
{
    "status": "ok"
}
```

ou

```json
{
    "status": "failed",
    "message": "Database unreachable"
}
```

### 2.2 Demais APIs Locais do MVP

As demais rotas locais do Helper (protegidas para superusuarios) sao:

- GET /api/helper/v1/ecosystems/
- GET /api/helper/v1/systems/
- GET /api/helper/v1/applications/
- GET /api/helper/v1/actions/
- GET /api/helper/v1/actions/<slug>/
- POST /api/helper/v1/actions/<slug>/execute/

Para payloads e regras completas dessas rotas, consultar docs/ARQUITETURA_FUNCIONAL_MVP.md.

---

## Decisoes Fechadas do MVP

### Escopo

- O Helper sera um servico independente (deploy e banco proprios).
- Nao havera multi-tenant por empresa no MVP; os ambientes STG/HML/PRD sao independentes por deploy.
- Cadastro de entidades sera somente via Django Admin no MVP.
- Acesso aos endpoints do Helper sera restrito a superusuarios.
- Excecao operacional: endpoint interno `GET /api/helper/v1/health/` sem autenticacao.

### Dominio e Relacionamentos

- Ecossistema x Sistema: N:N.
- Sistema x Administradores: N:N com usuarios internos do Django.
- Aplicacao pertence a exatamente um Sistema.
- Servico pertence a exatamente uma Aplicacao.
- Acao pertence a exatamente uma Aplicacao.
- Acao x Servico: N:N sem prioridade por vinculo.
- Soft delete para entidades de dominio, com hard delete via Admin Action.
- Versionamento de Acao e obrigatorio; Servico nao tera versionamento formal.

### Status e Regras

- Status de Servico: OK, FAILED, UNKNOWN.
- Status de App em app-health: stable, failed.
- Notificacao de incidente: apenas em mudanca de status para FAILED.
- Notificacao de recuperacao: enviar quando voltar para OK.

### APIs Locais (MVP)

- Listagem de Ecossistemas.
- Listagem de Sistemas.
- Listagem de Aplicacoes.
- Listagem de Acoes.
- Execucao de Acao via POST sincrono.
- Todos os endpoints de listagem terao paginacao, filtros e ordenacao.

### Filtros Obrigatorios

- Ecossistema: busca por nome.
- Sistema: busca por nome, filtro por ecossistema.
- Aplicacao: busca por nome, filtro por sistema e ecossistema.
- Servico: busca por nome, filtro por aplicacao e sistema.
- Acao: busca por nome, filtro por servico.

### Integracoes Externas

- Rotas externas monitoradas: /api/helper/v1/healthcare/ e /api/helper/v1/actions/.
- Autenticacao externa: TODO (a definir, por ora sem autenticacao).
- Chaves de conciliacao:
  - Servico: name.
  - Acao: slug.
- Regra de sincronizacao:
  - Novo item encontrado: criar.
  - Item ausente na origem: inativar.
- Indisponibilidade externa no health check deve ser tratada como FAILED.

### Agendamentos (Django-q2 + Redis)

- Health check + sync de servicos: a cada 10 minutos.
- Sync de acoes: 1 vez por dia.
- Retry para health check e sync de acoes: 3 tentativas com intervalo de 1 minuto.
- Notificacao por email em falhas.
- Janela de manutencao: tabela no Admin para pausar alertas por periodo.

### Auditoria, Logs e Retencao

- Historico de monitoramento com retencao de 90 dias.
- Historico de execucao de acoes sem autodelete.
- Auditoria de execucao obrigatoria: quem executou, quando, parametros e resultado.
- Logs estruturados em JSON obrigatorios.
- Painel de incidentes no Django Admin faz parte do MVP.

---

## Autenticacao CAS + SimpleJWT (MVP)

Fluxo adotado:

1. User/browser acessa o frontend.
2. Frontend redireciona para o backend (CAS client).
3. Backend redireciona para o CAS Server (SSO).
4. Usuario autentica no SSO.
5. CAS redireciona para o backend com ticket valido.
6. Backend valida ticket no CAS Server, cria/atualiza usuario local e emite token JWT para o frontend.
7. Frontend recebe o redirecionamento final e passa a consumir APIs com JWT.

Variaveis de ambiente:

- `CAS_SERVER_URL`: URL base do servidor CAS/SSO.
- `FRONTEND_AUTH_REDIRECT`: URL de redirecionamento final para o frontend apos autenticacao.

Observacoes:

- Criterios formais de aceite por modulo nao serao definidos nesta fase.
- A estrategia de refresh/expiracao do JWT ficara alinhada com configuracao do SimpleJWT no backend.
