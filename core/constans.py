import numpy as np

DEFAULT_PARAMS = {
   # Mechanical properties
    'c_c': 1.0, # Collagen stiffness [kPa]
    'c_e': 50.0, # Elastin stiffness [kPa]
    'c_g': 10.0, # Proteoglycan matrix stiffness [kPa]
    
   # Initial Volume Fractions
    'fi0_c': 0.75, # Collagen
    'fi0_e': 0.05, # Elastin
    'fi0_g': 0.20, # Proteoglycans
    
   # Synthesis/degradation kinetics
    'k_cplus': 1.0, # Collagen synthesis rate [1/day]
    'k_cminus': 1.0, # Collagen degradation rate
    'k_eplus': 1.0, # For elastin
    'k_eminus': 1.0,
    
   # Stretch parameters
    'lambda0_c': 1.05, # Initial stretch of collagen
    'lambda0_e': 1.10, # For elastin
    'lambda_roof': 1.1, # Base tissue stretch
    'a': 0.1, # Stretching growth rate coefficient
    
   # Mechanical feedback
    'K_cplus': 0.04, # Feedback coefficient
    'sigma0_c': None, # Calculated automatically
    
   # Numerical parameters
    'alpha_c': 0.01, # Nonlinearity coefficient of collagen
    'gamma': 1.0, # Anisotropy parameter
    't_end': 10.0, # Simulation time [days]
    'n_points': 1000, # Number of sampling points
    'epsilon': 1e-4, # Iteration convergence criterion
    
   # Cyclic stretching parameters
    'omega': np.pi, # Frequency for cyclic mode (π from sin(πt))
}

J0 = 1.0                 
DEFAULT_TIME = np.linspace(0, DEFAULT_PARAMS['t_end'], DEFAULT_PARAMS['n_points'])

def get_parameters(overrides=None):
    params = DEFAULT_PARAMS.copy()
    
    if overrides:
        params.update(overrides)

    params['J0'] = 1.0 
    params['Jc0'] = params['fi0_c']
    params['Je0'] = params['fi0_e']
    params['Jg0'] = params['fi0_g']
    
    params['j_cplus'] = params['k_cplus'] * params['Jc0']
    params['j_eplus'] = params['k_eplus'] * params['Je0']
    
    if params['sigma0_c'] is None:
        Gx_c0 = params['Jc0'] ** (1.0 / (1.0 + 2.0 * params['gamma']))
        lambda_c0 = params['lambda0_c'] * Gx_c0 / Gx_c0  # = lambda0_c
        sigma_c_roof_0 = (4 * params['c_c'] * (lambda_c0**2) * 
                         (lambda_c0**2 - 1) * 
                         np.exp(params['alpha_c'] * (lambda_c0**2 - 1)**2))
        params['sigma0_c'] = (params['Jc0'] / params['J0']) * sigma_c_roof_0
    
    if params['k_cminus'] == 0 and params['k_cplus'] != 0:
        raise ValueError("k_cminus cannot be 0 when k_cplus != 0")
    
    if params['a'] <= 0:
        raise ValueError("Parameter 'a' must be > 0")
    
    if 'omega' not in params:
        params['omega'] = np.pi 
    
    params['time'] = np.linspace(0, params['t_end'], params['n_points'])
    
    return params
