from pathlib import Path
from typing import Any

import pandas as pd
import streamlit as st


APP_TITLE = "Manufacturing Release Command Center"
DATA_DIR = Path(__file__).parent / "data"

STATUS_ORDER = ["BLOCKED", "HOLD", "REVIEW", "READY"]
STATUS_COLORS = {
    "BLOCKED": "#b42318",
    "HOLD": "#b54708",
    "REVIEW": "#ca8504",
    "READY": "#067647",
}


st.set_page_config(page_title=APP_TITLE, layout="wide")


def inject_css() -> None:
    st.markdown(
        """
        <style>
        .block-container {
            padding-top: 1.25rem;
            padding-bottom: 1.5rem;
        }
        h1 {
            font-size: 1.45rem !important;
            line-height: 1.2 !important;
            margin-bottom: 0.15rem !important;
            color: #101828;
        }
        h2, h3 {
            color: #101828;
            letter-spacing: 0;
        }
        div[data-testid="stMetric"] {
            background: #ffffff;
            border: 1px solid #e4e7ec;
            border-radius: 8px;
            padding: 0.8rem 0.9rem;
            box-shadow: 0 1px 2px rgba(16, 24, 40, 0.04);
        }
        div[data-testid="stMetricLabel"] {
            color: #667085;
            font-size: 0.78rem;
        }
        div[data-testid="stMetricValue"] {
            color: #101828;
            font-size: 1.55rem;
        }
        .section-card {
            background: #ffffff;
            border: 1px solid #e4e7ec;
            border-radius: 8px;
            padding: 1rem;
            box-shadow: 0 1px 2px rgba(16, 24, 40, 0.04);
            margin-bottom: 0.75rem;
        }
        .executive-header {
            border: 1px solid #d0d5dd;
            border-left: 4px solid #344054;
            border-radius: 8px;
            padding: 0.85rem 1rem;
            background: #fcfcfd;
            margin-bottom: 0.85rem;
        }
        .synthetic-label {
            display: inline-block;
            color: #344054;
            background: #f2f4f7;
            border: 1px solid #d0d5dd;
            border-radius: 999px;
            padding: 0.15rem 0.55rem;
            font-size: 0.72rem;
            font-weight: 700;
            letter-spacing: 0.04em;
        }
        .status-badge {
            display: inline-block;
            border-radius: 999px;
            padding: 0.2rem 0.55rem;
            font-size: 0.75rem;
            font-weight: 700;
            border: 1px solid transparent;
        }
        .badge-ready { color: #067647; background: #ecfdf3; border-color: #abefc6; }
        .badge-review { color: #93370d; background: #fffaeb; border-color: #fedf89; }
        .badge-hold { color: #b54708; background: #fff4ed; border-color: #fed7aa; }
        .badge-blocked { color: #b42318; background: #fef3f2; border-color: #fecdca; }
        .insight-panel {
            background: #f8fafc;
            border: 1px solid #d0d5dd;
            border-radius: 8px;
            padding: 1rem;
            color: #344054;
            min-height: 8.5rem;
        }
        .small-muted {
            color: #667085;
            font-size: 0.86rem;
        }
        section[data-testid="stSidebar"] {
            background: #f9fafb;
        }
        div[data-testid="stDataFrame"] {
            border: 1px solid #e4e7ec;
            border-radius: 8px;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )


def normalize_columns(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    df.columns = (
        df.columns.str.strip()
        .str.lower()
        .str.replace(" ", "_", regex=False)
        .str.replace("-", "_", regex=False)
    )
    return df


@st.cache_data(show_spinner=False)
def load_csv(name: str) -> pd.DataFrame:
    path = DATA_DIR / name
    if not path.exists():
        return pd.DataFrame()
    return normalize_columns(pd.read_csv(path))


def first_present(row: pd.Series, names: list[str], default: Any = "") -> Any:
    for name in names:
        if name in row and pd.notna(row[name]) and row[name] != "":
            return row[name]
    return default


def text_contains(value: Any, *needles: str) -> bool:
    text = str(value or "").lower().replace("_", " ").replace("-", " ")
    return any(needle.lower().replace("_", " ").replace("-", " ") in text for needle in needles)


def is_open(value: Any) -> bool:
    return str(value or "").strip().lower() in {
        "open",
        "active",
        "pending",
        "in_progress",
        "in progress",
        "overdue",
        "not_started",
        "not started",
    }


def is_yes(value: Any) -> bool:
    return str(value or "").strip().lower() in {"yes", "y", "true", "1", "required"}


def issue_flag_has(row: pd.Series, *needles: str) -> bool:
    flag_columns = [column for column in row.index if "issue" in column or "flag" in column]
    return any(text_contains(row.get(column, ""), *needles) for column in flag_columns)


def parsed_date(value: Any) -> pd.Timestamp | pd.NaT:
    return pd.to_datetime(value, errors="coerce")


def get_lot_supplier_ids(lot: pd.Series) -> list[str]:
    supplier_values = [
        first_present(lot, ["supplier_id", "primary_supplier_id", "material_supplier_id"]),
        first_present(lot, ["supplier_ids", "supplier_list"]),
    ]
    supplier_ids: list[str] = []
    for value in supplier_values:
        if pd.isna(value) or value == "":
            continue
        supplier_ids.extend(
            item.strip() for item in str(value).replace("|", ",").replace(";", ",").split(",") if item.strip()
        )
    return sorted(set(supplier_ids))


def supplier_risk_for_lot(lot: pd.Series, suppliers: pd.DataFrame) -> tuple[str, list[str]]:
    supplier_ids = get_lot_supplier_ids(lot)
    if suppliers.empty:
        return "UNKNOWN", []

    id_column = "supplier_id" if "supplier_id" in suppliers.columns else None
    risk_column = next((col for col in ["risk_level", "supplier_risk", "risk_tier"] if col in suppliers.columns), None)
    if not id_column or not risk_column:
        return "UNKNOWN", []

    matched = suppliers[suppliers[id_column].astype(str).isin([str(value) for value in supplier_ids])]
    if matched.empty:
        return "UNKNOWN", []

    risks = matched[risk_column].astype(str).str.upper().tolist()
    evidence = [
        f"Supplier {row[id_column]} risk: {str(row[risk_column]).upper()}"
        for _, row in matched.iterrows()
        if pd.notna(row.get(risk_column))
    ]
    if "HIGH" in risks:
        return "HIGH", evidence
    if "MEDIUM" in risks:
        return "MEDIUM", evidence
    if "LOW" in risks:
        return "LOW", evidence
    return "UNKNOWN", evidence


def open_deviations_for_lot(lot_id: Any, deviations: pd.DataFrame) -> pd.DataFrame:
    if deviations.empty or "lot_id" not in deviations.columns:
        return pd.DataFrame()
    status_column = next((col for col in ["status", "deviation_status"] if col in deviations.columns), None)
    subset = deviations[deviations["lot_id"].astype(str) == str(lot_id)]
    if status_column:
        subset = subset.loc[subset[status_column].apply(is_open).astype(bool)]
    return subset


def open_validation_changes_for_lot(lot: pd.Series, changes: pd.DataFrame) -> pd.DataFrame:
    if changes.empty:
        return pd.DataFrame()

    required_columns = {"product_id", "plant_id"}
    if not required_columns.issubset(set(changes.columns)):
        return pd.DataFrame()

    status_column = next((col for col in ["status", "change_status"] if col in changes.columns), None)
    validation_column = next(
        (col for col in ["validation_required", "requires_validation", "validation_required_flag"] if col in changes.columns),
        None,
    )
    subset = changes[
        (changes["product_id"].astype(str) == str(lot.get("product_id", "")))
        & (changes["plant_id"].astype(str) == str(lot.get("plant_id", "")))
    ]
    if status_column:
        subset = subset.loc[subset[status_column].apply(is_open).astype(bool)]
    if validation_column:
        subset = subset.loc[subset[validation_column].apply(is_yes).astype(bool)]
    else:
        subset = subset.loc[subset.apply(lambda row: text_contains(row.to_string(), "validation"), axis=1).astype(bool)]
    return subset


def blocking_validation_changes_for_lot(lot: pd.Series, changes: pd.DataFrame) -> pd.DataFrame:
    if changes.empty:
        return changes

    direct_columns = [column for column in ["lot_id", "affected_lot_id"] if column in changes.columns]
    direct_mask = pd.Series(False, index=changes.index)
    for column in direct_columns:
        direct_mask = direct_mask | (changes[column].astype(str) == str(lot.get("lot_id", "")))

    if "effective_date" not in changes.columns:
        return changes.loc[direct_mask] if direct_columns else changes

    manufacture_date = parsed_date(lot.get("manufacture_date", ""))
    if pd.isna(manufacture_date):
        return changes.loc[direct_mask] if direct_columns else pd.DataFrame(columns=changes.columns)

    effective_dates = pd.to_datetime(changes["effective_date"], errors="coerce")
    effective_for_lot = effective_dates.notna() & (effective_dates <= manufacture_date)
    return changes.loc[direct_mask | effective_for_lot]


def overdue_capas_for_lot(lot_id: Any, capas: pd.DataFrame) -> pd.DataFrame:
    if capas.empty:
        return pd.DataFrame()

    subset = capas.copy()
    if "lot_id" in subset.columns:
        subset = subset.loc[subset["lot_id"].astype(str) == str(lot_id)]

    status_column = next((col for col in ["status", "capa_status"] if col in subset.columns), None)
    if status_column:
        subset = subset.loc[subset[status_column].apply(is_open).astype(bool)]

    overdue_column = next((col for col in ["overdue", "is_overdue", "overdue_flag"] if col in subset.columns), None)
    if overdue_column:
        subset = subset.loc[subset[overdue_column].apply(is_yes).astype(bool)]
    elif "due_date" in subset.columns:
        due_dates = pd.to_datetime(subset["due_date"], errors="coerce")
        subset = subset[due_dates < pd.Timestamp.today().normalize()]
    else:
        subset = subset[subset.apply(lambda row: text_contains(row.to_string(), "overdue"), axis=1)]
    return subset


def pending_training_for_lot(lot: pd.Series, training: pd.DataFrame) -> pd.DataFrame:
    if training.empty:
        return pd.DataFrame()

    subset = training.copy()
    for column in ["plant_id", "product_id"]:
        if column in subset.columns and column in lot.index:
            subset = subset.loc[subset[column].astype(str) == str(lot.get(column, ""))]

    status_column = next((col for col in ["status", "training_status", "completion_status"] if col in subset.columns), None)
    if status_column:
        subset = subset.loc[
            subset[status_column].astype(str).str.lower().isin(["pending", "incomplete", "overdue", "not started"])
        ]
    else:
        subset = subset.loc[
            subset.apply(lambda row: text_contains(row.to_string(), "pending", "incomplete", "overdue"), axis=1).astype(bool)
        ]
    return subset


def incomplete_overdue_training_for_changes(training: pd.DataFrame, changes: pd.DataFrame, lot: pd.Series) -> bool:
    if training.empty or changes.empty:
        return False
    change_ids = set()
    if "change_control_id" in changes.columns:
        change_ids.update(changes["change_control_id"].astype(str).tolist())
    if "change_id" in changes.columns:
        change_ids.update(changes["change_id"].astype(str).tolist())

    candidates = training.copy()
    for column in ["plant_id", "product_id"]:
        if column in candidates.columns and column in lot.index:
            candidates = candidates.loc[candidates[column].astype(str) == str(lot.get(column, ""))]

    if change_ids:
        change_column = next((col for col in ["change_control_id", "change_id"] if col in candidates.columns), None)
        if change_column:
            candidates = candidates.loc[candidates[change_column].astype(str).isin(change_ids)]

    if candidates.empty:
        return False

    overdue_column = next((col for col in ["overdue", "is_overdue", "overdue_flag"] if col in candidates.columns), None)
    if overdue_column:
        overdue = candidates[overdue_column].apply(is_yes)
    elif "due_date" in candidates.columns:
        overdue = pd.to_datetime(candidates["due_date"], errors="coerce") < pd.Timestamp.today().normalize()
    else:
        overdue = candidates.apply(lambda row: text_contains(row.to_string(), "overdue"), axis=1)

    status_column = next((col for col in ["status", "training_status", "completion_status"] if col in candidates.columns), None)
    if status_column:
        incomplete = candidates[status_column].astype(str).str.lower().isin(["pending", "incomplete", "overdue", "not started"])
    else:
        incomplete = candidates.apply(lambda row: text_contains(row.to_string(), "pending", "incomplete", "not started"), axis=1)
    return bool((overdue & incomplete).any())


def record_ref(row: pd.Series, fallback_prefix: str) -> str:
    for column in ["id", "record_id", "deviation_id", "capa_id", "change_control_id", "change_id", "training_id"]:
        if column in row and pd.notna(row[column]):
            return f"{fallback_prefix} {row[column]}"
    return fallback_prefix


def score_lot(
    lot: pd.Series,
    suppliers: pd.DataFrame,
    deviations: pd.DataFrame,
    capas: pd.DataFrame,
    changes: pd.DataFrame,
    training: pd.DataFrame,
) -> dict[str, Any]:
    score = 100
    penalties: list[str] = []
    blockers: list[str] = []
    evidence: list[str] = []

    lot_id = lot.get("lot_id", lot.name)
    lot_deviations = open_deviations_for_lot(lot_id, deviations)
    severity_column = next((col for col in ["severity", "deviation_severity", "classification"] if col in lot_deviations.columns), None)

    for _, deviation in lot_deviations.iterrows():
        severity = str(deviation.get(severity_column, "")).lower() if severity_column else deviation.to_string().lower()
        reference = record_ref(deviation, "Deviation")
        if "critical" in severity:
            score -= 35
            penalties.append("-35 open critical deviation")
            blockers.append("Open critical deviation")
            evidence.append(f"{reference}: open critical deviation")
        elif "major" in severity:
            score -= 15
            penalties.append("-15 open major deviation")
            evidence.append(f"{reference}: open major deviation")

    if issue_flag_has(lot, "failed environmental", "environmental monitoring", "em failure"):
        score -= 25
        penalties.append("-25 failed environmental monitoring")
        blockers.append("Failed environmental monitoring")
        evidence.append("Lot issue flag: failed environmental monitoring")

    if issue_flag_has(lot, "incomplete batch", "batch record"):
        score -= 20
        penalties.append("-20 incomplete batch record")
        blockers.append("Incomplete batch record")
        evidence.append("Lot issue flag: incomplete batch record")

    if issue_flag_has(lot, "missing coa", "coa missing", "certificate of analysis"):
        score -= 15
        penalties.append("-15 missing COA")
        blockers.append("Missing COA")
        evidence.append("Lot issue flag: missing COA")

    if issue_flag_has(lot, "pending qa review") or text_contains(lot.get("current_release_status", ""), "review"):
        qa_penalty = 16 if is_yes(lot.get("is_high_priority", False)) else 12
        score -= qa_penalty
        penalties.append(f"-{qa_penalty} pending QA review")
        evidence.append("Lot issue flag: pending QA review")

    lot_changes = open_validation_changes_for_lot(lot, changes)
    blocking_changes = blocking_validation_changes_for_lot(lot, lot_changes)
    if not lot_changes.empty:
        score -= 20
        penalties.append("-20 open validation-required change impact")
        if not blocking_changes.empty:
            blockers.append("Open validation-required change effective for lot")
        for _, change in lot_changes.iterrows():
            if change.name in blocking_changes.index:
                evidence.append(f"{record_ref(change, 'Change')}: effective validation-required change")
            else:
                evidence.append(f"{record_ref(change, 'Change')}: open validation-required change, not yet effective for lot")

    lot_capas = overdue_capas_for_lot(lot_id, capas)
    if not lot_capas.empty:
        score -= 10
        penalties.append("-10 overdue CAPA")
        for _, capa in lot_capas.iterrows():
            evidence.append(f"{record_ref(capa, 'CAPA')}: overdue")

    lot_training = pending_training_for_lot(lot, training)
    if not lot_training.empty:
        score -= 8
        penalties.append("-8 pending training")
        for _, training_row in lot_training.head(3).iterrows():
            evidence.append(f"{record_ref(training_row, 'Training')}: pending/incomplete")

    if incomplete_overdue_training_for_changes(training, blocking_changes, lot):
        blockers.append("Incomplete overdue training linked to open validation-required change")
        evidence.append("Training blocker: incomplete overdue training linked to open validation-required change")

    supplier_risk, supplier_evidence = supplier_risk_for_lot(lot, suppliers)
    evidence.extend(supplier_evidence)
    if supplier_risk == "HIGH":
        score -= 35
        penalties.append("-35 high-risk supplier")
    elif supplier_risk == "MEDIUM":
        score -= 16
        penalties.append("-16 medium-risk supplier")

    score = max(0, min(100, score))
    if blockers:
        status = "BLOCKED"
    elif score < 60:
        status = "HOLD"
    elif score <= 84:
        status = "REVIEW"
    else:
        status = "READY"

    return {
        "lot_id": lot_id,
        "plant_id": lot.get("plant_id", ""),
        "product_id": lot.get("product_id", ""),
        "supplier_id": first_present(lot, ["supplier_id", "primary_supplier_id", "material_supplier_id"]),
        "readiness_score": score,
        "recommended_status": status,
        "supplier_risk": supplier_risk,
        "penalties": "; ".join(dict.fromkeys(penalties)) or "None",
        "hard_blockers": "; ".join(dict.fromkeys(blockers)) or "None",
        "evidence_references": "; ".join(dict.fromkeys(evidence)) or "No exceptions identified",
    }


@st.cache_data(show_spinner=False)
def build_scored_table() -> tuple[pd.DataFrame, dict[str, pd.DataFrame]]:
    data = {
        "plant": load_csv("plant.csv"),
        "product": load_csv("product.csv"),
        "supplier": load_csv("supplier.csv"),
        "lot": load_csv("lot.csv"),
        "deviation": load_csv("deviation.csv"),
        "capa": load_csv("capa.csv"),
        "change_control": load_csv("change_control.csv"),
        "training_record": load_csv("training_record.csv"),
        "release_decision": load_csv("release_decision.csv"),
        "scored_release_readiness": load_csv("scored_release_readiness.csv"),
    }

    lots = data["lot"]
    if lots.empty:
        return pd.DataFrame(), data

    scored_rows = [
        score_lot(row, data["supplier"], data["deviation"], data["capa"], data["change_control"], data["training_record"])
        for _, row in lots.iterrows()
    ]
    scored = pd.DataFrame(scored_rows)

    if "plant_id" in data["plant"].columns:
        plant_name_col = next((col for col in ["plant_name", "name", "site_name"] if col in data["plant"].columns), None)
        if plant_name_col:
            scored = scored.merge(data["plant"][["plant_id", plant_name_col]], on="plant_id", how="left")
            scored = scored.rename(columns={plant_name_col: "plant_name"})

    if "product_id" in data["product"].columns:
        product_name_col = next((col for col in ["product_name", "name", "sku_name"] if col in data["product"].columns), None)
        if product_name_col:
            scored = scored.merge(data["product"][["product_id", product_name_col]], on="product_id", how="left")
            scored = scored.rename(columns={product_name_col: "product_name"})

    scored["status_rank"] = scored["recommended_status"].map({status: index for index, status in enumerate(STATUS_ORDER)})
    scored = scored.sort_values(["status_rank", "readiness_score", "lot_id"], ascending=[True, True, True]).drop(
        columns=["status_rank"]
    )
    return scored, data


def apply_filters(scored: pd.DataFrame) -> pd.DataFrame:
    st.sidebar.markdown("### Filters")
    plant_options = sorted(scored["plant_id"].dropna().astype(str).unique().tolist()) if "plant_id" in scored else []
    product_options = sorted(scored["product_id"].dropna().astype(str).unique().tolist()) if "product_id" in scored else []

    selected_plant = st.sidebar.selectbox("Plant", ["All plants"] + plant_options)
    selected_product = st.sidebar.selectbox("Product", ["All products"] + product_options)
    selected_status = st.sidebar.selectbox("Recommended status", ["All statuses"] + STATUS_ORDER)

    filtered = scored.copy()
    if selected_plant != "All plants":
        filtered = filtered[filtered["plant_id"].astype(str) == selected_plant]
    if selected_product != "All products":
        filtered = filtered[filtered["product_id"].astype(str) == selected_product]
    if selected_status != "All statuses":
        filtered = filtered[filtered["recommended_status"] == selected_status]
    return filtered


def add_display_fields(scored: pd.DataFrame) -> pd.DataFrame:
    display = scored.copy()
    display["review_drivers"] = display.apply(review_drivers_for_row, axis=1)
    display["next_best_action"] = display.apply(next_best_action_for_row, axis=1)
    display["owner_role"] = display.apply(owner_role_for_row, axis=1)
    display["expected_release_impact"] = display.apply(expected_release_impact_for_row, axis=1)
    display["priority"] = display["recommended_status"].map({status: index + 1 for index, status in enumerate(STATUS_ORDER)})
    return display


def render_status_badge(status: str) -> str:
    class_name = {
        "READY": "badge-ready",
        "REVIEW": "badge-review",
        "HOLD": "badge-hold",
        "BLOCKED": "badge-blocked",
    }.get(status, "")
    return f"<span class='status-badge {class_name}'>{status}</span>"


def split_items(value: Any) -> list[str]:
    text = str(value or "").strip()
    if not text or text.lower() == "none":
        return []
    return [item.strip() for item in text.split(";") if item.strip()]


def compact_text(value: Any, max_items: int = 2, max_chars: int = 92) -> str:
    items = split_items(value)
    if not items:
        return "No open readiness exceptions"
    text = "; ".join(items[:max_items])
    if len(items) > max_items:
        text = f"{text}; +{len(items) - max_items} more"
    if len(text) > max_chars:
        return f"{text[: max_chars - 1].rstrip()}..."
    return text


def review_drivers_for_row(row: pd.Series) -> str:
    blockers = split_items(row.get("hard_blockers", ""))
    if blockers:
        return "; ".join(blockers)
    penalties = [item.split(" ", 1)[1] if " " in item else item for item in split_items(row.get("penalties", ""))]
    if penalties:
        return "; ".join(penalties)
    return "No open readiness exceptions"


def owner_role_for_row(row: pd.Series) -> str:
    text = f"{row.get('hard_blockers', '')}; {row.get('penalties', '')}; {row.get('evidence_references', '')}".lower()
    if "coa" in text or "supplier" in text:
        return "Supplier Quality"
    if "training" in text:
        return "Training Coordinator"
    if "capa" in text or "deviation" in text or "environmental" in text:
        return "Quality Operations"
    if "batch record" in text:
        return "Manufacturing"
    if "validation" in text or "change" in text:
        return "Validation Lead"
    return "Release Lead"


def next_best_action_for_row(row: pd.Series) -> str:
    text = f"{row.get('hard_blockers', '')}; {row.get('penalties', '')}; {row.get('evidence_references', '')}".lower()
    status = row.get("recommended_status", "")
    if "critical deviation" in text:
        return "Close critical deviation and document QA disposition."
    if "missing coa" in text or "coa" in text:
        return "Obtain COA and complete supplier-quality release check."
    if "incomplete batch record" in text or "batch record" in text:
        return "Complete batch record review and resolve missing entries."
    if "environmental" in text:
        return "Complete EM investigation and QA impact assessment."
    if "validation" in text or "change" in text:
        return "Review validation-change impact and confirm release applicability."
    if "training" in text:
        return "Close required training records for affected roles."
    if "supplier" in text:
        return "Perform supplier-risk review and document release rationale."
    if "qa review" in text:
        return "Complete QA review and capture release decision."
    if status == "READY":
        return "Prepare final QA release sign-off."
    return "Review readiness evidence and assign accountable owner."


def expected_release_impact_for_row(row: pd.Series) -> str:
    status = row.get("recommended_status", "")
    if status == "BLOCKED":
        return "Release blocked until hard blocker closure."
    if status == "HOLD":
        return "Likely release delay without owner action."
    if status == "REVIEW":
        return "Release possible after QA review."
    return "No material release delay expected."


ACTION_LIBRARY = [
    {
        "action_type": "Resolve missing COA issues",
        "checkbox_label": "Resolve all missing COA issues",
        "owner_role": "Supplier Quality",
        "evidence_basis": "Lot issue flags and COA evidence references",
        "recommended_first_step": "Request missing COAs from suppliers and attach QA-reviewed certificates to impacted lots.",
    },
    {
        "action_type": "Complete incomplete batch records",
        "checkbox_label": "Complete all incomplete batch records",
        "owner_role": "Manufacturing",
        "evidence_basis": "Lot issue flags and batch-record readiness blockers",
        "recommended_first_step": "Assign manufacturing owners to complete missing batch-record entries and route to QA review.",
    },
    {
        "action_type": "Close open critical deviations",
        "checkbox_label": "Close all open critical deviations",
        "owner_role": "Quality Operations",
        "evidence_basis": "Open critical deviation records linked to lots",
        "recommended_first_step": "Prioritize critical deviation investigations and document QA disposition for release impact.",
    },
    {
        "action_type": "Complete overdue validation training",
        "checkbox_label": "Complete overdue training linked to validation-required changes",
        "owner_role": "Training Coordinator",
        "evidence_basis": "Overdue incomplete training linked to open validation-required changes",
        "recommended_first_step": "Schedule overdue role-based training for affected plant/product change controls.",
    },
    {
        "action_type": "Approve validation-required changes",
        "checkbox_label": "Approve or disposition open validation-required changes",
        "owner_role": "Validation Lead",
        "evidence_basis": "Open validation-required change controls affecting plant/product release",
        "recommended_first_step": "Hold change board review and record approval, disposition, or release applicability decision.",
    },
    {
        "action_type": "Downgrade high supplier risk",
        "checkbox_label": "Downgrade high supplier risk to medium after supplier review",
        "owner_role": "Supplier Quality",
        "evidence_basis": "High-risk supplier tier on lot supplier records",
        "recommended_first_step": "Complete supplier-risk review and document controlled downgrade rationale.",
    },
]


def status_counts(scored: pd.DataFrame) -> pd.Series:
    return scored["recommended_status"].value_counts().reindex(STATUS_ORDER, fill_value=0)


def remove_issue_flag_text(value: Any, patterns: list[str]) -> Any:
    if pd.isna(value) or str(value).strip() == "":
        return value
    parts = [part.strip() for part in str(value).replace("|", ";").split(";") if part.strip()]
    kept = [part for part in parts if not any(text_contains(part, pattern) for pattern in patterns)]
    return ";".join(kept) if kept else pd.NA


def copy_operational_data(data: dict[str, pd.DataFrame]) -> dict[str, pd.DataFrame]:
    return {name: frame.copy() for name, frame in data.items()}


def apply_intervention(data: dict[str, pd.DataFrame], action_type: str) -> dict[str, pd.DataFrame]:
    projected = copy_operational_data(data)

    if action_type == "Resolve missing COA issues" and not projected["lot"].empty and "issue_flags" in projected["lot"].columns:
        projected["lot"]["issue_flags"] = projected["lot"]["issue_flags"].apply(
            lambda value: remove_issue_flag_text(value, ["missing coa", "coa missing", "certificate of analysis"])
        )

    elif action_type == "Complete incomplete batch records" and not projected["lot"].empty and "issue_flags" in projected["lot"].columns:
        projected["lot"]["issue_flags"] = projected["lot"]["issue_flags"].apply(
            lambda value: remove_issue_flag_text(value, ["incomplete batch", "batch record"])
        )

    elif action_type == "Close open critical deviations" and not projected["deviation"].empty:
        deviations = projected["deviation"]
        severity_col = next((col for col in ["severity", "deviation_severity", "classification"] if col in deviations.columns), None)
        status_col = next((col for col in ["status", "deviation_status"] if col in deviations.columns), None)
        if severity_col and status_col:
            mask = deviations[severity_col].astype(str).str.lower().str.contains("critical") & deviations[status_col].apply(is_open)
            projected["deviation"].loc[mask, status_col] = "Closed"

    elif action_type == "Complete overdue validation training" and not projected["training_record"].empty:
        training = projected["training_record"]
        changes = projected["change_control"]
        linked_change_ids: set[str] = set()
        if not changes.empty:
            change_status = next((col for col in ["status", "change_status"] if col in changes.columns), None)
            validation_col = next(
                (col for col in ["validation_required", "requires_validation", "validation_required_flag"] if col in changes.columns),
                None,
            )
            open_changes = changes.copy()
            if change_status:
                open_changes = open_changes.loc[open_changes[change_status].apply(is_open).astype(bool)]
            if validation_col:
                open_changes = open_changes.loc[open_changes[validation_col].apply(is_yes).astype(bool)]
            if "change_id" in open_changes.columns:
                linked_change_ids = set(open_changes["change_id"].astype(str))
        change_col = next((col for col in ["change_control_id", "change_id"] if col in training.columns), None)
        status_col = next((col for col in ["status", "training_status", "completion_status"] if col in training.columns), None)
        overdue_col = next((col for col in ["overdue", "is_overdue", "overdue_flag"] if col in training.columns), None)
        if change_col and status_col and overdue_col:
            mask = (
                training[change_col].astype(str).isin(linked_change_ids)
                & training[overdue_col].apply(is_yes)
                & training[status_col].astype(str).str.lower().isin(["pending", "incomplete", "overdue", "not started"])
            )
            projected["training_record"].loc[mask, status_col] = "Completed"
            projected["training_record"].loc[mask, overdue_col] = False

    elif action_type == "Approve validation-required changes" and not projected["change_control"].empty:
        changes = projected["change_control"]
        status_col = next((col for col in ["status", "change_status"] if col in changes.columns), None)
        validation_col = next(
            (col for col in ["validation_required", "requires_validation", "validation_required_flag"] if col in changes.columns),
            None,
        )
        if status_col:
            mask = changes[status_col].apply(is_open).astype(bool)
            if validation_col:
                mask = mask & changes[validation_col].apply(is_yes).astype(bool)
                projected["change_control"].loc[mask, validation_col] = False
            projected["change_control"].loc[mask, status_col] = "Closed"

    elif action_type == "Downgrade high supplier risk" and not projected["supplier"].empty:
        suppliers = projected["supplier"]
        risk_col = next((col for col in ["risk_level", "supplier_risk", "risk_tier"] if col in suppliers.columns), None)
        if risk_col:
            mask = suppliers[risk_col].astype(str).str.upper().eq("HIGH")
            projected["supplier"].loc[mask, risk_col] = "Medium"

    return projected


def score_from_data(data: dict[str, pd.DataFrame]) -> pd.DataFrame:
    lots = data["lot"]
    if lots.empty:
        return pd.DataFrame()
    scored_rows = [
        score_lot(row, data["supplier"], data["deviation"], data["capa"], data["change_control"], data["training_record"])
        for _, row in lots.iterrows()
    ]
    scored = pd.DataFrame(scored_rows)
    scored["priority"] = scored["recommended_status"].map({status: index + 1 for index, status in enumerate(STATUS_ORDER)})
    return scored.sort_values(["priority", "readiness_score", "lot_id"]).drop(columns=["priority"])


def project_with_actions(data: dict[str, pd.DataFrame], action_types: list[str]) -> pd.DataFrame:
    projected = copy_operational_data(data)
    for action_type in action_types:
        projected = apply_intervention(projected, action_type)
    return score_from_data(projected)


def action_type_for_row(row: pd.Series) -> str:
    text = f"{row.get('hard_blockers', '')}; {row.get('penalties', '')}; {row.get('evidence_references', '')}".lower()
    if "missing coa" in text or "coa" in text:
        return "Resolve missing COA issues"
    if "incomplete batch record" in text or "batch record" in text:
        return "Complete incomplete batch records"
    if "critical deviation" in text:
        return "Close open critical deviations"
    if "training" in text:
        return "Complete overdue validation training"
    if "validation" in text or "change" in text:
        return "Approve validation-required changes"
    if "high-risk supplier" in text or "supplier" in text:
        return "Downgrade high supplier risk"
    return "Complete QA review"


def action_metadata(action_type: str) -> dict[str, str]:
    return next((action for action in ACTION_LIBRARY if action["action_type"] == action_type), {})


def blockers_resolved_by_actions(action_types: list[str]) -> list[str]:
    mapping = {
        "Resolve missing COA issues": ["Missing COA"],
        "Complete incomplete batch records": ["Incomplete batch record"],
        "Close open critical deviations": ["Open critical deviation"],
        "Complete overdue validation training": [
            "Incomplete overdue training linked to open validation-required change",
        ],
        "Approve validation-required changes": ["Open validation-required change effective for lot"],
        "Downgrade high supplier risk": ["High supplier risk score pressure"],
    }
    resolved: list[str] = []
    for action_type in action_types:
        resolved.extend(mapping.get(action_type, []))
    return resolved


def blocker_counts(scored: pd.DataFrame) -> pd.Series:
    blockers = scored["hard_blockers"].str.split("; ").explode()
    blockers = blockers[blockers.notna() & (blockers != "None")]
    return blockers.value_counts()


def simulation_explanation(
    selected_actions: list[str],
    baseline: pd.DataFrame,
    projected: pd.DataFrame,
) -> dict[str, Any]:
    baseline_by_lot = baseline.set_index("lot_id")
    projected_by_lot = projected.set_index("lot_id")
    blocked_before = set(baseline.loc[baseline["recommended_status"].eq("BLOCKED"), "lot_id"].astype(str))
    blocked_after = set(projected.loc[projected["recommended_status"].eq("BLOCKED"), "lot_id"].astype(str))
    moved_out = blocked_before - blocked_after
    still_blocked = blocked_before & blocked_after

    remaining_counts = blocker_counts(projected)
    remaining_blockers = remaining_counts.head(8)
    resolved = blockers_resolved_by_actions(selected_actions)
    baseline_counts = status_counts(baseline)
    projected_counts = status_counts(projected)
    blocked_reduction = int(baseline_counts["BLOCKED"] - projected_counts["BLOCKED"])
    ready_increase = int(projected_counts["READY"] - baseline_counts["READY"])

    reasons: list[str] = []
    for lot_id in sorted(still_blocked):
        blockers = split_items(projected_by_lot.loc[lot_id, "hard_blockers"])
        if blockers:
            reasons.extend(blockers)
    reason_counts = pd.Series(reasons).value_counts() if reasons else pd.Series(dtype="int64")

    if not selected_actions:
        explanation = "Select one or more interventions to see why the projected release posture changes."
    elif len(moved_out) == 0:
        top_reasons = ", ".join(reason_counts.head(4).index.tolist()) or "other hard blockers"
        explanation = (
            f"The selected intervention does not reduce BLOCKED lots because affected lots still have "
            f"other hard blockers such as {top_reasons}."
        )
    else:
        selected_phrases = [executive_intervention_phrase(action_type) for action_type in selected_actions]
        selected_text = (
            " and ".join(selected_phrases)
            if len(selected_phrases) <= 2
            else ", ".join(selected_phrases[:-1]) + f", and {selected_phrases[-1]}"
        )
        top_remaining = ", ".join(remaining_blockers.head(3).index.tolist()) or "no remaining hard blockers"
        next_priority = recommended_next_priority(projected)["priority"]
        explanation = (
            f"{selected_text} is projected to move {blocked_reduction} lots out of BLOCKED and increase READY lots "
            f"by {ready_increase}. Remaining blocked lots are primarily constrained by {top_remaining}. "
            f"The next operational priority should be {next_priority.lower()}."
        )

    return {
        "selected_interventions": selected_actions or ["No interventions selected"],
        "blockers_resolved": resolved or ["None selected"],
        "remaining_blockers": remaining_blockers,
        "why_lots_remain_blocked": reason_counts.head(8),
        "summary": explanation,
        "blocked_reduction": blocked_reduction,
        "ready_increase": ready_increase,
    }


def executive_intervention_phrase(action_type: str) -> str:
    phrases = {
        "Resolve missing COA issues": "Resolving missing COA issues",
        "Complete incomplete batch records": "completing incomplete batch records",
        "Close open critical deviations": "closing open critical deviations",
        "Complete overdue validation training": "completing overdue validation training",
        "Approve validation-required changes": "dispositioning validation-required changes",
        "Downgrade high supplier risk": "downgrading high supplier risk after supplier review",
    }
    return phrases.get(action_type, action_type)


def recommended_next_priority(projected: pd.DataFrame) -> dict[str, str]:
    remaining = blocker_counts(projected)
    if remaining.empty:
        return {
            "priority": "Proceed with QA release review",
            "rationale": "No hard blockers remain in the current projection.",
            "largest_blocker": "None",
        }

    largest = str(remaining.index[0])
    if largest == "Incomplete batch record":
        priority = "Complete incomplete batch records"
    elif largest == "Open critical deviation":
        priority = "Close or disposition critical deviations"
    elif largest == "Failed environmental monitoring":
        priority = "Investigate and disposition failed environmental monitoring events"
    elif largest == "Missing COA":
        priority = "Resolve missing COA issues"
    elif largest == "Open validation-required change effective for lot":
        priority = "Approve or disposition validation-required changes"
    else:
        priority = "Proceed with QA release review"

    return {
        "priority": priority,
        "rationale": "This is the largest remaining release constraint after the selected interventions.",
        "largest_blocker": largest,
    }


def action_impact_table(baseline: pd.DataFrame, data: dict[str, pd.DataFrame]) -> pd.DataFrame:
    rows = []
    baseline_by_lot = baseline.set_index("lot_id")
    baseline_blocked = int((baseline["recommended_status"] == "BLOCKED").sum())
    baseline_ready = int((baseline["recommended_status"] == "READY").sum())
    for action in ACTION_LIBRARY:
        projected = project_with_actions(data, [action["action_type"]])
        projected_by_lot = projected.set_index("lot_id")
        changed_lots = baseline_by_lot.index[
            (baseline_by_lot["readiness_score"] != projected_by_lot.loc[baseline_by_lot.index, "readiness_score"])
            | (baseline_by_lot["recommended_status"] != projected_by_lot.loc[baseline_by_lot.index, "recommended_status"])
        ]
        projected_blocked = int((projected["recommended_status"] == "BLOCKED").sum())
        projected_ready = int((projected["recommended_status"] == "READY").sum())
        rows.append(
            {
                "action_type": action["action_type"],
                "owner_role": action["owner_role"],
                "affected_lot_count": len(changed_lots),
                "projected_blocked_reduction": baseline_blocked - projected_blocked,
                "projected_ready_increase": projected_ready - baseline_ready,
                "evidence_basis": action["evidence_basis"],
                "recommended_first_step": action["recommended_first_step"],
            }
        )
    ranking = pd.DataFrame(rows).sort_values(
        ["projected_blocked_reduction", "projected_ready_increase", "affected_lot_count"],
        ascending=[False, False, False],
    )
    ranking.insert(0, "priority_rank", range(1, len(ranking) + 1))
    return ranking


def recommended_decision_for_row(row: pd.Series) -> str:
    status = row.get("recommended_status", "")
    if status == "READY":
        return "Release"
    if status == "REVIEW":
        return "QA Review"
    if status == "HOLD":
        return "Hold"
    return "Escalate"


def rationale_for_row(row: pd.Series) -> str:
    blockers = split_items(row.get("hard_blockers", ""))
    if blockers:
        return f"Hard blocker present: {compact_text(row.get('hard_blockers'), max_items=2)}."
    if row.get("recommended_status") == "READY":
        return "No open readiness exceptions identified by the baseline rules."
    return f"Review driver present: {compact_text(row.get('penalties'), max_items=2)}."


def add_decision_fields(scored: pd.DataFrame, data: dict[str, pd.DataFrame]) -> pd.DataFrame:
    queue = add_display_fields(scored)
    queue["recommended_decision"] = queue.apply(recommended_decision_for_row, axis=1)
    queue["required_action"] = queue.apply(action_type_for_row, axis=1)
    queue["current_score"] = queue["readiness_score"]
    queue["release_impact"] = queue["expected_release_impact"]
    queue["rationale"] = queue.apply(rationale_for_row, axis=1)

    projected_scores: dict[str, pd.Series] = {}
    for action_type in queue["required_action"].unique():
        if action_type in [action["action_type"] for action in ACTION_LIBRARY]:
            projected_scores[action_type] = project_with_actions(data, [action_type]).set_index("lot_id")["readiness_score"]

    def projected_score(row: pd.Series) -> int:
        scores = projected_scores.get(row["required_action"])
        if scores is None or row["lot_id"] not in scores.index:
            return int(row["current_score"])
        return int(scores.loc[row["lot_id"]])

    queue["projected_score_after_action"] = queue.apply(projected_score, axis=1)
    return queue


def render_header() -> None:
    st.markdown(
        f"""
        <div class="executive-header">
            <div class="synthetic-label">SYNTHETIC DEMO DATA ONLY</div>
            <h1>{APP_TITLE}</h1>
            <div class="small-muted">Release readiness, quality exceptions, and action prioritization for manufacturing operations.</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_kpis(scored: pd.DataFrame) -> None:
    total_lots = len(scored)
    ready_count = int((scored["recommended_status"] == "READY").sum()) if total_lots else 0
    blocked_count = int((scored["recommended_status"] == "BLOCKED").sum()) if total_lots else 0
    average_score = scored["readiness_score"].mean() if total_lots else 0

    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Total lots", f"{total_lots:,}")
    col2.metric("Percent ready", f"{(ready_count / total_lots * 100) if total_lots else 0:.1f}%")
    col3.metric("Blocked lots", f"{blocked_count:,}")
    col4.metric("Average score", f"{average_score:.1f}")


def executive_overview(scored: pd.DataFrame) -> None:
    display = add_display_fields(scored)
    st.info(
        "This app is not intended to replace QA decision-making. It prioritizes release blockers, explains evidence, "
        "and helps QA/Ops decide where to act first."
    )
    render_kpis(display)

    left, right = st.columns([1, 2])
    with left:
        st.markdown("#### Recommended Status Counts")
        counts = scored["recommended_status"].value_counts().reindex(STATUS_ORDER, fill_value=0)
        max_count = max(int(counts.max()), 1)
        for status, count in counts.items():
            width = int((int(count) / max_count) * 100)
            st.markdown(
                f"""
                <div style="margin:0.4rem 0 0.65rem 0;">
                    <div style="display:flex;justify-content:space-between;font-size:0.82rem;color:#344054;">
                        <strong>{status}</strong><span>{int(count)}</span>
                    </div>
                    <div style="height:0.55rem;background:#f2f4f7;border-radius:999px;border:1px solid #e4e7ec;">
                        <div style="height:100%;width:{width}%;background:{STATUS_COLORS[status]};border-radius:999px;"></div>
                    </div>
                </div>
                """,
                unsafe_allow_html=True,
            )
        st.markdown("#### AI Insight")
        blocked_count = int((display["recommended_status"] == "BLOCKED").sum())
        st.markdown(
            f"""
            <div class="insight-panel">
            <strong>Current Release Posture:</strong> {blocked_count} of {len(display)} lots are blocked by hard release blockers.<br><br>
            <strong>Top Risk Drivers:</strong> missing COA, incomplete batch records, critical deviations, and failed environmental monitoring.<br><br>
            <strong>Recommended Next 3 Actions:</strong><br>
            1. Resolve missing COA and incomplete batch records for blocked lots.<br>
            2. Close or disposition critical deviations tied to release-blocked lots.<br>
            3. Review HOLD lots driven by supplier risk or validation-change pressure.
            </div>
            """,
            unsafe_allow_html=True,
        )
    with right:
        st.markdown("#### Top 5 Highest-Risk Lots")
        top_risk = display.sort_values(["priority", "readiness_score", "lot_id"]).head(5).copy()
        top_risk["review_drivers"] = top_risk["review_drivers"].apply(lambda value: compact_text(value, max_items=2))
        top_risk["next_best_action"] = top_risk["next_best_action"].apply(lambda value: compact_text(value, max_items=1, max_chars=86))
        st.dataframe(
            top_risk[
                [
                    "lot_id",
                    "plant_id",
                    "product_id",
                    "supplier_risk",
                    "readiness_score",
                    "recommended_status",
                    "review_drivers",
                    "next_best_action",
                ]
            ],
            width="stretch",
            hide_index=True,
            height=215,
        )
        st.markdown("#### Plant-Level Risk Summary")
        plant_summary = (
            display.assign(blocked=display["recommended_status"].eq("BLOCKED"))
            .groupby("plant_id", as_index=False)
            .agg(
                total_lots=("lot_id", "count"),
                blocked_lots=("blocked", "sum"),
                average_score=("readiness_score", "mean"),
            )
        )
        plant_summary["average_score"] = plant_summary["average_score"].round(1)
        st.dataframe(
            plant_summary.sort_values(["blocked_lots", "average_score"], ascending=[False, True]),
            width="stretch",
            hide_index=True,
            height=150,
        )


def lot_drilldown(scored: pd.DataFrame) -> None:
    display = add_display_fields(scored).sort_values(["readiness_score", "lot_id"], ascending=[True, True])
    st.markdown("#### Lot Drilldown")
    st.dataframe(
        display[
            [
                "lot_id",
                "plant_id",
                "product_id",
                "supplier_id",
                "supplier_risk",
                "readiness_score",
                "recommended_status",
                "hard_blockers",
                "review_drivers",
                "next_best_action",
            ]
        ],
        width="stretch",
        hide_index=True,
        height=410,
    )

    lot_ids = display["lot_id"].astype(str).tolist()
    selected_lot = st.selectbox("Select lot", lot_ids)
    lot = display[display["lot_id"].astype(str) == selected_lot].iloc[0]

    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Readiness score", int(lot["readiness_score"]))
    col2.markdown(f"**Recommended status**<br>{render_status_badge(lot['recommended_status'])}", unsafe_allow_html=True)
    col3.metric("Plant", lot.get("plant_name", lot.get("plant_id", "")))
    col4.metric("Product", lot.get("product_name", lot.get("product_id", "")))

    st.divider()
    left, right = st.columns(2)
    with left:
        st.markdown("#### Release Drivers")
        st.markdown(f"**Hard blockers:** {lot['hard_blockers']}")
        st.markdown(f"**Review drivers:** {lot['review_drivers']}")
        st.markdown(f"**Next best action:** {lot['next_best_action']}")
    with right:
        st.markdown("#### Evidence References")
        for item in str(lot["evidence_references"]).split("; "):
            st.write(f"- {item}")

    st.markdown("#### Decision Rationale")
    blocker_type = "Hard blocker" if split_items(lot.get("hard_blockers", "")) else "Review driver"
    rationale_cols = st.columns(2)
    with rationale_cols[0]:
        st.markdown(f"**Current recommendation:** {render_status_badge(lot['recommended_status'])}", unsafe_allow_html=True)
        st.markdown(f"**Why the system recommends it:** {rationale_for_row(lot)}")
        st.markdown(f"**Issue type:** {blocker_type}")
    with rationale_cols[1]:
        st.markdown(f"**What evidence supports it:** {compact_text(lot.get('evidence_references'), max_items=3, max_chars=220)}")
        st.markdown(f"**What action would change it:** {lot['next_best_action']}")


def control_tower(data: dict[str, pd.DataFrame]) -> None:
    st.markdown("#### Control Tower")
    deviations = data["deviation"]
    capas = data["capa"]
    changes = data["change_control"]
    training = data["training_record"]

    col1, col2, col3, col4 = st.columns(4)
    open_deviations = deviations.copy()
    if not open_deviations.empty and "status" in open_deviations.columns:
        open_deviations = open_deviations.loc[open_deviations["status"].apply(is_open).astype(bool)]
    overdue_capas = capas.copy()
    if not overdue_capas.empty and "is_overdue" in overdue_capas.columns:
        overdue_capas = overdue_capas.loc[overdue_capas["is_overdue"].apply(is_yes).astype(bool)]
    open_changes = changes.copy()
    if not open_changes.empty and "status" in open_changes.columns:
        open_changes = open_changes.loc[open_changes["status"].apply(is_open).astype(bool)]
    if not open_changes.empty and "validation_required" in open_changes.columns:
        open_changes = open_changes.loc[open_changes["validation_required"].apply(is_yes).astype(bool)]
    incomplete_training = training.copy()
    if not incomplete_training.empty and "completion_status" in incomplete_training.columns:
        incomplete_training = incomplete_training.loc[
            incomplete_training["completion_status"].astype(str).str.lower().isin(["pending", "incomplete", "overdue", "not started"])
        ]

    col1.metric("Open deviations", len(open_deviations))
    col2.metric("Overdue CAPAs", len(overdue_capas))
    col3.metric("Validation changes", len(open_changes))
    col4.metric("Incomplete training", len(incomplete_training))

    left, right = st.columns(2)
    with left:
        st.markdown("##### Open Deviations by Severity")
        if open_deviations.empty or "severity" not in open_deviations.columns:
            st.info("No open deviation data loaded.")
        else:
            severity_summary = open_deviations["severity"].value_counts().reset_index()
            severity_summary.columns = ["severity", "open_count"]
            st.dataframe(severity_summary, width="stretch", hide_index=True, height=140)
            st.dataframe(open_deviations, width="stretch", hide_index=True, height=220)

        st.markdown("##### Open Validation-Required Changes")
        if open_changes.empty:
            st.info("No open validation-required changes.")
        else:
            st.dataframe(open_changes, width="stretch", hide_index=True, height=220)

    with right:
        st.markdown("##### Overdue CAPAs")
        if overdue_capas.empty:
            st.info("No overdue CAPAs.")
        else:
            st.dataframe(overdue_capas, width="stretch", hide_index=True, height=200)

        st.markdown("##### Incomplete / Overdue Training")
        if incomplete_training.empty:
            st.info("No incomplete training records.")
        else:
            st.dataframe(incomplete_training, width="stretch", hide_index=True, height=200)

        st.markdown("##### Affected Products and Plants")
        affected_frames = []
        for frame in [open_deviations, overdue_capas, open_changes, incomplete_training]:
            cols = [col for col in ["plant_id", "product_id"] if col in frame.columns]
            if cols:
                affected_frames.append(frame[cols])
        if affected_frames:
            affected = pd.concat(affected_frames, ignore_index=True).drop_duplicates()
            st.dataframe(affected.sort_values([col for col in ["plant_id", "product_id"] if col in affected.columns]), width="stretch", hide_index=True, height=160)
        else:
            st.info("No affected product or plant records.")


def action_queue(scored: pd.DataFrame, data: dict[str, pd.DataFrame]) -> None:
    st.markdown("#### Action Queue")
    queue = add_decision_fields(scored, data)
    queue = queue.sort_values(["priority", "readiness_score", "lot_id"])
    st.dataframe(
        queue[
            [
                "priority",
                "lot_id",
                "recommended_decision",
                "required_action",
                "owner_role",
                "evidence_references",
                "current_score",
                "projected_score_after_action",
                "release_impact",
                "rationale",
            ]
        ],
        width="stretch",
        hide_index=True,
        height=560,
    )


def decision_simulator(scored: pd.DataFrame, data: dict[str, pd.DataFrame]) -> None:
    st.markdown("#### Decision Simulator")
    st.caption("Simulations are in-memory projections only. Source CSV files are not modified.")

    baseline = scored.copy()
    visible_lots = set(baseline["lot_id"].astype(str))
    action_cols = st.columns(2)
    selected_actions: list[str] = []
    default_actions = {
        "Resolve missing COA issues",
        "Approve validation-required changes",
    }
    for index, action in enumerate(ACTION_LIBRARY):
        with action_cols[index % 2]:
            if st.checkbox(
                action["checkbox_label"],
                value=action["action_type"] in default_actions,
                key=f"sim_{action['action_type']}",
            ):
                selected_actions.append(action["action_type"])

    projected = project_with_actions(data, selected_actions) if selected_actions else baseline.copy()
    projected = projected[projected["lot_id"].astype(str).isin(visible_lots)]

    baseline_counts = status_counts(baseline)
    projected_counts = status_counts(projected)
    comparison = pd.DataFrame(
        {
            "recommended_status": STATUS_ORDER,
            "baseline_count": [int(baseline_counts[status]) for status in STATUS_ORDER],
            "projected_count": [int(projected_counts[status]) for status in STATUS_ORDER],
            "net_change": [int(projected_counts[status] - baseline_counts[status]) for status in STATUS_ORDER],
        }
    )

    blocked_before = int(baseline_counts["BLOCKED"])
    blocked_after = int(projected_counts["BLOCKED"])
    ready_before = int(baseline_counts["READY"])
    ready_after = int(projected_counts["READY"])
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Blocked before", blocked_before)
    col2.metric("Blocked after", blocked_after)
    col3.metric("Moved out of BLOCKED", max(0, blocked_before - blocked_after))
    col4.metric("READY increase", ready_after - ready_before)

    top_left, top_right = st.columns([1.15, 1])
    with top_left:
        st.markdown("##### Before vs After Counts")
        st.dataframe(comparison, width="stretch", hide_index=True, height=180)
    with top_right:
        next_priority = recommended_next_priority(projected)
        st.markdown("##### Recommended Next Priority")
        st.markdown(
            f"""
            <div class="insight-panel">
            <strong>{next_priority["priority"]}</strong><br><br>
            <span class="small-muted">Largest remaining blocker: {next_priority["largest_blocker"]}</span><br><br>
            {next_priority["rationale"]}
            </div>
            """,
            unsafe_allow_html=True,
        )

    explanation = simulation_explanation(selected_actions, baseline, projected)
    st.markdown("##### Simulation Explanation")
    st.markdown(
        f"""
        <div class="insight-panel">
        <strong>Executive Interpretation:</strong> {explanation["summary"]}
        </div>
        """,
        unsafe_allow_html=True,
    )
    exp_col1, exp_col2 = st.columns(2)
    with exp_col1:
        st.markdown("**Selected interventions**")
        st.write(", ".join(explanation["selected_interventions"]))
        st.markdown("**Blockers resolved by selected interventions**")
        st.write(", ".join(explanation["blockers_resolved"]))
    with exp_col2:
        st.markdown("**Remaining blockers after simulation**")
        if explanation["remaining_blockers"].empty:
            st.success("No hard blockers remain in the current projection.")
        else:
            remaining = explanation["remaining_blockers"].reset_index()
            remaining.columns = ["remaining_blocker", "lot_count"]
            st.dataframe(remaining, width="stretch", hide_index=True, height=180)
        st.markdown("**Why lots remain blocked**")
        if explanation["why_lots_remain_blocked"].empty:
            st.write("No baseline-blocked lots remain blocked under the current projection.")
        else:
            reasons = explanation["why_lots_remain_blocked"].reset_index()
            reasons.columns = ["remaining_reason", "lot_count"]
            st.dataframe(reasons, width="stretch", hide_index=True, height=180)

    st.markdown("##### Next Best Action Ranking")
    ranking = action_impact_table(baseline, data)
    ranking = ranking.rename(
        columns={
            "priority_rank": "Priority",
            "action_type": "Recommended Intervention",
            "owner_role": "Primary Owner",
            "affected_lot_count": "Lots Affected",
            "projected_blocked_reduction": "Projected Blocked Reduction",
            "projected_ready_increase": "Projected READY Increase",
            "evidence_basis": "Why This Matters",
            "recommended_first_step": "Recommended First Step",
        }
    )
    st.dataframe(
        ranking[
            [
                "Priority",
                "Recommended Intervention",
                "Primary Owner",
                "Lots Affected",
                "Projected Blocked Reduction",
                "Projected READY Increase",
                "Why This Matters",
                "Recommended First Step",
            ]
        ],
        width="stretch",
        hide_index=True,
        height=330,
    )


def architecture_data_model() -> None:
    st.markdown("#### Architecture / Data Model")
    st.write(
        "This page shows how fragmented manufacturing and quality records can be translated into a common "
        "operating model for release-readiness decisions."
    )

    st.markdown("##### Source Systems")
    source_systems = pd.DataFrame(
        [
            {"source_system": "ERP / MES", "example_data": "lot records, product, batch record status, target release date"},
            {"source_system": "QMS / eQMS", "example_data": "deviations, CAPAs, change controls, release dispositions"},
            {"source_system": "LMS", "example_data": "training records and completion status"},
            {"source_system": "Supplier Quality", "example_data": "supplier risk, COA status, supplier-related release blockers"},
            {"source_system": "LIMS / Environmental Monitoring", "example_data": "environmental monitoring pass/fail status"},
            {"source_system": "Manual QA Review", "example_data": "pending QA review, disposition notes, escalation rationale"},
        ]
    )
    st.dataframe(source_systems, width="stretch", hide_index=True, height=250)

    st.markdown("##### Canonical Objects")
    canonical_objects = pd.DataFrame(
        [
            {
                "object": "Plant",
                "object_definition": "Manufacturing or quality site where lots are produced, tested, or released.",
                "primary_key": "plant_id",
                "release_readiness_value": "Scopes deviations, changes, training, and operational ownership.",
            },
            {
                "object": "Product",
                "object_definition": "Manufactured item or SKU under release evaluation.",
                "primary_key": "product_id",
                "release_readiness_value": "Links lots to product-specific validation and release expectations.",
            },
            {
                "object": "Supplier",
                "object_definition": "External provider of materials, testing, logistics, or services.",
                "primary_key": "supplier_id",
                "release_readiness_value": "Adds supplier risk and COA readiness to lot disposition.",
            },
            {
                "object": "Lot",
                "object_definition": "Batch or lot requiring readiness assessment and release decision.",
                "primary_key": "lot_id",
                "release_readiness_value": "Central object for score, status, evidence, and action queue.",
            },
            {
                "object": "Deviation",
                "object_definition": "Quality exception or process event linked to a lot or plant.",
                "primary_key": "deviation_id",
                "release_readiness_value": "Critical and major deviations drive blockers and review pressure.",
            },
            {
                "object": "CAPA",
                "object_definition": "Corrective or preventive action linked to a quality issue.",
                "primary_key": "capa_id",
                "release_readiness_value": "Overdue CAPAs indicate unresolved quality risk.",
            },
            {
                "object": "Change Control",
                "object_definition": "Controlled manufacturing, process, equipment, packaging, or validation change.",
                "primary_key": "change_id",
                "release_readiness_value": "Open validation-required changes can block affected lots.",
            },
            {
                "object": "Training Record",
                "object_definition": "Role-based training completion evidence for affected products and plants.",
                "primary_key": "training_id",
                "release_readiness_value": "Overdue linked training can block or delay release readiness.",
            },
            {
                "object": "Release Decision",
                "object_definition": "Final or recommended release disposition with rationale and evidence.",
                "primary_key": "lot_id / decision_id",
                "release_readiness_value": "Converts operational evidence into QA/Ops decision outputs.",
            },
        ]
    )
    st.dataframe(canonical_objects, width="stretch", hide_index=True, height=360)

    st.markdown("##### Decision Outputs")
    decision_outputs = pd.DataFrame(
        [
            {"decision_output": "Readiness Score", "description": "Numerical release-readiness score recalculated from operational records."},
            {"decision_output": "Recommended Status", "description": "READY, REVIEW, HOLD, or BLOCKED disposition based on score and hard blockers."},
            {"decision_output": "Hard Blockers", "description": "Release-blocking conditions such as critical deviations, missing COA, incomplete batch record, failed EM, effective validation changes, or linked overdue training."},
            {"decision_output": "Review Drivers", "description": "Non-blocking risk drivers that explain why a lot requires review or hold action."},
            {"decision_output": "Next Best Action", "description": "Operational next step mapped to the highest-value readiness constraint."},
            {"decision_output": "Projected Release Impact", "description": "Expected release consequence if no action is taken or if simulated interventions are applied."},
            {"decision_output": "Decision Rationale", "description": "Plain-language explanation of why the system recommends the current disposition."},
        ]
    )
    st.dataframe(decision_outputs, width="stretch", hide_index=True, height=280)

    st.markdown("##### Workflow Map")
    st.markdown(
        """
        <div class="section-card" style="text-align:center;font-weight:700;color:#344054;">
        Source Systems &rarr; Canonical Objects &rarr; Scoring Logic &rarr; Decision Recommendation &rarr; Action Queue &rarr; Simulation / Next Best Action
        </div>
        """,
        unsafe_allow_html=True,
    )

    left, right = st.columns(2)
    with left:
        st.markdown("##### Deployment Notes")
        st.markdown(
            """
            - This prototype uses synthetic CSVs only.
            - In a real deployment, these data objects would connect to MES, QMS/eQMS, LMS, supplier quality, and environmental monitoring systems.
            - The app supports QA/Ops decision-making but does not replace validated QA release authority.
            - A real deployment would require role-based access, audit trail, validated release procedures, and controlled writeback to source systems.
            """
        )
    with right:
        st.markdown("##### Why This Matters For Deployment")
        st.markdown(
            """
            - It starts from a real operational decision: which lots can release, which are blocked, and what should QA/Ops do first.
            - It identifies relevant datasets and turns them into shared operational objects.
            - It creates role-specific workflows for QA, Operations, Supplier Quality, Training, and Change Control.
            - It supports executive visibility, lot-level evidence, action prioritization, and what-if simulation.
            """
        )


def main() -> None:
    inject_css()
    render_header()

    scored, data = build_scored_table()
    if scored.empty:
        st.warning("Add CSV files to the data folder to populate the dashboard. lot.csv is required.")
        st.stop()

    st.sidebar.markdown("## Command Center")
    st.sidebar.caption(
        "This prototype converts fragmented manufacturing quality records into release-readiness decisions using synthetic data."
    )
    page = st.sidebar.radio(
        "Navigation",
        [
            "Executive Overview",
            "Lot Drilldown",
            "Control Tower",
            "Action Queue",
            "Decision Simulator",
            "Architecture / Data Model",
        ],
    )
    filtered = apply_filters(scored)

    if filtered.empty:
        st.info("No lots match the current filters.")
        st.stop()

    if page == "Executive Overview":
        executive_overview(filtered)
    elif page == "Lot Drilldown":
        lot_drilldown(filtered)
    elif page == "Control Tower":
        control_tower(data)
    elif page == "Decision Simulator":
        decision_simulator(filtered, data)
    elif page == "Architecture / Data Model":
        architecture_data_model()
    else:
        action_queue(filtered, data)


if __name__ == "__main__":
    main()
