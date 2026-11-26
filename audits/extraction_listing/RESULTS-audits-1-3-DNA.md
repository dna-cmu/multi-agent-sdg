# Audit results — auditor DNA (one auditor; second auditor not yet returned)

## Audit 1 — claim extraction
Spans: 4 (BDMS-2024-SR-EN-p115-117, BDMS-2024-SR-EN-p82-84, DELTA-2024-SR-EN-p21-23, DELTA-2024-SR-EN-p65-67). Auditor listed 30 claims; the extractor produced 11 claims on the same pages.

| match threshold | recall: auditor claims found by the extractor | precision: extracted claims that match an auditor claim |
|---|---|---|
| 60% (main) | 4 of 30 (13%; 95% interval 5–30%) | 4 of 11 (36%; 95% interval 15–65%) |
| 50% | 4 of 30 (13%; 95% interval 5–30%) | 4 of 11 (36%; 95% interval 15–65%) |
| 70% | 4 of 30 (13%; 95% interval 5–30%) | 4 of 11 (36%; 95% interval 15–65%) |

By span (60% threshold):
| span | auditor claims | found by extractor | extracted claims | match an auditor claim |
|---|---|---|---|---|
| BDMS-2024-SR-EN-p115-117 | 5 | 0 | 0 | 0 |
| BDMS-2024-SR-EN-p82-84 | 6 | 2 | 5 | 2 |
| DELTA-2024-SR-EN-p21-23 | 11 | 0 | 0 | 0 |
| DELTA-2024-SR-EN-p65-67 | 8 | 2 | 6 | 2 |

Auditor claims the extractor did not capture:
- BDMS-2024-SR-EN-p82-84 p.82 [commitment]: BDMS emphasizes protecting data subject rights and upholds data protection as a part of responsible operations towards society and regulatory requirements. 
- BDMS-2024-SR-EN-p82-84 p.82 [commitment]: BDMS has established clear and effective processes for data subject rights to ensure the users can fully and accurately exercise their rights.
- BDMS-2024-SR-EN-p82-84 p.84 [target]: The main goal is to create a good interaction between healthcare services and providers to customers and to deliver an excellent experience to them. BDMS recognizes the i
- BDMS-2024-SR-EN-p82-84 p.84 [commitment]:  BDMS is committed to advancing the safety culture within the organization and employing quality control strategies for service delivery at both national and internationa
- BDMS-2024-SR-EN-p115-117 p.115 [achievement]: Emphasizing screening and selecting potential suppliers to ensure efficient supply chain management which contributes to corporate sustainability, BDMS sets out guideline
- BDMS-2024-SR-EN-p115-117 p.115 [achievement]: Moreover, the process ensures sustainable values for internal and external stakeholders and encourages continuous development throughout the supply chain covering economi
- BDMS-2024-SR-EN-p115-117 p.116 [achievement]: The Supplier Code of Conduct authorizes the rights for all suppliers to inquire, report wrongdoings, or submit complaints about any violations or suspected violations aga
- BDMS-2024-SR-EN-p115-117 p.116 [metric]: Supplier Engagement ethics as well as social, environmental and safety aspects. Details of Suppliers Unit Number of Suppliers Number of suppliers covered and received com
- BDMS-2024-SR-EN-p115-117 p.117 [commitment]: All suppliers must undergo a selection and evaluation process based on the sustainability criteria in line with the BDMS Supplier Code of Conduct. The suppliers are then 
- DELTA-2024-SR-EN-p21-23 p.22 [achievement]: To systematically drive transparency among Delta Group, Corporate Governance Committee has been set up in early 2019. 
- DELTA-2024-SR-EN-p21-23 p.22 [achievement]: n 2023, Delta utilizes online conference technology to facilitate our sub-committee’s discussion. The sub-committees’ attendance rate has been reported as follows. Find m
- DELTA-2024-SR-EN-p21-23 p.23 [target]: Anti-corruption, ethics, and transparencyh are crucial for a tech company in the energy transformation era, particularly as its targets eco-friendly growth and carbon neu
- DELTA-2024-SR-EN-p21-23 p.23 [metric]: 3 confirmed incidents of business partner's contgract termination or not renew due to corruption issue
- DELTA-2024-SR-EN-p21-23 p.23 [metric]: 35,166  2023 Learning hour. Our Business Ethics and Anti Corruption Policy
- DELTA-2024-SR-EN-p21-23 p.23 [metric]: 3 Cases confirmed employee dismissals or disciplinary actions for corruption.
- DELTA-2024-SR-EN-p65-67 p.65 [achievement]: For example, our power supply units used in data centers have the highest efficiencies in the world to significantly reduce power loss. Furthermore, the energy storage sy
- DELTA-2024-SR-EN-p65-67 p.65 [target]: The company will continue to improve our product’s energy efficiency. Most of Delta's power management products have surpassed 92% energy efficiency, such as our PV inver
- DELTA-2024-SR-EN-p65-67 p.65 [target]: Delta aim to achieve Product Carbon Footprint (PCF) data or certifications for all products exported to EU customers by 2030.
- DELTA-2024-SR-EN-p65-67 p.65 [target]: y 2024-2025, we plan to build up another badge of PCF expert pool as well as provide LCA software training. To enhance all business unit capacity, Delta listed Simapro as
- DELTA-2024-SR-EN-p65-67 p.66 [achievement]: Delta Group's participation in COP21 and various climate change events has highlighted the increasing focus on product safety, health, and environmental handling instruct
- DELTA-2024-SR-EN-p65-67 p.67 [commitment]: Based on the International Energy Agency (IEA)’s climate-related scenarios for transition risks including Sustainable Development Scenario, Net Zero Emissions by 2050 Sce
- DELTA-2024-SR-EN-p21-23 p.21 [achievement]: In 2023, 6 majors' operation risks by business with 2 critical concerns had communicated to the highest governance.
- DELTA-2024-SR-EN-p21-23 p.21 [achievement]:  Up to 2023, there is no claw back provision for deferred share policy, sign-on bonuses or recruitment incentive payment and termination payment. 
- DELTA-2024-SR-EN-p21-23 p.21 [metric]: The NCC works together with the President to set the President’s KPI with consideration to his/her role as the Chairman of the Sustainable Development Committee. The Pres
- DELTA-2024-SR-EN-p21-23 p.21 [achievement]: In 2023, remuneration of Chairman of the Board, non-Executive Director, executive director, independent director and Audit committee chairman had 100% approved by the com
- DELTA-2024-SR-EN-p21-23 p.21 [achievement]: The Ratio of the annual total compensation for Delta President, Executive and management to the median annual total compensation for all employee was 1.25659.

Extracted claims with no matching auditor claim (to be classified by the auditors):
- BDMS-2024-SR-EN-p82-84 p.82 CLM-0086 [commitment]: BDMS develops user-friendly and accessible channels for submitting requests and complaints to ensure rapid and effective flow.
- BDMS-2024-SR-EN-p82-84 p.82 CLM-0087 [commitment]: BDMS regularly assesses and evaluates the process to ensure compliance with data protection regulations and standards.
- BDMS-2024-SR-EN-p82-84 p.82 CLM-0089 [policy]: The agreements signed among BDMS subsidiaries standardize procedures for managing and sharing data while enhancing collaboration and operation efficiency between entities
- DELTA-2024-SR-EN-p65-67 p.66 CLM-0041 [commitment]: Delta ensures that 100% of its products comply with health, safety, and environmental regulations, enabling our global customers to make informed purchasing decisions.
- DELTA-2024-SR-EN-p65-67 p.66 CLM-0043 [commitment]: Delta also supports informed purchasing choices by applying eco-labels to its products.
- DELTA-2024-SR-EN-p65-67 p.66 CLM-0045 [achievement]: Up to 2023 more than 200 Delta power supply products had obtained 80 plus certification, and some of them achieved the Titanium level launched in volume production.
- DELTA-2024-SR-EN-p65-67 p.66 CLM-0046 [achievement]: During the reporting period, there were no incidents of non-compliance concerning product and service information labeling, marketing communication, the health and safety

Claim type, matched pairs: same type 1 of 4.

## Audit 3 — declared SDG priorities (30 reports × 17 goals = 510 cells)

**Strict reading (main).** Auditor declares 304 cells; detector declares 127 cells.
- Both declare: 98. Auditor only (detector missed): 206. Detector only (not declared according to the auditor): 29. Neither: 177.
- Cell agreement 53.9%; Cohen’s κ 0.16. Of the detector’s declared cells, 98 of 127 (77%; 95% interval 69–84%) are declared according to the auditor; of the auditor’s declared cells, 98 of 304 (32%; 95% interval 27–38%) were detected.
- Reports where the two sets are identical: 1 of 30.

**Broad reading (sensitivity).** Auditor declares 333 cells; detector declares 127 cells.
- Both declare: 104. Auditor only (detector missed): 229. Detector only (not declared according to the auditor): 23. Neither: 154.
- Cell agreement 50.6%; Cohen’s κ 0.14. Of the detector’s declared cells, 104 of 127 (82%; 95% interval 74–88%) are declared according to the auditor; of the auditor’s declared cells, 104 of 333 (31%; 95% interval 26–36%) were detected.
- Reports where the two sets are identical: 1 of 30.

| company | auditor (strict) | auditor (broad, n) | detector | detector only | 
|---|---|---|---|---|
| Advanced Info Service | 1 3 4 5 8 9 10 11 16 17 | 10 | 4 9 13 | 13 |
| Airports of Thailand | none | 0 | 12 13 | 12 13 |
| Asset World Corporation | 1 5 6 8 10 11 12 13 14 15 16 17 | 12 | 7 12 13 15 | 7 |
| Bangchak Corporation | 6 8 11 12 13 15 16 17 | 8 | 7 12 13 | 7 |
| Bangkok Dusit Medical Services | 3 4 5 6 7 8 9 10 12 13 16 17 | 12 | 3 5 6 12 13 16 | – |
| Bangkok Expressway and Metro | 3 4 5 6 7 8 9 10 11 12 13 15 16 | 13 | 7 13 | – |
| Berli Jucker | 3 4 8 9 10 | 5 | 5 6 12 13 15 | 5 6 12 13 15 |
| CP ALL | 1 2 3 4 5 6 7 8 9 10 11 12 13 14 15 16 17 | 17 | 1 2 8 10 11 | – |
| Carabao Group | 1 3 4 5 6 7 8 9 10 12 13 14 15 16 17 | 15 | 1 2 3 4 5 6 7 8 9 10 12 13 14 15 17 | 2 |
| Central Pattana | 3 5 7 8 10 11 12 13 17 | 9 | 13 17 | – |
| Central Retail Corporation | 1 3 4 7 8 9 10 11 12 13 14 15 | 12 | 1 2 3 5 8 10 12 15 16 | 2 5 16 |
| Charoen Pokphand Foods | 2 3 9 11 12 14 17 | 7 | 2 13 | 13 |
| Delta Electronics Thailand | 1 2 3 4 5 6 7 8 9 11 12 13 14 15 16 17 | 16 | 8 12 13 | – |
| Global Power Synergy | 3 4 5 6 7 8 9 10 11 12 13 15 16 17 | 14 | 6 7 13 | – |
| Indorama Ventures | 3 4 6 7 8 9 12 13 17 | 9 | 5 12 13 | 5 |
| Kasikornbank | none | 0 | 4 8 13 | 4 8 13 |
| Krungthai Bank | 1 2 4 5 7 8 9 10 12 13 16 | 11 | 8 10 13 | – |
| Minor International | 9 12 13 14 15 | 5 | 9 12 13 14 15 | – |
| Osotspa | 1 2 3 5 8 9 10 12 13 14 16 17 | 12 | 3 6 7 12 13 | 6 7 |
| PTT | 1 2 3 4 5 6 7 8 9 10 11 12 13 14 15 16 17 | 17 | 7 12 13 16 | – |
| PTT Exploration and Production | 1 2 3 4 5 6 7 8 9 10 11 12 13 14 15 16 17 | 17 | 3 7 8 9 12 13 14 15 16 | – |
| PTT Global Chemical | 9 12 13 | 17 | 1 3 9 13 | – |
| SCG Packaging | 1 3 4 5 6 7 8 9 10 11 12 13 15 16 17 | 15 | 6 12 13 15 | – |
| Siam Cement Group | 6 13 | 17 | 7 10 12 13 15 | – |
| Siam Commercial Bank | 1 4 5 6 7 8 9 10 11 12 13 15 16 17 | 14 | 8 9 13 | – |
| TISCO Financial Group | 1 3 4 5 7 8 9 10 11 12 13 16 17 | 13 | 7 13 16 | – |
| Thai Oil | 3 4 7 8 9 12 13 15 16 | 9 | 12 13 15 | – |
| Thai Union Group | 2 3 5 8 10 12 13 14 15 | 9 | 12 | – |
| True Corporation | 3 4 8 9 10 12 13 16 17 | 9 | 4 7 12 | 7 |
| WHA Corporation | 3 6 7 8 9 12 13 16 17 | 9 | 6 7 12 13 15 | 15 |
## Follow-up checks after scoring (24 Nov 2026)

### Why extraction recall is low: section text is cut at 12,000 characters (CORRECTED 24 Nov 2026)
- Key check: searching the whole report for each auditor claim (ignoring page) finds 5 of 30, against 4 of 30 on the audited pages, so the key's page placement is not the cause.
- Cause in the code: `agents/planner.py` (lines 551–553) joins the text of a section and truncates it to 12,000 characters before the claim-extraction call.
- Confirmed in the outputs, independently of the code: for 764 sections with at least three located claims, the stretch of text spanned by a section's claims is at most 12,500 characters in 98.7% of sections (median 3,100), although in 45% of cases the next section's first claim is more than 15,000 characters further on.
- CORRECTION. An earlier version of this note said that a median of 30% of each report's text reached the extractor (range 8% to 64%). That figure was computed by applying the stored section boundaries (chunk indices from the parse of 15–16 April) to the chunk files of 24–25 April, which come from a later parse with different chunk numbering. The figure is withdrawn.
- Replacement estimate, which does not use chunk indices: the share of each report's text that lies more than 12,000 characters from the first extracted claim of every section, and so was very probably never read, has a median of 37% (range 3% to 89% across the 30 reports); BDMS 18%, DELTA 47%. This is a lower bound for unread text in sections that produced claims; it cannot see sections that were read and produced no claim.

### Firm–goal rules recomputed with the auditor's declaration matrix (SMTE, cells with at least 3 claims)
| declared according to | declared cells | with ≥3 claims | Rule A (mean ≥ 2.0) | Rule B (≥1 substantiated) | Rule B (≥3) | median share substantiated | mean cell mean |
|---|---|---|---|---|---|---|---|
| detector (as in the paper) | 127 | 125 | 0 | 100 (80%) | 69 (55%) | 7.7% | 1.10 |
| auditor, strict (main) | 304 | 286 | 0 | 212 (74%) | 128 (45%) | 6.2% | 1.08 |
| auditor, broad | 333 | 308 | 1 | 224 (73%) | 138 (45%) | 6.2% | 1.09 |
Undeclared cells under the auditor's strict matrix: 152 with ≥3 claims; Rule A 2; Rule B 88 (58%); ≥3: 38 (25%).
