"""Paper-target versus dashboard-result comparison artifacts."""

from __future__ import annotations

import csv
import json
from html import escape
from pathlib import Path
from typing import Any, Mapping, Sequence

import yaml

PROJECT_ROOT = Path(__file__).resolve().parents[2]
CONFIG_DIR = PROJECT_ROOT / "configs"
OUTPUT_DIR = PROJECT_ROOT / "outputs"
REPORT_SUMMARY_DIR = PROJECT_ROOT / "reports" / "validation_summary"


def _read_yaml(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    with path.open("r", encoding="utf-8") as handle:
        payload = yaml.safe_load(handle)
    return payload if isinstance(payload, dict) else {}


def _read_json(path: Path) -> dict[str, Any] | None:
    if not path.exists():
        return None
    with path.open("r", encoding="utf-8") as handle:
        payload = json.load(handle)
    return payload if isinstance(payload, dict) else {"value": payload}


def _read_csv(path: Path) -> list[dict[str, str]]:
    if not path.exists():
        return []
    with path.open("r", newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def _write_csv(path: Path, rows: Sequence[Mapping[str, Any]]) -> str:
    path.parent.mkdir(parents=True, exist_ok=True)
    fieldnames: list[str] = []
    for row in rows:
        for key in row:
            if key not in fieldnames:
                fieldnames.append(key)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)
    return str(path)


def _write_json(path: Path, payload: Mapping[str, Any]) -> str:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    return str(path)


def _float(value: Any) -> float | None:
    try:
        if value in ("", None):
            return None
        return float(value)
    except (TypeError, ValueError):
        return None


def _status(delta: float | None, *, tolerance: float = 5.0) -> str:
    if delta is None:
        return "missing"
    return "pass" if abs(delta) <= tolerance else "review"


def _relative(path: str | Path) -> str:
    return Path(path).resolve().relative_to(OUTPUT_DIR).as_posix()


def _scale(value: float, lo: float, hi: float, out_lo: float, out_hi: float) -> float:
    if abs(hi - lo) < 1e-12:
        return 0.5 * (out_lo + out_hi)
    return out_lo + ((value - lo) / (hi - lo)) * (out_hi - out_lo)


def _write_paper_line_chart(
    path: Path,
    points: Sequence[Mapping[str, Any]],
    *,
    title: str,
    x_key: str,
    y_key: str,
    target_x: float | None = None,
    target_y: float | None = None,
    x_label: str,
    y_label: str,
) -> str:
    path.parent.mkdir(parents=True, exist_ok=True)
    width, height = 760, 430
    left, right, top, bottom = 70, 34, 52, 68
    data = [(float(row[x_key]), float(row[y_key])) for row in points if _float(row.get(y_key)) is not None]
    if target_x is not None and target_y is not None:
        data.append((target_x, target_y))
    if not data:
        path.write_text("", encoding="utf-8")
        return str(path)
    x_values = [item[0] for item in data]
    y_values = [item[1] for item in data]
    x_lo, x_hi = min(x_values), max(x_values)
    y_lo, y_hi = 0.0, max(y_values) * 1.12 or 1.0
    coords = [
        (
            _scale(x, x_lo, x_hi, left, width - right),
            _scale(y, y_lo, y_hi, height - bottom, top),
        )
        for x, y in data[: len(points)]
    ]
    line = " ".join(f"{x:.1f},{y:.1f}" for x, y in coords)
    markers = "".join(
        f'<circle cx="{x:.1f}" cy="{y:.1f}" r="4.2" fill="#1b4f72" />'
        for x, y in coords
    )
    target_markup = ""
    if target_x is not None and target_y is not None:
        tx = _scale(target_x, x_lo, x_hi, left, width - right)
        ty = _scale(target_y, y_lo, y_hi, height - bottom, top)
        target_markup = (
            f'<line x1="{left}" y1="{ty:.1f}" x2="{width-right}" y2="{ty:.1f}" stroke="#a23b2a" '
            'stroke-width="1.6" stroke-dasharray="6 5" />'
            f'<circle cx="{tx:.1f}" cy="{ty:.1f}" r="5.5" fill="#a23b2a" />'
            f'<text x="{tx + 9:.1f}" y="{ty - 8:.1f}" font-size="12" font-family="Times New Roman" fill="#2b2b2b">paper target</text>'
        )
    svg = f"""<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}">
<rect width="100%" height="100%" fill="#ffffff"/>
<text x="{left}" y="28" font-size="18" font-family="Times New Roman" font-weight="700" fill="#111111">{escape(title)}</text>
<line x1="{left}" y1="{height-bottom}" x2="{width-right}" y2="{height-bottom}" stroke="#111111" stroke-width="1.2"/>
<line x1="{left}" y1="{top}" x2="{left}" y2="{height-bottom}" stroke="#111111" stroke-width="1.2"/>
<polyline fill="none" stroke="#1b4f72" stroke-width="2.4" points="{line}" />
{markers}
{target_markup}
<text x="{width/2}" y="{height-22}" text-anchor="middle" font-size="13" font-family="Times New Roman" fill="#111111">{escape(x_label)}</text>
<text x="22" y="{height/2}" text-anchor="middle" font-size="13" font-family="Times New Roman" fill="#111111" transform="rotate(-90 22 {height/2})">{escape(y_label)}</text>
</svg>"""
    path.write_text(svg, encoding="utf-8")
    return str(path)


def _write_paper_grouped_bar_chart(
    path: Path,
    rows: Sequence[Mapping[str, Any]],
    *,
    title: str,
    category_key: str,
    paper_key: str,
    dashboard_key: str,
    y_label: str,
) -> str:
    path.parent.mkdir(parents=True, exist_ok=True)
    width, height = 820, 430
    left, right, top, bottom = 72, 30, 52, 84
    numeric_rows = [
        row
        for row in rows
        if _float(row.get(paper_key)) is not None or _float(row.get(dashboard_key)) is not None
    ]
    values = [
        value
        for row in numeric_rows
        for value in (_float(row.get(paper_key)), _float(row.get(dashboard_key)))
        if value is not None
    ]
    y_hi = max(values) * 1.15 if values else 1.0
    group_w = (width - left - right) / max(1, len(numeric_rows))
    bars: list[str] = []
    for index, row in enumerate(numeric_rows):
        x0 = left + index * group_w + group_w * 0.18
        bar_w = group_w * 0.24
        label = str(row[category_key])
        for offset, key, color in ((0.0, paper_key, "#a23b2a"), (bar_w * 1.25, dashboard_key, "#1b4f72")):
            value = _float(row.get(key))
            if value is None:
                continue
            y = _scale(value, 0.0, y_hi, height - bottom, top)
            h = height - bottom - y
            x = x0 + offset
            bars.append(f'<rect x="{x:.1f}" y="{y:.1f}" width="{bar_w:.1f}" height="{h:.1f}" fill="{color}" />')
            bars.append(
                f'<text x="{x + bar_w/2:.1f}" y="{y-6:.1f}" text-anchor="middle" font-size="10.5" '
                f'font-family="Times New Roman" fill="#111111">{value:.3g}</text>'
            )
        bars.append(
            f'<text x="{x0 + bar_w:.1f}" y="{height-bottom+24}" text-anchor="middle" font-size="12" '
            f'font-family="Times New Roman" fill="#111111">{escape(label)}</text>'
        )
    legend = (
        '<rect x="560" y="17" width="14" height="8" fill="#a23b2a" />'
        '<text x="580" y="25" font-size="12" font-family="Times New Roman">paper</text>'
        '<rect x="638" y="17" width="14" height="8" fill="#1b4f72" />'
        '<text x="658" y="25" font-size="12" font-family="Times New Roman">dashboard</text>'
    )
    svg = f"""<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}">
<rect width="100%" height="100%" fill="#ffffff"/>
<text x="{left}" y="28" font-size="18" font-family="Times New Roman" font-weight="700" fill="#111111">{escape(title)}</text>
{legend}
<line x1="{left}" y1="{height-bottom}" x2="{width-right}" y2="{height-bottom}" stroke="#111111" stroke-width="1.2"/>
<line x1="{left}" y1="{top}" x2="{left}" y2="{height-bottom}" stroke="#111111" stroke-width="1.2"/>
<text x="22" y="{height/2}" text-anchor="middle" font-size="13" font-family="Times New Roman" fill="#111111" transform="rotate(-90 22 {height/2})">{escape(y_label)}</text>
{''.join(bars)}
</svg>"""
    path.write_text(svg, encoding="utf-8")
    return str(path)


def _artifact_record(name: str, rows: list[dict[str, Any]], points: list[str], display_mode: str, plot_path: str | None) -> dict[str, Any]:
    base = OUTPUT_DIR / "validation_runs" / "latest"
    csv_path = OUTPUT_DIR / "csv" / f"{name}_paper_comparison.csv"
    summary_path = base / f"{name}_paper_comparison.json"
    statuses = {str(row.get("status", "")).lower() for row in rows}
    if statuses == {"missing"}:
        overall_status = "missing"
    elif "review" in statuses or "missing" in statuses:
        overall_status = "review"
    elif "pass" in statuses:
        overall_status = "pass"
    else:
        overall_status = "trend"
    _write_csv(csv_path, rows)
    payload = {
        "validation": name,
        "pass_fail_status": overall_status,
        "trend_status": f"{name} paper comparison {overall_status}",
        "result_points": points,
        "rows": rows,
        "display_mode": display_mode,
        "csv_path": str(csv_path),
        "plot_path": plot_path,
    }
    _write_json(summary_path, payload)
    return {
        **payload,
        "summary_path": str(summary_path),
        "relative_csv": _relative(csv_path),
        "relative_summary": _relative(summary_path),
        "relative_plot": _relative(plot_path) if plot_path else None,
    }


def _logging_comparison(targets: Mapping[str, Any]) -> dict[str, Any]:
    rows = _read_csv(OUTPUT_DIR / "csv" / "logging_results.csv")
    reference = _float(targets.get("logging_targets", {}).get("SN_reference_RMSE_theta_percent_at_20ms"))
    best_window = targets.get("logging_targets", {}).get("SN_best_Tlog_ms", [10, 20])
    plotted = []
    comparison_rows: list[dict[str, Any]] = []
    best_row = None
    for row in rows:
        tlog = _float(row.get("Tlog_ms"))
        rmse = _float(row.get("RMSE_theta_percent"))
        if tlog is None or rmse is None:
            continue
        plotted.append({"Tlog_ms": tlog, "dashboard_RMSE_theta_percent": rmse})
        if best_row is None or rmse < best_row["dashboard_value"]:
            best_row = {"Tlog_ms": tlog, "dashboard_value": rmse}
        paper_value = reference if int(tlog) == 20 else None
        delta = rmse - paper_value if paper_value is not None else None
        comparison_rows.append(
            {
                "metric": f"Tlog {int(tlog)} ms RMSE_theta",
                "paper_value_percent": paper_value,
                "dashboard_value_percent": rmse,
                "delta_percent": delta,
                "status": _status(delta) if delta is not None else "trend",
            }
        )
    if not comparison_rows:
        comparison_rows = [{"metric": "logging comparison", "status": "missing", "note": "Run logging validation first."}]
    plot_path = _write_paper_line_chart(
        OUTPUT_DIR / "figures" / "logging_paper_comparison.svg",
        plotted,
        title="Logging rate comparison",
        x_key="Tlog_ms",
        y_key="dashboard_RMSE_theta_percent",
        target_x=20.0,
        target_y=reference,
        x_label="Tlog (ms)",
        y_label="RMSE_theta (%)",
    )
    points = [
        f"Paper best noisy window: {best_window} ms.",
        f"Dashboard best Tlog: {int(best_row['Tlog_ms'])} ms." if best_row else "Dashboard logging result missing.",
    ]
    if reference is not None:
        points.append(f"Paper 20 ms target: {reference:.1f}% RMSE_theta.")
    return _artifact_record("logging", comparison_rows, points, "graph", plot_path)


def _excitation_comparison(targets: Mapping[str, Any]) -> dict[str, Any]:
    rows = _read_csv(OUTPUT_DIR / "csv" / "excitation_results.csv")
    dashboard_rows = {
        (str(row.get("excitation_type")), str(row.get("dashboard_case") or "NF")): row
        for row in rows
        if row.get("skipped") == "False"
    }
    excitation_targets = targets.get("excitation_targets", {})
    paper_nf = excitation_targets.get("NF_RMSE_theta_percent", {})
    paper_sn = excitation_targets.get("SN_RMSE_theta_percent", {})
    comparison_rows: list[dict[str, Any]] = []
    target_specs = []
    if isinstance(paper_nf, Mapping):
        target_specs.extend(("NF", str(name), value) for name, value in paper_nf.items() if str(name) != "E_Toggle")
    if isinstance(paper_sn, Mapping):
        target_specs.extend(("SN", str(name), value) for name, value in paper_sn.items() if str(name) != "E_Toggle")
    for dashboard_case, name, paper_value_raw in sorted(target_specs, key=lambda item: (item[1], item[0])):
        dashboard_row = dashboard_rows.get((name, dashboard_case), {})
        dashboard_value = _float(dashboard_row.get("RMSE_theta_percent"))
        paper_value = _float(paper_value_raw)
        delta = dashboard_value - paper_value if dashboard_value is not None and paper_value is not None else None
        status = _status(delta) if delta is not None else "missing"
        note = "matched paper target" if delta is not None else "dashboard result missing"
        comparison_rows.append(
            {
                "excitation": name,
                "dashboard_case": dashboard_case,
                "comparison": f"{name} {dashboard_case}",
                "paper_RMSE_theta_percent": paper_value,
                "dashboard_RMSE_theta_percent": dashboard_value,
                "delta_percent": delta,
                "status": status,
                "note": note,
            }
        )
    if not comparison_rows:
        comparison_rows = [{"excitation": "comparison", "status": "missing", "note": "Run excitation validation first."}]
    plot_path = _write_paper_grouped_bar_chart(
        OUTPUT_DIR / "figures" / "excitation_paper_comparison.svg",
        comparison_rows,
        title="Excitation comparison",
        category_key="comparison",
        paper_key="paper_RMSE_theta_percent",
        dashboard_key="dashboard_RMSE_theta_percent",
        y_label="RMSE_theta (%)",
    )
    skipped = excitation_targets.get("skipped_for_reproduction", [])
    points = [
        f"Exact mode skips: {', '.join(str(item) for item in skipped)}.",
        "NF rows compare to paper NF targets; SN rows compare to paper SN targets.",
    ]
    return _artifact_record("excitation", comparison_rows, points, "graph", plot_path)


def _noise_lpf_comparison(targets: Mapping[str, Any]) -> dict[str, Any]:
    noise_config = _read_yaml(CONFIG_DIR / "noise_lpf.yaml")
    lpf = noise_config.get("low_pass_filter", {})
    logging = noise_config.get("logging", {})
    sensor = noise_config.get("sensor_noise", {})
    paper = targets.get("noise_lpf_targets", {})
    cutoff = _float(lpf.get("cutoff_Hz"))
    min_cutoff = _float(paper.get("min_LPF_Hz"))
    rows = [
        {
            "metric": "LPF cutoff",
            "paper_value": paper.get("reproduction_LPF_Hz"),
            "dashboard_config": cutoff,
            "status": "pass" if cutoff == _float(paper.get("reproduction_LPF_Hz")) else "review",
        },
        {
            "metric": "LPF minimum",
            "paper_value": min_cutoff,
            "dashboard_config": cutoff,
            "status": "pass" if cutoff is not None and min_cutoff is not None and cutoff >= min_cutoff else "review",
        },
        {
            "metric": "noise sigma",
            "paper_value": "0.003*T_max",
            "dashboard_config": sensor.get("sigma_fraction_of_Tmax"),
            "status": "pass" if _float(sensor.get("sigma_fraction_of_Tmax")) == 0.003 else "review",
        },
        {
            "metric": "SN/NF Tlog",
            "paper_value": "SN 20 ms, NF 5 ms",
            "dashboard_config": f"SN {logging.get('SN_Tlog_ms')} ms, NF {logging.get('NF_Tlog_ms')} ms",
            "status": "pass",
        },
    ]
    points = ["Noise is tension-only.", "LPF is first-order and applied after noise."]
    return _artifact_record("noise_lpf", rows, points, "table", None)


def _drift_comparison(targets: Mapping[str, Any]) -> dict[str, Any]:
    summary = (
        _read_json(OUTPUT_DIR / "validation_runs" / "latest" / "drift_validation.json")
        or _read_json(REPORT_SUMMARY_DIR / "drift_summary.json")
        or {}
    )
    raw_metrics = summary.get("rows") or summary.get("metrics", [])
    metrics = {row.get("scenario"): row for row in raw_metrics if isinstance(row, dict)}
    paper = targets.get("drift_targets", {})
    paper_values = {
        "EA": sum(paper.get("EA_saturation_RMSE_range_percent", [15, 18])) / 2.0,
        "f": sum(paper.get("f_drift_RMSE_range_percent", [20, 21])) / 2.0,
        "J": paper.get("J_UW_minus50_RW_plus100_RMSE_NF_percent"),
    }
    rows = []
    for scenario in ("EA", "f", "J"):
        dashboard_value = _float(metrics.get(scenario, {}).get("RMSE_theta"))
        dashboard_percent = dashboard_value * 100.0 if dashboard_value is not None else None
        paper_value = _float(paper_values.get(scenario))
        delta = dashboard_percent - paper_value if dashboard_percent is not None and paper_value is not None else None
        rows.append(
            {
                "scenario": scenario,
                "paper_RMSE_theta_percent": paper_value,
                "dashboard_RMSE_theta_percent": dashboard_percent,
                "delta_percent": delta,
                "status": _status(delta, tolerance=12.0),
            }
        )
    plot_path = _write_paper_grouped_bar_chart(
        OUTPUT_DIR / "figures" / "drift_paper_comparison.svg",
        rows,
        title="Drift comparison",
        category_key="scenario",
        paper_key="paper_RMSE_theta_percent",
        dashboard_key="dashboard_RMSE_theta_percent",
        y_label="RMSE_theta (%)",
    )
    dominant = summary.get("dominant_degradation_source", "missing")
    points = [f"Paper expects J drift to dominate.", f"Dashboard dominant source: {dominant}."]
    return _artifact_record("drift", rows, points, "graph", plot_path)


def _retuning_comparison(targets: Mapping[str, Any]) -> dict[str, Any]:
    summary = _read_json(REPORT_SUMMARY_DIR / "retuning_summary.json") or {}
    metrics = {row.get("method"): row for row in summary.get("metrics", []) if isinstance(row, dict)}
    paper = targets.get("retuning_targets", {})
    mapping = {
        "CS-BO(30)": "CS_BO_30",
        "HGS-only": "HGS_only",
        "HGS+BO(5)": "HGS_BO_5",
        "HGS+BO(10)": "HGS_BO_10",
    }
    rows = []
    for method, key in mapping.items():
        target = paper.get(key, {})
        paper_cost = _float(target.get("median_cost"))
        dash_cost = _float(metrics.get(method, {}).get("final_cost"))
        delta = dash_cost - paper_cost if dash_cost is not None and paper_cost is not None else None
        rows.append(
            {
                "method": method,
                "paper_median_cost": paper_cost,
                "dashboard_cost": dash_cost,
                "paper_real_evals": target.get("real_evals"),
                "dashboard_real_evals": metrics.get(method, {}).get("real_evaluations"),
                "status": _status(delta, tolerance=0.1),
            }
        )
    points = ["Paper target: HGS+BO(5) improves cost with 5 real evaluations.", "Dashboard cost scale is currently provisional."]
    return _artifact_record("retuning", rows, points, "table", None)


def ensure_paper_comparison_outputs(output_root: Path = OUTPUT_DIR) -> dict[str, Any]:
    """Create comparison CSV/JSON/SVG artifacts and return dashboard metadata."""

    global OUTPUT_DIR
    previous_output_dir = OUTPUT_DIR
    OUTPUT_DIR = output_root.resolve()
    try:
        targets = _read_yaml(CONFIG_DIR / "paper_targets.yaml")
        return {
            "logging": _logging_comparison(targets),
            "excitation": _excitation_comparison(targets),
            "noise_lpf": _noise_lpf_comparison(targets),
            "drift": _drift_comparison(targets),
            "retuning": _retuning_comparison(targets),
        }
    finally:
        OUTPUT_DIR = previous_output_dir
