# Stricter Evidence reading — sensitivity results

Pre-specified in scorer/PRESPEC-E-strict-sensitivity-10Nov2026.md. Primary instrument: frozen V4. Tier shares: unsubstantiated / partially / substantiated (%).

## Corpus

- Claims with V4 Evidence = 2: 1,542 of 6,320 (24.4%). Under the stricter reading 228 of them (14.8%) fall below 2 (228 to 1, 0 to 0); that is 3.6% of all claims.
- Placebo (exploratory, not pre-specified): re-scoring a random 300 of the E = 2 claims with the unchanged V4 prompt moved 6.3% below 2 by run-to-run variation alone. Net of that, the stricter reading lowers roughly 8% of E = 2 claims.
- Mean Evidence: 1.22 → 1.19. Mean SMTE: 1.116 → 1.107.
- SMTE tiers: V4 37.5 / 53.1 / 9.4; stricter reading 38.2 / 52.6 / 9.2. Claims that change tier: 49 (0.8%).

Firm–goal rules, declared cells:

| reading    |   declared cells (≥3 claims) |   Rule A: mean ≥ 2.0 |   Rule B: ≥ 1 substantiated claim |   Rule B robust: ≥ 3 |
|:-----------|-----------------------------:|---------------------:|----------------------------------:|---------------------:|
| V4         |                          125 |                    0 |                               100 |                   69 |
| stricter E |                          125 |                    0 |                               100 |                   69 |

By claim type (claims with V4 E = 2):

| claim_type   |   E = 2 claims |   lowered % |
|:-------------|---------------:|------------:|
| commitment   |          699.0 |        14.2 |
| achievement  |          259.0 |        12.7 |
| metric       |          231.0 |         8.2 |
| policy       |          223.0 |        14.8 |
| alignment    |          112.0 |        39.3 |
| target       |           13.0 |         0.0 |

## Round 1 held-out claims (rater agreement on Evidence under both readings)

V4 Evidence = 2 on 18 of 60 claims; the stricter reading lowers 3 of them.

| rater   |   mean rater E |   κ vs V4 E |   κ vs stricter E |   mean V4 E |   mean stricter E |
|:--------|---------------:|------------:|------------------:|------------:|------------------:|
| Rater A |           1.02 |        0.49 |              0.49 |        1.40 |              1.35 |
| Rater B   |           1.67 |        0.47 |              0.43 |        1.40 |              1.35 |
| Rater C    |           1.68 |        0.17 |              0.14 |        1.40 |              1.35 |
| Rater D   |           1.25 |        0.29 |              0.21 |        1.40 |              1.35 |