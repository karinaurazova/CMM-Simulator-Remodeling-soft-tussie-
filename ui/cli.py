import argparse
import matplotlib.pyplot as plt
import numpy as np
from core.models import ConstrainedMixtureModel

def parse_arguments():
    parser = argparse.ArgumentParser(
        description="Constrained Mixture Model (CMM) Simulator CLI",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter
    )
    
    parser.add_argument('protocol', 
                      choices=['constant', 'linear', 'cyclic', 'all'],
                      help="Loading protocol type")
    parser.add_argument('--feedback', action='store_true',
                      help="Activate mechanical feedback")
    
    material = parser.add_argument_group('Material parameters')
    material.add_argument('--c_c', type=float, default=1.0,
                        help="Collagen stiffness [kPa]")
    material.add_argument('--c_e', type=float, default=50.0,
                        help="Elastin stiffness [kPa]")
    material.add_argument('--c_g', type=float, default=10.0,
                        help="Matrix stiffness [kPa]")
    material.add_argument('--fi0_c', type=float, default=0.75,
                        help="Initial collagen content")
    material.add_argument('--fi0_e', type=float, default=0.05,
                        help="Initial elastin content")
    material.add_argument('--fi0_g', type=float, default=0.20,
                        help="Initial matrix content")
    material.add_argument('--lambda0_c', type=float, default=1.05,
                        help="Initial stretching of collagen")
    material.add_argument('--lambda0_e', type=float, default=1.10,
                        help="Initial stretching of elastin")
    
    remodel = parser.add_argument_group('Remodeling parameters')
    remodel.add_argument('--k_cplus', type=float, default=1.0,
                       help="Rate of collagen synthesis [1/day]")
    remodel.add_argument('--k_cminus', type=float, default=1.0,
                       help="Rate of collagen degradation [1/day]")
    remodel.add_argument('--k_eplus', type=float, default=1.0,
                       help="Elastin synthesis rate [1/day]")
    remodel.add_argument('--k_eminus', type=float, default=1.0,
                       help="Elastin degradation rate [1/day]")
    remodel.add_argument('--alpha_c', type=float, default=0.01,
                       help="Nonlinearity coefficient of collagen")
    remodel.add_argument('--gamma', type=float, default=1.0,
                       help="Anisotropy parameter")
    remodel.add_argument('--K_cplus', type=float, default=0.04,
                       help="Mechanical feedback coefficient")
    
    protocol = parser.add_argument_group('Protocol parameters')
    protocol.add_argument('--a', type=float, default=0.1,
                        help="Growth rate parameter (for linear/cyclic)")
    protocol.add_argument('--lambda_roof', type=float, default=1.1,
                        help="Basic fabric stretch")
    
    sim = parser.add_argument_group('Simulation parameters')
    sim.add_argument('--t_end', type=float, default=10.0,
                   help="Simulation time [days]")
    sim.add_argument('--n_points', type=int, default=1000,
                   help="Number of sampling points")
    sim.add_argument('--epsilon', type=float, default=1e-4,
                   help="Iteration convergence criterion")
    
    output = parser.add_argument_group('Output Settings')
    output.add_argument('--save', type=str,
                      help="Save results to file (no extension)")
    output.add_argument('--quiet', action='store_true',
                      help="Don't show progress")
    
    return parser.parse_args()

def run_simulation(params):
    if not params.quiet:
        print(f"\nRunning a simulation with a protocol '{params.protocol}'...")
        if params.feedback:
            print(f"Mechanical feedback: K_c+ = {params.K_cplus}")
    
    model = ConstrainedMixtureModel(vars(params))
    
    if params.protocol == 'all':
        results = model.simulate_all_protocols(feedback=params.feedback)
    else:
        results = model.simulate(params.protocol, feedback=params.feedback)
    
    if not params.quiet:
        print("Simulation completed successfully!")
        if params.protocol == 'all':
            for protocol, data in results.items():
                print(f"{protocol}: final stress = {data['sigma_total'][-1]:.2f} kPa")
        else:
            print(f"Last value σ_c: {results['sigma_c'][-1]:.2f} kPa")
    
    return results

def save_results(results, base_filename):
    np.savez(f"{base_filename}.npz", **results)
    import pandas as pd
    df = pd.DataFrame(results)
    df.to_csv(f"{base_filename}.csv", index=False)
    plt.figure(figsize=(10, 6))
    if isinstance(results, dict) and 'time' in results:  
        plt.plot(results['time'], results['sigma_c'], label='Collagen')
        if 'sigma_e' in results:
            plt.plot(results['time'], results['sigma_e'], label='Elastin')
        plt.title(f"Protocol: {args.protocol}")
    else:  
        for protocol, data in results.items():
            plt.plot(data['time'], data['sigma_total'], 
                   label=f"{protocol}")
        plt.title("Comparison of protocols")
    
    plt.xlabel('Time (days)')
    plt.ylabel('Stress (kPa)')
    plt.legend()
    plt.grid(True)
    plt.savefig(f"{base_filename}.png", dpi=300)
    plt.close()

def plot_interactive(results, protocol):
    plt.figure(figsize=(10, 6))
    if isinstance(results, dict) and 'time' in results:  
        if 'sigma_c' in results:
            plt.plot(results['time'], results['sigma_c'], label='Collagen')
        if 'sigma_e' in results:
            plt.plot(results['time'], results['sigma_e'], label='Elastin')
        if 'sigma_g' in results:
            plt.plot(results['time'], results['sigma_g'], label='Matrix')
        if 'sigma_total' in results:
            plt.plot(results['time'], results['sigma_total'], 'k--', label='Total stress')
        plt.title(f"Protocol: {protocol}")
    else:  
        for protocol_name, data in results.items():
            if 'sigma_total' in data:
                plt.plot(data['time'], data['sigma_total'], 
                       label=f"{protocol_name}")
        plt.title("Protocol comparison")
    
    plt.xlabel('Time (days)')
    plt.ylabel('Stress (kPa)')
    if any(plt.gca().get_legend_handles_labels()[0]): 
        plt.legend()
    plt.grid(True)
    plt.show()

def main():
    args = parse_arguments()
    results = run_simulation(args)
    if args.save:
        save_results(results, args.save)
        if not args.quiet:
            print(f"The results are saved in {args.save}.[npz/csv/png]")
    
    if not args.quiet:
        plot_interactive(results, args.protocol)

if __name__ == "__main__":
    main()