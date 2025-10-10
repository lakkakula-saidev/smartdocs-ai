# Static Analysis Review Rules

When a Static Analysis Review is requested you MUST follow these rules:

- Select review tools to run:
  - You must look for static analysis instructions in the project and follow them if found.
  - If no instructions are found, you must check how github/gitlab pull-request workflows verify their pull requests. And choose the same tools.
  - Only if no guiding is found from rules, github or gitlb CI, you must choose the typical tools for building and analyzing this type of project.
- Execute the selected tools.
- If tools are missing on your machine, you can skip them.
- Decide REQUEST_CHANGES as soon as the first tool fails.
- Do not check the code any other way.
- If REQUEST_CHANGES, also include relevant sections of all logs of failing analysis tools in your result.
