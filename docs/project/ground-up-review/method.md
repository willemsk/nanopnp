# Ground-up review: how it was made

The record of the review's method: the author's interview, each blind designer's brief, model and list of calls, and
the main session's own list of calls. An appendix of [the ground-up review](../ground-up-review.md).

## The author's view

The interview of 24 November 2026. Each round is kept as it was asked and answered: the question, the suggestions
offered with it, the suggestions the author ticked, and the author's own words, unedited. A suggestion was an
option the question named as such; it carried no recommendation.

### Round 1

**Question 1.** Three years from now, what has nanopnp become, and for whom?

Suggestions offered:

- *A lab's everyday tool.* An experimental nanopore laboratory simulates its own pore before or after a measurement,
  without a modeller in the room.
- *A method developer's base.* A research code that other groups extend with new physics, corrections and pores,
  and publish with.
- *The open reference.* The trusted open implementation of the paper's model, the one other results are checked
  against.
- *A pore design tool.* Someone designs or mutates a pore and sees what it does to current, selectivity and flow
  before making it.

Ticked: a method developer's base; a lab's everyday tool; a pore design tool.

The author's words:

> A modelling and design tool that interfaces between the molecular and microscale (continuum) worlds, in a
> bidirectional way. On the long term it should feature seamless multiscale modelling (MD, continuum, BD, ...) and
> inverse design (user defines the features needed, tool then proposes mutations or new designs).  I also see it go
> beyond nanopores, to a general modelling that that seemingly interfaces the solid-state electronics and
> (bio)molecular "worlds". Full 3D capability.

**Question 2.** If you started nanopnp over today, with what you know now, what would you not build again, or build
differently, and why?

Suggestions offered:

- *The order of the work.* Too much was built before the core was proven against the paper; you would prove the
  physics first.
- *The graphical workbench.* You would build less of it, build it later, or build it another way.
- *The process and its records.* The specification, the rulings and the plans weigh more than they return.
- *The technical base.* A different language, simulation engine, mesh tool or way to ship it.

Ticked: the process and its records; the order of the work.

The author's words:

> The focus would be less on being a perfect OSS implementation of the paper guideline with perfect number
> reproducibility, and more on building an extensible, modular platform. The use of agentic coding does make these
> kind of rescopings feasible though, so the organic nature of the process is insightful. For the physics proof: the
> baseline should be proven to hold against limiting cases with analytical solutions.

**Question 3.** What must a start-over not lose: what does today's program have, or promise, that you would insist
on again?

Suggestions offered:

- *Results you can rebuild.* Every result can be reproduced from its case file and its record of the run.
- *Faith to the paper.* The model as published, each term checked against an analytic answer before anything is
  compared.
- *An easy install.* One command on Windows, macOS and Linux, with no compiler and no paid licence.
- *Open and extensible.* A free licence, and a structure another group can read and extend.

Ticked: open and extensible.

The author's words:

> The current scope of features of the program. I find this one difficult to answer.

### Round 2

**Question 1.** You described a tool far wider than today's: multiscale (MD, continuum, BD), inverse design, beyond
nanopores, full 3D. Of all that, what must exist and work three years from now, and what is the long term that a
start-over only has to leave room for?

Suggestions offered:

- *Nanopores done well.* In three years the nanopore continuum tool is complete and trusted; multiscale, inverse
  design and 3D are prepared for but not built.
- *Full 3D by then.* Three-dimensional pores and off-axis analytes work in three years; the other extensions come
  after.
- *The molecular link.* In three years it already exchanges with molecular simulation in both directions; more
  features come after.
- *Inverse design.* In three years you state the behaviour you want and it proposes mutations or designs.

Ticked: all four. The author added no words.

**Question 2.** You ticked three users: the method developer, the experimental lab, the pore designer. When they
want different things, who comes first, second and third? And what must each be able to do with the tool?

Suggestions offered:

- *Method developer.* If the platform is extensible and modular, the other two can be served on top of it.
- *The laboratory.* A tool only a modeller can use has failed, whatever it can compute.
- *The pore designer.* Design is the reason the tool exists; the rest is means.
- *Your own research.* First a tool for your own work; others are served when that works.

Ticked: your own research. The author added no words.

**Question 3.** You ticked "the process and its records" as something you would do differently, without saying
which part. What of the way nanopnp is developed (the specification, the rulings you make, the plans, the reviews,
the registers) would you drop, and what would you keep?

Suggestions offered:

- *Fewer written rules.* The tests and the code are the record; most of the specification and its rulings go.
- *Lighter steps.* Keep the specification, but plan and review less for each change.
- *Fewer calls on you.* The agents decide more themselves; you rule on direction only.
- *Same form, less time.* The form is right; it must only cost less of your time and fewer sessions.

Ticked: same form, less time. The author added no words.

### Round 3

**Question 1.** Last round you ticked suggestions and added no words, so each is asked why; the designers need your
reasons. You ticked all four horizons: nanopores done well, full 3D, the molecular link and inverse design, all
within three years. If time allows only one or two of them, which come first, and why those?

Suggestions offered:

- *3D first.* Without three dimensions the tool cannot treat the pores and analytes that matter to you.
- *Molecular link first.* The exchange with molecular simulation is what no other tool offers.
- *Inverse design first.* Proposing designs is the use that justifies everything else.
- *The base first.* A complete, trusted nanopore tool comes first; the three others follow in whatever order proves
  easiest.

Ticked: the base first. The author added no words.

**Question 2.** You put your own research first among the users. What is that research in the next three years:
what will you yourself need to compute, design or publish with the tool that you cannot do today? And after you, in
what order come the method developer, the laboratory and the pore designer?

Suggestions offered:

- *Pore design studies.* You design and compare pore variants yourself, then others reuse the route.
- *Method papers.* You develop and publish new models and couplings on it; you are the first method developer.
- *With experimentalists.* You model the pores that partner laboratories measure, and they take over the tool later.
- *Devices beyond pores.* You model the interface between solid-state electronics and biomolecules, with nanopores
  as one case.

Ticked: none. The author's words:

> 2, then 4

That is the second suggestion, method papers, then the fourth, devices beyond pores.

**Question 3.** You said the form of the process is right and it must cost less of your time and fewer sessions.
Where does it cost you too much today, and what would "less" look like: how often should you have to act, and on
what kind of question?

Suggestions offered:

- *Fewer rulings.* You are asked too many questions that the agents could settle from what you already said.
- *Less to read.* The plans, reports and pages you must read to decide are too long or too many.
- *Fewer sessions to start.* Each package needs too many separate commands and sessions from you.
- *Less waiting.* Too much calendar time passes between a decision and working code.

Ticked: fewer sessions to start. The author added no words.

### Round 4

**Question 1.** You put the base first: a complete, trusted nanopore tool before 3D, the molecular link and inverse
design. Why the base before the others, and how would you see that it has succeeded: what would you, or someone
else, be able to point at in three years?

Suggestions offered:

- *Papers built on it.* You, and then other groups, publish results and new methods computed with it.
- *Others extend it.* Someone outside adds a model or a pore without your help.
- *It matches the limits.* Every part of the model holds against its analytic limiting cases, and that is shown
  openly.
- *Labs use it unaided.* Experimental groups run their own pores with it and trust what it says.

Ticked: it matches the limits; papers built on it; others extend it.

The author's words:

> We refined the existing ePNP-NS model to a form based on first principles.

**Question 2.** After your own research (method papers, then devices beyond pores), three other users remain:
another group's method developer, the experimental laboratory, the pore designer. In what order do they come, and
what is the one thing each must be able to do?

Suggestions offered:

- *Developer, designer, lab.* Other method developers first, then the people who design pores, then the
  experimental laboratories.
- *Developer, lab, designer.* Other method developers first, then the laboratories, then the designers.
- *Designer, developer, lab.* Pore designers first, then other method developers, then the laboratories.
- *Lab, designer, developer.* The laboratories first, then the designers, then other method developers.

Ticked: developer, lab, designer. The author added no words.

**Question 3.** What must the tool never become? Name what would make you call it a failure even if it computed
correctly.

Suggestions offered:

- *A closed black box.* Results no one can trace, or a core that needs a paid licence or a closed part.
- *A one-paper code.* A faithful copy of one paper that cannot grow beyond it.
- *An experts-only code.* Something only you, or only a trained modeller, can install and run.
- *A framework for all.* So general that it does nothing well, nanopores included.

Ticked: a closed black box; a one-paper code; an experts-only code. The author added no words.

### Round 5

**Question 1.** You named as a success: "We refined the existing ePNP-NS model to a form based on first
principles." What does that ask of the tool? Today the paper's model, with its fitted correction functions, is
taken as given. Should a start-over treat the model itself as something you will replace, term by term, and what
would "first principles" replace?

Suggestions offered:

- *Swap the corrections.* The fitted correction functions give way to forms derived from theory or from molecular
  simulation; the equations stay.
- *Change the equations.* The governing equations themselves will be extended or replaced; no term is fixed.
- *Compare models.* The paper's model and its refinements run side by side on the same pore, so a paper can show
  the difference.
- *Paper's model as baseline.* The published model stays as the proven starting point; refinement is your research
  on top, not the tool's job.

Ticked: swap the corrections; change the equations; compare models.

The author's words:

> The tool allows for rapid implementation, testing, and comparison of new physics.

**Question 2.** What is fixed from outside, whatever a start-over would prefer? Think of the licence, the computers
it must run on, how it is installed, money, and the time you yourself can give it each week.

Suggestions offered:

- *Free and open throughout.* No part may need a paid licence, and the whole may be used and changed by anyone.
- *Any ordinary computer.* It installs with one command on Windows, macOS and Linux, on a laptop, with no compiler.
- *Clusters allowed.* The heavy work may need a workstation or a cluster; only the simple cases must run on a
  laptop.
- *Your time is the limit.* You are the only maintainer and can give it a few hours a week; the agents do the rest.

Ticked: clusters allowed; your time is the limit; any ordinary computer; free and open throughout. The author added
no words.

**Question 3.** When two goals pull apart, which wins? Name the conflicts you expect and your choice in each.

Suggestions offered:

- *Extensible over exact.* A platform that can grow wins over reproducing the paper's numbers to the last digit.
- *Proven over new.* A new capability waits until what exists holds against its analytic limits.
- *Developer over ease.* When power for the method developer and simplicity for the laboratory conflict, the
  developer wins.
- *Your research over users.* When your own research needs and other users' needs conflict, your research wins.

Ticked: extensible over exact; developer over ease.

The author's words:

> Another important goal is GUI architecture and design, which I have no experience with myself, but it's ease of
> use, power, and clean design will both attract users and keep them.

### The summary, and its close

The closing question carried this summary, here set out by its labels with no word changed.

> **What it becomes:** a modelling and design tool between the molecular and continuum worlds, both directions. In
> three years: first a complete, trusted nanopore tool; then full 3D, exchange with molecular simulation, and inverse
> design (you state features, it proposes mutations or designs). Long term: seamless multiscale (MD, continuum, BD)
> and, beyond nanopores, the interface of solid-state electronics and biomolecules.
>
> **For whom, in order:** your own research (method papers, then devices beyond pores); other groups' method
> developers; experimental labs; pore designers. The developer can implement, test and compare new physics rapidly:
> swap corrections, change equations, run models side by side.
>
> **Differently:** less a perfect copy of the paper with exact numbers, more an extensible modular platform; baseline
> physics proven against analytic limiting cases; same process form, fewer sessions started by you.
>
> **Not to lose:** openness, extensibility, today's feature scope.
>
> **Success:** every part holds against its analytic limits; papers built on it; others extend it without you;
> ePNP-NS refined to a first-principles form.
>
> **Never:** a closed black box, a one-paper code, an experts-only code.
>
> **Fixed:** free and open throughout; simple cases on any ordinary computer, heavy work may need a cluster; you are
> the only maintainer and your time is the limit.
>
> **Which wins:** extensible over exact; developer's power over the lab's ease; the graphical interface is a goal of
> its own (ease, power, clean design attract and keep users).
>
> **My readings:** you named no hours a week and no single task for the lab or the designer, so the designers decide
> those.

Asked "Is this summary of your picture complete?", with the options *Complete*, *Complete, with corrections* and
*Not complete, ask more*, the author answered: **Complete.** The interview ended there, after five rounds.
