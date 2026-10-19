# Rangers historical roster source audit

Oracle source snapshot: 2026-10-07 America/New_York (fetched 2026-10-08 02:27 UTC).

## Verified coverage

`make rangers-roster-audit` fetches the official NHL statistics API, retaining every response and its URL in ignored `build/rangers-roster/`. The current snapshot contains **1,162 distinct NHL player IDs**: 1,156 regular-season players (1,063 skaters, 93 goalies), union 507 playoff players (476 skaters, 31 goalies). Six appear only in Rangers playoffs: Steve Andrascik (8444933), Buck Davies (8445849), John Hughes (8448070), Bobby Sheehan (8449004), Gordie Bell (8449816), Joe Miller (8450043).

Definition: at least one recorded Rangers NHL regular-season or playoff appearance. Exclude preseason, prospects and merely signed players. Union by numeric NHL ID, never spelling/name. A player may have both skater and goalie records; preserve both rather than creating a second sticker. Lester Patrick (8448095) demonstrates this: one regular-season skater appearance and one playoff goalie appearance. Do not add the GP totals from unlike roles blindly.

Official endpoint: `https://api.nhle.com/stats/rest/en/{skater|goalie}/summary`. Parameters: `isAggregate=true`, `isGame=false`, `cayenneExp=teamId=3 and gameTypeId={2|3}`, `factCayenneExp=gamesPlayed>=1`, `limit=100`, `start=0,100,...`, and `sort=[{"property":"playerId","direction":"ASC"}]`. Game type 2 is regular season; 3 playoffs. Require row count equals response total and distinct player IDs per report. Unsorted pagination demonstrably duplicated/skipped 14 skaters; sorting is mandatory. `factCayenneExp=teamId=3` is invalid (HTTP400); team filtering belongs in `cayenneExp`.

Team-only aggregation checked against Wayne Gretzky: NYR regular 234GP,57G,192A,249P; Henrik Lundqvist: NYR regular 887GP,459W. These are not whole-league career totals.

## Importer requirements / remaining enrichment

The four career reports supply skater GP/G/A/P and goalie GP/W/L/T/SO/SV%, saves and shots against. They do not supply first/last Rangers season. Fetch the same four queries with `isAggregate=false` and stable sort by `playerId`, then `seasonId`; reconcile their unique ID union against the audited career union. Min/max seasonId per NHL ID across both game types yields first/last actual Rangers appearance season. This enrichment is complete via `make rangers-roster-seasons`: 2,760 regular-season skater rows, 1,175 playoff skater rows, 268 regular-season goalie rows and 95 playoff goalie rows reconcile to all 1,162 audited IDs. `build/rangers-roster/seasons-audit.json` records exact first/last season IDs.

An alternative official per-player enrichment endpoint is `https://api-web.nhle.com/v1/player/{id}/landing`; its season totals must be filtered to NHL, NYR and game type2/3. Do not replace team-only stats with unfiltered careerTotals. Career API fields have historical nulls: render an em dash/unavailable, never invented zero. Preserve null ties versus zero. Do not average goalie save percentages; use official aggregate or total saves/shots when both are available. Separate postseason statistics visibly from regular-season totals. Store exact source query URLs and snapshot timestamp with the generated catalog; refresh deliberately and reconcile coverage rather than claiming a permanently fixed roster count.

NHL's [all-time playoff statistics announcement](https://www.nhl.com/news/all-time-playoff-stats-box-scores-on-nhl-com-289306906) explains historical postseason coverage. The [official Rangers history hub](https://www.nhl.com/rangers/team/history/) corroborates the roster scale of over1,000. The NHL Records roster `https://records.nhl.com/nyr/overview/roster` exists but web retrieval failed; use as optional cross-check, not sole importer.

## Rarity evidence

[Official retired numbers](https://www.nhl.com/rangers/team/history/retired-numbers), with its team-owned embedded [list](https://view.ceros.com/msg/nyr-retired-numbers): Ed Giacomin, Brian Leetch, Harry Howell, Rod Gilbert, Andy Bathgate, Adam Graves, Vic Hadfield, Mark Messier, Jean Ratelle, Henrik Lundqvist and Mike Richter. Embedded text misspells Leetch/Ratelle: use canonical API names and ID mapping. These eleven form a defensible minimum Legendary pool; honors are a declared editorial proxy for popularity, not measured universal rankings.

[Official captains](https://www.nhl.com/rangers/team/history/captains) is an additional honors signal. [Centennial Fan Favorites](https://www.nhl.com/rangers/centennial/fan-favorites) provides directly editorial popularity evidence (including Lundqvist, Graves, Callahan, Fotiu, Erixon, Dubinsky, Avery, Don Maloney, Orr, McPhee, Larouche, Granato, Domi, Langdon, Beukeboom, Prust, McCarthy and Prucha). This is not a ranked poll. [Legendary Blueshirts](https://www.nhl.com/rangers/centennial/legendary-blueshirts) offers another official recognition pool. Define and publish deterministic tiers with explicit player-ID overrides; ordinary career-stat rank alone does not equal popularity.

## Facts and humor

Prefer an original factual sentence computed from verified Rangers stats for every player (including one-game appearances). Player quotations require a specific attribution/source and should remain optional. Original humorous art captions must be labeled as original flavor, never presented as something the player said. Keep humor affectionate: oversized equipment, puck piles, theatrical poses and era details. No unsupported personal/medical/criminal claims. Do not reuse official photographs as the delivered artwork; the user requested fresh caricatures through the existing generator.

## Season-source follow-up

Compiled catalog provenance now includes four official nonaggregate season-query URLs (skater/goalie × regular/playoffs), with stable playerId/seasonId sorting and pagination start. The seasons-audit SHA256 pins the reconciled tenure output. Use `make rangers-roster-seasons` then `make rangers-catalog` to reproduce.

The artwork sample spans Steve Andrascik, Lester Patrick, Bill Cook, Wayne Gretzky, Henrik Lundqvist and Artemi Panarin. Smith owns visual approval. Historical likeness needs reliable references where available; an NHL ID alone is not a portrait reference. No sample images exist yet.
