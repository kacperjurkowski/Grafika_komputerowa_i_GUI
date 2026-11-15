# Polecenie do wygenerowania sieci:
# netconvert --node-files intersection.nod.xml --edge-files intersection.edg.xml -o intersection.net.xml --offset.disable-normalization true --no-turnarounds true
import traci
from pathlib import Path

def main():
    CFG = Path(__file__).parent / "intersection.sumocfg"

    traci.start(["sumo", "-c", str(CFG)])
    try:
        for step in range(200):
            traci.simulationStep()
            print(f"--- Step {step} ---")
            for veh_id in traci.vehicle.getIDList():
                x,y = traci.vehicle.getPosition(veh_id)
                print(f"Vehicle {veh_id}: X={x:.2f}, Y={y:.2f}")
    finally:
        traci.close()

if __name__ == "__main__":
    main()