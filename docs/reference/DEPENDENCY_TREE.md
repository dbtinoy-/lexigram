# Dependency Tree

Generated from the locked workspace with '`uv tree --locked`' run at the repository root. Regenerate with:

```bash
uv tree --locked > docs/reference/DEPENDENCY_TREE.md
```

> Direct dependencies per workspace member are the first level under each package name;
> the full transitive graph is shown beneath. This file exists so reviewers and
> tooling can inspect the dependency graph without re-resolving it.

xgboost v3.4.1 (group: tooling)
├── numpy v2.5.2
├── nvidia-nccl-cu13 v2.31.2
└── scipy v1.18.0
    └── numpy v2.5.2
uvicorn v0.52.4 (group: tooling)
├── click v8.4.2
├── h11 v0.16.0
├── httptools v0.8.0 (extra: standard)
├── python-dotenv v1.2.3 (extra: standard)
├── pyyaml v6.0.3 (extra: standard)
├── uvloop v0.22.1 (extra: standard)
├── watchfiles v1.2.0 (extra: standard)
│   └── anyio v4.14.2
│       └── idna v3.19
└── websockets v17.0.1 (extra: standard)
types-pyyaml v6.0.12.20260815 (group: tooling)
scipy v1.18.0 (group: tooling) (*)
scikit-learn v1.9.0 (group: tooling)
├── joblib v1.5.3
├── narwhals v2.24.0
├── numpy v2.5.2
├── scipy v1.18.0 (*)
└── threadpoolctl v3.6.0
ruff v0.16.3 (group: tooling)
redis v8.1.0 (group: tooling)
pyyaml v6.0.3 (group: tooling)
python-dotenv v1.2.3 (group: tooling)
pytest-timeout v2.4.0 (group: tooling)
└── pytest v9.1.1
    ├── iniconfig v2.3.0
    ├── packaging v26.3
    ├── pluggy v1.6.0
    └── pygments v2.21.0
pymemcache v4.0.0 (group: tooling)
prometheus-client v0.26.0 (group: tooling)
playwright v1.62.0 (group: tooling)
├── greenlet v3.5.5
└── pyee v13.0.1
    └── typing-extensions v4.16.0
pip-audit v2.10.1 (group: tooling)
├── cachecontrol[filecache] v0.14.4
│   ├── msgpack v1.2.1
│   ├── requests v2.34.2
│   │   ├── certifi v2026.7.22
│   │   ├── charset-normalizer v3.5.1
│   │   ├── idna v3.19
│   │   └── urllib3 v2.7.0
│   └── filelock v3.32.3 (extra: filecache)
├── cyclonedx-python-lib v11.12.0
│   ├── license-expression v30.4.4
│   │   └── boolean-py v5.0
│   ├── packageurl-python v0.17.6
│   ├── py-serializable v2.1.0
│   │   └── defusedxml v0.7.1
│   └── sortedcontainers v2.4.0
├── packaging v26.3
├── pip-api v0.0.34
│   └── pip v26.2.1
├── pip-requirements-parser v32.0.1
│   ├── packaging v26.3
│   └── pyparsing v3.3.2
├── platformdirs v4.11.3
├── requests v2.34.2 (*)
├── rich v13.9.4
│   ├── markdown-it-py v4.2.0
│   │   └── mdurl v0.1.2
│   └── pygments v2.21.0
├── tomli v2.4.1
└── tomli-w v1.2.0
pillow v12.3.0 (group: tooling)
opentelemetry-sdk v1.44.0 (group: tooling)
├── opentelemetry-api v1.44.0
│   └── typing-extensions v4.16.0
├── opentelemetry-semantic-conventions v0.65b0
│   ├── opentelemetry-api v1.44.0 (*)
│   └── typing-extensions v4.16.0
└── typing-extensions v4.16.0
opentelemetry-api v1.44.0 (group: tooling) (*)
openai v2.54.0 (group: tooling)
├── anyio v4.14.2 (*)
├── distro v1.9.0
├── httpx v0.28.1
│   ├── anyio v4.14.2 (*)
│   ├── certifi v2026.7.22
│   ├── httpcore v1.0.9
│   │   ├── certifi v2026.7.22
│   │   └── h11 v0.16.0
│   ├── idna v3.19
│   └── h2 v4.4.1 (extra: http2)
│       ├── hpack v4.2.0
│       └── hyperframe v6.1.0
├── jiter v0.14.0
├── pydantic v2.13.4
│   ├── annotated-types v0.8.0
│   ├── pydantic-core v2.46.4
│   │   └── typing-extensions v4.16.0
│   ├── typing-extensions v4.16.0
│   └── typing-inspection v0.4.4
│       └── typing-extensions v4.16.0
├── sniffio v1.3.1
├── tqdm v4.67.1
└── typing-extensions v4.16.0
ollama v0.6.2 (group: tooling)
├── httpx v0.28.1 (*)
└── pydantic v2.13.4 (*)
nh3 v0.3.6 (group: tooling)
mypy v2.3.1 (group: tooling)
├── ast-serialize v0.8.0
├── librt v0.15.0
├── mypy-extensions v1.1.0
├── pathspec v1.1.1
└── typing-extensions v4.16.0
motor v3.7.1 (group: tooling)
└── pymongo v4.17.0
    └── dnspython v2.8.0
lexigram-nosql v0.1.3007 (group: tooling)
├── jinja2 v3.1.6
│   └── markupsafe v3.0.3
├── lexigram v0.1.3009
│   ├── jinja2 v3.1.6 (*)
│   ├── lexigram-contracts v0.1.3007
│   │   ├── typing-extensions v4.16.0
│   │   ├── mypy v2.3.1 (extra: dev) (*)
│   │   ├── ruff v0.16.3 (extra: dev)
│   │   ├── pytest v9.1.1 (extra: test) (*)
│   │   ├── pytest-asyncio v1.4.0 (extra: test)
│   │   │   └── pytest v9.1.1 (*)
│   │   ├── pytest-cov v7.1.0 (extra: test)
│   │   │   ├── coverage[toml] v7.15.4
│   │   │   ├── pluggy v1.6.0
│   │   │   └── pytest v9.1.1 (*)
│   │   ├── pytest-mock v3.15.1 (extra: test)
│   │   │   └── pytest v9.1.1 (*)
│   │   ├── mypy v2.3.1 (group: dev) (*)
│   │   ├── ruff v0.16.3 (group: dev)
│   │   └── typing-extensions v4.16.0 (group: dev)
│   ├── orjson v3.12.0
│   ├── pydantic v2.13.4 (*)
│   ├── structlog v26.1.0
│   ├── lexigram-admin v0.1.3010 (extra: all)
│   │   ├── aiofiles v25.1.0
│   │   ├── cryptography v50.0.0
│   │   │   └── cffi v2.1.1
│   │   │       └── pycparser v3.0
│   │   ├── htpy v26.5.1
│   │   │   └── markupsafe v3.0.3
│   │   ├── httpx v0.28.1 (*)
│   │   ├── itsdangerous v2.2.0
│   │   ├── lexigram v0.1.3009 (*)
│   │   ├── lexigram-contracts v0.1.3007 (*)
│   │   ├── lexigram-ui v0.1.3009
│   │   │   ├── htpy v26.5.1 (*)
│   │   │   ├── httpx v0.28.1 (*)
│   │   │   ├── lexigram v0.1.3009 (*)
│   │   │   ├── lexigram-contracts v0.1.3007 (*)
│   │   │   ├── markupsafe v3.0.3
│   │   │   ├── starlette v1.6.0
│   │   │   │   └── anyio v4.14.2 (*)
│   │   │   ├── typer v0.27.1
│   │   │   │   ├── annotated-doc v0.0.5
│   │   │   │   ├── rich v13.9.4 (*)
│   │   │   │   └── shellingham v1.5.4
│   │   │   ├── httpx v0.28.1 (extra: a11y) (*)
│   │   │   ├── playwright v1.62.0 (extra: a11y) (*)
│   │   │   ├── pytest-playwright v0.9.0 (extra: a11y)
│   │   │   │   ├── playwright v1.62.0 (*)
│   │   │   │   ├── pytest v9.1.1 (*)
│   │   │   │   ├── pytest-base-url v2.1.0
│   │   │   │   │   ├── pytest v9.1.1 (*)
│   │   │   │   │   └── requests v2.34.2 (*)
│   │   │   │   └── python-slugify v8.0.4
│   │   │   │       └── text-unidecode v1.3
│   │   │   ├── starlette v1.6.0 (extra: a11y) (*)
│   │   │   ├── mypy v2.3.1 (extra: dev) (*)
│   │   │   ├── ruff v0.16.3 (extra: dev)
│   │   │   ├── lexigram-testing v0.1.3007 (extra: test)
│   │   │   │   ├── lexigram v0.1.3009 (*)
│   │   │   │   ├── lexigram-contracts v0.1.3007 (*)
│   │   │   │   ├── lexigram-sql v0.1.3007
│   │   │   │   │   ├── aiosqlite v0.22.1
│   │   │   │   │   ├── alembic v1.19.1
│   │   │   │   │   │   ├── mako v1.4.1
│   │   │   │   │   │   │   └── markupsafe v3.0.3
│   │   │   │   │   │   ├── sqlalchemy v2.0.52
│   │   │   │   │   │   │   ├── greenlet v3.5.5
│   │   │   │   │   │   │   └── typing-extensions v4.16.0
│   │   │   │   │   │   └── typing-extensions v4.16.0
│   │   │   │   │   ├── anyio v4.14.2 (*)
│   │   │   │   │   ├── jinja2 v3.1.6 (*)
│   │   │   │   │   ├── lexigram v0.1.3009 (*)
│   │   │   │   │   ├── lexigram-contracts v0.1.3007 (*)
│   │   │   │   │   ├── sqlalchemy v2.0.52 (*)
│   │   │   │   │   ├── starlette v1.6.0 (*)
│   │   │   │   │   ├── typer v0.27.1 (*)
│   │   │   │   │   ├── typing-extensions v4.16.0
│   │   │   │   │   ├── aiomysql v0.3.2 (extra: all)
│   │   │   │   │   │   └── pymysql v1.2.0
│   │   │   │   │   ├── aiosqlite v0.22.1 (extra: all)
│   │   │   │   │   ├── asyncpg v0.31.0 (extra: all)
│   │   │   │   │   ├── lexigram-testing v0.1.3007 (extra: all) (*)
│   │   │   │   │   ├── pytest v9.1.1 (extra: all) (*)
│   │   │   │   │   ├── pytest-asyncio v1.4.0 (extra: all) (*)
│   │   │   │   │   ├── pytest-cov v7.1.0 (extra: all) (*)
│   │   │   │   │   ├── pytest-mock v3.15.1 (extra: all) (*)
│   │   │   │   │   ├── black v26.5.1 (extra: dev)
│   │   │   │   │   │   ├── click v8.4.2
│   │   │   │   │   │   ├── mypy-extensions v1.1.0
│   │   │   │   │   │   ├── packaging v26.3
│   │   │   │   │   │   ├── pathspec v1.1.1
│   │   │   │   │   │   ├── platformdirs v4.11.3
│   │   │   │   │   │   └── pytokens v0.4.1
│   │   │   │   │   ├── mypy v2.3.1 (extra: dev) (*)
│   │   │   │   │   ├── ruff v0.16.3 (extra: dev)
│   │   │   │   │   ├── aiomysql v0.3.2 (extra: mysql) (*)
│   │   │   │   │   ├── asyncpg v0.31.0 (extra: postgres)
│   │   │   │   │   ├── aiosqlite v0.22.1 (extra: sqlite)
│   │   │   │   │   ├── lexigram-testing v0.1.3007 (extra: test) (*)
│   │   │   │   │   ├── pytest v9.1.1 (extra: test) (*)
│   │   │   │   │   ├── pytest-asyncio v1.4.0 (extra: test) (*)
│   │   │   │   │   ├── pytest-cov v7.1.0 (extra: test) (*)
│   │   │   │   │   ├── pytest-mock v3.15.1 (extra: test) (*)
│   │   │   │   │   ├── black v26.5.1 (group: dev) (*)
│   │   │   │   │   ├── lexigram-testing v0.1.3007 (group: dev) (*)
│   │   │   │   │   ├── mypy v2.3.1 (group: dev) (*)
│   │   │   │   │   └── ruff v0.16.3 (group: dev)
│   │   │   │   ├── pytest v9.1.1 (*)
│   │   │   │   ├── pytest-asyncio v1.4.0 (*)
│   │   │   │   ├── pytest-cov v7.1.0 (*)
│   │   │   │   ├── pytest-mock v3.15.1 (*)
│   │   │   │   ├── aiosqlite v0.22.1 (extra: all)
│   │   │   │   ├── asyncpg v0.31.0 (extra: all)
│   │   │   │   ├── httpx v0.28.1 (extra: all) (*)
│   │   │   │   ├── httpx2 v2.12.0 (extra: all)
│   │   │   │   │   ├── anyio v4.14.2 (*)
│   │   │   │   │   ├── httpcore2 v2.12.0
│   │   │   │   │   │   ├── h11 v0.16.0
│   │   │   │   │   │   └── truststore v0.10.4
│   │   │   │   │   ├── idna v3.19
│   │   │   │   │   └── truststore v0.10.4
│   │   │   │   ├── lexigram-auth v0.1.3007 (extra: all)
│   │   │   │   │   ├── argon2-cffi v25.1.0
│   │   │   │   │   │   └── argon2-cffi-bindings v25.1.0
│   │   │   │   │   │       └── cffi v2.1.1 (*)
│   │   │   │   │   ├── cryptography v50.0.0 (*)
│   │   │   │   │   ├── jinja2 v3.1.6 (*)
│   │   │   │   │   ├── lexigram v0.1.3009 (*)
│   │   │   │   │   ├── lexigram-contracts v0.1.3007 (*)
│   │   │   │   │   ├── orjson v3.12.0
│   │   │   │   │   ├── passlib[bcrypt] v1.7.4
│   │   │   │   │   │   └── bcrypt v5.0.0 (extra: bcrypt)
│   │   │   │   │   ├── pydantic v2.13.4 (*)
│   │   │   │   │   ├── pyjwt v2.13.0
│   │   │   │   │   │   └── cryptography v50.0.0 (extra: crypto) (*)
│   │   │   │   │   ├── starlette v1.6.0 (*)
│   │   │   │   │   ├── typer v0.27.1 (*)
│   │   │   │   │   ├── typing-extensions v4.16.0
│   │   │   │   │   ├── authlib v1.7.2 (extra: all)
│   │   │   │   │   │   ├── cryptography v50.0.0 (*)
│   │   │   │   │   │   └── joserfc v1.7.4
│   │   │   │   │   │       └── cryptography v50.0.0 (*)
│   │   │   │   │   ├── ldap3 v2.9.1 (extra: all)
│   │   │   │   │   │   └── pyasn1 v0.6.4
│   │   │   │   │   ├── lexigram-testing v0.1.3007 (extra: all) (*)
│   │   │   │   │   ├── pysaml2 v7.5.4 (extra: all)
│   │   │   │   │   │   ├── cryptography v50.0.0 (*)
│   │   │   │   │   │   ├── defusedxml v0.7.1
│   │   │   │   │   │   ├── pyopenssl v22.0.0
│   │   │   │   │   │   │   └── cryptography v50.0.0 (*)
│   │   │   │   │   │   ├── python-dateutil v2.9.0.post0
│   │   │   │   │   │   │   └── six v1.17.0
│   │   │   │   │   │   ├── requests v2.34.2 (*)
│   │   │   │   │   │   └── xmlschema v2.5.1
│   │   │   │   │   │       └── elementpath v4.8.0
│   │   │   │   │   ├── pytest v9.1.1 (extra: all) (*)
│   │   │   │   │   ├── pytest-asyncio v1.4.0 (extra: all) (*)
│   │   │   │   │   ├── pytest-cov v7.1.0 (extra: all) (*)
│   │   │   │   │   ├── pytest-mock v3.15.1 (extra: all) (*)
│   │   │   │   │   ├── xmlsec v1.3.17 (extra: all)
│   │   │   │   │   │   └── lxml v6.1.2
│   │   │   │   │   ├── black v26.5.1 (extra: dev) (*)
│   │   │   │   │   ├── mypy v2.3.1 (extra: dev) (*)
│   │   │   │   │   ├── ruff v0.16.3 (extra: dev)
│   │   │   │   │   ├── ldap3 v2.9.1 (extra: ldap) (*)
│   │   │   │   │   ├── authlib v1.7.2 (extra: oauth2) (*)
│   │   │   │   │   ├── pysaml2 v7.5.4 (extra: saml) (*)
│   │   │   │   │   ├── xmlsec v1.3.17 (extra: saml) (*)
│   │   │   │   │   ├── lexigram-testing v0.1.3007 (extra: test) (*)
│   │   │   │   │   ├── pytest v9.1.1 (extra: test) (*)
│   │   │   │   │   ├── pytest-asyncio v1.4.0 (extra: test) (*)
│   │   │   │   │   ├── pytest-cov v7.1.0 (extra: test) (*)
│   │   │   │   │   ├── pytest-mock v3.15.1 (extra: test) (*)
│   │   │   │   │   ├── black v26.5.1 (group: dev) (*)
│   │   │   │   │   ├── mypy v2.3.1 (group: dev) (*)
│   │   │   │   │   └── ruff v0.16.3 (group: dev)
│   │   │   │   ├── lexigram-cache v0.1.3007 (extra: all)
│   │   │   │   │   ├── jinja2 v3.1.6 (*)
│   │   │   │   │   ├── lexigram v0.1.3009 (*)
│   │   │   │   │   ├── lexigram-contracts v0.1.3007 (*)
│   │   │   │   │   ├── orjson v3.12.0
│   │   │   │   │   ├── starlette v1.6.0 (*)
│   │   │   │   │   ├── typer v0.27.1 (*)
│   │   │   │   │   ├── typing-extensions v4.16.0
│   │   │   │   │   ├── faiss-cpu v1.15.0 (extra: all)
│   │   │   │   │   │   ├── numpy v2.5.2
│   │   │   │   │   │   └── packaging v26.3
│   │   │   │   │   ├── lexigram-testing v0.1.3007 (extra: all) (*)
│   │   │   │   │   ├── numpy v2.5.2 (extra: all)
│   │   │   │   │   ├── pymemcache v4.0.0 (extra: all)
│   │   │   │   │   ├── pytest v9.1.1 (extra: all) (*)
│   │   │   │   │   ├── pytest-asyncio v1.4.0 (extra: all) (*)
│   │   │   │   │   ├── pytest-cov v7.1.0 (extra: all) (*)
│   │   │   │   │   ├── pytest-mock v3.15.1 (extra: all) (*)
│   │   │   │   │   ├── redis v8.1.0 (extra: all)
│   │   │   │   │   ├── black v26.5.1 (extra: dev) (*)
│   │   │   │   │   ├── mypy v2.3.1 (extra: dev) (*)
│   │   │   │   │   ├── ruff v0.16.3 (extra: dev)
│   │   │   │   │   ├── types-redis v4.6.0.20241004 (extra: dev)
│   │   │   │   │   │   ├── cryptography v50.0.0 (*)
│   │   │   │   │   │   └── types-pyopenssl v24.1.0.20240722
│   │   │   │   │   │       ├── cryptography v50.0.0 (*)
│   │   │   │   │   │       └── types-cffi v2.0.0.20260518
│   │   │   │   │   │           └── types-setuptools v84.0.0.20260812
│   │   │   │   │   ├── pymemcache v4.0.0 (extra: memcached)
│   │   │   │   │   ├── redis v8.1.0 (extra: redis)
│   │   │   │   │   ├── faiss-cpu v1.15.0 (extra: semantic) (*)
│   │   │   │   │   ├── numpy v2.5.2 (extra: semantic)
│   │   │   │   │   ├── lexigram-testing v0.1.3007 (extra: test) (*)
│   │   │   │   │   ├── pytest v9.1.1 (extra: test) (*)
│   │   │   │   │   ├── pytest-asyncio v1.4.0 (extra: test) (*)
│   │   │   │   │   ├── pytest-cov v7.1.0 (extra: test) (*)
│   │   │   │   │   ├── pytest-mock v3.15.1 (extra: test) (*)
│   │   │   │   │   ├── black v26.5.1 (group: dev) (*)
│   │   │   │   │   ├── mypy v2.3.1 (group: dev) (*)
│   │   │   │   │   ├── ruff v0.16.3 (group: dev)
│   │   │   │   │   └── types-redis v4.6.0.20241004 (group: dev) (*)
│   │   │   │   ├── lexigram-storage v0.1.3007 (extra: all)
│   │   │   │   │   ├── aiofiles v25.1.0
│   │   │   │   │   ├── jinja2 v3.1.6 (*)
│   │   │   │   │   ├── lexigram v0.1.3009 (*)
│   │   │   │   │   ├── lexigram-contracts v0.1.3007 (*)
│   │   │   │   │   ├── python-magic v0.4.27
│   │   │   │   │   ├── aiobotocore v2.25.1 (extra: all)
│   │   │   │   │   │   ├── aiohttp v3.14.3
│   │   │   │   │   │   │   ├── aiohappyeyeballs v2.7.1
│   │   │   │   │   │   │   ├── aiosignal v1.4.0
│   │   │   │   │   │   │   │   └── frozenlist v1.8.0
│   │   │   │   │   │   │   ├── attrs v26.1.0
│   │   │   │   │   │   │   ├── frozenlist v1.8.0
│   │   │   │   │   │   │   ├── multidict v6.7.1
│   │   │   │   │   │   │   ├── propcache v0.5.2
│   │   │   │   │   │   │   └── yarl v1.24.5
│   │   │   │   │   │   │       ├── idna v3.19
│   │   │   │   │   │   │       ├── multidict v6.7.1
│   │   │   │   │   │   │       └── propcache v0.5.2
│   │   │   │   │   │   ├── aioitertools v0.13.0
│   │   │   │   │   │   ├── botocore v1.40.61
│   │   │   │   │   │   │   ├── jmespath v1.1.0
│   │   │   │   │   │   │   ├── python-dateutil v2.9.0.post0 (*)
│   │   │   │   │   │   │   └── urllib3 v2.7.0
│   │   │   │   │   │   ├── jmespath v1.1.0
│   │   │   │   │   │   ├── multidict v6.7.1
│   │   │   │   │   │   ├── python-dateutil v2.9.0.post0 (*)
│   │   │   │   │   │   ├── wrapt v1.17.3
│   │   │   │   │   │   └── boto3 v1.40.61 (extra: boto3)
│   │   │   │   │   │       ├── botocore v1.40.61 (*)
│   │   │   │   │   │       ├── jmespath v1.1.0
│   │   │   │   │   │       └── s3transfer v0.14.0
│   │   │   │   │   │           └── botocore v1.40.61 (*)
│   │   │   │   │   ├── azure-storage-blob v12.30.0 (extra: all)
│   │   │   │   │   │   ├── azure-core v1.41.0
│   │   │   │   │   │   │   ├── requests v2.34.2 (*)
│   │   │   │   │   │   │   └── typing-extensions v4.16.0
│   │   │   │   │   │   ├── cryptography v50.0.0 (*)
│   │   │   │   │   │   ├── isodate v0.7.2
│   │   │   │   │   │   └── typing-extensions v4.16.0
│   │   │   │   │   ├── gcloud-aio-storage v9.6.4 (extra: all)
│   │   │   │   │   │   ├── aiofiles v25.1.0
│   │   │   │   │   │   ├── gcloud-aio-auth v5.5.0
│   │   │   │   │   │   │   ├── aiohttp v3.14.3 (*)
│   │   │   │   │   │   │   ├── chardet v7.6.0
│   │   │   │   │   │   │   ├── cryptography v50.0.0 (*)
│   │   │   │   │   │   │   ├── pyjwt v2.13.0 (*)
│   │   │   │   │   │   │   └── tenacity v9.1.4
│   │   │   │   │   │   ├── pyasn1-modules v0.4.2
│   │   │   │   │   │   │   └── pyasn1 v0.6.4
│   │   │   │   │   │   └── rsa v4.9.1
│   │   │   │   │   │       └── pyasn1 v0.6.4
│   │   │   │   │   ├── lexigram-testing v0.1.3007 (extra: all) (*)
│   │   │   │   │   ├── pytest v9.1.1 (extra: all) (*)
│   │   │   │   │   ├── pytest-asyncio v1.4.0 (extra: all) (*)
│   │   │   │   │   ├── pytest-cov v7.1.0 (extra: all) (*)
│   │   │   │   │   ├── pytest-mock v3.15.1 (extra: all) (*)
│   │   │   │   │   ├── types-aiobotocore[s3] v3.9.0 (extra: all)
│   │   │   │   │   │   ├── botocore-stubs v1.43.67
│   │   │   │   │   │   └── types-aiobotocore-s3 v3.9.0 (extra: s3)
│   │   │   │   │   ├── aiobotocore v2.25.1 (extra: aws) (*)
│   │   │   │   │   ├── types-aiobotocore[s3] v3.9.0 (extra: aws) (*)
│   │   │   │   │   ├── azure-storage-blob v12.30.0 (extra: azure) (*)
│   │   │   │   │   ├── black v26.5.1 (extra: dev) (*)
│   │   │   │   │   ├── mypy v2.3.1 (extra: dev) (*)
│   │   │   │   │   ├── ruff v0.16.3 (extra: dev)
│   │   │   │   │   ├── gcloud-aio-storage v9.6.4 (extra: gcp) (*)
│   │   │   │   │   ├── lexigram-testing v0.1.3007 (extra: test) (*)
│   │   │   │   │   ├── pytest v9.1.1 (extra: test) (*)
│   │   │   │   │   ├── pytest-asyncio v1.4.0 (extra: test) (*)
│   │   │   │   │   ├── pytest-cov v7.1.0 (extra: test) (*)
│   │   │   │   │   ├── pytest-mock v3.15.1 (extra: test) (*)
│   │   │   │   │   ├── black v26.5.1 (group: dev) (*)
│   │   │   │   │   ├── mypy v2.3.1 (group: dev) (*)
│   │   │   │   │   └── ruff v0.16.3 (group: dev)
│   │   │   │   ├── starlette v1.6.0 (extra: all) (*)
│   │   │   │   ├── lexigram-auth v0.1.3007 (extra: auth) (*)
│   │   │   │   ├── lexigram-cache v0.1.3007 (extra: cache) (*)
│   │   │   │   ├── aiosqlite v0.22.1 (extra: db)
│   │   │   │   ├── asyncpg v0.31.0 (extra: db)
│   │   │   │   ├── black v26.5.1 (extra: dev) (*)
│   │   │   │   ├── mypy v2.3.1 (extra: dev) (*)
│   │   │   │   ├── ruff v0.16.3 (extra: dev)
│   │   │   │   ├── aiokafka v0.14.0 (extra: integration)
│   │   │   │   │   ├── async-timeout v5.0.1
│   │   │   │   │   ├── packaging v26.3
│   │   │   │   │   └── typing-extensions v4.16.0
│   │   │   │   ├── aiosqlite v0.22.1 (extra: integration)
│   │   │   │   ├── asyncpg v0.31.0 (extra: integration)
│   │   │   │   ├── elasticsearch[async] v9.5.0 (extra: integration)
│   │   │   │   │   ├── anyio v4.14.2 (*)
│   │   │   │   │   ├── elastic-transport v9.4.2
│   │   │   │   │   │   ├── certifi v2026.7.22
│   │   │   │   │   │   ├── sniffio v1.3.1
│   │   │   │   │   │   └── urllib3 v2.7.0
│   │   │   │   │   ├── python-dateutil v2.9.0.post0 (*)
│   │   │   │   │   ├── sniffio v1.3.1
│   │   │   │   │   ├── typing-extensions v4.16.0
│   │   │   │   │   └── aiohttp v3.14.3 (extra: async) (*)
│   │   │   │   ├── motor v3.7.1 (extra: integration) (*)
│   │   │   │   ├── neo4j v6.2.0 (extra: integration)
│   │   │   │   │   └── pytz v2026.3.post1
│   │   │   │   ├── qdrant-client v1.19.0 (extra: integration)
│   │   │   │   │   ├── grpcio v1.78.0
│   │   │   │   │   │   └── typing-extensions v4.16.0
│   │   │   │   │   ├── httpx[http2] v0.28.1 (*)
│   │   │   │   │   ├── numpy v2.5.2
│   │   │   │   │   ├── portalocker v3.2.0
│   │   │   │   │   ├── protobuf v6.33.6
│   │   │   │   │   ├── pydantic v2.13.4 (*)
│   │   │   │   │   └── urllib3 v2.7.0
│   │   │   │   ├── redis v8.1.0 (extra: integration)
│   │   │   │   ├── lexigram-storage v0.1.3007 (extra: storage) (*)
│   │   │   │   ├── httpx v0.28.1 (extra: web) (*)
│   │   │   │   ├── httpx2 v2.12.0 (extra: web) (*)
│   │   │   │   ├── starlette v1.6.0 (extra: web) (*)
│   │   │   │   ├── black v26.5.1 (group: dev) (*)
│   │   │   │   ├── mypy v2.3.1 (group: dev) (*)
│   │   │   │   └── ruff v0.16.3 (group: dev)
│   │   │   ├── pytest v9.1.1 (extra: test) (*)
│   │   │   ├── pytest-asyncio v1.4.0 (extra: test) (*)
│   │   │   ├── pytest-cov v7.1.0 (extra: test) (*)
│   │   │   ├── pytest-mock v3.15.1 (extra: test) (*)
│   │   │   ├── mypy v2.3.1 (group: dev) (*)
│   │   │   └── ruff v0.16.3 (group: dev)
│   │   ├── markupsafe v3.0.3
│   │   ├── orjson v3.12.0
│   │   ├── pydantic v2.13.4 (*)
│   │   ├── pyotp v2.10.0
│   │   ├── python-multipart v0.0.32
│   │   ├── pyyaml v6.0.3
│   │   ├── segno v1.6.6
│   │   ├── starlette v1.6.0 (*)
│   │   ├── typer v0.27.1 (*)
│   │   ├── lexigram-auth v0.1.3007 (extra: auth) (*)
│   │   ├── pysaml2 v7.5.4 (extra: auth) (*)
│   │   ├── xmlsec v1.3.17 (extra: auth) (*)
│   │   ├── lexigram-cache v0.1.3007 (extra: cache) (*)
│   │   ├── black v26.5.1 (extra: dev) (*)
│   │   ├── mypy v2.3.1 (extra: dev) (*)
│   │   ├── ruff v0.16.3 (extra: dev)
│   │   ├── lexigram-events v0.1.3007 (extra: events)
│   │   │   ├── jinja2 v3.1.6 (*)
│   │   │   ├── lexigram v0.1.3009 (*)
│   │   │   ├── lexigram-contracts v0.1.3007 (*)
│   │   │   ├── starlette v1.6.0 (*)
│   │   │   ├── typer v0.27.1 (*)
│   │   │   ├── typing-extensions v4.16.0
│   │   │   ├── aio-pika v10.0.1 (extra: all)
│   │   │   │   ├── aiormq v7.0.0
│   │   │   │   │   ├── pamqp v4.0.1
│   │   │   │   │   └── yarl v1.24.5 (*)
│   │   │   │   └── yarl v1.24.5 (*)
│   │   │   ├── aiokafka v0.14.0 (extra: all) (*)
│   │   │   ├── aiosqlite v0.22.1 (extra: all)
│   │   │   ├── asyncpg v0.31.0 (extra: all)
│   │   │   ├── azure-servicebus v7.14.3 (extra: all)
│   │   │   │   ├── azure-core v1.41.0 (*)
│   │   │   │   ├── isodate v0.7.2
│   │   │   │   └── typing-extensions v4.16.0
│   │   │   ├── lexigram-testing v0.1.3007 (extra: all) (*)
│   │   │   ├── motor v3.7.1 (extra: all) (*)
│   │   │   ├── pytest v9.1.1 (extra: all) (*)
│   │   │   ├── pytest-asyncio v1.4.0 (extra: all) (*)
│   │   │   ├── pytest-cov v7.1.0 (extra: all) (*)
│   │   │   ├── pytest-mock v3.15.1 (extra: all) (*)
│   │   │   ├── azure-servicebus v7.14.3 (extra: azure) (*)
│   │   │   ├── black v26.5.1 (extra: dev) (*)
│   │   │   ├── mypy v2.3.1 (extra: dev) (*)
│   │   │   ├── ruff v0.16.3 (extra: dev)
│   │   │   ├── aiokafka v0.14.0 (extra: kafka) (*)
│   │   │   ├── aio-pika v10.0.1 (extra: messaging) (*)
│   │   │   ├── aiokafka v0.14.0 (extra: messaging) (*)
│   │   │   ├── azure-servicebus v7.14.3 (extra: messaging) (*)
│   │   │   ├── motor v3.7.1 (extra: mongo) (*)
│   │   │   ├── asyncpg v0.31.0 (extra: postgres)
│   │   │   ├── aio-pika v10.0.1 (extra: rabbitmq) (*)
│   │   │   ├── aiosqlite v0.22.1 (extra: sqlite)
│   │   │   ├── lexigram-testing v0.1.3007 (extra: test) (*)
│   │   │   ├── pytest v9.1.1 (extra: test) (*)
│   │   │   ├── pytest-asyncio v1.4.0 (extra: test) (*)
│   │   │   ├── pytest-cov v7.1.0 (extra: test) (*)
│   │   │   ├── pytest-mock v3.15.1 (extra: test) (*)
│   │   │   ├── black v26.5.1 (group: dev) (*)
│   │   │   ├── mypy v2.3.1 (group: dev) (*)
│   │   │   └── ruff v0.16.3 (group: dev)
│   │   ├── openpyxl v3.1.5 (extra: export)
│   │   │   └── et-xmlfile v2.0.0
│   │   ├── reportlab v5.0.0 (extra: export)
│   │   │   ├── charset-normalizer v3.5.1
│   │   │   └── pillow v12.3.0
│   │   ├── authlib v1.7.2 (extra: full) (*)
│   │   ├── ldap3 v2.9.1 (extra: full) (*)
│   │   ├── lexigram-auth v0.1.3007 (extra: full) (*)
│   │   ├── lexigram-cache v0.1.3007 (extra: full) (*)
│   │   ├── lexigram-events v0.1.3007 (extra: full) (*)
│   │   ├── lexigram-tasks v0.1.3007 (extra: full)
│   │   │   ├── croniter v6.2.4
│   │   │   │   └── python-dateutil v2.9.0.post0 (*)
│   │   │   ├── jinja2 v3.1.6 (*)
│   │   │   ├── lexigram v0.1.3009 (*)
│   │   │   ├── lexigram-contracts v0.1.3007 (*)
│   │   │   ├── psutil v7.2.2
│   │   │   ├── starlette v1.6.0 (*)
│   │   │   ├── typer v0.27.1 (*)
│   │   │   ├── typing-extensions v4.16.0
│   │   │   ├── aio-pika v10.0.1 (extra: all) (*)
│   │   │   ├── lexigram-testing v0.1.3007 (extra: all) (*)
│   │   │   ├── pika v1.4.4 (extra: all)
│   │   │   ├── pytest v9.1.1 (extra: all) (*)
│   │   │   ├── pytest-asyncio v1.4.0 (extra: all) (*)
│   │   │   ├── pytest-cov v7.1.0 (extra: all) (*)
│   │   │   ├── pytest-mock v3.15.1 (extra: all) (*)
│   │   │   ├── redis v8.1.0 (extra: all)
│   │   │   ├── rq v2.11.0 (extra: all)
│   │   │   │   ├── click v8.4.2
│   │   │   │   ├── croniter v6.2.4 (*)
│   │   │   │   └── redis v8.1.0
│   │   │   ├── black v26.5.1 (extra: dev) (*)
│   │   │   ├── mypy v2.3.1 (extra: dev) (*)
│   │   │   ├── ruff v0.16.3 (extra: dev)
│   │   │   ├── types-croniter v6.2.4.20260711 (extra: dev)
│   │   │   ├── aio-pika v10.0.1 (extra: rabbitmq) (*)
│   │   │   ├── pika v1.4.4 (extra: rabbitmq)
│   │   │   ├── redis v8.1.0 (extra: redis)
│   │   │   ├── rq v2.11.0 (extra: redis) (*)
│   │   │   ├── lexigram-testing v0.1.3007 (extra: test) (*)
│   │   │   ├── pytest v9.1.1 (extra: test) (*)
│   │   │   ├── pytest-asyncio v1.4.0 (extra: test) (*)
│   │   │   ├── pytest-cov v7.1.0 (extra: test) (*)
│   │   │   ├── pytest-mock v3.15.1 (extra: test) (*)
│   │   │   ├── black v26.5.1 (group: dev) (*)
│   │   │   ├── mypy v2.3.1 (group: dev) (*)
│   │   │   ├── ruff v0.16.3 (group: dev)
│   │   │   └── types-croniter v6.2.4.20260711 (group: dev)
│   │   ├── lexigram-web v0.1.3007 (extra: full)
│   │   │   ├── aiofiles v25.1.0
│   │   │   ├── jinja2 v3.1.6 (*)
│   │   │   ├── lexigram v0.1.3009 (*)
│   │   │   ├── lexigram-contracts v0.1.3007 (*)
│   │   │   ├── markupsafe v3.0.3
│   │   │   ├── orjson v3.12.0
│   │   │   ├── starlette v1.6.0 (*)
│   │   │   ├── typing-extensions v4.16.0
│   │   │   ├── granian v2.8.1 (extra: all)
│   │   │   │   └── click v8.4.2
│   │   │   ├── httpx v0.28.1 (extra: all) (*)
│   │   │   ├── httpx2 v2.12.0 (extra: all) (*)
│   │   │   ├── itsdangerous v2.2.0 (extra: all)
│   │   │   ├── jinja2 v3.1.6 (extra: all) (*)
│   │   │   ├── lexigram-testing v0.1.3007 (extra: all) (*)
│   │   │   ├── pytest v9.1.1 (extra: all) (*)
│   │   │   ├── pytest-asyncio v1.4.0 (extra: all) (*)
│   │   │   ├── pytest-cov v7.1.0 (extra: all) (*)
│   │   │   ├── pytest-mock v3.15.1 (extra: all) (*)
│   │   │   ├── pyyaml v6.0.3 (extra: all)
│   │   │   ├── uvicorn[standard] v0.52.4 (extra: all) (*)
│   │   │   ├── websockets v17.0.1 (extra: all)
│   │   │   ├── httpx v0.28.1 (extra: client) (*)
│   │   │   ├── httpx2 v2.12.0 (extra: client) (*)
│   │   │   ├── black v26.5.1 (extra: dev) (*)
│   │   │   ├── mypy v2.3.1 (extra: dev) (*)
│   │   │   ├── ruff v0.16.3 (extra: dev)
│   │   │   ├── types-aiofiles v25.1.0.20260518 (extra: dev)
│   │   │   ├── pyyaml v6.0.3 (extra: docs)
│   │   │   ├── granian v2.8.1 (extra: granian) (*)
│   │   │   ├── hypercorn v0.18.0 (extra: hypercorn)
│   │   │   │   ├── h11 v0.16.0
│   │   │   │   ├── h2 v4.4.1 (*)
│   │   │   │   ├── priority v2.0.0
│   │   │   │   └── wsproto v1.3.2
│   │   │   │       └── h11 v0.16.0
│   │   │   ├── itsdangerous v2.2.0 (extra: security)
│   │   │   ├── jinja2 v3.1.6 (extra: templates) (*)
│   │   │   ├── httpx v0.28.1 (extra: test) (*)
│   │   │   ├── httpx2 v2.12.0 (extra: test) (*)
│   │   │   ├── lexigram-testing v0.1.3007 (extra: test) (*)
│   │   │   ├── pytest v9.1.1 (extra: test) (*)
│   │   │   ├── pytest-asyncio v1.4.0 (extra: test) (*)
│   │   │   ├── pytest-cov v7.1.0 (extra: test) (*)
│   │   │   ├── pytest-mock v3.15.1 (extra: test) (*)
│   │   │   ├── uvicorn[standard] v0.52.4 (extra: uvicorn) (*)
│   │   │   ├── websockets v17.0.1 (extra: websocket)
│   │   │   ├── black v26.5.1 (group: dev) (*)
│   │   │   ├── mypy v2.3.1 (group: dev) (*)
│   │   │   ├── ruff v0.16.3 (group: dev)
│   │   │   └── types-aiofiles v25.1.0.20260518 (group: dev)
│   │   ├── openpyxl v3.1.5 (extra: full) (*)
│   │   ├── pysaml2 v7.5.4 (extra: full) (*)
│   │   ├── reportlab v5.0.0 (extra: full) (*)
│   │   ├── xmlsec v1.3.17 (extra: full) (*)
│   │   ├── ldap3 v2.9.1 (extra: ldap) (*)
│   │   ├── lexigram-monitor v0.1.3007 (extra: monitor)
│   │   │   ├── lexigram v0.1.3009 (*)
│   │   │   ├── lexigram-contracts v0.1.3007 (*)
│   │   │   ├── starlette v1.6.0 (*)
│   │   │   ├── typer v0.27.1 (*)
│   │   │   ├── typing-extensions v4.16.0
│   │   │   ├── lexigram-testing v0.1.3007 (extra: all) (*)
│   │   │   ├── opentelemetry-distro v0.65b0 (extra: all)
│   │   │   │   ├── opentelemetry-api v1.44.0 (*)
│   │   │   │   ├── opentelemetry-instrumentation v0.65b0
│   │   │   │   │   ├── opentelemetry-api v1.44.0 (*)
│   │   │   │   │   ├── opentelemetry-semantic-conventions v0.65b0 (*)
│   │   │   │   │   ├── packaging v26.3
│   │   │   │   │   └── wrapt v1.17.3
│   │   │   │   └── opentelemetry-sdk v1.44.0 (*)
│   │   │   ├── opentelemetry-exporter-otlp v1.44.0 (extra: all)
│   │   │   │   ├── opentelemetry-exporter-otlp-proto-grpc v1.44.0
│   │   │   │   │   ├── googleapis-common-protos v1.75.1
│   │   │   │   │   │   ├── protobuf v6.33.6
│   │   │   │   │   │   └── grpcio v1.78.0 (extra: grpc) (*)
│   │   │   │   │   ├── grpcio v1.78.0 (*)
│   │   │   │   │   ├── opentelemetry-api v1.44.0 (*)
│   │   │   │   │   ├── opentelemetry-exporter-otlp-proto-common v1.44.0
│   │   │   │   │   │   └── opentelemetry-proto v1.44.0
│   │   │   │   │   │       └── protobuf v6.33.6
│   │   │   │   │   ├── opentelemetry-proto v1.44.0 (*)
│   │   │   │   │   ├── opentelemetry-sdk v1.44.0 (*)
│   │   │   │   │   └── typing-extensions v4.16.0
│   │   │   │   └── opentelemetry-exporter-otlp-proto-http v1.44.0
│   │   │   │       ├── googleapis-common-protos v1.75.1 (*)
│   │   │   │       ├── opentelemetry-api v1.44.0 (*)
│   │   │   │       ├── opentelemetry-exporter-otlp-proto-common v1.44.0 (*)
│   │   │   │       ├── opentelemetry-proto v1.44.0 (*)
│   │   │   │       ├── opentelemetry-sdk v1.44.0 (*)
│   │   │   │       ├── requests v2.34.2 (*)
│   │   │   │       └── typing-extensions v4.16.0
│   │   │   ├── opentelemetry-instrumentation v0.65b0 (extra: all) (*)
│   │   │   ├── prometheus-client v0.26.0 (extra: all)
│   │   │   ├── psutil v7.2.2 (extra: all)
│   │   │   ├── pytest v9.1.1 (extra: all) (*)
│   │   │   ├── pytest-asyncio v1.4.0 (extra: all) (*)
│   │   │   ├── pytest-cov v7.1.0 (extra: all) (*)
│   │   │   ├── pytest-mock v3.15.1 (extra: all) (*)
│   │   │   ├── black v26.5.1 (extra: dev) (*)
│   │   │   ├── mypy v2.3.1 (extra: dev) (*)
│   │   │   ├── ruff v0.16.3 (extra: dev)
│   │   │   ├── opentelemetry-distro v0.65b0 (extra: otel) (*)
│   │   │   ├── opentelemetry-exporter-otlp v1.44.0 (extra: otel) (*)
│   │   │   ├── opentelemetry-instrumentation v0.65b0 (extra: otel) (*)
│   │   │   ├── prometheus-client v0.26.0 (extra: prometheus)
│   │   │   ├── psutil v7.2.2 (extra: system)
│   │   │   ├── lexigram-tasks v0.1.3007 (extra: test) (*)
│   │   │   ├── lexigram-testing v0.1.3007 (extra: test) (*)
│   │   │   ├── pytest v9.1.1 (extra: test) (*)
│   │   │   ├── pytest-asyncio v1.4.0 (extra: test) (*)
│   │   │   ├── pytest-cov v7.1.0 (extra: test) (*)
│   │   │   ├── pytest-mock v3.15.1 (extra: test) (*)
│   │   │   ├── black v26.5.1 (group: dev) (*)
│   │   │   ├── mypy v2.3.1 (group: dev) (*)
│   │   │   └── ruff v0.16.3 (group: dev)
│   │   ├── authlib v1.7.2 (extra: oauth2) (*)
│   │   ├── pysaml2 v7.5.4 (extra: saml) (*)
│   │   ├── xmlsec v1.3.17 (extra: saml) (*)
│   │   ├── lexigram-search v0.1.3007 (extra: search)
│   │   │   ├── jinja2 v3.1.6 (*)
│   │   │   ├── lexigram v0.1.3009 (*)
│   │   │   ├── lexigram-contracts v0.1.3007 (*)
│   │   │   ├── typing-extensions v4.16.0
│   │   │   ├── algoliasearch v4.45.0 (extra: algolia)
│   │   │   │   ├── aiohttp v3.14.3 (*)
│   │   │   │   ├── async-timeout v5.0.1
│   │   │   │   ├── pydantic v2.13.4 (*)
│   │   │   │   ├── python-dateutil v2.9.0.post0 (*)
│   │   │   │   ├── requests v2.34.2 (*)
│   │   │   │   └── urllib3 v2.7.0
│   │   │   ├── algoliasearch v4.45.0 (extra: all) (*)
│   │   │   ├── elasticsearch v9.5.0 (extra: all) (*)
│   │   │   ├── lexigram-testing v0.1.3007 (extra: all) (*)
│   │   │   ├── meilisearch v0.43.0 (extra: all)
│   │   │   │   ├── camel-converter[pydantic] v5.1.0
│   │   │   │   │   └── pydantic v2.13.4 (extra: pydantic) (*)
│   │   │   │   └── requests v2.34.2 (*)
│   │   │   ├── pytest v9.1.1 (extra: all) (*)
│   │   │   ├── pytest-asyncio v1.4.0 (extra: all) (*)
│   │   │   ├── pytest-cov v7.1.0 (extra: all) (*)
│   │   │   ├── pytest-mock v3.15.1 (extra: all) (*)
│   │   │   ├── aiomysql v0.3.2 (extra: database) (*)
│   │   │   ├── aiosqlite v0.22.1 (extra: database)
│   │   │   ├── asyncpg v0.31.0 (extra: database)
│   │   │   ├── black v26.5.1 (extra: dev) (*)
│   │   │   ├── mypy v2.3.1 (extra: dev) (*)
│   │   │   ├── ruff v0.16.3 (extra: dev)
│   │   │   ├── elasticsearch v9.5.0 (extra: elasticsearch) (*)
│   │   │   ├── meilisearch v0.43.0 (extra: meilisearch) (*)
│   │   │   ├── motor v3.7.1 (extra: mongodb) (*)
│   │   │   ├── aiomysql v0.3.2 (extra: mysql) (*)
│   │   │   ├── asyncpg v0.31.0 (extra: postgres)
│   │   │   ├── aiomysql v0.3.2 (extra: search-all) (*)
│   │   │   ├── aiosqlite v0.22.1 (extra: search-all)
│   │   │   ├── algoliasearch v4.45.0 (extra: search-all) (*)
│   │   │   ├── asyncpg v0.31.0 (extra: search-all)
│   │   │   ├── elasticsearch v9.5.0 (extra: search-all) (*)
│   │   │   ├── meilisearch v0.43.0 (extra: search-all) (*)
│   │   │   ├── motor v3.7.1 (extra: search-all) (*)
│   │   │   ├── aiosqlite v0.22.1 (extra: sqlite)
│   │   │   ├── lexigram-testing v0.1.3007 (extra: test) (*)
│   │   │   ├── pytest v9.1.1 (extra: test) (*)
│   │   │   ├── pytest-asyncio v1.4.0 (extra: test) (*)
│   │   │   ├── pytest-cov v7.1.0 (extra: test) (*)
│   │   │   ├── pytest-mock v3.15.1 (extra: test) (*)
│   │   │   ├── black v26.5.1 (group: dev) (*)
│   │   │   ├── mypy v2.3.1 (group: dev) (*)
│   │   │   └── ruff v0.16.3 (group: dev)
│   │   ├── lexigram-tasks v0.1.3007 (extra: tasks) (*)
│   │   ├── lexigram-tenancy v0.1.3007 (extra: tenancy)
│   │   │   ├── lexigram v0.1.3009 (*)
│   │   │   ├── lexigram-contracts v0.1.3007 (*)
│   │   │   ├── typer v0.27.1 (*)
│   │   │   ├── typing-extensions v4.16.0
│   │   │   ├── lexigram-sql v0.1.3007 (extra: all) (*)
│   │   │   ├── lexigram-testing v0.1.3007 (extra: all) (*)
│   │   │   ├── lexigram-workflow v0.1.3007 (extra: all)
│   │   │   │   ├── lexigram v0.1.3009 (*)
│   │   │   │   ├── lexigram-contracts v0.1.3007 (*)
│   │   │   │   ├── typer v0.27.1 (*)
│   │   │   │   ├── typing-extensions v4.16.0
│   │   │   │   ├── mypy v2.3.1 (extra: dev) (*)
│   │   │   │   ├── ruff v0.16.3 (extra: dev)
│   │   │   │   ├── lexigram-testing v0.1.3007 (extra: test) (*)
│   │   │   │   ├── pytest v9.1.1 (extra: test) (*)
│   │   │   │   ├── pytest-asyncio v1.4.0 (extra: test) (*)
│   │   │   │   ├── pytest-cov v7.1.0 (extra: test) (*)
│   │   │   │   ├── pytest-mock v3.15.1 (extra: test) (*)
│   │   │   │   ├── mypy v2.3.1 (group: dev) (*)
│   │   │   │   └── ruff v0.16.3 (group: dev)
│   │   │   ├── mypy v2.3.1 (extra: all) (*)
│   │   │   ├── pytest v9.1.1 (extra: all) (*)
│   │   │   ├── pytest-asyncio v1.4.0 (extra: all) (*)
│   │   │   ├── pytest-cov v7.1.0 (extra: all) (*)
│   │   │   ├── pytest-mock v3.15.1 (extra: all) (*)
│   │   │   ├── ruff v0.16.3 (extra: all)
│   │   │   ├── mypy v2.3.1 (extra: dev) (*)
│   │   │   ├── ruff v0.16.3 (extra: dev)
│   │   │   ├── lexigram-sql v0.1.3007 (extra: sql) (*)
│   │   │   ├── lexigram-testing v0.1.3007 (extra: test) (*)
│   │   │   ├── lexigram-workflow v0.1.3007 (extra: test) (*)
│   │   │   ├── pytest v9.1.1 (extra: test) (*)
│   │   │   ├── pytest-asyncio v1.4.0 (extra: test) (*)
│   │   │   ├── pytest-cov v7.1.0 (extra: test) (*)
│   │   │   ├── pytest-mock v3.15.1 (extra: test) (*)
│   │   │   ├── mypy v2.3.1 (group: dev) (*)
│   │   │   └── ruff v0.16.3 (group: dev)
│   │   ├── pytest v9.1.1 (extra: test) (*)
│   │   ├── pytest-asyncio v1.4.0 (extra: test) (*)
│   │   ├── pytest-cov v7.1.0 (extra: test) (*)
│   │   ├── pytest-mock v3.15.1 (extra: test) (*)
│   │   ├── lexigram-web v0.1.3007 (extra: web) (*)
│   │   ├── black v26.5.1 (group: dev) (*)
│   │   ├── mypy v2.3.1 (group: dev) (*)
│   │   └── ruff v0.16.3 (group: dev)
│   ├── lexigram-ai v0.1.3007 (extra: all)
│   │   ├── lexigram v0.1.3009 (*)
│   │   ├── lexigram-ai-feedback v0.1.3007
│   │   │   ├── lexigram v0.1.3009 (*)
│   │   │   ├── lexigram-contracts v0.1.3007 (*)
│   │   │   ├── typing-extensions v4.16.0
│   │   │   ├── mypy v2.3.1 (extra: dev) (*)
│   │   │   ├── ruff v0.16.3 (extra: dev)
│   │   │   ├── lexigram-testing v0.1.3007 (extra: test) (*)
│   │   │   ├── pytest v9.1.1 (extra: test) (*)
│   │   │   ├── pytest-asyncio v1.4.0 (extra: test) (*)
│   │   │   ├── pytest-cov v7.1.0 (extra: test) (*)
│   │   │   ├── pytest-mock v3.15.1 (extra: test) (*)
│   │   │   ├── mypy v2.3.1 (group: dev) (*)
│   │   │   └── ruff v0.16.3 (group: dev)
│   │   ├── lexigram-ai-llm v0.1.3007
│   │   │   ├── aiohttp v3.14.3 (*)
│   │   │   ├── httpx v0.28.1 (*)
│   │   │   ├── lexigram v0.1.3009 (*)
│   │   │   ├── lexigram-contracts v0.1.3007 (*)
│   │   │   ├── pydantic v2.13.4 (*)
│   │   │   ├── starlette v1.6.0 (*)
│   │   │   ├── typing-extensions v4.16.0
│   │   │   ├── lexigram-admin v0.1.3010 (extra: admin) (*)
│   │   │   ├── anthropic v0.125.0 (extra: all)
│   │   │   │   ├── anyio v4.14.2 (*)
│   │   │   │   ├── distro v1.9.0
│   │   │   │   ├── docstring-parser v0.18.0
│   │   │   │   ├── httpx v0.28.1 (*)
│   │   │   │   ├── jiter v0.14.0
│   │   │   │   ├── pydantic v2.13.4 (*)
│   │   │   │   ├── sniffio v1.3.1
│   │   │   │   └── typing-extensions v4.16.0
│   │   │   ├── cohere v7.0.9 (extra: all)
│   │   │   │   ├── fastavro v1.12.2
│   │   │   │   ├── httpx v0.28.1 (*)
│   │   │   │   ├── pydantic v2.13.4 (*)
│   │   │   │   ├── pydantic-core v2.46.4 (*)
│   │   │   │   ├── requests v2.34.2 (*)
│   │   │   │   ├── tokenizers v0.21.4
│   │   │   │   │   └── huggingface-hub v0.36.2
│   │   │   │   │       ├── filelock v3.32.3
│   │   │   │   │       ├── fsspec v2024.12.0
│   │   │   │   │       │   └── aiohttp v3.14.3 (extra: http) (*)
│   │   │   │   │       ├── hf-xet v1.6.0
│   │   │   │   │       ├── packaging v26.3
│   │   │   │   │       ├── pyyaml v6.0.3
│   │   │   │   │       ├── requests v2.34.2 (*)
│   │   │   │   │       ├── tqdm v4.67.1
│   │   │   │   │       └── typing-extensions v4.16.0
│   │   │   │   ├── types-requests v2.33.0.20260712
│   │   │   │   │   └── urllib3 v2.7.0
│   │   │   │   └── typing-extensions v4.16.0
│   │   │   ├── groq v1.6.0 (extra: all)
│   │   │   │   ├── anyio v4.14.2 (*)
│   │   │   │   ├── distro v1.9.0
│   │   │   │   ├── httpx v0.28.1 (*)
│   │   │   │   ├── pydantic v2.13.4 (*)
│   │   │   │   ├── sniffio v1.3.1
│   │   │   │   └── typing-extensions v4.16.0
│   │   │   ├── instructor v1.15.4 (extra: all)
│   │   │   │   ├── aiohttp v3.14.3 (*)
│   │   │   │   ├── docstring-parser v0.18.0
│   │   │   │   ├── jinja2 v3.1.6 (*)
│   │   │   │   ├── jiter v0.14.0
│   │   │   │   ├── openai v2.54.0 (*)
│   │   │   │   ├── pydantic v2.13.4 (*)
│   │   │   │   ├── pydantic-core v2.46.4 (*)
│   │   │   │   ├── requests v2.34.2 (*)
│   │   │   │   ├── rich v13.9.4 (*)
│   │   │   │   ├── tenacity v9.1.4
│   │   │   │   └── typer v0.27.1 (*)
│   │   │   ├── jinja2 v3.1.6 (extra: all) (*)
│   │   │   ├── mistralai v2.9.3 (extra: all)
│   │   │   │   ├── eval-type-backport v0.4.0
│   │   │   │   ├── httpx v0.28.1 (*)
│   │   │   │   ├── jsonpath-python v1.1.6
│   │   │   │   ├── opentelemetry-api v1.44.0 (*)
│   │   │   │   ├── opentelemetry-semantic-conventions v0.65b0 (*)
│   │   │   │   ├── pydantic v2.13.4 (*)
│   │   │   │   ├── python-dateutil v2.9.0.post0 (*)
│   │   │   │   └── typing-inspection v0.4.4 (*)
│   │   │   ├── ollama v0.6.2 (extra: all) (*)
│   │   │   ├── openai v2.54.0 (extra: all) (*)
│   │   │   ├── redis v8.1.0 (extra: all)
│   │   │   ├── tiktoken v0.14.0 (extra: all)
│   │   │   │   ├── regex v2026.7.19
│   │   │   │   └── requests v2.34.2 (*)
│   │   │   ├── transformers v4.50.0 (extra: all)
│   │   │   │   ├── filelock v3.32.3
│   │   │   │   ├── huggingface-hub v0.36.2 (*)
│   │   │   │   ├── numpy v2.5.2
│   │   │   │   ├── packaging v26.3
│   │   │   │   ├── pyyaml v6.0.3
│   │   │   │   ├── regex v2026.7.19
│   │   │   │   ├── requests v2.34.2 (*)
│   │   │   │   ├── safetensors v0.5.3
│   │   │   │   ├── tokenizers v0.21.4 (*)
│   │   │   │   └── tqdm v4.67.1
│   │   │   ├── anthropic v0.125.0 (extra: anthropic) (*)
│   │   │   ├── redis v8.1.0 (extra: cache)
│   │   │   ├── cohere v7.0.9 (extra: cohere) (*)
│   │   │   ├── mypy v2.3.1 (extra: dev) (*)
│   │   │   ├── ruff v0.16.3 (extra: dev)
│   │   │   ├── groq v1.6.0 (extra: groq) (*)
│   │   │   ├── transformers v4.50.0 (extra: huggingface) (*)
│   │   │   ├── mistralai v2.9.3 (extra: mistral) (*)
│   │   │   ├── ollama v0.6.2 (extra: ollama) (*)
│   │   │   ├── openai v2.54.0 (extra: openai) (*)
│   │   │   ├── tiktoken v0.14.0 (extra: openai) (*)
│   │   │   ├── jinja2 v3.1.6 (extra: prompts) (*)
│   │   │   ├── instructor v1.15.4 (extra: structured) (*)
│   │   │   ├── lexigram-testing v0.1.3007 (extra: test) (*)
│   │   │   ├── pytest v9.1.1 (extra: test) (*)
│   │   │   ├── pytest-asyncio v1.4.0 (extra: test) (*)
│   │   │   ├── pytest-cov v7.1.0 (extra: test) (*)
│   │   │   ├── pytest-mock v3.15.1 (extra: test) (*)
│   │   │   ├── mypy v2.3.1 (group: dev) (*)
│   │   │   └── ruff v0.16.3 (group: dev)
│   │   ├── lexigram-ai-observability v0.1.3007
│   │   │   ├── lexigram v0.1.3009 (*)
│   │   │   ├── lexigram-contracts v0.1.3007 (*)
│   │   │   ├── typing-extensions v4.16.0
│   │   │   ├── mypy v2.3.1 (extra: dev) (*)
│   │   │   ├── ruff v0.16.3 (extra: dev)
│   │   │   ├── lexigram-testing v0.1.3007 (extra: test) (*)
│   │   │   ├── pytest v9.1.1 (extra: test) (*)
│   │   │   ├── pytest-asyncio v1.4.0 (extra: test) (*)
│   │   │   ├── pytest-cov v7.1.0 (extra: test) (*)
│   │   │   ├── pytest-mock v3.15.1 (extra: test) (*)
│   │   │   ├── mypy v2.3.1 (group: dev) (*)
│   │   │   └── ruff v0.16.3 (group: dev)
│   │   ├── lexigram-ai-rag v0.1.3007
│   │   │   ├── aiofiles v25.1.0
│   │   │   ├── lexigram v0.1.3009 (*)
│   │   │   ├── lexigram-contracts v0.1.3007 (*)
│   │   │   ├── numpy v2.5.2
│   │   │   ├── pyyaml v6.0.3
│   │   │   ├── typing-extensions v4.16.0
│   │   │   ├── aiohttp v3.14.3 (extra: all) (*)
│   │   │   ├── beautifulsoup4 v4.15.0 (extra: all)
│   │   │   │   ├── soupsieve v2.9.2
│   │   │   │   └── typing-extensions v4.16.0
│   │   │   ├── flashrank v0.2.10 (extra: all)
│   │   │   │   ├── numpy v2.5.2
│   │   │   │   ├── onnxruntime v1.29.0
│   │   │   │   │   ├── flatbuffers v25.12.19
│   │   │   │   │   ├── numpy v2.5.2
│   │   │   │   │   ├── packaging v26.3
│   │   │   │   │   └── protobuf v6.33.6
│   │   │   │   ├── requests v2.34.2 (*)
│   │   │   │   ├── tokenizers v0.21.4 (*)
│   │   │   │   └── tqdm v4.67.1
│   │   │   ├── llmlingua v0.2.2 (extra: all)
│   │   │   │   ├── accelerate v1.6.0
│   │   │   │   │   ├── huggingface-hub v0.36.2 (*)
│   │   │   │   │   ├── numpy v2.5.2
│   │   │   │   │   ├── packaging v26.3
│   │   │   │   │   ├── psutil v7.2.2
│   │   │   │   │   ├── pyyaml v6.0.3
│   │   │   │   │   ├── safetensors v0.5.3
│   │   │   │   │   └── torch v2.9.0
│   │   │   │   │       ├── filelock v3.32.3
│   │   │   │   │       ├── fsspec v2024.12.0 (*)
│   │   │   │   │       ├── jinja2 v3.1.6 (*)
│   │   │   │   │       ├── networkx v3.6.1
│   │   │   │   │       ├── nvidia-cublas-cu12 v12.8.4.1
│   │   │   │   │       ├── nvidia-cuda-cupti-cu12 v12.8.90
│   │   │   │   │       ├── nvidia-cuda-nvrtc-cu12 v12.8.93
│   │   │   │   │       ├── nvidia-cuda-runtime-cu12 v12.8.90
│   │   │   │   │       ├── nvidia-cudnn-cu12 v9.10.2.21
│   │   │   │   │       │   └── nvidia-cublas-cu12 v12.8.4.1
│   │   │   │   │       ├── nvidia-cufft-cu12 v11.3.3.83
│   │   │   │   │       │   └── nvidia-nvjitlink-cu12 v12.8.93
│   │   │   │   │       ├── nvidia-cufile-cu12 v1.13.1.3
│   │   │   │   │       ├── nvidia-curand-cu12 v10.3.9.90
│   │   │   │   │       ├── nvidia-cusolver-cu12 v11.7.3.90
│   │   │   │   │       │   ├── nvidia-cublas-cu12 v12.8.4.1
│   │   │   │   │       │   ├── nvidia-cusparse-cu12 v12.5.8.93
│   │   │   │   │       │   │   └── nvidia-nvjitlink-cu12 v12.8.93
│   │   │   │   │       │   └── nvidia-nvjitlink-cu12 v12.8.93
│   │   │   │   │       ├── nvidia-cusparse-cu12 v12.5.8.93 (*)
│   │   │   │   │       ├── nvidia-cusparselt-cu12 v0.7.1
│   │   │   │   │       ├── nvidia-nccl-cu12 v2.27.5
│   │   │   │   │       ├── nvidia-nvjitlink-cu12 v12.8.93
│   │   │   │   │       ├── nvidia-nvshmem-cu12 v3.3.20
│   │   │   │   │       ├── nvidia-nvtx-cu12 v12.8.90
│   │   │   │   │       ├── setuptools v80.10.2
│   │   │   │   │       ├── sympy v1.14.0
│   │   │   │   │       │   └── mpmath v1.3.0
│   │   │   │   │       ├── triton v3.5.0
│   │   │   │   │       └── typing-extensions v4.16.0
│   │   │   │   ├── nltk v3.10.3
│   │   │   │   │   ├── click v8.4.2
│   │   │   │   │   ├── defusedxml v0.7.1
│   │   │   │   │   ├── joblib v1.5.3
│   │   │   │   │   ├── regex v2026.7.19
│   │   │   │   │   └── tqdm v4.67.1
│   │   │   │   ├── numpy v2.5.2
│   │   │   │   ├── tiktoken v0.14.0 (*)
│   │   │   │   ├── torch v2.9.0 (*)
│   │   │   │   └── transformers v4.50.0 (*)
│   │   │   ├── pillow v12.3.0 (extra: all)
│   │   │   ├── pypdf2 v3.0.1 (extra: all)
│   │   │   ├── torch v2.9.0 (extra: all) (*)
│   │   │   ├── transformers v4.50.0 (extra: all) (*)
│   │   │   ├── librosa v0.11.0 (extra: audio)
│   │   │   │   ├── audioread v3.1.0
│   │   │   │   │   ├── standard-aifc v3.13.0
│   │   │   │   │   │   ├── audioop-lts v0.2.2
│   │   │   │   │   │   └── standard-chunk v3.13.0
│   │   │   │   │   └── standard-sunau v3.13.0
│   │   │   │   │       └── audioop-lts v0.2.2
│   │   │   │   ├── decorator v5.3.1
│   │   │   │   ├── joblib v1.5.3
│   │   │   │   ├── lazy-loader v0.5
│   │   │   │   │   └── packaging v26.3
│   │   │   │   ├── msgpack v1.2.1
│   │   │   │   ├── numba v0.67.0
│   │   │   │   │   ├── llvmlite v0.49.0
│   │   │   │   │   └── numpy v2.5.2
│   │   │   │   ├── numpy v2.5.2
│   │   │   │   ├── pooch v1.9.0
│   │   │   │   │   ├── packaging v26.3
│   │   │   │   │   ├── platformdirs v4.11.3
│   │   │   │   │   └── requests v2.34.2 (*)
│   │   │   │   ├── scikit-learn v1.9.0 (*)
│   │   │   │   ├── scipy v1.18.0 (*)
│   │   │   │   ├── soundfile v0.13.1
│   │   │   │   │   ├── cffi v2.1.1 (*)
│   │   │   │   │   └── numpy v2.5.2
│   │   │   │   ├── soxr v1.1.0
│   │   │   │   │   └── numpy v2.5.2
│   │   │   │   ├── standard-aifc v3.13.0 (*)
│   │   │   │   ├── standard-sunau v3.13.0 (*)
│   │   │   │   └── typing-extensions v4.16.0
│   │   │   ├── mutagen v1.48.1 (extra: audio)
│   │   │   ├── pillow v12.3.0 (extra: clip)
│   │   │   ├── torch v2.9.0 (extra: clip) (*)
│   │   │   ├── transformers v4.50.0 (extra: clip) (*)
│   │   │   ├── llmlingua v0.2.2 (extra: compression) (*)
│   │   │   ├── mypy v2.3.1 (extra: dev) (*)
│   │   │   ├── ruff v0.16.3 (extra: dev)
│   │   │   ├── pypdf2 v3.0.1 (extra: pdf)
│   │   │   ├── flashrank v0.2.10 (extra: reranking) (*)
│   │   │   ├── lexigram-testing v0.1.3007 (extra: test) (*)
│   │   │   ├── pytest v9.1.1 (extra: test) (*)
│   │   │   ├── pytest-asyncio v1.4.0 (extra: test) (*)
│   │   │   ├── pytest-cov v7.1.0 (extra: test) (*)
│   │   │   ├── pytest-mock v3.15.1 (extra: test) (*)
│   │   │   ├── opencv-python v5.0.0.93 (extra: video)
│   │   │   │   └── numpy v2.5.2
│   │   │   ├── aiohttp v3.14.3 (extra: web) (*)
│   │   │   ├── beautifulsoup4 v4.15.0 (extra: web) (*)
│   │   │   ├── mypy v2.3.1 (group: dev) (*)
│   │   │   └── ruff v0.16.3 (group: dev)
│   │   ├── lexigram-contracts v0.1.3007 (*)
│   │   ├── numpy v2.5.2
│   │   ├── starlette v1.6.0 (*)
│   │   ├── typer v0.27.1 (*)
│   │   ├── chromadb v1.5.9 (extra: ai)
│   │   │   ├── bcrypt v5.0.0
│   │   │   ├── build v1.5.0
│   │   │   │   ├── packaging v26.3
│   │   │   │   └── pyproject-hooks v1.2.0
│   │   │   ├── grpcio v1.78.0 (*)
│   │   │   ├── httpx v0.28.1 (*)
│   │   │   ├── importlib-resources v5.12.0
│   │   │   ├── jsonschema v4.26.0
│   │   │   │   ├── attrs v26.1.0
│   │   │   │   ├── jsonschema-specifications v2025.9.1
│   │   │   │   │   └── referencing v0.37.0
│   │   │   │   │       ├── attrs v26.1.0
│   │   │   │   │       └── rpds-py v2026.6.3
│   │   │   │   ├── referencing v0.37.0 (*)
│   │   │   │   └── rpds-py v2026.6.3
│   │   │   ├── kubernetes v36.0.3
│   │   │   │   ├── aiohttp v3.14.3 (*)
│   │   │   │   ├── certifi v2026.7.22
│   │   │   │   ├── durationpy v0.10
│   │   │   │   ├── python-dateutil v2.9.0.post0 (*)
│   │   │   │   ├── pyyaml v6.0.3
│   │   │   │   ├── requests v2.34.2 (*)
│   │   │   │   ├── requests-oauthlib v2.0.0
│   │   │   │   │   ├── oauthlib v3.3.1
│   │   │   │   │   └── requests v2.34.2 (*)
│   │   │   │   ├── six v1.17.0
│   │   │   │   ├── urllib3 v2.7.0
│   │   │   │   └── websocket-client v1.9.0
│   │   │   ├── mmh3 v5.2.1
│   │   │   ├── numpy v2.5.2
│   │   │   ├── onnxruntime v1.29.0 (*)
│   │   │   ├── opentelemetry-api v1.44.0 (*)
│   │   │   ├── opentelemetry-exporter-otlp-proto-grpc v1.44.0 (*)
│   │   │   ├── opentelemetry-sdk v1.44.0 (*)
│   │   │   ├── orjson v3.12.0
│   │   │   ├── overrides v7.7.0
│   │   │   ├── pybase64 v1.5.0
│   │   │   ├── pydantic v2.13.4 (*)
│   │   │   ├── pydantic-settings v2.15.0
│   │   │   │   ├── pydantic v2.13.4 (*)
│   │   │   │   ├── python-dotenv v1.2.3
│   │   │   │   └── typing-inspection v0.4.4 (*)
│   │   │   ├── pypika v0.51.1
│   │   │   ├── pyyaml v6.0.3
│   │   │   ├── rich v13.9.4 (*)
│   │   │   ├── tenacity v9.1.4
│   │   │   ├── tokenizers v0.21.4 (*)
│   │   │   ├── tqdm v4.67.1
│   │   │   ├── typer v0.27.1 (*)
│   │   │   ├── typing-extensions v4.16.0
│   │   │   └── uvicorn[standard] v0.52.4 (*)
│   │   ├── jinja2 v3.1.6 (extra: ai) (*)
│   │   ├── pgvector v0.5.0 (extra: ai)
│   │   ├── pypdf v6.16.1 (extra: ai)
│   │   ├── qdrant-client v1.19.0 (extra: ai) (*)
│   │   ├── scikit-learn v1.9.0 (extra: ai) (*)
│   │   ├── tiktoken v0.14.0 (extra: ai) (*)
│   │   ├── anthropic v0.125.0 (extra: all) (*)
│   │   ├── beautifulsoup4 v4.15.0 (extra: all) (*)
│   │   ├── black v26.5.1 (extra: all) (*)
│   │   ├── chromadb v1.5.9 (extra: all) (*)
│   │   ├── jinja2 v3.1.6 (extra: all) (*)
│   │   ├── joblib v1.5.3 (extra: all)
│   │   ├── jsonschema v4.26.0 (extra: all) (*)
│   │   ├── lexigram-ai-feedback v0.1.3007 (extra: all) (*)
│   │   ├── lexigram-ai-llm v0.1.3007 (extra: all) (*)
│   │   ├── lexigram-ai-observability v0.1.3007 (extra: all) (*)
│   │   ├── lexigram-ai-rag v0.1.3007 (extra: all) (*)
│   │   ├── lexigram-testing v0.1.3007 (extra: all) (*)
│   │   ├── lexigram-vector v0.1.3007 (extra: all)
│   │   │   ├── aiohttp v3.14.3 (*)
│   │   │   ├── lexigram v0.1.3009 (*)
│   │   │   ├── lexigram-contracts v0.1.3007 (*)
│   │   │   ├── typer v0.27.1 (*)
│   │   │   ├── aiohttp v3.14.3 (extra: all) (*)
│   │   │   ├── asyncpg v0.31.0 (extra: all)
│   │   │   ├── chromadb v1.5.9 (extra: all) (*)
│   │   │   ├── pinecone-client v6.0.0 (extra: all)
│   │   │   │   ├── certifi v2026.7.22
│   │   │   │   ├── pinecone-plugin-interface v0.0.7
│   │   │   │   ├── python-dateutil v2.9.0.post0 (*)
│   │   │   │   ├── typing-extensions v4.16.0
│   │   │   │   └── urllib3 v2.7.0
│   │   │   ├── qdrant-client v1.19.0 (extra: all) (*)
│   │   │   ├── weaviate-client v4.23.0 (extra: all)
│   │   │   │   ├── authlib v1.7.2 (*)
│   │   │   │   ├── grpcio v1.78.0 (*)
│   │   │   │   ├── httpx v0.28.1 (*)
│   │   │   │   ├── packaging v26.3
│   │   │   │   ├── protobuf v6.33.6
│   │   │   │   ├── pydantic v2.13.4 (*)
│   │   │   │   └── validators v0.35.0
│   │   │   ├── chromadb v1.5.9 (extra: chroma) (*)
│   │   │   ├── mypy v2.3.1 (extra: dev) (*)
│   │   │   ├── ruff v0.16.3 (extra: dev)
│   │   │   ├── aiohttp v3.14.3 (extra: embed) (*)
│   │   │   ├── asyncpg v0.31.0 (extra: pgvector)
│   │   │   ├── pinecone-client v6.0.0 (extra: pinecone) (*)
│   │   │   ├── qdrant-client v1.19.0 (extra: qdrant) (*)
│   │   │   ├── lexigram-testing v0.1.3007 (extra: test) (*)
│   │   │   ├── numpy v2.5.2 (extra: test)
│   │   │   ├── pytest v9.1.1 (extra: test) (*)
│   │   │   ├── pytest-asyncio v1.4.0 (extra: test) (*)
│   │   │   ├── pytest-cov v7.1.0 (extra: test) (*)
│   │   │   ├── pytest-mock v3.15.1 (extra: test) (*)
│   │   │   ├── weaviate-client v4.23.0 (extra: weaviate) (*)
│   │   │   ├── mypy v2.3.1 (group: dev) (*)
│   │   │   └── ruff v0.16.3 (group: dev)
│   │   ├── markdown v3.10.3 (extra: all)
│   │   ├── milvus v2.3.9 (extra: all)
│   │   ├── mkdocs v1.6.1 (extra: all)
│   │   │   ├── click v8.4.2
│   │   │   ├── ghp-import v2.1.0
│   │   │   │   └── python-dateutil v2.9.0.post0 (*)
│   │   │   ├── jinja2 v3.1.6 (*)
│   │   │   ├── markdown v3.10.3
│   │   │   ├── markupsafe v3.0.3
│   │   │   ├── mergedeep v1.3.4
│   │   │   ├── mkdocs-get-deps v0.2.2
│   │   │   │   ├── mergedeep v1.3.4
│   │   │   │   ├── platformdirs v4.11.3
│   │   │   │   └── pyyaml v6.0.3
│   │   │   ├── packaging v26.3
│   │   │   ├── pathspec v1.1.1
│   │   │   ├── pyyaml v6.0.3
│   │   │   ├── pyyaml-env-tag v1.1
│   │   │   │   └── pyyaml v6.0.3
│   │   │   └── watchdog v6.0.0
│   │   ├── mkdocs-material v9.7.7 (extra: all)
│   │   │   ├── babel v2.18.0
│   │   │   ├── backrefs v8.0
│   │   │   ├── colorama v0.4.6
│   │   │   ├── jinja2 v3.1.6 (*)
│   │   │   ├── markdown v3.10.3
│   │   │   ├── mkdocs v1.6.1 (*)
│   │   │   ├── mkdocs-material-extensions v1.3.1
│   │   │   ├── paginate v0.5.7
│   │   │   ├── pygments v2.21.0
│   │   │   ├── pymdown-extensions v11.0.1
│   │   │   │   ├── markdown v3.10.3
│   │   │   │   └── pyyaml v6.0.3
│   │   │   └── requests v2.34.2 (*)
│   │   ├── mypy v2.3.1 (extra: all) (*)
│   │   ├── numpy v2.5.2 (extra: all)
│   │   ├── ollama v0.6.2 (extra: all) (*)
│   │   ├── openai v2.54.0 (extra: all) (*)
│   │   ├── pgvector v0.5.0 (extra: all)
│   │   ├── pinecone-client v6.0.0 (extra: all) (*)
│   │   ├── pre-commit v4.6.2 (extra: all)
│   │   │   ├── cfgv v3.5.0
│   │   │   ├── identify v2.6.19
│   │   │   ├── nodeenv v1.10.0
│   │   │   ├── pyyaml v6.0.3
│   │   │   └── virtualenv v21.7.4
│   │   │       ├── distlib v0.4.3
│   │   │       ├── filelock v3.32.3
│   │   │       ├── platformdirs v4.11.3
│   │   │       └── python-discovery v1.5.2
│   │   │           └── filelock v3.32.3
│   │   ├── psycopg[binary] v3.3.4 (extra: all)
│   │   │   └── psycopg-binary v3.3.4 (extra: binary)
│   │   ├── pypdf v6.16.1 (extra: all)
│   │   ├── pytest v9.1.1 (extra: all) (*)
│   │   ├── pytest-asyncio v1.4.0 (extra: all) (*)
│   │   ├── pytest-cov v7.1.0 (extra: all) (*)
│   │   ├── pytest-mock v3.15.1 (extra: all) (*)
│   │   ├── pyyaml v6.0.3 (extra: all)
│   │   ├── qdrant-client v1.19.0 (extra: all) (*)
│   │   ├── redis v8.1.0 (extra: all)
│   │   ├── ruff v0.16.3 (extra: all)
│   │   ├── scikit-learn v1.9.0 (extra: all) (*)
│   │   ├── scipy v1.18.0 (extra: all) (*)
│   │   ├── sentence-transformers v5.7.0 (extra: all)
│   │   │   ├── huggingface-hub v0.36.2 (*)
│   │   │   ├── numpy v2.5.2
│   │   │   ├── scikit-learn v1.9.0 (*)
│   │   │   ├── scipy v1.18.0 (*)
│   │   │   ├── tokenizers v0.21.4 (*)
│   │   │   ├── torch v2.9.0 (*)
│   │   │   ├── tqdm v4.67.1
│   │   │   ├── transformers v4.50.0 (*)
│   │   │   └── typing-extensions v4.16.0
│   │   ├── tiktoken v0.14.0 (extra: all) (*)
│   │   ├── weaviate-client v4.23.0 (extra: all) (*)
│   │   ├── xgboost v3.4.1 (extra: all) (*)
│   │   ├── black v26.5.1 (extra: dev) (*)
│   │   ├── mypy v2.3.1 (extra: dev) (*)
│   │   ├── pre-commit v4.6.2 (extra: dev) (*)
│   │   ├── ruff v0.16.3 (extra: dev)
│   │   ├── types-beautifulsoup4 v4.12.0.20250516 (extra: dev)
│   │   │   └── types-html5lib v1.1.11.20260518
│   │   │       └── types-webencodings v0.5.0.20260408
│   │   ├── types-pillow v10.2.0.20240822 (extra: dev)
│   │   ├── types-pyyaml v6.0.12.20260815 (extra: dev)
│   │   ├── types-requests v2.33.0.20260712 (extra: dev) (*)
│   │   ├── mkdocs v1.6.1 (extra: docs) (*)
│   │   ├── mkdocs-material v9.7.7 (extra: docs) (*)
│   │   ├── lexigram-ai-feedback v0.1.3007 (extra: feedback) (*)
│   │   ├── anthropic v0.125.0 (extra: llm) (*)
│   │   ├── lexigram-ai-llm v0.1.3007 (extra: llm) (*)
│   │   ├── ollama v0.6.2 (extra: llm) (*)
│   │   ├── openai v2.54.0 (extra: llm) (*)
│   │   ├── openrouter v0.10.8 (extra: llm)
│   │   │   ├── httpcore v1.0.9 (*)
│   │   │   ├── httpx v0.28.1 (*)
│   │   │   ├── jsonpath-python v1.1.6
│   │   │   └── pydantic v2.13.4 (*)
│   │   ├── jinja2 v3.1.6 (extra: llm-utils) (*)
│   │   ├── redis v8.1.0 (extra: llm-utils)
│   │   ├── tiktoken v0.14.0 (extra: llm-utils) (*)
│   │   ├── lexigram-ai-observability v0.1.3007 (extra: observability) (*)
│   │   ├── beautifulsoup4 v4.15.0 (extra: rag) (*)
│   │   ├── lexigram-ai-rag v0.1.3007 (extra: rag) (*)
│   │   ├── markdown v3.10.3 (extra: rag)
│   │   ├── opencv-python-headless v5.0.0.93 (extra: rag)
│   │   │   └── numpy v2.5.2
│   │   ├── pillow v12.3.0 (extra: rag)
│   │   ├── pypdf v6.16.1 (extra: rag)
│   │   ├── sentence-transformers v5.7.0 (extra: rag) (*)
│   │   ├── jsonschema v4.26.0 (extra: test) (*)
│   │   ├── lexigram-testing v0.1.3007 (extra: test) (*)
│   │   ├── pytest v9.1.1 (extra: test) (*)
│   │   ├── pytest-asyncio v1.4.0 (extra: test) (*)
│   │   ├── pytest-cov v7.1.0 (extra: test) (*)
│   │   ├── pytest-mock v3.15.1 (extra: test) (*)
│   │   ├── pyyaml v6.0.3 (extra: test)
│   │   ├── chromadb v1.5.9 (extra: vector) (*)
│   │   ├── lexigram-vector v0.1.3007 (extra: vector) (*)
│   │   ├── milvus v2.3.9 (extra: vector)
│   │   ├── pgvector v0.5.0 (extra: vector)
│   │   ├── pinecone-client v6.0.0 (extra: vector) (*)
│   │   ├── psycopg[binary] v3.3.4 (extra: vector) (*)
│   │   ├── qdrant-client v1.19.0 (extra: vector) (*)
│   │   ├── weaviate-client v4.23.0 (extra: vector) (*)
│   │   ├── black v26.5.1 (group: dev) (*)
│   │   ├── mypy v2.3.1 (group: dev) (*)
│   │   ├── pre-commit v4.6.2 (group: dev) (*)
│   │   ├── ruff v0.16.3 (group: dev)
│   │   ├── types-beautifulsoup4 v4.12.0.20250516 (group: dev) (*)
│   │   ├── types-pillow v10.2.0.20240822 (group: dev)
│   │   ├── types-pyyaml v6.0.12.20260815 (group: dev)
│   │   └── types-requests v2.33.0.20260712 (group: dev) (*)
│   ├── lexigram-ai-agents v0.1.3007 (extra: all)
│   │   ├── lexigram v0.1.3009 (*)
│   │   ├── lexigram-contracts v0.1.3007 (*)
│   │   ├── typing-extensions v4.16.0
│   │   ├── black v26.5.1 (extra: dev) (*)
│   │   ├── mypy v2.3.1 (extra: dev) (*)
│   │   ├── ruff v0.16.3 (extra: dev)
│   │   ├── lexigram-testing v0.1.3007 (extra: test) (*)
│   │   ├── pytest v9.1.1 (extra: test) (*)
│   │   ├── pytest-asyncio v1.4.0 (extra: test) (*)
│   │   ├── pytest-cov v7.1.0 (extra: test) (*)
│   │   ├── pytest-mock v3.15.1 (extra: test) (*)
│   │   ├── black v26.5.1 (group: dev) (*)
│   │   ├── mypy v2.3.1 (group: dev) (*)
│   │   └── ruff v0.16.3 (group: dev)
│   ├── lexigram-ai-evaluation v0.1.3007 (extra: all)
│   │   ├── lexigram v0.1.3009 (*)
│   │   ├── lexigram-contracts v0.1.3007 (*)
│   │   ├── mypy v2.3.1 (group: dev) (*)
│   │   └── ruff v0.16.3 (group: dev)
│   ├── lexigram-ai-feedback v0.1.3007 (extra: all) (*)
│   ├── lexigram-ai-governance v0.1.3007 (extra: all)
│   │   ├── lexigram v0.1.3009 (*)
│   │   ├── lexigram-contracts v0.1.3007 (*)
│   │   ├── starlette v1.6.0 (*)
│   │   ├── typing-extensions v4.16.0
│   │   ├── mypy v2.3.1 (extra: dev) (*)
│   │   ├── ruff v0.16.3 (extra: dev)
│   │   ├── lexigram-testing v0.1.3007 (extra: test) (*)
│   │   ├── pytest v9.1.1 (extra: test) (*)
│   │   ├── pytest-asyncio v1.4.0 (extra: test) (*)
│   │   ├── pytest-cov v7.1.0 (extra: test) (*)
│   │   ├── pytest-mock v3.15.1 (extra: test) (*)
│   │   ├── mypy v2.3.1 (group: dev) (*)
│   │   └── ruff v0.16.3 (group: dev)
│   ├── lexigram-ai-guard v0.1.3007 (extra: all)
│   │   ├── lexigram v0.1.3009 (*)
│   │   ├── lexigram-contracts v0.1.3007 (*)
│   │   ├── starlette v1.6.0 (*)
│   │   ├── typing-extensions v4.16.0
│   │   ├── mypy v2.3.1 (extra: dev) (*)
│   │   ├── ruff v0.16.3 (extra: dev)
│   │   ├── lexigram-testing v0.1.3007 (extra: test) (*)
│   │   ├── pytest v9.1.1 (extra: test) (*)
│   │   ├── pytest-asyncio v1.4.0 (extra: test) (*)
│   │   ├── pytest-cov v7.1.0 (extra: test) (*)
│   │   ├── pytest-mock v3.15.1 (extra: test) (*)
│   │   ├── mypy v2.3.1 (group: dev) (*)
│   │   └── ruff v0.16.3 (group: dev)
│   ├── lexigram-ai-llm v0.1.3007 (extra: all) (*)
│   ├── lexigram-ai-mcp v0.1.3008 (extra: all)
│   │   ├── lexigram v0.1.3009 (*)
│   │   ├── lexigram-contracts v0.1.3007 (*)
│   │   ├── typer v0.27.1 (*)
│   │   ├── typing-extensions v4.16.0
│   │   ├── mypy v2.3.1 (extra: dev) (*)
│   │   ├── ruff v0.16.3 (extra: dev)
│   │   ├── lexigram-testing v0.1.3007 (extra: test) (*)
│   │   ├── pytest v9.1.1 (extra: test) (*)
│   │   ├── pytest-asyncio v1.4.0 (extra: test) (*)
│   │   ├── pytest-cov v7.1.0 (extra: test) (*)
│   │   ├── pytest-mock v3.15.1 (extra: test) (*)
│   │   ├── mypy v2.3.1 (group: dev) (*)
│   │   └── ruff v0.16.3 (group: dev)
│   ├── lexigram-ai-memory v0.1.3007 (extra: all)
│   │   ├── lexigram v0.1.3009 (*)
│   │   ├── lexigram-contracts v0.1.3007 (*)
│   │   ├── typing-extensions v4.16.0
│   │   ├── mypy v2.3.1 (extra: dev) (*)
│   │   ├── ruff v0.16.3 (extra: dev)
│   │   ├── redis v8.1.0 (extra: redis)
│   │   ├── lexigram-testing v0.1.3007 (extra: test) (*)
│   │   ├── pytest v9.1.1 (extra: test) (*)
│   │   ├── pytest-asyncio v1.4.0 (extra: test) (*)
│   │   ├── pytest-cov v7.1.0 (extra: test) (*)
│   │   ├── pytest-mock v3.15.1 (extra: test) (*)
│   │   ├── mypy v2.3.1 (group: dev) (*)
│   │   └── ruff v0.16.3 (group: dev)
│   ├── lexigram-ai-observability v0.1.3007 (extra: all) (*)
│   ├── lexigram-ai-prompt v0.1.3007 (extra: all)
│   │   ├── jinja2 v3.1.6 (*)
│   │   ├── lexigram v0.1.3009 (*)
│   │   ├── lexigram-contracts v0.1.3007 (*)
│   │   ├── typing-extensions v4.16.0
│   │   ├── mypy v2.3.1 (extra: dev) (*)
│   │   ├── ruff v0.16.3 (extra: dev)
│   │   ├── lexigram-testing v0.1.3007 (extra: test) (*)
│   │   ├── pytest v9.1.1 (extra: test) (*)
│   │   ├── pytest-asyncio v1.4.0 (extra: test) (*)
│   │   ├── pytest-cov v7.1.0 (extra: test) (*)
│   │   ├── pytest-mock v3.15.1 (extra: test) (*)
│   │   ├── mypy v2.3.1 (group: dev) (*)
│   │   └── ruff v0.16.3 (group: dev)
│   ├── lexigram-ai-rag v0.1.3007 (extra: all) (*)
│   ├── lexigram-ai-relay v0.1.3007 (extra: all)
│   │   ├── lexigram v0.1.3009 (*)
│   │   ├── lexigram-contracts v0.1.3007 (*)
│   │   ├── typing-extensions v4.16.0
│   │   ├── mypy v2.3.1 (extra: dev) (*)
│   │   ├── ruff v0.16.3 (extra: dev)
│   │   ├── lexigram-testing v0.1.3007 (extra: test) (*)
│   │   ├── pytest v9.1.1 (extra: test) (*)
│   │   ├── pytest-asyncio v1.4.0 (extra: test) (*)
│   │   ├── pytest-cov v7.1.0 (extra: test) (*)
│   │   ├── pytest-mock v3.15.1 (extra: test) (*)
│   │   ├── mypy v2.3.1 (group: dev) (*)
│   │   └── ruff v0.16.3 (group: dev)
│   ├── lexigram-ai-relay-gateway v0.1.3007 (extra: all)
│   │   ├── lexigram v0.1.3009 (*)
│   │   ├── lexigram-contracts v0.1.3007 (*)
│   │   ├── orjson v3.12.0
│   │   ├── starlette v1.6.0 (*)
│   │   ├── mypy v2.3.1 (extra: dev) (*)
│   │   ├── ruff v0.16.3 (extra: dev)
│   │   ├── redis v8.1.0 (extra: redis)
│   │   ├── lexigram-testing v0.1.3007 (extra: test) (*)
│   │   ├── pytest v9.1.1 (extra: test) (*)
│   │   ├── pytest-asyncio v1.4.0 (extra: test) (*)
│   │   ├── pytest-cov v7.1.0 (extra: test) (*)
│   │   ├── pytest-mock v3.15.1 (extra: test) (*)
│   │   ├── mypy v2.3.1 (group: dev) (*)
│   │   └── ruff v0.16.3 (group: dev)
│   ├── lexigram-ai-session v0.1.3007 (extra: all)
│   │   ├── lexigram v0.1.3009 (*)
│   │   ├── lexigram-contracts v0.1.3007 (*)
│   │   ├── typing-extensions v4.16.0
│   │   ├── mypy v2.3.1 (extra: dev) (*)
│   │   ├── ruff v0.16.3 (extra: dev)
│   │   ├── lexigram-testing v0.1.3007 (extra: test) (*)
│   │   ├── pytest v9.1.1 (extra: test) (*)
│   │   ├── pytest-asyncio v1.4.0 (extra: test) (*)
│   │   ├── pytest-cov v7.1.0 (extra: test) (*)
│   │   ├── pytest-mock v3.15.1 (extra: test) (*)
│   │   ├── mypy v2.3.1 (group: dev) (*)
│   │   └── ruff v0.16.3 (group: dev)
│   ├── lexigram-ai-skills v0.1.3007 (extra: all)
│   │   ├── lexigram v0.1.3009 (*)
│   │   ├── lexigram-contracts v0.1.3007 (*)
│   │   ├── pyyaml v6.0.3
│   │   ├── typing-extensions v4.16.0
│   │   ├── mypy v2.3.1 (extra: dev) (*)
│   │   ├── ruff v0.16.3 (extra: dev)
│   │   ├── lexigram-testing v0.1.3007 (extra: test) (*)
│   │   ├── pytest v9.1.1 (extra: test) (*)
│   │   ├── pytest-asyncio v1.4.0 (extra: test) (*)
│   │   ├── pytest-cov v7.1.0 (extra: test) (*)
│   │   ├── pytest-mock v3.15.1 (extra: test) (*)
│   │   ├── mypy v2.3.1 (group: dev) (*)
│   │   └── ruff v0.16.3 (group: dev)
│   ├── lexigram-ai-workers v0.1.3007 (extra: all)
│   │   ├── lexigram v0.1.3009 (*)
│   │   ├── lexigram-contracts v0.1.3007 (*)
│   │   ├── typing-extensions v4.16.0
│   │   ├── mypy v2.3.1 (extra: dev) (*)
│   │   ├── ruff v0.16.3 (extra: dev)
│   │   ├── lexigram-testing v0.1.3007 (extra: test) (*)
│   │   ├── pytest v9.1.1 (extra: test) (*)
│   │   ├── pytest-asyncio v1.4.0 (extra: test) (*)
│   │   ├── pytest-cov v7.1.0 (extra: test) (*)
│   │   ├── pytest-mock v3.15.1 (extra: test) (*)
│   │   ├── mypy v2.3.1 (group: dev) (*)
│   │   └── ruff v0.16.3 (group: dev)
│   ├── lexigram-audit v0.1.3007 (extra: all)
│   │   ├── lexigram v0.1.3009 (*)
│   │   ├── lexigram-contracts v0.1.3007 (*)
│   │   ├── starlette v1.6.0 (*)
│   │   ├── typer v0.27.1 (*)
│   │   ├── mypy v2.3.1 (extra: dev) (*)
│   │   ├── ruff v0.16.3 (extra: dev)
│   │   ├── lexigram-sql v0.1.3007 (extra: sql) (*)
│   │   ├── lexigram-testing v0.1.3007 (extra: test) (*)
│   │   ├── pytest v9.1.1 (extra: test) (*)
│   │   ├── pytest-asyncio v1.4.0 (extra: test) (*)
│   │   ├── pytest-cov v7.1.0 (extra: test) (*)
│   │   ├── pytest-mock v3.15.1 (extra: test) (*)
│   │   ├── mypy v2.3.1 (group: dev) (*)
│   │   └── ruff v0.16.3 (group: dev)
│   ├── lexigram-auth v0.1.3007 (extra: all) (*)
│   ├── lexigram-cache v0.1.3007 (extra: all) (*)
│   ├── lexigram-cli v0.1.3007 (extra: all)
│   │   ├── aiofiles v25.1.0
│   │   ├── httpx v0.28.1 (*)
│   │   ├── jinja2 v3.1.6 (*)
│   │   ├── lexigram v0.1.3009 (*)
│   │   ├── lexigram-contracts v0.1.3007 (*)
│   │   ├── pydantic v2.13.4 (*)
│   │   ├── pyyaml v6.0.3
│   │   ├── rich v13.9.4 (*)
│   │   ├── shellingham v1.5.4
│   │   ├── tomli v2.4.1
│   │   ├── typer v0.27.1 (*)
│   │   ├── watchfiles v1.2.0 (*)
│   │   ├── lexigram-testing v0.1.3007 (extra: all) (*)
│   │   ├── pytest v9.1.1 (extra: all) (*)
│   │   ├── pytest-asyncio v1.4.0 (extra: all) (*)
│   │   ├── pytest-cov v7.1.0 (extra: all) (*)
│   │   ├── black v26.5.1 (extra: dev) (*)
│   │   ├── mypy v2.3.1 (extra: dev) (*)
│   │   ├── ruff v0.16.3 (extra: dev)
│   │   ├── lexigram-testing v0.1.3007 (extra: test) (*)
│   │   ├── pytest v9.1.1 (extra: test) (*)
│   │   ├── pytest-asyncio v1.4.0 (extra: test) (*)
│   │   ├── pytest-cov v7.1.0 (extra: test) (*)
│   │   ├── black v26.5.1 (group: dev) (*)
│   │   ├── mypy v2.3.1 (group: dev) (*)
│   │   ├── ruff v0.16.3 (group: dev)
│   │   ├── tomli v2.4.1 (group: dev)
│   │   └── tomli-w v1.2.0 (group: dev)
│   ├── lexigram-contracts v0.1.3007 (extra: all) (*)
│   ├── lexigram-events v0.1.3007 (extra: all) (*)
│   ├── lexigram-features v0.1.3007 (extra: all)
│   │   ├── lexigram v0.1.3009 (*)
│   │   ├── lexigram-contracts v0.1.3007 (*)
│   │   ├── typer v0.27.1 (*)
│   │   ├── mypy v2.3.1 (extra: dev) (*)
│   │   ├── ruff v0.16.3 (extra: dev)
│   │   ├── lexigram-testing v0.1.3007 (extra: test) (*)
│   │   ├── pytest v9.1.1 (extra: test) (*)
│   │   ├── pytest-asyncio v1.4.0 (extra: test) (*)
│   │   ├── pytest-cov v7.1.0 (extra: test) (*)
│   │   ├── pytest-mock v3.15.1 (extra: test) (*)
│   │   ├── pyyaml v6.0.3 (extra: yaml)
│   │   ├── mypy v2.3.1 (group: dev) (*)
│   │   └── ruff v0.16.3 (group: dev)
│   ├── lexigram-graph v0.1.3007 (extra: all)
│   │   ├── lexigram v0.1.3009 (*)
│   │   ├── lexigram-contracts v0.1.3007 (*)
│   │   ├── neo4j v6.2.0 (extra: all) (*)
│   │   ├── mypy v2.3.1 (extra: dev) (*)
│   │   ├── ruff v0.16.3 (extra: dev)
│   │   ├── neo4j v6.2.0 (extra: neo4j) (*)
│   │   ├── lexigram-testing v0.1.3007 (extra: test) (*)
│   │   ├── pytest v9.1.1 (extra: test) (*)
│   │   ├── pytest-asyncio v1.4.0 (extra: test) (*)
│   │   ├── pytest-cov v7.1.0 (extra: test) (*)
│   │   ├── pytest-mock v3.15.1 (extra: test) (*)
│   │   ├── mypy v2.3.1 (group: dev) (*)
│   │   └── ruff v0.16.3 (group: dev)
│   ├── lexigram-graphql v0.1.3007 (extra: all)
│   │   ├── graphql-core v3.2.11
│   │   ├── jinja2 v3.1.6 (*)
│   │   ├── lexigram v0.1.3009 (*)
│   │   ├── lexigram-contracts v0.1.3007 (*)
│   │   ├── starlette v1.6.0 (*)
│   │   ├── strawberry-graphql v0.324.0
│   │   │   ├── cross-web v0.7.0
│   │   │   │   └── typing-extensions v4.16.0
│   │   │   ├── graphql-core v3.2.11
│   │   │   ├── packaging v26.3
│   │   │   ├── python-dateutil v2.9.0.post0 (*)
│   │   │   └── typing-extensions v4.16.0
│   │   ├── typing-extensions v4.16.0
│   │   ├── lexigram-testing v0.1.3007 (extra: all) (*)
│   │   ├── pytest v9.1.1 (extra: all) (*)
│   │   ├── pytest-asyncio v1.4.0 (extra: all) (*)
│   │   ├── pytest-cov v7.1.0 (extra: all) (*)
│   │   ├── pytest-mock v3.15.1 (extra: all) (*)
│   │   ├── starlette v1.6.0 (extra: all) (*)
│   │   ├── websockets v17.0.1 (extra: all)
│   │   ├── black v26.5.1 (extra: dev) (*)
│   │   ├── mypy v2.3.1 (extra: dev) (*)
│   │   ├── ruff v0.16.3 (extra: dev)
│   │   ├── starlette v1.6.0 (extra: starlette) (*)
│   │   ├── websockets v17.0.1 (extra: subscriptions)
│   │   ├── lexigram-testing v0.1.3007 (extra: test) (*)
│   │   ├── pytest v9.1.1 (extra: test) (*)
│   │   ├── pytest-asyncio v1.4.0 (extra: test) (*)
│   │   ├── pytest-cov v7.1.0 (extra: test) (*)
│   │   ├── pytest-mock v3.15.1 (extra: test) (*)
│   │   ├── black v26.5.1 (group: dev) (*)
│   │   ├── mypy v2.3.1 (group: dev) (*)
│   │   └── ruff v0.16.3 (group: dev)
│   ├── lexigram-http v0.1.3007 (extra: all)
│   │   ├── aiohttp v3.14.3 (*)
│   │   ├── jinja2 v3.1.6 (*)
│   │   ├── lexigram v0.1.3009 (*)
│   │   ├── lexigram-contracts v0.1.3007 (*)
│   │   ├── mypy v2.3.1 (extra: dev) (*)
│   │   ├── ruff v0.16.3 (extra: dev)
│   │   ├── lexigram-testing v0.1.3007 (extra: test) (*)
│   │   ├── pytest v9.1.1 (extra: test) (*)
│   │   ├── pytest-aiohttp v1.1.1 (extra: test)
│   │   │   ├── aiohttp v3.14.3 (*)
│   │   │   ├── pytest v9.1.1 (*)
│   │   │   └── pytest-asyncio v1.4.0 (*)
│   │   ├── pytest-asyncio v1.4.0 (extra: test) (*)
│   │   ├── pytest-cov v7.1.0 (extra: test) (*)
│   │   ├── pytest-mock v3.15.1 (extra: test) (*)
│   │   ├── mypy v2.3.1 (group: dev) (*)
│   │   └── ruff v0.16.3 (group: dev)
│   ├── lexigram-monitor v0.1.3007 (extra: all) (*)
│   ├── lexigram-multimedia v0.1.3007 (extra: all)
│   │   ├── lexigram v0.1.3009 (*)
│   │   ├── lexigram-contracts v0.1.3007 (*)
│   │   ├── lexigram-multimedia-beat v0.1.3007
│   │   │   ├── aiohttp v3.14.3 (*)
│   │   │   ├── lexigram v0.1.3009 (*)
│   │   │   ├── lexigram-contracts v0.1.3007 (*)
│   │   │   ├── typing-extensions v4.16.0
│   │   │   ├── mypy v2.3.1 (extra: dev) (*)
│   │   │   ├── ruff v0.16.3 (extra: dev)
│   │   │   ├── librosa v0.11.0 (extra: librosa) (*)
│   │   │   ├── soundfile v0.13.1 (extra: librosa) (*)
│   │   │   ├── madmom v0.16.1 (extra: madmom-server)
│   │   │   │   ├── cython v3.2.9
│   │   │   │   ├── mido v1.3.3
│   │   │   │   │   └── packaging v26.3
│   │   │   │   ├── numpy v2.5.2
│   │   │   │   └── scipy v1.18.0 (*)
│   │   │   ├── lexigram-testing v0.1.3007 (extra: test) (*)
│   │   │   ├── librosa v0.11.0 (extra: test) (*)
│   │   │   ├── numpy v2.5.2 (extra: test)
│   │   │   ├── pytest v9.1.1 (extra: test) (*)
│   │   │   ├── pytest-asyncio v1.4.0 (extra: test) (*)
│   │   │   ├── pytest-cov v7.1.0 (extra: test) (*)
│   │   │   ├── pytest-mock v3.15.1 (extra: test) (*)
│   │   │   ├── soundfile v0.13.1 (extra: test) (*)
│   │   │   ├── mypy v2.3.1 (group: dev) (*)
│   │   │   └── ruff v0.16.3 (group: dev)
│   │   ├── lexigram-multimedia-image v0.1.3007
│   │   │   ├── aiohttp v3.14.3 (*)
│   │   │   ├── lexigram v0.1.3009 (*)
│   │   │   ├── lexigram-contracts v0.1.3007 (*)
│   │   │   ├── typing-extensions v4.16.0
│   │   │   ├── mypy v2.3.1 (extra: dev) (*)
│   │   │   ├── ruff v0.16.3 (extra: dev)
│   │   │   ├── lexigram-testing v0.1.3007 (extra: test) (*)
│   │   │   ├── pytest v9.1.1 (extra: test) (*)
│   │   │   ├── pytest-asyncio v1.4.0 (extra: test) (*)
│   │   │   ├── pytest-cov v7.1.0 (extra: test) (*)
│   │   │   ├── pytest-mock v3.15.1 (extra: test) (*)
│   │   │   ├── mypy v2.3.1 (group: dev) (*)
│   │   │   └── ruff v0.16.3 (group: dev)
│   │   ├── lexigram-multimedia-interpolate v0.1.3007
│   │   │   ├── aiohttp v3.14.3 (*)
│   │   │   ├── lexigram v0.1.3009 (*)
│   │   │   ├── lexigram-contracts v0.1.3007 (*)
│   │   │   ├── typing-extensions v4.16.0
│   │   │   ├── mypy v2.3.1 (extra: dev) (*)
│   │   │   ├── ruff v0.16.3 (extra: dev)
│   │   │   ├── torch v2.9.0 (extra: rife-server) (*)
│   │   │   ├── lexigram-testing v0.1.3007 (extra: test) (*)
│   │   │   ├── pytest v9.1.1 (extra: test) (*)
│   │   │   ├── pytest-asyncio v1.4.0 (extra: test) (*)
│   │   │   ├── pytest-cov v7.1.0 (extra: test) (*)
│   │   │   ├── pytest-mock v3.15.1 (extra: test) (*)
│   │   │   ├── mypy v2.3.1 (group: dev) (*)
│   │   │   └── ruff v0.16.3 (group: dev)
│   │   ├── lexigram-multimedia-music v0.1.3007
│   │   │   ├── aiohttp v3.14.3 (*)
│   │   │   ├── lexigram v0.1.3009 (*)
│   │   │   ├── lexigram-contracts v0.1.3007 (*)
│   │   │   ├── typing-extensions v4.16.0
│   │   │   ├── ace-step v0.1.0 (extra: ace-step-server)
│   │   │   │   ├── accelerate v1.6.0 (*)
│   │   │   │   ├── click v8.4.2
│   │   │   │   ├── cutlet v0.5.2
│   │   │   │   │   ├── fugashi v1.5.2
│   │   │   │   │   │   └── unidic-lite v1.0.8 (extra: unidic-lite)
│   │   │   │   │   ├── jaconv v0.5.0
│   │   │   │   │   └── mojimoji v0.0.13
│   │   │   │   ├── datasets v3.4.1
│   │   │   │   │   ├── aiohttp v3.14.3 (*)
│   │   │   │   │   ├── dill v0.3.8
│   │   │   │   │   ├── filelock v3.32.3
│   │   │   │   │   ├── fsspec[http] v2024.12.0 (*)
│   │   │   │   │   ├── huggingface-hub v0.36.2 (*)
│   │   │   │   │   ├── multiprocess v0.70.16
│   │   │   │   │   │   └── dill v0.3.8
│   │   │   │   │   ├── numpy v2.5.2
│   │   │   │   │   ├── packaging v26.3
│   │   │   │   │   ├── pandas v3.0.5
│   │   │   │   │   │   ├── numpy v2.5.2
│   │   │   │   │   │   └── python-dateutil v2.9.0.post0 (*)
│   │   │   │   │   ├── pyarrow v25.0.1
│   │   │   │   │   ├── pyyaml v6.0.3
│   │   │   │   │   ├── requests v2.34.2 (*)
│   │   │   │   │   ├── tqdm v4.67.1
│   │   │   │   │   └── xxhash v4.0.1
│   │   │   │   ├── diffusers v0.32.2
│   │   │   │   │   ├── filelock v3.32.3
│   │   │   │   │   ├── huggingface-hub v0.36.2 (*)
│   │   │   │   │   ├── importlib-metadata v9.0.0
│   │   │   │   │   │   └── zipp v4.1.0
│   │   │   │   │   ├── numpy v2.5.2
│   │   │   │   │   ├── pillow v12.3.0
│   │   │   │   │   ├── regex v2026.7.19
│   │   │   │   │   ├── requests v2.34.2 (*)
│   │   │   │   │   └── safetensors v0.5.3
│   │   │   │   ├── fugashi[unidic-lite] v1.5.2 (*)
│   │   │   │   ├── gradio v6.17.3
│   │   │   │   │   ├── anyio v4.14.2 (*)
│   │   │   │   │   ├── audioop-lts v0.2.2
│   │   │   │   │   ├── brotli v1.2.0
│   │   │   │   │   ├── fastapi v0.141.1
│   │   │   │   │   │   ├── annotated-doc v0.0.5
│   │   │   │   │   │   ├── pydantic v2.13.4 (*)
│   │   │   │   │   │   ├── starlette v1.6.0 (*)
│   │   │   │   │   │   ├── typing-extensions v4.16.0
│   │   │   │   │   │   └── typing-inspection v0.4.4 (*)
│   │   │   │   │   ├── gradio-client v2.5.0
│   │   │   │   │   │   ├── fsspec v2024.12.0 (*)
│   │   │   │   │   │   ├── httpx v0.28.1 (*)
│   │   │   │   │   │   ├── huggingface-hub v0.36.2 (*)
│   │   │   │   │   │   ├── packaging v26.3
│   │   │   │   │   │   └── typing-extensions v4.16.0
│   │   │   │   │   ├── groovy v0.1.2
│   │   │   │   │   ├── hf-gradio v0.4.1
│   │   │   │   │   │   ├── gradio-client v2.5.0 (*)
│   │   │   │   │   │   └── typer v0.27.1 (*)
│   │   │   │   │   ├── httpx v0.28.1 (*)
│   │   │   │   │   ├── huggingface-hub v0.36.2 (*)
│   │   │   │   │   ├── jinja2 v3.1.6 (*)
│   │   │   │   │   ├── markupsafe v3.0.3
│   │   │   │   │   ├── numpy v2.5.2
│   │   │   │   │   ├── orjson v3.12.0
│   │   │   │   │   ├── packaging v26.3
│   │   │   │   │   ├── pandas v3.0.5 (*)
│   │   │   │   │   ├── pillow v12.3.0
│   │   │   │   │   ├── pydantic v2.13.4 (*)
│   │   │   │   │   ├── pydub v0.25.1
│   │   │   │   │   ├── python-multipart v0.0.32
│   │   │   │   │   ├── pytz v2026.3.post1
│   │   │   │   │   ├── pyyaml v6.0.3
│   │   │   │   │   ├── safehttpx v0.1.7
│   │   │   │   │   │   └── httpx v0.28.1 (*)
│   │   │   │   │   ├── semantic-version v2.10.0
│   │   │   │   │   ├── starlette v1.6.0 (*)
│   │   │   │   │   ├── tomlkit v0.14.0
│   │   │   │   │   ├── typer v0.27.1 (*)
│   │   │   │   │   ├── typing-extensions v4.16.0
│   │   │   │   │   └── uvicorn v0.52.4 (*)
│   │   │   │   ├── hangul-romanize v0.1.0
│   │   │   │   ├── librosa v0.11.0 (*)
│   │   │   │   ├── loguru v0.7.3
│   │   │   │   ├── matplotlib v3.10.1
│   │   │   │   │   ├── contourpy v1.3.3
│   │   │   │   │   │   └── numpy v2.5.2
│   │   │   │   │   ├── cycler v0.12.1
│   │   │   │   │   ├── fonttools v4.63.0
│   │   │   │   │   ├── kiwisolver v1.5.0
│   │   │   │   │   ├── numpy v2.5.2
│   │   │   │   │   ├── packaging v26.3
│   │   │   │   │   ├── pillow v12.3.0
│   │   │   │   │   ├── pyparsing v3.3.2
│   │   │   │   │   └── python-dateutil v2.9.0.post0 (*)
│   │   │   │   ├── num2words v0.5.14
│   │   │   │   │   └── docopt v0.6.2
│   │   │   │   ├── numpy v2.5.2
│   │   │   │   ├── py3langid v0.3.0
│   │   │   │   │   └── numpy v2.5.2
│   │   │   │   ├── pypinyin v0.53.0
│   │   │   │   ├── pytorch-lightning v2.6.5
│   │   │   │   │   ├── fsspec[http] v2024.12.0 (*)
│   │   │   │   │   ├── lightning-utilities v0.15.3
│   │   │   │   │   │   ├── packaging v26.3
│   │   │   │   │   │   └── typing-extensions v4.16.0
│   │   │   │   │   ├── packaging v26.3
│   │   │   │   │   ├── pyyaml v6.0.3
│   │   │   │   │   ├── torch v2.9.0 (*)
│   │   │   │   │   ├── torchmetrics v1.9.0
│   │   │   │   │   │   ├── lightning-utilities v0.15.3 (*)
│   │   │   │   │   │   ├── numpy v2.5.2
│   │   │   │   │   │   ├── packaging v26.3
│   │   │   │   │   │   └── torch v2.9.0 (*)
│   │   │   │   │   ├── tqdm v4.67.1
│   │   │   │   │   └── typing-extensions v4.16.0
│   │   │   │   ├── soundfile v0.13.1 (*)
│   │   │   │   ├── spacy v3.8.4
│   │   │   │   │   ├── catalogue v2.0.10
│   │   │   │   │   ├── cymem v2.0.13
│   │   │   │   │   ├── jinja2 v3.1.6 (*)
│   │   │   │   │   ├── langcodes v3.5.1
│   │   │   │   │   ├── murmurhash v1.0.15
│   │   │   │   │   ├── numpy v2.5.2
│   │   │   │   │   ├── packaging v26.3
│   │   │   │   │   ├── preshed v3.0.13
│   │   │   │   │   │   ├── cymem v2.0.13
│   │   │   │   │   │   └── murmurhash v1.0.15
│   │   │   │   │   ├── pydantic v2.13.4 (*)
│   │   │   │   │   ├── requests v2.34.2 (*)
│   │   │   │   │   ├── setuptools v80.10.2
│   │   │   │   │   ├── spacy-legacy v3.0.12
│   │   │   │   │   ├── spacy-loggers v1.0.5
│   │   │   │   │   ├── srsly v2.5.3
│   │   │   │   │   │   └── catalogue v2.0.10
│   │   │   │   │   ├── thinc v8.3.11
│   │   │   │   │   │   ├── blis v1.3.3
│   │   │   │   │   │   │   └── numpy v2.5.2
│   │   │   │   │   │   ├── catalogue v2.0.10
│   │   │   │   │   │   ├── confection v0.1.5
│   │   │   │   │   │   │   ├── pydantic v2.13.4 (*)
│   │   │   │   │   │   │   └── srsly v2.5.3 (*)
│   │   │   │   │   │   ├── cymem v2.0.13
│   │   │   │   │   │   ├── murmurhash v1.0.15
│   │   │   │   │   │   ├── numpy v2.5.2
│   │   │   │   │   │   ├── packaging v26.3
│   │   │   │   │   │   ├── preshed v3.0.13 (*)
│   │   │   │   │   │   ├── pydantic v2.13.4 (*)
│   │   │   │   │   │   ├── setuptools v80.10.2
│   │   │   │   │   │   ├── srsly v2.5.3 (*)
│   │   │   │   │   │   └── wasabi v1.1.3
│   │   │   │   │   ├── tqdm v4.67.1
│   │   │   │   │   ├── typer v0.27.1 (*)
│   │   │   │   │   ├── wasabi v1.1.3
│   │   │   │   │   └── weasel v0.4.3
│   │   │   │   │       ├── cloudpathlib v0.24.0
│   │   │   │   │       ├── confection v0.1.5 (*)
│   │   │   │   │       ├── packaging v26.3
│   │   │   │   │       ├── pydantic v2.13.4 (*)
│   │   │   │   │       ├── requests v2.34.2 (*)
│   │   │   │   │       ├── smart-open v7.7.1
│   │   │   │   │       │   └── wrapt v1.17.3
│   │   │   │   │       ├── srsly v2.5.3 (*)
│   │   │   │   │       ├── typer-slim v0.24.0
│   │   │   │   │       │   └── typer v0.27.1 (*)
│   │   │   │   │       └── wasabi v1.1.3
│   │   │   │   ├── torch v2.9.0 (*)
│   │   │   │   ├── torchaudio v2.9.0
│   │   │   │   │   └── torch v2.9.0 (*)
│   │   │   │   ├── torchvision v0.28.0
│   │   │   │   │   ├── numpy v2.5.2
│   │   │   │   │   ├── pillow v12.3.0
│   │   │   │   │   └── torch v2.9.0 (*)
│   │   │   │   ├── tqdm v4.67.1
│   │   │   │   └── transformers v4.50.0 (*)
│   │   │   ├── torch v2.9.0 (extra: ace-step-server) (*)
│   │   │   ├── mypy v2.3.1 (extra: dev) (*)
│   │   │   ├── ruff v0.16.3 (extra: dev)
│   │   │   ├── stable-audio-tools v0.0.20 (extra: stable-audio-open-server)
│   │   │   │   ├── alias-free-torch v0.0.6
│   │   │   │   ├── dill v0.3.8
│   │   │   │   ├── einops v0.8.2
│   │   │   │   ├── einops-exts v0.0.4
│   │   │   │   │   └── einops v0.8.2
│   │   │   │   ├── huggingface-hub v0.36.2 (*)
│   │   │   │   ├── importlib-resources v5.12.0
│   │   │   │   ├── nnaudio v0.3.4
│   │   │   │   │   ├── numpy v2.5.2
│   │   │   │   │   ├── scipy v1.18.0 (*)
│   │   │   │   │   └── torch v2.9.0 (*)
│   │   │   │   ├── pywavelets v1.4.1
│   │   │   │   │   └── numpy v2.5.2
│   │   │   │   ├── safetensors v0.5.3
│   │   │   │   ├── scipy v1.18.0 (*)
│   │   │   │   ├── sentencepiece v0.1.99
│   │   │   │   ├── setuptools v80.10.2
│   │   │   │   ├── soxr v1.1.0 (*)
│   │   │   │   ├── torch v2.9.0 (*)
│   │   │   │   ├── torchaudio v2.9.0 (*)
│   │   │   │   ├── torchsde v0.2.6
│   │   │   │   │   ├── numpy v2.5.2
│   │   │   │   │   ├── scipy v1.18.0 (*)
│   │   │   │   │   ├── torch v2.9.0 (*)
│   │   │   │   │   └── trampoline v0.1.2
│   │   │   │   ├── tqdm v4.67.1
│   │   │   │   ├── transformers v4.50.0 (*)
│   │   │   │   ├── v-diffusion-pytorch v0.0.2
│   │   │   │   │   ├── ftfy v6.3.1
│   │   │   │   │   │   └── wcwidth v0.8.2
│   │   │   │   │   ├── pillow v12.3.0
│   │   │   │   │   ├── regex v2026.7.19
│   │   │   │   │   ├── requests v2.34.2 (*)
│   │   │   │   │   ├── torch v2.9.0 (*)
│   │   │   │   │   ├── torchvision v0.28.0 (*)
│   │   │   │   │   └── tqdm v4.67.1
│   │   │   │   └── vector-quantize-pytorch v1.14.41
│   │   │   │       ├── einops v0.8.2
│   │   │   │       ├── einx v0.4.3
│   │   │   │       │   ├── frozendict v2.4.7
│   │   │   │       │   ├── numpy v2.5.2
│   │   │   │       │   └── sympy v1.14.0 (*)
│   │   │   │       └── torch v2.9.0 (*)
│   │   │   ├── torch v2.9.0 (extra: stable-audio-open-server) (*)
│   │   │   ├── lexigram-testing v0.1.3007 (extra: test) (*)
│   │   │   ├── pytest v9.1.1 (extra: test) (*)
│   │   │   ├── pytest-asyncio v1.4.0 (extra: test) (*)
│   │   │   ├── pytest-cov v7.1.0 (extra: test) (*)
│   │   │   ├── pytest-mock v3.15.1 (extra: test) (*)
│   │   │   ├── mypy v2.3.1 (group: dev) (*)
│   │   │   └── ruff v0.16.3 (group: dev)
│   │   ├── lexigram-multimedia-tts v0.1.3007
│   │   │   ├── aiohttp v3.14.3 (*)
│   │   │   ├── lexigram v0.1.3009 (*)
│   │   │   ├── lexigram-contracts v0.1.3007 (*)
│   │   │   ├── typing-extensions v4.16.0
│   │   │   ├── chatterbox-tts v0.1.7 (extra: chatterbox-server)
│   │   │   │   ├── conformer v0.3.2
│   │   │   │   │   ├── einops v0.8.2
│   │   │   │   │   └── torch v2.9.0 (*)
│   │   │   │   ├── diffusers v0.32.2 (*)
│   │   │   │   ├── gradio v6.17.3 (*)
│   │   │   │   ├── librosa v0.11.0 (*)
│   │   │   │   ├── numpy v2.5.2
│   │   │   │   ├── omegaconf v2.3.1
│   │   │   │   │   ├── antlr4-python3-runtime v4.9.3
│   │   │   │   │   └── pyyaml v6.0.3
│   │   │   │   ├── pykakasi v2.3.0
│   │   │   │   │   ├── deprecated v1.3.1
│   │   │   │   │   │   └── wrapt v1.17.3
│   │   │   │   │   └── jaconv v0.5.0
│   │   │   │   ├── pyloudnorm v0.2.0
│   │   │   │   │   ├── numpy v2.5.2
│   │   │   │   │   └── scipy v1.18.0 (*)
│   │   │   │   ├── resemble-perth v1.0.1
│   │   │   │   ├── s3tokenizer v0.3.0
│   │   │   │   │   ├── einops v0.8.2
│   │   │   │   │   ├── numpy v2.5.2
│   │   │   │   │   ├── onnx v1.22.0
│   │   │   │   │   │   ├── ml-dtypes v0.6.0
│   │   │   │   │   │   │   └── numpy v2.5.2
│   │   │   │   │   │   ├── numpy v2.5.2
│   │   │   │   │   │   ├── protobuf v6.33.6
│   │   │   │   │   │   └── typing-extensions v4.16.0
│   │   │   │   │   ├── pre-commit v4.6.2 (*)
│   │   │   │   │   ├── torch v2.9.0 (*)
│   │   │   │   │   ├── torchaudio v2.9.0 (*)
│   │   │   │   │   └── tqdm v4.67.1
│   │   │   │   ├── safetensors v0.5.3
│   │   │   │   ├── spacy-pkuseg v1.0.1
│   │   │   │   │   ├── numpy v2.5.2
│   │   │   │   │   └── srsly v2.5.3 (*)
│   │   │   │   ├── torch v2.9.0 (*)
│   │   │   │   ├── torchaudio v2.9.0 (*)
│   │   │   │   └── transformers v4.50.0 (*)
│   │   │   ├── torch v2.9.0 (extra: chatterbox-server) (*)
│   │   │   ├── torchaudio v2.9.0 (extra: chatterbox-server) (*)
│   │   │   ├── mypy v2.3.1 (extra: dev) (*)
│   │   │   ├── ruff v0.16.3 (extra: dev)
│   │   │   ├── f5-tts v1.1.22 (extra: f5-tts-server)
│   │   │   │   ├── accelerate v1.6.0 (*)
│   │   │   │   ├── bitsandbytes v0.50.1
│   │   │   │   │   ├── numpy v2.5.2
│   │   │   │   │   ├── packaging v26.3
│   │   │   │   │   └── torch v2.9.0 (*)
│   │   │   │   ├── cached-path v1.8.10
│   │   │   │   │   ├── boto3 v1.40.61 (*)
│   │   │   │   │   ├── filelock v3.32.3
│   │   │   │   │   ├── google-cloud-storage v3.13.1
│   │   │   │   │   │   ├── google-api-core v2.34.0
│   │   │   │   │   │   │   ├── google-auth v2.56.3
│   │   │   │   │   │   │   │   ├── cryptography v50.0.0 (*)
│   │   │   │   │   │   │   │   └── pyasn1-modules v0.4.2 (*)
│   │   │   │   │   │   │   ├── googleapis-common-protos v1.75.1 (*)
│   │   │   │   │   │   │   ├── proto-plus v1.28.3
│   │   │   │   │   │   │   │   └── protobuf v6.33.6
│   │   │   │   │   │   │   ├── protobuf v6.33.6
│   │   │   │   │   │   │   ├── requests v2.34.2 (*)
│   │   │   │   │   │   │   ├── grpcio v1.78.0 (extra: grpc) (*)
│   │   │   │   │   │   │   └── grpcio-status v1.78.0 (extra: grpc)
│   │   │   │   │   │   │       ├── googleapis-common-protos v1.75.1 (*)
│   │   │   │   │   │   │       ├── grpcio v1.78.0 (*)
│   │   │   │   │   │   │       └── protobuf v6.33.6
│   │   │   │   │   │   ├── google-auth v2.56.3 (*)
│   │   │   │   │   │   ├── google-cloud-core v2.6.1
│   │   │   │   │   │   │   ├── google-api-core v2.34.0 (*)
│   │   │   │   │   │   │   └── google-auth v2.56.3 (*)
│   │   │   │   │   │   ├── google-crc32c v1.8.0
│   │   │   │   │   │   ├── google-resumable-media v2.10.1
│   │   │   │   │   │   │   └── google-crc32c v1.8.0
│   │   │   │   │   │   └── requests v2.34.2 (*)
│   │   │   │   │   ├── huggingface-hub v0.36.2 (*)
│   │   │   │   │   ├── packaging v26.3
│   │   │   │   │   ├── requests v2.34.2 (*)
│   │   │   │   │   └── rich v13.9.4 (*)
│   │   │   │   ├── click v8.4.2
│   │   │   │   ├── datasets v3.4.1 (*)
│   │   │   │   ├── ema-pytorch v0.8.3
│   │   │   │   │   └── torch v2.9.0 (*)
│   │   │   │   ├── gradio v6.17.3 (*)
│   │   │   │   ├── hydra-core v1.3.5
│   │   │   │   │   ├── antlr4-python3-runtime v4.9.3
│   │   │   │   │   ├── omegaconf v2.3.1 (*)
│   │   │   │   │   └── packaging v26.3
│   │   │   │   ├── librosa v0.11.0 (*)
│   │   │   │   ├── matplotlib v3.10.1 (*)
│   │   │   │   ├── pydub v0.25.1
│   │   │   │   ├── pypinyin v0.53.0
│   │   │   │   ├── rjieba v0.2.1
│   │   │   │   ├── safetensors v0.5.3
│   │   │   │   ├── soundfile v0.13.1 (*)
│   │   │   │   ├── tomli v2.4.1
│   │   │   │   ├── torch v2.9.0 (*)
│   │   │   │   ├── torchaudio v2.9.0 (*)
│   │   │   │   ├── torchcodec v0.16.0
│   │   │   │   ├── torchdiffeq v0.2.5
│   │   │   │   │   ├── scipy v1.18.0 (*)
│   │   │   │   │   └── torch v2.9.0 (*)
│   │   │   │   ├── tqdm v4.67.1
│   │   │   │   ├── transformers v4.50.0 (*)
│   │   │   │   ├── transformers-stream-generator v0.0.5
│   │   │   │   │   └── transformers v4.50.0 (*)
│   │   │   │   ├── unidecode v1.4.0
│   │   │   │   ├── vocos v0.1.0
│   │   │   │   │   ├── einops v0.8.2
│   │   │   │   │   ├── encodec v0.1.1
│   │   │   │   │   │   ├── einops v0.8.2
│   │   │   │   │   │   ├── numpy v2.5.2
│   │   │   │   │   │   ├── torch v2.9.0 (*)
│   │   │   │   │   │   └── torchaudio v2.9.0 (*)
│   │   │   │   │   ├── huggingface-hub v0.36.2 (*)
│   │   │   │   │   ├── numpy v2.5.2
│   │   │   │   │   ├── pyyaml v6.0.3
│   │   │   │   │   ├── scipy v1.18.0 (*)
│   │   │   │   │   ├── torch v2.9.0 (*)
│   │   │   │   │   └── torchaudio v2.9.0 (*)
│   │   │   │   ├── wandb v0.28.2
│   │   │   │   │   ├── click v8.4.2
│   │   │   │   │   ├── opentelemetry-api v1.44.0 (*)
│   │   │   │   │   ├── packaging v26.3
│   │   │   │   │   ├── platformdirs v4.11.3
│   │   │   │   │   ├── protobuf v6.33.6
│   │   │   │   │   ├── pydantic v2.13.4 (*)
│   │   │   │   │   ├── pyyaml v6.0.3
│   │   │   │   │   ├── requests v2.34.2 (*)
│   │   │   │   │   ├── sentry-sdk v2.68.0
│   │   │   │   │   │   ├── certifi v2026.7.22
│   │   │   │   │   │   └── urllib3 v2.7.0
│   │   │   │   │   └── typing-extensions v4.16.0
│   │   │   │   └── x-transformers v2.25.5
│   │   │   │       ├── einops v0.8.2
│   │   │   │       ├── einx v0.4.3 (*)
│   │   │   │       ├── loguru v0.7.3
│   │   │   │       ├── packaging v26.3
│   │   │   │       ├── torch v2.9.0 (*)
│   │   │   │       └── torch-einops-utils v0.1.20
│   │   │   │           ├── einops v0.8.2
│   │   │   │           └── torch v2.9.0 (*)
│   │   │   ├── torch v2.9.0 (extra: f5-tts-server) (*)
│   │   │   ├── torchaudio v2.9.0 (extra: f5-tts-server) (*)
│   │   │   ├── kokoro v0.9.4 (extra: kokoro-server)
│   │   │   │   ├── huggingface-hub v0.36.2 (*)
│   │   │   │   ├── loguru v0.7.3
│   │   │   │   ├── misaki[en] v0.9.4
│   │   │   │   │   ├── addict v2.4.0
│   │   │   │   │   ├── regex v2026.7.19
│   │   │   │   │   ├── espeakng-loader v0.2.4 (extra: en)
│   │   │   │   │   ├── num2words v0.5.14 (extra: en) (*)
│   │   │   │   │   ├── phonemizer-fork v3.3.2 (extra: en)
│   │   │   │   │   │   ├── attrs v26.1.0
│   │   │   │   │   │   ├── dlinfo v2.0.0
│   │   │   │   │   │   ├── joblib v1.5.3
│   │   │   │   │   │   ├── segments v2.4.0
│   │   │   │   │   │   │   ├── csvw v4.1.0
│   │   │   │   │   │   │   │   ├── babel v2.18.0
│   │   │   │   │   │   │   │   ├── isodate v0.7.2
│   │   │   │   │   │   │   │   ├── jsonschema v4.26.0 (*)
│   │   │   │   │   │   │   │   ├── language-tags v1.3.1
│   │   │   │   │   │   │   │   ├── python-dateutil v2.9.0.post0 (*)
│   │   │   │   │   │   │   │   ├── rdflib v7.6.0
│   │   │   │   │   │   │   │   │   └── pyparsing v3.3.2
│   │   │   │   │   │   │   │   ├── rfc3986 v1.5.0
│   │   │   │   │   │   │   │   ├── termcolor v3.3.0
│   │   │   │   │   │   │   │   └── uritemplate v4.2.0
│   │   │   │   │   │   │   └── regex v2026.7.19
│   │   │   │   │   │   └── typing-extensions v4.16.0
│   │   │   │   │   ├── spacy v3.8.4 (extra: en) (*)
│   │   │   │   │   └── spacy-curated-transformers v0.3.1 (extra: en)
│   │   │   │   │       ├── curated-tokenizers v0.0.9
│   │   │   │   │       │   └── regex v2026.7.19
│   │   │   │   │       ├── curated-transformers v0.1.1
│   │   │   │   │       │   └── torch v2.9.0 (*)
│   │   │   │   │       └── torch v2.9.0 (*)
│   │   │   │   ├── numpy v2.5.2
│   │   │   │   ├── torch v2.9.0 (*)
│   │   │   │   └── transformers v4.50.0 (*)
│   │   │   ├── soundfile v0.13.1 (extra: kokoro-server) (*)
│   │   │   ├── piper-tts v1.7.0 (extra: piper-server)
│   │   │   │   ├── onnxruntime v1.29.0 (*)
│   │   │   │   └── pathvalidate v3.3.1
│   │   │   ├── lexigram-testing v0.1.3007 (extra: test) (*)
│   │   │   ├── pytest v9.1.1 (extra: test) (*)
│   │   │   ├── pytest-asyncio v1.4.0 (extra: test) (*)
│   │   │   ├── pytest-cov v7.1.0 (extra: test) (*)
│   │   │   ├── pytest-mock v3.15.1 (extra: test) (*)
│   │   │   ├── mypy v2.3.1 (group: dev) (*)
│   │   │   └── ruff v0.16.3 (group: dev)
│   │   ├── lexigram-multimedia-upscale v0.1.3007
│   │   │   ├── aiohttp v3.14.3 (*)
│   │   │   ├── lexigram v0.1.3009 (*)
│   │   │   ├── lexigram-contracts v0.1.3007 (*)
│   │   │   ├── typing-extensions v4.16.0
│   │   │   ├── mypy v2.3.1 (extra: dev) (*)
│   │   │   ├── ruff v0.16.3 (extra: dev)
│   │   │   ├── lexigram-testing v0.1.3007 (extra: test) (*)
│   │   │   ├── pytest v9.1.1 (extra: test) (*)
│   │   │   ├── pytest-asyncio v1.4.0 (extra: test) (*)
│   │   │   ├── pytest-cov v7.1.0 (extra: test) (*)
│   │   │   ├── pytest-mock v3.15.1 (extra: test) (*)
│   │   │   ├── mypy v2.3.1 (group: dev) (*)
│   │   │   └── ruff v0.16.3 (group: dev)
│   │   ├── lexigram-multimedia-video v0.1.3007
│   │   │   ├── aiohttp v3.14.3 (*)
│   │   │   ├── lexigram v0.1.3009 (*)
│   │   │   ├── lexigram-contracts v0.1.3007 (*)
│   │   │   ├── typing-extensions v4.16.0
│   │   │   ├── diffusers v0.32.2 (extra: cogvideox-server) (*)
│   │   │   ├── torch v2.9.0 (extra: cogvideox-server) (*)
│   │   │   ├── transformers v4.50.0 (extra: cogvideox-server) (*)
│   │   │   ├── mypy v2.3.1 (extra: dev) (*)
│   │   │   ├── ruff v0.16.3 (extra: dev)
│   │   │   ├── diffusers v0.32.2 (extra: svd-server) (*)
│   │   │   ├── torch v2.9.0 (extra: svd-server) (*)
│   │   │   ├── lexigram-testing v0.1.3007 (extra: test) (*)
│   │   │   ├── pytest v9.1.1 (extra: test) (*)
│   │   │   ├── pytest-asyncio v1.4.0 (extra: test) (*)
│   │   │   ├── pytest-cov v7.1.0 (extra: test) (*)
│   │   │   ├── pytest-mock v3.15.1 (extra: test) (*)
│   │   │   ├── mypy v2.3.1 (group: dev) (*)
│   │   │   └── ruff v0.16.3 (group: dev)
│   │   ├── lexigram-storage v0.1.3007 (*)
│   │   ├── lexigram-tasks v0.1.3007 (*)
│   │   ├── mypy v2.3.1 (extra: dev) (*)
│   │   ├── ruff v0.16.3 (extra: dev)
│   │   ├── lexigram-testing v0.1.3007 (extra: test) (*)
│   │   ├── pytest v9.1.1 (extra: test) (*)
│   │   ├── pytest-asyncio v1.4.0 (extra: test) (*)
│   │   ├── pytest-cov v7.1.0 (extra: test) (*)
│   │   ├── pytest-mock v3.15.1 (extra: test) (*)
│   │   ├── mypy v2.3.1 (group: dev) (*)
│   │   └── ruff v0.16.3 (group: dev)
│   ├── lexigram-multimedia-beat v0.1.3007 (extra: all) (*)
│   ├── lexigram-multimedia-image v0.1.3007 (extra: all) (*)
│   ├── lexigram-multimedia-interpolate v0.1.3007 (extra: all) (*)
│   ├── lexigram-multimedia-music v0.1.3007 (extra: all) (*)
│   ├── lexigram-multimedia-tts v0.1.3007 (extra: all) (*)
│   ├── lexigram-multimedia-upscale v0.1.3007 (extra: all) (*)
│   ├── lexigram-multimedia-video v0.1.3007 (extra: all) (*)
│   ├── lexigram-nosql v0.1.3007 (extra: all) (*)
│   ├── lexigram-notification v0.1.3007 (extra: all)
│   │   ├── aiofiles v25.1.0
│   │   ├── aiohttp v3.14.3 (*)
│   │   ├── lexigram v0.1.3009 (*)
│   │   ├── lexigram-contracts v0.1.3007 (*)
│   │   ├── pywebpush v2.4.0
│   │   │   ├── aiohttp v3.14.3 (*)
│   │   │   ├── cryptography v50.0.0 (*)
│   │   │   ├── http-ece v1.2.1
│   │   │   │   └── cryptography v50.0.0 (*)
│   │   │   ├── py-vapid v1.9.4
│   │   │   │   └── cryptography v50.0.0 (*)
│   │   │   └── requests v2.34.2 (*)
│   │   ├── starlette v1.6.0 (*)
│   │   ├── typer v0.27.1 (*)
│   │   ├── cryptography v50.0.0 (extra: apns) (*)
│   │   ├── httpx[http2] v0.28.1 (extra: apns) (*)
│   │   ├── pyjwt v2.13.0 (extra: apns) (*)
│   │   ├── mypy v2.3.1 (extra: dev) (*)
│   │   ├── ruff v0.16.3 (extra: dev)
│   │   ├── sendgrid v6.12.5 (extra: sendgrid)
│   │   │   ├── cryptography v50.0.0 (*)
│   │   │   ├── python-http-client v3.3.7
│   │   │   └── werkzeug v3.1.8
│   │   │       └── markupsafe v3.0.3
│   │   ├── httpx v0.28.1 (extra: slack) (*)
│   │   ├── slack-sdk v3.43.0 (extra: slack)
│   │   ├── lexigram-testing v0.1.3007 (extra: test) (*)
│   │   ├── pytest v9.1.1 (extra: test) (*)
│   │   ├── pytest-asyncio v1.4.0 (extra: test) (*)
│   │   ├── pytest-cov v7.1.0 (extra: test) (*)
│   │   ├── pytest-mock v3.15.1 (extra: test) (*)
│   │   ├── twilio v9.11.0 (extra: twilio)
│   │   │   ├── aiohttp v3.14.3 (*)
│   │   │   ├── aiohttp-retry v2.9.1
│   │   │   │   └── aiohttp v3.14.3 (*)
│   │   │   ├── pyjwt v2.13.0 (*)
│   │   │   └── requests v2.34.2 (*)
│   │   ├── pywebpush v2.4.0 (extra: web-push) (*)
│   │   ├── httpx v0.28.1 (extra: whatsapp) (*)
│   │   ├── mypy v2.3.1 (group: dev) (*)
│   │   └── ruff v0.16.3 (group: dev)
│   ├── lexigram-queue v0.1.3007 (extra: all)
│   │   ├── jinja2 v3.1.6 (*)
│   │   ├── lexigram v0.1.3009 (*)
│   │   ├── lexigram-contracts v0.1.3007 (*)
│   │   ├── starlette v1.6.0 (*)
│   │   ├── mypy v2.3.1 (extra: dev) (*)
│   │   ├── ruff v0.16.3 (extra: dev)
│   │   ├── mypy v2.3.1 (group: dev) (*)
│   │   └── ruff v0.16.3 (group: dev)
│   ├── lexigram-resilience v0.1.3007 (extra: all)
│   │   ├── lexigram v0.1.3009 (*)
│   │   ├── lexigram-contracts v0.1.3007 (*)
│   │   ├── mypy v2.3.1 (extra: dev) (*)
│   │   ├── ruff v0.16.3 (extra: dev)
│   │   ├── lexigram-sql v0.1.3007 (extra: idempotency-database) (*)
│   │   ├── lexigram-cache v0.1.3007 (extra: idempotency-redis) (*)
│   │   ├── lexigram-testing v0.1.3007 (extra: test) (*)
│   │   ├── pytest v9.1.1 (extra: test) (*)
│   │   ├── pytest-asyncio v1.4.0 (extra: test) (*)
│   │   ├── pytest-cov v7.1.0 (extra: test) (*)
│   │   ├── pytest-mock v3.15.1 (extra: test) (*)
│   │   ├── mypy v2.3.1 (group: dev) (*)
│   │   └── ruff v0.16.3 (group: dev)
│   ├── lexigram-search v0.1.3007 (extra: all) (*)
│   ├── lexigram-secrets v0.1.3007 (extra: all)
│   │   ├── botocore v1.40.61 (*)
│   │   ├── lexigram v0.1.3009 (*)
│   │   ├── lexigram-contracts v0.1.3007 (*)
│   │   ├── typing-extensions v4.16.0
│   │   ├── aioboto3 v15.5.0 (extra: all)
│   │   │   ├── aiobotocore[boto3] v2.25.1 (*)
│   │   │   └── aiofiles v25.1.0
│   │   ├── azure-identity v1.25.3 (extra: all)
│   │   │   ├── azure-core v1.41.0 (*)
│   │   │   ├── cryptography v50.0.0 (*)
│   │   │   ├── msal v1.37.0
│   │   │   │   ├── cryptography v50.0.0 (*)
│   │   │   │   ├── pyjwt[crypto] v2.13.0 (*)
│   │   │   │   └── requests v2.34.2 (*)
│   │   │   ├── msal-extensions v1.3.1
│   │   │   │   └── msal v1.37.0 (*)
│   │   │   └── typing-extensions v4.16.0
│   │   ├── azure-keyvault-secrets v4.11.1 (extra: all)
│   │   │   ├── azure-core v1.41.0 (*)
│   │   │   ├── isodate v0.7.2
│   │   │   └── typing-extensions v4.16.0
│   │   ├── google-cloud-secret-manager v2.30.0 (extra: all)
│   │   │   ├── google-api-core[grpc] v2.34.0 (*)
│   │   │   ├── google-auth v2.56.3 (*)
│   │   │   ├── grpc-google-iam-v1 v0.14.5
│   │   │   │   ├── googleapis-common-protos[grpc] v1.75.1 (*)
│   │   │   │   ├── grpcio v1.78.0 (*)
│   │   │   │   └── protobuf v6.33.6
│   │   │   ├── grpcio v1.78.0 (*)
│   │   │   ├── proto-plus v1.28.3 (*)
│   │   │   └── protobuf v6.33.6
│   │   ├── hvac v2.4.0 (extra: all)
│   │   │   └── requests v2.34.2 (*)
│   │   ├── aioboto3 v15.5.0 (extra: aws) (*)
│   │   ├── azure-identity v1.25.3 (extra: azure) (*)
│   │   ├── azure-keyvault-secrets v4.11.1 (extra: azure) (*)
│   │   ├── mypy v2.3.1 (extra: dev) (*)
│   │   ├── ruff v0.16.3 (extra: dev)
│   │   ├── google-cloud-secret-manager v2.30.0 (extra: gcp) (*)
│   │   ├── lexigram-testing v0.1.3007 (extra: test) (*)
│   │   ├── pytest v9.1.1 (extra: test) (*)
│   │   ├── pytest-asyncio v1.4.0 (extra: test) (*)
│   │   ├── pytest-cov v7.1.0 (extra: test) (*)
│   │   ├── pytest-mock v3.15.1 (extra: test) (*)
│   │   ├── hvac v2.4.0 (extra: vault) (*)
│   │   ├── mypy v2.3.1 (group: dev) (*)
│   │   └── ruff v0.16.3 (group: dev)
│   ├── lexigram-sql v0.1.3007 (extra: all) (*)
│   ├── lexigram-storage v0.1.3007 (extra: all) (*)
│   ├── lexigram-tasks v0.1.3007 (extra: all) (*)
│   ├── lexigram-tenancy v0.1.3007 (extra: all) (*)
│   ├── lexigram-testing v0.1.3007 (extra: all) (*)
│   ├── lexigram-ui v0.1.3009 (extra: all) (*)
│   ├── lexigram-vector v0.1.3007 (extra: all) (*)
│   ├── lexigram-web v0.1.3007 (extra: all) (*)
│   ├── lexigram-webhook v0.1.3007 (extra: all)
│   │   ├── httpx v0.28.1 (*)
│   │   ├── lexigram v0.1.3009 (*)
│   │   ├── lexigram-contracts v0.1.3007 (*)
│   │   ├── starlette v1.6.0 (*)
│   │   ├── lexigram-sql v0.1.3007 (extra: sql) (*)
│   │   ├── mypy v2.3.1 (group: dev) (*)
│   │   └── ruff v0.16.3 (group: dev)
│   ├── lexigram-workflow v0.1.3007 (extra: all) (*)
│   ├── lexigram-audit v0.1.3007 (extra: auth) (*)
│   ├── lexigram-auth v0.1.3007 (extra: auth) (*)
│   ├── lexigram-cache v0.1.3007 (extra: cache) (*)
│   ├── lexigram-nosql v0.1.3007 (extra: db) (*)
│   ├── lexigram-search v0.1.3007 (extra: db) (*)
│   ├── lexigram-storage v0.1.3007 (extra: db) (*)
│   ├── mypy v2.3.1 (extra: dev) (*)
│   ├── pre-commit v4.6.2 (extra: dev) (*)
│   ├── ruff v0.16.3 (extra: dev)
│   ├── mkdocs v1.6.1 (extra: docs) (*)
│   ├── mkdocs-material v9.7.7 (extra: docs) (*)
│   ├── lexigram-events v0.1.3007 (extra: events) (*)
│   ├── lexigram-graphql v0.1.3007 (extra: graphql) (*)
│   ├── lexigram-monitor v0.1.3007 (extra: monitor) (*)
│   ├── cryptography v50.0.0 (extra: security) (*)
│   ├── nh3 v0.3.6 (extra: security)
│   ├── lexigram-tasks v0.1.3007 (extra: tasks) (*)
│   ├── lexigram-monitor v0.1.3007 (extra: test) (*)
│   ├── pytest v9.1.1 (extra: test) (*)
│   ├── pytest-asyncio v1.4.0 (extra: test) (*)
│   ├── pytest-cov v7.1.0 (extra: test) (*)
│   ├── pytest-mock v3.15.1 (extra: test) (*)
│   └── lexigram-web[uvicorn] v0.1.3007 (extra: web) (*)
├── lexigram-contracts v0.1.3007 (*)
├── aioboto3 v15.5.0 (extra: all) (*)
├── google-cloud-firestore v2.28.1 (extra: all)
│   ├── google-api-core[grpc] v2.34.0 (*)
│   ├── google-auth v2.56.3 (*)
│   ├── google-cloud-core v2.6.1 (*)
│   ├── grpcio v1.78.0 (*)
│   ├── proto-plus v1.28.3 (*)
│   └── protobuf v6.33.6
├── motor v3.7.1 (extra: all) (*)
├── pymongo v4.17.0 (extra: all) (*)
├── mypy v2.3.1 (extra: dev) (*)
├── ruff v0.16.3 (extra: dev)
├── aioboto3 v15.5.0 (extra: dynamodb) (*)
├── google-cloud-firestore v2.28.1 (extra: firestore) (*)
├── motor v3.7.1 (extra: mongodb) (*)
├── pymongo v4.17.0 (extra: mongodb) (*)
├── lexigram-testing v0.1.3007 (extra: test) (*)
├── pytest v9.1.1 (extra: test) (*)
├── pytest-asyncio v1.4.0 (extra: test) (*)
├── pytest-cov v7.1.0 (extra: test) (*)
├── pytest-mock v3.15.1 (extra: test) (*)
├── mypy v2.3.1 (group: dev) (*)
└── ruff v0.16.3 (group: dev)
joblib v1.5.3 (group: tooling)
itsdangerous v2.2.0 (group: tooling)
import-linter v2.6 (group: tooling)
├── click v8.4.2
├── grimp v3.13
│   └── typing-extensions v4.16.0
└── typing-extensions v4.16.0
granian v2.8.1 (group: tooling) (*)
botocore v1.40.61 (group: tooling) (*)
azure-servicebus v7.14.3 (group: tooling) (*)
asyncpg v0.31.0 (group: tooling)
aiosqlite v0.22.1 (group: tooling)
nh3 v0.3.6 (group: security)
websockets v17.0.1 (group: qa)
uvicorn v0.52.4 (group: qa) (*)
typer v0.27.1 (group: qa) (*)
scikit-learn v1.9.0 (group: qa) (*)
redis v8.1.0 (group: qa)
pytest-playwright v0.9.0 (group: qa) (*)
pytest-mock v3.15.1 (group: qa) (*)
pytest-cov v7.1.0 (group: qa) (*)
pytest-asyncio v1.4.0 (group: qa) (*)
pytest v9.1.1 (group: qa) (*)
pymongo v4.17.0 (group: qa) (*)
psutil v7.2.2 (group: qa)
motor v3.7.1 (group: qa) (*)
memory-profiler v0.61.0 (group: qa)
└── psutil v7.2.2
jinja2 v3.1.6 (group: qa) (*)
itsdangerous v2.2.0 (group: qa)
httpx v0.28.1 (group: qa) (*)
granian v2.8.1 (group: qa) (*)
asyncpg v0.31.0 (group: qa)
aiosqlite v0.22.1 (group: qa)
aiomysql v0.3.2 (group: qa) (*)
lexigram-workflow v0.1.3007 (*)
lexigram-webhook v0.1.3007 (*)
lexigram-web v0.1.3007 (*)
lexigram-vector v0.1.3007 (*)
lexigram-ui v0.1.3009 (*)
lexigram-testing v0.1.3007 (*)
lexigram-tenancy v0.1.3007 (*)
lexigram-tasks v0.1.3007 (*)
lexigram-storage v0.1.3007 (*)
lexigram-sql v0.1.3007 (*)
lexigram-secrets v0.1.3007 (*)
lexigram-search v0.1.3007 (*)
lexigram-resilience v0.1.3007 (*)
lexigram-queue v0.1.3007 (*)
lexigram-notification v0.1.3007 (*)
lexigram-nosql v0.1.3007 (*)
lexigram-multimedia-video v0.1.3007 (*)
lexigram-multimedia-upscale v0.1.3007 (*)
lexigram-multimedia-tts v0.1.3007 (*)
lexigram-multimedia-music v0.1.3007 (*)
lexigram-multimedia-interpolate v0.1.3007 (*)
lexigram-multimedia-image v0.1.3007 (*)
lexigram-multimedia-beat v0.1.3007 (*)
lexigram-multimedia v0.1.3007 (*)
lexigram-monitor v0.1.3007 (*)
lexigram-http v0.1.3007 (*)
lexigram-graphql v0.1.3007 (*)
lexigram-graph v0.1.3007 (*)
lexigram-features v0.1.3007 (*)
lexigram-events v0.1.3007 (*)
lexigram-contracts v0.1.3007 (*)
lexigram-cli v0.1.3007 (*)
lexigram-cache v0.1.3007 (*)
lexigram-auth v0.1.3007 (*)
lexigram-audit v0.1.3007 (*)
lexigram-ai-workers v0.1.3007 (*)
lexigram-ai-skills v0.1.3007 (*)
lexigram-ai-session v0.1.3007 (*)
lexigram-ai-relay-gateway v0.1.3007 (*)
lexigram-ai-relay v0.1.3007 (*)
lexigram-ai-rag v0.1.3007 (*)
lexigram-ai-prompt v0.1.3007 (*)
lexigram-ai-observability v0.1.3007 (*)
lexigram-ai-memory v0.1.3007 (*)
lexigram-ai-mcp v0.1.3008 (*)
lexigram-ai-llm v0.1.3007 (*)
lexigram-ai-guard v0.1.3007 (*)
lexigram-ai-governance v0.1.3007 (*)
lexigram-ai-feedback v0.1.3007 (*)
lexigram-ai-evaluation v0.1.3007 (*)
lexigram-ai-agents v0.1.3007 (*)
lexigram-ai v0.1.3007 (*)
lexigram-admin v0.1.3010 (*)
lexigram v0.1.3009 (*)
(*) Package tree already displayed
