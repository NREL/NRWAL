**********************************************************
Welcome to the Getting Started with NRWAL Example Project!
**********************************************************

Want to use NRWAL but don't want to contribute to the github repo? No problem! Follow these steps:

#. Create a new conda environment using python >= 3.7: ``conda create --name nrwal python=3.7``
#. Activate the new environment: ``conda activate nrwal``
#. Install NRWAL using the following command: ``pip install nrel-nrwal``
#. Copy this directory (everything in ``getting_started/``) somewhere on your local machine. This will be the main directory for your project.
#. Update the filepaths in ``config.yaml`` and ``run_nrwal.py`` to include this new project directory.
#. Run the following: ``python run_nrwal.py``
#. You should see some printouts of the evaluated equations.
#. Go ahead and build more equations in ``equations/model.yaml`` and reference them in the ``config.yaml`` file.
#. Build out your model and feel free to open a pull request if you want to contribute to the NRWAL library!
