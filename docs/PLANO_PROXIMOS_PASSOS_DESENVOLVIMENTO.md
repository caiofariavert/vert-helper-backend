# Plano de Proximos Passos de Desenvolvimento - Helper

## 1. Objetivo

Definir a sequencia de implementacao do MVP do Helper, com foco em entregas incrementais, baixo retrabalho e validacao continua.

Este plano considera as decisoes registradas em:

- docs/ESPECIFICACAO_TECNICA_URLS.md
- docs/ARQUITETURA_FUNCIONAL_MVP.md

---

## 2. Estrategia de Execucao

- Implementacao por fases curtas, sempre entregando algo funcional.
- Priorizar base de dominio e seguranca antes de integracoes externas.
- Garantir rastreabilidade via logs e auditoria desde o inicio.
- Evitar acoplamento alto entre sync, notificacao e execucao de acoes.

---

## 3. Roadmap Tecnico (ordem recomendada)

## Fase 0 - Preparacao do Projeto

Objetivo: deixar o ambiente pronto para desenvolver com previsibilidade.

Entregaveis:

- Revisao e complementacao de src/.env.sample com variaveis do MVP:
  - CAS_SERVER_URL
  - FRONTEND_AUTH_REDIRECT
  - configuracoes de email
  - configuracoes do Redis/Django-q2
- Revisao de settings para centralizar configuracoes do modulo Helper.
- Definicao de padrao de logs JSON para API e jobs.

Checklist:

- Aplicacao sobe localmente com make up.
- Django admin acessivel.
- Fila Django-q2 conectada ao Redis.

---

## Fase 1 - Modelagem de Dominio e Admin

Objetivo: criar o nucleo de dados do MVP com soft delete e operacao via admin.

Entregaveis:

- Models e migrations de:
  - Ecosystem
  - System
  - Application
  - Service
  - Action
  - Incident
  - HealthCheckLog
  - ActionExecutionLog
  - SyncLog
  - MaintenanceWindow
  - EscalationTarget
- Campos obrigatorios e chaves conforme especificacao:
  - Service.name obrigatorio
  - Action.slug obrigatorio
  - Ecosystem.slug e System.slug como lookup
- Soft delete padrao + Admin Action para hard delete.
- Django Admin com filtros e busca para operacao inicial.

Checklist:

- Migrations aplicam sem erro.
- Admin exibe ativos e inativos.
- Hard delete disponivel somente por acao administrativa explicita.

---

## Fase 2 - API Local do MVP (Leitura + Health Interno)

Objetivo: disponibilizar endpoints internos do Helper para consulta do frontend e operacao.

Entregaveis:

- Endpoint operacional interno:
  - GET /api/helper/v1/health/
- Endpoints de listagem:
  - GET /api/helper/v1/ecosystems/
  - GET /api/helper/v1/systems/
  - GET /api/helper/v1/applications/
  - GET /api/helper/v1/actions/
- Endpoint de detalhe:
  - GET /api/helper/v1/actions/<slug>/
- Paginacao, filtros e ordenacao conforme regras definidas.
- Restricao de acesso a superusuarios nas rotas funcionais.

Checklist:

- Rotas respondem conforme contrato.
- Filtros obrigatorios funcionando.
- Endpoint interno /health responde sem autenticacao.

---

## Fase 3 - Execucao Sincrona de Acoes + Auditoria

Objetivo: permitir disparo de acao pelo frontend com trilha completa de execucao.

Entregaveis:

- Endpoint:
  - POST /api/helper/v1/actions/<slug>/execute/
- Validacao de questions dinamicas e parent_question/parent_value.
- Mapeamento de respostas para kwargs (action_kwarg).
- Registro obrigatorio em ActionExecutionLog:
  - usuario
  - entrada
  - kwargs mapeados
  - status final
  - mensagem
  - detalhes tecnicos

Checklist:

- Execucao sincrona finalizada no mesmo request.
- Erros e infos retornam no padrao da especificacao.
- Auditoria registrada em 100% das execucoes.

---

## Fase 4 - Integracao Externa e Sincronizacao

Objetivo: sincronizar dados vindos dos sistemas monitorados.

Entregaveis:

- Cliente de integracao por Application para:
  - /api/helper/v1/healthcare/
  - /api/helper/v1/actions/
  - /api/helper/v1/app-health/
- Regra de conciliacao:
  - Service por name
  - Action por slug
- Upsert dos itens encontrados e inativacao dos ausentes.
- Versionamento de Action quando houver alteracao de definicao.
- Registro de execucao e falha em SyncLog.

Checklist:

- Sync cria/atualiza/inativa corretamente.
- Falhas de comunicacao ficam registradas.
- Nao ocorre hard delete automatico por sync.

---

## Fase 5 - Jobs Django-q2 e Monitoramento

Objetivo: automatizar monitoramento e sincronizacao.

Entregaveis:

- Job de health check + sync de servicos a cada 10 min.
- Job de sync de acoes 1x ao dia.
- Retry de 3 tentativas com 1 min de intervalo.
- Job de limpeza de HealthCheckLog para retencao de 90 dias.

Checklist:

- Jobs cadastrados e executando por agendamento.
- Retry aplicado nos cenarios de falha.
- Logs de job com identificador de execucao.

---

## Fase 6 - Incidentes, Alertas e Recuperacao

Objetivo: operacionalizar notificacao de falha/recuperacao sem ruido.

Entregaveis:

- Deteccao de mudanca de status por Service.
- Regra de notificacao:
  - notifica na transicao para FAILED
  - nao repete enquanto permanecer FAILED
  - notifica recuperacao ao voltar para OK
- Templates de email:
  - alerta de incidente
  - recuperacao
- Suporte a MaintenanceWindow para suprimir envio temporariamente.
- Escalonamento por EscalationTarget.

Checklist:

- Deduplicacao funcionando conforme regra definida.
- Recuperacao envia email.
- Janela de manutencao bloqueia notificacao e registra evento.

---

## Fase 7 - CAS + SimpleJWT

Objetivo: concluir autenticacao e autorizacao do fluxo web.

Entregaveis:

- Fluxo CAS client no backend:
  - redirecionar para CAS
  - validar ticket
  - criar/atualizar usuario
- Emissao de JWT para o frontend.
- Redirecionamento final para FRONTEND_AUTH_REDIRECT.
- Garantia de acesso funcional apenas para superusuario no MVP.

Checklist:

- Login via SSO funcionando fim-a-fim.
- JWT aceito nas APIs locais.
- Usuario sem superuser nao acessa rotas funcionais.

---

## Fase 8 - Testes, Harden e Go-live

Objetivo: estabilizar antes de promover ambiente.

Entregaveis:

- Testes de APIs locais.
- Testes de jobs principais com cenarios de falha e retry.
- Testes de permissao e auditoria.
- Validacao de logs JSON.
- Revisao de configuracao por ambiente (STG/HML/PRD).

Checklist:

- Suite minima de testes verde.
- Sem erros criticos pendentes em fluxo principal.
- Plano de rollback documentado para deploy inicial.

---

## 4. Dependencias e Pontos de Atencao

- Definir formato final de autenticacao das APIs externas (TODO em aberto).
- Padronizar identificacao de Application.environment para evitar inconsistencias de cadastro.
- Garantir timeout e tratamento de erro de rede nas integracoes externas.
- Definir politica de expiracao e refresh do JWT no backend.

---

## 5. Sequencia de Entrega Recomendada

1. Fase 0 + Fase 1
2. Fase 2 + Fase 3
3. Fase 4 + Fase 5
4. Fase 6
5. Fase 7
6. Fase 8

---

## 6. Definicao de Pronto (DoD) por Fase

Uma fase e considerada concluida quando:

- codigo implementado e revisado;
- migrations aplicadas com sucesso;
- testes da fase executados sem falha;
- logs essenciais do fluxo validos;
- documentacao atualizada (arquitetura e especificacao, se houver impacto).

---

## 7. Proxima Acao Imediata

Iniciar Fase 0 e Fase 1 em paralelo leve:

- atualizar variaveis necessarias em src/.env.sample;
- criar apps/modelos do dominio do Helper;
- preparar migrations iniciais e configuracao de Admin.
