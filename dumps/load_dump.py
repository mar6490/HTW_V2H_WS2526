from pathlib import Path

import matplotlib
matplotlib.use("TkAgg")  # vermeidet Qt/Wayland-Probleme

import matplotlib.pyplot as plt
from oemof.solph import EnergySystem
import pandas as pd

# --- 1) Dump laden ---------------------------------------------------------
script_dir = Path(__file__).resolve().parent
dump_dir = script_dir
dump_name = "case4_es_charger_limited_BEV_transformer_bi_directional"

es = EnergySystem()
es.restore(dpath=dump_dir, filename=dump_name)

results = es.results["main"]

print("✅ Dump loaded successfully.")
print("Available components in 'results[\"main\"]':")
for key in results.keys():
    print(" -", key)


def get_series_by_substrings(substrings):
    """
    Suche in results nach einem Key, der alle substrings enthält,
    und gib die erste Zeitreihenspalte als Series zurück.
    """
    for k in results.keys():
        s = str(k)
        if all(sub in s for sub in substrings):
            res = results[k]
            seq = res["sequences"]  # DataFrame
            # Wenn es eine 'flow'-Spalte gibt, nimm die, sonst erste Spalte
            if "flow" in seq.columns:
                return seq["flow"]
            else:
                return seq.iloc[:, 0]
    raise KeyError(f"No result key found matching substrings: {substrings}")


def get_soc_series():
    """
    Hole SOC aus BEV_Storage. Falls es keine Spalte 'capacity' gibt,
    nimm einfach die erste Spalte.
    """
    for k in results.keys():
        s = str(k)
        # Storage-Eintrag hat (BEV_Storage, None)
        if "BEV_Storage" in s and "None" in s:
            seq = results[k]["sequences"]
            print("BEV_Storage sequences columns:", seq.columns)
            if "capacity" in seq.columns:
                return seq["capacity"]
            else:
                return seq.iloc[:, 0]
    raise RuntimeError("Could not find SOC sequence for BEV_Storage.")


# --- 2) Zeitreihen holen ---------------------------------------------------

pv = get_series_by_substrings(["Source: 'pv'"])
grid_import = get_series_by_substrings(["Source: 'grid-supply'"])
house_demand = get_series_by_substrings(["Sink: 'demand'"])
grid_excess = get_series_by_substrings(["Sink: 'excess_bel'"])

# Wallbox-Leistungen auf Elektrizitätsbus
wallbox_to_bev_el = get_series_by_substrings(
    ["Converter: 'wallbox_to_BEV'", "Bus: 'electricity'"]
)
wallbox_from_bev_el = get_series_by_substrings(
    ["Converter: 'wallbox_from_BEV'", "Bus: 'electricity'"]
)

# Fahrleistung auf Mobility-Bus
bev_drive = get_series_by_substrings(["Sink: 'BEV_drive'"])

# SOC des BEV-Speichers
soc = get_soc_series()

# --- 3) Plots ------------------------------------------------
# Plot 1 ------------------------------------------------------

fig, ax1 = plt.subplots(figsize=(16, 6))

# Leistungen (linke Achse)
pv.plot(ax=ax1, label="PV -> electricity bus")
grid_import.plot(ax=ax1, label="Grid import")
house_demand.plot(ax=ax1, label="Household demand")
grid_excess.plot(ax=ax1, label="Grid feed-in (excess)")
wallbox_to_bev_el.plot(ax=ax1, label="Wallbox: electricity -> BEV")
wallbox_from_bev_el.plot(ax=ax1, label="Wallbox: BEV -> electricity")
bev_drive.plot(ax=ax1, label="BEV driving demand (mobility bus)")

ax1.set_xlabel("Zeit")
ax1.set_ylabel("Leistung [kW]")
ax1.grid(True)

# SOC (rechte Achse)
ax2 = ax1.twinx()
soc.plot(ax=ax2, color="black", linewidth=2, label="SOC")
ax2.set_ylabel("State of Charge [Einheit je nach Modell]")

# Legend zusammenführen
h1, l1 = ax1.get_legend_handles_labels()
h2, l2 = ax2.get_legend_handles_labels()
ax1.legend(h1 + h2, l1 + l2, loc="upper center", ncol=4)

plt.title("Zeitreihe mit SOC – neues BEV_drive-Modell")
plt.tight_layout()

# Plot 2 ---------------------------------------------------
wallbox_to_bev_mob = get_series_by_substrings(
    ["Converter: 'wallbox_to_BEV'", "Bus: 'mobility'"]
)

plt.figure()
wallbox_to_bev_mob.plot()
plt.title("Wallbox: electricity -> BEV (mobility bus)")
plt.xlabel("Zeit")
plt.ylabel("Leistung [kW]")
plt.grid(True)
plt.tight_layout()

# --- 4) Konsistenzcheck: Wird beim Fahren aus der Wallbox geladen? -------

# gemeinsame Zeitachse mit Fahr- und Wallbox-Leistung
df = pd.DataFrame({
    "drive": bev_drive,
    "wallbox_to_bev": wallbox_to_bev_mob,  # aus get_series_by_substrings(...)
})

# alle Zeitschritte, in denen gleichzeitig gefahren und geladen würde
violations = df[(df["drive"] > 1e-6) & (df["wallbox_to_bev"] > 1e-6)]

print(
    "Anzahl Zeitschritte mit gleichzeitig Fahrt + Wallbox-Import:",
    len(violations),
)

# Optional: ein paar Problem-Zeiten anzeigen, falls es welche gibt
if len(violations) > 0:
    print("Beispiele für gleichzeitige Fahrt + Laden:")
    print(violations.head())




plt.show()



