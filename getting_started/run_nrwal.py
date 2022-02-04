"""
This sample script loads the NRWAL getting started config file, sets a table of
input parameters, and evaluates the nrwal equations.
"""
import pandas as pd
from NRWAL import NrwalConfig

if __name__ == '__main__':
    # make sure you update this filepath
    con = NrwalConfig('/Users/gbuster/code/NRWAL/getting_started/config.yaml')
    print(con.missing_inputs)

    inputs = pd.DataFrame({'input1': [4, 5],
                           'input2': [6, 7],
                           'input3': [3, 2]})
    con.inputs = inputs
    out = con.eval()
    print(out)

    full = inputs.join(pd.DataFrame(out))
    print(full)
