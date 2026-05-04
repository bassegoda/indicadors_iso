"""Análisis de los 10 gérmenes más frecuentes en frotis rectal MDR
por unidad (E073, I073), 2019-2025.

Regla de deduplicación:
    Cada paciente cuenta una sola vez por (año, organismo). Si un mismo
    paciente tiene varios aislados del mismo germen el mismo año, suma 1.
    Patrones de resistencia se analizarán al cruzar con `antibiograms`.

Salidas:
    micro/output/rectal_mdr_top10_<unit>.png  (gráficos)
    micro/output/rectal_mdr_top10_<unit>.csv  (tabla pivot año x germen)

Tests estadísticos:
    - Chi-cuadrado global sobre la tabla año x germen (¿cambia el mix?).
    - Por germen: regresión lineal de la proporción anual ~ año.
"""
from __future__ import annotations

from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from scipy.stats import chi2_contingency, linregress

_REPO_ROOT = Path(__file__).resolve().parent.parent.parent
OUT_DIR = _REPO_ROOT / "micro" / "output"

UNITS = ["E073", "I073"]
TOP_N = 10
YEARS = list(range(2019, 2026))

# Fusión de etiquetas que el laboratorio re-codificó durante el periodo.
# El cambio "K. pneumoniae" → "K. pneumoniae complex" hacia 2021 era un
# artefacto de catálogo, no un cambio epidemiológico. Aplicamos la misma
# normalización a Enterobacter cloacae y Citrobacter freundii por
# coherencia (mismo patrón "specie" / "specie complex" en MALDI-TOF).
ORGANISM_MERGES = {
    "Klebsiella pneumoniae": "Klebsiella pneumoniae (complex)",
    "Klebsiella pneumoniae complex": "Klebsiella pneumoniae (complex)",
    "Enterobacter cloacae": "Enterobacter cloacae (complex)",
    "Enterobacter cloacae complex": "Enterobacter cloacae (complex)",
    "Citrobacter freundii": "Citrobacter freundii (complex)",
    "Citrobacter freundii complex": "Citrobacter freundii (complex)",
}


def deduplicate(df: pd.DataFrame) -> pd.DataFrame:
    """1 fila por (año, paciente, organismo). Descarta NaN en micro_descr.

    Aplica `ORGANISM_MERGES` ANTES de la dedup para que un paciente con
    'K. pneumoniae' y 'K. pneumoniae complex' el mismo año cuente 1.
    """
    sub = df.dropna(subset=["micro_descr"]).copy()
    sub["micro_descr"] = sub["micro_descr"].replace(ORGANISM_MERGES)
    return sub.drop_duplicates(
        subset=["year_admission", "patient_ref", "micro_descr"]
    )


def top_n_organisms(df_unique: pd.DataFrame, n: int = TOP_N) -> list[str]:
    return df_unique["micro_descr"].value_counts().head(n).index.tolist()


def yearly_pivot(
    df_unique: pd.DataFrame, organisms: list[str]
) -> pd.DataFrame:
    sub = df_unique[df_unique["micro_descr"].isin(organisms)]
    pivot = (
        sub.groupby(["year_admission", "micro_descr"]).size().unstack(fill_value=0)
    )
    pivot = pivot.reindex(index=YEARS, columns=organisms, fill_value=0)
    return pivot


def chi2_global(pivot: pd.DataFrame) -> tuple[float, float, int]:
    chi2, p, dof, _ = chi2_contingency(pivot.values)
    return chi2, p, dof


def per_organism_trend(pivot: pd.DataFrame) -> pd.DataFrame:
    """Regresión lineal de proporción anual ~ año, por organismo."""
    totals = pivot.sum(axis=1).replace(0, np.nan)
    prop = pivot.div(totals, axis=0).fillna(0)
    rows = []
    years = np.array(prop.index, dtype=float)
    for org in pivot.columns:
        y = prop[org].values
        slope, intercept, r, p, se = linregress(years, y)
        rows.append({
            "micro_descr": org,
            "total_n": int(pivot[org].sum()),
            "prop_first_year": round(float(y[0]) * 100, 1),
            "prop_last_year": round(float(y[-1]) * 100, 1),
            "slope_pct_per_year": round(slope * 100, 2),
            "r2": round(r * r, 3),
            "p_value": round(p, 4),
        })
    return pd.DataFrame(rows).sort_values("total_n", ascending=False)


def plot_unit(
    unit: str, pivot: pd.DataFrame, chi: tuple[float, float, int]
) -> Path:
    fig, axes = plt.subplots(1, 2, figsize=(15, 6))
    chi2, p, dof = chi
    fig.suptitle(
        f"Frotis rectal MDR — Top {TOP_N} gérmenes — {unit} (2019-2025)\n"
        f"χ² global año × germen: χ²={chi2:.1f}, dof={dof}, p={p:.3g}",
        fontsize=12,
    )

    # Panel 1: cuentas absolutas
    ax = axes[0]
    cmap = plt.get_cmap("tab10")
    for i, org in enumerate(pivot.columns):
        ax.plot(
            pivot.index, pivot[org],
            marker="o", linewidth=1.8, color=cmap(i % 10), label=org,
        )
    ax.set_title("Pacientes únicos / año (recuento)")
    ax.set_xlabel("Año de ingreso")
    ax.set_ylabel("Pacientes únicos con aislado")
    ax.set_xticks(pivot.index)
    ax.grid(alpha=0.3)

    # Panel 2: proporción 100% apilada
    ax = axes[1]
    totals = pivot.sum(axis=1).replace(0, np.nan)
    prop = pivot.div(totals, axis=0).fillna(0) * 100
    bottom = np.zeros(len(prop))
    for i, org in enumerate(prop.columns):
        ax.bar(
            prop.index, prop[org], bottom=bottom,
            color=cmap(i % 10), label=org, width=0.7,
        )
        bottom += prop[org].values
    ax.set_title("Proporción dentro del Top 10 (%)")
    ax.set_xlabel("Año de ingreso")
    ax.set_ylabel("% del total Top 10")
    ax.set_xticks(prop.index)
    ax.set_ylim(0, 100)
    ax.grid(alpha=0.3, axis="y")

    handles, labels = axes[0].get_legend_handles_labels()
    fig.legend(
        handles, labels,
        loc="lower center", ncol=5, fontsize=9,
        bbox_to_anchor=(0.5, -0.02),
    )
    plt.tight_layout(rect=[0, 0.06, 1, 0.94])

    out_path = OUT_DIR / f"rectal_mdr_top10_{unit}.png"
    plt.savefig(out_path, dpi=140, bbox_inches="tight")
    plt.close(fig)
    return out_path


def analyze_unit(unit: str) -> None:
    csv = OUT_DIR / f"rectal_mdr_{unit}_2019-2025.csv"
    df = pd.read_csv(csv)
    df_unique = deduplicate(df)

    print(f"\n=== {unit} ===")
    print(
        f"Aislados crudos: {len(df)} | tras dedup (año,paciente,germen): "
        f"{len(df_unique)} | pacientes únicos: {df_unique['patient_ref'].nunique()}"
    )

    top10 = top_n_organisms(df_unique)
    pivot = yearly_pivot(df_unique, top10)
    chi = chi2_global(pivot)
    trend = per_organism_trend(pivot)

    pivot_out = OUT_DIR / f"rectal_mdr_top10_{unit}.csv"
    pivot.to_csv(pivot_out)
    trend_out = OUT_DIR / f"rectal_mdr_top10_{unit}_trend.csv"
    trend.to_csv(trend_out, index=False)
    png = plot_unit(unit, pivot, chi)

    print("\nTabla pivot (año × germen):")
    print(pivot.to_string())
    print("\nχ² global año × germen:")
    print(f"  χ²={chi[0]:.2f}, dof={chi[2]}, p={chi[1]:.4g}")
    print("\nTendencia por germen (regresión lineal de proporción anual):")
    print(trend.to_string(index=False))
    print(f"\nGuardado: {png.relative_to(_REPO_ROOT)}")
    print(f"Guardado: {pivot_out.relative_to(_REPO_ROOT)}")
    print(f"Guardado: {trend_out.relative_to(_REPO_ROOT)}")


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    for unit in UNITS:
        analyze_unit(unit)


if __name__ == "__main__":
    main()
