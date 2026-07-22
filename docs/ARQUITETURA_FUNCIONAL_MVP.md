# Arquitetura Funcional do MVP - Helper

## 1. Objetivo

Definir a arquitetura funcional do MVP do Helper, centralizando:

- monitoramento de saude de aplicacoes e servicos;
- sincronizacao de servicos e acoes vindos de APIs externas;
- recomendacao e execucao de acoes;
- notificacao por email em incidentes e recuperacao;
- trilha de auditoria e historico operacional.

Este documento e a base para implementacao incremental no backend.

---

## 2. Escopo do MVP

### Incluido

- Servico independente (deploy e banco proprios).
- CRUD operacional via Django Admin (com soft delete como padrao).
- APIs locais de listagem e consulta para frontend.
- Execucao sincrona de acao via endpoint POST.
- Health check agendado via Django-q2.
- Sync de servicos e sync de acoes via jobs.
- Notificacao de falha e de recuperacao por email.
- Historico de monitoramento com retencao de 90 dias.
- Historico de execucao de acoes sem autodelete.
- Painel de incidentes no Django Admin.
- Logs estruturados em JSON.

### Nao incluido

- Multi-tenant por empresa.
- Criterio formal de aceite por modulo nesta fase.
- Testes de contrato com APIs externas.
- Rate limit para execucao de acao.

---

## 3. Modelo de Dominio

## 3.1 Entidades

### Ecosystem

- Campos principais: name, slug, is_active, deleted_at, created_at, updated_at.
- Relacionamento: N:N com System.
- Observacao: slug sera usado como lookup_field.

### System

- Campos principais: name, slug, description, is_active, deleted_at, created_at, updated_at.
- Relacionamentos:
  - N:N com Ecosystem.
  - N:N com User (administradores internos Django).
  - 1:N com Application.
- Observacao: slug sera usado como lookup_field.

### Application

- Campos principais: name, slug, base_url, environment, is_active, deleted_at, created_at, updated_at.
- Relacionamento: pertence a um System (1:N).
- Responsabilidade: origem dos endpoints externos monitorados:
  - /api/helper/v1/healthcare/
  - /api/helper/v1/actions/

### Service

- Campos principais: name, description, status, last_checked_at, last_status_change_at, is_active, deleted_at, created_at, updated_at.
- Relacionamento: pertence a uma Application (1:N).
- Chave de conciliacao externa: name (por aplicacao).
- Regra: nome obrigatorio.

### Action

- Campos principais: slug, name, description, questions_schema, source_version, is_active, deleted_at, created_at, updated_at.
- Relacionamentos:
  - pertence a uma Application (1:N).
  - N:N com Service.
- Chave de conciliacao externa: slug (por aplicacao).
- Regra: slug obrigatorio.
- Versionamento: obrigatorio para Action.

### Incident

- Campos principais: service, previous_status, current_status, opened_at, recovered_at, is_active, notification_sent_at, recovery_notification_sent_at.
- Objetivo: registrar mudanca de estado e controlar deduplicacao de notificacao.

### HealthCheckLog

- Campos principais: application, service_name, status, message, checked_at, raw_payload.
- Retencao: 90 dias.
- Objetivo: trilha historica de monitoramento.

### ActionExecutionLog

- Campos principais: action, executed_by, input_payload, mapped_kwargs, result_status, result_message, result_details, started_at, finished_at, raw_response.
- Retencao: sem autodelete.
- Objetivo: auditoria completa de execucao de acao.

### SyncLog

- Campos principais: application, sync_type (services/actions), status, started_at, finished_at, attempt, message, raw_payload.
- Objetivo: trilha de sincronizacao (sem diff obrigatorio no MVP).

### MaintenanceWindow

- Campos principais: name, start_at, end_at, scope_type (global/system/application), scope_id, reason, is_active.
- Objetivo: pausar alertas em janelas planejadas.

### EscalationTarget

- Campos principais: name, email, system, is_active.
- Objetivo: destinos adicionais de notificacao para escalonamento.

## 3.2 Regras de status

- Service.status: OK, FAILED, UNKNOWN.
- App health remoto: stable, failed.
- Incidente abre quando status muda para FAILED.
- Incidente recupera quando status muda de FAILED para OK.

## 3.3 Soft delete

- Entidades de dominio utilizam inativacao e deleted_at.
- Admin deve exibir ativos e inativos.
- Hard delete somente por Admin Action explicita.

---

## 4. APIs Locais (MVP)

## 4.1 Endpoints principais

- GET /api/helper/v1/ecosystems/
- GET /api/helper/v1/systems/
- GET /api/helper/v1/applications/
- GET /api/helper/v1/actions/
- GET /api/helper/v1/actions/<slug>/
- POST /api/helper/v1/actions/<slug>/execute/
- GET /api/helper/v1/health/

## 4.2 Seguranca e acesso

- Endpoints funcionais: acesso restrito a superusuarios.
- Excecao operacional: GET /api/helper/v1/health/ sem autenticacao.

## 4.3 Filtros obrigatorios

- Ecosystem: search por nome.
- System: search por nome, filtro por ecosystem.
- Application: search por nome, filtro por system e ecosystem.
- Service: search por nome, filtro por application e system.
- Action: search por nome, filtro por service.

## 4.4 Execucao de Action

- Fluxo sincrono.
- Payload de entrada com questions respondidas pelo frontend.
- Validacao dinamica baseada em questions_schema.
- Mapeamento para kwargs via action_kwarg.
- Registrar auditoria sempre, inclusive erro.

---

## 5. Integracoes Externas

## 5.1 Origens

Cada Application e monitorada por suas proprias rotas:

- /api/helper/v1/healthcare/
- /api/helper/v1/actions/
- /api/helper/v1/app-health/

Observacao:

- O documento docs/ESPECIFICACAO_TECNICA_URLS.md descreve o contrato dessas APIs externas monitoradas.
- O endpoint /api/helper/v1/app-health/ e a referencia para saude da aplicacao monitorada.
- O endpoint /api/helper/v1/health/ e apenas saude interna do servico Helper e nao substitui o app-health remoto.

## 5.2 Conciliacao

### Servicos

- Chave: name por Application.
- Se chegou da API externa e nao existe localmente: criar.
- Se existe localmente e nao veio na API externa: inativar.

### Acoes

- Chave: slug por Application.
- Se chegou da API externa e nao existe localmente: criar.
- Se existe localmente e nao veio na API externa: inativar.
- Alteracao de definicao (name/description/questions/services): atualizar e incrementar source_version.

## 5.3 Falhas de origem

- Indisponibilidade da API externa no health check deve ser tratada como FAILED.
- Registrar falha em SyncLog/HealthCheckLog.
- Aplicar retry conforme politica de agendamento.

## 5.4 Autenticacao externa

- TODO: definir estrategia final (token, OAuth2, mTLS, etc).
- MVP inicia sem autenticacao externa obrigatoria.

---

## 6. Agendamentos com Django-q2

Infra: Redis como broker.

## 6.1 Jobs

### Job 1 - Health check + sync de servicos

- Frequencia: a cada 10 minutos.
- Entrada: todas as Applications ativas.
- Processamento por aplicacao:
  - consultar healthcare remoto;
  - atualizar status por Service;
  - sincronizar cadastro de Service;
  - detectar mudanca de status;
  - abrir/fechar incidente;
  - notificar quando aplicavel.
- Retry: ate 3 tentativas com intervalo de 1 minuto.

### Job 2 - Sync de acoes

- Frequencia: 1 vez por dia.
- Entrada: todas as Applications ativas.
- Processamento por aplicacao:
  - consultar actions remotas;
  - upsert por slug;
  - inativar ausentes;
  - atualizar vinculo Action x Service;
  - versionar Action quando houver mudanca.
- Retry: ate 3 tentativas com intervalo de 1 minuto.

### Job 3 - Limpeza de historico de monitoramento

- Frequencia: 1 vez por dia.
- Regra: remover HealthCheckLog com mais de 90 dias.

## 6.2 Janela de manutencao

- Antes de enviar alerta, verificar MaintenanceWindow ativa para escopo correspondente.
- Se houver janela ativa, registrar evento e suprimir envio de email.

---

## 7. Notificacoes e Escalonamento

## 7.1 Destinatarios

- Primario: administradores do System associado.
- Escalonamento: EscalationTarget ativo para o System.

## 7.2 Regras de deduplicacao

- Enviar alerta somente em transicao para FAILED.
- Nao reenviar enquanto permanecer FAILED.
- Enviar novo alerta apenas se houver recuperacao seguida de nova falha.

## 7.3 Recuperacao

- Enviar email quando status retornar para OK.

## 7.4 Templates

Criar templates iniciais para:

- alerta de incidente;
- recuperacao de incidente;
- falha operacional de job (quando relevante para administracao).

---

## 8. Autenticacao CAS + SimpleJWT

## 8.1 Componentes

- CAS client: backend Helper.
- CAS server (SSO): configurado por CAS_SERVER_URL.
- Frontend redirect final: configurado por FRONTEND_AUTH_REDIRECT.

## 8.2 Fluxo

1. Usuario acessa frontend.
2. Frontend redireciona para backend Helper (CAS client).
3. Backend redireciona para CAS server.
4. Usuario autentica no CAS.
5. CAS retorna ticket para backend.
6. Backend valida ticket no CAS, cria/atualiza usuario local e emite JWT.
7. Backend redireciona usuario para FRONTEND_AUTH_REDIRECT com contexto de autenticacao.
8. Frontend utiliza JWT para consumir APIs locais.

## 8.3 Observacoes

- Todas as rotas funcionais exigem superusuario no MVP.
- Ajustes de expiracao/refresh seguem configuracao do SimpleJWT.

---

## 9. Observabilidade e Operacao

- Logs em JSON para API, jobs e integracoes.
- Correlation id por requisicao/job recomendado.
- Endpoint interno operacional:
  - GET /api/helper/v1/health/
- Painel de incidentes no Django Admin com filtros por status, sistema, aplicacao e periodo.

---

## 10. Testes do MVP

Cobertura minima esperada nesta fase:

- APIs locais (listagem, detalhes, execucao).
- Validacao de filtro/paginacao/ordenacao.
- Regras de permissao para superusuario.
- Jobs Django-q2 (health check, sync de acoes, retry, deduplicacao de alerta).
- Fluxo de auditoria de ActionExecutionLog.

Fora de escopo nesta fase:

- Testes de contrato com APIs externas.

---

## 11. Plano de Implementacao Sugerido

### Fase 1 - Base de dominio e admin

- Modelos, migrations e soft delete.
- Admin com listagem de ativos/inativos e hard delete por action.

### Fase 2 - APIs locais

- Endpoints de listagem e detalhes.
- Endpoint de execucao sincrona de acao.
- Endpoint interno de health.

### Fase 3 - Jobs e monitoramento

- Jobs Django-q2 + retry.
- Sync de servicos e acoes.
- Historico de monitoramento e limpeza de 90 dias.

### Fase 4 - Notificacao e incidente

- Modelo de incidente.
- Dedupe de alerta e notificacao de recuperacao.
- Templates de email.

### Fase 5 - CAS + JWT

- Integracao CAS client.
- Emissao e validacao SimpleJWT.
- Redirecionamento para frontend autenticado.

---

## 12. Riscos e TODOs

- Definir autenticacao das APIs externas monitoradas.
- Definir convencao de environment em Application (STG/HML/PRD) para evitar cadastro inconsistente.
- Definir politica final de expiracao e refresh de JWT.
- Definir estrategia de idempotencia para execucao de acoes sensiveis (quando aplicavel).
