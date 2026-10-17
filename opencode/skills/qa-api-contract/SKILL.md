---
name: QA API contract
description: Verifies code against an OpenAPI or Swagger spec, or against JSON Schema, GraphQL SDL or protobuf. Covers operations, parameters, schemas, enums, status codes and error shapes, and flags breaking changes for existing clients. Use it when a repository has an API spec, or when a change touches routes, handlers, DTOs or API clients.
---

# API contract check

## Find the contract

- **Spec files:** look for `openapi.{yaml,yml,json}`, `swagger.*`, `*.openapi.*`, `api/**/*.yaml`, `docs/api/**`, `schema.graphql`, `*.proto`, `asyncapi.*` and JSON Schemas.
- **Generated specs** (FastAPI `/openapi.json`, NestJS Swagger, springdoc): when the spec is generated from the code, the code is the source and a checked-in copy may be stale. Say which of the two you compared.
- **Source of truth:** find out whether the spec or the code is the master in this repository. The README or AGENTS.md often says. If nothing says, report that as missing information. Also note the spec version.

## Map the operations

Make one row for each operation that the change touches, directly or through a schema:

`METHOD /path` → operationId → handler (`file:line`) → request model → response model for each status

Then check each row against these points:
- **Route:** it exists with the same method and path. Check path parameter names, trailing slashes and the version prefix.
- **Parameters:** where each one goes (path, query, header or cookie), and its name, required flag, type, format, default, enum, minimum and maximum, and pattern.
- **Request body:** content type, required fields, nullable versus optional, `additionalProperties`, enum values, and string formats such as date-time with a time zone, uuid and email.
- **Responses:** every status the code can return is documented, including 400, 401, 403, 404, 409, 422 and 500. Every documented status can actually be reached, and the error body matches the documented error schema.
- **Field names and casing:** camelCase or snake_case matches, and no serializer renames fields silently.
- **Pagination, sorting and filtering:** the parameters and their defaults match.
- **Auth:** the security requirement of each operation matches the middleware or guards that are applied.
- **Examples:** the examples in the spec validate against its schemas and match real behaviour.

## Breaking changes for existing clients

Treat each of these as major, unless the project versions its API and the change lives in a new version:
- removing or renaming an operation, field, parameter or enum value;
- making an optional request field required, or adding a required request field;
- narrowing a type or format, or changing a default;
- changing status codes, the error shape or pagination semantics;
- changing what a field means while keeping its name.

Adding optional fields or new operations is usually safe. When it is, say so.

## Tools the project already has

A tool's answer beats a reading. If the repository already runs one of these tools (look in `package.json` scripts, a Makefile, a CI workflow or the dev dependencies), run it the way the project does and cite its output:
- [oasdiff](https://github.com/oasdiff/oasdiff): breaking changes between the base spec and the changed spec;
- [Spectral](https://github.com/stoplightio/spectral): lints the spec against the project's ruleset;
- [Schemathesis](https://github.com/schemathesis/schemathesis): generates requests from the spec and runs them against a test server.

Don't install a tool the project doesn't use. Name it in the report as a suggestion instead.

## Runtime check, when an app URL is available

- Prefer read-only calls (GET and HEAD) against a local or test environment. Never use production or real credentials.
- With a browser (the `qa-browser` skill), use the network requests to compare the real requests and responses with the spec: status, fields, types, enum values and nulls.
- Without a browser, ask before you run `curl` against the URL, then compare the response body with the schema field by field.

## Report

For each mismatch, give:
- the operation;
- the spec location, as file plus JSON pointer (for example `#/paths/~1orders/get/responses/200`);
- the code location;
- the expected and the observed behaviour.
