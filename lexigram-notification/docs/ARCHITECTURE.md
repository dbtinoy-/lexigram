# Architecture

Internal design of the `lexigram-notification` package.

---

## Role in the System

`lexigram-notification` provides multi-channel notification delivery (SMS, push, email, in-app inbox) for Lexigram applications. It is an extension package depending only on `lexigram` and `lexigram-contracts`.

```mermaid
flowchart BT
    subgraph Apps[Application Layer]
        Controller[Web Controller]
        Service[Domain Service]
        Worker[Background Worker]
    end
    subgraph Notification[lexigram-notification]
        Inbox[InboxService]
        Mailer[MailerProtocol]
        SMS[SMSChannelProtocol]
        Push[PushChannelProtocol]
    end
    subgraph Providers[External Providers]
        Twilio
        FCM
        APNs
        SMTP
        SendGrid
    end

    Controller --> Inbox
    Service --> Mailer
    Service --> SMS
    Worker --> Push
    Service --> Inbox
    Mailer --> SMTP
    Mailer --> SendGrid
    SMS --> Twilio
    Push --> FCM
    Push --> APNs
    Push --> WebPush[Web Push]
```

Import constraint: `lexigram-notification` imports only from `lexigram` and `lexigram-contracts`. No cross-extension imports.

---

## Channels

The package delivers notifications through four channel families, each backed by one or more providers:

```mermaid
flowchart LR
    subgraph Email[Email]
        SMTP[SMTPMailer]
        SendGrid[SendGridMailer]
    end
    subgraph SMSChannel[SMS]
        TW[Twilio]
        WA[WhatsApp]
    end
    subgraph PushChannel[Push]
        FCM
        APNs
        WP[Web Push]
    end
    subgraph InApp[In-App]
        IB[InboxService]
    end

    Email -->|MailerProtocol| SMTP
    Email -->|MailerProtocol| SendGrid
    SMSChannel -->|SMSChannelProtocol| TW
    SMSChannel -->|SMSChannelProtocol| WA
    PushChannel -->|PushChannelProtocol| FCM
    PushChannel -->|PushChannelProtocol| APNs
    PushChannel -->|PushChannelProtocol| WP
    InApp -->|InboxStoreProtocol| IB
```

**Channel routing** for backend selection is driven by **Named DI multi-backend**:

```python
# Primary backend (unnamed binding — auto-injected)
sms = await container.resolve(SMSChannelProtocol)

# Named backend — explicit routing by name
alerts_sms = await container.resolve(
    Annotated[SMSChannelProtocol, Named("alerts")]
)
```

Each channel family (SMS, push, email) supports multiple named backends. The primary backend gets the unnamed binding; named backends are addressed via `Annotated[Protocol, Named("name")]`.

---

## Notification Pipeline

```mermaid
sequenceDiagram
    participant App as Application
    participant Inbox as InboxService
    participant Mailer as MailerProtocol
    participant SMS as SMSChannelProtocol
    participant Push as PushChannelProtocol
    participant Retry as RetryingMailer
    participant Store as DeliveryStore
    participant Events as Event Bus

    App->>Inbox: send(user_id, title, body)
    Inbox->>Inbox: Create InboxMessage
    Inbox->>Store: save(message)
    Inbox->>Events: emit InboxMessageCreatedEvent

    App->>Mailer: send(EmailMessage)
    alt Infrastructure failure
        Mailer->>Retry: exponential backoff (max 3)
        Retry->>Store: record_attempt / schedule_retry
        Store-->>Retry: retry state
        Retry->>Mailer: resend
        Mailer-->>Retry: Ok | Err
        Retry->>Events: emit EmailSentEvent / EmailBouncedEvent
    else Expected failure (bounce)
        Mailer->>Events: emit EmailBouncedEvent
    else Success
        Mailer-->>App: Ok(MessageDeliveryReceipt)
        Mailer->>Events: emit EmailSentEvent
    end

    App->>SMS: send(SMSMessage)
    SMS-->>App: Ok | Err(NotificationError)
    App->>Push: send(PushMessage)
    Push-->>App: Ok | Err(NotificationError)
    Push->>Events: emit PushNotificationSentEvent
```

**Delivery status tracking** follows this lifecycle:

```
PENDING → RETRYING → (DELIVERED | FAILED)
```

The `DeliveryStoreProtocol` (defined in `lexigram-contracts`) records every attempt. `RetryingMailer` wraps any `MailerProtocol` with exponential backoff (1s, 2s, 4s) up to 3 attempts. Infrastructure exceptions (timeout, network error) trigger retries; `Err(MailerError)` returns from the inner mailer are terminal — never retried.

---

## Template System

Email templates use the **Mailable** pattern — a lightweight strategy class that encapsulates template rendering for a single email type:

```python
class WelcomeMail(Mailable):
    def __init__(self, user_name: str, user_email: str) -> None:
        self.user_name = user_name
        self.user_email = user_email

    def to_message(self) -> EmailMessage:
        return EmailMessage(
            to=[self.user_email],
            subject=f"Welcome, {self.user_name}!",
            body=f"Hi {self.user_name}, welcome aboard.",
            html_body=f"<p>Hi <b>{self.user_name}</b>, welcome aboard.</p>",
        )
```

```mermaid
flowchart LR
    M[Mailable subclass] -->|to_message| EM[EmailMessage]
    EM -->|MailerProtocol.send| Backend[SMTP / SendGrid]
    M -->|render| HTML[HTML body]
    M -->|render| Text[Plain text body]
```

Channels without templates (SMS, push) construct `SMSMessage` / `PushMessage` value objects directly — no templating layer beyond simple string formatting. The `Mailable` base class ships in `lexigram.notification.mailer.mailable`.

---

## Provider Lifecycle

Two DI providers register notification backends:

### NotificationProvider (SMS + Push)

```python
class NotificationProvider(Provider):
    name = "notification"
    priority = ProviderPriority.INFRASTRUCTURE
```

### MailerProvider (Email)

```python
class MailerProvider(Provider):
    name = "mailer"
    priority = ProviderPriority.INFRASTRUCTURE
```

Discovered automatically via the `lexigram.providers` entry point (`mailer = lexigram.notification.di.mailer_provider:MailerProvider`).

```mermaid
sequenceDiagram
    participant App as Application
    participant Container as DI Container
    participant NP as NotificationProvider
    participant MP as MailerProvider
    participant SMS as TwilioSMS
    participant Push as FCMPush
    participant Mail as SMTPMailer

    App->>Container: ModuleCompiler.compile()
    Container->>NP: register(registrar)
    NP->>NP: Iterate sms_backends
    NP->>SMS: _create_sms(entry)
    NP->>Container: singleton(SMSChannelProtocol, name=..., factory)
    NP->>NP: Iterate push_backends
    NP->>Push: _create_push(entry)
    NP->>Container: singleton(PushChannelProtocol, name=..., factory)
    Container->>MP: register(registrar)
    MP->>Mail: _create_mailer(entry)
    MP->>Container: singleton(MailerProtocol, name=..., factory)
    Container->>Container: freeze()
    Container->>NP: boot(resolver)
    NP->>SMS: health_check()
    NP->>Push: health_check()
    Container->>MP: boot(resolver)
    Note over MP: no-op (stateless)
    App->>Container: resolve(SMSChannelProtocol) → TwilioSMS
    App->>Container: resolve(PushChannelProtocol) → FCMPush
    App->>Container: resolve(MailerProtocol) → SMTPMailer
```

---

## Contracts Used

| Protocol | Location (lexigram-contracts) | Implemented By |
|----------|-------------------------------|----------------|
| `SMSChannelProtocol` | `lexigram.contracts.notification.protocols` | `TwilioSMS` |
| `PushChannelProtocol` | `lexigram.contracts.notification.protocols` | `FCMPush`, `APNsPush`, `WebPushChannel` |
| `MailerProtocol` | `lexigram.contracts.mailer.protocols` | `SMTPMailer`, `SendGridMailer`, `RetryingMailer` |
| `InboxStoreProtocol` | `lexigram.contracts.notification.inbox` | `InMemoryInboxStore`, `DatabaseInboxStore` |
| `DeliveryStoreProtocol` | `lexigram.contracts.notification.delivery` | Application-provided (persistent tracking) |

**Value types shared across packages:**

| Type | Location | Used By |
|------|----------|---------|
| `SMSMessage` | `lexigram.contracts.notification.types` | SMS backends |
| `PushMessage` | `lexigram.contracts.notification.types` | Push backends |
| `EmailMessage` | `lexigram.contracts.mailer.types` | Mailer backends |
| `MessageDeliveryReceipt` | `lexigram.contracts.mailer.types` | All channels |
| `InboxMessage` | `lexigram.contracts.notification.inbox` | Inbox service and stores |

**Exception hierarchy:**

```
NotificationError (lexigram-contracts)
├── TwilioNotificationError
├── FCMNotificationError
├── APNsNotificationError
├── WebPushNotificationError
├── PermanentDeliveryFailure
├── InboxError
│   ├── InboxMessageNotFoundError
│   └── InboxPermissionError
MailerError (lexigram-contracts)
├── SMTPMailerError
└── SendGridMailerError
```

---

## Extension Points

| Point | Mechanism |
|-------|-----------|
| **Custom SMS driver** | Implement `SMSChannelProtocol`, add a `NamedSMSConfig` subclass |
| **Custom push driver** | Implement `PushChannelProtocol`, add a `NamedPushConfig` subclass |
| **Custom mailer** | Implement `MailerProtocol`, add a `NamedMailerConfig` subclass |
| **Custom inbox store** | Implement `InboxStoreProtocol` |
| **Custom delivery store** | Implement `DeliveryStoreProtocol` |
| **Retry wrapper** | `RetryingMailer` wraps any `MailerProtocol` with configurable retry (max 3 attempts, exponential backoff) |
| **Named multi-backend** | Declare multiple entries in `backends` / `sms_backends` / `push_backends` in config |
| **Hook points** | Register callbacks via `HookRegistryProtocol` for `NotificationSentHook`, `NotificationFailedHook`, `EmailDispatchedHook`, `EmailRenderedHook`, `InboxMessageCreatedHook`, `InboxMessageReadHook` |
| **Domain events** | Subscribe to `NotificationSentEvent`, `NotificationFailedEvent`, `EmailSentEvent`, `EmailBouncedEvent`, `InboxMessageCreatedEvent`, `InboxMessageReadEvent` |
