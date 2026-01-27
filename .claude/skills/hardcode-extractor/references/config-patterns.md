# Configuration Patterns by Language

Language-specific patterns for extracting hardcodes into config files.

## Python

### Recommended Structure
```
project/
├── .env                 # Secrets (gitignored)
├── .env.example         # Template for .env
├── config/
│   ├── __init__.py      # Exports settings
│   ├── settings.py      # Main config with env loading
│   └── constants.py     # Non-sensitive constants
```

### Settings Module Pattern
```python
# config/settings.py
import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

# Required - will raise if missing
API_KEY = os.environ["API_KEY"]
DATABASE_URL = os.environ["DATABASE_URL"]

# Optional with defaults
DEBUG = os.getenv("DEBUG", "false").lower() == "true"
API_TIMEOUT = int(os.getenv("API_TIMEOUT", "30"))
MAX_RETRIES = int(os.getenv("MAX_RETRIES", "3"))
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")

# Derived
BASE_DIR = Path(__file__).resolve().parent.parent
```

### Constants Module Pattern
```python
# config/constants.py
"""Application constants that don't change per environment."""

# HTTP Status Codes (acceptable to keep)
HTTP_OK = 200
HTTP_CREATED = 201
HTTP_BAD_REQUEST = 400

# Business Constants
MAX_UPLOAD_SIZE_MB = 10
SUPPORTED_FILE_TYPES = frozenset([".pdf", ".docx", ".txt"])
DEFAULT_PAGE_SIZE = 25
```

### Pydantic Settings (Type-Safe)
```python
# config/settings.py
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    api_key: str
    database_url: str
    debug: bool = False
    api_timeout: int = 30
    max_retries: int = 3
    
    class Config:
        env_file = ".env"

settings = Settings()
```

---

## JavaScript / TypeScript

### Recommended Structure
```
project/
├── .env                 # Secrets (gitignored)
├── .env.example
├── src/
│   └── config/
│       ├── index.ts     # Main config export
│       ├── env.ts       # Environment variable loading
│       └── constants.ts # Non-sensitive constants
```

### Config Module Pattern (TypeScript)
```typescript
// src/config/env.ts
import dotenv from 'dotenv';
dotenv.config();

function required(key: string): string {
  const value = process.env[key];
  if (!value) throw new Error(`Missing required env var: ${key}`);
  return value;
}

function optional(key: string, defaultValue: string): string {
  return process.env[key] ?? defaultValue;
}

export const env = {
  // Required
  API_KEY: required('API_KEY'),
  DATABASE_URL: required('DATABASE_URL'),
  
  // Optional with defaults
  NODE_ENV: optional('NODE_ENV', 'development'),
  PORT: parseInt(optional('PORT', '3000'), 10),
  API_TIMEOUT: parseInt(optional('API_TIMEOUT', '30000'), 10),
  MAX_RETRIES: parseInt(optional('MAX_RETRIES', '3'), 10),
};

// src/config/constants.ts
export const constants = {
  MAX_UPLOAD_SIZE_BYTES: 10 * 1024 * 1024,
  SUPPORTED_MIME_TYPES: ['application/pdf', 'image/png', 'image/jpeg'],
  DEFAULT_PAGE_SIZE: 25,
} as const;

// src/config/index.ts
export { env } from './env';
export { constants } from './constants';
```

### Zod Schema Validation
```typescript
import { z } from 'zod';
import dotenv from 'dotenv';
dotenv.config();

const envSchema = z.object({
  API_KEY: z.string().min(1),
  DATABASE_URL: z.string().url(),
  PORT: z.coerce.number().default(3000),
  NODE_ENV: z.enum(['development', 'production', 'test']).default('development'),
});

export const env = envSchema.parse(process.env);
```

---

## Go

### Recommended Structure
```
project/
├── .env
├── config/
│   ├── config.go       # Config struct and loading
│   └── config.yaml     # Default values
├── internal/
│   └── constants/
│       └── constants.go
```

### Viper Config Pattern
```go
// config/config.go
package config

import (
    "github.com/spf13/viper"
)

type Config struct {
    Server   ServerConfig
    Database DatabaseConfig
    API      APIConfig
}

type ServerConfig struct {
    Port         int    `mapstructure:"port"`
    Host         string `mapstructure:"host"`
    ReadTimeout  int    `mapstructure:"read_timeout"`
    WriteTimeout int    `mapstructure:"write_timeout"`
}

type DatabaseConfig struct {
    URL string `mapstructure:"url"`
}

type APIConfig struct {
    Key        string `mapstructure:"key"`
    Timeout    int    `mapstructure:"timeout"`
    MaxRetries int    `mapstructure:"max_retries"`
}

func Load() (*Config, error) {
    viper.SetConfigName("config")
    viper.SetConfigType("yaml")
    viper.AddConfigPath(".")
    viper.AddConfigPath("./config")
    
    // Environment variable overrides
    viper.AutomaticEnv()
    viper.SetEnvPrefix("APP")
    
    // Defaults
    viper.SetDefault("server.port", 8080)
    viper.SetDefault("server.read_timeout", 10)
    viper.SetDefault("api.timeout", 30)
    viper.SetDefault("api.max_retries", 3)
    
    if err := viper.ReadInConfig(); err != nil {
        if _, ok := err.(viper.ConfigFileNotFoundError); !ok {
            return nil, err
        }
    }
    
    var cfg Config
    if err := viper.Unmarshal(&cfg); err != nil {
        return nil, err
    }
    
    return &cfg, nil
}
```

### Constants Package
```go
// internal/constants/constants.go
package constants

const (
    MaxUploadSizeMB   = 10
    DefaultPageSize   = 25
    MaxPageSize       = 100
)

var SupportedFileTypes = []string{".pdf", ".docx", ".txt"}
```

---

## Rust

### Recommended Structure
```
project/
├── .env
├── config/
│   └── default.toml
├── src/
│   ├── config.rs
│   └── constants.rs
```

### Config Crate Pattern
```rust
// src/config.rs
use config::{Config, ConfigError, Environment, File};
use serde::Deserialize;

#[derive(Debug, Deserialize)]
pub struct Settings {
    pub server: ServerSettings,
    pub database: DatabaseSettings,
    pub api: ApiSettings,
}

#[derive(Debug, Deserialize)]
pub struct ServerSettings {
    pub port: u16,
    pub host: String,
}

#[derive(Debug, Deserialize)]
pub struct DatabaseSettings {
    pub url: String,
}

#[derive(Debug, Deserialize)]
pub struct ApiSettings {
    pub key: String,
    pub timeout_secs: u64,
    pub max_retries: u32,
}

impl Settings {
    pub fn new() -> Result<Self, ConfigError> {
        let config = Config::builder()
            // Start with defaults
            .set_default("server.port", 8080)?
            .set_default("server.host", "127.0.0.1")?
            .set_default("api.timeout_secs", 30)?
            .set_default("api.max_retries", 3)?
            // Layer on config file
            .add_source(File::with_name("config/default").required(false))
            // Layer on environment (APP_SERVER__PORT, etc.)
            .add_source(Environment::with_prefix("APP").separator("__"))
            .build()?;
            
        config.try_deserialize()
    }
}

// src/constants.rs
pub const MAX_UPLOAD_SIZE_MB: usize = 10;
pub const DEFAULT_PAGE_SIZE: usize = 25;
pub const SUPPORTED_EXTENSIONS: &[&str] = &["pdf", "docx", "txt"];
```

---

## Java / Spring Boot

### Recommended Structure
```
src/main/
├── resources/
│   ├── application.properties      # Or application.yml
│   ├── application-dev.properties
│   └── application-prod.properties
└── java/com/example/
    └── config/
        ├── AppConfig.java
        └── Constants.java
```

### application.properties
```properties
# Server
server.port=${PORT:8080}
server.servlet.context-path=/api

# Database
spring.datasource.url=${DATABASE_URL}
spring.datasource.username=${DB_USERNAME}
spring.datasource.password=${DB_PASSWORD}

# Application
app.api.key=${API_KEY}
app.api.timeout=30000
app.api.max-retries=3
```

### Configuration Class
```java
// config/AppConfig.java
@Configuration
@ConfigurationProperties(prefix = "app")
public class AppConfig {
    private Api api = new Api();
    
    public static class Api {
        private String key;
        private int timeout = 30000;
        private int maxRetries = 3;
        
        // Getters and setters
    }
    
    // Getters and setters
}

// config/Constants.java
public final class Constants {
    private Constants() {} // Prevent instantiation
    
    public static final int MAX_UPLOAD_SIZE_MB = 10;
    public static final int DEFAULT_PAGE_SIZE = 25;
    public static final Set<String> SUPPORTED_FILE_TYPES = 
        Set.of(".pdf", ".docx", ".txt");
}
```

---

## C# / .NET

### Recommended Structure
```
project/
├── appsettings.json
├── appsettings.Development.json
├── appsettings.Production.json
└── Config/
    ├── AppSettings.cs
    └── Constants.cs
```

### appsettings.json
```json
{
  "Server": {
    "Port": 5000
  },
  "Api": {
    "Key": "",
    "TimeoutSeconds": 30,
    "MaxRetries": 3
  },
  "ConnectionStrings": {
    "Default": ""
  }
}
```

### Strongly-Typed Config
```csharp
// Config/AppSettings.cs
public class ApiSettings
{
    public string Key { get; set; } = string.Empty;
    public int TimeoutSeconds { get; set; } = 30;
    public int MaxRetries { get; set; } = 3;
}

// Registration in Program.cs
builder.Services.Configure<ApiSettings>(
    builder.Configuration.GetSection("Api"));

// Usage
public class MyService
{
    private readonly ApiSettings _settings;
    
    public MyService(IOptions<ApiSettings> settings)
    {
        _settings = settings.Value;
    }
}

// Config/Constants.cs
public static class Constants
{
    public const int MaxUploadSizeMB = 10;
    public const int DefaultPageSize = 25;
    public static readonly string[] SupportedFileTypes = { ".pdf", ".docx", ".txt" };
}
```

---

## Environment Files

### .env Template
```bash
# .env.example - Copy to .env and fill in values
# DO NOT commit .env to version control!

# Required
API_KEY=
DATABASE_URL=

# Optional (defaults shown)
DEBUG=false
LOG_LEVEL=INFO
API_TIMEOUT=30
MAX_RETRIES=3
PORT=8080
```

### .gitignore Entries
```gitignore
# Environment files with secrets
.env
.env.local
.env.*.local
*.env

# Keep examples
!.env.example
!.env.template
```

---

## Naming Conventions

| Type | Convention | Examples |
|------|------------|----------|
| Environment vars | SCREAMING_SNAKE_CASE | `API_KEY`, `DATABASE_URL` |
| Config properties | snake_case or camelCase | `api_timeout`, `maxRetries` |
| Constants | SCREAMING_SNAKE_CASE | `MAX_UPLOAD_SIZE`, `DEFAULT_PAGE_SIZE` |
| Config files | lowercase with dots | `config.yaml`, `appsettings.json` |

## What to Keep Inline

These are acceptable as inline literals:
- HTTP status codes: `200`, `404`, `500`
- Mathematical constants: `Math.PI`, `Math.E`
- Boolean flags in conditionals
- Array indices: `[0]`, `[-1]`
- Common defaults: `null`, `""`, `[]`, `{}`
- Type coercions: `int(x)`, `str(y)`

---

## Ruby

### Recommended Structure
```
project/
├── .env
├── config/
│   ├── application.rb
│   └── initializers/
│       └── config.rb
└── lib/
    └── constants.rb
```

### Config Pattern (with dotenv)
```ruby
# config/initializers/config.rb
require 'dotenv/load'

module Config
  # Required
  API_KEY = ENV.fetch('API_KEY')
  DATABASE_URL = ENV.fetch('DATABASE_URL')
  
  # Optional with defaults
  TIMEOUT = ENV.fetch('TIMEOUT', 30).to_i
  MAX_RETRIES = ENV.fetch('MAX_RETRIES', 3).to_i
  DEBUG = ENV.fetch('DEBUG', 'false') == 'true'
end

# lib/constants.rb
module Constants
  MAX_UPLOAD_SIZE_MB = 10
  DEFAULT_PAGE_SIZE = 25
  SUPPORTED_FORMATS = %w[pdf docx txt].freeze
end
```

---

## PHP

### Recommended Structure
```
project/
├── .env
├── config/
│   ├── config.php
│   └── constants.php
└── src/
```

### Config Pattern (with vlucas/phpdotenv)
```php
<?php
// config/config.php
require_once __DIR__ . '/../vendor/autoload.php';

$dotenv = Dotenv\Dotenv::createImmutable(__DIR__ . '/..');
$dotenv->load();

return [
    // Required
    'api_key' => $_ENV['API_KEY'] ?? throw new Exception('API_KEY required'),
    'database_url' => $_ENV['DATABASE_URL'] ?? throw new Exception('DATABASE_URL required'),
    
    // Optional with defaults
    'timeout' => (int) ($_ENV['TIMEOUT'] ?? 30),
    'max_retries' => (int) ($_ENV['MAX_RETRIES'] ?? 3),
    'debug' => filter_var($_ENV['DEBUG'] ?? false, FILTER_VALIDATE_BOOLEAN),
];

// config/constants.php
<?php
define('MAX_UPLOAD_SIZE_MB', 10);
define('DEFAULT_PAGE_SIZE', 25);
define('SUPPORTED_FORMATS', ['pdf', 'docx', 'txt']);
```

---

## CI/CD Integration

### Pre-commit Hook
```bash
#!/bin/bash
# .git/hooks/pre-commit or use pre-commit framework

# Scan for HIGH severity hardcodes (secrets)
python path/to/scan_hardcodes.py . --severity high --format json --output /tmp/hardcode-report.json

if [ $? -ne 0 ]; then
    echo "❌ BLOCKED: Hardcoded secrets detected!"
    echo "Run 'python scan_hardcodes.py . --severity high' for details"
    exit 1
fi
```

### GitHub Actions
```yaml
# .github/workflows/hardcode-check.yml
name: Hardcode Check

on: [push, pull_request]

jobs:
  scan:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      
      - name: Set up Python
        uses: actions/setup-python@v5
        with:
          python-version: '3.11'
      
      - name: Scan for hardcoded secrets
        run: |
          python scan_hardcodes.py . --severity high
        continue-on-error: false
```

### GitLab CI
```yaml
# .gitlab-ci.yml
hardcode-scan:
  stage: test
  script:
    - python scan_hardcodes.py . --severity high
  allow_failure: false
```

---

## Docker / Kubernetes

### Docker Compose
```yaml
# docker-compose.yml
services:
  app:
    build: .
    environment:
      - API_KEY=${API_KEY}
      - DATABASE_URL=${DATABASE_URL}
      - TIMEOUT=${TIMEOUT:-30}
    env_file:
      - .env  # For local development
```

### Kubernetes ConfigMap + Secret
```yaml
# configmap.yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: app-config
data:
  TIMEOUT: "30"
  MAX_RETRIES: "3"
  LOG_LEVEL: "info"

---
# secret.yaml (values should be base64 encoded)
apiVersion: v1
kind: Secret
metadata:
  name: app-secrets
type: Opaque
data:
  API_KEY: <base64-encoded-value>
  DATABASE_URL: <base64-encoded-value>

---
# deployment.yaml
spec:
  containers:
    - name: app
      envFrom:
        - configMapRef:
            name: app-config
        - secretRef:
            name: app-secrets
```

---

## Naming Conventions

| Type | Convention | Examples |
|------|------------|----------|
| Environment vars | SCREAMING_SNAKE_CASE | `API_KEY`, `DATABASE_URL` |
| Config properties | snake_case or camelCase | `api_timeout`, `maxRetries` |
| Constants | SCREAMING_SNAKE_CASE | `MAX_UPLOAD_SIZE`, `DEFAULT_PAGE_SIZE` |
| Config files | lowercase with dots | `config.yaml`, `appsettings.json` |
