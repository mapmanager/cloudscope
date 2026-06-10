# Technologies and engineering strategy

CloudScope is a scientific image-analysis application designed around a strict separation between backend data/analysis code and frontend user interfaces. The same backend engine is used from the desktop GUI, browser GUI, tests, and scripted workflows.

## Separation of concerns

CloudScope is split into three source packages: `acqstore`, `nicewidgets`, and `cloudscope`. This keeps scientific logic out of the GUI and makes the analysis layer scriptable, testable, and reusable.

## Reproducible development with uv

CloudScope uses `uv` for dependency management, local development, testing, documentation, and command execution.

## Testing and CI/CD

The project uses `pytest` for unit tests across backend analysis code, reusable widgets, and application logic. GitHub Actions run tests on repository events so regressions can be caught early.

## Desktop and browser distribution

The same application can run as a desktop GUI or as a browser GUI. The public browser deployment makes CloudScope available for trial use without installing desktop software.
