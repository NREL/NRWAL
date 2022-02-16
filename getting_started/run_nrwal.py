"""
This sample script loads the NRWAL getting started config file, sets a table of
input parameters, and evaluates the nrwal equations.
"""
import pandas as pd
from NRWAL import NrwalConfig

if __name__ == '__main__':
    # make sure you update this filepath
    con = NrwalConfig('/Users/gbuster/code/NRWAL/getting_started/config.yaml')
    print('\nInput variables that need to be specified before we '
          'can evaluate the NRWAL object:',
          con.missing_inputs, end='\n\n')

    inputs = pd.DataFrame({'id': [42, 123],
                           'name': ['product1', 'product2'],
                           'input_price_1': [4, 5],
                           'input_price_2': [6, 7],
                           'input_variable_x': [3, 2]})
    print("Our input data table:")
    print(inputs, end='\n\n')
    con.inputs = inputs
    out = con.eval()
    print("NRWAL evaluation output:", out, end='\n\n')

    full = inputs.join(pd.DataFrame(out))
    print("Final data table that we can export:")
    print(full)
