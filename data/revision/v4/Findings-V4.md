# Findings on the frozen-V4 corpus scores

30 reports, 6,325 claims; 6,320 with a complete score (5 missing, see scorer/CORPUS-V4-RUN.md). Tier shares are given as unsubstantiated / partially / substantiated (%). Headline composite: SMTE (pre-registered rule; raters' α for C < 0.667).

## 1. Overall

| dimension   |   mean |   sd |   % at 0 |   % at 1 |   % at 2 |   % at 3 |
|:------------|-------:|-----:|---------:|---------:|---------:|---------:|
| S           |   1.56 | 0.71 |     1.19 |    53.28 |    34.00 |    11.53 |
| M           |   0.85 | 0.99 |    51.99 |    17.03 |    25.35 |     5.63 |
| T           |   0.84 | 0.89 |    44.89 |    30.87 |    19.79 |     4.45 |
| E           |   1.22 | 0.69 |    10.87 |    60.38 |    24.40 |     4.35 |
| C           |   0.49 | 0.61 |    56.27 |    38.34 |     5.17 |     0.22 |

Mean SMTE 1.12 (sd 0.52); mean SMTEC 0.99.

Tiers: SMTE 37.5 / 53.1 / 9.4; SMTEC 45.3 / 51.7 / 3.0.

## 2. Sensitivity of the tiers (R3.7)

| rule                                          | unsub / partial / sub (%)   |
|:----------------------------------------------|:----------------------------|
| SMTE, cut-points 1.0 / 2.0 (headline)         | 37.5 / 53.1 / 9.4           |
| SMTEC, 1.0 / 2.0                              | 45.3 / 51.7 / 3.0           |
| SMTE, cut-points 1.1 / 2.1 (next step up)     | 54.7 / 41.8 / 3.5           |
| SMTE, cut-points 0.75 / 1.75 (next step down) | 19.4 / 62.1 / 18.5          |
| E counted twice: (S+M+T+2E)/5                 | 33.5 / 59.9 / 6.6           |
| Non-compensatory: min(S, M, T, E)             | 70.5 / 27.1 / 2.4           |
| Non-compensatory on evidence: min(SMTE, E)    | 40.6 / 55.2 / 4.3           |
| SMTE tertiles (0.75, 1.25)                    | —                           |

Compensation: of the 591 claims that reach the substantiated tier on SMTE, 54.5% have E ≤ 1 and 0.8% have E = 0; 45.5% have E ≥ 2.

## 3. Relations between dimensions (Spearman)

|    |    S |     M |    T |     E |     C |
|:---|-----:|------:|-----:|------:|------:|
| S  | 1    |  0.18 | 0.39 |  0.17 |  0.18 |
| M  | 0.18 |  1    | 0.4  | -0.09 | -0    |
| T  | 0.39 |  0.4  | 1    |  0.07 |  0.07 |
| E  | 0.17 | -0.09 | 0.07 |  1    |  0.49 |
| C  | 0.18 | -0    | 0.07 |  0.49 |  1    |

## 4. V4 against the earlier V7 scores (development history)

| dimension   |   mean V7 |   mean V4 |   same score % |   Spearman |
|:------------|----------:|----------:|---------------:|-----------:|
| S           |      1.71 |      1.56 |          62.71 |       0.59 |
| M           |      0.71 |      0.85 |          76.25 |       0.80 |
| T           |      0.95 |      0.84 |          73.09 |       0.75 |
| E           |      1.16 |      1.22 |          64.57 |       0.40 |
| C           |      2.63 |      0.49 |           5.57 |       0.18 |

SMTE tiers: V7 43.7 / 43.1 / 13.1; V4 37.5 / 53.1 / 9.4. Same SMTE tier under both: 76.6%. C = 3: V7 81.6%, V4 0.2%.

## 5. Claim type (R3.6)

| ct          |    n |    S |    M |    T |    E |    C |   SMTE |   % substantiated (SMTE) |   % unsubstantiated (SMTE) |
|:------------|-----:|-----:|-----:|-----:|-----:|-----:|-------:|-------------------------:|---------------------------:|
| commitment  | 2963 | 1.44 | 0.55 | 0.61 | 1.15 | 0.47 |   0.94 |                     5.67 |                      53.39 |
| achievement | 1258 | 1.87 | 1.00 | 1.28 | 1.34 | 0.56 |   1.37 |                    15.26 |                      15.02 |
| metric      | 1018 | 1.59 | 2.01 | 1.29 | 1.17 | 0.47 |   1.52 |                    19.06 |                       4.32 |
| policy      |  667 | 1.50 | 0.16 | 0.44 | 1.29 | 0.49 |   0.85 |                     0.30 |                      56.37 |
| alignment   |  283 | 1.42 | 0.13 | 0.42 | 1.54 | 0.46 |   0.88 |                     1.77 |                      56.18 |
| target      |  103 | 1.57 | 2.27 | 1.35 | 1.00 | 0.59 |   1.55 |                    27.18 |                       5.83 |
| other       |   28 | 1.36 | 0.79 | 0.54 | 1.11 | 0.61 |   0.95 |                     7.14 |                      53.57 |

"other" = 28 claims with a type outside the six listed (action_plan, analysis, aspiration, compliance, contribution, explanation, investment, opportunity, outcome, plan, projection, risk, strategy).

## 6. Sector (R3.8)

| sector                 |   firms |   claims |   claim_mean |   mean of firm means |   claim-type-standardised |   % substantiated |
|:-----------------------|--------:|---------:|-------------:|---------------------:|--------------------------:|------------------:|
| Technology             |       1 |      165 |         1.31 |                 1.31 |                      1.28 |             16.97 |
| Transportation         |       2 |      352 |         1.21 |                 1.21 |                      1.29 |             11.65 |
| Construction Materials |       3 |      622 |         1.19 |                 1.18 |                      1.19 |             12.38 |
| Telecommunications     |       2 |      326 |         1.19 |                 1.20 |                      1.15 |              8.90 |
| Real Estate            |       4 |     1027 |         1.12 |                 1.12 |                      1.14 |              9.54 |
| Energy                 |       6 |      985 |         1.11 |                 1.10 |                      1.11 |             10.66 |
| Food & Agribusiness    |       4 |      913 |         1.11 |                 1.12 |                      1.13 |              8.98 |
| Retail                 |       3 |      722 |         1.07 |                 1.04 |                      1.05 |              6.93 |
| Healthcare             |       1 |      219 |         1.04 |                 1.04 |                      1.02 |              4.11 |
| Banking & Finance      |       4 |      989 |         1.03 |                 1.03 |                      1.05 |              7.28 |

Mixed model (random intercept for firm, claim type and sector as fixed effects, ML). Firm ICC (null model): SMTE 0.047, SMTEC 0.045. Likelihood-ratio test for sector, adjusting for claim type: SMTE χ²(9) = 17.7, p = 0.039; SMTEC χ²(9) = 18.1, p = 0.035.

SMTE model coefficients (reference: commitment; Banking & Finance):

| term                           |   coef |    se |     p |
|:-------------------------------|-------:|------:|------:|
| Intercept                      |  0.878 | 0.039 | 0.000 |
| claim type: achievement        |  0.424 | 0.015 | 0.000 |
| claim type: alignment          | -0.058 | 0.028 | 0.039 |
| claim type: metric             |  0.583 | 0.017 | 0.000 |
| claim type: other              |  0.038 | 0.086 | 0.658 |
| claim type: policy             | -0.088 | 0.019 | 0.000 |
| claim type: target             |  0.620 | 0.045 | 0.000 |
| sector: Construction Materials |  0.125 | 0.059 | 0.033 |
| sector: Energy                 |  0.046 | 0.050 | 0.355 |
| sector: Food & Agribusiness    |  0.081 | 0.054 | 0.131 |
| sector: Healthcare             | -0.032 | 0.085 | 0.707 |
| sector: Real Estate            |  0.077 | 0.055 | 0.159 |
| sector: Retail                 | -0.023 | 0.058 | 0.694 |
| sector: Technology             |  0.227 | 0.087 | 0.009 |
| sector: Telecommunications     |  0.096 | 0.067 | 0.151 |
| sector: Transportation         |  0.223 | 0.067 | 0.001 |

## 7. SDG goals (R3.8)

|   SDG |   claims (full count) |   claims (fractional) |   firms |   mean SMTE (claims) |   mean SMTE (fractional weights) |   mean of firm means |   claim-type-standardised |   % substantiated |
|------:|----------------------:|----------------------:|--------:|---------------------:|---------------------------------:|---------------------:|--------------------------:|------------------:|
|  1.00 |                131.00 |                 46.92 |   24.00 |                 0.98 |                             0.98 |                 0.96 |                      0.96 |              6.11 |
|  2.00 |                171.00 |                 66.50 |   20.00 |                 1.08 |                             1.09 |                 1.08 |                      1.05 |              5.26 |
|  3.00 |                655.00 |                296.67 |   30.00 |                 1.07 |                             1.08 |                 1.07 |                      1.06 |              6.26 |
|  4.00 |                649.00 |                297.42 |   30.00 |                 1.14 |                             1.18 |                 1.10 |                      1.09 |              7.86 |
|  5.00 |                200.00 |                 78.50 |   29.00 |                 0.91 |                             0.98 |                 0.91 |                      0.95 |              4.00 |
|  6.00 |                319.00 |                140.83 |   27.00 |                 1.17 |                             1.19 |                 1.19 |                      1.15 |             12.23 |
|  7.00 |                928.00 |                367.50 |   30.00 |                 1.26 |                             1.27 |                 1.32 |                      1.21 |             14.22 |
|  8.00 |               2129.00 |                904.58 |   30.00 |                 1.04 |                             1.07 |                 1.04 |                      1.05 |              7.84 |
|  9.00 |               1609.00 |                650.33 |   30.00 |                 1.08 |                             1.09 |                 1.08 |                      1.11 |              7.83 |
| 10.00 |                363.00 |                132.25 |   30.00 |                 0.93 |                             0.95 |                 0.95 |                      0.98 |              4.68 |
| 11.00 |                656.00 |                247.17 |   30.00 |                 1.11 |                             1.12 |                 1.11 |                      1.10 |              8.38 |
| 12.00 |               2625.00 |               1096.50 |   30.00 |                 1.12 |                             1.14 |                 1.10 |                      1.12 |             10.25 |
| 13.00 |               1760.00 |                729.17 |   30.00 |                 1.20 |                             1.22 |                 1.20 |                      1.19 |             12.90 |
| 14.00 |                197.00 |                 80.33 |   22.00 |                 1.29 |                             1.31 |                 1.25 |                      1.26 |             12.69 |
| 15.00 |                476.00 |                199.83 |   30.00 |                 1.17 |                             1.19 |                 1.07 |                      1.17 |             11.97 |
| 16.00 |               1230.00 |                691.00 |   30.00 |                 1.00 |                             1.02 |                 1.01 |                      1.07 |              4.80 |
| 17.00 |                738.00 |                294.50 |   30.00 |                 0.99 |                             0.97 |                 0.98 |                      1.08 |              6.64 |
- Environmental goals (6, 7, 11–15) vs social goals (1–5, 8, 10, 16), claim-level mean: 1.19 vs 1.02 (difference +0.17).
- Environmental goals (6, 7, 11–15) vs social goals (1–5, 8, 10, 16), mean of firm means: 1.18 vs 1.02 (difference +0.16).
- Environmental goals (6, 7, 11–15) vs social goals (1–5, 8, 10, 16), claim-type-standardised: 1.17 vs 1.03 (difference +0.14).

Claims mapped to more than one goal: 89.8% (mean 2.35 goals per claim).

## 8. Firm–goal cells under the two pre-specified rules (R3.5)

| composite   |   min claims | cells      |   all cells |   cells with enough claims |   Rule A: mean ≥ 2.0 |   Rule B: ≥ 1 substantiated claim |   Rule B (robust): ≥ 3 |   median share substantiated % |   mean cell mean |
|:------------|-------------:|:-----------|------------:|---------------------------:|---------------------:|----------------------------------:|-----------------------:|-------------------------------:|-----------------:|
| SMTE        |            3 | declared   |         127 |                        125 |                    0 |                               100 |                     69 |                           7.69 |             1.10 |
| SMTE        |            3 | undeclared |         383 |                        313 |                    2 |                               200 |                     97 |                           5.56 |             1.09 |
| SMTE        |            5 | declared   |         127 |                        121 |                    0 |                                99 |                     69 |                           7.69 |             1.10 |
| SMTE        |            5 | undeclared |         383 |                        274 |                    1 |                               190 |                     96 |                           6.20 |             1.08 |
| SMTEC       |            3 | declared   |         127 |                        125 |                    0 |                                73 |                     31 |                           1.85 |             0.98 |
| SMTEC       |            3 | undeclared |         383 |                        313 |                    2 |                               106 |                     27 |                           0.00 |             0.97 |
| SMTEC       |            5 | declared   |         127 |                        121 |                    0 |                                72 |                     31 |                           1.89 |             0.98 |
| SMTEC       |            5 | undeclared |         383 |                        274 |                    1 |                               102 |                     26 |                           0.00 |             0.96 |

Declared cells (SMTE, ≥ 3 claims, n = 125): highest cell mean 1.75; mean number of substantiated claims per cell 5.1 of 50.0; dimension profile S 1.50, M 0.86, T 0.81, E 1.22. 0 declared cells have no mapped claim at all.

## 9. Stability across the three runs

| dimension   |   all three runs equal % |   max spread ≥ 2 % |   Krippendorff α (ordinal, 3 runs) |
|:------------|-------------------------:|-------------------:|-----------------------------------:|
| S           |                   87.658 |              0.111 |                              0.920 |
| M           |                   94.684 |              1.171 |                              0.966 |
| T           |                   92.184 |              0.380 |                              0.954 |
| E           |                   85.665 |              0.079 |                              0.887 |

## 10. Passage labels and corroboration (R3.2, R3.4)

Share of retrieved passages by label and slot (%; empty slots excluded):

| slot   |   Contradicts |   Extend |   Redundant |   Related |   Unrelated |   empty slots (n) |
|:-------|--------------:|---------:|------------:|----------:|------------:|------------------:|
| S1     |           3.9 |     10   |         5.4 |      65.8 |        14.8 |               289 |
| S2     |           1.6 |      7.9 |         1.9 |      68.4 |        20.3 |               844 |
| X1     |           2   |     23.3 |        48.8 |      22.9 |         2.9 |                 1 |
| X2     |           1.8 |     19.7 |        12.6 |      53.2 |        12.7 |                 7 |
| X3     |           1.6 |     13.5 |         5.9 |      57.2 |        21.7 |                15 |

C: 0 = 56.3%, 1 = 38.3%, 2 = 5.2%, 3 = 0.2%. Claims with at least one passage labelled Contradicts: 6.5% (408). Claims with no cross-section passage at all: 1. Claims with no Extend passage in any slot: 49.3%.

By report: mean SMTE ranges from 0.92 to 1.43; share of passages labelled Unrelated from 8.1% to 19.7% (table: by_report.csv).
