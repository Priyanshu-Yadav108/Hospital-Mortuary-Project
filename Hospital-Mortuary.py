# app.py
import os
import uuid
from datetime import datetime, date, time
import pandas as pd
import streamlit as st
from dateutil import tz

# ----------------------------
# Config & Constants
# ----------------------------
DATA_DIR = "data"
CSV_PATH = os.path.join(DATA_DIR, "mortuary_records.csv")

COLUMNS = [
    "record_id",               # UUID
    "body_tag_no",
    "deceased_name",
    "age",
    "sex",                     # Male / Female / Other / Unknown
    "dod_date",                # Date of death (YYYY-MM-DD)
    "tod_time",                # Time of death (HH:MM)
    "cause_of_death",
    "ward_unit",
    "brought_by",
    "admitted_dt",             # Datetime to mortuary ISO string
    "storage_location",        # e.g., Drawer # / Room
    "next_of_kin",
    "next_of_kin_contact",
    "id_docs_seen",            # Yes/No
    "autopsy_required",        # Yes/No/Pending
    "autopsy_date",            # Date or empty
    "release_status",          # In Storage / Released / Transferred
    "released_dt",             # Datetime ISO or empty
    "released_to",
    "remarks",
    "last_updated"             # ISO datetime
]

SEX_OPTIONS = ["Male", "Female", "Other", "Unknown"]
STATUS_OPTIONS = ["In Storage", "Released", "Transferred"]
YN_OPTIONS = ["Yes", "No"]
AUTO_OPTIONS = ["Yes", "No", "Pending"]

# ----------------------------
# Helpers
# ----------------------------
def ensure_storage():
    os.makedirs(DATA_DIR, exist_ok=True)
    if not os.path.exists(CSV_PATH):
        df = pd.DataFrame(columns=COLUMNS)
        df.to_csv(CSV_PATH, index=False)

def load_data() -> pd.DataFrame:
    ensure_storage()
    df = pd.read_csv(CSV_PATH, dtype=str, keep_default_na=False)
    # Normalize missing fields if schema evolves
    for col in COLUMNS:
        if col not in df.columns:
            df[col] = ""
    # Keep only known cols, in order
    df = df[COLUMNS]
    return df

def save_data(df: pd.DataFrame):
    df[COLUMNS].to_csv(CSV_PATH, index=False)

def now_iso():
    return datetime.now(tz.tzlocal()).isoformat(timespec="seconds")

def combine_date_time(d: date | str, t: time | str) -> str:
    if not d:
        return ""
    if isinstance(d, str) and d.strip() == "":
        return ""
    if isinstance(t, str) and t.strip() == "":
        t = "00:00"
    try:
        if isinstance(d, str):
            d_obj = datetime.strptime(d, "%Y-%m-%d").date()
        else:
            d_obj = d
        if isinstance(t, str):
            t_obj = datetime.strptime(t, "%H:%M").time()
        else:
            t_obj = t
        dt = datetime.combine(d_obj, t_obj).astimezone(tz.tzlocal())
        return dt.isoformat(timespec="minutes")
    except Exception:
        return ""

def to_date_str(d: date | None):
    return "" if d is None else d.strftime("%Y-%m-%d")

def to_time_str(t: time | None):
    return "" if t is None else t.strftime("%H:%M")

def validate_required(fields: dict[str, str]) -> list[str]:
    errors = []
    for k, v in fields.items():
        if (v is None) or (isinstance(v, str) and v.strip() == ""):
            errors.append(k)
    return errors

# ----------------------------
# UI
# ----------------------------
st.set_page_config(page_title="Hospital Mortuary Records", page_icon="🏥", layout="wide")
st.title("🏥 Hospital Mortuary Record System")
st.caption("Streamlit + pandas · Local CSV storage")

with st.sidebar:
    st.header("⚙️ Controls")
    st.write("Data file:", f"`{CSV_PATH}`")
    if st.button("Create Backup (CSV)"):
        df_bk = load_data().copy()
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_path = os.path.join(DATA_DIR, f"mortuary_records_backup_{ts}.csv")
        df_bk.to_csv(backup_path, index=False)
        st.success(f"Backup created: {backup_path}")

    uploaded = st.file_uploader("Restore/Import from CSV", type=["csv"], help="Imports and overwrites by matching columns.")
    if uploaded is not None:
        try:
            df_imp = pd.read_csv(uploaded, dtype=str, keep_default_na=False)
            # Align columns
            for col in COLUMNS:
                if col not in df_imp.columns:
                    df_imp[col] = ""
            df_imp = df_imp[COLUMNS]
            save_data(df_imp)
            st.success("Import complete. Reload the page if needed.")
        except Exception as e:
            st.error(f"Import failed: {e}")

tab_add, tab_browse, tab_edit = st.tabs(["➕ Add Record", "🔎 Browse & Filter", "✏️ Edit / Update"])

# ----------------------------
# Add Record
# ----------------------------
with tab_add:
    st.subheader("Add New Mortuary Record")

    col1, col2, col3 = st.columns(3)
    with col1:
        deceased_name = st.text_input("Deceased Name*")
        age = st.text_input("Age", placeholder="e.g., 65")
        sex = st.selectbox("Sex", options=SEX_OPTIONS, index=3)  # default Unknown
        body_tag_no = st.text_input("Body Tag Number*")
        ward_unit = st.text_input("Ward / Unit")
    with col2:
        dod = st.date_input("Date of Death*", value=date.today())
        tod = st.time_input("Time of Death", value=time(0, 0))
        cause = st.text_input("Cause of Death")
        brought_by = st.text_input("Brought By")
        storage_location = st.text_input("Storage Location*", placeholder="e.g., Drawer 3 / Cold Room B")
    with col3:
        nok = st.text_input("Next of Kin")
        nok_contact = st.text_input("Next of Kin Contact")
        id_docs = st.selectbox("ID Documents Verified?", options=YN_OPTIONS, index=1)
        autopsy_required = st.selectbox("Autopsy Required?", options=AUTO_OPTIONS, index=2)
        autopsy_date = st.date_input("Autopsy Date (if set)", value=None, format="YYYY-MM-DD") if st.checkbox("Set autopsy date?") else None

    remarks = st.text_area("Remarks")

    # Admission datetime: default now
    admitted_date = st.date_input("Admitted to Mortuary (Date)", value=date.today())
    admitted_time = st.time_input("Admitted to Mortuary (Time)", value=datetime.now().time().replace(second=0, microsecond=0))

    if st.button("Save Record", type="primary"):
        # Validate
        req = {
            "Deceased Name": deceased_name,
            "Body Tag Number": body_tag_no,
            "Date of Death": dod,
            "Storage Location": storage_location,
        }
        missing = validate_required(req)
        if missing:
            st.error(f"Please fill required fields: {', '.join(missing)}")
        else:
            df = load_data()
            record = {
                "record_id": str(uuid.uuid4()),
                "body_tag_no": body_tag_no.strip(),
                "deceased_name": deceased_name.strip(),
                "age": str(age).strip(),
                "sex": sex,
                "dod_date": to_date_str(dod),
                "tod_time": to_time_str(tod),
                "cause_of_death": cause.strip(),
                "ward_unit": ward_unit.strip(),
                "brought_by": brought_by.strip(),
                "admitted_dt": combine_date_time(admitted_date, admitted_time),
                "storage_location": storage_location.strip(),
                "next_of_kin": nok.strip(),
                "next_of_kin_contact": nok_contact.strip(),
                "id_docs_seen": id_docs,
                "autopsy_required": autopsy_required,
                "autopsy_date": to_date_str(autopsy_date) if autopsy_date else "",
                "release_status": "In Storage",
                "released_dt": "",
                "released_to": "",
                "remarks": remarks.strip(),
                "last_updated": now_iso(),
            }
            df = pd.concat([df, pd.DataFrame([record])], ignore_index=True)
            save_data(df)
            st.success("Record saved ✅")
            st.experimental_rerun()

# ----------------------------
# Browse & Filter
# ----------------------------
with tab_browse:
    st.subheader("Browse & Filter Records")
    df = load_data()

    # Filters
    fc1, fc2, fc3, fc4 = st.columns([1,1,1,1])
    with fc1:
        f_status = st.multiselect("Status", options=STATUS_OPTIONS, default=[])
    with fc2:
        f_sex = st.multiselect("Sex", options=SEX_OPTIONS, default=[])
    with fc3:
        f_from = st.date_input("DoD From", value=None)
    with fc4:
        f_to = st.date_input("DoD To", value=None)

    # Text filters
    tc1, tc2, tc3 = st.columns([1,1,1])
    with tc1:
        q_name = st.text_input("Search Name / Tag / NOK", placeholder="partial matches ok")
    with tc2:
        q_location = st.text_input("Search Storage Location")
    with tc3:
        q_cause = st.text_input("Search Cause of Death")

    df_f = df.copy()

    # Apply filters
    if f_status:
        df_f = df_f[df_f["release_status"].isin(f_status)]
    if f_sex:
        df_f = df_f[df_f["sex"].isin(f_sex)]
    # Date range filter on dod_date
    def parse_date(x):
        try:
            return datetime.strptime(x, "%Y-%m-%d").date()
        except Exception:
            return None
    if f_from:
        df_f = df_f[df_f["dod_date"].apply(lambda x: (d := parse_date(x)) is not None and d >= f_from)]
    if f_to:
        df_f = df_f[df_f["dod_date"].apply(lambda x: (d := parse_date(x)) is not None and d <= f_to)]
    # Text search
    if q_name.strip():
        q = q_name.strip().lower()
        df_f = df_f[
            df_f["deceased_name"].str.lower().str.contains(q, na=False)
            | df_f["body_tag_no"].str.lower().str.contains(q, na=False)
            | df_f["next_of_kin"].str.lower().str.contains(q, na=False)
        ]
    if q_location.strip():
        q = q_location.strip().lower()
        df_f = df_f[df_f["storage_location"].str.lower().str.contains(q, na=False)]
    if q_cause.strip():
        q = q_cause.strip().lower()
        df_f = df_f[df_f["cause_of_death"].str.lower().str.contains(q, na=False)]

    st.caption(f"{len(df_f)} record(s) found")
    # Lightweight view for large tables
    show_cols = [
        "record_id", "body_tag_no", "deceased_name", "age", "sex",
        "dod_date", "tod_time", "storage_location", "release_status", "last_updated"
    ]
    st.dataframe(df_f[show_cols], use_container_width=True, hide_index=True)

    # Download filtered
    st.download_button(
        "Download filtered (CSV)",
        data=df_f.to_csv(index=False).encode("utf-8"),
        file_name="mortuary_records_filtered.csv",
        mime="text/csv"
    )

# ----------------------------
# Edit / Update
# ----------------------------
with tab_edit:
    st.subheader("Edit / Update an Existing Record")
    df = load_data()

    if df.empty:
        st.info("No records available.")
    else:
        # Select by body tag or record_id
        id_choice = st.selectbox(
            "Select a record (Body Tag — Name — Status)",
            options=[
                f"{r.body_tag_no} — {r.deceased_name} — {r.release_status} — ({r.record_id[:8]})"
                for _, r in df.iterrows()
            ],
            index=0
        )
        # Extract record_id from selection
        selected_id = id_choice.split("—")[-1].strip().strip("()")
        selected_id = selected_id  # 8 chars
        # Locate the real row by matching prefix
        row_idx = None
        for i, rid in enumerate(df["record_id"].tolist()):
            if rid.startswith(selected_id):
                row_idx = i
                break

        if row_idx is None:
            st.error("Could not locate the record.")
        else:
            rec = df.loc[row_idx].copy()

            st.markdown("**Basic Details**")
            c1, c2, c3 = st.columns(3)
            with c1:
                deceased_name_e = st.text_input("Deceased Name*", value=rec["deceased_name"])
                age_e = st.text_input("Age", value=rec["age"])
                sex_e = st.selectbox("Sex", options=SEX_OPTIONS, index=max(0, SEX_OPTIONS.index(rec["sex"]) if rec["sex"] in SEX_OPTIONS else 3))
                body_tag_no_e = st.text_input("Body Tag Number*", value=rec["body_tag_no"])
            with c2:
                try:
                    dod_e = datetime.strptime(rec["dod_date"], "%Y-%m-%d").date() if rec["dod_date"] else None
                except Exception:
                    dod_e = None
                dod_e = st.date_input("Date of Death*", value=dod_e)
                try:
                    tod_e = datetime.strptime(rec["tod_time"], "%H:%M").time() if rec["tod_time"] else None
                except Exception:
                    tod_e = None
                tod_e = st.time_input("Time of Death", value=tod_e if tod_e else time(0, 0))
                cause_e = st.text_input("Cause of Death", value=rec["cause_of_death"])
                ward_unit_e = st.text_input("Ward / Unit", value=rec["ward_unit"])
            with c3:
                brought_by_e = st.text_input("Brought By", value=rec["brought_by"])
                storage_location_e = st.text_input("Storage Location*", value=rec["storage_location"])
                nok_e = st.text_input("Next of Kin", value=rec["next_of_kin"])
                nokc_e = st.text_input("Next of Kin Contact", value=rec["next_of_kin_contact"])

            st.markdown("---")
            st.markdown("**Verification & Autopsy**")
            c4, c5, c6 = st.columns(3)
            with c4:
                id_docs_e = st.selectbox("ID Documents Verified?", options=YN_OPTIONS, index=max(0, YN_OPTIONS.index(rec["id_docs_seen"]) if rec["id_docs_seen"] in YN_OPTIONS else 1))
                autopsy_req_e = st.selectbox("Autopsy Required?", options=AUTO_OPTIONS, index=max(0, AUTO_OPTIONS.index(rec["autopsy_required"]) if rec["autopsy_required"] in AUTO_OPTIONS else 2))
            with c5:
                try:
                    autopsy_date_e = datetime.strptime(rec["autopsy_date"], "%Y-%m-%d").date() if rec["autopsy_date"] else None
                except Exception:
                    autopsy_date_e = None
                ad_check = st.checkbox("Set autopsy date?", value=bool(autopsy_date_e))
                autopsy_date_e = st.date_input("Autopsy Date", value=autopsy_date_e) if ad_check else None
            with c6:
                remarks_e = st.text_area("Remarks", value=rec["remarks"])

            st.markdown("---")
            st.markdown("**Admission & Release**")
            c7, c8, c9 = st.columns(3)
            with c7:
                # Show current admitted_dt (read-only)
                st.text_input("Admitted Datetime (ISO)", value=rec["admitted_dt"], disabled=True)
                storage_location_e2 = st.text_input("Storage Location (confirm)", value=storage_location_e)
            with c8:
                status_e = st.selectbox("Release Status", options=STATUS_OPTIONS,
                                        index=max(0, STATUS_OPTIONS.index(rec["release_status"]) if rec["release_status"] in STATUS_OPTIONS else 0))
                released_to_e = st.text_input("Released/Transferred To", value=rec["released_to"])
            with c9:
                # If marking as released/transferred, allow setting datetime
                try:
                    released_dt_cur = datetime.fromisoformat(rec["released_dt"]) if rec["released_dt"] else None
                except Exception:
                    released_dt_cur = None
                released_date_e = st.date_input("Release/Transfer Date", value=released_dt_cur.date() if released_dt_cur else None)
                released_time_e = st.time_input("Release/Transfer Time", value=released_dt_cur.time() if released_dt_cur else time(0, 0))

            # Buttons row
            bc1, bc2, bc3 = st.columns([1,1,1])
            with bc1:
                if st.button("💾 Save Changes", type="primary"):
                    req2 = {
                        "Deceased Name": deceased_name_e,
                        "Body Tag Number": body_tag_no_e,
                        "Date of Death": dod_e,
                        "Storage Location": storage_location_e2,
                    }
                    missing = validate_required(req2)
                    if missing:
                        st.error(f"Please fill required fields: {', '.join(missing)}")
                    else:
                        df.loc[row_idx, :] = {
                            "record_id": rec["record_id"],
                            "body_tag_no": body_tag_no_e.strip(),
                            "deceased_name": deceased_name_e.strip(),
                            "age": str(age_e).strip(),
                            "sex": sex_e,
                            "dod_date": to_date_str(dod_e),
                            "tod_time": to_time_str(tod_e),
                            "cause_of_death": cause_e.strip(),
                            "ward_unit": ward_unit_e.strip(),
                            "brought_by": brought_by_e.strip(),
                            "admitted_dt": rec["admitted_dt"],  # keep original
                            "storage_location": storage_location_e2.strip(),
                            "next_of_kin": nok_e.strip(),
                            "next_of_kin_contact": nokc_e.strip(),
                            "id_docs_seen": id_docs_e,
                            "autopsy_required": autopsy_req_e,
                            "autopsy_date": to_date_str(autopsy_date_e) if autopsy_date_e else "",
                            "release_status": status_e,
                            "released_dt": combine_date_time(released_date_e, released_time_e) if status_e != "In Storage" else "",
                            "released_to": released_to_e.strip() if status_e != "In Storage" else "",
                            "remarks": remarks_e.strip(),
                            "last_updated": now_iso(),
                        }
                        save_data(df)
                        st.success("Changes saved ✅")
                        st.experimental_rerun()
            with bc2:
                if st.button("📝 Mark as Released Now"):
                    df.loc[row_idx, "release_status"] = "Released"
                    df.loc[row_idx, "released_dt"] = now_iso()
                    df.loc[row_idx, "last_updated"] = now_iso()
                    save_data(df)
                    st.success("Marked as Released.")
                    st.experimental_rerun()
            with bc3:
                if st.button("🚚 Mark as Transferred Now"):
                    df.loc[row_idx, "release_status"] = "Transferred"
                    df.loc[row_idx, "released_dt"] = now_iso()
                    df.loc[row_idx, "last_updated"] = now_iso()
                    save_data(df)
                    st.success("Marked as Transferred.")
                    st.experimental_rerun()

# ----------------------------
# Footer
# ----------------------------
st.markdown("---")
st.caption("Data is stored locally as CSV. Keep regular backups. For multi-user or audit trails, consider migrating to SQLite/PostgreSQL later.")
