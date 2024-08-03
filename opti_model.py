import numpy as np
import pandas as pd
import gurobipy as gp
from gurobipy import GRB
from inputs import ModelInputs
import time

def get_compatible_distances(d, distances):
    idx = distances.index(d)
    return distances[: idx + 1]
    
# Function to get compatible fuel types for a vehicle
def get_compatible_fuels(v):
    v_type = v.split('_')[0]
    if v_type == 'BEV':
        return ['Electricity']
    elif v_type == 'LNG':
        return ['LNG', 'BioLNG']
    return ['HVO', 'B20']
    
class OptiModel:
    def __init__(self, df_demand, df_vehicles, df_fuels, df_vehicles_fuels, df_carbon_emissions, df_cost_profiles, df_start=None):
        self.model = gp.Model('Fleet Optimization')
        self.demand_df = df_demand
        self.vehicles_df = df_vehicles
        self.fuels_df = df_fuels
        self.vehicles_fuels_df = df_vehicles_fuels
        self.carbon_emissions_df = df_carbon_emissions
        self.cost_profiles_df = df_cost_profiles
        # self.cost_profiles_path = cost_profiles_path
        self.start_df = df_start
        
        self.result_dict = None
        self.fleet = None

    def startFleet(self):
        if self.start_df is None:
            return {}

        # assuming that path string is valid
        # self.start_df = pd.read_csv(self.start_path)
        
        years = list(self.start_df['Year'].unique())
        vehicle_ids = list(self.start_df['ID'].unique())
        
        buy_df = self.start_df[self.start_df['Type'] == 'Buy'][['ID', 'Num_Vehicles']]
        buy_init = {v: 0 for v in vehicle_ids}
        for i in range(len(buy_df)):
            row = buy_df.iloc[i]
            buy_init[row['ID']] = row['Num_Vehicles']
        
        sell_df = self.start_df[self.start_df['Type'] == 'Sell'][['Year', 'ID', 'Num_Vehicles']]
        sell_init = {(yr, v): 0 for yr in years for v in vehicle_ids}
        for i in range(len(sell_df)):
            row = sell_df.iloc[i]
            sell_init[row['Year'], row['ID']] += row['Num_Vehicles']

        # compute vehicles in fleet at the end of last year
        last_year = years[-1]
        fleet = {v: 0 for v in vehicle_ids}
        for v in vehicle_ids:
            if self.yrp[v] <= last_year and last_year - self.yrp[v] < 10:
                fleet[v] += buy_init[v] - sum(sell_init[yrs, v] for yrs in range(self.yrp[v], last_year + 1)) # consider all sales till the end of last year
        return fleet

    def addConstraints(self):
        vehicle_ids = self.vehicle_cost.keys()
        
        for v in vehicle_ids:
            if self.yrp[v] not in self.years:
                self.model.addConstr(self.buy[v] == 0, name=f'no_buy_{v}')
                
        # sell are zero when vehicle yrp and year mismatch 
        for yr in self.years:
            for v in vehicle_ids:
                if self.yrp[v] > yr:
                    self.model.addConstr(self.sell[yr, v] == 0, name=f'no_sale_pre_yrp_{yr}_{v}')

        # no sale after ten-year time frame and in 2038
        for v in vehicle_ids:
            for yr in range(max(self.yrp[v] + 10, self.years[0]), self.years[-1] + 1):
                self.model.addConstr(self.sell[yr, v] == 0, name=f'no_sale_outside_ten_year_{yr}_{v}')
            self.model.addConstr(self.sell[self.years[-1], v] == 0, name=f'no_sale_{self.years[-1]}_{v}')

        # compute vehicles in fleet at the start of each year
        fleet = {yr: {v: 0 for v in vehicle_ids} for yr in self.years}
        for yr in self.years:
            for v in vehicle_ids:
                if self.yrp[v] <= yr and yr - self.yrp[v] < 10:
                    fleet[yr][v] += self.fleet_start.get(v, 0) + self.buy[v] - gp.quicksum(self.sell[yrs, v] for yrs in range(max(self.yrp[v], self.years[0]), yr))

        # sell as many ids in fleet and as many of each id in fleet
        for yr in self.years:
            for v in vehicle_ids:
                self.model.addConstr(self.sell[yr, v] <= fleet[yr][v], name=f'sell_within_fleet_{yr}_{v}')

        # ensure all vehicles that can reach their 10th year, are sold by that time
        for v in vehicle_ids:
            if self.yrp[v] + 9 < self.years[-1]:
                if self.yrp[v] in self.years:
                    self.model.addConstr(self.buy[v] == gp.quicksum(self.sell[yr, v] for yr in range(self.yrp[v], self.yrp[v] + 10)), name=f'sell_curr_by_10th_year_{v}')
                elif self.yrp[v] + 9 >= self.years[0]:
                    self.model.addConstr(gp.quicksum(self.sell[yr, v] for yr in range(self.years[0], self.yrp[v] + 10)) == self.fleet_start.get(v, 0), name=f'sell_prev_by_10th_year_{v}')

        # if incompatible fuel, total_distance[yr, v, f, d] = 0
        for yr in self.years:
            for v in vehicle_ids:
                for f in self.fuels:
                    for d in self.distances:
                        if f not in get_compatible_fuels(v) or d not in get_compatible_distances(self.db[v], self.distances):
                            self.model.addConstr(self.total_distance[yr, v, f, d] == 0, name=f'incompatible_fuel_or_distance_{yr}_{v}_{f}_{d}')
        
        # use an many ids in fleet and as many of each id in fleet
        EPS = 1e-12
        for yr in self.years:
            for v in vehicle_ids:
                self.model.addConstr(gp.quicksum(self.use[yr, v, f, d] for f in get_compatible_fuels(v) for d in get_compatible_distances(self.db[v], self.distances)) <= fleet[yr][v], name=f'use_within_fleet_{yr}_{v}')
                
                # Add constraints to enforce ceiling function
                for f in self.fuels:
                    for d in self.distances:
                        self.model.addConstr(self.total_distance[yr, v, f, d] <= self.use[yr, v, f, d] * self.vehicle_range[v], name=f'use_lb_{yr}_{v}_{f}_{d}')
                        self.model.addConstr(self.use[yr, v, f, d] * self.vehicle_range[v] <= self.total_distance[yr, v, f, d] + self.vehicle_range[v] * (1 - EPS), name=f'use_ub_{yr}_{v}_{f}_{d}')

        # carbon emissions limit
        for yr in self.years:
            self.model.addConstr(gp.quicksum(self.total_distance[yr, v, f, d] * self.vehicle_fuel_consumption.get((v, f), 0) * self.fuel_emissions[f, yr] for v in vehicle_ids for f in get_compatible_fuels(v) for d in get_compatible_distances(self.db[v], self.distances)) <= self.emissions_limit[yr], name=f'emissions_limit_{yr}')

        # 20pct sale constraint
        for yr in self.years:
            if yr < self.years[-1]:
               self.model.addConstr(gp.quicksum(self.sell[yr, v] for v in vehicle_ids) <= 0.2 * gp.quicksum(fleet[yr][v] for v in vehicle_ids), name=f'20pct_sale_{yr}')

        # meet Sx, Dx demands each year
        for yr in self.years:
            for s in self.sizes:
                for d in self.distances:
                    self.model.addConstr(gp.quicksum(self.total_distance[yr, v, f, d] for v in vehicle_ids for f in get_compatible_fuels(v) if self.sb[v] == s and d in get_compatible_distances(self.db[v], self.distances) and self.yrp[v] <= yr) >= self.demand.get((yr, s, d), 0), name=f'SxDx_demand_{yr}_{s}_{d}')
                    
        return fleet

    def setObjective(self, fleet):
        vehicle_ids = self.vehicle_cost.keys()
        
        cost_buy = gp.quicksum(self.buy[v] * self.vehicle_cost[v] for v in vehicle_ids)
        cost_fuel = gp.quicksum(self.total_distance[yr, v, f, d] * self.vehicle_fuel_consumption.get((v, f), 0) * self.fuel_cost[f, yr] for yr in self.years for v in vehicle_ids for f in get_compatible_fuels(v) for d in get_compatible_distances(self.db[v], self.distances))
        revenue_sell = gp.quicksum(self.sell[yr, v] * self.vehicle_cost[v] * self.resale_rates.get(yr - self.yrp[v] + 1, 0) for yr in self.years for v in vehicle_ids) + gp.quicksum(fleet[self.years[-1]][v] * self.vehicle_cost[v] * self.resale_rates.get(self.years[-1] - self.yrp[v] + 1, 0) for v in vehicle_ids)
        
        # insurance and maintenance costs
        cost_insure = gp.quicksum(fleet[yr][v] * self.vehicle_cost[v] * self.insure_rates.get(yr - self.yrp[v] + 1, 0) for yr in self.years for v in vehicle_ids)
        cost_maintain = gp.quicksum(fleet[yr][v] * self.vehicle_cost[v] * self.maintain_rates.get(yr - self.yrp[v] + 1, 0) for yr in self.years for v in vehicle_ids)
        
        self.model.setObjective(cost_buy + cost_fuel + cost_insure + cost_maintain - revenue_sell, GRB.MINIMIZE)

    def setParams(self, time_limit):
        # Set the solver parameters
        self.model.setParam('TimeLimit', time_limit)
        self.model.setParam('NumericFocus', 3)
        # self.model.setParam('Heuristics', 0.05)
        self.model.setParam('IntegralityFocus', 1)

    def runtime(self):
        return self.model.Params.TimeLimit
    
    def optimize(self):
        # Solve the model
        self.model.optimize()

    def insertRowToResult(self, result_dict, yr, v, n, t, f, d, dist):
        result_dict['Year'].append(yr)
        result_dict['ID'].append(v)
        result_dict['Num_Vehicles'].append(n)
        result_dict['Type'].append(t)
        result_dict['Fuel'].append(f)
        result_dict['Distance_bucket'].append(d)
        result_dict['Distance_per_vehicle(km)'].append(dist)
        
    def getResults(self):
        if self.result_dict is not None:
            return
        
        # compute fleet
        fleet = {yr: {v: 0 for v in self.vehicle_cost.keys()} for yr in self.years}
        for yr in self.years:
            for v in self.vehicle_cost.keys():
                if self.yrp[v] <= yr and yr - self.yrp[v] < 10:
                    fleet[yr][v] += self.fleet_start.get(v, 0) + self.buy[v].x - sum(self.sell[yrs, v].x for yrs in range(max(self.yrp[v], self.years[0]), yr))
    
        result_dict = {
            'Year': [], 'ID': [], 'Num_Vehicles': [], 'Type': [], 'Fuel': [], 'Distance_bucket': [], 'Distance_per_vehicle(km)': []
        }
        for yr in self.years:
            for v in self.vehicle_cost.keys():
                if self.yrp[v] == yr and self.buy[v].x > 1e-4:
                    self.insertRowToResult(result_dict, yr, v, int(np.round(self.buy[v].x)), 'Buy', '', '', 0)
                    
                for f in self.fuels:
                    for d in self.distances:
                        if self.use[yr, v, f, d].x > 1e-4:
                            self.insertRowToResult(result_dict, yr, v, int(np.round(self.use[yr, v, f, d].x)), 'Use', f, d, self.total_distance[yr, v, f, d].x/ self.use[yr, v, f, d].x)
        
                if self.sell[yr, v].x > 1e-4:
                    self.insertRowToResult(result_dict, yr, v, int(np.round(self.sell[yr, v].x)), 'Sell', '', '', 0)
                    
        yr = self.years[-1] # last year fleet must all be sold
        for v in self.vehicle_cost.keys():
            if fleet[yr][v] > 0:
                self.insertRowToResult(result_dict, yr, v, fleet[yr][v], 'Sell', '', '', 0)

        self.result_dict = result_dict
        self.fleet = fleet
        return

    def optGap(self):
        return self.model.MIPGap

    def create(self):
        model_inputs = ModelInputs(self.demand_df, self.vehicles_df, self.fuels_df, self.vehicles_fuels_df, self.carbon_emissions_df, self.cost_profiles_df, self.start_df)
        years, sizes, distances, fuels, demand, vehicle_cost, vehicle_range, sb, db, yrp, vehicle_fuel_consumption, fuel_emissions, fuel_cost, emissions_limit, resale_rates, insure_rates, maintain_rates = model_inputs.processInputs()

        self.years = years
        self.sizes = sizes 
        self.distances = distances
        self.fuels = fuels
        self.demand = demand
        self.vehicle_cost = vehicle_cost
        self.vehicle_range = vehicle_range
        self.sb = sb
        self.db = db 
        self.yrp = yrp
        self.vehicle_fuel_consumption = vehicle_fuel_consumption
        self.fuel_emissions = fuel_emissions
        self.fuel_cost = fuel_cost
        self.emissions_limit = emissions_limit
        self.resale_rates = resale_rates
        self.insure_rates = insure_rates
        self.maintain_rates = maintain_rates
        
        # Define decision variables
        NUM_UB = 100 # may vary
        DIST_UB = max(self.vehicle_range.values())
        TOTAL_DIST_UB = DIST_UB * NUM_UB

        vehicle_ids = self.vehicle_cost.keys()
        buy = self.model.addVars(vehicle_ids, lb=0, ub=NUM_UB, vtype=GRB.INTEGER, name="buy")
        sell = self.model.addVars(self.years, vehicle_ids, lb=0, ub=NUM_UB, vtype=GRB.INTEGER, name="sell")
        total_distance = self.model.addVars(self.years, vehicle_ids, self.fuels, self.distances, lb=0, ub=TOTAL_DIST_UB, vtype=GRB.CONTINUOUS, name="total_distance")
        use = self.model.addVars(self.years, vehicle_ids, self.fuels, self.distances, lb=0, ub=NUM_UB, vtype=GRB.INTEGER, name="use")

        self.buy = buy
        self.sell = sell
        self.total_distance = total_distance
        self.use = use
        
        # starting fleet
        self.fleet_start = self.startFleet()
        
        fleet = self.addConstraints() 
        self.setObjective(fleet) 
        
    def solve(self):
        # solve
        self.optimize()

        # reset
        self.result_dict = None
        self.fleet = None
        self.getResults()
        return self.result_dict, self.model.ObjBound, self.years[0], self.years[-1]

    def cost_breakdown(self, r, t='All', s='All'):
        self.getResults()
        df = pd.DataFrame.from_dict(self.result_dict)
        df = df[df['Year'].isin(range(r[0], r[1] + 1))]
        
        if t != 'All':
            df = df[df['ID'].str.split('_').str[0] == t]
        if df.empty or len(df) == 0:
            return {}
        
        if s != 'All':
            df = df[df['ID'].str.split('_').str[1] == s]  
        if df.empty or len(df) == 0:
            return {}  

        buy_mask = df['Type'] == 'Buy'
        df.loc[buy_mask, 'cost'] = df.loc[buy_mask, 'Num_Vehicles'] * df.loc[buy_mask, 'ID'].map(self.vehicle_cost)
        
        sell_mask = df['Type'] == 'Sell'
        df.loc[sell_mask, 'cost'] = df.loc[sell_mask, 'Num_Vehicles'] * df.loc[sell_mask, 'ID'].map(self.vehicle_cost) * (df.loc[sell_mask, 'Year'] - df.loc[sell_mask, 'ID'].map(self.yrp) + 1).map(self.resale_rates)
        # df.loc[sell_mask, 'cost'] *= -1

        use_mask = df['Type'] == 'Use'
        df.loc[use_mask, 'cost'] = (
            df.loc[use_mask, 'Distance_per_vehicle(km)'] * df.loc[use_mask, 'Num_Vehicles'] * 
            df.loc[use_mask].apply(lambda row: self.vehicle_fuel_consumption[(row['ID'], row['Fuel'])], axis=1) *
            df.loc[use_mask].apply(lambda row: self.fuel_cost[(row['Fuel'], row['Year'])], axis=1)
        )
        df['cost'] = df['cost'].round(1)
    
        cost_data = []
        category_map = {'Buy': 'Buy<br>Cost', 'Sell': 'Sell<br>Revenue', 'Use': 'Fuel<br>Cost'}
        for _, row in df.iterrows():
            cost_data.append({
                'Fuel': row['Fuel'] if row['Type'] == 'Use' else None,
                'ID': row['ID'],
                'Year': row['Year'],
                'Cat': category_map[row['Type']],
                'Cost': row['cost'], 
                # 'Total': 'Total<br>Cost'
            })

        # insurance and maintenance costs
        for yr in self.years:
            if yr >= r[0] and yr <= r[1]:
                for v in self.vehicle_cost.keys():
                    if (t == 'All' or v.split('_')[0] == t) and (s == 'All' or v.split('_')[1] == s):
                        cost_data.append({ 
                            'Fuel': None, 
                            'ID': v, 
                            'Year': yr, 
                            'Cat': 'Insurance<br>Cost', 
                            'Cost': round(self.fleet[yr][v] * self.vehicle_cost[v] * self.insure_rates.get(yr - self.yrp[v] + 1, 0), 1), 
                            # 'Total': 'Total<br>Cost'
                        })
                        cost_data.append({
                            'Fuel': None, 
                            'ID': v, 
                            'Year': yr, 
                            'Cat': 'Maintenance<br>Cost', 
                            'Cost': round(self.fleet[yr][v] * self.vehicle_cost[v] * self.maintain_rates.get(yr - self.yrp[v] + 1, 0), 1), 
                            # 'Total': 'Total<br>Cost'
                        })
        return pd.DataFrame(cost_data)

    def emissions_breakdown(self, r, t='All', s='All'):
        if t == 'BEV': # electric vehicles have no emissions
            return {}

        self.getResults()
        df = pd.DataFrame.from_dict(self.result_dict)
        df = df[(df['Type'] == 'Use') & (df['Year'].isin(range(r[0], r[1] + 1)))]
        
        if t != 'All': 
            df = df[(df['ID'].str.split('_').str[0] == t)]
        if df.empty or len(df) == 0:
            return {}
        
        if s != 'All': 
            df = df[(df['ID'].str.split('_').str[1] == s)]
        if df.empty or len(df) == 0:
            return {}
            
        # print(df) 
        df['Emissions'] = (
            df['Distance_per_vehicle(km)'] * df['Num_Vehicles'] * 
            df.apply(lambda row: self.vehicle_fuel_consumption[(row['ID'], row['Fuel'])], axis=1) *
            df.apply(lambda row: self.fuel_emissions[(row['Fuel'], row['Year'])], axis=1)
        )
        df['Emissions'] = df['Emissions'].round(1) 
        df['Total'] = 'Total<br>Emissions'
        return df[['Fuel', 'ID', 'Year', 'Emissions', 'Total']]

    def distance_covered_breakdown(self, r, t='All', s='All'):
        self.getResults()
        df = pd.DataFrame.from_dict(self.result_dict)
        df = df[(df['Type'] == 'Use') & (df['Year'].isin(range(r[0], r[1] + 1)))]
        
        if t != 'All':   
            df = df[(df['ID'].str.split('_').str[0] == t)]
        if df.empty or len(df) == 0:
            return {}
        
        if s != 'All':   
            df = df[(df['ID'].str.split('_').str[1] == s)]
        if df.empty or len(df) == 0:
            return {}
            
        df['Size'] = df['ID'].str.split('_').str[1]
        df['Distance'] = df['Num_Vehicles'] * df['Distance_per_vehicle(km)']
        df['Distance'] = df['Distance'].round(1)
        df['Total'] = 'Total<br>Distance'
        
        return df[['Fuel', 'ID', 'Distance_bucket', 'Size', 'Year', 'Distance', 'Total']]

    def buy_sell_filtered(self, r, t, s): 
        self.getResults()
        df = pd.DataFrame.from_dict(self.result_dict)
        df['ID_Year'] = df['ID'].str.split('_').str[2].astype(int)
        return df[(
            (df['Type'].isin(['Buy', 'Sell'])) & (df['Year'].isin(range(r[0], r[1] + 1))) & 
            (df['ID'].str.split('_').str[0] == t) & (df['ID'].str.split('_').str[1] == s)
        )][['Type', 'Year', 'Num_Vehicles', 'ID_Year']]
  
    def use_filtered(self, r, t, s, f, d):
        self.getResults()
        df = pd.DataFrame.from_dict(self.result_dict)
        df['ID_Year'] = df['ID'].str.split('_').str[2].astype(int)
        return df[(
            (df['Type'] == 'Use') & (df['Year'].isin(range(r[0], r[1] + 1))) & (df['ID'].str.split('_').str[0] == t) & 
            (df['ID'].str.split('_').str[1] == s) & (df['Fuel'] == f) & (df['Distance_bucket'] == d)
        )][['Year', 'ID_Year', 'Num_Vehicles']]
    
    def use_trend(self, r):
        self.getResults()
        df = pd.DataFrame.from_dict(self.result_dict)

        df = df[(df['Type'] == 'Use') & (df['Year'].isin(range(r[0], r[1] + 1)))]
        if df.empty or len(df) == 0:
            return {}
        
        df['Vehicle_Type'] = df['ID'].str.split('_').str[0]
        df = df.groupby(['Year', 'Vehicle_Type']).sum().reset_index()

        new_df = df[['Year', 'Vehicle_Type', 'Num_Vehicles']]
        # new_df = new_df.sort_values(['Year'])
        return new_df

    def emissions_trend(self, r):
        df = self.emissions_breakdown(r)
        df = df.groupby(['Year']).sum().reset_index()[['Year', 'Emissions']]

        df['Emissions_limit'] = [self.emissions_limit[yr] for yr in range(r[0], r[1] + 1)]
        df['Emissions_limit'] = df['Emissions_limit'].round(0)
        return df

    
        
 