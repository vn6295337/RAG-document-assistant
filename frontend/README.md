# RAG Document Assistant - Frontend

React + Vite frontend for the RAG Document Assistant.

## Stack

- React 18
- Vite
- Tailwind CSS v4

## Features

- Dropbox OAuth integration for file selection
- Client-side text chunking
- Zero-storage architecture (files never stored on server)
- Real-time processing status
- Query interface with cited answers

## Development

```bash
npm install
npm run dev
```

## Build

```bash
npm run build
```

## Environment

Create `.env` with:

```
VITE_API_URL=http://localhost:8000
VITE_DROPBOX_APP_KEY=your_dropbox_app_key
```
