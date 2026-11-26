# English translations of the rater handbooks (30 Oct 2026)

For reviewers and readers. Raters received the Thai handbooks; the Thai text is authoritative.

| English file | Translated from (Thai, as sent to raters) | Used in |
|---|---|---|
| `Scorer-Handbook-Holistics-10OCT26-EN.docx` | `scorer/handbooks-as-sent/Scorer-Handbook-Holistics-10OCT26-fixed.docx` | Round 1 Phase 1 (holistic judgement) |
| `Scorer-Handbook-SMTEC-21OCT26-EN.docx` | `scorer/Scorer-Handbook-SMTEC-21OCT26-changes-marked-DNA-EE.docx` (MD5 e2f6758e0dd2f14bcd99a502a1dd4a76) | Round 1 Phase 2 (SMTEC) and Pilot 20 |

Method: each Thai paragraph was translated and written back into a copy of the Thai docx, so headings, tables and order are unchanged. Paragraphs already in English (examples in the anchor tables) are untouched. Red text and highlighting that marked edits in the Thai SMTEC handbook are not reproduced. The Thai font was swapped for Calibri, with sizes scaled to match. Document metadata (author names) was replaced with "SDG Credibility study team".

`translation/` holds the paragraph pairs (`*_TH_paragraphs.json` and `*_EN_paragraphs.json`, same order) so the translation can be checked line by line, and the script that builds the docx (`translate_handbook_docx.py`).

Translation notes:
- One Thai sentence in SMTEC §5.5 repeats itself ("from the same section, but from the same Section"); it is translated by its meaning: several Extend passages from one section count as 1 section.
- Thai "ข้อกล่าวอ้าง" = claim; "ชุดหลักฐาน" = evidence pack; "ป้ายกำกับข้อความ" = passage label; "ผู้ให้ความเชื่อมั่น" = assurer.
- Dates are given in the Common Era; the Thai originals use B.E. 2569 (= 2026).
