from typing import Optional

import pandas as pd

from demographics._bed_capacity_eras import COMBINED_UNIT_LABEL

ABS_CLINIC = [
    "2A", "2B", "2C", "2D", "2E",
    "3A", "3B", "3C", "3D", "3E",
    "3G", "3H", "3I",
    "4A", "4B", "4C",
    "5A", "5B", "5C", "5D",
]
CP_CLINIC = [
    "08004", "08011", "08014", "08015", "08017", "08021",
    "08022", "08028", "08029", "08034", "08036", "08038",
]

# (name, csv_label, html_label, section_key, style)
_ROW_DEFS = [
    ("n_stays",   "N estancias",                                 "N estancias",                   "demo",               "bold"),
    ("n_patients","N pacientes",                                 "N pacientes",                   "demo",               "bold"),
    ("occupancy", "Ocupaci\u00f3n de camas (%)",                 "Ocupaci\u00f3n de camas",       "demo",               ""),
    # (*) en la columna de ocupaci\u00f3n indica que ese a\u00f1o incluye
    # meses de la \u00e9poca COVID (2020-03 \u2192 2022-02): durante ese
    # tramo E073 e I073 se reportan agregadas como UCI sobre 12 camas.
    ("age",       "Edad, mediana [IQR]",                         "Edad, mediana [IQR]",           "demo",               ""),
    ("male",      "Sexo masculino (n, %)",                       "Sexo masculino",                "demo",               "indent"),
    ("female",    "Sexo femenino (n, %)",                        "Sexo femenino",                 "demo",               "indent"),
    ("spain",     "Nacionalidad espa\u00f1ola (n, %)",           "Nacionalidad espa\u00f1ola",    "demo",               "indent"),
    ("other_nat", "Otras nacionalidades (n, %)",                 "Otras nacionalidades",          "demo",               "indent"),
    ("aisbe",     "Pacientes AISBE (n, %)",                      "Pacientes AISBE",               "demo",               ""),
    ("other_hosp","Procedencia otro hospital (n, %)",            "Procedencia otro hospital",     "demo",               ""),
    ("los",       "Estancia (d\u00edas), mediana [IQR]",         "Estancia (d\u00edas), mediana [IQR]", "clinical",    ""),
    ("cirr",      "Cirrosis (n, %)",                             "Cirrosis",                      "clinical",           ""),
    ("readm24",   "Reingreso 24h (n, %)",                        "Reingreso 24h",                 "clinical",           ""),
    ("readm72",   "Reingreso 72h (n, %)",                        "Reingreso 72h",                 "clinical",           ""),
    ("mg_stay",   "Mortalidad global - en estancia (n, %)",      "En estancia",                   "mortality",          ""),
    ("mg_30",     "Mortalidad global - 30 d\u00edas (n, %)",     "A 30 d\u00edas",               "mortality",          ""),
    ("mg_90",     "Mortalidad global - 90 d\u00edas (n, %)",     "A 90 d\u00edas",               "mortality",          ""),
    ("mc_stay",   "Mortalidad cirrosis - en estancia (n, %)",    "En estancia",                   "mortality-cirr",     ""),
    ("mc_30",     "Mortalidad cirrosis - 30 d\u00edas (n, %)",   "A 30 d\u00edas",               "mortality-cirr",     ""),
    ("mc_90",     "Mortalidad cirrosis - 90 d\u00edas (n, %)",   "A 90 d\u00edas",               "mortality-cirr",     ""),
    ("mn_stay",   "Mortalidad no AISBE - en estancia (n, %)",    "En estancia",                   "mortality-noaisbe",  ""),
    ("mn_30",     "Mortalidad no AISBE - 30 d\u00edas (n, %)",   "A 30 d\u00edas",               "mortality-noaisbe",  ""),
    ("mn_90",     "Mortalidad no AISBE - 90 d\u00edas (n, %)",   "A 90 d\u00edas",               "mortality-noaisbe",  ""),
    ("mo_stay",   "Mortalidad otro hospital - en estancia (n, %)","En estancia",                  "mortality-otherhosp","" ),
    ("mo_30",     "Mortalidad otro hospital - 30 d\u00edas (n, %)","A 30 d\u00edas",              "mortality-otherhosp","" ),
    ("mo_90",     "Mortalidad otro hospital - 90 d\u00edas (n, %)","A 90 d\u00edas",              "mortality-otherhosp","" ),
]

_SECTION_DEFS = [
    ("demo",                "Demograf\u00eda",                       "demo"),
    ("clinical",            "Cl\u00ednica",                          "clinical"),
    ("mortality",           "Mortalidad global",                     "mortality"),
    ("mortality-cirr",      "Mortalidad en cirrosis",                "mortality-cirr"),
    ("mortality-noaisbe",   "Mortalidad en no AISBE",                "mortality-noaisbe"),
    ("mortality-otherhosp", "Mortalidad procedencia otro hospital",  "mortality-otherhosp"),
]


def _format_median_iqr(series: pd.Series) -> str:
    series = series.dropna()
    if series.empty:
        return ""
    q1 = series.quantile(0.25)
    q2 = series.median()
    q3 = series.quantile(0.75)
    return f"{q2:.1f} [{q1:.1f}-{q3:.1f}]"


def _fmt_n_pct(count: int, total: int) -> str:
    if total == 0:
        return ""
    pct = count / total * 100
    return f"{count} ({pct:.1f}%)"


def _classify_aisbe(patient_df: pd.DataFrame) -> pd.Series:
    """Classify patients as AISBE based on health_area and postcode."""
    ha = patient_df["health_area"].astype(str).str.strip()
    pc = patient_df["postcode"].astype(str).str.strip().str[:5]
    is_abs = ha.isin(ABS_CLINIC)
    is_cp = (~is_abs) & pc.isin(CP_CLINIC)
    return is_abs | is_cp


def _mortality(sub: pd.DataFrame) -> dict:
    """Compute in-stay, 30-day and 90-day mortality from admission date."""
    n = len(sub)
    if n == 0:
        return {
            "deaths_stay": 0, "deaths_30": 0, "deaths_90": 0, "n": 0,
            "stay_fmt": "", "d30_fmt": "", "d90_fmt": "",
        }

    deaths_stay = int((sub["exitus_during_stay"] == "Yes").sum())

    admission_dt = pd.to_datetime(sub["admission_date"], errors="coerce", utc=True)
    exitus_dt = pd.to_datetime(sub["exitus_date"], errors="coerce", utc=True)
    valid = exitus_dt.notna() & admission_dt.notna()
    delta = (exitus_dt - admission_dt).dt.total_seconds() / 86400

    deaths_30 = int((valid & (delta >= 0) & (delta <= 30)).sum())
    deaths_90 = int((valid & (delta >= 0) & (delta <= 90)).sum())

    return {
        "deaths_stay": deaths_stay,
        "deaths_30": deaths_30,
        "deaths_90": deaths_90,
        "n": n,
        "stay_fmt": _fmt_n_pct(deaths_stay, n),
        "d30_fmt": _fmt_n_pct(deaths_30, n),
        "d90_fmt": _fmt_n_pct(deaths_90, n),
    }


def compute_summary(
    df: pd.DataFrame,
    bed_occupancy: Optional[pd.DataFrame] = None,
) -> tuple[list[dict], list[int]]:
    """Compute all metrics once and return structured sections + years list.

    Args:
        df: cohort DataFrame.
        bed_occupancy: optional DataFrame returned by
            `demographics._bed_occupancy.compute_bed_occupancy(...)` with
            columns `unit`, `year`, `bed_hours_used`, `bed_hours_available`,
            `pct`. If provided, the "Ocupación de camas" row is filled
            from this table (empirical, monthly aggregated). If None or
            empty, that row is left blank.

    Returns:
        (sections, years) where sections is a list of section dicts suitable
        for both HTML rendering and CSV flattening via _report.to_dataframe().
    """
    if df.empty:
        return [], []

    df = df.copy()
    df = df[df["still_admitted"] == "No"]
    if df.empty:
        return [], []
    if "days_stay" not in df.columns and "hours_stay" in df.columns:
        df["days_stay"] = df["hours_stay"] / 24.0
    df["year_admission"] = df["year_admission"].astype(int)

    years = sorted(df["year_admission"].dropna().unique())

    units_in_cohort: list[str] = sorted(
        u for u in df["ou_loc_ref"].dropna().unique().tolist()
    ) if "ou_loc_ref" in df.columns else []

    # Filtrado y agregación de la ocupación de camas. El bed_occupancy
    # esperado proviene de `compute_bed_occupancy_nominal()` y trae:
    #   effective_unit ∈ {"E073", "I073", "UCI"}, year, regimen, used, avail.
    # En la época `covid` E073 e I073 se colapsan en "UCI" (12 camas), así
    # que para una cohorte que toque cualquiera de las dos unidades hay
    # que aceptar también las filas "UCI". Marcamos los años que incluyen
    # algún tramo COVID con un asterisco; la nota a pie de tabla explica
    # que durante esa época el etiquetado por unidad no es interpretable.
    occupancy_by_year: dict[int, str] = {}
    occupancy_total_text: str = ""
    if bed_occupancy is not None and not bed_occupancy.empty and units_in_cohort:
        unit_col = (
            "effective_unit"
            if "effective_unit" in bed_occupancy.columns
            else "unit"
        )
        allowed_units = set(units_in_cohort)
        if any(u in {"E073", "I073"} for u in units_in_cohort):
            allowed_units.add(COMBINED_UNIT_LABEL)
        occ = bed_occupancy[bed_occupancy[unit_col].isin(allowed_units)].copy()
        if not occ.empty:
            occ["year"] = pd.to_numeric(occ["year"], errors="coerce").astype("Int64")
            occ["bed_hours_used"] = pd.to_numeric(
                occ["bed_hours_used"], errors="coerce"
            ).fillna(0.0)
            occ["bed_hours_available"] = pd.to_numeric(
                occ["bed_hours_available"], errors="coerce"
            ).fillna(0.0)
            has_regimen = "regimen" in occ.columns
            agg = {
                "used": ("bed_hours_used", "sum"),
                "avail": ("bed_hours_available", "sum"),
            }
            if has_regimen:
                agg["covid_in_year"] = (
                    "regimen", lambda s: bool((s == "covid").any())
                )
            yearly = occ.groupby("year", as_index=False).agg(**agg)
            for _, row in yearly.iterrows():
                year_int = int(row["year"])
                avail = float(row["avail"])
                used = float(row["used"])
                if avail > 0:
                    txt = f"{used / avail * 100:.1f}%"
                    if has_regimen and bool(row.get("covid_in_year", False)):
                        txt += " *"
                    occupancy_by_year[year_int] = txt
            total_used = float(yearly["used"].sum())
            total_avail = float(yearly["avail"].sum())
            if total_avail > 0:
                occupancy_total_text = f"{total_used / total_avail * 100:.1f}%"
                if has_regimen and bool(yearly["covid_in_year"].any()):
                    occupancy_total_text += " *"

    rows = {
        name: {
            "label": html_label,
            "csv_label": csv_label,
            "values": {},
            "total": "",
            "style": style,
            "sticky": False,
        }
        for name, csv_label, html_label, _section, style in _ROW_DEFS
    }

    # Totals accumulators
    total_stays = 0
    all_patients: set = set()
    all_ages: list = []
    total_male = total_female = 0
    total_spain = total_other_nat = 0
    total_aisbe = total_n_pat = 0
    total_other_hosp = 0
    all_los: list = []
    total_cirr = total_readm24 = total_readm72 = 0
    t_mg = {"stay": 0, "d30": 0, "d90": 0, "n": 0}
    t_mc = {"stay": 0, "d30": 0, "d90": 0, "n": 0}
    t_mn = {"stay": 0, "d30": 0, "d90": 0, "n": 0}
    t_mo = {"stay": 0, "d30": 0, "d90": 0, "n": 0}

    for year in years:
        sub = df[df["year_admission"] == year]
        n = len(sub)
        total_stays += n
        rows["n_stays"]["values"][year] = str(n)

        if n == 0:
            for r in rows.values():
                r["values"].setdefault(year, "")
            continue

        patients = sub.drop_duplicates(subset=["patient_ref"])
        n_pat = len(patients)
        all_patients.update(patients["patient_ref"].tolist())
        total_n_pat += n_pat
        rows["n_patients"]["values"][year] = str(n_pat)

        rows["occupancy"]["values"][year] = occupancy_by_year.get(int(year), "")

        ages = pd.to_numeric(sub["age_at_admission"], errors="coerce").dropna()
        all_ages.extend(ages.tolist())
        rows["age"]["values"][year] = _format_median_iqr(ages)

        sex_counts = patients["sex"].value_counts(dropna=False)
        male = int(sex_counts.get("Male", 0))
        female = int(sex_counts.get("Female", 0))
        total_male += male
        total_female += female
        rows["male"]["values"][year] = _fmt_n_pct(male, n_pat)
        rows["female"]["values"][year] = _fmt_n_pct(female, n_pat)

        natio = patients["natio_ref"].fillna("").astype(str)
        n_spain = int((natio == "ES").sum())
        n_other = n_pat - n_spain
        total_spain += n_spain
        total_other_nat += n_other
        rows["spain"]["values"][year] = _fmt_n_pct(n_spain, n_pat)
        rows["other_nat"]["values"][year] = _fmt_n_pct(n_other, n_pat)

        patient_health = patients[["patient_ref", "health_area", "postcode"]].set_index(
            "patient_ref"
        )
        is_aisbe = _classify_aisbe(patient_health)
        n_aisbe = int(is_aisbe.sum())
        total_aisbe += n_aisbe
        rows["aisbe"]["values"][year] = _fmt_n_pct(n_aisbe, n_pat)

        if "from_other_hospital" in patients.columns:
            other_hosp_col = pd.to_numeric(
                patients["from_other_hospital"], errors="coerce"
            ).fillna(0)
            n_other_hosp = int((other_hosp_col == 1).sum())
        else:
            n_other_hosp = 0
        total_other_hosp += n_other_hosp
        rows["other_hosp"]["values"][year] = _fmt_n_pct(n_other_hosp, n_pat)

        los = pd.to_numeric(sub["days_stay"], errors="coerce").dropna()
        all_los.extend(los.tolist())
        rows["los"]["values"][year] = _format_median_iqr(los)

        cirr = pd.to_numeric(sub["has_cirrhosis"], errors="coerce").fillna(0)
        has_cirr = int((cirr == 1).sum())
        total_cirr += has_cirr
        rows["cirr"]["values"][year] = _fmt_n_pct(has_cirr, n)

        for col, key in [("readmission_24h", "readm24"), ("readmission_72h", "readm72")]:
            vals = pd.to_numeric(sub[col], errors="coerce").fillna(0)
            count = int((vals == 1).sum())
            rows[key]["values"][year] = _fmt_n_pct(count, n)
            if key == "readm24":
                total_readm24 += count
            else:
                total_readm72 += count

        mort = _mortality(sub)
        rows["mg_stay"]["values"][year] = mort["stay_fmt"]
        rows["mg_30"]["values"][year] = mort["d30_fmt"]
        rows["mg_90"]["values"][year] = mort["d90_fmt"]
        t_mg["stay"] += mort["deaths_stay"]
        t_mg["d30"] += mort["deaths_30"]
        t_mg["d90"] += mort["deaths_90"]
        t_mg["n"] += mort["n"]

        sub_cirr = sub[cirr == 1]
        mort_c = _mortality(sub_cirr)
        rows["mc_stay"]["values"][year] = mort_c["stay_fmt"]
        rows["mc_30"]["values"][year] = mort_c["d30_fmt"]
        rows["mc_90"]["values"][year] = mort_c["d90_fmt"]
        t_mc["stay"] += mort_c["deaths_stay"]
        t_mc["d30"] += mort_c["deaths_30"]
        t_mc["d90"] += mort_c["deaths_90"]
        t_mc["n"] += mort_c["n"]

        patient_is_aisbe = sub["patient_ref"].map(is_aisbe).fillna(False)
        sub_no_aisbe = sub[~patient_is_aisbe.values]
        mort_n = _mortality(sub_no_aisbe)
        rows["mn_stay"]["values"][year] = mort_n["stay_fmt"]
        rows["mn_30"]["values"][year] = mort_n["d30_fmt"]
        rows["mn_90"]["values"][year] = mort_n["d90_fmt"]
        t_mn["stay"] += mort_n["deaths_stay"]
        t_mn["d30"] += mort_n["deaths_30"]
        t_mn["d90"] += mort_n["deaths_90"]
        t_mn["n"] += mort_n["n"]

        if "from_other_hospital" in sub.columns:
            stay_other_hosp = pd.to_numeric(
                sub["from_other_hospital"], errors="coerce"
            ).fillna(0)
            sub_other_hosp = sub[stay_other_hosp == 1]
        else:
            sub_other_hosp = sub.iloc[0:0]
        mort_o = _mortality(sub_other_hosp)
        rows["mo_stay"]["values"][year] = mort_o["stay_fmt"]
        rows["mo_30"]["values"][year] = mort_o["d30_fmt"]
        rows["mo_90"]["values"][year] = mort_o["d90_fmt"]
        t_mo["stay"] += mort_o["deaths_stay"]
        t_mo["d30"] += mort_o["deaths_30"]
        t_mo["d90"] += mort_o["deaths_90"]
        t_mo["n"] += mort_o["n"]

    # Fill totals
    rows["n_stays"]["total"] = str(total_stays)
    rows["n_patients"]["total"] = str(len(all_patients))
    rows["occupancy"]["total"] = occupancy_total_text
    rows["age"]["total"] = _format_median_iqr(pd.Series(all_ages)) if all_ages else ""
    rows["male"]["total"] = _fmt_n_pct(total_male, total_n_pat)
    rows["female"]["total"] = _fmt_n_pct(total_female, total_n_pat)
    rows["spain"]["total"] = _fmt_n_pct(total_spain, total_n_pat)
    rows["other_nat"]["total"] = _fmt_n_pct(total_other_nat, total_n_pat)
    rows["aisbe"]["total"] = _fmt_n_pct(total_aisbe, total_n_pat)
    rows["other_hosp"]["total"] = _fmt_n_pct(total_other_hosp, total_n_pat)
    rows["los"]["total"] = _format_median_iqr(pd.Series(all_los)) if all_los else ""
    rows["cirr"]["total"] = _fmt_n_pct(total_cirr, total_stays)
    rows["readm24"]["total"] = _fmt_n_pct(total_readm24, total_stays)
    rows["readm72"]["total"] = _fmt_n_pct(total_readm72, total_stays)
    rows["mg_stay"]["total"] = _fmt_n_pct(t_mg["stay"], t_mg["n"])
    rows["mg_30"]["total"] = _fmt_n_pct(t_mg["d30"], t_mg["n"])
    rows["mg_90"]["total"] = _fmt_n_pct(t_mg["d90"], t_mg["n"])
    rows["mc_stay"]["total"] = _fmt_n_pct(t_mc["stay"], t_mc["n"])
    rows["mc_30"]["total"] = _fmt_n_pct(t_mc["d30"], t_mc["n"])
    rows["mc_90"]["total"] = _fmt_n_pct(t_mc["d90"], t_mc["n"])
    rows["mn_stay"]["total"] = _fmt_n_pct(t_mn["stay"], t_mn["n"])
    rows["mn_30"]["total"] = _fmt_n_pct(t_mn["d30"], t_mn["n"])
    rows["mn_90"]["total"] = _fmt_n_pct(t_mn["d90"], t_mn["n"])
    rows["mo_stay"]["total"] = _fmt_n_pct(t_mo["stay"], t_mo["n"])
    rows["mo_30"]["total"] = _fmt_n_pct(t_mo["d30"], t_mo["n"])
    rows["mo_90"]["total"] = _fmt_n_pct(t_mo["d90"], t_mo["n"])

    # Assemble sections
    sections = []
    for section_key, section_title, css_class in _SECTION_DEFS:
        section_rows = [
            rows[name]
            for name, _csv, _html, sk, _style in _ROW_DEFS
            if sk == section_key
        ]
        sections.append({
            "section": section_title,
            "css": css_class,
            "rows": section_rows,
        })

    return sections, [int(y) for y in years]
