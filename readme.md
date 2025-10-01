# Smart Note Summarizer

This demo app is a full-stack application that processes text inputs to generate concise summaries using an integrated LLM. It is powered by the most intelligent AI model available on the market today: OpenAI's GPT-5.

## Local setup

The project requires `Python 3.13` as well as `Node.js v24` or higher.

1. Clone the project to your system
2. Navigate to the `/backend` folder
3. Create a virtual environment & install dependencies:

```bash
python -m venv .venv
source .venv/bin/activate # Linux/mac
# .venv\Scripts\activate # Windows

pip install fastapi[standard] python-dotenv openai
```

4. Create a `.env` file in the backend folder, providing three key configuration variables:

```
OPENAI_APIKEY="sk-XXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX"
APP_VERSION="1.0.0"
APP_ENVIRONMENT="dev" # one of 'dev' or 'prod'
```

5. Run the backend server with `fastapi run`
6. Navigate back to the `/frontend` folder
7. Run npm to get it running:

```bash
npm install
npm run dev
```

## API Reference

The server supports 3 API endpoints (plus the default openAPI endpoint for automatically generated documentation):

### GET /healthcheck

Returns HTTP 200 or HTTP 503 indicating the server health state
Also returns a JSON response with key details about the server state

### POST /summarize

The main endpoint, takes the text input and generates a JSON object with the resulting summary as output

### POST /log/client

Used to send client logs to the server's log file for debugging & support