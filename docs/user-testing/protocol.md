# User-testing protocol

Five sessions that use nanopnp as a nanopore modeller would, before anyone else relies on it. The
author runs them (§8.2.6 F3), one sitting each, and logs every surprise in
[findings.md](findings.md). A session states a task and what the physics says should happen; it never
gives a number, and it never names a weakness for the tester to look for.

## Setup

Install the program as the [getting-started page](../getting-started.md) says a user does, from the
repository at a release tag into a fresh environment, not from a development checkout. Installing is
part of what a user meets, so a stumble here is a finding (area `install`).

1. Make a fresh virtual environment and activate it.
2. Install the release with the `notebook` extra, which session 04 needs:

   ```bash
   pip install "nanopnp[notebook] @ git+https://github.com/willemsk/nanopnp@<tag>"
   ```

   `<tag>` is the release the author names for the round: `v0.5.0-alpha.21`, the first to carry
   these pages, or a later one.
3. Check it: `nanopnp --env` prints the version, the interpreter and where the data and the store are.
4. Clone the repository at the same tag, for the session files only:

   ```bash
   git clone --branch <tag> https://github.com/willemsk/nanopnp
   ```

5. Copy one session's directory, `nanopnp/docs/user-testing/sessions/NN-<slug>/`, to a working
   directory outside the clone, and work there. Every command runs in that directory, without
   `uv run`. A session directory is self-contained: nothing in it names a path outside itself.

## Order

Run the sessions in order, 01 to 05, one sitting each. Each is meant to take twenty to forty minutes;
stop at forty and log where you were.

| Session | Area | Task |
|---|---|---|
| [01-command-line](sessions/01-command-line/README.md) | `cli` | A case file to a reproduced current |
| [02-physics](sessions/02-physics/README.md) | `physics` | The model's corrections and the salt |
| [03-numerics](sessions/03-numerics/README.md) | `numerics` | Mesh refinement, and a refused mesh |
| [04-python-api](sessions/04-python-api/README.md) | `api` | The Python interface in a notebook, with a step of one's own |
| [05-sweep](sessions/05-sweep/README.md) | `cli` | A sweep over voltage and salt |

## Each session

A session README has the same sections, in this order:

- **The task**, as a modeller would set it;
- **You start with**, the files in the directory;
- **Steps**, the commands, and what each does;
- **What to expect**, a property of the model that the physics gives, never a number. If what you see
  disagrees, that is a finding whether or not you can say why;
- **Then try**, one variation you make without a script;
- **Record**, a reminder to log what you met.

The commands of the **Steps** block are the ones a nightly test runs, so they work as written on the
tagged release. If one fails, that is a finding.

## Recording

Open [findings.md](findings.md) at the start. Add a row for each surprise as it happens, not at the
end: a wrong or unusable result, a step that needed knowledge the documentation does not give, or
friction. Give it an area and a severity by the legend there. Paste the command and its output in the
row's own section, below the table, so the finding can be reproduced. A row's status is `open`; the
author rules it at the second amendment of Phase 4 (§8.2.7 G7).

## Dry runs

An agent may run a session to debug it, and records nothing: only the author's own surprises are
findings (§8.2.7 G7). A failure in a session's script is fixed in the script. A failure in the
program is a review-findings row, and the session is not rewritten to step around it.
