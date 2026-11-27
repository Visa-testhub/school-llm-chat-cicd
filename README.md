# Week 5 - Self-hosted LLM Chat

Flask chat application using Gunicorn, Ollama, MySQL and Nginx.

Chat: http://195.148.21.169/viikko5/

## Setup

- Install Python, Nginx, MySQL, Ollama and rsync.
- Download the model: `ollama pull qwen2.5:0.5b`
- Create the Linux service user `chatapp`.
- Create the MySQL database `chatapp` and a user with SELECT and INSERT permissions.
- Apply `deploy/sql/schema.sql`.
- Create `/etc/chatapp/chatapp.env` with database credentials and Ollama settings. Set permissions to 640 and ownership to root:chatapp.
- Copy the repository to `/opt/chatapp/app`.
- Include `snippets/chatapp.conf` in the existing Nginx server configuration.

## Testing

```bash
pip install -r requirements-dev.txt
ruff check .
python -m pytest
bash -n scripts/deploy.sh
```

## Deployment

Configure the following GitHub Actions secrets:

- CPOUTA_HOST
- CPOUTA_USER
- CPOUTA_SSH_KEY
- CPOUTA_KNOWN_HOSTS

Push to main. GitHub Actions runs the tests, transfers the files and executes `scripts/deploy.sh` on the server if the tests pass.

Deployment is verified using `/viikko5/health`, which returns the running commit SHA.

Further documentation and test results are on the chat page.