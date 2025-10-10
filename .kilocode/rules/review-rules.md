# Rules for all reviews

**You MUST produce the following result**

- Decision: APPROVE | REQUEST_CHANGES, with a short rationale.
- If REQUEST_CHANGES, a check list of all found issues.
- If REQUEST_CHANGES, include the following information for each issue:
    - Source location (e.g., unified patch notation)
    - Citation of relevant source context
    - Clearly defined scope of what must be addressed
    - All necessary context to resolve the objection

**You MUST ignore all changes to .kilocodemodes and to all files in .kilocode.**

- Changes to .kilocodemodes and to all files in .kilocode are never out of scope.
- Changes to .kilocodemodes and to all files in .kilocode must never be reviewed.

**You must understand the logic of each change**

- If you need more context then just the changeset to understand the performed changes, you must look at whole files and at their dependencies, as
  needed.
- You must use all tools needed to understand the code and its context.

**You must not do any code changes.**

- If changes are neede you must report REQUEST_CHANGE
