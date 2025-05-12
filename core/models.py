import numpy as np
from scipy import integrate
from scipy.optimize import fsolve
import matplotlib.pyplot as plt

class ConstrainedMixtureModel:
    def __init__(self, params=None):
        self.params = self._validate_and_complete_params(params)
        self.results = {}
        self.all_protocol_results = {}
        if 'j_cplus' not in self.params:
            self.params['j_cplus'] = self.params['k_cplus'] * self.params['Jc0']
        if 'j_eplus' not in self.params:
            self.params['j_eplus'] = self.params['k_eplus'] * self.params['Je0']

    def _validate_and_complete_params(self, params):
        default_params = {
            # Mechanical properties
            'c_c': 1.0, 'c_e': 50.0, 'c_g': 10.0,
            # Initial volume fractions
            'fi0_c': 0.75, 'fi0_e': 0.05, 'fi0_g': 0.20,
            # Remodeling parameters
            'k_cplus': 1.0, 'k_cminus': 1.0, 'k_eplus': 1.0, 'k_eminus': 1.0,
            # Stretching parameters
            'lambda0_c': 1.05, 'lambda0_e': 1.10, 'lambda_roof': 1.1, 'a': 0.1,
            # Mechanical feedback
            'K_cplus': 0.04, 'sigma0_c': None,
            # Numerical parameters
            'alpha_c': 0.01, 'gamma': 1.0, 't_end': 10.0, 'n_points': 1000
        }
        
        complete_params = {**default_params, **(params or {})}
        
        # Automatic calculation of derived parameters
        complete_params['time'] = np.linspace(0, complete_params['t_end'], 
                                           complete_params['n_points'])
        complete_params['J0'] = 1.0
        complete_params['Jc0'] = complete_params['fi0_c']
        complete_params['Je0'] = complete_params['fi0_e']
        complete_params['Jg0'] = complete_params['fi0_g']
        
       # Calculation of homeostatic tension
        if complete_params['sigma0_c'] is None:
            Gx_c0 = complete_params['Jc0']**(1/(1 + 2*complete_params['gamma']))
            lambda_c0 = complete_params['lambda0_c']
            sigma_c_roof = self._sigma_c_roof(lambda_c0)
            complete_params['sigma0_c'] = (complete_params['Jc0']/complete_params['J0']) * sigma_c_roof
        
        return complete_params

    def simulate_all_protocols(self, feedback=False):
        protocols = ['constant', 'linear', 'cyclic']
        self.all_protocol_results = {}
        
        for protocol in protocols:
            self.all_protocol_results[protocol] = self.simulate(protocol, feedback)
        
        return self.all_protocol_results

    def simulate(self, protocol, feedback=False):
        protocol_funcs = {
            'constant': self._constant_protocol,
            'linear': self._linear_protocol,
            'cyclic': self._cyclic_protocol
        }
        
        if protocol not in protocol_funcs:
            raise ValueError(f"Unknown protocol: {protocol}")
        
        results = protocol_funcs[protocol]()
        
        if feedback:
            results = self._apply_mechanical_feedback(results)
        results['J_total'] = results.get('J_c', 0) + results.get('J_e', 0) + self.params['Jg0']
        results['sigma_total'] = results.get('sigma_c', 0) + results.get('sigma_e', 0) + results.get('sigma_g', 0)
        
        self.results = results
        return results
    
    def _constant_protocol(self):
        t = self.params['time']
        lambda_t = self.params['lambda_roof']
        
        results = {
            'time': t,
            'lambda': np.full_like(t, lambda_t),
            'sigma_c': np.zeros_like(t),
            'sigma_e': np.zeros_like(t),
            'sigma_g': np.zeros_like(t),
            'J_c': np.zeros_like(t),
            'J_e': np.zeros_like(t)
        }
        
        for i, ti in enumerate(t):
            Q_c = self._Q_c(ti)
            Q_e = self._Q_e(ti)
            results['J_c'][i] = self.params['Jc0'] * Q_c
            results['J_e'][i] = self.params['Je0'] * Q_e
            results['sigma_c'][i] = self._sigma_c_roof(lambda_t) * results['J_c'][i]
            results['sigma_e'][i] = 4 * self.params['c_e'] * lambda_t**2 * (lambda_t**2 - 1) * results['J_e'][i]
            results['sigma_g'][i] = self._calc_sigma_g(ti, lambda_t)
        
        return results

    def _linear_protocol(self):
        t = self.params['time']
        results = {
            'time': t,
            'lambda': self.params['lambda_roof'] * (1 + self.params['a'] * t),
            'sigma_c': np.zeros_like(t),
            'sigma_e': np.zeros_like(t),
            'sigma_g': np.zeros_like(t),
            'J_c': np.zeros_like(t),
            'J_e': np.zeros_like(t)
        }
        
        for i, ti in enumerate(t):
            lambda_t = results['lambda'][i]
            def integrand_c(tau):
                return self._q_c(tau, ti) * self._sigma_c_roof(lambda_t)
            
            def integrand_e(tau):
                return self._q_e(tau, ti) * 4 * self.params['c_e'] * lambda_t**2 * (lambda_t**2 - 1)
            
            integral_c, _ = integrate.quad(integrand_c, 0, ti)
            integral_e, _ = integrate.quad(integrand_e, 0, ti)
            Q_c = self._Q_c(ti)
            Q_e = self._Q_e(ti)
            results['J_c'][i] = self.params['Jc0'] * Q_c
            results['J_e'][i] = self.params['Je0'] * Q_e
            
            results['sigma_c'][i] = (self.params['Jc0']/self.params['J0']) * self._sigma_c_roof(lambda_t) * self._q_c(0, ti) + \
                                   (self.params['j_cplus']/results['J_c'][i]) * integral_c
            
            results['sigma_e'][i] = (self.params['Je0']/self.params['J0']) * 4 * self.params['c_e'] * lambda_t**2 * (lambda_t**2 - 1) * self._q_e(0, ti) + \
                                   (self.params['j_eplus']/results['J_e'][i]) * integral_e
            
            results['sigma_g'][i] = self._calc_sigma_g(ti, lambda_t)
        
        return results

    def _cyclic_protocol(self):
        t = self.params['time']
        n = len(t)
        results = {
            'time': t,
            'lambda': np.zeros(n),
            'sigma_c': np.zeros(n),
            'sigma_e': np.zeros(n),
            'sigma_g': np.zeros(n),
            'J_c': np.zeros(n),
            'J_e': np.zeros(n),
            'J_total': np.zeros(n)
        }
        
        a = self.params['a']
        lambda_roof = self.params['lambda_roof']
        omega = np.pi 
        
        for i, ti in enumerate(t):
            try:
                results['lambda'][i] = lambda_roof * (1 + a * np.sin(omega * ti)**2)
                lambda_t = results['lambda'][i]
                Q_c = self._Q_c(ti)
                Q_e = self._Q_e(ti)
                results['J_c'][i] = self.params['Jc0'] * Q_c
                results['J_e'][i] = self.params['Je0'] * Q_e
                results['J_total'][i] = results['J_c'][i] + results['J_e'][i] + self.params['Jg0']
                def integrand_c(tau):
                    lambda_tau = lambda_roof * (1 + a * np.sin(omega * tau)**2)
                    G_ratio = (self._G_c(tau) / self._G_c(ti)) ** (1/(1 + 2*self.params['gamma']))
                    lambda_cx = self.params['lambda0_c'] * (lambda_t/lambda_tau) * G_ratio
                    return self._q_c(tau, ti) * self._sigma_c_roof(lambda_cx)
                
                def integrand_e(tau):
                    lambda_tau = lambda_roof * (1 + a * np.sin(omega * tau)**2)
                    G_ratio = (self._G_e(tau) / self._G_e(ti)) ** (1/(1 + 2*self.params['gamma']))
                    lambda_ex = self.params['lambda0_e'] * (lambda_t/lambda_tau) * G_ratio
                    return self._q_e(tau, ti) * 4 * self.params['c_e'] * lambda_ex**2 * (lambda_ex**2 - 1)
                
                integral_c, _ = integrate.quad(integrand_c, 0, ti, limit=100)
                integral_e, _ = integrate.quad(integrand_e, 0, ti, limit=100)

                lambda_c0 = self.params['lambda0_c'] * (lambda_t/self.params['lambda_roof']) * \
                        (self._G_c(0)/self._G_c(ti)) ** (1/(1 + 2*self.params['gamma']))
                
                sigma_c_initial = (self.params['Jc0']/self.params['J0']) * \
                                self._sigma_c_roof(lambda_c0) * \
                                self._q_c(0, ti)
                
                sigma_c_integral = (self.params['j_cplus']/results['J_total'][i]) * integral_c
                results['sigma_c'][i] = sigma_c_initial + sigma_c_integral
            
                lambda_e0 = self.params['lambda0_e'] * (lambda_t/self.params['lambda_roof']) * \
                        (self._G_e(0)/self._G_e(ti)) ** (1/(1 + 2*self.params['gamma']))
                
                sigma_e_initial = (self.params['Je0']/self.params['J0']) * \
                                4 * self.params['c_e'] * lambda_e0**2 * (lambda_e0**2 - 1) * \
                                self._q_e(0, ti)
                
                sigma_e_integral = (self.params['j_eplus']/results['J_total'][i]) * integral_e
                results['sigma_e'][i] = sigma_e_initial + sigma_e_integral
                
                results['sigma_g'][i] = self._calc_sigma_g(ti, lambda_t)
                
            except Exception as e:
                print(f"Error in step {i}, t={ti}: {str(e)}")
                raise
        
        results['sigma_total'] = results['sigma_c'] + results['sigma_e'] + results['sigma_g']
        
        return results

    def _apply_mechanical_feedback(self, results):
        t = self.params['time']
        n = len(t)
        dt = t[1] - t[0] if n > 1 else 0
        sigma_c_fb = np.zeros(n)
        J_c_fb = np.zeros(n)
        sigma_c_fb[0] = results['sigma_c'][0]
        J_c_fb[0] = self.params['Jc0']
        
        K_cplus = self.params['K_cplus']
        sigma0_c = sigma_c_fb[0] 
        k_cplus = self.params['k_cplus']
        epsilon = self.params['epsilon']
        
        for i in range(1, n):
            ti = t[i]
            max_iter = 20
            converged = False
            sigma_prev = results['sigma_c'][i]
            J_prev = results['J_c'][i]
            
            for _ in range(max_iter):
                sigma_ratio = sigma_prev / sigma0_c
                feedback_factor = 1 + K_cplus * (sigma_ratio - 1)
                integral_sigma = 0
                integral_J = 0
                
                for j in range(1, i+1):
                    tj = t[j]
                    dtj = t[j] - t[j-1] if j > 0 else 0
                    J_tj = J_c_fb[j] if j < i else J_prev
                    sigma_tj = sigma_c_fb[j] if j < i else sigma_prev
                    J_tj_1 = J_c_fb[j-1]
                    sigma_tj_1 = sigma_c_fb[j-1]
                    if self.params['protocol'] == 'constant':
                        lambda_tau = self.params['lambda_roof']
                    elif self.params['protocol'] == 'linear':
                        lambda_tau = self.params['lambda_roof'] * (1 + self.params['a'] * tj)
                    else:  # cyclic
                        lambda_tau = self.params['lambda_roof'] * (1 + self.params['a'] * np.sin(np.pi * tj)**2)

                    term_sigma = J_tj * k_cplus * feedback_factor * self._sigma_c_roof(lambda_tau) * self._q_c(tj, ti)
                    term_J = J_tj * k_cplus * feedback_factor * self._q_c(tj, ti)
                
                    integral_sigma += 0.5 * dtj * term_sigma
                    integral_J += 0.5 * dtj * term_J
                
                J_total = J_prev + results['J_e'][i] + self.params['Jg0']
                
                sigma_new = (self.params['Jc0']/self.params['J0']) * \
                        self._sigma_c_roof(lambda_tau) * self._q_c(0, ti) + \
                        (1/J_total) * integral_sigma
                
                J_new = self.params['Jc0'] * self._q_c(0, ti) + integral_J
                
                if (np.abs(sigma_new - sigma_prev) < epsilon and 
                    np.abs(J_new - J_prev) < epsilon):
                    converged = True
                    break
                    
                sigma_prev = sigma_new
                J_prev = J_new
            
            if not converged:
                print(f"Warning: convergence not reached at step {i}")
            sigma_c_fb[i] = sigma_new
            J_c_fb[i] = J_new
        
        results['sigma_c'] = sigma_c_fb
        results['J_c'] = J_c_fb
        results['sigma_total'] = sigma_c_fb + results['sigma_e'] + results['sigma_g']
        
        return results

    def _q_c(self, tau, t):
        return np.exp(-self.params['k_cminus'] * (t - tau))

    def _sigma_c_roof(self, lambda_):
        return (4 * self.params['c_c'] * lambda_**2 * 
            (lambda_**2 - 1) * 
            np.exp(self.params['alpha_c'] * (lambda_**2 - 1)**2))
    def _G_c(self, t):
        if t == 0:
            return self.params['Jc0'] ** (1/(1 + 2*self.params['gamma']))
        return self._calc_J_c(t) ** (1/(1 + 2*self.params['gamma']))

    def _G_e(self, t):
        if t == 0:
            return self.params['Je0'] ** (1/(1 + 2*self.params['gamma']))
        return self._calc_J_e(t) ** (1/(1 + 2*self.params['gamma']))

    def _calc_J_c(self, t):
        return self.params['Jc0'] * self._Q_c(t)

    def _calc_J_e(self, t):
        return self.params['Je0'] * self._Q_e(t)

    def _Q_c(self, t):
        if self.params['k_cminus'] == 0 and self.params['k_cplus'] == 0:
            return 1.0
        return (np.exp(-self.params['k_cminus'] * t)) + \
            (self.params['k_cplus']/self.params['k_cminus']) * \
            (1.0 - np.exp(-self.params['k_cminus'] * t))

    def _q_e(self, tau, t):
        return np.exp(-self.params['k_eminus'] * (t - tau))
    
    def _Q_e(self, t):
        if self.params['k_eminus'] == 0 and self.params['k_eplus'] != 0:
            return 1.0
        return (np.exp(-self.params['k_eminus'] * t)) + \
            (self.params['k_eplus']/self.params['k_eminus']) * \
            (1.0 - np.exp(-self.params['k_eminus'] * t))
            
    def _calc_sigma_g(self, t, lambda_t):
        return (self.params['Jg0']/self.params['J0']) * \
            4 * self.params['c_g'] * lambda_t**2 * (lambda_t**2 - 1)
