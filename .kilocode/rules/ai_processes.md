# AI Process Rules

## 1. File Creation Patterns

- **When creating a new file:**  
  Always search for and review examples of the same kind of file within the existing project. Read as many as needed to identify the standard pattern
  and distinguish it from exceptional deviations. This ensures consistency and leverages established conventions.

## 1. Trouble with API

- **When running into issues with external or skeleton library APIs:**  
  Always search for and review examples of this API's usage to see how things are used in other places of the code. Read as many as needed to identify the standard pattern
  and distinguish it from exceptional deviations. This ensures consistency and leverages established conventions.

## 2. Change Reversion

- **When reverting changes:**  
  Always review the git diff against HEAD to recall exactly what was changed. This helps avoid mistakes and ensures you only revert what is necessary.

## 3. Dependency Troubleshooting

- **When a dependency appears missing:**  
  First, check if the dependency is already used by older code in the latest git version (HEAD). If it is, the problem is likely not a missing
  dependency but something else (e.g., configuration, import, or build issue).

## 4. X-Reference and identifier search

- **When a job can be done with either bifrost mcp or filesystem based queries**
  You must always prefer bifrost mcp server over file system operations

- **When analyzing architecture and project structure:**
  Remember to use the bifrost mcp service

---

These rules are intended to maintain code quality, consistency, and efficient troubleshooting across the project.