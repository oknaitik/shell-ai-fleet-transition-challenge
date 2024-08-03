import numpy as np
import pandas as pd

class ModelInputs:
    def __init__(self, df_demand, df_vehicles, df_fuels, df_vehicles_fuels, df_carbon_emissions, df_cost_profiles, df_start=None):
        self.df_demand = df_demand 
        self.df_vehicles = df_vehicles
        self.df_fuels = df_fuels
        self.df_vehicles_fuels = df_vehicles_fuels
        self.df_carbon_emissions = df_carbon_emissions
        self.df_cost_profiles = df_cost_profiles
        self.df_start = df_start
 
    def processInputs(self):
        ymin = 0
        if self.df_start is None: # zero rows
            ymin = min(self.df_vehicles['Year'])
        else:
            ymin = max(self.df_start['Year']) + 1 # start from next year
            
        years = range(ymin, max(self.df_vehicles['Year']) + 1)
        sizes = list(self.df_demand['Size'].unique())
        distances = list(self.df_demand['Distance'].unique())
        fuels = list(self.df_fuels['Fuel'].unique())

        # subset the dataframes
        self.df_demand = self.df_demand[self.df_demand['Year'] >= years[0]]
        self.df_fuels = self.df_fuels[self.df_fuels['Year'] >= years[0]]
        self.df_carbon_emissions = self.df_carbon_emissions[self.df_carbon_emissions['Year'] >= years[0]]
        
        # Create dictionaries for easy access
        del_demand = 1e-6
        del_emissions = 1e-8
        del_range = 1e-8
        
        demand = {(row['Year'], row['Size'], row['Distance']): row['Demand (km)'] + del_demand for _, row in self.df_demand.iterrows()}
        vehicle_cost = {row['ID']: row['Cost ($)'] for _, row in self.df_vehicles.iterrows()}
        vehicle_range = {row['ID']: row['Yearly range (km)'] - del_range for _, row in self.df_vehicles.iterrows() }
        sb = {row['ID']: row['Size'] for _, row in self.df_vehicles.iterrows()}
        db = {row['ID']: row['Distance'] for _, row in self.df_vehicles.iterrows()}
        yrp = {row['ID']: int(row['ID'][-4:]) for _, row in self.df_vehicles.iterrows()}
        vehicle_fuel_consumption = {(row['ID'], row['Fuel']): row['Consumption (unit_fuel/km)'] for _, row in self.df_vehicles_fuels.iterrows()}
        fuel_emissions = {(row['Fuel'], row['Year']): row['Emissions (CO2/unit_fuel)'] for _, row in self.df_fuels.iterrows()}
        fuel_cost = {(row['Fuel'], row['Year']): row['Cost ($/unit_fuel)'] for _, row in self.df_fuels.iterrows()}
        # fuel_cost_uncertainty = {(row['Fuel'], row['Year']): row['Cost Uncertainty (±%)'] for _, row in self.df_fuels.iterrows()}
        carbon_limit = {row['Year']: row['Carbon emission CO2/kg'] - del_emissions for _, row in self.df_carbon_emissions.iterrows()}
        
        resale_rates = {row['End of Year']: 0.01 * row['Resale Value %'] for _, row in self.df_cost_profiles.iterrows()}
        insure_rates = {row['End of Year']: 0.01 * row['Insurance Cost %'] for _, row in self.df_cost_profiles.iterrows()}
        maintain_rates = {row['End of Year']: 0.01 * row['Maintenance Cost %'] for _, row in self.df_cost_profiles.iterrows()}

        return years, sizes, distances, fuels, demand, vehicle_cost, vehicle_range, sb, db, yrp, vehicle_fuel_consumption, fuel_emissions, fuel_cost, carbon_limit, resale_rates, insure_rates, maintain_rates
        
        
        