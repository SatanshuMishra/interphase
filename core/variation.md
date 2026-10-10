# Varying behaviour

These rules apply to every spec on every pathway. Some behaviour gives a different result each run, so one passing example proves nothing about it.

## Kinds

Three kinds of behaviour vary from run to run. Mark every behaviour the request touches that is one of these, without waiting for the user to mention it.

| Kind | What varies | Signals |
|---|---|---|
| open-ended input | speech, free text, gestures | a speech or text-parsing API in the code; a request to understand what people say or type |
| varying output | model calls, sampling | a language-model or machine-learning API; a prompt; a temperature |
| results measured on a device | frame rate, timing, touch input | a performance target; a defect seen only on hardware |

## Specify a population

Specify each varying behaviour as a population, never as one example.

- List the ways its input varies, such as phrasing, speaker, accent, noise, pacing and document state.
- Spread the cases across those ways.
- Draft a held-out set during the interview: cases nothing is ever tuned on.
- Show the user a sample of at least one held-out case for each way the input varies, and get approval.
- Carry the held-out cases in full in the task of the Step that tests them, the way a bug's draft test is carried.

The spec's Variation section lists each varying behaviour, its kind, the ways it varies, the held-out set and the pass rule. When nothing varies, it reads `Not applicable: <reason>`.

## Grade and pass

- Grade the outcome, such as the document's final state, never the exact output text.
- Run each case more than once.
- Pass on a stated pass rate.
- Allow a harmful class of failure, such as editing the wrong passage, zero times.

## Keep the acceptance set untouched

No Step tunes a prompt, rule or threshold against the cases that accept it. The builder writes its own development cases for tuning. Add a leak test that fails when any held-out case appears in a prompt or rule.

## Bugs

Reproduce a bug in varying behaviour as its class. Generate variants of the failing case along each way its input varies, run them, and record the failure rate. Accept the fix by its pass rate on held-out variants, never by the reported example alone.

## Measured on a device

- Measure repeatedly. State the statistic, such as the median or the 95th percentile, and the number of runs.
- When the builder cannot run the device, mark the criterion unproven and give the owner the measurement method.
- List a finding that depends on how input was delivered, such as a double click, a drag, an edge swipe or a long press, for the owner's hand check. Never report it as a defect.

## In the record

Mark each varying criterion with `varies` set to `input`, `output` or `measured`. Give each of its tests `cases`, `runs` (at least 2) and `pass_rate`. `check_record.py` reports an error otherwise, and the render script writes them as a Population line.
