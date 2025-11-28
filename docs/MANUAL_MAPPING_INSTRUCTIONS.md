# Instructions for AI Browser to Complete Manual ISIN-ORGNR Mapping

## Task Overview
Find Swedish organization numbers (ORGNR) for 20 unmapped Swedish companies that are still actively trading.

## Input File
`data/intermediate/top_unmapped_companies.csv`

## Output Format
Create a CSV file: `data/intermediate/manual_isin_orgnr_mapping_complete.csv`

Format:
```csv
isin,orgnr,company_name,source,verification_status
SE0000242455,5020177753,Swedbank AB,allabolag.se,verified
```

## Companies to Map (Prioritized by Trading Volume)

### Top Priority (Already Done - 5 ISINs)
1. ✅ SE0000242455 - Swedbank AB → 5020177753
2. ✅ SE0000667891 - Sandvik AB → 5560003468
3. ✅ SE0000112625 - Sandvik AB → 5560003468
4. ✅ SE0007100599 - Svenska Handelsbanken AB → 5020077862
5. ✅ SE0007100607 - Svenska Handelsbanken AB → 5020077862

### High Priority - DO THESE (15 ISINs)
6. SE0001174970 - Millicom International Cellular SA
7. SE0007871645 - Kindred Group PLC
8. SE0012454072 - Avanza Bank Holding AB
9. SE0007048020 - Collector AB
10. SE0014428835 - VNV Global AB (publ)
11. SE0012231074 - VNV Global AB (publ)
12. SE0008321608 - Investment Oresund AB
13. SE0002579912 - GHP Specialty Care AB
14. SE0007192018 - VEF Ltd
15. SE0007184189 - Genova Property Group AB
16. SE0004777241 - TSR Noisiver 7 AB
17. SE0007526132 - Genova Property Group AB
18. SE0000391716 - Traction AB
19. SE0010023432 - Mertiva AB
20. SE0000312043 - Havsfrun Investment AB

---

## Step-by-Step Instructions for AI Browser

### For Each Company, Follow These Steps:

#### Step 1: Search for Swedish ORGNR
**Search Query Template:**
```
"[COMPANY_NAME]" Sweden ORGNR organization number
```

**Example:**
```
"Avanza Bank Holding AB" Sweden ORGNR organization number
```

#### Step 2: Check Primary Sources (in order of reliability)

**Source 1: Allabolag.se (Most Reliable)**
- URL pattern: `https://www.allabolag.se/[ORGNR]/[company-name]`
- Look for: "Org.nr" or "Organisationsnummer"
- Format: `XXXXXX-XXXX` (with hyphen) or `XXXXXXXXXX` (10 digits)
- Example: `556274-8458` or `5562748458`

**Source 2: Company's Official Website**
- Look for: "Organisationsnummer", "Org.nr", "Corporate Registration Number"
- Usually found in: Footer, "About Us", "Contact", "Legal Notice"

**Source 3: Swedish Companies Registration Office (Bolagsverket)**
- Search at: `https://bolagsverket.se`
- Official government registry

**Source 4: Financial Databases**
- Bloomberg, Reuters, D&B, ZoomInfo
- Look for Swedish registration number

#### Step 3: Validate the ORGNR Format
Swedish ORGNRs must be:
- **Exactly 10 digits** (when hyphen removed)
- Format: `XXXXXX-XXXX` or `XXXXXXXXXX`
- First 6 digits: Registration date (YYMMDD format, but not always actual date)
- Last 4 digits: Sequential number + check digit

**Valid Examples:**
- `556274-8458` → `5562748458` ✓
- `502017-7753` → `5020177753` ✓
- `556030-8313` → `5560308313` ✓

**Invalid Examples:**
- `SE556274845801` (this is VAT number, remove "SE" and "01")
- `123456` (too short)
- `FR31542019096` (French tax number, not Swedish)

#### Step 4: Special Cases to Handle

**Case A: Foreign Companies (No Swedish ORGNR)**
Some ISINs are Swedish Depositary Receipts (SDRs) for foreign companies:
- Millicom International Cellular SA (Luxembourg)
- Kindred Group PLC (Malta/UK)
- VEF Ltd (Bermuda/Guernsey)

For these, record:
```csv
SE0001174970,NONE,Millicom International Cellular SA,official_website,foreign_company_no_swedish_orgnr
```

**Case B: Acquired/Merged Companies**
If company was acquired:
- Look for: "acquired by", "merged with", "now part of"
- Use the PARENT company's ORGNR
- Note in source: `acquired_by_[PARENT]_[PARENT_ORGNR]`

**Case C: Multiple ORGNRs Found**
If you find multiple ORGNRs:
- Choose the one marked "publ" (publicly traded)
- Choose the one matching the company legal name exactly
- Prefer "AB (publ)" over subsidiaries

#### Step 5: Verify via Cross-Reference
After finding ORGNR, verify by searching:
```
"ORGNR [found_number]" Sweden
```

This should return pages about the SAME company. If different company appears, the ORGNR is wrong.

---

## Exact Prompts for AI Browser

### Prompt 1: Initial Search
```
Search for the Swedish organization number (ORGNR) for "[COMPANY_NAME]" in Sweden.

Check these sources in order:
1. allabolag.se - search for the company name
2. Company's official website (look in footer, about us, or legal notice)
3. bolagsverket.se (Swedish Companies Registration Office)
4. Financial databases (Bloomberg, Reuters, D&B)

The ORGNR should be a 10-digit number, often written as XXXXXX-XXXX.

If this is a foreign company listed on the Swedish exchange, report "FOREIGN" and note the country of incorporation.

Report back:
- ORGNR (10 digits, no hyphen)
- Source URL
- Confidence level (high/medium/low)
```

### Prompt 2: Verification
```
Verify that ORGNR [found_number] belongs to "[COMPANY_NAME]" by:
1. Searching "ORGNR [found_number]" on Google
2. Checking if search results confirm this is the same company
3. Looking for any discrepancies in company name or registration

Report:
- Confirmed: YES/NO
- Any discrepancies found
- Alternative ORGNRs if found
```

### Prompt 3: Handle Special Cases
```
For company "[COMPANY_NAME]":
1. Check if it's a foreign company (not Swedish) - look for "Luxembourg", "Malta", "UK", "Bermuda", etc.
2. Check if it was acquired or merged - search "[COMPANY_NAME] acquired merged"
3. If acquired, find the parent company's ORGNR

Report the finding with status:
- SWEDISH_ACTIVE: Found valid Swedish ORGNR
- FOREIGN: Foreign company, no Swedish ORGNR expected
- ACQUIRED: Acquired by [PARENT], use parent ORGNR [NUMBER]
- NOT_FOUND: Could not find valid ORGNR
```

---

## Output Template for AI Browser

After completing all 15 companies, provide a CSV with this exact format:

```csv
isin,orgnr,company_name,source,verification_status
SE0012454072,5562748458,Avanza Bank Holding AB,allabolag.se,verified
SE0001174970,NONE,Millicom International Cellular SA,official_website,foreign_company
SE0007048020,5560686278,Collector AB,allabolag.se,verified
```

**Columns:**
- `isin`: The ISIN from the input list
- `orgnr`: 10-digit number (no hyphen) OR "NONE" if foreign/not found
- `company_name`: Official company name
- `source`: Where you found it (allabolag.se, official_website, bolagsverket, bloomberg, etc.)
- `verification_status`:
  - `verified` - Found and cross-checked
  - `foreign_company` - No Swedish ORGNR expected
  - `acquired_by_[PARENT]` - Use parent company ORGNR
  - `uncertain` - Found but not confident
  - `not_found` - Could not find

---

## Quality Control Checklist

Before submitting results, verify:
- [ ] All ORGNRs are exactly 10 digits (when hyphen removed)
- [ ] No ORGNRs start with "SE" (that's VAT format, not ORGNR)
- [ ] No ORGNRs end with "01" (that's VAT suffix, remove it)
- [ ] Foreign companies marked as "NONE" or "FOREIGN"
- [ ] Each ORGNR cross-referenced with company name
- [ ] Sources documented for all entries
- [ ] Verification status provided for all entries

---

## Expected Results

After completing this task:
- **15-20 additional ISINs mapped**
- **Combined total: 510-515 mapped ISINs** (495 current + 15-20 new)
- **Estimated market cap coverage: 75-80%**

Some companies may be foreign (no Swedish ORGNR), which is expected and correct.

---

## What to Do with Results

Once AI browser completes the CSV:

1. Save to: `data/intermediate/manual_isin_orgnr_mapping_complete.csv`

2. Merge with existing mapping using Python:
```python
import pandas as pd

# Load existing
df_existing = pd.read_csv('data/intermediate/isin_orgnr_mapping_improved.csv')

# Load manual mappings
df_manual = pd.read_csv('data/intermediate/manual_isin_orgnr_mapping_complete.csv')

# Filter only verified Swedish companies
df_manual_valid = df_manual[
    (df_manual['orgnr'] != 'NONE') &
    (df_manual['verification_status'].str.contains('verified|acquired'))
]

# Convert ORGNR to numeric
df_manual_valid['orgnr'] = pd.to_numeric(df_manual_valid['orgnr'], errors='coerce')

# Merge
df_existing = df_existing.set_index('isin')
for idx, row in df_manual_valid.iterrows():
    if row['isin'] in df_existing.index:
        df_existing.loc[row['isin'], 'orgnr'] = row['orgnr']
        df_existing.loc[row['isin'], 'mapping_method'] = 'manual'
df_existing = df_existing.reset_index()

# Save final
df_existing.to_csv('data/intermediate/isin_orgnr_mapping_final.csv', index=False)

print(f"Final mapping: {df_existing['orgnr'].notna().sum()} ISINs")
```

---

## Example Walkthrough: Avanza Bank Holding AB

**ISIN**: SE0012454072

**Step 1:** Search "Avanza Bank Holding AB Sweden ORGNR"

**Step 2:** Found on allabolag.se:
- URL: `https://www.allabolag.se/5562748458/avanza-bank-holding-ab`
- ORGNR: `556274-8458`

**Step 3:** Validate format:
- Remove hyphen: `5562748458` ✓
- 10 digits ✓
- Valid Swedish ORGNR ✓

**Step 4:** Verify:
- Search "ORGNR 5562748458"
- Results confirm: Avanza Bank Holding AB ✓

**Output:**
```csv
SE0012454072,5562748458,Avanza Bank Holding AB,allabolag.se,verified
```

---

## Summary

**Task**: Find ORGNRs for 15 unmapped Swedish company ISINs

**Method**: Search Swedish registries and official sources

**Expected Time**: 30-60 minutes for an AI browser

**Expected Success Rate**: 10-15 out of 15 (some may be foreign companies)

**Final Coverage**: ~75-80% of Swedish market cap
