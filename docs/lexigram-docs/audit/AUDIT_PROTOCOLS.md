# AUDIT_PROTOCOLS.md — Lexigram Framework Protocol Inventory

> **Source**: `class *Protocol` declarations across framework source trees.

---

## Summary

- Files with protocol declarations: 154
- Total protocol declarations: 427

## Protocol Files

| File | Protocols |
|------|-----------|
| `lexigram-contracts/src/lexigram/contracts/admin/action_hooks.py` | ActionHookProtocol |
| `lexigram-contracts/src/lexigram/contracts/admin/audit_logger.py` | AdminAuditLoggerProtocol |
| `lexigram-contracts/src/lexigram/contracts/admin/authorizer.py` | AdminAuthorizerProtocol |
| `lexigram-contracts/src/lexigram/contracts/admin/cache_provider.py` | CacheProviderProtocol |
| `lexigram-contracts/src/lexigram/contracts/admin/dependencies.py` | ContributorWithDependenciesProtocol |
| `lexigram-contracts/src/lexigram/contracts/admin/operations.py` | BulkOperationsProtocol, RelationLoaderProtocol, AdminSearchableProtocol, AggregatableProtocol |
| `lexigram-contracts/src/lexigram/contracts/admin/pii_redactor.py` | PiiRedactorProtocol |
| `lexigram-contracts/src/lexigram/contracts/admin/protocols.py` | AdminContributorProtocol, AdminContributorRegistryProtocol, AdminDashboardProtocol |
| `lexigram-contracts/src/lexigram/contracts/admin/repository.py` | AdminRepositoryProtocol |
| `lexigram-contracts/src/lexigram/contracts/admin/widget_protocols.py` | WidgetHandlerProtocol |
| `lexigram-contracts/src/lexigram/contracts/ai/agents.py` | ToolProtocol, AgentProtocol, StrategyProtocol, AgentExecutorProtocol, ToolRegistryProtocol, MemoryProtocol, AgentStrategyProtocol, SkillComposerProtocol, RunnableAgentProtocol |
| `lexigram-contracts/src/lexigram/contracts/ai/callbacks.py` | CallbackHandlerProtocol, CallbackManagerProtocol |
| `lexigram-contracts/src/lexigram/contracts/ai/evaluation.py` | EvaluatorProtocol, EvaluationHarnessProtocol |
| `lexigram-contracts/src/lexigram/contracts/ai/feedback.py` | FeedbackStoreProtocol, FeedbackProtocol |
| `lexigram-contracts/src/lexigram/contracts/ai/governance/__init__.py` | CostTrackingProtocol, AIGovernanceProtocol, AIAuditStoreProtocol |
| `lexigram-contracts/src/lexigram/contracts/ai/governance/relay_billing.py` | RelayUsageStoreProtocol, RelayPriceEstimatorProtocol, RelayBillingProtocol |
| `lexigram-contracts/src/lexigram/contracts/ai/guards.py` | GuardResultProtocol, InputGuardProtocol, OutputGuardProtocol, GuardPipelineProtocol |
| `lexigram-contracts/src/lexigram/contracts/ai/index.py` | IndexProtocol, QueryEngineProtocol |
| `lexigram-contracts/src/lexigram/contracts/ai/llm.py` | ChatMessageProtocol, CompletionProtocol, LLMClientProtocol, EmbeddingClientProtocol, StructuredExtractorProtocol, PromptTemplateProtocol, PromptRegistryProtocol, TokenCounterProtocol, PromptAssemblerProtocol, PromptRendererProtocol, PromptOptimizerProtocol, SemanticCacheProtocol, CostEstimatorProtocol |
| `lexigram-contracts/src/lexigram/contracts/ai/loaders.py` | DocumentLoaderProtocol, LoaderRegistryProtocol |
| `lexigram-contracts/src/lexigram/contracts/ai/memory.py` | MemoryStoreProtocol, WorkingMemoryProtocol, EpisodicMemoryProtocol, SemanticMemoryProtocol, MemoryConsolidatorProtocol, MemoryProtocol |
| `lexigram-contracts/src/lexigram/contracts/ai/protocols.py` | AIProviderProtocol, AISubsystemProtocol |
| `lexigram-contracts/src/lexigram/contracts/ai/providers.py` | ProviderRegistryProtocol, ModelSelectorProtocol, FallbackChainProtocol |
| `lexigram-contracts/src/lexigram/contracts/ai/rag.py` | ChunkProtocol, DocumentLoaderProtocol, SynthesizerProtocol, RAGPipelineProtocol, RetrievalStrategyProtocol, RerankingStrategyProtocol, RAGEvaluatorProtocol, PromptCompressorProtocol |
| `lexigram-contracts/src/lexigram/contracts/ai/relay/auth.py` | RelayAuthVerifierProtocol |
| `lexigram-contracts/src/lexigram/contracts/ai/relay/context.py` | MediaResolverProtocol |
| `lexigram-contracts/src/lexigram/contracts/ai/relay/gateway.py` | RelayGatewayProtocol |
| `lexigram-contracts/src/lexigram/contracts/ai/relay/ledger.py` | RelayLedgerServiceProtocol |
| `lexigram-contracts/src/lexigram/contracts/ai/relay/logs.py` | RelayRequestLogStoreProtocol |
| `lexigram-contracts/src/lexigram/contracts/ai/relay/operations.py` | RelayPolicyStoreProtocol, RelayOperationsProtocol, RelayOperationsControlProtocol |
| `lexigram-contracts/src/lexigram/contracts/ai/relay/protocols.py` | RelayConverterProtocol, RelayStreamSessionProtocol, RelayMapperProtocol, RelayRegistryProtocol |
| `lexigram-contracts/src/lexigram/contracts/ai/relay/ratelimit.py` | RelayRateLimitCounterProtocol |
| `lexigram-contracts/src/lexigram/contracts/ai/relay/store.py` | RelayChannelStoreProtocol |
| `lexigram-contracts/src/lexigram/contracts/ai/relay/transport.py` | RelayUpstreamProtocol |
| `lexigram-contracts/src/lexigram/contracts/ai/relay/usage.py` | RelayUsageServiceProtocol |
| `lexigram-contracts/src/lexigram/contracts/ai/retrievers.py` | RetrieverProtocol, NodePostprocessorProtocol |
| `lexigram-contracts/src/lexigram/contracts/ai/routing.py` | RoutingStrategyProtocol, LLMRouterProtocol, QuotaBackendProtocol, InferenceLoggerProtocol |
| `lexigram-contracts/src/lexigram/contracts/ai/runnable.py` | RunnableProtocol |
| `lexigram-contracts/src/lexigram/contracts/ai/session.py` | SessionStoreProtocol, SessionManagerProtocol, SessionContextProtocol, ContextPrunerProtocol |
| `lexigram-contracts/src/lexigram/contracts/ai/skills.py` | SkillProtocol, SkillRegistryProtocol, SkillExecutorProtocol, ToolkitProtocol |
| `lexigram-contracts/src/lexigram/contracts/ai/vector.py` | DocumentProtocol, SearchResultProtocol, BatchProcessorProtocol, DocumentVectorStoreProtocol, ChunkerProtocol |
| `lexigram-contracts/src/lexigram/contracts/ai/workflow.py` | AIWorkflowNodeProtocol, WorkflowProtocol |
| `lexigram-contracts/src/lexigram/contracts/audit/protocols.py` | AuditLoggerProtocol, AuditStoreProtocol, AuditVerifierProtocol, RetentionPolicyProtocol |
| `lexigram-contracts/src/lexigram/contracts/auth/blacklist.py` | TokenBlacklistProtocol |
| `lexigram-contracts/src/lexigram/contracts/auth/guard.py` | AuthenticatorProtocol, AuthorizerProtocol |
| `lexigram-contracts/src/lexigram/contracts/auth/identity.py` | IdentityResolverProtocol |
| `lexigram-contracts/src/lexigram/contracts/auth/models.py` | UserIdentityProtocol |
| `lexigram-contracts/src/lexigram/contracts/auth/policy.py` | PolicyStoreProtocol |
| `lexigram-contracts/src/lexigram/contracts/auth/protocols.py` | LoginAttemptTrackerProtocol, PasswordHasherProtocol, PasswordPolicyProtocol, MFAManagerProtocol, AuthProviderProtocol |
| `lexigram-contracts/src/lexigram/contracts/auth/repositories.py` | APIKeyRepositoryProtocol, SessionRepositoryProtocol |
| `lexigram-contracts/src/lexigram/contracts/auth/store.py` | UserReaderProtocol, UserWriterProtocol, UserStoreProtocol |
| `lexigram-contracts/src/lexigram/contracts/auth/token.py` | TokenManagerProtocol |
| `lexigram-contracts/src/lexigram/contracts/auth/user.py` | UserProtocol, AuthenticatedUserProtocol |
| `lexigram-contracts/src/lexigram/contracts/cli/generators.py` | GeneratorProtocol |
| `lexigram-contracts/src/lexigram/contracts/cli/protocols.py` | CliContributorProtocol |
| `lexigram-contracts/src/lexigram/contracts/codegen/protocols.py` | ScaffoldGeneratorProtocol, TemplateGeneratorProtocol |
| `lexigram-contracts/src/lexigram/contracts/core/clock.py` | ClockProtocol |
| `lexigram-contracts/src/lexigram/contracts/core/concurrency_protocols.py` | TaskManagerProtocol, DispatcherProtocol, ParallelProtocol, ChannelProtocol |
| `lexigram-contracts/src/lexigram/contracts/core/config.py` | ConfigProtocol |
| `lexigram-contracts/src/lexigram/contracts/core/context.py` | ContextProtocol, RequestContextProtocol |
| `lexigram-contracts/src/lexigram/contracts/core/di.py` | ContainerRegistrarProtocol, ContainerResolverProtocol, ContainerValidationProtocol, BootContainerProtocol, ContainerProtocol |
| `lexigram-contracts/src/lexigram/contracts/core/disposable.py` | AsyncDisposableProtocol |
| `lexigram-contracts/src/lexigram/contracts/core/health.py` | HealthCheckProtocol, HealthCheckAggregatorProtocol |
| `lexigram-contracts/src/lexigram/contracts/core/hooks.py` | HookRegistryProtocol |
| `lexigram-contracts/src/lexigram/contracts/core/idempotency.py` | IdempotencyStoreProtocol, IdempotencyMiddlewareProtocol |
| `lexigram-contracts/src/lexigram/contracts/core/identity.py` | IdGeneratorProtocol |
| `lexigram-contracts/src/lexigram/contracts/core/invocation.py` | InvocationContextProtocol, InvocationHandlerProtocol, InvocationMiddlewareProtocol, InvocationPipelineProtocol |
| `lexigram-contracts/src/lexigram/contracts/core/lifecycle.py` | OnModuleInitProtocol, OnApplicationBootstrapProtocol, OnBeforeShutdownProtocol, OnApplicationShutdownProtocol, GracefulShutdownProtocol, OnConfigReloadProtocol |
| `lexigram-contracts/src/lexigram/contracts/core/lock.py` | DistributedLockProtocol, AsyncLockProtocol, LockManagerProtocol |
| `lexigram-contracts/src/lexigram/contracts/core/logging.py` | LoggerProtocol, LoggerFactoryProtocol, RedactorProtocol |
| `lexigram-contracts/src/lexigram/contracts/core/middleware.py` | MiddlewareProtocol, ExceptionFilterChainProtocol, MiddlewarePipelineProtocol |
| `lexigram-contracts/src/lexigram/contracts/core/module.py` | ModuleMetadataProtocol, ModuleProtocol, DynamicModuleProtocol, CompiledModuleGraphProtocol, ModuleCompilerProtocol, ModuleRegistryProtocol |
| `lexigram-contracts/src/lexigram/contracts/core/provider.py` | ProviderProtocol |
| `lexigram-contracts/src/lexigram/contracts/core/registry.py` | RegistryProtocol, BackendRegistryProtocol, StrategyRegistryProtocol |
| `lexigram-contracts/src/lexigram/contracts/core/serialization.py` | JsonSerializerProtocol, AsyncStringSerializerProtocol, SerializerProtocol |
| `lexigram-contracts/src/lexigram/contracts/core/stores.py` | LockStoreProtocol |
| `lexigram-contracts/src/lexigram/contracts/core/validation.py` | RuleProtocol, AsyncRuleProtocol, ValidatorProtocol |
| `lexigram-contracts/src/lexigram/contracts/data/aggregatable.py` | AggregatableProtocol |
| `lexigram-contracts/src/lexigram/contracts/data/bulk_operations.py` | BulkOperationsProtocol |
| `lexigram-contracts/src/lexigram/contracts/data/data_source.py` | DataSourceProtocol |
| `lexigram-contracts/src/lexigram/contracts/data/graph/protocols.py` | GraphStoreProtocol, GraphProtocol |
| `lexigram-contracts/src/lexigram/contracts/data/nosql/nosql.py` | CollectionProtocol, DocumentStoreProtocol |
| `lexigram-contracts/src/lexigram/contracts/data/nosql/nosql_repository.py` | DocumentRepositoryProtocol |
| `lexigram-contracts/src/lexigram/contracts/data/outbox.py` | OutboxStoreProtocol |
| `lexigram-contracts/src/lexigram/contracts/data/protocols.py` | QueryFilterProtocol, FilterCompilerProtocol, CursorCodecProtocol, PaginatorProtocol |
| `lexigram-contracts/src/lexigram/contracts/data/relation_loader.py` | RelationLoaderProtocol |
| `lexigram-contracts/src/lexigram/contracts/data/repository.py` | ReadOnlyRepositoryProtocol, RepositoryProtocol |
| `lexigram-contracts/src/lexigram/contracts/data/searchable.py` | SearchableProtocol |
| `lexigram-contracts/src/lexigram/contracts/data/sql/append_log.py` | AppendLogProtocol |
| `lexigram-contracts/src/lexigram/contracts/data/sql/context_protocol.py` | DatabaseContextProtocol |
| `lexigram-contracts/src/lexigram/contracts/data/sql/database.py` | ConnectionProtocol, DatabaseProviderProtocol, ConnectionPoolProtocol, MigrationManagerProtocol, TransactionManagerProtocol, SchemaManagerProtocol, CrudOperationsProtocol, HealthMonitorProtocol, DatabaseMetricsProtocol |
| `lexigram-contracts/src/lexigram/contracts/data/sql/mapper.py` | ReadOnlyMapperProtocol, DataMapperProtocol |
| `lexigram-contracts/src/lexigram/contracts/data/sql/migrations.py` | MigrationRunnerProtocol |
| `lexigram-contracts/src/lexigram/contracts/data/sql/query_log.py` | QueryLoggerProtocol |
| `lexigram-contracts/src/lexigram/contracts/data/sql/unit_of_work.py` | UnitOfWorkProtocol |
| `lexigram-contracts/src/lexigram/contracts/data/timeseries/protocols.py` | TimeSeriesStoreProtocol |
| `lexigram-contracts/src/lexigram/contracts/data/vector/protocols.py` | VectorStoreProtocol, VectorCollectionProtocol |
| `lexigram-contracts/src/lexigram/contracts/domain/aggregates.py` | AggregateRootProtocol |
| `lexigram-contracts/src/lexigram/contracts/domain/base.py` | DomainModelProtocol |
| `lexigram-contracts/src/lexigram/contracts/domain/pagination.py` | OffsetPageProtocol, CursorPageProtocol |
| `lexigram-contracts/src/lexigram/contracts/domain/services.py` | DomainServiceProtocol, PolicyViolationProtocol, PolicyProtocol |
| `lexigram-contracts/src/lexigram/contracts/domain/specification.py` | SpecificationProtocol |
| `lexigram-contracts/src/lexigram/contracts/events/messages.py` | MessageSerializerProtocol |
| `lexigram-contracts/src/lexigram/contracts/events/outbox.py` | OutboxEntryProtocol, OutboxBackendProtocol, OutboxRelayProtocol |
| `lexigram-contracts/src/lexigram/contracts/events/protocols.py` | DomainEventPublisherProtocol, EventHandlerProtocol, MultiEventHandlerProtocol, EventBusProtocol, EventMiddlewareProtocol, CommandHandlerProtocol, CommandBusProtocol, QueryHandlerProtocol, QueryBusProtocol, EventStoreProtocol, SnapshotStoreProtocol, EventSourcedReadRepositoryProtocol, EventSourcedRepositoryProtocol, AggregateFactoryProtocol, ProjectionProtocol, PubSubProtocol, IntegrationEventProtocol, WebhookSignatureVerifierProtocol |
| `lexigram-contracts/src/lexigram/contracts/feature_flags/protocols.py` | FlagProviderProtocol, MutableFlagProviderProtocol, FlagManagerProtocol |
| `lexigram-contracts/src/lexigram/contracts/graphql/protocols.py` | GraphQLExecutorProtocol, GraphQLControllerProtocol, SchemaBuilderProtocol, DataLoaderProtocol, ResolverProtocol, EntityResolverProtocol, ValidationRuleProtocol, SubscriptionHandlerProtocol, SubscriptionAuthHandlerProtocol, WebSocketTransportProtocol, MutationHandlerProtocol, DirectiveHandlerProtocol, ErrorFormatterProtocol, GraphQLRequestProtocol, IntrospectionHandlerProtocol, GraphQLPrincipalResolverProtocol |
| `lexigram-contracts/src/lexigram/contracts/infra/cache/protocols.py` | CacheBackendProtocol, CacheProtectionStrategyProtocol, CacheKeyBuilderProtocol, CacheHealthCheckerProtocol, CacheProviderProtocol |
| `lexigram-contracts/src/lexigram/contracts/infra/resilience/protocols.py` | CircuitBreakerProtocol, RetryPolicyProtocol, BulkheadProtocol, ResiliencePipelineProtocol, ResiliencePipelineFactoryProtocol, CircuitBreakerRegistryProtocol, ThrottlerProtocol, RateLimiterProtocol, ResilienceFallbackProtocol, TimeoutProtocol |
| `lexigram-contracts/src/lexigram/contracts/infra/resources.py` | PoolStatsProtocol, PoolProtocol, PoolManagerProtocol |
| `lexigram-contracts/src/lexigram/contracts/infra/state.py` | StateStoreProtocol |
| `lexigram-contracts/src/lexigram/contracts/infra/storage/kv.py` | StorageBackendProtocol |
| `lexigram-contracts/src/lexigram/contracts/infra/storage/protocols.py` | BlobStoreProtocol, StorageDriverProtocol, StorageProviderProtocol |
| `lexigram-contracts/src/lexigram/contracts/infra/tasks/progress.py` | ProgressTrackerProtocol |
| `lexigram-contracts/src/lexigram/contracts/infra/tasks/protocols.py` | JobProtocol, TaskQueueProtocol, TaskExecutorProtocol, TaskProviderProtocol, JobTemplateProtocol, TaskWorkerProtocol, DLQProtocol |
| `lexigram-contracts/src/lexigram/contracts/lifecycle/auditable.py` | AuditableProtocol |
| `lexigram-contracts/src/lexigram/contracts/lifecycle/cache_aware.py` | CacheAwareProtocol |
| `lexigram-contracts/src/lexigram/contracts/lifecycle/exportable.py` | ExportableProtocol |
| `lexigram-contracts/src/lexigram/contracts/lifecycle/transactional.py` | TransactionalProtocol |
| `lexigram-contracts/src/lexigram/contracts/lifecycle/validatable.py` | ValidatableProtocol |
| `lexigram-contracts/src/lexigram/contracts/mailer/protocols.py` | MailerProtocol |
| `lexigram-contracts/src/lexigram/contracts/mapping/protocols.py` | ObjectMapperProtocol |
| `lexigram-contracts/src/lexigram/contracts/mcp/protocols.py` | MCPToolProviderProtocol, MCPResourceProviderProtocol, MCPPromptProviderProtocol, MCPTransportProtocol, MCPServerProtocol, MCPToolHandlerProtocol, MCPResourceHandlerProtocol, MCPPromptHandlerProtocol |
| `lexigram-contracts/src/lexigram/contracts/notification/delivery.py` | DeliveryStoreProtocol |
| `lexigram-contracts/src/lexigram/contracts/notification/inbox.py` | InboxStoreProtocol |
| `lexigram-contracts/src/lexigram/contracts/notification/protocols.py` | SMSChannelProtocol, PushChannelProtocol |
| `lexigram-contracts/src/lexigram/contracts/observability/ai.py` | ObservabilityProtocol, AITracerProtocol, AIMetricsProtocol, AIHealthMonitorProtocol |
| `lexigram-contracts/src/lexigram/contracts/observability/audit.py` | AuditVerifierSchedulerProtocol |
| `lexigram-contracts/src/lexigram/contracts/observability/metrics.py` | AlertDispatcherProtocol, MetricsRecorderProtocol, MetricsFactoryProtocol, MetricProtocol, MetricsBackendProtocol, MetricsCollectorProtocol, HealthCheckRegistryProtocol |
| `lexigram-contracts/src/lexigram/contracts/observability/tracing.py` | TracerProtocol, SpanProtocol |
| `lexigram-contracts/src/lexigram/contracts/queue/protocols.py` | QueueProtocol, MessageConsumerProtocol |
| `lexigram-contracts/src/lexigram/contracts/search/protocols.py` | SearchEngineProtocol, IndexManagerProtocol, SearchableProtocol, SearchAnalyticsProtocol, DatabaseSearchBackendProtocol, DocumentTransformerProtocol |
| `lexigram-contracts/src/lexigram/contracts/security/protocols.py` | HasherProtocol, KeyDerivationProtocol, GuardChainProtocol, InputSanitizerProtocol, SecurityHeadersProtocol, EncryptionProtocol, CORSProtocol, CSPProtocol, CSRFProtocol |
| `lexigram-contracts/src/lexigram/contracts/security/secrets.py` | SecretStoreProtocol |
| `lexigram-contracts/src/lexigram/contracts/security/stores.py` | AsyncSecretStoreProtocol |
| `lexigram-contracts/src/lexigram/contracts/tenancy/protocols.py` | TenantResolverProtocol, TenantProviderProtocol, TenantConfigProviderProtocol, TenantIsolationStrategyProtocol |
| `lexigram-contracts/src/lexigram/contracts/web/controller.py` | ControllerProtocol |
| `lexigram-contracts/src/lexigram/contracts/web/execution_context.py` | ExecutionContextProtocol |
| `lexigram-contracts/src/lexigram/contracts/web/guard.py` | GuardProtocol |
| `lexigram-contracts/src/lexigram/contracts/web/http_protocols.py` | ServiceMeshRegistryProtocol, SelectorProtocol, HTTPSessionProtocol, HTTPClientProtocol, InterceptorProtocol, InterceptorChainProtocol, ConnectMetricsCollectorProtocol, WebSocketProtocol |
| `lexigram-contracts/src/lexigram/contracts/web/middleware/protocols.py` | ASGIMiddlewareProtocol |
| `lexigram-contracts/src/lexigram/contracts/web/middleware/registry_protocol.py` | MiddlewareRegistryProtocol |
| `lexigram-contracts/src/lexigram/contracts/web/protocols.py` | HttpRequestLoggerProtocol, CORSPolicyProtocol, BackgroundTaskRunnerProtocol, CSRFProtectionProtocol, WebRateLimiterProtocol, WebMiddlewareProtocol, ExceptionFilterProtocol, RequestProtocol, ResponseProtocol, ResponseFactoryProtocol, WebProviderProtocol, HTTPApplicationProtocol, CRUDServiceProtocol, ConnectionManagerProtocol, WebContributorProtocol |
| `lexigram-contracts/src/lexigram/contracts/web/sse.py` | SseResponseFactoryProtocol |
| `lexigram-contracts/src/lexigram/contracts/webhook/protocols.py` | WebhookSubscriptionStoreProtocol, WebhookDeliveryStoreProtocol, WebhookDeliveryServiceProtocol |
| `lexigram-contracts/src/lexigram/contracts/workflow/content_checkpoint.py` | ContentCheckpointStoreProtocol |
| `lexigram-contracts/src/lexigram/contracts/workflow/protocols.py` | WorkflowGraphProtocol, WorkflowNodeProtocol, ApprovalProtocol, ExecutionProtocol, SagaStoreProtocol, PipelineContextProtocol, PipelineStepProtocol, PipelineProtocol, BulkProcessorProtocol, SagaProtocol, SagaManagerProtocol, StateMachineProtocol, StatePersistenceProtocol |
| `lexigram/src/lexigram/app/protocols.py` | AppLifecycleProtocol |
| `lexigram/src/lexigram/config/protocols.py` | ConfigSourceProtocol |
| `lexigram/src/lexigram/config/secrets.py` | SecretsValidatorProtocol |
| `lexigram/src/lexigram/di/extensions/aop_interceptors.py` | MethodInterceptorProtocol |
| `lexigram/src/lexigram/di/protocols.py` | DIResolverProtocol, TypeHintResolverProtocol, DIServiceRegistryProtocol, ProtocolValidatorProtocol, InjectorProtocol |
| `lexigram/src/lexigram/mapping/protocols.py` | TypeConverterProtocol |
| `lexigram/src/lexigram/mapping/types.py` | MapperProtocol |

