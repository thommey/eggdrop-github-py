# eggdrop-github-py
Eggdrop Github webhook script

# Prerequisites
You need Eggdrop v1.10.0 with python.mod (which requires Python >= 3.8) and the following Python packages:

- Flask
- pydantic
- requests

Eggdrop's python.mod supports venv (https://docs.python.org/3/library/venv.html) so you can install them without root access:

```
cd eggdrop
python3 -m venv .venv
source .venv/bin/activate
pip install Flask pydantic requests
./eggdrop
```

Always start eggdrop with the venv activated if you used this method.

You also need to register a Github Webhook (all events is fine, only some events are currently supported) with your public IP/Port and copy the secret into the script.

# Package versions
It was tested with Python 3.11.2 and the specific packages versions:

```
Flask==3.0.3
├── blinker [required: >=1.6.2, installed: 1.8.2]
├── click [required: >=8.1.3, installed: 8.1.7]
├── itsdangerous [required: >=2.1.2, installed: 2.2.0]
├── Jinja2 [required: >=3.1.2, installed: 3.1.4]
│   └── MarkupSafe [required: >=2.0, installed: 2.1.5]
└── Werkzeug [required: >=3.0.0, installed: 3.0.3]
    └── MarkupSafe [required: >=2.1.1, installed: 2.1.5]
pydantic==2.8.2
├── annotated-types [required: >=0.4.0, installed: 0.7.0]
├── pydantic_core [required: ==2.20.1, installed: 2.20.1]
│   └── typing_extensions [required: >=4.6.0,!=4.7.0, installed: 4.12.2]
└── typing_extensions [required: >=4.6.1, installed: 4.12.2]
requests==2.32.3
├── certifi [required: >=2017.4.17, installed: 2024.7.4]
├── charset-normalizer [required: >=2,<4, installed: 3.3.2]
├── idna [required: >=2.5,<4, installed: 3.7]
└── urllib3 [required: >=1.21.1,<3, installed: 2.2.2]
```
