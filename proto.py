import dash
from dash import html, dash_table, dcc, Input, Output, State, callback
import dash_bootstrap_components as dbc
import base64
import io
import pandas as pd
# import os
from opti_model import OptiModel
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots

# Initialize the app
app = dash.Dash(__name__, external_stylesheets=[
    dbc.themes.BOOTSTRAP
])


def create_upload_component(id, label, icon_file, info_mark_text=None, info_mark_id=None):
    return html.Div([
        html.Div([
            html.Img(src=f'/assets/{icon_file}', style={
                'height': '18px',  # Adjust as needed
                'width': '18px',   # Adjust as needed
                'marginLeft': '5px',
                'marginRight': '4px', 
                'verticalAlign': 'middle'
            }),
            html.Div(label + ('' if info_mark_text else '*'), style={'textAlign': 'left', 'display': 'inline-block', 'fontWeight': '400'}),
            info_mark(info_text=info_mark_text, id=info_mark_id) if info_mark_text else None
        ], style={'width': '180px', 'display': 'flex', 'alignItems': 'center'}), 
        dcc.Upload(
            id=f'upload-{id}',
            children=html.Div(['Drag and Drop or ', html.A('Select File')]),
            style={
                'width': '100%', 'height': '23px', 'lineHeight': '20px', 
                'borderWidth': '1px', 'borderStyle': 'solid', 'borderColor': 'lightGrey',
                'borderRadius': '5px', 'textAlign': 'center', 
                'fontSize': '13px', 'display': 'inline-block', 
                'color': 'white', 'background': '#226220d6', 
                'padding': '0 16px', 'fontWeight': '300'
            }, 
            multiple=False # *addition*
        ), 
        html.Div(id=f'file-name-{id}', style={'fontSize': '12px', 'marginLeft': '4px'})
    ], style={'width': '100%', 'display': 'flex', 'flexDirection': 'row',  'alignItems': 'center', 'marginBottom': '3px'})

def create_button(text, id, margin_top=0, disabled=False, width='35%'):
    return dbc.Button(text, id=id,  disabled=disabled, style={
        'borderRadius': '30px', 
        # 'padding': '8px 24px', 
        'background': 'rgb(34 98 32)', 
        'border': 'none',
        'width': width, 
        'marginTop': margin_top,
        'paddingTop': '8px', 
        'paddingBottom': '8px', 
    })

def create_cost_box(id, name, icon_link, s):
    return html.Div(
        style={
            'display': 'flex', 'flexDirection': 'row', 
            'height': '76px', 'width': '166px', 
            # 'border': '1px solid grey', 
            'boxShadow': 'rgb(210, 210, 210) 2px 2px 3px 1px', 
        },
        children=[
            html.Div([
                dcc.Loading(
                    id=f"loading-figure-{id}",
                    children=[html.Div(id=f'figure-{id}', style={'textAlign': 'center', 'display': 'flex', 'alignItems': 'center', 'justifyContent': 'center', 'fontSize': '30px'})],
                    type="default",
                ),
                html.Div(id=f'figure-best-{id}', style={'fontSize': '10px'}),
                html.Div([name], style={'fontSize': '14px'})
            ], style={
                'display': 'flex', 'flexDirection': 'column', 
                'justifyContent': 'center', 'alignItems': 'start', 
                'width': '130px',  'color': 'rgb(80, 80, 80)', 
                'paddingLeft': '6px', 'backgroundColor': 'rgb(212 236 211)'
            }),
            html.Div(
                html.Img(src=icon_link, style={
                    'height': s,  # Adjust as needed
                    'width': s,   # Adjust as needed),
                }),
                style={
                    'width': '40px',
                    'textAlign': 'center', 
                    'display': 'flex', 
                    'alignItems': 'center', 
                    'justifyContent': 'center', 
                    'backgroundColor': 'rgb(34 98 32)'
                }
            )
        ]
    )

def create_radio_items(items, value, id):
    return dcc.RadioItems(
        options=[{'label': x, 'value': x} for x in items], # all option added in callback
        value=value,
        id=id, 
        inline=True, 
        inputStyle={"margin-right": "3px"},  
        labelStyle={"margin-right": "30px"}, 
        style={'display': 'inline-block'}
    )

def add_integer_ticks_xaxis(fig):
    fig.update_xaxes(
        tickmode='linear',
        dtick=1,
        tickformat='d'  # 'd' format specifier for integers
    )

def center_title(fig):
    fig.update_layout(
        title={
            'x': 0.5,
            'xanchor': 'center',
            'yanchor': 'top'
        }
    )
    return fig

def add_text_empty_plot(fig):
    fig.add_annotation(
        text="Data unavailable. Kindly try tweaking choices.",
        xref="paper", yref="paper",
        x=0.5, y=0.5,
        showarrow=False,
        font=dict(size=18) #, color="", family="Arial")
    )
    return fig

toggle_button_style = {
    'borderRadius': '30px', 
    'border': 'none', 
    'width': '120px',
    'background': 'rgb(34 98 32)', 
    'color': 'white', 
    'fontWeight': '400', 
    'padding': '8px'
    # 'transition': 'background-color 0.3s, color 0.3s'
}

# Navbar component
navbar = dbc.Navbar(
    [
        html.Div([
            html.Img(src=f'/assets/shell-logo.png', style={
                'height': '36px',  # Adjust as needed
                'width': '42px',   # Adjust as needed
                # 'marginLeft': '5px',
                'verticalAlign': 'middle', 
                'marginRight': '4px'
            }), 
            html.Div(style={'border': '1px solid rgb(120 120 120)', 'marginRight': '8px', 'height': '34px'}), 
            dbc.NavbarBrand("FLEET DECARBONIZATION", style={'fontSize': '16px', 'color': 'rgb(80 80 80)', 'fontWeight': '400'}),
        ], style={'display': 'flex', 'flexDirection': 'row', 'alignItems': 'center'}),
        dbc.Button(
            "Input", id="toggle-btn", className="ml-auto", n_clicks=0, style=toggle_button_style
        ),
    ],
    style={
        'display': 'flex', 
        'flexDirection': 'row', 
        'justifyContent': 'space-between', 
        'position': 'sticky',
        'padding': '12px 40px', 
        'top': '0', 
        'zIndex': '1000',
    },
    color="rgb(252, 252, 252)",
    # light=True,
)

toggle_switch = dbc.Switch(
    id='toggle-switch',
    # label="Toggle Me",
    value=False  # Initial value
)

input_content_style = {
    'width': '580px', 
    'height': 'auto', 
    # 'display': 'block', 
    'padding': '30px',
    'backgroundColor': 'rgb(199 221 198)', 
    # 'boxShadow': '#226220 8px 8px 0px 0px', 
    'borderRadius': '8px', 
    # 'marginLeft': '50%'
    # 'border': '1px solid black'
}

background_style = {
    'backgroundColor': 'rgb(205 232 205)',
    'backgroundImage': 'url("assets/aerial-view-bridge-creek-powerlines-with-cars-road-lg.jpg")',
    'backgroundSize': 'cover',
    'backgroundPosition': 'center',
    'backgroundRepeat': 'no-repeat', 
    'height': '100vh', 
    'width': '100vw', 
    'position': 'fixed', 
    'top': '0',
    'left': '0',
    # 'filter': 'blur(1px)',
    'zIndex': '-1',
}

input_wrapper_style = {
    'height': '100vh',
    'width': '100vw',
    'position': 'relative',
    # 'zIndex': '1',
    'display': 'block',
}
output_wrapper_style = {
    'height': '100vh',
    'width': '100vw',
    'position': 'relative',
    # 'zIndex': '1',
    'display': 'none',
}

output_content_style = {
    'width': '1400px', 
    'padding': '30px',
    'borderRadius': '8px', 
    'backgroundColor': '#eff8ee', 
}

def info_mark(info_text, id):
    return html.Div([
        dbc.Button(
            "?", 
            id=f"info-mark-{id}", 
            className="rounded-circle p-0", 
            style={
                "width": "16px",  # Reduced from 20px
                "height": "16px",  # Reduced from 20px
                "font-size": "10px",  # Reduced from 12px
                "display": "inline-flex",
                "align-items": "center",
                "justify-content": "center",
                "vertical-align": "middle",
                "line-height": "1",
                "padding": "0"
            }
        ), 
        dbc.Tooltip(
            info_text,
            target=f"info-mark-{id}",
        )
    ], style={'marginLeft': '6px'})

def parse_contents(contents, filename):
    content_type, content_string = contents.split(',')
    decoded = base64.b64decode(content_string)

    # Assume that the user uploaded a CSV file
    df = pd.read_csv(io.StringIO(decoded.decode('utf-8')))
    return df


# Define the layout
app.layout = dbc.Container([
    navbar, 
    html.Div(style=background_style),

    html.Div([  
        dbc.Container([
            html.Div(children=[
                html.Div([
                    html.Div(['Upload Data Files ', html.I('(*Mandatory)', style={'color': 'red'})], style={'fontWeight': '500', 'marginLeft': '6px'}),
                    html.Div(
                        [
                            create_upload_component('demand', 'Demand', 'demand.png'),
                            create_upload_component('fuels', 'Fuels', 'fuels.png'),
                            create_upload_component('vehicles', 'Vehicles', 'vehicles.png'),
                            create_upload_component('vehicles-fuels', 'Vehicles Fuels', 'vehicles_fuels.png'),
                            create_upload_component('cost-profiles', 'Cost Profiles', 'cost_profiles.png'),
                            create_upload_component('carbon-emissions', 'Carbon Emissions', 'carbon_emissions.png')
                        ], 
                        style={
                            # 'border': '1px solid black',
                            # 'box-shadow': '0 0 4px 6px rgb(50 50 50)', 
                            'borderRadius': '5px', 
                            'padding': '8px', 
                            'backgroundColor': 'rgb(236 254 235)'
                        }
                    ), 
                    
                    html.Div(
                        [
                            create_upload_component(
                                'start', 'Updated Data', 'file-pencil.png', 
                                info_mark_text='(Optional) If you have updated data upto a particular year and want to run the model for future years, please upload the file here.', 
                                info_mark_id='upload-data'
                            ), 
                            # info_mark()
                        ], 
                        style={
                            # 'border': '1px solid black', 
                            'display': 'flex', 'flexDirection': 'row', 
                            'marginTop': '16px', 'alignItems': 'center', 
                            'borderRadius': '4px', 
                            'padding': '4px', 
                            'backgroundColor': 'rgb(236 254 235)'
                        }
                    ),
                    
                    html.Div([
                        create_button(text='Submit', id='submit-btn'),
                        html.Div(id='submit-message', style={'fontSize': '14px', 'marginLeft': '10px', }), 
                    ], style={
                        'display': 'flex', 
                        'flexDirection': 'row', 
                        'justifyContent': 'spaceBetween', 
                        'alignItems': 'center', 
                        'marginTop': '20px'
                    }),
                ]), 
                create_button(text='View', id='open-view-inputs-overlay', margin_top='6px'),
                dbc.Modal([
                    dbc.ModalHeader(
                        dbc.ModalTitle("Input Files"),
                        close_button=True,
                    ),
                    dbc.ModalBody([
                        dcc.Dropdown(
                            id="inputs-dropdown",
                            placeholder="Select a file",
                            className="mb-3"
                        ),
                        html.Div(id="inputs-table-container")
                    ]),
                    dbc.ModalFooter(
                        dbc.Button("Close", id="close-view-inputs-overlay", className="ml-auto", style={
                            'borderRadius': '30px', 
                            'padding': '6px 30px', 
                            'background': 'rgb(34 98 32)', 
                            'border': 'none',
                        })
                    ),
                ], id="view-inputs-overlay", is_open=False, size='xl'), 

                html.Div([
                    create_button(text='Create', id='create-btn',),
                    dcc.Loading(
                        id='loading-create-model', 
                        children=[html.Div(id='model-message', style={'fontSize': '14px', 'marginLeft': '10px', 'width': '300px'})], 
                        type="default",
                    )
                ], style={'display': 'flex', 'flexDirection': 'row', 'alignItems': 'center', 'marginTop': '22px'}),
                
                html.Div([
                    # html.Div(['Model Parameters']), 
                    html.Div([
                        html.Div([
                            html.Div([
                                html.Img(src=f'/assets/time.png', style={
                                    'height': '18px',  # Adjust as needed
                                    'width': '18px',   # Adjust as needed
                                    'marginLeft': '6px',
                                    'verticalAlign': 'middle', 
                                    'marginRight': '4px', 
                                }),
                                html.Div(['Runtime (secs)*'], style={'fontWeight': '400'}),
                                info_mark(info_text='(*Mandatory) Enter the duration you want the model to run for. Greater the duration, better the result.', id='runtime'),
                            ], style={'width': '180px', 'display': 'flex', 'alignItems': 'center', 'marginRight': '8px'}),
                            
                            dbc.Input(id='input-time-limit', type='number', placeholder='', min=60, style={
                                'width': '180px', 
                                'color': 'white', 
                                'background': '#226220d6', 
                                'padding': '2px 10px', 
                            }),    
                        ], style={ 
                            'display': 'flex', 
                            'flexDirection': 'row',
                            'justifyContent': 'spaceBetween', 
                        }),
                    ], style={
                        'display': 'flex', 
                        'flexDirection': 'row',
                        'borderRadius': '5px',
                        'backgroundColor': 'rgb(236 254 235)',
                        'padding': '6px',
                        'marginTop': '16px'
                    }),
                    html.Div([
                        create_button(text='Set Runtime', id='set-params-btn'), 
                        html.Div(id='set-params-message', style={'fontSize': '14px', 'marginLeft': '10px',})
                    ], style={'display': 'flex', 'flexDirection': 'row', 'alignItems': 'center', 'marginTop': '12px'})
                ]),
                html.Div([ 
                    create_button(text='Solve', id='solve-btn'), 
                    dbc.Progress(id="solve-progress", value=0, max=100, striped=True, animated=True, style={"display": "none"}), 
                    dcc.Interval(id="progress-interval", interval=2000, n_intervals=0, disabled=True), 
                ], style={'display': 'flex', 'flexDirection': 'row', 'alignItems': 'center', 'marginTop': '6px'})
            ], id='input-content', style=input_content_style),
        ], id='input-container', className="d-flex justify-content-center align-items-center", style={'paddingTop': '30px'}),
    ], id='input-wrapper', style=input_wrapper_style), 
    
    html.Div([
        dbc.Container([
            html.Div([
                create_button(text='View Result', id='open-decision-vars-overlay', margin_top='10px', width='200px'),
                dbc.Modal([
                    dbc.ModalHeader(
                        dbc.ModalTitle("Result"),
                        close_button=True
                    ),
                    dbc.ModalBody([
                        html.Div(id="decision-vars-container")
                    ]),
                    dbc.ModalFooter([
                        create_button(text='Download (.csv)', id='download-decision-vars', width='180px'), 
                        create_button(text='Close', id='close-decision-vars-overlay', width='120px'), 
                        # dbc.Button("Download", id="download-decision-vars", color="primary", className="me-2"),
                        # dbc.Button("Close", id="close-decision-vars-overlay", className="ml-auto"), 
                        dcc.Download(id="download-decision-vars-csv"),
                    ]),
                ], id="view-decision-vars-overlay", is_open=False, size='xl'), 
                # html.Div(id='result-container', style={'marginTop': '20px'}), 
                # html.Div(id='model-cost', style={'fontSize': '16px', 'marginTop': '10px'}), 

                html.Div(
                    style={'display': 'flex', 'flexWrap': 'wrap', 'alignItems': 'center', 'justifyContent': 'space-between', 'gap': '10px', 'fontSize': '22px', 'marginTop': '16px'},
                    children=[
                        # Box A
                        create_cost_box('total', 'Total Cost ($)', 'assets/icons/cost-round-svgrepo-com.svg', '20px'),
                        # Equal sign
                        html.Div("=", style={'textAlign': 'center'}),
                        # Box B
                        create_cost_box('buy', 'Buy Cost', 'assets/icons/market-purchase-svgrepo-com.svg', '18px'), 
                        # Plus sign 
                        html.Div("+", style={'textAlign': 'center'}), 
                        # Box C 
                        create_cost_box('fuel', 'Fuel Cost', 'assets/icons/fuel-14-svgrepo-com.svg', '16px'), 
                        # Plus sign 
                        html.Div("+", style={'textAlign': 'center'}), 
                        # Box D
                        create_cost_box('ins', 'Insurance Cost', 'assets/icons/shield-svgrepo-com.svg', '22px'), 
                        # Plus sign
                        html.Div("+", style={'textAlign': 'center'}),
                        # Box E
                        create_cost_box('mnt', 'Maintenance Cost', 'assets/icons/repair-svgrepo-com.svg', '22px'), 
                        # Plus sign
                        html.Div("-", style={'textAlign': 'center'}),
                        # Box F
                        create_cost_box('sell', 'Sale Revenue', 'assets/icons/sale-svgrepo-com.svg', '14px'), 
                    ]
                ),

                html.Div([
                    html.Label("Filter by Time",),
                    html.Div([
                        dcc.RangeSlider(
                            id='time-slider',
                            min=2023, # dummy value
                            max=2038, # dummy value
                            step=1,
                            marks={i: str(i) for i in range(2023, 2039)}, # dummy value
                            value=[2023, 2038], # dummy value
                        ),
                    ], style={'width': '90%'})
                ], style={'marginTop': '20px', 'display': 'flex', 'flexDirection': 'row', 'justifyContent': 'space-between'}),
                html.Div([
                    html.Label("Select Chart", style={'width': '140px'}),
                    dcc.Dropdown(
                        id='chart-dropdown',
                        options=[
                            {'label': 'Cost Breakdown', 'value': 'cost'},
                            {'label': 'Carbon Emissions Breakdown', 'value': 'carbon_emissions'}, 
                            {'label': 'Distance Covered Breakdown', 'value': 'distance'}, 
                            {'label': 'Vehicles Bought and Sold', 'value': 'buy_sell'},
                            # {'label': 'Sell', 'value': 'sell'},
                            {'label': 'Vehicles Used', 'value': 'use'}, 
                            {'label': 'Adoption Trend of Vehicles by Type', 'value': 'adoption_trend'}, 
                            {'label': 'Carbon Emissions Trend', 'value': 'emissions_trend'}
                        ],
                        placeholder="Select",
                        style={'width': '100%'}
                    ),
                ], style={'marginTop': '6px', 'marginBottom': '6px', 'display': 'flex', 'flexDirection': 'row', 'justifyContent': 'space-around', 'alignItems': 'center'}),
                
                html.Div([
                    html.Div([
                        html.Div([
                            html.Label('Type:', style={'display': 'inline-block', 'marginRight': '10px'}),
                            create_radio_items(items=['BEV', 'Diesel', 'LNG'], value='LNG', id='type-filter'), 
                        ], style={'width': '60%', 'display': 'inline-block'}),
                        html.Div([
                            html.Label('Size:', style={'display': 'inline-block', 'marginRight': '10px'}),
                            create_radio_items(['S1', 'S2', 'S3', 'S4'], 'S1', 'size-filter')
                        ], style={'width': '40%', 'display': 'inline-block'}),
                    ], id='filter-1', style={'width': '96%', 'display': 'none'}), 
                    html.Div([
                        html.Div([
                            html.Label('Fuel:', style={'display': 'inline-block', 'marginRight': '10px'}), 
                            create_radio_items(['Electricity', 'B20', 'HVO', 'LNG', 'BioLNG'], 'LNG', 'fuel-filter')
                        ], style={'width': '60%', 'display': 'inline-block'}), 
                        html.Div([
                            html.Label('Distance:', style={'display': 'inline-block', 'marginRight': '10px'}), 
                            create_radio_items(['D1', 'D2', 'D3', 'D4'], 'D1', 'dist-filter')
                        ], style={'width': '40%', 'display': 'inline-block'})
                    ], id='filter-2', style={'width': '96%', 'display': 'none'})
                ], style={'display': 'flex', 'flexDirection': 'column'}, id='filter-container'), 
                
                # insert plot here
                dcc.Loading(
                    id='loading-chart',
                    children=[dcc.Graph(id='result-chart', style={'height': '600px'})], 
                    type='default'
                ), 
            ], id='output-content', style=output_content_style),
        ], id='output-container', className="d-flex justify-content-center align-items-center", style={'paddingTop': '30px', 'paddingBottom': '30px'}),
    ], id='output-wrapper', style=output_wrapper_style),

], fluid=True, style={
    'margin': '0', 
    'padding': '0', 
    'width': '100vw'
}) 


#############################################################################
# Callback to toggle between input and output content
@app.callback(
    [
        Output("input-wrapper", "style"),
        Output("output-wrapper", "style"),
        Output("toggle-btn", "children"), 
        Output('toggle-btn', 'style')
    ],
    [Input("toggle-btn", "n_clicks")],
    [State("toggle-btn", "children")]
)
def toggle_content(n_clicks, button_text):
    inp_wrapper_style = input_wrapper_style.copy()
    out_wrapper_style = output_wrapper_style.copy()
    button_style = toggle_button_style.copy()

    if n_clicks is None or n_clicks == 0 or button_text == 'Output':
        inp_wrapper_style['display'] = 'block'
        out_wrapper_style['display'] = 'none'
        return inp_wrapper_style, out_wrapper_style, "Input", button_style
    
    inp_wrapper_style['display'] = 'none'
    out_wrapper_style['display'] = 'block'

    button_style['background'] = 'rgb(199, 221, 198)'
    button_style['color'] = 'rgb(25 79 23)'
    button_style['fontWeight'] = '500'
    return inp_wrapper_style, out_wrapper_style, "Output", button_style

model = None
uploaded_data = {} # *addition*

# Callback to handle the submit button
@app.callback(
    Output('submit-message', 'children'),
    Output('inputs-dropdown', 'options'), 
    Input('submit-btn', 'n_clicks'),
    State('upload-demand', 'filename'),
    State('upload-fuels', 'filename'),
    State('upload-vehicles', 'filename'),
    State('upload-vehicles-fuels', 'filename'),
    State('upload-cost-profiles', 'filename'),
    State('upload-carbon-emissions', 'filename'),
    State('upload-start', 'filename')
)
def handle_submit(n_clicks, demand, fuels, vehicles, vehicles_fuels, cost_profiles, carbon_emissions, start):
    if n_clicks is None:
        return "", []

    # Check if all mandatory files are uploaded
    if not all([demand, fuels, vehicles, vehicles_fuels, cost_profiles, carbon_emissions]):
        return "Please upload all mandatory files.", []

    options = []
    if demand:
        options.append({'label': 'Demand', 'value': 'demand'})
    if fuels:
        options.append({'label': 'Fuels', 'value': 'fuels'})
    if vehicles:
        options.append({'label': 'Vehicles', 'value': 'vehicles'})
    if vehicles_fuels:
        options.append({'label': 'Vehicles Fuels', 'value': 'vehicles_fuels'})
    if cost_profiles:
        options.append({'label': 'Cost Profiles', 'value': 'cost_profiles'})
    if carbon_emissions:
        options.append({'label': 'Carbon Emissions', 'value': 'carbon_emissions'})
    if start:
        options.append({'label': 'Updated Data', 'value': 'start'})
    return 'Click on "Create" to create model.', options

@app.callback(
    Output('set-params-message', 'children'),
    Input('set-params-btn', 'n_clicks'),
    State('input-time-limit', 'value'), 
)
def handle_set_params(n_clicks, time_limit):
    if n_clicks is None:
        return ""
    if time_limit is None:
        return "Please set runtime."

    # global disable_solve
    # disable_solve = True
    model.setParams(time_limit=time_limit)
    return 'Click on "Solve" to start optimization.'

@app.callback(
    Output('file-name-demand', 'children'),
    Output('file-name-fuels', 'children'),
    Output('file-name-vehicles', 'children'),
    Output('file-name-vehicles-fuels', 'children'),
    Output('file-name-cost-profiles', 'children'),
    Output('file-name-carbon-emissions', 'children'),
    Output('file-name-start', 'children'),
    Input('upload-demand', 'contents'),
    Input('upload-fuels', 'contents'),
    Input('upload-vehicles', 'contents'),
    Input('upload-vehicles-fuels', 'contents'),
    Input('upload-cost-profiles', 'contents'),
    Input('upload-carbon-emissions', 'contents'),
    Input('upload-start', 'contents'),
    State('upload-demand', 'filename'),
    State('upload-fuels', 'filename'),
    State('upload-vehicles', 'filename'),
    State('upload-vehicles-fuels', 'filename'),
    State('upload-cost-profiles', 'filename'),
    State('upload-carbon-emissions', 'filename'),
    State('upload-start', 'filename')
)
def update_output(
    demand_contents, fuels_contents, vehicles_contents, vehicles_fuels_contents, cost_profiles_contents, carbon_emissions_contents, start_contents, 
    demand_filename, fuels_filename, vehicles_filename, vehicles_fuels_filename, cost_profiles_filename, carbon_emissions_filename, start_filename
):
    global uploaded_data
    for content, filename, key in zip(
        [demand_contents, fuels_contents, vehicles_contents, vehicles_fuels_contents,
         cost_profiles_contents, carbon_emissions_contents, start_contents],
        [demand_filename, fuels_filename, vehicles_filename, vehicles_fuels_filename,
         cost_profiles_filename, carbon_emissions_filename, start_filename],
        ['demand', 'fuels', 'vehicles', 'vehicles_fuels', 'cost_profiles', 'carbon_emissions', 'start']
    ):
        if content is not None:
            df = parse_contents(content, filename)
            if df is not None:
                uploaded_data[key] = df

    return (demand_filename or '', fuels_filename or '', vehicles_filename or '', 
            vehicles_fuels_filename or '', cost_profiles_filename or '', 
            carbon_emissions_filename or '', start_filename or '')

# Callback to toggle the overlay
@app.callback(
    Output("view-inputs-overlay", "is_open"),
    [Input("open-view-inputs-overlay", "n_clicks"), Input("close-view-inputs-overlay", "n_clicks")],
    [State("view-inputs-overlay", "is_open")],
)
def toggle_inputs_overlay(open_click, close_click, is_open):
    if open_click or close_click:
        return not is_open
    return is_open

# Callback to display the data table
@app.callback(
    Output('inputs-table-container', 'children'),
    Input('inputs-dropdown', 'value')
)
def display_table(selected_filename):
    if selected_filename is None:
        return ''
    df = uploaded_data[selected_filename]
    return dash_table.DataTable(data=df.to_dict('records'), page_size=5)

@app.callback(
    Output('create-btn', 'disabled'), 
    Input('submit-btn', 'n_clicks'), 
    Input('inputs-dropdown', 'options'), 
)
def disable_create_button(n_clicks, options):
    if n_clicks is None or len(options) < 6: 
        return True
    return False

@app.callback(
    Output('set-params-btn', 'disabled'),
    # Input('submit-btn', 'n_clicks'), 
    Input('create-btn', 'n_clicks'),
    Input('create-btn', 'disabled')
)
def disable_set_params_button(create_n_clicks, create_disabled):
    if create_n_clicks is None or create_disabled:
        return True
    return False

@app.callback(
    Output('solve-btn', 'disabled'),
    Input('set-params-btn', 'n_clicks'),
    Input('set-params-btn', 'disabled'),
    State('input-time-limit', 'value')
)
def disable_solve_button(params_n_clicks, params_disabled, time_limit):
    if params_n_clicks is None or params_disabled or time_limit is None:
        return True
    return False

@app.callback(
    Output('model-message', 'children'), 
    Input('create-btn', 'n_clicks'), 
)
def create_model(n_clicks,):
    if n_clicks is None:
        return ''
        
    global model, uploaded_data
    # instantiate model
    model = OptiModel(
        uploaded_data['demand'],
        uploaded_data['vehicles'],
        uploaded_data['fuels'],
        uploaded_data['vehicles_fuels'],
        uploaded_data['carbon_emissions'],
        uploaded_data['cost_profiles'],
        uploaded_data.get('start'), 
    )

    # add decision variables, constraints and objective
    model.create()
    return 'Model created. Set model runtime.'

# Callback to show the output content when the Solve button is clicked
@app.callback(
    Output('decision-vars-container', 'children'), 
    Output('figure-best-total', 'children'), 
    Output('time-slider', 'min'), 
    Output('time-slider', 'max'), 
    Output('time-slider', 'marks'), 
    Output('time-slider', 'value'),
    Input('solve-btn', 'n_clicks'), 
)
def solve_model_and_show_output_content(n_clicks):
    global model
    if n_clicks is None or model is None:
        return {}, '-', 0, 0, {}, []

    result, best_bound, ymin, ymax = model.solve() # dictionary
    result_df = pd.DataFrame.from_dict(result)
    return (
        dash_table.DataTable(data=result_df.to_dict('records'), page_size=10), 
        f'*Best Bound: {best_bound/ 1e6: .2f}M', 
        ymin, ymax, {i: str(i) for i in range(ymin, ymax+1)}, [ymin, ymax]
    )

@app.callback(
    Output('figure-total', 'children'),
    Output('figure-buy', 'children'),
    Output('figure-sell', 'children'),
    Output('figure-fuel', 'children'),
    Output('figure-ins', 'children'),
    Output('figure-mnt', 'children'),
    Input('time-slider', 'value'), 
)
def update_subcosts(selected_range):
    global model
    if model is None:
        return ['-'], ['-'], ['-'], ['-'], ['-'], ['-']
    
    cost_df = model.cost_breakdown(selected_range, 'All', 'All')
    cost_df = cost_df.groupby(['Cat']).sum()
    buy_cost, sell_rev, fuel_cost, ins_cost, mnt_cost = (
        cost_df.loc['Buy<br>Cost', 'Cost'], 
        cost_df.loc['Sell<br>Revenue', 'Cost'], 
        cost_df.loc['Fuel<br>Cost', 'Cost'], 
        cost_df.loc['Insurance<br>Cost', 'Cost'], 
        cost_df.loc['Maintenance<br>Cost', 'Cost']
    )
    total_cost = buy_cost + fuel_cost + ins_cost + mnt_cost - sell_rev
    return [f'{total_cost/ 1e6: .2f}M'], [f'{buy_cost/ 1e6: .2f}M'], [f'{sell_rev/ 1e6: .2f}M'], [f'{fuel_cost/ 1e6: .2f}M'], [f'{ins_cost/ 1e6: .2f}M'], [f'{mnt_cost/ 1e6: .2f}M']

@app.callback(
    Output('solve-progress', 'value'), 
    Output('solve-progress', 'label'), 
    Output('solve-progress', 'style'), 
    Output('solve-progress', 'animated'), 
    Output('progress-interval', 'disabled'), 
    Output('progress-interval', 'n_intervals'),
    Input('progress-interval', 'n_intervals'),
    Input('solve-btn', 'n_clicks'),
    # prevent_initial_call=True, 
)
def update_progress(n_intervals, n_clicks):
    base_style = {
        # 'marginTop': '8px', 
        'width': '100%', 
        'marginLeft': '20px',
    }

    if n_clicks is None: 
        return 0, '', {**base_style, 'display': 'none'}, False, True, 0
        
    time_limit = model.runtime()
    progress = min(100, n_intervals * (2000/ (time_limit * 1000)) * 100) 
    if progress >= 100:
        return 100, '100%', {**base_style, 'display': 'block'}, False, True, 0
    
    progress_text = f'{int(progress)}%' if progress >= 5 else ''
    return progress, progress_text, {**base_style, 'display': 'block'}, True, False, n_intervals
    
# Callback to toggle the overlay
@app.callback(
    Output("view-decision-vars-overlay", "is_open"),
    [Input("open-decision-vars-overlay", "n_clicks"), Input("close-decision-vars-overlay", "n_clicks")],
    [State("view-decision-vars-overlay", "is_open")],
)
def toggle_decision_vars_overlay(open_click, close_click, is_open):
    if open_click or close_click:
        return not is_open
    return is_open
    
@app.callback(
    Output("download-decision-vars-csv", "data"),
    Input("download-decision-vars", "n_clicks"),
    State("decision-vars-container", "children"),
    prevent_initial_call=True,
)
def download_decision_vars(n_clicks, table_content):
    if n_clicks is None:
        return dash.no_update
    
    df = pd.DataFrame(table_content['props']['data'])
    # Return the CSV file
    return dcc.send_data_frame(df.to_csv, "output.csv", index=False)


@app.callback(
    Output('filter-container', 'style'),
    Output('filter-1', 'style'),
    Output('filter-2', 'style'),
    Input('chart-dropdown', 'value')
)
def display_filter(selected_variable):
    disp_none = {'display': 'none'} 
    disp_block = {'display': 'block'}
    
    if selected_variable in ['use']:
        return disp_block, disp_block, disp_block 
    if selected_variable in ['cost', 'carbon_emissions', 'distance', 'buy_sell']: 
        return disp_block, disp_block, disp_none 
    return disp_none, disp_none, disp_none 

@app.callback(
    Output('type-filter', 'options'), 
    Output('size-filter', 'options'), 
    Input('chart-dropdown', 'value')
)
def add_all_option(selected_chart):
    T = ['BEV', 'Diesel', 'LNG']
    S = ['S1', 'S2', 'S3', 'S4']
    if selected_chart in ['cost', 'distance', 'carbon_emissions']:
        T.append('All')
        S.append('All')
        if selected_chart == 'carbon_emissions':
            T.remove('BEV')

    options_size = [{'label': s, 'value': s} for s in S]
    options_type = [{'label': t, 'value': t} for t in T]
    return options_type, options_size

@app.callback( 
    Output('fuel-filter', 'options'), 
    Input('type-filter', 'value'),
)
def link_type_and_fuel(selected_type):
    fuels = []
    if selected_type == 'BEV':
        fuels.append('Electricity')
    elif selected_type == 'LNG':
        fuels.extend(['LNG', 'BioLNG'])
    elif selected_type == 'Diesel':
        fuels.extend(['B20', 'HVO'])
    return [{'label': f, 'value': f} for f in fuels] 

# callback for charts 
@app.callback(
    Output('result-chart', 'figure'),
    Input('time-slider', 'value'),
    Input('type-filter', 'value'),
    Input('size-filter', 'value'),
    Input('fuel-filter', 'value'),
    Input('dist-filter', 'value'),
    Input('chart-dropdown', 'value')
)
def update_chart(selected_range, selected_type, selected_size, selected_fuel, selected_dist, selected_variable):
    if not selected_variable:
        return {}
        
    fig = None
    color_map = {'Buy': '#ef553b', 'Sell': '#636efa'}
    if selected_variable == 'cost': 
        df = model.cost_breakdown(selected_range, selected_type, selected_size)
        
        if (isinstance(df, pd.DataFrame) or isinstance(df, pd.Series)) and not df.empty and len(df) > 0:
            fig = px.treemap( 
                df, 
                path=['Cat', 'Year', 'ID', 'Fuel'],  
                values='Cost', 
            ) 
            fig.update_traces(hovertemplate='Cost/Revenue:<br> <b>$ %{value}<b>',)
            fig.update_layout(
                margin=dict(t=40, l=10, r=10, b=10)
            )
        else:
            fig = px.treemap()
            fig = add_text_empty_plot(fig)
        
    elif selected_variable == 'carbon_emissions': 
        df = model.emissions_breakdown(selected_range, selected_type, selected_size)
        # print(df)

        if (isinstance(df, pd.DataFrame) or isinstance(df, pd.Series)) and not df.empty and len(df) > 0:
            fig = px.treemap(
                df, 
                path=['Total', 'Year', 'ID', 'Fuel'], 
                values='Emissions', 
            )
            fig.update_traces(hovertemplate='Emissions:<br> <b>%{value} kg CO2<b>', root_color="lightgrey")
            fig.update_layout(
                margin = dict(t=40, l=10, r=10, b=10)
            )
        else:
            fig = px.treemap()
            fig = add_text_empty_plot(fig)
        
    elif selected_variable == 'distance':
        df = model.distance_covered_breakdown(selected_range, selected_type, selected_size)
        # print(df.head())
        
        if (isinstance(df, pd.DataFrame) or isinstance(df, pd.Series)) and not df.empty and len(df) > 0:
            # print(df.head())
            fig = px.treemap(
                df, 
                path=['Total', 'Year', 'Size', 'Distance_bucket', 'ID', 'Fuel'], 
                values='Distance',
            )

            fig.update_traces(hovertemplate='Distance Covered:<br> <b>%{value} km<b>', root_color="lightgrey")
            fig.update_layout(
                margin = dict(t=40, l=10, r=10, b=10)
            )
        else:
            fig = px.treemap()
            fig = add_text_empty_plot(fig)
        
    elif selected_variable == 'buy_sell':
        df = model.buy_sell_filtered(selected_range, selected_type, selected_size) 

        if (isinstance(df, pd.DataFrame) or isinstance(df, pd.Series)) and not df.empty and len(df) > 0:
            nmax = max(df.loc[df['Type'] == 'Buy', 'Num_Vehicles']) + max(df.loc[df['Type'] == 'Sell', 'Num_Vehicles']) + 1
            df = df.sort_values('ID_Year')
            fig = px.bar( 
                df, 
                x='Year', 
                y='Num_Vehicles', 
                color='Type', 
                animation_frame='ID_Year', 
                title=f'{selected_type}_{selected_size} Vehicles Bought/Sold by Year', 
                range_x=[selected_range[0] - 1, selected_range[1] + 1], 
                range_y=[0, nmax], 
                color_discrete_map=color_map
            )

            # Update x-axis to show only integer ticks
            fig.update_xaxes(
                tickmode='linear',
                dtick=1,
                tickformat='d'  # 'd' format specifier for integers
            )
            fig.update_yaxes(title_text='No. of Vehicles')
            fig.update_traces(width=0.5)
            fig = center_title(fig)
        else:
            fig = px.bar()
            fig = add_text_empty_plot(fig)
        
    elif selected_variable == 'use':
        df = model.use_filtered(selected_range, selected_type, selected_size, selected_fuel, selected_dist)

        if (isinstance(df, pd.DataFrame) or isinstance(df, pd.Series)) and not df.empty and len(df) > 0:
            nmax = max(df['Num_Vehicles']) + 1
            df = df.sort_values('ID_Year')
            fig = px.bar(
                df,
                x='Year', 
                y='Num_Vehicles', 
                animation_frame='ID_Year', 
                title=f'{selected_type}_{selected_size} Vehicles Used by Year [{selected_fuel} fuel; {selected_dist} demand]', 
                range_x = [selected_range[0] - 1, selected_range[1] + 1], 
                range_y = [0, nmax], 
            )

            fig.update_xaxes(
                tickmode='linear',
                dtick=1,
                tickformat='d'  # 'd' format specifier for integers
            )
            fig.update_yaxes(title_text='No. of Vehicles')
            fig.update_traces(width=0.5)
            fig = center_title(fig)
        else:
            fig = px.bar()
            fig = add_text_empty_plot(fig)

    elif selected_variable == 'adoption_trend':
        df = model.use_trend(selected_range)
        # print(df)
        if (isinstance(df, pd.DataFrame) or isinstance(df, pd.Series)) and not df.empty and len(df) > 0:
            fig = px.line(
                df, 
                x='Year', 
                y='Num_Vehicles', 
                color='Vehicle_Type', 
                title=f'Adoption Trend of Vehicles by Type (based on No. of Vehicles used)',
                range_x = [selected_range[0] - 1, selected_range[1] + 1], 
                line_shape = 'spline', 
                # markers=True
            )

            # fig = add_integer_ticks_xaxis(fig)
            fig.update_xaxes(
                tickmode='linear',
                dtick=1,
                tickformat='d'  # 'd' format specifier for integers
            )
            fig.update_yaxes(title_text='No. of Vehicles')
            fig.update_traces(
                mode='lines+markers',
                marker=dict(symbol='diamond-open', size=10, line=dict(width=1, color='DarkSlateGrey')),
                line=dict(width=2)
            )

            fig = center_title(fig)
        else:
            fig = px.line()
            fig = add_text_empty_plot(fig)
    
    elif selected_variable == 'emissions_trend':
        df = model.emissions_trend(selected_range)
        # print(df)

        if (isinstance(df, pd.DataFrame) or isinstance(df, pd.Series)) and not df.empty and len(df) > 0:
            fig = go.Figure()

            # Add bar trace for Emissions
            fig.add_trace(
                go.Bar(x=df['Year'], y=df['Emissions'], name="Emissions")
            )

            fig.add_trace(
                go.Scatter(x=df['Year'], y=df['Emissions_limit'], name="Emissions Limit", 
                        mode='lines+markers',
                        line=dict(width=2),
                        marker=dict(symbol='diamond-open', size=10, line=dict(width=1, color='DarkSlateGrey')))
            )

            # Update layout
            fig.update_layout(
                title='Carbon Emissions Trend',
                xaxis=dict(
                    title='Year',
                    tickmode='linear',
                    dtick=1,
                    tickformat='d',  # 'd' format specifier for integers
                    range=[selected_range[0] - 1, selected_range[1] + 1]
                ),
                yaxis=dict(title='Emissions (kg CO2)'),
                barmode='overlay',  # This allows the line to be visible through the bars
                legend=dict(x=1, y=1, bgcolor='rgba(255, 255, 255, 0.5)')
            )
            fig = center_title(fig)
            
        else:
            fig = px.line()
            fig = add_text_empty_plot(fig)
    return fig


# Run the app
if __name__ == '__main__':
    app.run_server(debug=True, port=8080)