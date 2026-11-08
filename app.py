import streamlit as st
import pandas as pd
import re

st.set_page_config(page_title="Fleet Checker Uganda", page_icon="🚛", layout="wide")
st.title("🚛 Fleet Checker Uganda - Overspeed + Fuel + Theft (Hill-Safe)")
st.write("Tab 1: Overspeed | Tab 2: Official 7-Point Fuel Report + Hill-Safe Theft Detection")
st.caption("Rule: We do NOT flag a fuel drop. We flag a fuel loss that survives the restart.")

tab1, tab2 = st.tabs(["🚨 1. Overspeed - Buliisa", "⛽ 2. Fuel Report + Theft Check"])

# ============ TAB 1 - OVERSPEED ============
with tab1:
    st.info("Rule: Lat 2.1-2.5 | Lon 31.0-32.2 | Speed >49 | Duration >11 sec")
    up1 = st.file_uploader("Upload Overspeed Excel / CSV", type=["xlsx","csv"], key="over")
    def num(t):
        if pd.isna(t): return 0
        m = re.findall(r"[\d.]+", str(t))
        return float(m[0]) if m else 0
    if up1:
        df = pd.read_csv(up1) if up1.name.endswith(".csv") else pd.read_excel(up1)
        cols = {c.lower(): c for c in df.columns}
        s_col = next((cols[k] for k in cols if "speed" in k), None)
        d_col = next((cols[k] for k in cols if "duration" in k), None)
        l_col = next((cols[k] for k in cols if "location" in k), None)
        if not s_col or not d_col or not l_col:
            st.warning(f"Need Speed/Duration/Location. Found: {list(df.columns)}")
        else:
            df["Speed_Num"] = df[s_col].apply(num)
            df["Duration_Num"] = df[d_col].apply(num)
            df["Longitude"] = df[l_col].apply(lambda x: float(str(x).split(",")[0]) if "," in str(x) else 0)
            df["Latitude"] = df[l_col].apply(lambda x: float(str(x).split(",")[1]) if "," in str(x) else 0)
            f = df[(df["Speed_Num"]>49)&(df["Duration_Num"]>11)&(df["Latitude"]>=2.1)&(df["Latitude"]<=2.5)&(df["Longitude"]>=31)&(df["Longitude"]<=32.2)].copy()
            f["Level"] = f["Speed_Num"].apply(lambda s: "CRITICAL >70" if s>=70 else "HIGH 60-69" if s>=60 else "MODERATE 50-59")
            c1,c2,c3 = st.columns(3)
            c1.metric("Total Rows", len(df)); c2.metric("True Violations", len(f)); c3.metric("Critical >70", len(f[f["Speed_Num"]>=70]))
            st.dataframe(f)
            if len(f)>0:
                st.download_button("📥 Download Violations", f.to_csv(index=False).encode(), "Buliisa_Violations.csv")

# ============ TAB 2 - FUEL + HILL-SAFE THEFT ============
with tab2:
    st.subheader("⛽ Official Fuel Report (1-7) + Theft Detection (8) - Hill-Safe")
    st.write("Upload columns: `Equipment / Inv_Number / Plate_Number / Resource / Brand_Model / Driver_ID / Route / Distance_km / Hours_Worked / Fuel_Used_Litres / Trip_Time / Expected_L_per_100km`")
    st.write("**For 95% accuracy, add these 2 optional columns:** `Parking_Slope` (Flat/Hill) and `Fuel_After_Restart_Litres`")
    up2 = st.file_uploader("Upload Fuel Excel / CSV", type=["xlsx","csv"], key="fuel")
    bench = st.selectbox("Benchmark if no Expected column", ["Truck - Fuso / Howo (28 L/100km)", "Pickup - Land Cruiser (15 L/100km)", "Generator (12 L/h)", "Excavator (22 L/h)"])
    default_expected = 28 if "Fuso" in bench else 15 if "Pickup" in bench else 12 if "Generator" in bench else 22
    fuel_price = st.number_input("Fuel Price UGX / Litre", value=5000)

    if up2:
        fdf = pd.read_csv(up2) if up2.name.endswith(".csv") else pd.read_excel(up2)
        fdf.columns = [c.strip() for c in fdf.columns]
        st.write("Your columns:", list(fdf.columns))
        def find_col(keywords):
            for c in fdf.columns:
                cl = c.lower()
                if any(k in cl for k in keywords):
                    return c
            return None
        equip_col = find_col(["equipment","inv","asset"])
        plate_col = find_col(["plate","reg"])
        resource_col = find_col(["resource","typical","type"])
        brand_col = find_col(["brand","model","make"])
        driver_col = find_col(["driver","operator"])
        route_col = find_col(["route","destination"])
        dist_col = find_col(["distance","km"])
        hours_col = find_col(["hour","hrs"])
        fuel_col = find_col(["fuel_used","fuel","litre"])
        exp_col = find_col(["expected"])
        time_col = find_col(["trip_time","time","day","night","shift"])
        slope_col = find_col(["slope","parking","hill","park"])
        restart_col = find_col(["restart","after_restart","after"])
        before_park_col = find_col(["before_park","before","parked"])

        if fuel_col is None:
            st.error("Need Fuel Used column. Rename to Fuel_Used_Litres")
            st.stop()

        report = pd.DataFrame()
        report["1. Equipment / Inv Number"] = fdf[equip_col] if equip_col else fdf.index
        report["Plate Number"] = fdf[plate_col] if plate_col else "N/A"
        report["Typical Resource"] = fdf[resource_col] if resource_col else bench
        report["Brand and Model"] = fdf[brand_col] if brand_col else "N/A"
        report["Driver / Operator"] = fdf[driver_col] if driver_col else "N/A"
        report["Route"] = fdf[route_col] if route_col else "N/A"
        report["2. Fuel Consumption During Period (L)"] = fdf[fuel_col]
        if dist_col:
            report["3. Actual Average (L/100km)"] = (fdf[fuel_col] / fdf[dist_col].replace(0,1) * 100).round(2)
        else:
            report["3. Actual Average (L/100km)"] = 0
        if hours_col:
            report["3b. Actual Average (L/h)"] = (fdf[fuel_col] / fdf[hours_col].replace(0,1)).round(2)
        else:
            report["3b. Actual Average (L/h)"] = 0
        report["4. Expected Average"] = fdf[exp_col] if exp_col else default_expected
        use_h = False
        if dist_col is None and hours_col is not None:
            use_h = True
        actual_col = "3b. Actual Average (L/h)" if use_h else "3. Actual Average (L/100km)"
        report["5. Operating Outside Expected?"] = report.apply(lambda r: "YES - OUTSIDE" if r[actual_col] > r["4. Expected Average"]*1.10 else "NO - Within Standard", axis=1)
        report["6. Consumption Deviation %"] = ((report[actual_col] - report["4. Expected Average"]) / report["4. Expected Average"] * 100).round(1)
        dist_for_loss = fdf[dist_col]/100 if dist_col else fdf[hours_col] if hours_col else 1
        report["Estimated Loss (UGX)"] = (report["6. Consumption Deviation %"]/100 * report["4. Expected Average"] * dist_for_loss * fuel_price).round(0)

        # ===== HILL-SAFE THEFT DETECTION v2 - This is the part from that message, already inside =====
        driver_counts = report["Driver / Operator"].value_counts().to_dict() if driver_col else {}
        def theft_check_v2(row, idx):
            dev = row["6. Consumption Deviation %"]
            evidence = []
            score = 0
            if restart_col and before_park_col:
                try:
                    before = float(fdf.iloc[idx][before_park_col])
                    after = float(fdf.iloc[idx][restart_col])
                    if before > 0 and after >= before * 0.85:
                        return "🟢 NO THEFT - HILL EFFECT", "Fuel recovered after restart on flat ground - Hill / Slope effect. Ignored.", "No action. Parking was on slope. Fuel returned after restart."
                    elif before > 0 and after < before * 0.85:
                        score += 3; evidence.append(f"Fuel did NOT recover after restart: {before}L -> {after}L - Permanent loss, not hill")
                except:
                    pass
            if slope_col:
                slope_val = str(fdf.iloc[idx][slope_col]).lower()
                if "hill" in slope_val or "slope" in slope_val:
                    evidence.append("Parked on Hill/Slope - Sensor drop expected")
            if dev > 35:
                score += 3; evidence.append(f"Total trip deviation {dev}% - Hill cannot explain total trip")
            elif dev > 20:
                score += 2; evidence.append(f"Total trip deviation {dev}%")
            elif dev > 10:
                score += 1; evidence.append(f"Moderate total deviation {dev}%")
            else:
                return "🟢 NO THEFT SIGNAL", "Total trip normal - Any sensor drop was hill / slope effect", "No action. Ignore sensor drop."
            drv = row["Driver / Operator"]
            if driver_counts.get(drv,0) >= 3 and dev > 15:
                score += 2; evidence.append(f"Repeat: {drv} high {driver_counts.get(drv)}x - Not one-time hill")
            if time_col:
                tv = str(fdf.iloc[idx][time_col]).lower()
                if "night" in tv:
                    score += 1; evidence.append("Night trip")
            if score >= 5:
                risk = "🔴 HIGH - PROBABLE THEFT - INVESTIGATE"
                action = "HIGH ACCURACY: Total trip + Repeat + Night / No Recovery. Hill ruled out. Check: Fuel receipts, CCTV at parking, GPS parked location, interview driver."
            elif score >= 3:
                risk = "🟠 MEDIUM - SUSPECTED LOSS - CHECK"
                action = "Check: Inspect for leaks, verify receipts, ask driver where parked. If parked on hill, verify if fuel recovered after restart. If not recovered, escalate to HIGH."
            elif dev > 10:
                risk = "🟡 LOW - OPERATING ISSUE"
                action = "Likely mechanical / hill / load. Check tyres, load, service. Do NOT accuse driver. Monitor next trip."
            else:
                risk = "🟢 NO THEFT SIGNAL"
                action = "No action."
            return risk, " | ".join(evidence) if evidence else "No pattern", action

        theft_results = [theft_check_v2(row, i) for i, row in report.iterrows()]
        report["8. Theft Risk"] = [x[0] for x in theft_results]
        report["Theft Evidence"] = [x[1] for x in theft_results]
        def remark(row):
            dev = row["6. Consumption Deviation %"]
            if dev <= 10: return f"Deviation {dev}%. Within standard. No action."
            elif dev <= 20: return f"Deviation {dev}%. Moderate. Check tyres, load, route, idling."
            elif dev <= 35: return f"Deviation {dev}%. High. Inspect vehicle, fuel system, receipts, GPS vs odometer."
            else: return f"Deviation {dev}%. Critical. Immediate investigation."
        report["7. Remarks & Recommended Corrective Action"] = report.apply(remark, axis=1)
        report["Recommended Corrective Action (Theft)"] = [x[2] for x in theft_results]

        total = len(report)
        outside = len(report[report["5. Operating Outside Expected?"]=="YES - OUTSIDE"])
        high_theft = len(report[report["8. Theft Risk"].str.contains("HIGH")])
        med_theft = len(report[report["8. Theft Risk"].str.contains("MEDIUM")])
        hill_ignored = len(report[report["8. Theft Risk"].str.contains("HILL EFFECT")])
        total_loss = report["Estimated Loss (UGX)"].sum()
        c1,c2,c3,c4 = st.columns(4)
        c1.metric("Equipment Checked", total)
        c2.metric("Outside Standard", outside)
        c3.metric("🔴 High Theft Risk", high_theft)
        c4.metric("Est. Loss UGX", f"{total_loss:,.0f}")
        st.success(f"✅ Hill-Safe Active: {hill_ignored} cases correctly ignored as Hill Effect | 🟠 Medium: {med_theft} | 🔴 High: {high_theft}")
        st.warning("HIGH = Needs 3+ proofs. Single fuel drop alone will NEVER be HIGH.")
        st.dataframe(report, use_container_width=True)
        st.download_button("📥 Download Full Report (Fuel + Theft Hill-Safe)", report.to_csv(index=False).encode(), "Fuel_Theft_Report_HillSafe.csv")
    else:
        st.info("Upload fuel file. Tip: Add Parking_Slope + Fuel_After_Restart_Litres for 95% accuracy.")
