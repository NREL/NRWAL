__author__ = ["Jake Nunemaker"]
__copyright__ = "Copyright 2021, National Renewable Energy Laboratory"
__maintainer__ = "Jake Nunemaker"
__email__ = ["jake.nunemaker@nrel.gov"]


import os
import pytest
import numpy as np
import pandas as pd
from NRWAL import NrwalConfig
from copy import deepcopy

TEST_DIR = os.path.dirname(os.path.abspath(__file__))
TEST_DATA_DIR = os.path.join(TEST_DIR, 'data/')


@pytest.fixture
def ORCA():
    """ORCA System class for regression tests."""

    ORCA = pytest.importorskip("ORCA")  # Skip tests if ORCA isn't found
    return ORCA.System, ORCA.Data


@pytest.fixture
def base_2015():
    """"""

    return {
        "sub_install": "Vertical",
        "rna_capex_eq": "OW3F2015",
        "tower_capex_eq": "OW3F2015",
        "turbine_install_eq": "OW3F2015",
        "substructure_capex_eq": "OW3F2015",
        "sub_install_capex_eq": "OW3F2015",
        "foundation_capex_eq": "OW3F2015",
        "pslt_capex_eq": "OW3F2015",
        "grid_conn_capex_eq": "OW3F2015",
        "array_cable_capex_eq": "OW3F2015",
        "export_cable_capex_eq": "OW3F2015",
        "cost_reduction_year": 2015,
        "cost_reductions": "OW3F2015"
    }


@pytest.mark.parametrize(
    "case", (
        # Base Equations
        "monopile_6MW_2015.yaml",
        "monopile_8MW_2015.yaml",
        "monopile_10MW_2015.yaml",
        "jacket_6MW_2015.yaml",
        "jacket_8MW_2015.yaml",
        "jacket_10MW_2015.yaml",
        "semi_6MW_2015.yaml",
        "semi_8MW_2015.yaml",
        "semi_10MW_2015.yaml",
        "spar_6MW_2015.yaml",
        "spar_8MW_2015.yaml",
        "spar_10MW_2015.yaml",

        # Cost Reductions
        "monopile_10MW_2017.yaml",
        "monopile_10MW_2020.yaml",
        "monopile_10MW_2025.yaml",
        "semi_10MW_2017.yaml",
        "semi_10MW_2020.yaml",
        "semi_10MW_2025.yaml",
    ),
)
def test_ORCA_2015_base_regression(ORCA, base_2015, case):
    """"""

    System, Data = ORCA

    # Setup
    sub_type = case.split("_")[0].capitalize()
    if sub_type in ["Monopile", "Jacket"]:
        data_fp = os.path.join(TEST_DATA_DIR, "test_data", "fixed.csv")

    elif sub_type in ["Semi", "Spar"]:
        data_fp = os.path.join(TEST_DATA_DIR, "test_data", "floating.csv")

    else:
        print("Substructure type not recognized.")
        assert False

    turb_size = float(case.split("_")[1].replace("MW", ""))
    num_turbines = np.ceil(600 / turb_size)

    cr_year = int(case.split("_")[2].replace(".yaml", ""))

    # NRWAL
    inputs = pd.read_csv(data_fp).to_dict(orient='list')
    inputs["num_turbines"] = [num_turbines] * len(inputs['depth'])
    inputs["turbine_capacity"] = [turb_size] * len(inputs['depth'])
    inputs = {k: np.array(v) for k, v in inputs.items()}

    conf_fp = os.path.join(TEST_DATA_DIR, "orca_configs", "2015", case)
    conf = NrwalConfig(conf_fp, interp_extrap_power=True, interp_extrap_year=True)
    res = conf.eval(inputs)

    # ORCA
    data = Data(data_fp)
    system = System({
        "sub_tech": sub_type,
        "turbine_capacity": turb_size,
        **base_2015,
        **conf.global_variables,
        "cost_reduction_year": cr_year
    })

    assert np.allclose(res['turbine'], system.get_turbine_capex(data))
    assert np.allclose(res['turbine_install'], system.get_turbine_install_capex(data))
    
    assert np.allclose(res['substructure'], system.get_substructure_capex(data))
    assert np.allclose(res['foundation'], system.get_foundation_capex(data))
    assert np.allclose(res['sub_install'], system.get_substructure_install_capex(data))
    assert np.allclose(res['pslt'], system.get_pslt_capex(data))
    
    assert np.allclose(res['array'], system.get_array_cable_capex(data))
    assert np.allclose(res['export'], system.get_export_cable_capex(data))
    assert np.allclose(res['grid'], system.get_grid_conn_capex(data))
    
    assert np.allclose(res['support'], system.get_support_capex(data))
    assert np.allclose(res['install'], system.get_install_capex(data))
    assert np.allclose(res['electrical'], system.get_electric_system_capex(data))
    assert np.allclose(res['development'], system.development_capex(data))
    assert np.allclose(res['soft'], system.soft_capex(data))
    assert np.allclose(res['capex'], system.total_capex(data))

    assert np.allclose(res['maintenance'], system.maintenance_costs(data, **system.system_kwargs))
    assert np.allclose(res['opex'], system.total_opex(data))
    assert np.allclose(res['ncf'], system.get_ncf(data))
    assert np.allclose(res['lcoe'], system.lcoe(data))
