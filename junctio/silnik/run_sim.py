import traci

def main():
    traci.start(["sumo", "-c", "intersection.sumocfg"])

    step = 0
    while step < 20:
        traci.simulationStep()
        vehicles_on_map = traci.vehicle.getIDList()
        
        print(f"--- Step {step} ---")
        for veh_id in vehicles_on_map:
            x, y = traci.vehicle.getPosition(veh_id)
            print(f"Vehicle {veh_id}: X={x:.2f}, Y={y:.2f}")
            
        step += 1

    traci.close()

if __name__ == "__main__":
    main()