# Configuration Templates

This directory contains configuration templates for the Genesis Replicator Framework.

## Blockchain Configuration

The `blockchain.json` template provides configuration for supported blockchain networks:

- BNB Chain (BSC)
  - RPC and WebSocket endpoints
  - Gas configuration
  - Rate limiting
  - Contract defaults

- Ethereum
  - Infura integration
  - Gas strategies
  - Network parameters

## AI Model Configuration

The `ai_models.json` template configures supported AI models:

- GPT-4
- Claude 3
- LLaMA 2
- Mistral AI
- Google Gemini

Each model configuration includes:
- Provider settings
- Token limits
- Rate limiting
- Retry configuration
- Fallback models

## Validation Schema

The `validation_schema.json` defines JSON Schema for validating configurations:

- Blockchain schema
  - Required fields
  - Data types
  - Value constraints

- AI model schema
  - Provider validation
  - Parameter ranges
  - Rate limit validation

## Usage

1. Copy the appropriate template
2. Modify parameters as needed
3. Validate against schema
4. Place in config directory

Example:
```python
from genesis_replicator.config import ConfigValidator

# Load and validate configuration
validator = ConfigValidator()
config = validator.load_and_validate("my_config.json")
```

## Environment Variables


Required environment variables:
- `INFURA_KEY`: Infura API key for Ethereum
- `OPENAI_API_KEY`: OpenAI API key
- `ANTHROPIC_API_KEY`: Anthropic API key
- `MISTRAL_API_KEY`: Mistral AI API key
- `GOOGLE_API_KEY`: Google API key

## Extending

To add new configurations:
1. Create template in appropriate format
2. Update validation schema
3. Add documentation
4. Test validation
