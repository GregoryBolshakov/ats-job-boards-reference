# Changelog

What changed and when, so you can tell whether the copy you read is the current one.

Everything here is checked against the live endpoints on the date given. When something
turns out to be wrong it gets corrected in place and listed here as a correction, not
quietly edited.

## 2026-09-01

- Added trap 11. Greenhouse `pay_input_ranges` is an array and reading `[0]` is wrong on
  20.1% of the adverts that declare pay. Measured across 21 boards and 2,978 adverts: 331
  carry more than one band, and on 111 of them the bands you drop are higher than the one
  you keep. The worst understates an advert by 150,000. Includes the base pay against total
  on-target earnings split, which is the pair you must not envelope together.

- Added trap 12. The period label is wrong in both directions on every board, not just on
  Lever. verkada publishes an annual band titled `Estimated Hourly Pay Range` and samsara
  publishes an hourly rate titled `Annual Base Salary`.

- **Correction.** Trap 10 said to carry Lever's `interval` across as given. That was half
  right. Never rescale the amount by it, which still holds, but carrying a label the
  numbers contradict still publishes something the company did not mean. Keep the label
  only while the amount could belong to that period. Trap 12 has the detail.

- `pay_transparency=true` works with `content=false`. Verkada is 523 KB that way against
  3.65 MB. Added to trap 5.

- Ten boards fetched twice back to back returned identical id sets, so a board that answers
  does not shuffle adverts in and out. Added after trap 12.

## 2026-08-29

- Added a second, bigger snapshot: `data/segments-2026-08-29.*`, 10,003 adverts from 69
  companies across four segments, whole boards. Pay disclosure runs 55% in AI labs and 4%
  in big tech, which is the widest split in the file.

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
