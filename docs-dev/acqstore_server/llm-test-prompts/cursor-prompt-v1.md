You are working inside the CloudScope repository.

Your task is to determine whether the AcqStore Server v2 documentation is sufficient for a new developer to build a browser client.

Read ONLY these documents first:

    docs-dev/acqstore_server/README.md

then

    docs-dev/acqstore_server/client-roadmap.md

Do not begin by reading the reference documentation unless the roadmap explicitly tells you to.

Your implementation task is to create a new standalone HTML file:

    scripts/acqstore_server/demo_cursor_client.html

Requirements:

- Pure HTML + JavaScript.
- No build system.
- No npm.
- No React/Vue/etc.
- No Python.
- Use only browser APIs.
- Use fetch().
- Use Canvas or Plotly for image display.
- The page should be completely self-contained.

The client should:

1. Verify the server is running.
2. Query server capabilities.
3. Allow opening an acquisition using the v2 API.
4. Display useful acquisition metadata.
5. Display the acquisition header.
6. Download and display one source image plane.
7. Perform whatever transpose/conversion the API documentation requires.
8. Allow deleting the session.

Important:

Do not ask a human how the API works.

Instead, determine everything from:

- the source code in src/acqstore_server/
- docs-dev/acqstore_server/
- the existing demo application
- the OpenAPI schema if needed

Treat the documentation as authoritative.

If something is unclear, make your best engineering judgement and continue.

When finished, write a critique.

Specifically answer:

1. What documentation was sufficient?
2. What documentation was confusing?
3. What assumptions were required?
4. Which reference documents did you actually open?
5. What information should have been in client-roadmap.md but was missing?
6. Estimate how long a new developer would need before becoming productive.
7. Recommend concrete improvements to the documentation.

Do not modify the server.

Do not modify src/acqstore_server.

Your goal is to evaluate whether the documentation is sufficient for an independent developer to successfully integrate with the AcqStore Server v2 API.