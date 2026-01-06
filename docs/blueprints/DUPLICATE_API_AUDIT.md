# Duplicate API Audit Report

Generated: 2026-06-19
Total findings: 238

## 🟡 CROSS-EXTENSION collision (review needed) (10)

### `AuditQueryService`
_No contracts/core version; defined independently in lexigram-ai-governance, lexigram-audit_

- **lexigram-ai-governance** `audit/query.py:69` class
- **lexigram-audit** `query.py:16` class

### `AuditRepositoryMixin`
_No contracts/core version; defined independently in lexigram-admin, lexigram-sql_

- **lexigram-admin** `core/resilience_config.py:134` class → `(Generic)`
- **lexigram-sql** `audit/mixin.py:17` class

### `Field`
_No contracts/core version; defined independently in lexigram-admin, lexigram-sql_

- **lexigram-admin** `forms/fields/_base.py:390` variable = `AbstractField`
- **lexigram-sql** `schema/model.py:78` class

### `MemoryProvider`
_No contracts/core version; defined independently in lexigram-ai-memory, lexigram-features, lexigram-testing_

- **lexigram-ai-memory** `di/provider.py:39` class → `(Provider)`
- **lexigram-features** `backends/testing.py:17` class → `(LocalProvider)`
- **lexigram-testing** `memory/di/provider.py:24` class → `(Provider)`

### `MetricsCollector`
_No contracts/core version; defined independently in lexigram-ai-llm, lexigram-ui_

- **lexigram-ai-llm** `metrics/collector.py:193` class
- **lexigram-ui** `performance/observability.py:38` class

### `Page`
_No contracts/core version; defined independently in lexigram-admin, lexigram-sql, lexigram-web_

- **lexigram-admin** `pages/base.py:18` class → `(ABC)`
- **lexigram-sql** `pagination/offset.py:18` class → `(Generic)`
- **lexigram-web** `pagination/models.py:102` class → `(Generic)`

### `SchemaDiff`
_No contracts/core version; defined independently in lexigram-graphql, lexigram-sql_

- **lexigram-graphql** `schema/diff.py:13` class
- **lexigram-sql** `types.py:80` class

### `SessionManagerImpl`
_No contracts/core version; defined independently in lexigram-ai-session, lexigram-auth_

- **lexigram-ai-session** `manager/core.py:37` class → `(SessionManagerProtocol)`
- **lexigram-auth** `session/manager.py:33` class

### `TransformationPipeline`
_No contracts/core version; defined independently in lexigram-ai-rag, lexigram-search_

- **lexigram-ai-rag** `query/pipeline.py:6` class
- **lexigram-search** `indexing/transformer.py:29` class

### `field`
_No contracts/core version; defined independently in lexigram-graphql, lexigram-sql_

- **lexigram-graphql** `schema/decorators.py:186` function
- **lexigram-sql** `repositories/filter_objects.py:198` function

## 🟢 Expected specialization (contracts/core extended) (198)

### `AIError`
_Canonical in lexigram-contracts (ai/exceptions.py); specialized in lexigram-ai, lexigram-ai-llm_

- **lexigram-ai** `exceptions.py:8` class → `(_ContractsAIError)`
- **lexigram-ai-llm** `types.py:159` variable = `LLMError`
- **lexigram-contracts** `ai/exceptions.py:18` class → `(DomainError)`

### `AbstractReadOnlyRepository`
_Canonical in lexigram (primitives/data.py); specialized in lexigram-events_

- **lexigram** `primitives/data.py:55` class → `(ReadOnlyRepositoryProtocol, Generic)`
- **lexigram-events** `repository/base.py:72` class → `(ABC, Generic)`

### `AbstractRepository`
_Canonical in lexigram (primitives/data.py); specialized in lexigram-events_

- **lexigram** `primitives/data.py:165` class → `(AbstractReadOnlyRepository, RepositoryProtocol, Generic)`
- **lexigram-events** `repository/base.py:19` class → `(ABC, Generic)`

### `ActionHandler`
_Canonical in lexigram (hooks/types.py); specialized in lexigram-admin_

- **lexigram** `hooks/types.py:11` variable = `...`
- **lexigram-admin** `realtime/ws_handler_registry.py:88` class

### `AdminCommand`
_Canonical in lexigram-contracts (admin/cqrs/command.py); specialized in lexigram-admin_

- **lexigram-admin** `cqrs/commands.py:15` class
- **lexigram-contracts** `admin/cqrs/command.py:6` class

### `AdminError`
_Canonical in lexigram-contracts (admin/errors.py); specialized in lexigram-admin_

- **lexigram-admin** `core/middleware.py:170` class → `(CoreAdminError)`
- **lexigram-contracts** `admin/errors.py:14` class → `(LexigramError)`

### `AdminQuery`
_Canonical in lexigram-contracts (admin/cqrs/query.py); specialized in lexigram-admin_

- **lexigram-admin** `cqrs/queries.py:14` class
- **lexigram-contracts** `admin/cqrs/query.py:6` class

### `AggregateRoot`
_Canonical in lexigram (domain/models/aggregate.py); specialized in lexigram-events_

- **lexigram** `domain/models/aggregate.py:15` class → `(Entity)`
- **lexigram-events** `aggregates/aggregate.py:26` class → `(BaseAggregateRoot, ABC)`

### `AsyncStringSerializerProtocol`
_Canonical in lexigram-contracts (core/serialization.py); specialized in lexigram-cli_

- **lexigram-cli** `registry/serializer.py:17` class → `(ABC)`
- **lexigram-contracts** `core/serialization.py:30` class → `(Protocol)`

### `AsyncValidator`
_Canonical in lexigram (validation/engine/validator.py); specialized in lexigram-admin_

- **lexigram** `validation/engine/validator.py:90` class → `(Generic)`
- **lexigram-admin** `forms/async_validation.py:108` class

### `AuditEntry`
_Canonical in lexigram-contracts (admin/audit_entry.py); specialized in lexigram-admin_

- **lexigram-admin** `core/resilience_config.py:77` class
- **lexigram-contracts** `admin/audit_entry.py:19` class

### `AuditLoggerProtocol`
_Canonical in lexigram-contracts (audit/protocols.py); specialized in lexigram-secrets_

- **lexigram-contracts** `audit/protocols.py:24` class → `(Protocol)`
- **lexigram-secrets** `audit/decorator.py:16` class → `(Protocol)`

### `AuditOutcome`
_Canonical in lexigram-contracts (admin/audit_entry.py); specialized in lexigram-audit_

- **lexigram-audit** `constants.py:54` class → `(StrEnum)`
- **lexigram-contracts** `admin/audit_entry.py:10` class → `(str, Enum)`

### `AuditQuery`
_Canonical in lexigram-contracts (audit/types.py); specialized in lexigram-ai-governance_

- **lexigram-ai-governance** `audit/models.py:18` class
- **lexigram-contracts** `audit/types.py:75` class

### `AuthError`
_Canonical in lexigram-contracts (auth/exceptions.py); specialized in lexigram-auth_

- **lexigram-auth** `exceptions.py:32` class → `(ContractsAuthError)`
- **lexigram-contracts** `auth/exceptions.py:29` class → `(DomainError)`

### `AuthenticationError`
_Canonical in lexigram-contracts (exceptions/domain.py); specialized in lexigram-auth, lexigram-graphql, lexigram-web_

- **lexigram-auth** `exceptions.py:38` class → `(LexigramAuthenticationError, AuthError)`
- **lexigram-contracts** `exceptions/domain.py:37` class → `(DomainError)`
- **lexigram-graphql** `exceptions.py:83` class → `(GraphQLError, _ContractsAuthenticationError)`
- **lexigram-web** `middleware/auth.py:202` variable = `LexigramAuthenticationError`

### `AuthorizationError`
_Canonical in lexigram-contracts (exceptions/domain.py); specialized in lexigram-auth, lexigram-graphql, lexigram-web_

- **lexigram-auth** `exceptions.py:44` class → `(LexigramAuthorizationError, AuthError)`
- **lexigram-contracts** `exceptions/domain.py:46` class → `(DomainError)`
- **lexigram-graphql** `exceptions.py:95` class → `(GraphQLError, _ContractsAuthorizationError)`
- **lexigram-web** `middleware/auth.py:203` variable = `LexigramAuthorizationError`

### `BackendRegistry`
_Canonical in lexigram (primitives/registry/core.py); specialized in lexigram-cache_

- **lexigram** `primitives/registry/core.py:372` class → `(Registry)`
- **lexigram-cache** `backends/registry.py:63` class → `(_CoreBackendRegistry)`

### `BudgetExceededError`
_Canonical in lexigram-contracts (ai/governance/errors.py); specialized in lexigram-ai-agents_

- **lexigram-ai-agents** `exceptions.py:177` class → `(AgentError)`
- **lexigram-contracts** `ai/governance/errors.py:14` class → `(GovernanceError)`

### `CacheError`
_Canonical in lexigram-contracts (infra/cache/exceptions.py); specialized in lexigram-cache, lexigram-search_

- **lexigram-cache** `exceptions.py:40` class → `(LexigramError)`
- **lexigram-contracts** `infra/cache/exceptions.py:10` class → `(DomainError)`
- **lexigram-search** `exceptions.py:42` class → `(SearchError)`

### `CacheKeyBuilderProtocol`
_Canonical in lexigram-contracts (infra/cache/protocols.py); specialized in lexigram-cache_

- **lexigram-cache** `protocols.py:67` class → `(Protocol)`
- **lexigram-contracts** `infra/cache/protocols.py:214` class → `(Protocol)`

### `CacheProtectionStrategyProtocol`
_Canonical in lexigram-contracts (infra/cache/protocols.py); specialized in lexigram-cache_

- **lexigram-cache** `protocols.py:92` class → `(Protocol)`
- **lexigram-contracts** `infra/cache/protocols.py:168` class → `(Protocol)`

### `CacheProviderProtocol`
_Canonical in lexigram-contracts (admin/cache_provider.py); specialized in lexigram-cache_

- **lexigram-cache** `protocols.py:24` class → `(Protocol)`
- **lexigram-contracts** `admin/cache_provider.py:9` class → `(Protocol)`

### `ChatMessage`
_Canonical in lexigram-contracts (ai/chat.py); specialized in lexigram-ai-llm_

- **lexigram-ai-llm** `types.py:24` class → `(DomainModel)`
- **lexigram-contracts** `ai/chat.py:13` class

### `ChatPromptTemplate`
_Canonical in lexigram-contracts (ai/prompt.py); specialized in lexigram-ai-prompt_

- **lexigram-ai-prompt** `template/chat.py:15` class → `(AbstractPromptTemplate)`
- **lexigram-contracts** `ai/prompt.py:53` class

### `Chunk`
_Canonical in lexigram-contracts (ai/chunks.py); specialized in lexigram-ai-rag_

- **lexigram-ai-rag** `chunking/types.py:15` class → `(DomainModel, ChunkBase)`
- **lexigram-contracts** `ai/chunks.py:10` class

### `ChunkerProtocol`
_Canonical in lexigram-contracts (ai/vector.py); specialized in lexigram-ai-rag_

- **lexigram-ai-rag** `protocols.py:7` class → `(Protocol)`
- **lexigram-contracts** `ai/vector.py:193` class → `(Protocol)`

### `CircuitBreakerConfig`
_Canonical in lexigram-contracts (infra/resilience/models.py); specialized in lexigram-ai-llm_

- **lexigram-ai-llm** `health/circuit_breaker.py:25` class
- **lexigram-contracts** `infra/resilience/models.py:39` class

### `CircuitBreakerMiddleware`
_Canonical in lexigram (middleware/builtins/resilience.py); specialized in lexigram-events_

- **lexigram** `middleware/builtins/resilience.py:106` class
- **lexigram-events** `middleware/circuit_breaker.py:20` class → `(AbstractMiddleware)`

### `CircuitOpenError`
_Canonical in lexigram-contracts (exceptions/resilience.py); specialized in lexigram-resilience_

- **lexigram-contracts** `exceptions/resilience.py:73` class → `(CircuitBreakerError)`
- **lexigram-resilience** `exceptions.py:47` class → `(CircuitBreakerError)`

### `CircuitState`
_Canonical in lexigram-contracts (infra/resilience/enums.py); specialized in lexigram-ai-llm_

- **lexigram-ai-llm** `health/circuit_breaker.py:16` class → `(StrEnum)`
- **lexigram-contracts** `infra/resilience/enums.py:8` class → `(StrEnum)`

### `Citation`
_Canonical in lexigram-contracts (ai/index.py); specialized in lexigram-ai-rag_

- **lexigram-ai-rag** `citations/_models.py:67` class
- **lexigram-contracts** `ai/index.py:35` class

### `Column`
_Canonical in lexigram-contracts (data/identifiers.py); specialized in lexigram-admin_

- **lexigram-admin** `forms/layout.py:129` class → `(AbstractLayoutNode)`
- **lexigram-contracts** `data/identifiers.py:252` class → `(Identifier)`

### `Command`
_Canonical in lexigram-contracts (events/messages.py); specialized in lexigram-admin, lexigram-events_

- **lexigram-admin** `models/provider_models.py:11` class
- **lexigram-contracts** `events/messages.py:182` class → `(Message, Generic)`
- **lexigram-events** `messages/command.py:20` class → `(_Command)`

### `CommandHandlerProtocol`
_Canonical in lexigram-contracts (events/protocols.py); specialized in lexigram-events_

- **lexigram-contracts** `events/protocols.py:165` class → `(Protocol)`
- **lexigram-events** `handlers/base.py:25` class → `(ABC, Generic)`

### `Completion`
_Canonical in lexigram-contracts (ai/llm.py); specialized in lexigram-ai-llm_

- **lexigram-ai-llm** `types.py:51` class → `(DomainModel)`
- **lexigram-contracts** `ai/llm.py:506` class

### `ConcurrencyError`
_Canonical in lexigram (concurrency/exceptions.py); specialized in lexigram-events_

- **lexigram** `concurrency/exceptions.py:10` class → `(LexigramError)`
- **lexigram-events** `exceptions.py:42` class → `(EventError)`

### `ConfigLoader`
_Canonical in lexigram (config/lib/sources.py); specialized in lexigram-cli_

- **lexigram** `config/lib/sources.py:311` class
- **lexigram-cli** `lib/config_loader.py:127` class

### `ConfigRegistry`
_Canonical in lexigram (config/lib/registry.py); specialized in lexigram-admin_

- **lexigram** `config/lib/registry.py:10` class
- **lexigram-admin** `settings/panel/registry.py:60` class

### `ConfigurationError`
_Canonical in lexigram (exceptions.py); specialized in lexigram-search, lexigram-testing_

- **lexigram** `exceptions.py:69` class → `(LexigramException)`
- **lexigram-contracts** `exceptions/config.py:29` class → `(LexigramError)`
- **lexigram-search** `exceptions.py:54` class → `(SearchError)`
- **lexigram-testing** `lib/stubs.py:19` class → `(Exception)`

### `ConflictError`
_Canonical in lexigram-contracts (exceptions/domain.py); specialized in lexigram-admin, lexigram-web_

- **lexigram-admin** `exceptions.py:41` class → `(DomainError)`
- **lexigram-contracts** `exceptions/domain.py:64` class → `(DomainError)`
- **lexigram-web** `exceptions.py:119` class → `(HTTPError)`

### `ConnectionProtocol`
_Canonical in lexigram-contracts (data/sql/database.py); specialized in lexigram-sql_

- **lexigram-contracts** `data/sql/database.py:93` class → `(Protocol)`
- **lexigram-sql** `api/protocols.py:15` class → `(Protocol)`

### `Container`
_Canonical in lexigram (di/container/container.py); specialized in lexigram-ui_

- **lexigram** `di/container/container.py:52` class → `(ContainerRegistrarProtocol, ContainerResolverProtocol)`
- **lexigram-ui** `atoms/layout.py:203` class → `(Component)`

### `Context`
_Canonical in lexigram (primitives/context.py); specialized in lexigram-ai-rag, lexigram-testing_

- **lexigram** `primitives/context.py:187` class
- **lexigram-ai-rag** `types.py:16` class → `(DomainModel)`
- **lexigram-testing** `fixtures/bed.py:105` variable = `None`

### `ContextChunk`
_Canonical in lexigram-contracts (ai/chunks.py); specialized in lexigram-ai-rag_

- **lexigram-ai-rag** `synthesis/types.py:36` class → `(ContextChunkBase)`
- **lexigram-contracts** `ai/chunks.py:21` class → `(Chunk)`

### `DataError`
_Canonical in lexigram-contracts (data/exceptions.py); specialized in lexigram-admin, lexigram-sql_

- **lexigram-admin** `exceptions.py:53` class → `(DomainError)`
- **lexigram-contracts** `data/exceptions.py:20` class → `(DomainError)`
- **lexigram-sql** `exceptions.py:353` class → `(LexigramError)`

### `DataLoaderProtocol`
_Canonical in lexigram-contracts (graphql/protocols.py); specialized in lexigram-admin, lexigram-graphql_

- **lexigram-admin** `data/data_loader.py:18` class → `(Generic)`
- **lexigram-contracts** `graphql/protocols.py:152` class → `(Protocol)`
- **lexigram-graphql** `dataloader/loader.py:26` class → `(Generic)`

### `DataMapper`
_Canonical in lexigram (primitives/data.py); specialized in lexigram-sql_

- **lexigram** `primitives/data.py:291` class → `(ReadOnlyMapper, Generic)`
- **lexigram-sql** `mappers/base.py:44` class → `(ABC, Generic)`

### `DatabaseProviderProtocol`
_Canonical in lexigram-contracts (data/sql/database.py); specialized in lexigram-sql_

- **lexigram-contracts** `data/sql/database.py:159` class → `(Protocol)`
- **lexigram-sql** `api/protocols.py:61` class → `(Protocol)`

### `DeleteResult`
_Canonical in lexigram-contracts (data/sql/database.py); specialized in lexigram-graphql_

- **lexigram-contracts** `data/sql/database.py:420` class
- **lexigram-graphql** `schema/types.py:179` class

### `DeliveryStatus`
_Canonical in lexigram-contracts (notification/delivery.py); specialized in lexigram-webhook_

- **lexigram-contracts** `notification/delivery.py:9` class → `(StrEnum)`
- **lexigram-webhook** `constants.py:57` class → `(StrEnum)`

### `DistributedLockProtocol`
_Canonical in lexigram-contracts (core/lock.py); specialized in lexigram-cache_

- **lexigram-cache** `locks/distributed.py:22` class
- **lexigram-contracts** `core/lock.py:38` class → `(Protocol)`

### `Document`
_Canonical in lexigram-contracts (ai/document.py); specialized in lexigram-ai-workers_

- **lexigram-ai-workers** `document_ingestion/types.py:35` class
- **lexigram-contracts** `ai/document.py:13` class

### `DuplicateHandlerError`
_Canonical in lexigram-contracts (exceptions/events.py); specialized in lexigram-testing_

- **lexigram-contracts** `exceptions/events.py:50` class → `(EventError)`
- **lexigram-testing** `memory/exceptions.py:46` class → `(CommandBusError, ContractDuplicateHandlerError)`

### `DuplicateKeyError`
_Canonical in lexigram-contracts (exceptions/infra.py); specialized in lexigram-nosql, lexigram-sql_

- **lexigram-contracts** `exceptions/infra.py:119` class → `(ConstraintError)`
- **lexigram-nosql** `exceptions.py:26` class → `(NoSQLError)`
- **lexigram-sql** `exceptions.py:158` class → `(IntegrityError)`

### `EmbeddingClientProtocol`
_Canonical in lexigram-contracts (ai/llm.py); specialized in lexigram-ai-rag_

- **lexigram-ai-rag** `evaluation/types.py:12` variable = `Any`
- **lexigram-contracts** `ai/llm.py:143` class → `(Protocol)`

### `EmbeddingError`
_Canonical in lexigram-contracts (data/vector/exceptions.py); specialized in lexigram-ai-memory_

- **lexigram-ai-memory** `exceptions.py:47` class → `(MemorySystemError)`
- **lexigram-contracts** `data/vector/exceptions.py:29` class → `(VectorError)`

### `Entity`
_Canonical in lexigram (domain/models/entity.py); specialized in lexigram-ai-rag, lexigram-events, lexigram-sql_

- **lexigram** `domain/models/entity.py:14` class → `(DomainModel, Generic)`
- **lexigram-ai-rag** `knowledge_graph/types.py:32` class
- **lexigram-events** `aggregates/entity.py:16` class → `(BaseEntity, ABC)`
- **lexigram-sql** `types.py:135` class → `(DomainModel)`

### `Environment`
_Canonical in lexigram-contracts (core/config.py); specialized in lexigram-cli_

- **lexigram-cli** `registry/environment.py:26` class → `(ABC)`
- **lexigram-contracts** `core/config.py:18` class → `(StrEnum)`

### `EvaluationResult`
_Canonical in lexigram-contracts (ai/evaluation.py); specialized in lexigram-ai-rag_

- **lexigram-ai-rag** `evaluation/types.py:44` class
- **lexigram-contracts** `ai/evaluation.py:25` class

### `EventHandlerProtocol`
_Canonical in lexigram-contracts (events/protocols.py); specialized in lexigram-events_

- **lexigram-contracts** `events/protocols.py:37` class → `(Protocol)`
- **lexigram-events** `handlers/base.py:94` class → `(ABC, Generic)`

### `ExecutionContextProtocol`
_Canonical in lexigram-contracts (web/execution_context.py); specialized in lexigram-graphql_

- **lexigram-contracts** `web/execution_context.py:16` class → `(Protocol)`
- **lexigram-graphql** `core/execution.py:48` class

### `ExtractionError`
_Canonical in lexigram-contracts (ai/exceptions.py); specialized in lexigram-ai-llm_

- **lexigram-ai-llm** `exceptions.py:116` class → `(_ContractsExtractionError)`
- **lexigram-contracts** `ai/exceptions.py:110` class → `(AIError)`

### `FieldError`
_Canonical in lexigram-contracts (exceptions/domain.py); specialized in lexigram-admin, lexigram-ui_

- **lexigram-admin** `schema/exceptions.py:4` class → `(Exception)`
- **lexigram-contracts** `exceptions/domain.py:100` class → `(DomainError)`
- **lexigram-ui** `exceptions.py:42` class

### `FieldIn`
_Canonical in lexigram-contracts (data/types.py); specialized in lexigram-sql_

- **lexigram-contracts** `data/types.py:59` class
- **lexigram-sql** `specification/sql.py:137` class → `(SqlSpecification)`

### `FileInfo`
_Canonical in lexigram-contracts (infra/storage/models.py); specialized in lexigram-testing_

- **lexigram-contracts** `infra/storage/models.py:14` class
- **lexigram-testing** `memory/blob_store.py:20` class

### `Filter`
_Canonical in lexigram-contracts (data/vector/filters.py); specialized in lexigram-admin, lexigram-sql_

- **lexigram-admin** `ui/filters/base.py:30` class → `(AbstractField)`
- **lexigram-contracts** `data/vector/filters.py:48` class
- **lexigram-sql** `repositories/filter_objects.py:27` class

### `FilterOperator`
_Canonical in lexigram-contracts (data/vector/filters.py); specialized in lexigram-admin, lexigram-events, lexigram-search_

- **lexigram-admin** `data/query.py:21` class → `(StrEnum)`
- **lexigram-contracts** `data/vector/filters.py:12` class → `(StrEnum)`
- **lexigram-events** `constants.py:100` class → `(StrEnum)`
- **lexigram-search** `filterset/types.py:17` class → `(str, Enum)`

### `FlagEvaluation`
_Canonical in lexigram-contracts (feature_flags/models.py); specialized in lexigram-features_

- **lexigram-contracts** `feature_flags/models.py:31` class
- **lexigram-features** `types.py:158` class

### `FlagType`
_Canonical in lexigram-contracts (feature_flags/models.py); specialized in lexigram-features_

- **lexigram-contracts** `feature_flags/models.py:14` class → `(StrEnum)`
- **lexigram-features** `types.py:25` class → `(StrEnum)`

### `FunctionCall`
_Canonical in lexigram-contracts (ai/llm.py); specialized in lexigram-ai-llm_

- **lexigram-ai-llm** `structured/typed_responses.py:34` class
- **lexigram-contracts** `ai/llm.py:522` class

### `GraphPath`
_Canonical in lexigram-contracts (data/graph/types.py); specialized in lexigram-ai-rag_

- **lexigram-ai-rag** `knowledge_graph/types.py:70` class
- **lexigram-contracts** `data/graph/types.py:40` class

### `GraphQLExecutorProtocol`
_Canonical in lexigram-contracts (graphql/protocols.py); specialized in lexigram-graphql_

- **lexigram-contracts** `graphql/protocols.py:29` class → `(Protocol)`
- **lexigram-graphql** `core/execution.py:90` class

### `GuardError`
_Canonical in lexigram-contracts (ai/exceptions.py); specialized in lexigram-ai-guard_

- **lexigram-ai-guard** `exceptions.py:8` class → `(_ContractsGuardError)`
- **lexigram-contracts** `ai/exceptions.py:97` class → `(AIError)`

### `HealthStatus`
_Canonical in lexigram-contracts (core/health.py); specialized in lexigram-admin, lexigram-events, lexigram-sql_

- **lexigram-admin** `monitoring/integration.py:87` variable = `_HealthStatus`
- **lexigram-contracts** `core/health.py:30` class → `(StrEnum)`
- **lexigram-events** `constants.py:53` class → `(StrEnum)`
- **lexigram-sql** `monitoring/metrics.py:70` class

### `HookRegistry`
_Canonical in lexigram (hooks/registry.py); specialized in lexigram-cli_

- **lexigram** `hooks/registry.py:19` class
- **lexigram-cli** `registry/hook.py:122` class

### `IdempotencyStatus`
_Canonical in lexigram-contracts (domain/idempotency.py); specialized in lexigram-resilience_

- **lexigram-contracts** `domain/idempotency.py:13` class → `(StrEnum)`
- **lexigram-resilience** `types.py:40` class → `(StrEnum)`

### `IdempotentCommand`
_Canonical in lexigram-contracts (events/messages.py); specialized in lexigram-events_

- **lexigram-contracts** `events/messages.py:212` class → `(Command)`
- **lexigram-events** `messages/command.py:43` class → `(_IdempotentCommand, Command)`

### `IdentityResolverProtocol`
_Canonical in lexigram-contracts (auth/identity.py); specialized in lexigram-auth_

- **lexigram-auth** `protocols.py:24` class → `(Protocol)`
- **lexigram-contracts** `auth/identity.py:12` class → `(Protocol)`

### `InputSanitizer`
_Canonical in lexigram (security/sanitization/sanitizer.py); specialized in lexigram-ai-prompt_

- **lexigram** `security/sanitization/sanitizer.py:21` class → `(InputSanitizerProtocol)`
- **lexigram-ai-prompt** `rendering/sanitizer.py:39` class

### `IntegrityError`
_Canonical in lexigram-contracts (exceptions/infra.py); specialized in lexigram-sql_

- **lexigram-contracts** `exceptions/infra.py:99` class → `(DatabaseError)`
- **lexigram-sql** `exceptions.py:135` class → `(DatabaseError)`

### `InterceptorChain`
_Canonical in lexigram (di/extensions/interceptors.py); specialized in lexigram-web_

- **lexigram** `di/extensions/interceptors.py:70` class
- **lexigram-web** `interceptors/pipeline.py:37` class → `(CallHandlerProtocol)`

### `JSON`
_Canonical in lexigram-contracts (core/types.py); specialized in lexigram-graphql_

- **lexigram-contracts** `core/types.py:36` variable = `...`
- **lexigram-graphql** `scalars/json.py:8` class

### `JSONOutputParser`
_Canonical in lexigram-contracts (ai/parsers.py); specialized in lexigram-ai-llm_

- **lexigram-ai-llm** `parsers/json.py:16` class
- **lexigram-contracts** `ai/parsers.py:39` class → `(BaseOutputParser)`

### `JobProtocol`
_Canonical in lexigram-contracts (infra/tasks/protocols.py); specialized in lexigram-tasks_

- **lexigram-contracts** `infra/tasks/protocols.py:15` class → `(Protocol)`
- **lexigram-tasks** `models/job.py:81` class

### `JobTemplateProtocol`
_Canonical in lexigram-contracts (infra/tasks/protocols.py); specialized in lexigram-tasks_

- **lexigram-contracts** `infra/tasks/protocols.py:319` class → `(Protocol)`
- **lexigram-tasks** `scheduling/templates.py:15` class

### `LLMClientProtocol`
_Canonical in lexigram-contracts (ai/llm.py); specialized in lexigram-ai-rag_

- **lexigram-ai-rag** `evaluation/types.py:11` variable = `Any`
- **lexigram-contracts** `ai/llm.py:61` class → `(Protocol)`

### `LLMError`
_Canonical in lexigram-contracts (ai/exceptions.py); specialized in lexigram-ai-llm_

- **lexigram-ai-llm** `exceptions.py:30` class → `(_ContractsLLMError)`
- **lexigram-contracts** `ai/exceptions.py:32` class → `(AIError)`

### `LockAcquisitionError`
_Canonical in lexigram-contracts (exceptions/components.py); specialized in lexigram-admin, lexigram-cache_

- **lexigram-admin** `core/distributed_lock.py:48` class → `(LockError)`
- **lexigram-cache** `exceptions.py:151` class → `(CacheError)`
- **lexigram-contracts** `exceptions/components.py:99` class → `(LockError, ComponentError)`

### `LockConflictError`
_Canonical in lexigram-contracts (exceptions/infra.py); specialized in lexigram-admin_

- **lexigram-admin** `services/collaborative.py:127` class → `(RuntimeError)`
- **lexigram-contracts** `exceptions/infra.py:46` class → `(LockError)`

### `LockError`
_Canonical in lexigram-contracts (exceptions/infra.py); specialized in lexigram-admin, lexigram-sql_

- **lexigram-admin** `core/distributed_lock.py:39` class → `(CoreLockError)`
- **lexigram-contracts** `exceptions/infra.py:37` class → `(InfrastructureError)`
- **lexigram-sql** `exceptions.py:249` class → `(DatabaseError)`

### `LogLevel`
_Canonical in lexigram (logging/types.py); specialized in lexigram-sql_

- **lexigram** `logging/types.py:11` class → `(StrEnum)`
- **lexigram-sql** `types.py:125` variable = `str`

### `LoggingConfig`
_Canonical in lexigram (logging/config/models.py); specialized in lexigram-monitor_

- **lexigram** `logging/config/models.py:13` class → `(BaseConfig)`
- **lexigram-monitor** `config.py:184` class → `(BaseConfig)`

### `LoggingMiddleware`
_Canonical in lexigram (middleware/builtins/observability.py); specialized in lexigram-events, lexigram-graphql, lexigram-tasks_

- **lexigram** `middleware/builtins/observability.py:49` class
- **lexigram-events** `middleware/logging.py:16` class → `(AbstractMiddleware)`
- **lexigram-graphql** `core/middleware.py:117` class → `(AbstractMiddleware)`
- **lexigram-tasks** `middleware/core.py:127` class → `(TaskMiddleware)`

### `MappingError`
_Canonical in lexigram (mapping/exceptions.py); specialized in lexigram-sql_

- **lexigram** `mapping/exceptions.py:12` class → `(LexigramError)`
- **lexigram-contracts** `exceptions/domain.py:82` class → `(LexigramError)`
- **lexigram-sql** `mappers/base.py:15` class → `(CoreMappingError)`

### `MetricProtocol`
_Canonical in lexigram-contracts (observability/metrics.py); specialized in lexigram-admin, lexigram-ui_

- **lexigram-admin** `ui/observability.py:38` class
- **lexigram-contracts** `observability/metrics.py:197` class → `(Protocol)`
- **lexigram-ui** `performance/observability.py:28` class

### `MetricsCollectorProtocol`
_Canonical in lexigram-contracts (observability/metrics.py); specialized in lexigram-admin, lexigram-graphql, lexigram-monitor, lexigram-web_

- **lexigram-admin** `ui/observability.py:48` class
- **lexigram-contracts** `observability/metrics.py:257` class → `(MetricsRecorderProtocol, MetricsFactoryProtocol, Protocol)`
- **lexigram-graphql** `monitoring/metrics.py:134` class
- **lexigram-monitor** `metrics/collector.py:10` class
- **lexigram-web** `middleware/metrics.py:50` class → `(Protocol)`

### `MiddlewareChain`
_Canonical in lexigram (middleware/core/chain.py); specialized in lexigram-events, lexigram-web_

- **lexigram** `middleware/core/chain.py:28` class
- **lexigram-events** `middleware/base.py:61` class → `(Generic)`
- **lexigram-web** `middleware/base.py:49` class

### `MiddlewarePipeline`
_Canonical in lexigram (app/pipeline.py); specialized in lexigram-graphql_

- **lexigram** `app/pipeline.py:36` class
- **lexigram-graphql** `core/middleware.py:247` class

### `MiddlewareRegistry`
_Canonical in lexigram (middleware/core/registry.py); specialized in lexigram-web_

- **lexigram** `middleware/core/registry.py:31` class → `(Registry)`
- **lexigram-web** `middleware/base.py:71` class

### `MigrationContext`
_Canonical in lexigram-contracts (tenancy/migration.py); specialized in lexigram-sql_

- **lexigram-contracts** `tenancy/migration.py:42` class
- **lexigram-sql** `migrations/manager.py:52` variable = `None`

### `MigrationRecord`
_Canonical in lexigram-contracts (data/sql/database.py); specialized in lexigram-nosql, lexigram-sql_

- **lexigram-contracts** `data/sql/database.py:482` class
- **lexigram-nosql** `migration/manager.py:26` class
- **lexigram-sql** `migrations/base.py:97` class

### `MultiEventHandlerProtocol`
_Canonical in lexigram-contracts (events/protocols.py); specialized in lexigram-events_

- **lexigram-contracts** `events/protocols.py:54` class → `(Protocol)`
- **lexigram-events** `handlers/base.py:129` class → `(ABC)`

### `NodeResult`
_Canonical in lexigram-contracts (data/graph/types.py); specialized in lexigram-workflow_

- **lexigram-contracts** `data/graph/types.py:85` class
- **lexigram-workflow** `types.py:21` class

### `NotFoundError`
_Canonical in lexigram-contracts (exceptions/domain.py); specialized in lexigram-admin, lexigram-events, lexigram-graphql, lexigram-web_

- **lexigram-admin** `exceptions.py:29` class → `(DomainError)`
- **lexigram-contracts** `exceptions/domain.py:19` class → `(DomainError)`
- **lexigram-events** `exceptions.py:34` variable = `_BaseNotFoundError`
- **lexigram-graphql** `exceptions.py:115` class → `(GraphQLError)`
- **lexigram-web** `exceptions.py:39` class → `(HTTPError)`

### `NotificationError`
_Canonical in lexigram-contracts (notification/errors.py); specialized in lexigram-admin_

- **lexigram-admin** `exceptions.py:69` class → `(DomainError)`
- **lexigram-contracts** `notification/errors.py:11` class → `(DomainError)`

### `ObservabilityProvider`
_Canonical in lexigram (observability/di/sub_providers/observability.py); specialized in lexigram-ai-observability, lexigram-monitor_

- **lexigram** `observability/di/sub_providers/observability.py:25` class → `(Provider)`
- **lexigram-ai-observability** `di/provider.py:35` class → `(Provider)`
- **lexigram-monitor** `di/sub_providers/observability.py:30` class → `(Provider)`

### `OutboxStatus`
_Canonical in lexigram-contracts (events/outbox.py); specialized in lexigram-testing_

- **lexigram-contracts** `events/outbox.py:24` class → `(StrEnum)`
- **lexigram-testing** `memory/outbox.py:52` class → `(StrEnum)`

### `PaginatedQuery`
_Canonical in lexigram-contracts (events/messages.py); specialized in lexigram-events_

- **lexigram-contracts** `events/messages.py:172` class → `(Query)`
- **lexigram-events** `messages/query.py:18` class → `(_PaginatedQuery)`

### `PermissionDeniedError`
_Canonical in lexigram-contracts (exceptions/domain.py); specialized in lexigram-admin_

- **lexigram-admin** `exceptions.py:35` class → `(DomainError)`
- **lexigram-contracts** `exceptions/domain.py:28` class → `(DomainError)`

### `PipelineContext`
_Canonical in lexigram (primitives/pipeline.py); specialized in lexigram-ai-rag_

- **lexigram** `primitives/pipeline.py:48` class
- **lexigram-ai-rag** `pipeline/types.py:74` class

### `PolicyStoreProtocol`
_Canonical in lexigram-contracts (auth/policy.py); specialized in lexigram-auth_

- **lexigram-auth** `policies/store.py:12` class → `(Protocol)`
- **lexigram-contracts** `auth/policy.py:17` class → `(Protocol)`

### `Priority`
_Canonical in lexigram (primitives/types.py); specialized in lexigram-tasks_

- **lexigram** `primitives/types.py:16` variable = `int`
- **lexigram-tasks** `types.py:13` class → `(IntEnum)`

### `ProjectionProtocol`
_Canonical in lexigram-contracts (events/protocols.py); specialized in lexigram-events_

- **lexigram-contracts** `events/protocols.py:403` class → `(Protocol)`
- **lexigram-events** `projections/base.py:42` class → `(ABC)`

### `PromptTemplate`
_Canonical in lexigram-contracts (ai/prompt.py); specialized in lexigram-ai-prompt_

- **lexigram-ai-prompt** `service/models.py:35` class
- **lexigram-contracts** `ai/prompt.py:14` class

### `ProtocolValidationError`
_Canonical in lexigram-contracts (exceptions/container.py); specialized in lexigram-sql_

- **lexigram-contracts** `exceptions/container.py:94` class → `(ContainerError)`
- **lexigram-sql** `validation/protocols.py:23` class → `(ConfigurationError)`

### `Provider`
_Canonical in lexigram (di/provider.py); specialized in lexigram-cli_

- **lexigram** `di/provider.py:80` class
- **lexigram-cli** `registry/provider.py:25` class → `(ABC)`

### `ProviderRegistry`
_Canonical in lexigram (di/orchestrator/registry.py); specialized in lexigram-ai-llm, lexigram-cli_

- **lexigram** `di/orchestrator/registry.py:18` class
- **lexigram-ai-llm** `registry/core.py:85` class → `(Registry)`
- **lexigram-cli** `registry/provider.py:480` class

### `PydanticOutputParser`
_Canonical in lexigram-contracts (ai/parsers.py); specialized in lexigram-ai-llm_

- **lexigram-ai-llm** `parsers/pydantic.py:22` class
- **lexigram-contracts** `ai/parsers.py:76` class → `(BaseOutputParser)`

### `Query`
_Canonical in lexigram-contracts (events/messages.py); specialized in lexigram-sql_

- **lexigram-contracts** `events/messages.py:163` class → `(Message, Generic)`
- **lexigram-sql** `query/builder.py:34` class

### `QueryHandlerProtocol`
_Canonical in lexigram-contracts (events/protocols.py); specialized in lexigram-events_

- **lexigram-contracts** `events/protocols.py:209` class → `(Protocol)`
- **lexigram-events** `handlers/base.py:60` class → `(ABC, Generic)`

### `QueryResult`
_Canonical in lexigram-contracts (data/sql/database.py); specialized in lexigram-admin, lexigram-cli, lexigram-events_

- **lexigram-admin** `data/data_source.py:15` class → `(Generic)`
- **lexigram-cli** `registry/database.py:24` class
- **lexigram-contracts** `data/sql/database.py:40` class
- **lexigram-events** `types.py:206` class → `(DomainModel)`

### `RAGError`
_Canonical in lexigram-contracts (ai/exceptions.py); specialized in lexigram-ai-rag_

- **lexigram-ai-rag** `exceptions.py:9` class → `(_ContractsRAGError)`
- **lexigram-contracts** `ai/exceptions.py:45` class → `(AIError)`

### `RAGSearchResult`
_Canonical in lexigram-contracts (ai/vector.py); specialized in lexigram-search_

- **lexigram-contracts** `ai/vector.py:232` class
- **lexigram-search** `types.py:64` variable = `SearchResult`

### `RateLimitError`
_Canonical in lexigram-contracts (exceptions/domain.py); specialized in lexigram-graphql, lexigram-web_

- **lexigram-contracts** `exceptions/domain.py:55` class → `(DomainError)`
- **lexigram-graphql** `exceptions.py:124` class → `(GraphQLError)`
- **lexigram-web** `exceptions.py:190` class → `(HTTPError)`

### `RequestContext`
_Canonical in lexigram (primitives/context.py); specialized in lexigram-http_

- **lexigram** `primitives/context.py:250` class
- **lexigram-http** `types.py:10` class

### `RetryExhaustedError`
_Canonical in lexigram-contracts (exceptions/resilience.py); specialized in lexigram-resilience_

- **lexigram-contracts** `exceptions/resilience.py:55` class → `(RetryError)`
- **lexigram-resilience** `exceptions.py:26` class → `(RetryError)`

### `RetryMiddleware`
_Canonical in lexigram (middleware/builtins/resilience.py); specialized in lexigram-events_

- **lexigram** `middleware/builtins/resilience.py:23` class
- **lexigram-events** `middleware/retry.py:22` class → `(AbstractMiddleware)`

### `RunnableLambda`
_Canonical in lexigram-contracts (ai/runnable.py); specialized in lexigram-ai-llm_

- **lexigram-ai-llm** `runnable/lambda_.py:18` class
- **lexigram-contracts** `ai/runnable.py:116` class

### `RunnableParallel`
_Canonical in lexigram-contracts (ai/runnable.py); specialized in lexigram-ai-llm_

- **lexigram-ai-llm** `runnable/parallel.py:11` class
- **lexigram-contracts** `ai/runnable.py:93` class

### `SagaManagerProtocol`
_Canonical in lexigram-contracts (workflow/protocols.py); specialized in lexigram-events_

- **lexigram-contracts** `workflow/protocols.py:295` class → `(Protocol)`
- **lexigram-events** `sagas/manager.py:62` class

### `SagaState`
_Canonical in lexigram-contracts (workflow/protocols.py); specialized in lexigram-events_

- **lexigram-contracts** `workflow/protocols.py:98` class → `(StrEnum)`
- **lexigram-events** `types.py:29` class → `(StrEnum)`

### `SchemaBuilderProtocol`
_Canonical in lexigram-contracts (graphql/protocols.py); specialized in lexigram-graphql_

- **lexigram-contracts** `graphql/protocols.py:65` class → `(Protocol)`
- **lexigram-graphql** `schema/builder.py:20` class

### `Scope`
_Canonical in lexigram (di/container/scope.py); specialized in lexigram-admin_

- **lexigram** `di/container/scope.py:33` class
- **lexigram-admin** `core/decorators.py:41` class → `(str, Enum)`

### `SearchQuery`
_Canonical in lexigram-contracts (data/vector/types.py); specialized in lexigram-search_

- **lexigram-contracts** `data/vector/types.py:29` class
- **lexigram-search** `engine/engine.py:45` class

### `SearchResult`
_Canonical in lexigram-contracts (data/vector/types.py); specialized in lexigram-admin, lexigram-search, lexigram-vector_

- **lexigram-admin** `services/search_service.py:10` class
- **lexigram-contracts** `data/vector/types.py:41` class
- **lexigram-search** `types.py:20` class → `(DomainModel, SearchIndexResult)`
- **lexigram-vector** `adapters/vector_store.py:33` variable = `RAGSearchResult`

### `SecretAccessError`
_Canonical in lexigram (security/exceptions.py); specialized in lexigram-secrets_

- **lexigram** `security/exceptions.py:33` class → `(SecretError)`
- **lexigram-contracts** `exceptions/security.py:75` class → `(SecurityError)`
- **lexigram-secrets** `exceptions.py:46` class → `(SecretsError)`

### `SecretNotFoundError`
_Canonical in lexigram (security/exceptions.py); specialized in lexigram-secrets_

- **lexigram** `security/exceptions.py:27` class → `(SecretError)`
- **lexigram-contracts** `exceptions/components.py:86` class → `(NotFoundError, ComponentError)`
- **lexigram-secrets** `exceptions.py:36` class → `(SecretsError)`

### `SecretRotatedEvent`
_Canonical in lexigram (security/events.py); specialized in lexigram-secrets_

- **lexigram** `security/events.py:37` class → `(DomainEvent)`
- **lexigram-secrets** `events.py:25` class → `(DomainEvent)`

### `SecurityConfig`
_Canonical in lexigram (security/config.py); specialized in lexigram-web_

- **lexigram** `security/config.py:47` class → `(BaseConfig)`
- **lexigram-web** `security/config.py:411` class → `(BaseConfig)`

### `SecurityError`
_Canonical in lexigram (security/exceptions.py); specialized in lexigram-events_

- **lexigram** `security/exceptions.py:15` class → `(LexigramError)`
- **lexigram-contracts** `exceptions/security.py:14` class → `(LexigramError)`
- **lexigram-events** `exceptions.py:267` class → `(EventError)`

### `SelectionStrategy`
_Canonical in lexigram-contracts (ai/providers.py); specialized in lexigram-ai-llm_

- **lexigram-ai-llm** `selection/core.py:62` class → `(DomainModel)`
- **lexigram-contracts** `ai/providers.py:18` class → `(StrEnum)`

### `SerializationError`
_Canonical in lexigram (exceptions.py); specialized in lexigram-sql_

- **lexigram** `exceptions.py:109` class → `(LexigramException)`
- **lexigram-contracts** `exceptions/domain.py:73` class → `(LexigramError)`
- **lexigram-sql** `exceptions.py:205` class → `(TransactionError)`

### `SerializerRegistry`
_Canonical in lexigram (serialization/registry/registry.py); specialized in lexigram-cli_

- **lexigram** `serialization/registry/registry.py:18` class
- **lexigram-cli** `registry/serializer.py:205` class

### `ServerSentEvent`
_Canonical in lexigram-contracts (web/sse.py); specialized in lexigram-ai-llm, lexigram-web_

- **lexigram-ai-llm** `streaming/sse_adapter.py:18` class
- **lexigram-contracts** `web/sse.py:37` class
- **lexigram-web** `transport/sse.py:17` class

### `SessionError`
_Canonical in lexigram-contracts (ai/session.py); specialized in lexigram-ai-session_

- **lexigram-ai-session** `exceptions.py:8` class → `(_ContractsSessionError)`
- **lexigram-contracts** `ai/session.py:20` class → `(LexigramError)`

### `SpecificationProtocol`
_Canonical in lexigram-contracts (domain/specification.py); specialized in lexigram-admin_

- **lexigram-admin** `domain/specifications.py:10` class → `(Generic)`
- **lexigram-contracts** `domain/specification.py:11` class → `(Protocol)`

### `StepResult`
_Canonical in lexigram-contracts (workflow/protocols.py); specialized in lexigram-tasks_

- **lexigram-contracts** `workflow/protocols.py:16` variable = `...`
- **lexigram-tasks** `workflows/core.py:56` class

### `StorageError`
_Canonical in lexigram-contracts (ai/memory.py); specialized in lexigram-storage_

- **lexigram-contracts** `ai/memory.py:109` class → `(AIMemoryError)`
- **lexigram-storage** `exceptions.py:8` class → `(LexigramError)`

### `StreamChunk`
_Canonical in lexigram-contracts (ai/llm.py); specialized in lexigram-ai-llm_

- **lexigram-ai-llm** `types.py:104` class → `(DomainModel)`
- **lexigram-contracts** `ai/llm.py:548` class

### `Table`
_Canonical in lexigram-contracts (data/identifiers.py); specialized in lexigram-sql_

- **lexigram-contracts** `data/identifiers.py:242` class → `(Identifier)`
- **lexigram-sql** `lib/helpers.py:20` function

### `TaskCancelledError`
_Canonical in lexigram-contracts (ai/session.py); specialized in lexigram-tasks_

- **lexigram-contracts** `ai/session.py:26` class → `(LexigramError)`
- **lexigram-tasks** `exceptions.py:53` class → `(TaskError)`

### `TaskError`
_Canonical in lexigram-contracts (ai/session.py); specialized in lexigram-tasks_

- **lexigram-contracts** `ai/session.py:32` class → `(LexigramError)`
- **lexigram-tasks** `exceptions.py:35` class → `(TaskQueueError)`

### `TaskTimeoutError`
_Canonical in lexigram-contracts (ai/session.py); specialized in lexigram-tasks_

- **lexigram-contracts** `ai/session.py:38` class → `(TaskError)`
- **lexigram-tasks** `exceptions.py:47` class → `(TaskError)`

### `TaskValidationError`
_Canonical in lexigram-contracts (ai/session.py); specialized in lexigram-tasks_

- **lexigram-contracts** `ai/session.py:44` class → `(TaskError)`
- **lexigram-tasks** `exceptions.py:75` class → `(TaskError)`

### `TenantNotFoundError`
_Canonical in lexigram-contracts (tenancy/errors.py); specialized in lexigram-admin_

- **lexigram-admin** `multitenancy/models.py:38` class → `(KeyError)`
- **lexigram-contracts** `tenancy/errors.py:25` class → `(TenantError)`

### `TimeoutMiddleware`
_Canonical in lexigram (middleware/builtins/resilience.py); specialized in lexigram-tasks_

- **lexigram** `middleware/builtins/resilience.py:80` class
- **lexigram-tasks** `middleware/core.py:219` class → `(TaskMiddleware)`

### `Timestamp`
_Canonical in lexigram-contracts (core/types.py); specialized in lexigram-graphql_

- **lexigram-contracts** `core/types.py:49` variable = `datetime`
- **lexigram-graphql** `scalars/timestamp.py:6` class

### `TimingMiddleware`
_Canonical in lexigram (middleware/builtins/observability.py); specialized in lexigram-web_

- **lexigram** `middleware/builtins/observability.py:17` class
- **lexigram-web** `middleware/timing.py:12` class

### `TokenError`
_Canonical in lexigram-contracts (auth/exceptions.py); specialized in lexigram-auth_

- **lexigram-auth** `exceptions.py:90` class → `(InvalidCredentialsError)`
- **lexigram-contracts** `auth/exceptions.py:46` class → `(DomainError)`

### `TracerProtocol`
_Canonical in lexigram-contracts (observability/tracing.py); specialized in lexigram-ai-observability_

- **lexigram-ai-observability** `tracing/core.py:31` variable = `Tracer`
- **lexigram-contracts** `observability/tracing.py:15` class → `(Protocol)`

### `TracingError`
_Canonical in lexigram-contracts (observability/ai.py); specialized in lexigram-ai-observability_

- **lexigram-ai-observability** `exceptions.py:26` class → `(ObservabilityError)`
- **lexigram-contracts** `observability/ai.py:17` class → `(LexigramError)`

### `UnitOfWorkError`
_Canonical in lexigram-contracts (data/exceptions.py); specialized in lexigram-sql_

- **lexigram-contracts** `data/exceptions.py:11` class → `(LexigramError)`
- **lexigram-sql** `exceptions.py:312` class → `(DatabaseError)`

### `UnitOfWorkProtocol`
_Canonical in lexigram-contracts (data/sql/unit_of_work.py); specialized in lexigram-sql_

- **lexigram-contracts** `data/sql/unit_of_work.py:16` class → `(Protocol)`
- **lexigram-sql** `api/protocols.py:35` class → `(Protocol)`

### `UserProtocol`
_Canonical in lexigram-contracts (auth/user.py); specialized in lexigram-auth_

- **lexigram-auth** `authz/service.py:72` class → `(Protocol)`
- **lexigram-contracts** `auth/user.py:12` class → `(Protocol)`

### `UserSession`
_Canonical in lexigram-contracts (auth/models.py); specialized in lexigram-auth_

- **lexigram-auth** `models/session.py:11` class
- **lexigram-contracts** `auth/models.py:27` class

### `UserStoreProtocol`
_Canonical in lexigram-contracts (auth/store.py); specialized in lexigram-auth_

- **lexigram-auth** `storage/token_store.py:49` class → `(Protocol)`
- **lexigram-contracts** `auth/store.py:121` class → `(UserReaderProtocol, UserWriterProtocol, Protocol)`

### `ValidationError`
_Canonical in lexigram (exceptions.py); specialized in lexigram-admin, lexigram-search_

- **lexigram** `exceptions.py:96` class → `(LexigramException)`
- **lexigram-admin** `forms/validation.py:17` class
- **lexigram-contracts** `exceptions/domain.py:135` class → `(DomainError)`
- **lexigram-search** `query/filters.py:16` variable = `SearchValidationError`

### `ValidationMiddleware`
_Canonical in lexigram (middleware/builtins/validation.py); specialized in lexigram-events_

- **lexigram** `middleware/builtins/validation.py:69` class
- **lexigram-events** `middleware/validation.py:19` class → `(AbstractMiddleware)`

### `ValidationResult`
_Canonical in lexigram-contracts (core/validation.py); specialized in lexigram-admin, lexigram-graphql_

- **lexigram-admin** `forms/async_validation.py:50` class
- **lexigram-contracts** `core/validation.py:19` variable = `...`
- **lexigram-graphql** `core/validation.py:23` class

### `ValueObject`
_Canonical in lexigram (domain/models/value_object.py); specialized in lexigram-events_

- **lexigram** `domain/models/value_object.py:12` class → `(DomainModel)`
- **lexigram-events** `aggregates/value_object.py:15` class → `(BaseValueObject, ABC)`

### `VectorError`
_Canonical in lexigram-contracts (data/vector/exceptions.py); specialized in lexigram-vector_

- **lexigram-contracts** `data/vector/exceptions.py:13` class → `(InfrastructureError)`
- **lexigram-vector** `exceptions.py:8` class → `(InfrastructureError)`

### `VectorProvider`
_Canonical in lexigram-contracts (ai/types.py); specialized in lexigram-vector_

- **lexigram-contracts** `ai/types.py:49` class → `(StrEnum)`
- **lexigram-vector** `di/provider.py:30` class → `(Provider)`

### `VectorStoreProtocol`
_Canonical in lexigram-contracts (data/vector/protocols.py); specialized in lexigram-ai-rag_

- **lexigram-ai-rag** `reasoning/strategy_registry.py:15` variable = `DocumentVectorStoreProtocol`
- **lexigram-contracts** `data/vector/protocols.py:26` class → `(Protocol)`

### `WebProviderProtocol`
_Canonical in lexigram-contracts (web/protocols.py); specialized in lexigram-web_

- **lexigram-contracts** `web/protocols.py:440` class → `(ProviderProtocol, Protocol)`
- **lexigram-web** `protocols.py:304` class → `(WebAppAccessorProtocol, ControllerSourceProtocol, ConfigAccessorProtocol, ProviderResourcesProtocol, Protocol)`

### `WorkflowError`
_Canonical in lexigram-contracts (ai/exceptions.py); specialized in lexigram-tasks, lexigram-workflow_

- **lexigram-contracts** `ai/exceptions.py:124` class → `(AIError)`
- **lexigram-tasks** `workflows/core.py:39` class → `(Exception)`
- **lexigram-workflow** `exceptions.py:35` class → `(PipelineExecutionError)`

### `WorkflowResult`
_Canonical in lexigram-contracts (ai/workflow.py); specialized in lexigram-tasks_

- **lexigram-contracts** `ai/workflow.py:19` class
- **lexigram-tasks** `workflows/core.py:67` class

### `build_json_schema`
_Canonical in lexigram (serialization/schema/schema.py); specialized in lexigram-ai-llm_

- **lexigram** `serialization/schema/schema.py:54` function
- **lexigram-ai-llm** `structured/parser.py:234` function

### `create_app`
_Canonical in lexigram (app/factory.py); specialized in lexigram-admin, lexigram-cli_

- **lexigram** `app/factory.py:22` function
- **lexigram-admin** `bootstrap/factory.py:27` function
- **lexigram-cli** `templates/project/full/src/{{ package_name }}/app.py:11` function

### `delete`
_Canonical in lexigram-contracts (web/routing.py); specialized in lexigram-web_

- **lexigram-contracts** `web/routing.py:88` function
- **lexigram-web** `routing/decorators.py:104` function

### `generate_device_id`
_Canonical in lexigram-contracts (auth/fingerprint.py); specialized in lexigram-auth_

- **lexigram-auth** `session/fingerprint.py:11` function
- **lexigram-contracts** `auth/fingerprint.py:18` function

### `get`
_Canonical in lexigram-contracts (web/routing.py); specialized in lexigram-admin, lexigram-web_

- **lexigram-admin** `integrations/__init__.py:24` function
- **lexigram-contracts** `web/routing.py:49` function
- **lexigram-web** `routing/decorators.py:49` function

### `injectable`
_Canonical in lexigram (di/decorators.py); specialized in lexigram-admin, lexigram-web_

- **lexigram** `di/decorators.py:92` function
- **lexigram-admin** `core/decorators.py:132` function
- **lexigram-web** `quickstart/core.py:87` function

### `max_length`
_Canonical in lexigram (validation/rules/rules.py); specialized in lexigram-admin_

- **lexigram** `validation/rules/rules.py:227` function
- **lexigram-admin** `forms/validation.py:196` function

### `min_length`
_Canonical in lexigram (validation/rules/rules.py); specialized in lexigram-admin_

- **lexigram** `validation/rules/rules.py:222` function
- **lexigram-admin** `forms/validation.py:185` function

### `patch`
_Canonical in lexigram-contracts (web/routing.py); specialized in lexigram-web_

- **lexigram-contracts** `web/routing.py:101` function
- **lexigram-web** `routing/decorators.py:117` function

### `post`
_Canonical in lexigram-contracts (web/routing.py); specialized in lexigram-web_

- **lexigram-contracts** `web/routing.py:62` function
- **lexigram-web** `routing/decorators.py:67` function

### `put`
_Canonical in lexigram-contracts (web/routing.py); specialized in lexigram-web_

- **lexigram-contracts** `web/routing.py:75` function
- **lexigram-web** `routing/decorators.py:91` function

### `required`
_Canonical in lexigram (validation/rules/rules.py); specialized in lexigram-admin_

- **lexigram** `validation/rules/rules.py:217` function
- **lexigram-admin** `forms/validation.py:168` function

### `schema`
_Canonical in lexigram-contracts (data/identifiers.py); specialized in lexigram-cli_

- **lexigram-cli** `commands/config.py:204` function
- **lexigram-contracts** `data/identifiers.py:352` function

### `scoped`
_Canonical in lexigram (di/decorators.py); specialized in lexigram-admin_

- **lexigram** `di/decorators.py:137` function
- **lexigram-admin** `core/decorators.py:99` function

### `singleton`
_Canonical in lexigram (di/decorators.py); specialized in lexigram-admin, lexigram-web_

- **lexigram** `di/decorators.py:123` function
- **lexigram-admin** `core/decorators.py:85` function
- **lexigram-web** `quickstart/core.py:54` function

### `tool`
_Canonical in lexigram-contracts (ai/tools.py); specialized in lexigram-ai-agents, lexigram-ai-mcp_

- **lexigram-ai-agents** `decorators.py:12` function
- **lexigram-ai-mcp** `controllers/decorators.py:10` function
- **lexigram-contracts** `ai/tools.py:71` function

### `transient`
_Canonical in lexigram (di/decorators.py); specialized in lexigram-admin_

- **lexigram** `di/decorators.py:151` function
- **lexigram-admin** `core/decorators.py:113` function

### `use_guards`
_Canonical in lexigram (security/guards/decorator.py); specialized in lexigram-auth, lexigram-web_

- **lexigram** `security/guards/decorator.py:23` function
- **lexigram-auth** `web/guards.py:179` function
- **lexigram-web** `security/guards.py:124` function

### `validate_protocol`
_Canonical in lexigram (di/extensions/validator.py); specialized in lexigram-sql_

- **lexigram** `di/extensions/validator.py:10` function
- **lexigram-sql** `validation/protocols.py:59` function

### `validate_range`
_Canonical in lexigram (validation/rules/rules.py); specialized in lexigram-ai-skills_

- **lexigram** `validation/rules/rules.py:333` function
- **lexigram-ai-skills** `validation/validators.py:38` function

### `with_context`
_Canonical in lexigram (primitives/context.py); specialized in lexigram-admin_

- **lexigram** `primitives/context.py:487` function
- **lexigram-admin** `state/context.py:237` function

## ⚪ Shared constant, same value (noise) (30)

### `BACKEND_MEMORY`
_Value 'memory' in 4 packages_

- **lexigram-graph** `constants.py:21` variable = `'memory'`
- **lexigram-search** `constants.py:37` variable = `'memory'`
- **lexigram-tasks** `constants.py:34` variable = `'memory'`
- **lexigram-vector** `constants.py:41` variable = `'memory'`

### `BACKEND_MYSQL`
_Value 'mysql' in 2 packages_

- **lexigram-search** `constants.py:34` variable = `'mysql'`
- **lexigram-sql** `constants.py:59` variable = `'mysql'`

### `BACKEND_POSTGRES`
_Value 'postgres' in 3 packages_

- **lexigram-search** `constants.py:33` variable = `'postgres'`
- **lexigram-sql** `constants.py:58` variable = `'postgres'`
- **lexigram-tasks** `constants.py:37` variable = `'postgres'`

### `BACKEND_SQLITE`
_Value 'sqlite' in 2 packages_

- **lexigram-search** `constants.py:35` variable = `'sqlite'`
- **lexigram-sql** `constants.py:57` variable = `'sqlite'`

### `DEFAULT_CACHE_ENABLED`
_Value True in 2 packages_

- **lexigram-ai-skills** `constants.py:26` variable = `True`
- **lexigram-cache** `constants.py:40` variable = `True`

### `DEFAULT_ENCODING`
_Value 'utf-8' in 3 packages_

- **lexigram** `serialization/constants.py:20` variable = `'utf-8'`
- **lexigram-cache** `constants.py:192` variable = `'utf-8'`
- **lexigram-contracts** `web/http_constants.py:51` variable = `'utf-8'`

### `DEFAULT_HEALTH_CHECK_TIMEOUT`
_Value 5.0 in 3 packages_

- **lexigram** `app/constants.py:31` variable = `5.0`
- **lexigram-nosql** `constants.py:34` variable = `5.0`
- **lexigram-vector** `constants.py:23` variable = `5.0`

### `DEFAULT_PAGE_SIZE`
_Value 20 in 3 packages_

- **lexigram-search** `constants.py:23` variable = `20`
- **lexigram-sql** `constants.py:65` variable = `20`
- **lexigram-web** `constants.py:41` variable = `20`

### `DEFAULT_QUERY_LIMIT`
_Value 100 in 2 packages_

- **lexigram-graph** `constants.py:32` variable = `100`
- **lexigram-nosql** `constants.py:37` variable = `100`

### `DEFAULT_REDIS_PORT`
_Value 6379 in 2 packages_

- **lexigram-cache** `constants.py:72` variable = `6379`
- **lexigram-testing** `constants.py:27` variable = `6379`

### `DEFAULT_SHUTDOWN_TIMEOUT`
_Value 30.0 in 2 packages_

- **lexigram** `app/constants.py:28` variable = `30.0`
- **lexigram-tasks** `constants.py:26` variable = `30.0`

### `DEFAULT_SUBSCRIPTIONS_PATH`
_Value '/graphql/ws' in 2 packages_

- **lexigram-contracts** `graphql/protocols.py:17` variable = `'/graphql/ws'`
- **lexigram-graphql** `constants.py:35` variable = `'/graphql/ws'`

### `DEFAULT_TASK_TIMEOUT`
_Value 300.0 in 2 packages_

- **lexigram-ai-workers** `constants.py:25` variable = `300.0`
- **lexigram-tasks** `constants.py:27` variable = `300.0`

### `DEFAULT_TEMPERATURE`
_Value 0.7 in 2 packages_

- **lexigram-ai** `constants.py:23` variable = `0.7`
- **lexigram-ai-llm** `constants.py:37` variable = `0.7`

### `ErrorHandler`
_Value ... in 2 packages_

- **lexigram** `types.py:69` variable = `...`
- **lexigram-graphql** `types.py:309` variable = `...`

### `FlagValue`
_Value ... in 2 packages_

- **lexigram-contracts** `feature_flags/models.py:27` variable = `...`
- **lexigram-features** `types.py:48` variable = `...`

### `INSECURE_SECRET_VALUES`
_Value ... in 2 packages_

- **lexigram** `config/constants.py:42` variable = `...`
- **lexigram-storage** `constants.py:46` variable = `...`

### `Metadata`
_Value ... in 2 packages_

- **lexigram-ai-session** `types.py:10` variable = `...`
- **lexigram-contracts** `core/types.py:37` variable = `...`

### `MiddlewareFunc`
_Value ... in 2 packages_

- **lexigram-events** `buses/base.py:42` variable = `...`
- **lexigram-graphql** `types.py:308` variable = `...`

### `NextHandler`
_Value ... in 2 packages_

- **lexigram** `middleware/types.py:11` variable = `...`
- **lexigram-events** `middleware/base.py:22` variable = `...`

### `QueryParams`
_Value ... in 2 packages_

- **lexigram-contracts** `core/types.py:46` variable = `...`
- **lexigram-sql** `types.py:100` variable = `...`

### `REQUEST_ID`
_Value ... in 2 packages_

- **lexigram** `primitives/context.py:155` variable = `...`
- **lexigram-sql** `context/keys.py:16` variable = `...`

### `TEMPLATE_DIR`
_Value ... in 2 packages_

- **lexigram-cli** `commands/new.py:16` variable = `...`
- **lexigram-web** `routing/openapi_templates.py:15` variable = `...`

### `TENANT_ID`
_Value ... in 2 packages_

- **lexigram** `primitives/context.py:161` variable = `...`
- **lexigram-sql** `context/keys.py:17` variable = `...`

### `TEntity`
_Value ... in 2 packages_

- **lexigram-nosql** `repository/base.py:19` variable = `...`
- **lexigram-sql** `mappers/base.py:11` variable = `...`

### `TKey`
_Value ... in 2 packages_

- **lexigram-nosql** `repository/base.py:20` variable = `...`
- **lexigram-sql** `repositories/base.py:29` variable = `...`

### `TResult`
_Value ... in 2 packages_

- **lexigram-contracts** `core/middleware.py:16` variable = `...`
- **lexigram-events** `buses/base.py:39` variable = `...`

### `USER_ID`
_Value ... in 2 packages_

- **lexigram** `primitives/context.py:162` variable = `...`
- **lexigram-sql** `context/keys.py:18` variable = `...`

### `app`
_Value ... in 3 packages_

- **lexigram-cli** `commands/add.py:13` variable = `...`
- **lexigram-ui** `cli/add.py:12` variable = `...`
- **lexigram-web** `quickstart/core.py:319` variable = `...`

### `logger`
_Value ... in 42 packages_

- **lexigram** `app/di/provider.py:17` variable = `...`
- **lexigram-admin** `actions/bulk_manager.py:24` variable = `...`
- **lexigram-ai** `admin/pages/overview.py:12` variable = `...`
- **lexigram-ai-agents** `crew/runner.py:14` variable = `...`
- **lexigram-ai-evaluation** `di/provider.py:19` variable = `...`
- **lexigram-ai-feedback** `di/provider.py:27` variable = `...`
- **lexigram-ai-governance** `audit/query.py:26` variable = `...`
- **lexigram-ai-guard** `admin/pages/overview.py:12` variable = `...`
- **lexigram-ai-llm** `admin/pages/overview.py:12` variable = `...`
- **lexigram-ai-mcp** `adapters/agent_tools.py:16` variable = `...`
- **lexigram-ai-memory** `consolidation/consolidator.py:26` variable = `...`
- **lexigram-ai-observability** `callbacks/manager.py:15` variable = `...`
- **lexigram-ai-prompt** `assembly/assembler.py:16` variable = `...`
- **lexigram-ai-rag** `cache/manager.py:15` variable = `...`
- **lexigram-ai-session** `analytics/core.py:21` variable = `...`
- **lexigram-ai-skills** `builtin/file_operations.py:16` variable = `...`
- **lexigram-ai-workers** `adapters/loader_worker.py:23` variable = `...`
- **lexigram-audit** `admin/contributor.py:24` variable = `...`
- **lexigram-auth** `admin/contributor.py:37` variable = `...`
- **lexigram-cache** `admin/contributor.py:44` variable = `...`
- **lexigram-cli** `lib/config_gen.py:25` variable = `...`
- **lexigram-events** `adapters/adapter_wirers.py:18` variable = `...`
- **lexigram-features** `backends/cache.py:30` variable = `...`
- **lexigram-graph** `backends/neo4j/backend.py:20` variable = `...`
- **lexigram-graphql** `controllers/graphql.py:25` variable = `...`
- **lexigram-http** `client/base_url_client.py:35` variable = `...`
- **lexigram-monitor** `alerts/alerting.py:38` variable = `...`
- **lexigram-nosql** `backends/base.py:16` variable = `...`
- **lexigram-notification** `backends/push/apns.py:25` variable = `...`
- **lexigram-queue** `admin/contributor.py:34` variable = `...`
- **lexigram-resilience** `bulkhead/limiter.py:17` variable = `...`
- **lexigram-search** `analytics/recorder.py:12` variable = `...`
- **lexigram-sql** `admin/contributor.py:30` variable = `...`
- **lexigram-storage** `backends/_s3_upload_mixin.py:22` variable = `...`
- **lexigram-tasks** `admin/contributor.py:30` variable = `...`
- **lexigram-tenancy** `config_overrides/service.py:13` variable = `...`
- **lexigram-testing** `clients/auth/fixtures.py:15` variable = `...`
- **lexigram-ui** `core/base.py:10` variable = `...`
- **lexigram-vector** `adapters/document_store.py:28` variable = `...`
- **lexigram-web** `admin/contributor.py:39` variable = `...`
- **lexigram-webhook** `admin/contributor.py:24` variable = `...`
- **lexigram-workflow** `approval/chain.py:12` variable = `...`
