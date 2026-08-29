# ATS job board reference

Four applicant tracking systems publish their job boards as open JSON. No key, no login,
no scraping. This repo is what those four endpoints actually return, measured on 5,118
live adverts from 16 companies on 2026-08-29, plus the snapshot itself so you can look at
the rows without signing up for anything.

Written while building an ingestion pipeline over these boards. Everything below was
checked against the live endpoints on the date given, not copied from documentation.

## The endpoints

| board | endpoint | returns |
|---|---|---|
| Greenhouse | `GET https://boards-api.greenhouse.io/v1/boards/{slug}/jobs?content=true` | `{ jobs: [] }`, whole board |
| Lever | `GET https://api.lever.co/v0/postings/{slug}?mode=json` | a bare array, whole board |
| Ashby | `GET https://api.ashbyhq.com/posting-api/job-board/{slug}?includeCompensation=true` | `{ jobs: [] }`, whole board |
| SmartRecruiters | `GET https://api.smartrecruiters.com/v1/companies/{slug}/postings?limit=100&offset=0` | `{ content: [], totalFound }`, **100 at a time** |

Ashby also has a GraphQL endpoint that turns up in a lot of blog posts. You do not need
it. The REST one above is a plain GET and returns the same board.

<!-- coverage:start -->
## Which fields each board actually fills in

Percentage of adverts where the field is present and not empty. 5,118 adverts.

| field | greenhouse (2,448) | lever (1,360) | ashby (1,168) | smartrecruiters (142) |
|---|---|---|---|---|
| `company` | 100% | 100% | 100% | 100% |
| `title` | 100% | 100% | 100% | 100% |
| `location` | 100% | 93% | 100% | 100% |
| `department` | 100% | 94% | 100% | 100% |
| `employmentType` | 0% | 76% | 100% | 100% |
| `postedAt` | 100% | 100% | 100% | 100% |
| `updatedAt` | 100% | 0% | 0% | 0% |
| `applyUrl` | 100% | 100% | 100% | 100% |
| `salaryMin` | 0% | 0% | 72% | 0% |
| `salaryRaw` | 0% | 0% | 72% | 0% |

`company` is 100% everywhere in this table only because the pipeline fills it from the
slug. See trap 2.

## Declared pay, per company

| board | company | adverts | with pay |
|---|---|---|---|
| lever | veeva | 887 | 0% |
| greenhouse | databricks | 855 | 0% |
| ashby | openai | 759 | 85% |
| greenhouse | stripe | 573 | 0% |
| greenhouse | anthropic | 570 | 0% |
| lever | leverdemo | 384 | 0% |
| greenhouse | gitlab | 220 | 0% |
| greenhouse | figma | 163 | 0% |
| smartrecruiters | Sodexo | 140 | 0% |
| ashby | ramp | 138 | 96% |
| ashby | notion | 133 | 0% |
| ashby | vanta | 109 | 61% |
| lever | spotify | 89 | 0% |
| greenhouse | monzo | 67 | 0% |
| ashby | linear | 29 | 0% |
| smartrecruiters | smartrecruiters | 2 | 0% |
<!-- coverage:end -->

Regenerate both tables with `python3 tools/coverage.py data/jobs-2026-08-29.json`.

## Six traps

These cost real time. In rough order of how much.

### 1. An empty board and a wrong slug look identical

SmartRecruiters answers HTTP 200 with `totalFound: 0` for a company name that does not
exist at all:

```
GET /v1/companies/nonsense-xyz-9/postings  ->  200 {"totalFound":0,"content":[]}
```

So zero results never tells you which of two things happened. The company is on the
board and hiring nobody, or you guessed the wrong system. Greenhouse and Lever return
404 for an unknown slug, which is much easier to handle. Ashby sits in between.

If you auto-detect the platform from a bare company name, "has adverts" is the only
signal you get, and a company with a genuinely empty board will be reported as not found.
Pin the platform explicitly when you can.

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

### 5. Pay is an Ashby feature, and then a per company choice

Only Ashby publishes pay as numbers, and only when the company filled it in. Across
1,168 Ashby adverts, 72% carry a number. Split by company that average is meaningless:
Ramp 96%, OpenAI 85%, Vanta 61%, Notion and Linear 0%.

Two things worth doing. Keep the board's own summary string next to the parsed numbers,
because Ashby's `compensationTierSummary` often holds bonus and equity that do not belong
in a salary range. And record whether a number was declared by the company or parsed out
of prose by you, so downstream nobody has to guess. "The company did not publish pay" and
"our parser missed it" are different facts and they look the same in an empty column.

### 6. The obvious dedup key breaks in three places

`platform:companySlug:jobId` is the natural key and it is right most of the time. It
breaks when:

- a company closes an advert and reposts it, which mints a new `jobId` for the same role
- a board publishes one posting per location, so one role arrives as eight rows
- a company migrates ATS. A Lever to Ashby move reads as every role closing and an equal
  number opening on the same day, which will set off any alerting you built on counts

The third one is the expensive one. Treat a mass close plus a mass open on one day as a
migration until proven otherwise.

## The snapshot

`data/jobs-2026-08-29.csv` and `.json`, 5,118 adverts, 16 companies, all four boards.
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
layer. That layer is the part that takes the time, and the six traps are what it costs.

The snapshot came from an Apify Actor that already does the normalising:
[ATS Jobs Scraper](https://apify.com/gubidonius/company-jobs-scraper). The
run that produced this file took 17 seconds and cost $0.026 for 5,118 adverts, on build
0.1.8. It is mine and it is paid, at $0.0005 per advert with no monthly fee. Apify's free
tier covers a run this size many times over.

The paging bug in trap 4 was found while generating this snapshot and fixed in 0.1.8.

## Licence

MIT for the code. The job data is published by the companies themselves on their own
public boards and is included here as a dated sample.
