<!--
  Originally from PySpur (https://github.com/PySpur-Dev/pyspur), licensed under Apache-2.0.
  Modified by Alokin LLC, 2026; modifications licensed under FCL-1.0-ALv2.
  SPDX-License-Identifier: Apache-2.0 AND FCL-1.0-ALv2
-->
<h1 align="center">
  <picture>
    <source media="(prefers-color-scheme: dark)" srcset="./assets/faraflow-logo-dark.svg">
    <img alt="Faraflow" src="./assets/faraflow-logo-light.svg" width="320">
  </picture>
</h1>

**Build agents fast. Run workflows reliably.**

Faraflow is a visual studio and a workflow engine for business-grade AI agents. You lay out an agent's steps on a canvas, run them on your own infrastructure, and look at what every step did.

[![License: FCL-1.0-ALv2](https://img.shields.io/badge/license-FCL--1.0--ALv2-blue)](./LICENSE.md)

[![Talk to us](https://img.shields.io/badge/Talk%20to%20us-15%20min%20video%20call-FFC247?style=for-the-badge&logo=googlemeet&logoColor=white&labelColor=232E5C&color=FFC247)](https://cal.com/faraflow/dubaiaifestival) [![Message us](https://img.shields.io/badge/Message%20us-Discord-5865F2?style=for-the-badge&logo=discord&logoColor=white)](https://discord.gg/aKT5mqRBU9)

## Why Faraflow

Ask an AI agent to do a job and it works out the steps on the spot; ask again and it may choose different ones. A workflow is the same job with the steps written down, so you can test it, compare runs, and explain what it did. AI is used only in the steps that need it.

- **Plan once, run many times.** Steps are decided up front and saved as a versioned workflow.
- **See every step.** Each run is recorded node by node, with inputs, outputs and errors.
- **Recover without starting over.** Continue or retry a run from where it stopped.
- **Your infrastructure.** Faraflow runs in Docker on your own machine or servers.

## Quick start

Requires Docker with Docker Compose.

1. Clone the repository and create your `.env`:

   ```sh
   git clone https://github.com/faraflow/faraflow.git
   cd faraflow
   cp .env.example .env
   ```

2. Choose an API key for your Faraflow instance. This key is yours to make up; the script generates a random one, saves it as `PYSPUR_API_KEY` in `.env` and prints it:

   ```sh
   ./scripts/generate_api_key.sh
   ```

3. Add an OpenAI key. Create one in your [OpenAI account](https://platform.openai.com/api-keys), then add this line to `.env` (the file has a commented-out `OPENAI_API_KEY` line you can use):

   ```sh
   OPENAI_API_KEY=your-openai-key
   ```

4. Start the stack:

   ```sh
   docker compose -f docker-compose.dev.yml up --build
   ```

Open <http://localhost:6080> and paste the `PYSPUR_API_KEY` from step 2 when the app asks for it.

## What you can do today

- Build workflows on a visual canvas and start from the bundled templates.
- Run workflows that mix LLM calls and Python code.
- Open a trace of any run to see each node's inputs, outputs and errors.
- Continue or retry a run after a failure.
- Keep versions of a workflow.
- Follow your workflows and recent runs from a dashboard.

## Contributing

To contribute code, you must first accept the Faraflow contributor agreement; we can't merge a contribution until it is accepted. See [CONTRIBUTING.md](./CONTRIBUTING.md) for how.

## License

Faraflow is **Fair Source**. It is released under the [Fair Core License](https://fcl.dev) (`FCL-1.0-ALv2`):

- You can read, run and modify the code, including in production and inside your own products.
- You cannot use it to offer a competing product or service. Hosting Faraflow as a service for others is done in partnership with Alokin.
- Each release converts to Apache 2.0 two years after it is published.

See [LICENSE.md](./LICENSE.md) for the full terms. Faraflow grew out of the open-source [PySpur](https://github.com/PySpur-Dev/pyspur) project; see [NOTICE](./NOTICE) for attribution.

Faraflow is developed and supported by [Alokin](https://alokin.in).
