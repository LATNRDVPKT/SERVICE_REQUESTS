# =============================================================================
# trip_analysis — views.py
# "Trip Analysis" — upload a raw packet-log CSV, get back an Excel report
# with a per-trip, per-time-range latency/packet summary (pivoted) plus the
# raw data on a second sheet. Open to every logged-in user.
# =============================================================================
import os
import datetime
import shutil

import logging

import pandas as pd
from django.conf import settings
from django.contrib.auth.decorators import login_required
from django.core.files.storage import FileSystemStorage
from django.shortcuts import render

logger = logging.getLogger(__name__)


def is_openpyxl_present() -> bool:
    try:
        import importlib
        importlib.import_module("openpyxl")
        return True
    except Exception:
        return False


OPENPYXL_PRESENT = is_openpyxl_present()


def _safe_int(value, default=0):
    """int() that never raises — real-world exports sometimes leave a
    numeric-looking column blank ('') or non-numeric for a given row."""
    try:
        return int(value)
    except (TypeError, ValueError):
        try:
            return int(float(value))
        except (TypeError, ValueError):
            return default


def process_csv_to_excel(input_csv_path: str, output_xlsx_path: str):
    a = pd.read_csv(input_csv_path)

    # normalize message type strings: strip whitespace and uppercase so comparisons are robust
    if "Message Type" in a.columns:
        a["Message Type"] = a["Message Type"].astype(str).str.strip().str.upper()

    # helper: try multiple parse strategies and pick the one that yields the most non-null values
    def _smart_parse(ser):
        # try common precise formats first
        fmts = ["%Y-%m-%d %H:%M:%S", "%Y-%m-%d %H:%M", "%d-%m-%Y %H:%M:%S", "%d-%m-%Y %H:%M", "%d/%m/%Y %H:%M:%S"]
        best = pd.to_datetime(ser, errors="coerce")
        best_count = best.notna().sum()
        for f in fmts:
            d = pd.to_datetime(ser, format=f, errors="coerce")
            cnt = d.notna().sum()
            if cnt > best_count:
                best = d
                best_count = cnt
        # fall back to infer (try both false/true for dayfirst) — modern pandas
        # infers the format automatically, no infer_datetime_format flag needed
        # (that kwarg was removed in pandas 3.x).
        if best_count == 0:
            inf = pd.to_datetime(ser, dayfirst=False, errors="coerce")
            if inf.notna().sum() > best_count:
                best = inf
            else:
                inf2 = pd.to_datetime(ser, dayfirst=True, errors="coerce")
                if inf2.notna().sum() > best_count:
                    best = inf2
        return best

    a['Event Time'] = _smart_parse(a.get('Event Time'))
    a['Ingestion Timestamp'] = _smart_parse(a.get('Ingestion Timestamp'))

    a['Vehicle Speed'] = pd.to_numeric(a.get('Vehicle Speed'), errors='coerce').fillna(0)

    total_packets = len(a)

    # assign Trip Number only for rows between TRIP_START and TRIP_END (inclusive)
    trip_num = 0
    in_trip = False
    trip_series = []
    for msg in a.get("Message Type", []):
        if not isinstance(msg, str):
            m = str(msg).strip().upper()
        else:
            m = msg
        # accept common variants and uppercase
        if m == "TRIP_START" or m == "TRIP START":
            trip_num += 1
            in_trip = True
            trip_series.append(trip_num)   # include TRIP_START row in the trip
        elif m == "TRIP_END" or m == "TRIP END":
            trip_series.append(trip_num)  # include TRIP_END row in the trip
            in_trip = False
        else:
            trip_series.append(trip_num if in_trip else None)
    a["Trip Number"] = trip_series

    # Fallback: if no trip markers found, treat whole file as a single trip so summary can still be built
    if all(x is None or x == 0 for x in trip_series):
        trip_series = [1] * len(trip_series)
        trip_num = 1
    a["Trip Number"] = trip_series

    a["Time Diff (sec)"] = (a["Ingestion Timestamp"] - a["Event Time"]).dt.total_seconds()

    def time_category(seconds):
        # keep a visible category so groups are not lost
        if pd.isna(seconds):
            return "Unknown"
        if seconds < 5 * 60:
            return "0-5Mins"
        if seconds < 15 * 60:
            return "5-15Mins"
        if seconds < 30 * 60:
            return "15-30Mins"
        if seconds < 60 * 60:
            return "30-1Hr"
        if seconds < 3 * 60 * 60:
            return "1-3Hrs"
        if seconds < 6 * 60 * 60:
            return "3-6Hrs"
        return ">6Hrs"

    a["Time Range"] = a["Time Diff (sec)"].apply(time_category)

    # periodic messages (any Message Type containing 'PERIODIC') but only those that are within a trip (Trip Number not null)
    periodic_all = a[a["Message Type"].astype(str).str.upper().str.contains("PERIODIC", na=False) & a["Trip Number"].notna()]
    total_periodic_all = periodic_all.shape[0]

    # filter periodic rows where Vehicle Speed > 3 and inside trips (used only for the listed message counts)
    periodic = periodic_all[periodic_all['Vehicle Speed'] > 3]
    total_periodic = periodic.shape[0]

    # If speed-filtered periodic data is empty but there are periodic_all rows,
    # fall back to periodic_all so the summary still builds (counts computed accordingly).
    used_speed_filter = True
    if periodic.empty and not periodic_all.empty:
        used_speed_filter = False
        periodic = periodic_all.copy()

    # If there are no periodic rows at all, generate groups from any trip/time combos so we still produce a summary.
    if periodic.empty and periodic_all.empty:
        used_speed_filter = False
        # use all rows with Trip Number assigned to build groups (Time Range may be "Unknown")
        periodic = a[a["Trip Number"].notna()].copy()
        # still allow summary creation if periodic is not empty after this fallback

    summary = []
    # iterate groups where PERIODIC exists and speed>3 (so message counts are relevant);
    # for all other parameters use all rows inside same Trip Number + Time Range (regardless of speed)
    for (trip, time_cat), group_speed in periodic.groupby(["Trip Number", "Time Range"]):
        if pd.isna(trip) or pd.isna(time_cat):
            continue
        group_speed = group_speed.sort_values("Event Time")

        # full_group_all = all rows for this Trip+TimeRange (regardless of speed) -> used for start/end times, addresses, lat/long, ingestion timestamps, time taken
        full_group_all = a[(a["Trip Number"] == trip) & (a["Time Range"] == time_cat)].sort_values("Event Time")

        # determine start/end rows for "other parameters" from full_group_all (fallback to group_speed if empty)
        if not full_group_all.empty:
            start_all = full_group_all.iloc[0]
            end_all = full_group_all.iloc[-1]
        else:
            start_all = group_speed.iloc[0]
            end_all = group_speed.iloc[-1]

        # For message counts we want the speed-filtered rows when used; otherwise use the group rows
        full_group_speed = group_speed if used_speed_filter else full_group_all
        msg_counts = full_group_speed["Message Type"].value_counts().to_dict()

        # Build fields:
        # Ingestion Timestamp Start = MIN ingestion timestamp in this Trip+TimeRange (all rows)
        # Ingestion Timestamp End   = MAX ingestion timestamp in this Trip+TimeRange (all rows)
        ingest_series = pd.to_datetime(full_group_all.get("Ingestion Timestamp"), errors='coerce')
        if ingest_series.notna().any():
            start_ingest = ingest_series.min()
            end_ingest = ingest_series.max()
        else:
            # fallback to row values (if full_group_all had no valid ingestion timestamps)
            start_ingest = start_all.get("Ingestion Timestamp")
            end_ingest = end_all.get("Ingestion Timestamp")

        # Difference Event (S - E) — computed from the all-rows start/end (per request other params use all rows)
        try:
            if pd.notna(start_all.get("Event Time")) and pd.notna(end_all.get("Event Time")):
                event_td = end_all.get("Event Time") - start_all.get("Event Time")
                diff_event_str = str(event_td)
                diff_event_seconds = event_td.total_seconds()
            else:
                diff_event_str = None
                diff_event_seconds = None
        except Exception:
            diff_event_str = None
            diff_event_seconds = None

        if pd.notna(start_ingest) and pd.notna(end_ingest):
            td = end_ingest - start_ingest
            time_taken = str(td)
            time_taken_hours = td.total_seconds() / 3600
        else:
            time_taken = None
            time_taken_hours = None

        # count periodic messages for this trip/time range (only from speed>3 filtered data)
        periodic_count = sum(count for key, count in msg_counts.items() if "PERIODIC" in str(key).upper())

        denom = total_periodic if used_speed_filter else total_periodic_all
        pct_of_total_periodic = round((periodic_count / denom * 100), 2) if denom else 0.0
        pct_of_total_packets = round((periodic_count / total_packets * 100), 2) if total_packets else 0.0

        # compute odometues for this Trip+TimeRange (exclude zeros)
        odo_series = pd.to_numeric(full_group_all.get("Odometer"), errors='coerce')
        odo_non_zero = odo_series[odo_series > 0]
        if not odo_non_zero.empty:
            start_odo = float(odo_non_zero.min())
            end_odo = float(odo_non_zero.max())
            total_odo = end_odo - start_odo
        else:
            start_odo = None
            end_odo = None
            total_odo = None

        row = {
            "Trip": f"Trip {_safe_int(trip, trip)}",
            "Time Range": time_cat,
            # use start_all/end_all (all rows in trip/time range) for these params as requested
            "Start Time (Event)": start_all.get("Event Time"),
            "End Time (Event)": end_all.get("Event Time"),
            "Difference Event(S-E)": diff_event_str,
            "PERIODIC": periodic_count,                                # count only when speed>3
            "Total PERIODIC for all trips": _safe_int(total_periodic),   # total of speed>3 periodic across trips
            "% of Total packets": pct_of_total_packets,
            # Start/End Odo and Difference (placed before Start Location as requested)
            "Start Odo": start_odo,
            "End Odo": end_odo,
            "Total Odo": total_odo,
            "Start Location (Address)": start_all.get("Address"),
            "End Location (Address)": end_all.get("Address"),
            "Ingestion Timestamp Start": start_ingest,
            "Ingestion Timestamp End": end_ingest,
            "Time taken to post (hh:mm:ss)": time_taken,
            "Time taken to post (hours)": time_taken_hours,
            "Start Latitude": start_all.get("Latitude"),
            "Start Longitude": start_all.get("Longitude"),
            "End Latitude": end_all.get("Latitude"),
            "End Longitude": end_all.get("Longitude"),
        }

        # The following message counts must be considered only when Vehicle Speed > 3 (per your request)
        msg_cols_speed_filtered = [
            "HARSH_ACCELERATION_START",
            "HARSH_ACCELERATION_END",
            "HARSH_BREAKING_START",
            "HARSH_BREAKING_END",
            "Ignition ON",
            "Ignition OFF",
            "HEARTBEAT_MESSAGE"
        ]
        # normalize keys when matching so counts work regardless of case/spacing/underscores
        def _norm(s):
            return ''.join(ch if ch.isalnum() else ' ' for ch in str(s)).upper()

        # Count these events within the Trip+TimeRange using rows where Vehicle Speed > 3
        if not full_group_all.empty:
            speed_mask = pd.to_numeric(full_group_all.get("Vehicle Speed"), errors="coerce") > 3
            speed_filtered_rows = full_group_all[speed_mask]
        else:
            # fallback to the already speed-filtered group if needed
            speed_mask = pd.to_numeric(full_group_speed.get("Vehicle Speed"), errors="coerce") > 3
            speed_filtered_rows = full_group_speed[speed_mask]

        # Use token-based matching with common synonyms to be robust to variations (e.g., BRAKING vs BREAKING)
        tokens_map = {
            "HARSH_ACCELERATION_START": [["HARSH","ACCELERATION","START"]],
            "HARSH_ACCELERATION_END": [["HARSH","ACCELERATION","END"]],
            # Accept multiple variants for braking/breaking phrasing
            "HARSH_BREAKING_START": [["HARSH","BREAK","START"], ["HARSH","BRAKE","START"], ["HARSH","BRAKING","START"], ["HARSH","BREAKING","START"]],
            "HARSH_BREAKING_END": [["HARSH","BREAK","END"], ["HARSH","BRAKE","END"], ["HARSH","BRAKING","END"], ["HARSH","BREAKING","END"]],
            "Ignition ON": [["IGNITION","ON"]],
            "Ignition OFF": [["IGNITION","OFF"]],
            "HEARTBEAT_MESSAGE": [["HEARTBEAT"], ["HEARTBEAT","MESSAGE"]],
        }

        def _match_any(normalized_msg, token_groups):
            for grp in token_groups:
                if all(tok in normalized_msg for tok in grp):
                    return True
            return False

        for mc in msg_cols_speed_filtered:
            token_groups = tokens_map.get(mc)
            # If we don't have a pre-defined token map, fall back to simple normalized word matching
            if token_groups is None:
                token_groups = [[t for t in _norm(mc).split() if t]]
            # match by checking tokens against normalized message text
            count = _safe_int(
                speed_filtered_rows
                .get("Message Type", pd.Series([], dtype=str))
                .astype(str)
                .apply(lambda x: _match_any(_norm(x), token_groups))
                .sum()
            )
            row[mc] = count

        summary.append(row)

    summary_df = pd.DataFrame(summary)

    # Desired order (include odo fields before addresses)
    desired_order = [
        "Start Time (Event)",
        "End Time (Event)",
        "Difference Event(S-E)",
        "PERIODIC",
        "Total PERIODIC for all trips",
        "% of Total packets",
        "Start Odo",
        "End Odo",
        "Total Odo",
        "Start Location (Address)",
        "End Location (Address)",
        "Ingestion Timestamp Start",
        "Ingestion Timestamp End",
        "Time taken to post (hh:mm:ss)",
        "Time taken to post (hours)",
        "Start Latitude",
        "Start Longitude",
        "End Latitude",
        "End Longitude",
        "HARSH_ACCELERATION_START",
        "HARSH_ACCELERATION_END",
        "HARSH_BREAKING_START",
        "HARSH_BREAKING_END",
        "Ignition ON",
        "Ignition OFF",
        "HEARTBEAT_MESSAGE"
    ]

    # Ensure all desired columns exist on summary_df (message/count -> 0, others -> None)
    for col in desired_order:
        if col not in summary_df.columns:
            if col in [
                "PERIODIC", "Total PERIODIC for all trips",
                "% of Total packets",
                "Start Odo", "End Odo", "Total Odo",
                "HARSH_ACCELERATION_START", "HARSH_ACCELERATION_END",
                "HARSH_BREAKING_START", "HARSH_BREAKING_END",
                "Ignition ON", "Ignition OFF", "HEARTBEAT_MESSAGE"
            ]:
                 summary_df[col] = 0
            else:
                 summary_df[col] = None

    # Keep Trip and Time Range so we can pivot; place desired_order columns after them
    cols_for_pivot = ["Trip", "Time Range"] + desired_order
    cols_for_pivot = [c for c in cols_for_pivot if c in summary_df.columns]

    ordered_df = summary_df[cols_for_pivot].copy()

    if summary_df.empty:
        # write sample debug CSV next to output (helps when summary unexpectedly empty)
        try:
            debug_csv = os.path.splitext(output_xlsx_path)[0] + "_debug_sample.csv"
            a.head(200).to_csv(debug_csv, index=False)
        except Exception:
            pass

    if not ordered_df.empty:
        ordered_df["Trip_TimeRange"] = ordered_df["Trip"] + " - " + ordered_df["Time Range"]
        pivot_df = ordered_df.drop(columns=["Trip", "Time Range"]).set_index("Trip_TimeRange").T
        present_rows = [r for r in desired_order if r in pivot_df.index]
        other_rows = [r for r in pivot_df.index if r not in present_rows]
        pivot_df = pivot_df.loc[present_rows + other_rows]
    else:
        pivot_df = pd.DataFrame()

    with pd.ExcelWriter(output_xlsx_path, engine="openpyxl") as writer:
        if pivot_df.empty:
            # create a small explanatory DataFrame for the summary sheet
            pd.DataFrame([{"note": "No summary produced — check 'Message Type' values, TRIP_START/TRIP_END markers, or Vehicle Speed thresholds"}])\
                .to_excel(writer, sheet_name="Summary_Report", index=False)
        else:
            pivot_df.to_excel(writer, sheet_name="Summary_Report")
        a.to_excel(writer, sheet_name="Raw_Data", index=False)


@login_required
def upload_file(request):
    download_url = None
    error = None

    # dynamic check for Excel engine
    if not is_openpyxl_present() and request.method == "GET":
        error = "Warning: server missing 'openpyxl' — report will be provided as CSV ZIP instead of XLSX."

    if request.method == "POST" and request.FILES.get("csv_file"):
        f = request.FILES["csv_file"]
        uploads_dir = os.path.join(settings.MEDIA_ROOT, "uploads")
        os.makedirs(uploads_dir, exist_ok=True)
        fs = FileSystemStorage(location=uploads_dir, base_url=os.path.join(settings.MEDIA_URL, "uploads/"))
        saved_name = fs.save(f.name, f)
        input_path = fs.path(saved_name)

        outputs_dir = os.path.join(settings.MEDIA_ROOT, "outputs")
        os.makedirs(outputs_dir, exist_ok=True)
        ts = datetime.datetime.now().strftime('%Y%m%d%H%M%S')
        try:
            if OPENPYXL_PRESENT:
                out_name = f"Trip_Summary_Report_{ts}.xlsx"
                out_path = os.path.join(outputs_dir, out_name)
                process_csv_to_excel(input_path, out_path)
                download_url = settings.MEDIA_URL.rstrip("/") + "/outputs/" + out_name
            else:
                # fallback: write raw CSV plus summary CSV (reuse logic to create summary_df if available)
                raw = pd.read_csv(input_path)
                # If you have a function to compute summary_df, call it here; otherwise provide raw only
                raw_csv_name = f"raw_data_{ts}.csv"
                raw_csv_path = os.path.join(outputs_dir, raw_csv_name)
                raw.to_csv(raw_csv_path, index=False)

                # optional: try to build summary using same logic but avoid Excel
                try:
                    # create a minimal summary using the same processing steps (you can call process_csv_to_excel internals)
                    # For safety, here we produce a simple counts summary
                    counts = raw["Message Type"].value_counts().reset_index()
                    counts.columns = ["Message Type", "Count"]
                    summary_csv_name = f"summary_{ts}.csv"
                    summary_csv_path = os.path.join(outputs_dir, summary_csv_name)
                    counts.to_csv(summary_csv_path, index=False)
                    files_to_zip = [raw_csv_path, summary_csv_path]
                except Exception:
                    files_to_zip = [raw_csv_path]

                zip_base = os.path.join(outputs_dir, f"Trip_Summary_{ts}")
                shutil.make_archive(zip_base, 'zip', os.path.dirname(files_to_zip[0]), '.')  # create zip of outputs_dir
                zip_name = os.path.basename(zip_base) + ".zip"
                download_url = settings.MEDIA_URL.rstrip("/") + "/outputs/" + zip_name

        except Exception as e:
            logger.exception("Trip Analysis report generation failed for %s", f.name)
            error = str(e)

    return render(request, "trip_analysis/upload.html", {"download_url": download_url, "error": error})
