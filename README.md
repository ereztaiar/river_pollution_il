# River Pollution in Israel — Power BI Report

A Power BI report on bacterial water-quality readings from Israeli rivers and
streams (נחלים), 2019–2026. It shows which sites and periods go over the
Ministry of Health's recommended limit of **400 CFU per 100 ml** for fecal
indicator bacteria, how often this happens, and whether it is getting better
or worse.

## Background

The Ministry of Health samples rivers and streams on a regular schedule
(normally about once every two weeks) and publishes a public notice when
readings go over its recommendation. For an example, see
[תוצאות חריגות בדיגום מים שבוצע לבחינת מצב הזיהום בנחלים בצפון](https://www.gov.il/he/pages/17092026-04)
(17.09.2026). In that notice, sites on the Hatzbani, the Jordan, Meshushim,
Jilabun, Zavitan, Zaki, El Al, Tzalmon, Kziv and others read between 440 and
3,600 CFU/100 ml. The Ministry warned the public that entering those streams
may be a health risk until readings come back normal and stable.

Each notice covers one day of samples. This report puts several years of
those samples in one place so you can compare sites and track trends.

## Data source

The raw data comes from the Ministry of Health's Freedom of Information page,
under **תוצאות ניטור מים בנחלים** (stream water monitoring results):
<https://www.gov.il/he/pages/freedom_of_information_public_health>

The files in [`data/`](data/) are:

- `csv/*.csv` — one extract per year (or year range): sampling point code,
  sampling date, bacterial index, result (CFU/100 ml), point name, and site.
  The raw text is in Hebrew.
- `locations*.csv` — sampling points, with coordinates, used by the map page.
- `units_environmental_health_streams.xlsx` — the original workbook from the
  Ministry. The CSVs were exported from it with
  [`scripts/export_sheets_to_csv.py`](scripts/export_sheets_to_csv.py).

## What the report covers

The data includes three bacterial indices:

| Index | Meaning |
|---|---|
| קוליפורם צואתי | Fecal coliforms |
| E.coli MUG | *E. coli* |
| סטרפטוקוק/אנטרוקוק ממוצא צואתי | Fecal streptococci / enterococci |

For all three, a sample counts as an **exceedance** when it reads above 400
CFU/100 ml. For enterococci, Israel has no limit of its own, so the report
uses the EU inland-waters "good" threshold, which is also 400.

Some lab results come back as **TNTC** ("too numerous to count", Hebrew
`פלטה מכוסה`). There is no number for these samples. The report plots them
as a gray bar above the highest real reading, not as zero and not as a gap.

The report pages are:

- **מבוא** (Introduction): what each bacterium is and what TNTC means
- **לוח בקרה** (Control panel): filters for year, bacteria, region/site/location,
  above/below 400, and minimum sampling events. These filters apply to every
  page.
- **מפה** (Map): sampling points and how polluted each one is
- **נתוני נחלים** (Stream data): monthly counts per site
- **מגמה ועונתיות** (Trend & seasonality)
- **האתרים המזוהמים ביותר / הנקיים ביותר** (Most / least polluted sites)
- **השוואת אתרים נבחרים** (Selected-site comparison)
- **איכות הנתונים** (Data quality)

## How to open the report

You need [Power BI Desktop](https://powerbi.microsoft.com/desktop/) (Windows).

### From the release bundle

1. Download `river_pollution_bundle.zip` from the
   [latest release](../../releases/tag/latest-bundle).
2. **Extract the whole zip.** Right-click it, choose **Extract All…**, and
   pick a folder.
3. Open `river_pollution.pbip` from the extracted folder.

> **Don't open the `.pbip` from inside the zip.** If you double-click it
> while browsing the zip in Explorer, Windows copies only that one file to a
> temp folder. Power BI then shows
> `ReportDefinition: Required artifact is missing in ...\definition.pbir`,
> because the report and model folders were not extracted next to it.

### From a clone

```bash
git clone https://github.com/ereztaiar/river_pollution_il.git
```

Open `river_pollution.pbip` from the cloned folder. The data files are loaded
from `data/csv/` in the same folder.

## Project layout

This project uses the Power BI Project (PBIP) format, so the report and model
are stored as text files you can compare in git:

- `river_pollution.pbip`: open this file in Power BI Desktop
- `river_pollution.SemanticModel/`: the data model (TMDL)
- `river_pollution.Report/`: report pages and visuals (PBIR JSON)
- `data/`: the source data
- `scripts/`: helper scripts for data prep (sheet export, location
  extraction, geocoding)
