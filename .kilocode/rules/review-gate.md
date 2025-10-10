# Code Review Gate: Mandatory Workflow for All Code Changes

This rule describes the mandatory workflow required when asked to do any code changes. It is mandatory and applies to **all code changes without
exception**.

## 1. Branching Before Any Code Change

- **Before making any change**, create a new git branch from the current branch.
- The branch name **must** start with `kilocode/`. If the name is already taken, choose a new unique name starting with `kilocode/`.

## 2. Task Breakdown

- Break down the main task into the smallest reasonable, self-consistent batches.
- Each batch should be as minimal as possible while remaining logically complete.

## 3. Review Process

For each batch that modifies any files do the following steps.

1. **Execute all of the following reviews in order:**
    1. Scope Review
    2. Architecture & Tech Review
    3. General Quality Review
    4. Static Analysis Review

2. **For each review**
    - Find the changeset under review by running `git diff HEAD` or use equivalent MCP if available.
    - Consider which task lead to the changeset.

3. **If any reviewers' result is REQUEST_CHANGE:**
    - Immediately address all objections.
    - All reviews must be fully executed again after the objections are addressed.

4. **If all reviewers' result is APPROVE:**
    - Commit your changes.

## 4. Final Review After All Subtasks

- After all subtasks are complete, run all reviewer subtasks again.
- This time, consider the overarching **main task** as context for each review.
- Only after all final reviews are approved is the task considered complete.

## 5. Completion Checklist

- **Before using attempt_completion, confirm that each reviews has been executed and approved for the current changeset.**

## 6. Enforcement

- **This process is mandatory for all code changes.**
- No code change may bypass this workflow for any reason.
- Each review, including identification of the changeset under review (git diff) must be executed within s a separate, isolated task. Use the new_task
  tool for each review.
- The exact wording of the relevant subtask or main task, must be considered in your reviews.
