<!--
  Originally from PySpur (https://github.com/PySpur-Dev/pyspur), licensed under Apache-2.0.
  Modified by Alokin LLC, 2026; modifications licensed under FCL-1.0-ALv2.
  SPDX-License-Identifier: Apache-2.0 AND FCL-1.0-ALv2
-->
# Development

## Adding an NPM Package

You can add a package to `package.json` via your favorite package manager and the next time your Docker container gets built from scratch, it will install that package too.

### Adding to an Existing Docker Container

If you need to add a package to a running Docker container for immediate use, follow these steps:

1. Access the running container:

```sh
docker compose -f docker-compose.dev.yml exec frontend sh
```

2. Install the package:

```sh
npm install <package_name>
```

3. Restart the container to apply changes:

```sh
docker compose -f docker-compose.dev.yml restart frontend
```
