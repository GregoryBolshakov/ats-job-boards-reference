# Changelog

What changed and when, so you can tell whether the copy you read is the current one.

Everything here is checked against the live endpoints on the date given. When something
turns out to be wrong it gets corrected in place and listed here as a correction, not
quietly edited.

## 2026-08-29

- **Correction.** Lever pay showed 0% and that was wrong. Lever publishes `salaryRange` and
  the run that made the snapshot never read it. Now trap 10, with the two traps inside it:
  `{min: 0, max: 0}` means absent rather than free, and `interval` is typed by the employer
  and is sometimes wrong.
- **Correction.** SmartRecruiters pay showed 0% and that was wrong too. It keeps
  `compensation` and `jobAd.sections` on the per advert endpoint, which the run never
  called. Now trap 9.
- Snapshot regenerated on Actor build 0.1.11 with both fixed. The two columns now read 1%
  and 13%. 5,122 adverts.
- Trap 6 gained the way out. `GET /v1/boards/{slug}/departments` rebuilds the department
  column without the ad bodies, about a ninth of the traffic. Found by
  [moonie0201](https://github.com/tonyperkins/seeker-os/issues/35#issuecomment-5460438424).
- Trap 1 measured properly instead of hand waved. Greenhouse, Lever and Ashby all 404 on an
  unknown slug and answer 200 with an empty list for a real board with nothing open.
  SmartRecruiters cannot separate the two.
- Trap 1b added. A company can answer on two systems at once during a migration. `duffel`
  returns an empty array on Lever and 11 live roles on Ashby.

## 2026-08-28

- Trap 5 added. Greenhouse pay only comes back with `pay_transparency=true`, and it is on
  47% of adverts once you ask.
- Trap 4 added. SmartRecruiters caps a response at 100 and ignores a bigger `limit`.
- Trap 6 added. `content=false` on Greenhouse silently drops `departments` and `offices`.
- First version. Four endpoints, field coverage, six traps.

## How to tell if this is stale

Every claim about an endpoint was run against that endpoint on the date in the section
above. The percentages come from one snapshot of 16 companies, so treat them as the shape
of the data and not as thresholds to validate against. Boards change daily and companies
turn pay on and off.
