# Installation and Running Instructions
```markdown
# Installation and Running Instructions

Minimum requirements

- Python: 3.9+

Steps

1. Create and activate a virtual environment (recommended)

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```

2. Install dependencies

```powershell
pip install -U pip
pip install -r requirements.txt
```

3. Configure keys and settings

- Edit `config/PROTECTED_INFO.json` and provide at least the following fields:
	- `TELEGRAM_TOKEN`
	- `DEEPSEEK_API_KEY`
	- `DEEPSEEK_API_URL`

- (Optional) The project uses `.env.prod` as the NoneBot environment file. Create this file or set the required environment variables in your system if needed.

4. Run the project

```powershell
python bot.py
```

Need help? Tell me whether you're running this on Windows, Linux, or inside a container, and whether you want me to install dependencies and run a quick test.

This project is maintained by an impulsive college student with little prior experience — please excuse any rough edges.