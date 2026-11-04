# Code review 032: WP5.07, variables and the rebuild forecast

Reviewed head `08857cd567e0b74b1de8990c33e568687ce10db7` against base `eec9a7099f680a22911c7342f8f6cca68dea9860`
(PR 159). Status: completed. Static review at `xhigh` with `--max-findings all`. Twelve findings; eight fixed,
four recorded. The review also noted that the case JSON Schema omits `variables:` (recorded with REV-201).

| # | Where | Finding | Outcome |
|---|---|---|---|
| 1 | `io/models.py` | `VariableRecord.written` could not descend into list entries, so an expression at `electrolyte.species.N.z` or `charge.edits.N.*` was dropped from the written case and never re-resolved. | Fixed: it walks list entries; the edit test checks `species`. |
| 2 | `io/models.py` | `study_layer` dropped an expression at a model-owned field whose value equalled the model's. | Fixed: such a field stays in the study layer. |
| 3 | `io/case_paths.py` | `_revalidated` (`with_section`, `with_profile`) lost the variable record. | Fixed: `VariableRecord.following` re-attaches it, keeping the expressions whose field the edit left alone. |
| 4 | `io/variables.py` | `exp` and `log` of an exact number beyond a float raised a raw `OverflowError`. | Fixed: `exp` is refused as a validation error; `log` is taken from numerator and denominator. |
| 5 | `sweep/plan.py` | An axis over a variable no field reads ran N identical members without a word. | Fixed: a plan warning; §5.3.4 states it. |
| 6 | `sweep/plan.py` | `base_case()` passes on equal resolved numbers though the plan read the variables as written. | Recorded, REV-198. |
| 7 | `sweep/forecast.py` | The forecast resolves every point again. | Recorded, REV-199. |
| 8 | `io/models.py` | `VariableRecord` repeats `Resolution`. | Recorded, REV-200. |
| 9 | `io/variables.py` | `inf` and `nan` read as numerals, so a variable of that name never resolved. | Fixed: a numeral needs a digit. |
| 10 | several | Identifiers in prose; docstrings on private code and tests. | Fixed. |
| 11 | `sweep/forecast.py` | `Forecast.summary` named the plan file, which never receives it. | Fixed. |
| 12 | `cli/__init__.py` | `sweep plan --json` drops the reason a forecast failed. | Recorded, REV-201. |

Checked on the fixes: `ruff check`, `ruff format`, `mypy src/`, and the Tier 1 files they touch. `gate.sh run` follows
in `/np-ship`.
