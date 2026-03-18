# Quick Start Guide

## Virtual Environment Setup

A virtual environment has been created at `./venv`

### Activate the virtual environment:

```bash
# On Linux/macOS
source venv/bin/activate

# On Windows
venv\Scripts\activate
```

### Install dependencies (if needed):

```bash
pip install -r requirements.txt
```

### Run the application:

```bash
# Make sure to set your API key first
export ANTHROPIC_API_KEY="your-key-here"

# Run the language teacher
python -m src
```

### Deactivate when done:

```bash
deactivate
```

## Installed Packages

- `anthropic` - Claude API client
- `pydantic` - Data validation
- `python-dotenv` - Environment variable management
- `rich` - Beautiful terminal output

## Next Steps

1. Copy `.env.example` to `.env`
2. Add your `ANTHROPIC_API_KEY`
3. Run `python -m src` to start!
