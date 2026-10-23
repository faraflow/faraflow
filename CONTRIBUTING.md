<!--
  Copyright 2026 Alokin LLC
  SPDX-License-Identifier: FCL-1.0-ALv2
-->
# Contributing to Faraflow

Thank you for helping improve Faraflow. This page explains how to contribute and what we need from you first.

## Before you contribute code: accept the contributor agreement

**We can only merge code from contributors who have accepted the [Faraflow Contributor Agreement](./CONTRIBUTOR_AGREEMENT.md).** You keep ownership of what you write. The agreement lets Alokin LLC, the licensor of Faraflow, include your code and license it as described in the agreement, including under separate terms for partners and customers.

How it works:

1. Open a pull request.
2. The contributor-agreement check on the pull request asks you to accept the agreement. Reply with the comment it shows:
   > I have read the Faraflow Contributor Agreement and I accept it.
3. Once you have accepted, the check passes. You only accept once; it covers your later contributions too.

If you contribute for your employer, read section 5 of the agreement first. Do not submit code that you do not have the right to license, or that comes from somewhere else, unless you tell us its source and license in the pull request.

## License of what you contribute

Faraflow is released under the [Fair Core License](./LICENSE.md) (`FCL-1.0-ALv2`). Parts of the code come from the Apache-2.0 PySpur project; [NOTICE](./NOTICE) explains which license applies to which file. Your contribution is licensed as the contributor agreement describes.

## Reporting problems and proposing changes

- Search the existing issues first, then open an issue describing the problem or the change you want. For larger changes, agree on the approach in an issue before you write code.
- Keep each pull request to one logical change, and describe what it does and how you tested it.

## Development setup

Follow the Quick start in the [README](./README.md). The repository has a Python (FastAPI) backend in `backend/` and a SvelteKit frontend in `frontend/`; both reload automatically while the stack runs.

Run `npm`, `pip` and `uv` commands inside the containers, not on your machine, for example:

```sh
docker compose -f docker-compose.dev.yml exec frontend npm run check
docker compose -f docker-compose.dev.yml exec backend ruff check pyspur/
```

Before you open a pull request:

- Frontend: `npm run check`, `npm run lint` and `npm run format`.
- Backend: `ruff check pyspur/` and `ruff format pyspur/`. The code base has existing lint warnings; do not add new ones.
- Add or update tests under `backend/tests/` when you change backend behavior.

Do not commit secrets, `.env` files, API keys, or local data.

## License headers

You do not need to add license headers. When we merge a pull request, maintainers add the header described in [NOTICE](./NOTICE) to new and changed files with `scripts/apply_license_headers.py`. Please do not remove existing headers.
