import traceback

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import scipy.io
try:
    from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
    from matplotlib.figure import Figure
except:
    pass
from epyt import epanet


class WaterQualitySimulation:
    def __init__(self,
                 inpname,
                 msxname,
                 excel_file,
                 sensor_id = [],
                 t_d = 1,
                 msx_timestep = 300,
                 injection_rate = [],
                 MSX_uncertainty = [],
                 species_names = [],
                 species_types = [],
                 initial_concentration = [],
                 chemical_value = [],
                 chemical_param = [],
                 Demand_Uncertainty = [],
                 Input_Type = [],
                 scenario_id = []):
        """
        Initializes a Water Quality Simulation scenario set.

        Parameters:
        ----------
        inpname : str
            Path to the EPANET .inp file defining the water distribution network.

        msxname : str
            Path to the EPANET-MSX .msx file defining the chemical reactions and species.

        excel_file : pd.DataFrame
            A DataFrame (read from Excel) containing demand patterns or sensor data to support scenario calibration.

        sensor_id : list of str
            List of node IDs representing sensor or injection locations (aligned per scenario).

        t_d : int, default=1
            Duration of the simulation in days.

        msx_timestep : int, default=300
            Time step for MSX simulation in seconds (e.g., 300 = 5 minutes).

        injection_rate : list of float
            List of injection rates per scenario (used in Scenario 1: Injection Insertion).

        MSX_uncertainty : list of float
            List of uncertainty values (±%) for each scenario, typically for MSX reactions.

        species_names : list of str
            Species names (e.g., "THMs", "CL2") for each scenario.

        species_types : list of str
            Type of species being injected or set (e.g., "MASS", "CONCEN", "SETPOINT").

        initial_concentration : list of float
            Initial concentration values for each species (used in Scenario 2).

        chemical_value : list of float
            Numerical value for the chemical parameter in the MSX model (used in Scenario 3).

        chemical_param : list of str
            Names of chemical parameters being modified (used in Scenario 3).

        Demand_Uncertainty : list of float
            Demand uncertainty values (±%) for each scenario (used in Scenario 4).

        Input_Type : list of int
            Input type indicator per scenario:
                1 → Injection Insertion
                2 → Initial Concentration
                3 → Chemical Parameter
                4 → Demand Uncertainty

        scenario_id : list of int
            Scenario index, used to iterate over and reference scenario-specific parameters.

        patID : list of str or None
            Pattern ID(s) for demand patterns (optional, if pattern-based control is used).

        parameter_excel : list or None
            Additional parameter values extracted from the Excel file (optional).
        """
        self.inpname = inpname
        self.msxname = msxname
        self.excel_file = excel_file
        self.sensor_id = sensor_id
        self.t_d = t_d
        self.msx_timestep = msx_timestep

        # From parsed inputs
        self.injection_rate = injection_rate
        self.MSX_uncertainty = MSX_uncertainty
        self.species_names = species_names
        self.species_types = species_types
        self.initial_concentration = initial_concentration
        self.chemical_value = chemical_value
        self.chemical_param = chemical_param
        self.Demand_Uncertainty = Demand_Uncertainty
        self.Input_Type = Input_Type
        self.scenario_id = scenario_id
        #LOAD
        #self.DMAcenterorganics = self.load_data(excel_file, 'DMA_DP1')
        self.dataf = self.load_data_from_df(excel_file, "FCL")

        self.locarrays = []
        self.locations = []
        for loc, values_array in self.dataf.items():
            self.locarrays.append(values_array)
            self.locations.append(loc)
        self.initials = self.get_initial_values() #initial values for simulation
        self.means = self.compute_means() #mean values for simulation

        self.t_sim = self.t_d * 24 * 60 * 60

    def get_initial_values(self):
        """
        For each location in self.dataf, return the first element of its array
        as the initial value. If the array is empty, store None.
        """
        initial_values = {}
        for location, values_array in self.dataf.items():
            if len(values_array) > 0:
                initial_values[location] = values_array[0]
            else:
                initial_values[location] = None  # or float('nan')
        return initial_values
    def compute_means(self):
        """
        For each location in self.dataf, take the first `self.t_d * 12 * 24` elements
        and compute the mean, storing them in a dictionary.
        """
        slice_length = self.t_d * 12 * 24
        results_dict = {}
        for location, values_array in self.dataf.items():
            sliced_values = values_array[:slice_length]
            mean_val = np.mean(sliced_values) if len(sliced_values) > 0 else float('nan')
            results_dict[location] = mean_val

        return results_dict


    def load_data_from_df(self, df: pd.DataFrame, parameter: str = 'FCL') -> dict:
        """
        Given a pandas DataFrame, return a dictionary of sensor-location
        Parameters
        ----------
        df : pd.DataFrame
            The DataFrame containing at least the columns ['SensorLocation', 'ParameterName', 'time', 'value'].
        parameter : str, optional
.
        """
        if 'SensorLocation' not in df.columns:
            raise ValueError("No 'SensorLocation' column found in the data.")

        # Gather all unique sensor locations
        unique_locations = df['SensorLocation'].unique()
        all_data = {}
        for loc in unique_locations:
            # Filter data for each unique location
            param_data = df[(df['ParameterName'] == parameter) & (df['SensorLocation'] == loc)]
            values = param_data.sort_values(by='time', ascending = False)['value'].to_numpy()
            all_data[loc] = values

        return all_data

    def setup_simulation(self):

        self.G = epanet(self.inpname)
        self.G.loadMSXFile(self.msxname)
        self.species_names_function = self.G.getMSXSpeciesNameID()
        self.node_id = self.G.getNodeNameID()
        self.species_indices = [
            self.G.getMSXSpeciesIndex([name])[0] if name is not None else None
            for name in self.species_names
        ]
        self.sensor_index = [
            self.G.getNodeIndex(node) if node is not None else None
            for node in self.sensor_id
        ]
        # print("Setting up simulation...")
        self.G.setTimeSimulationDuration(self.t_sim)
        # self.G.setMSXTimeStep(self.msx_timestep)

        for i in range(len(self.Input_Type)):
            input_type = self.Input_Type[i]

            # Case 1 Injection-> inputs -> NodeID, Species, SpeciesType,
            #InjectionRate and Uncertainty
            if input_type == 1:
                node = self.sensor_id[i]
                specie = self.species_names[i]
                specie_type = self.species_types[i]
                rate = self.injection_rate[i]
                patID = f"pat{i}"
                # Warning in case the parse is wrong or csv.
                if node is None or specie is None or specie_type is None or rate is None:
                    print(f"[Warning] Missing data for Scenario {i}. Skipping.")
                    continue
                if node in self.locations:
                    # Use normalized pattern based on sensor data
                    norma = self.dataf[node] / self.means[node]
                    self.G.addMSXPattern(patID)
                    self.G.setMSXPattern(patID, norma)
                else:
                    # Fallback: use a flat pattern of 1s
                    self.G.addMSXPattern(patID)
                    self.G.setMSXPattern(patID, np.ones(1))

                # Check that the first case is correct
                # print(f"[Action {i + 1}] Injecting {specie} at {node} with rate {rate} using pattern {patID} (type:"
                #      f" {specie_type})")

                if specie_type == "Set Point Booster":
                    specie_type = 'SETPOINT'
                if specie_type == "Inflow Concentration":
                    specie_type = 'CONCEN'
                if specie_type == "Flow Paced Booster":
                    specie_type = 'FLOWPACED'
                if specie_type == "Mass Inflow Booster":
                    specie_type = 'MASS'
                if specie_type == "No Source": #need name for csv
                    specie_type = 'NOSOURCE'
                self.G.setMSXSources(node, specie, specie_type, rate, patID)
            #Case 2 InInputs NodeID, Species Initial Concetration Uncertainty
            if input_type == 2:
                node = self.sensor_id[i]
                node_index = self.sensor_index[i]
                species_index = self.species_indices[i]-1
                init_value = self.initial_concentration[i]

                # Warning in case the parse is wrong or csv.
                if node_index is None or species_index is None or init_value is None:
                    print(f"[Warning] Missing data for Scenario {i}. Skipping initial concentration.")
                    continue

                values = self.G.getMSXNodeInitqualValue()
                values[node_index - 1][species_index] = init_value
                # print(f"[Action {i + 1}] Setting initial concentration: {init_value} "
                #      f"→ Node: {node}, Species Name: {self.species_names[i]}")
                self.G.setMSXNodeInitqualValue(values)
            #Case 3 Inputs Chemical parameter Chemical Value
            if input_type == 3:
                param_name = self.chemical_param[i]
                param_value = self.chemical_value[i]

                # Warning in case the parse is wrong or csv.
                if param_name is None or param_value is None:
                    print(f"[Warning] Missing chemical param or value in Scenario {i}. Skipping.")
                    continue

                try:
                    param_index = self.G.getMSXParametersIndex([param_name])[0]
                    # test123 = self.G.getMSXParametersNameID([param_index])
                    # print(param_name,param_index,test123)
                except Exception as e:
                    print(f"[Action {i + 1 }] Error finding parameter '{param_name}': {e}")
                    continue

                # Apply to tanks
                for tank_index in self.G.getNodeTankIndex():
                    self.G.setMSXParametersTanksValue(tank_index, param_index, param_value)

                # Apply to pipes
                for pipe_index in self.G.getLinkPipeIndex():
                    self.G.setMSXParametersPipesValue(pipe_index, param_index, param_value)

                # print(f"[Action {i + 1}] Set chemical parameter '{param_name}' = {param_value} "
                #      f"→ Applied to all tanks and pipes.")
            #Demand Uncertainty
            if input_type == 4:
                continue


    def run_simulation(self):

        G = self.G
        # Run a single simulation without uncertainty
        MSX_comp = G.getMSXComputedQualityNode()
        self.MSX_comp = MSX_comp
        self.G.unloadMSX()
        self.G.unload()
        return self.MSX_comp, self.node_id, self.species_names_function

    def Measured_Chlorine(self):
        """Return measured chlorine data as a dictionary with padded arrays."""
        keys_list = list(self.dataf.keys())
        if not keys_list:  # this case should never trigger
            return {}

        arrays_dict = {}

        # Convert to NumPy arrays and check type
        for key in keys_list:
            array = self.dataf[key]

            if not isinstance(array, np.ndarray):
                array = np.array(array)
            if not np.issubdtype(array.dtype, np.number):
                raise TypeError(f"Array for key '{key}' contains non-numeric data.")

            arrays_dict[key] = array

        # Determine the maximum length among all arrays
        max_length = max(arr.shape[0] for arr in arrays_dict.values())

        # Pad arrays and build the result dictionary
        padded_dict = {}
        for key, arr in arrays_dict.items():
            current_length = arr.shape[0]
            if current_length < max_length:
                padding = np.zeros(max_length - current_length, dtype=arr.dtype)
                padded_arr = np.concatenate([arr, padding])
            else:
                padded_arr = arr[:max_length]  # Trim if too long
            padded_dict[key] = padded_arr

        return padded_dict

    def export_to_excel(self, results, output_file='computedtoexcel.xlsx', selected_nodes=None,
                        selected_species=None,
                        header=True):
        if not output_file.endswith('.xlsx'):
            output_file += '.xlsx'

        if not hasattr(results, 'Time') or not hasattr(results, 'Quality'):
            raise ValueError("Simulation results are not properly initialized or run.")

        time_data = results.Time
        species_list = self.species_names_function

        # Get node IDs and indices
        node_ids = self.node_id
        node_indices = list(range(len(node_ids)))

        # Filter nodes if selected_nodes is provided
        if selected_nodes:
            selected_node_indices = []
            for node in selected_nodes:
                if isinstance(node, str):  # Node ID
                    if node in node_ids:
                        selected_node_indices.append(node_ids.index(node))
                    else:
                        raise ValueError(f"Node ID '{node}' not found.")
                elif isinstance(node, int):  # Node index
                    if 0 <= node < len(node_ids):
                        selected_node_indices.append(node)
                    else:
                        raise ValueError(f"Node index '{node}' is out of range.")
                else:
                    raise ValueError(f"Invalid node identifier: {node}")
        else:
            selected_node_indices = node_indices

        # Filter species if selected_species is provided
        if selected_species:
            selected_species_indices = []
            for species in selected_species:
                if isinstance(species, str):  # Species name
                    if species in species_list:
                        selected_species_indices.append(species_list.index(species))
                    else:
                        raise ValueError(f"Species name '{species}' not found.")
                elif isinstance(species, int):  # Species index
                    if 0 <= species < len(species_list):
                        selected_species_indices.append(species)
                    else:
                        raise ValueError(f"Species index '{species}' is out of range.")
                else:
                    raise ValueError(f"Invalid species identifier: {species}")
        else:
            selected_species_indices = list(range(len(species_list)))

        with pd.ExcelWriter(output_file, engine='xlsxwriter') as writer:
            node_keys = list(results.Quality.keys())

            for species_index in selected_species_indices:
                species_name = species_list[species_index]
                species_data = []

                for node_index in selected_node_indices:
                    node_key = node_keys[node_index]
                    quality_data = np.array(results.Quality[node_key])

                    # If quality_data has an extra leading dimension
                    if quality_data.ndim == 3 and quality_data.shape[0] == 1:
                        quality_data = quality_data[0]

                    num_timesteps = len(time_data)
                    num_species = len(species_list)
                    expected_shape = (num_timesteps, num_species)

                    if quality_data.shape != expected_shape:
                        raise ValueError(
                            f"Node {node_key}: quality_data does not match expected shape {expected_shape}. "
                            f"Actual shape: {quality_data.shape}"
                        )
                    species_data.append(quality_data[:, species_index])

                species_data_array = np.array(species_data)

                df = pd.DataFrame(species_data_array, columns=time_data,
                                  index=[node_ids[i] for i in selected_node_indices])
                df.insert(0, 'NODE INDEX', [node_indices[i] for i in selected_node_indices])
                df.insert(1, 'NODE ID', [node_ids[i] for i in selected_node_indices])

                # If header is False, remove the first data row from df
                if not header and len(df) > 0:
                    df = df.iloc[1:].copy()

                sheet_name = f"{species_name}"
                # If header=False, no column headers will be written to the Excel sheet.
                df.to_excel(writer, index=False, sheet_name=sheet_name, header=header)

                worksheet = writer.sheets[sheet_name]
                worksheet.set_column('A:A', 13.0)

        # print(f"Data successfully written to {output_file}")

    def plot_data(self, measured_data, simulated_data, sensor_index, species_index, species_names, sensor_description,
                  subtitle=None, show_measured=True):
        # Create the figure and canvas
        figure = Figure(figsize=(10, 12))
        canvas = FigureCanvas(figure)

        # Plot data using the figure object
        k = 1
        for index_locations, i in enumerate(sensor_index):
            ax = figure.add_subplot(4, 1, k)
            sensor_name = sensor_description[index_locations]
            measured_array = measured_data.get(sensor_name)
            if measured_array is not None:
                ax.plot(measured_array[:288], label='Measured Chlorine') # for 1 day simulation
            else:
                print(f"Warning: No measured data found for sensor '{sensor_name}'")
            for index, sp_ind in enumerate(species_index):
                if sp_ind is None or i == 0:
                    continue
                quality_data = simulated_data[0].Quality[i][:, sp_ind-1]
                species_name = species_names[index]
                ax.plot(quality_data, label=f'{species_name}')

            if index_locations < len(sensor_description):
                ax.set_title(sensor_description[index_locations], fontsize='small')
            else:
                ax.set_title(f"Sensor {index_locations}", fontsize='small')

            if index_locations == len(sensor_index) - 1:
                ax.set_xlabel('Datetime (Minutes)')
            ax.set_ylabel('mg/L or ug/L')
            ax.legend(loc='upper right', fontsize='small')
            ax.grid(True)
            k += 1
        # Add a super title if specified
        if subtitle:
            figure.suptitle(subtitle, fontsize=16)
        # Adjust layout to avoid overlap
        figure.tight_layout(rect=[0, 0, 1, 0.96])
        # Render the canvas
        canvas.draw()
        return canvas

