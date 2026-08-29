# ATS job board reference

Four applicant tracking systems publish their job boards as open JSON. No key, no login,
no scraping. This repo is what those four endpoints actually return, measured on 5,122
live adverts from 16 companies on 2026-08-29, plus the snapshot itself so you can look at
the rows without signing up for anything.

Written while building an ingestion pipeline over these boards. Everything below was
checked against the live endpoints on the date given, not copied from documentation.

## The endpoints

| board | endpoint | returns |
|---|---|---|
| Greenhouse | `GET https://boards-api.greenhouse.io/v1/boards/{slug}/jobs?content=true&pay_transparency=true` | `{ jobs: [] }`, whole board |
| Lever | `GET https://api.lever.co/v0/postings/{slug}?mode=json` | a bare array, whole board |
| Ashby | `GET https://api.ashbyhq.com/posting-api/job-board/{slug}?includeCompensation=true` | `{ jobs: [] }`, whole board |
| SmartRecruiters | `GET https://api.smartrecruiters.com/v1/companies/{slug}/postings?limit=100&offset=0` | `{ content: [], totalFound }`, **100 at a time** |

Ashby also has a GraphQL endpoint that turns up in a lot of blog posts. You do not need
it. The REST one above is a plain GET and returns the same board.

<!-- coverage:start -->
## Which fields each board actually fills in

Percentage of adverts where the field is present and not empty. `company` is 100%
everywhere only because the pipeline fills it from the slug. See trap 2.

| field | greenhouse (2,453) | lever (1,360) | ashby (1,168) | smartrecruiters (141) |
|---|---|---|---|---|
| `company` | 100% | 100% | 100% | 100% |
| `title` | 100% | 100% | 100% | 100% |
| `location` | 100% | 93% | 100% | 100% |
| `department` | 100% | 94% | 100% | 100% |
| `employmentType` | 0% | 76% | 100% | 100% |
| `postedAt` | 100% | 100% | 100% | 100% |
| `updatedAt` | 100% | 0% | 0% | 0% |
| `applyUrl` | 100% | 100% | 100% | 100% |
| `salaryMin` | 47% | 1% | 72% | 13% |
| `salaryRaw` | 47% | 0% | 72% | 0% |

## Declared pay, per company

| board | company | adverts | with pay |
|---|---|---|---|
| lever | veeva | 887 | 0% |
| greenhouse | databricks | 857 | 55% |
| ashby | openai | 758 | 85% |
| greenhouse | stripe | 575 | 0% |
| greenhouse | anthropic | 571 | 89% |
| lever | leverdemo | 384 | 2% |
| greenhouse | gitlab | 220 | 38% |
| greenhouse | figma | 163 | 60% |
| ashby | ramp | 139 | 96% |
| smartrecruiters | Sodexo | 139 | 13% |
| ashby | notion | 133 | 0% |
| ashby | vanta | 109 | 61% |
| lever | spotify | 89 | 0% |
| greenhouse | monzo | 67 | 0% |
| ashby | linear | 29 | 0% |
| smartrecruiters | smartrecruiters | 2 | 0% |
<!-- coverage:end -->

Regenerate both tables with `python3 tools/coverage.py data/jobs-2026-08-29.json`.

**Both pay columns were wrong in the first two versions of this file and are now fixed.**
Lever's `salaryRange` was never read, and SmartRecruiters keeps pay on a second endpoint
that the run never called, so both showed 0%. They now show 1% and 13%, which are the real
numbers and are still low. Traps 9 and 10 say why.

## Ten traps

These cost real time. In rough order of how much.

### 1. An empty board and a wrong slug look identical

Three of the four boards let you tell them apart, and the fourth does not. Measured
2026-08-29:

| | unknown slug | real board, nothing open |
|---|---|---|
| Greenhouse | 404 | 200, `jobs: []` |
| Lever | 404 | 200, `[]` |
| Ashby | 404 | 200, `jobs: []` |
| SmartRecruiters | **200, `totalFound: 0`** | 200, `totalFound: 0` |

```
GET /v1/companies/nonsense-xyz-9/postings  ->  200 {"totalFound":0,"content":[]}
GET /posting-api/job-board/snyk            ->  200 {"jobs":[]}      real board, no roles
```

So on SmartRecruiters zero results never tells you which happened. On the other three a
404 means you guessed wrong and a 200 with no rows means the company is hiring nobody.

If you auto-detect the platform from a bare company name, "has adverts" is still the only
signal that works on all four, and a company with a genuinely empty board comes back as
not found. Pin the platform explicitly when you can.

### 1b. A company can answer on two systems at once

An ATS migration leaves the old board up and answering. `duffel` on 2026-08-29:

```
GET api.lever.co/v0/postings/duffel?mode=json          ->  200 []
GET api.ashbyhq.com/posting-api/job-board/duffel       ->  200 11 live roles
```

Nothing 404s. If your detection keeps the first provider that returns 200, and you try
Lever before Ashby, you get the dead board and report the company as hiring nobody. Rank
the candidates by row count instead of by who answers first.

This also breaks board retirement built on 404s. A migrated board never returns one.

### 2. Lever and Ashby never send the company name

Not under any key. The payload is about the job and assumes you already know whose board
you asked for. If you group by company, that column is null on two boards out of four
until you fill it from the slug yourself.

### 3. `updatedAt` exists on Greenhouse only

Greenhouse sends `updated_at`. The other three send nothing equivalent. Any logic built
on "changed since last run" works on a quarter of your data and silently does nothing on
the rest. Diff the rows yourself instead.

### 4. SmartRecruiters caps a response at 100

`limit` above 100 is ignored. Without paging on `offset` you lose everything past the
first hundred and the response still looks successful. Sodexo has 140 live postings and
returns 100. This one is easy to ship and not notice, because the failure produces a
plausible number rather than an error.

The other three boards return the whole board in one response, so paging them just
doubles your request count.

### 5. Greenhouse hides pay behind a query parameter

The default Greenhouse response contains no pay field at all, and it is easy to conclude
the board simply does not carry pay. It does. Add `pay_transparency=true` and jobs come
back with a `pay_input_ranges` array:

```json
"pay_input_ranges": [{
  "min_cents": 22280000, "max_cents": 29000000, "currency_type": "USD",
  "title": "Annual Salary:",
  "blurb": "<p>For sales roles, the range provided is the role's On Target Earnings ..."
}]
```

Three things about that shape.

Amounts are integer **cents**, so 22280000 is 222,800.

`title` is free text the company wrote, and it is the only clue about the period. One
sample of 488 adverts contained `Annual Salary:`, `Annual base salary range (excluding
equity and bonus):`, `The base salary range for this position is:`, `United States Salary
Range`, `Internship` and `Hourly Base Pay Range:`. Defaulting to annual would report an
hourly rate as a yearly salary, which is wrong by a factor of about two thousand and
looks perfectly plausible in a spreadsheet.

`blurb` is where a company says the range is On Target Earnings rather than base salary,
so throwing it away loses the one thing that makes the number comparable.

Coverage, once you ask for it: Anthropic 89% of adverts, Databricks 55%, Figma 60%,
GitLab 38%, Stripe 0%.

Credit for this one goes to [@moonie0201's
comment](https://github.com/tonyperkins/seeker-os/issues/35#issuecomment-5455924861) on
seeker-os, which is where I learned the parameter exists.

### 6. `content=true` on Greenhouse is not a description toggle

It looks like one, and turning it off is tempting because it is worth 9.1 MB against 715
KB on Databricks. But `content=false` also removes `departments` and `offices` from every
job in the response. Turn it off to save bandwidth and the `department` column goes null
across the entire board, with no error anywhere.

There is a way to have both, from
[moonie0201 on `tonyperkins/seeker-os` #35](https://github.com/tonyperkins/seeker-os/issues/35#issuecomment-5460438424).
Call `GET /v1/boards/{slug}/departments` alongside the bare jobs call. It returns every
department with the job ids under it, so you can rebuild the column without the ad bodies.
Measured on the wire, gzipped, 2026-08-29:

| board | bare `/jobs` | `/departments` | `/jobs?content=true` |
|---|---|---|---|
| stripe | 29.3 KB | 50.6 KB | 717.1 KB |
| anthropic | 30.6 KB | 29.7 KB | 892.1 KB |

Both calls together are about a ninth of the one call. On both boards no job id appeared
under more than one department, so the mapping is one to one and needs no tie break.

### 7. Pay coverage is a company setting, not a platform property

All three boards that carry pay leave it up to the company, so a board-level average is
useless for validation:

| board | company | with declared pay |
|---|---|---|
| ashby | ramp | 96% |
| ashby | openai | 85% |
| ashby | notion | 0% |
| ashby | linear | 0% |
| greenhouse | anthropic | 89% |
| greenhouse | stripe | 0% |
| smartrecruiters | wise | 95% |
| smartrecruiters | Sodexo | 22% |
| smartrecruiters | BoschGroup | 0% |

A rule like "Ashby rows should have a salary" fires constantly on Notion and Linear, and
both of those are correct behaviour. Zero is a real answer.

The SmartRecruiters rows are 40 adverts sampled per board, not the whole board. The other
rows are the full board.

Worth recording alongside the number whether a company declared it or you parsed it out
of prose. "The company published no pay" and "our parser missed the pay" produce the same
empty column and mean completely different things.

### 8. The obvious dedup key breaks in three places

`platform:companySlug:jobId` is the natural key and it is right most of the time. It
breaks when:

- a company closes an advert and reposts it, which mints a new `jobId` for the same role
- a board publishes one posting per location, so one role arrives as eight rows
- a company migrates ATS. A Lever to Ashby move reads as every role closing and an equal
  number opening on the same day, which will set off any alerting you built on counts

The third one is the expensive one. Treat a mass close plus a mass open on one day as a
migration until proven otherwise.

### 9. SmartRecruiters keeps pay and advert text on a second endpoint

The list response has neither. No `compensation` key, no `jobAd` key, so a pipeline that
reads only the list reports no pay for every company on that board and an empty
description for every advert. Both look like the company published nothing.

```
GET /v1/companies/wise/postings           ->  no jobAd, no compensation
GET /v1/companies/wise/postings/{id}      ->  jobAd.sections + compensation
```

`compensation` is `{min, max, currency, period}` and `period` is one of `YEARLY`,
`MONTHLY`, `HOURLY`. That makes SmartRecruiters the only board of the four that states the
period as a field rather than free text, so it is the one place the interval needs no
guessing. Compare trap 5, where Greenhouse leaves it in a free text `title` and one sample
carried both `Annual Salary:` and `Hourly Base Pay Range:`.

`jobAd.sections` has four blocks: `companyDescription`, `jobDescription`, `qualifications`
and `additionalInformation`.

The cost is one request per advert. On a 4,780 advert board like BoschGroup that is real
money and real time, so fetch details only for the rows you are keeping.

### 10. Lever does publish pay, and it is easy to get wrong twice

`salaryRange` is `{min, max, currency, interval}`. Coverage is tiny. Across 2,527 postings
on eight boards, 12 carried one, and 8 of those 12 were on `leverdemo`, Lever's own demo
board. So on a real board it is well under 1% and calling Lever a no-pay board is nearly
right, which is why it is easy to ship the wrong thing.

Two traps, both of which return a plausible number rather than an error.

A company can turn the field on and leave it at zero:

```
{"currency":"USD","interval":"per-year-salary","min":0,"max":0}
```

That is absent, not a job paying nothing. Map it straight through and you publish a
declared range of zero.

`interval` is typed by the employer and is sometimes wrong. One live advert carried
`bi-week-salary` on a 22.4 to 26 range, which is an hourly rate. Lever's own values are
`per-year-salary`, `per-month-salary`, `bi-week-salary`, `per-week-salary`, `per-day-wage`
and `per-hour-wage`. Carry the label across, and never use it to rescale the amount. A
wrong label stays a wrong label. A rescale turns it into a wrong number.

There is also `salaryDescription` and `salaryDescriptionPlain`, free text, which is where a
company says the range is base only.

## The snapshot

`data/jobs-2026-08-29.csv` and `.json`, 5,122 adverts, 16 companies, all four boards.
`data/input.json` is the exact input that produced it.

Columns: `platform`, `companySlug`, `company`, `jobId`, `title`, `location`,
`department`, `employmentType`, `isRemote`, `postedAt`, `updatedAt`, `applyUrl`,
`salaryMin`, `salaryMax`, `salaryCurrency`, `salaryInterval`, `salarySource`,
`salaryRaw`.

One flat shape for all four boards, so nothing downstream has to branch on which system a
row came from. Descriptions are left out to keep the file readable in a browser.

This is a snapshot with a date on it, not a feed. Job boards change daily. Use it to see
the shape of the data and to test a parser, then read the boards yourself.

## Reproducing it

Every endpoint above is public, so you can do all of this with `curl` and a normalisation
layer. That layer is the part that takes the time, and the ten traps are what it costs.

The snapshot came from an Apify Actor that already does the normalising:
[ATS Jobs Scraper](https://apify.com/gubidonius/company-jobs-scraper). The
run that produced this file cost $0.028 for 5,122 adverts, on build 0.1.11. The
SmartRecruiters rows take one extra request each, so that board is the slow one. It is mine and it is paid, at $0.0005 per advert with no monthly fee. Apify's free
tier covers a run this size many times over.

Traps 4, 5, 6, 9 and 10 were all found while measuring for this repo, and every one of
them was a bug in that Actor before it was an entry in this list. Each returned a run that
succeeded with a wrong number in it, which is the only failure shape worth being afraid of
here. All five are fixed as of build 0.1.11. Trap 6's `/departments` route came from
moonie0201, who found it the same way.

## Licence

MIT for the code. The job data is published by the companies themselves on their own
public boards and is included here as a dated sample.
